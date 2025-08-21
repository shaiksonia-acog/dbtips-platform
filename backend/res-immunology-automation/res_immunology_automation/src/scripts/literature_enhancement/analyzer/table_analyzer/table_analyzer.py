import os
import sys
sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)
import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from literature_enhancement.db_utils.async_utils import (
    afetch_rows, 
    aupdate_table_rows, 
    AsyncSessionLocal, 
    create_pipeline_status,
    check_pipeline_status,
    afetch_rows_with_null_check  # Now imported from utils
)
from literature_enhancement.analyzer.table_analyzer.table_analyzer_client import TableAnalyzerFactory
from literature_enhancement.analyzer.retry_decorators import (
    async_api_retry, 
    PipelineStopException, 
    ContinueToNextRecordException
)
from db.models import LiteratureTablesAnalysis

import logging
module_name = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(module_name)

# Initialize the analyzer
analyzer = TableAnalyzerFactory.create_analyzer_client()

def log_prefix(disease: str, target: str) -> str:
    """Generate consistent log prefix"""
    return f"[Disease: {disease}, Target: {target}]"

def get_normalized_values(disease: str, target: str) -> tuple:
    """Get normalized disease and target values with defaults"""
    return (
        disease or "no-disease",
        target or "no-target"
    )

async def should_skip_analysis(disease: str, target: str) -> bool:
    """Check if table analysis should be skipped (already completed)"""
    current_status = await check_pipeline_status(disease, target, "table-analysis")
    if current_status == "completed":
        logger.info(f"{log_prefix(disease, target)} Table analysis already completed - skipping")
        return True
    return False

async def check_prerequisites(disease: str, target: str) -> bool:
    """Check if prerequisite pipelines (extraction, segregation) are completed"""
    required_pipelines = ["extraction", "segregation"]
    
    for pipeline_type in required_pipelines:
        status = await check_pipeline_status(disease, target, pipeline_type)
        if status != "completed":
            logger.error(f"{log_prefix(disease, target)} Prerequisite pipeline '{pipeline_type}' not completed (status: {status})")
            return False
    
    logger.info(f"{log_prefix(disease, target)} All prerequisite pipelines completed")
    return True

# -------------------------
# Fetch unprocessed tables (now uses utils function)
# -------------------------
async def fetch_tables(disease: str, target: Optional[str] = None):
    """Fetch tables from database that need processing (where analysis or keywords are null)"""
    return await afetch_rows_with_null_check(
        table_cls=LiteratureTablesAnalysis, 
        disease=disease, 
        target=target,
        null_columns=['analysis', 'keywords']  # Specify which columns to check
    )

@async_api_retry(max_retries=3, base_delay=2.0, backoff_multiplier=2.5)
async def analyze_single_table_with_retry(analyzer_instance, table_data: Dict) -> Dict:
    """
    Wrapper for table analysis with retry mechanism
    This function will be retried by the decorator
    """
    try:
        logger.debug(f"Making OpenAI API call for table analysis: {table_data.get('pmcid')}")
        
        # Analyze the table - this may raise exceptions
        table_analysis = await analyzer_instance.analyze(table_data)
        logger.debug("Generated Analysis from OpenAI GPT-4o-mini")
        
        return table_analysis
        
    except Exception as e:
        # Convert specific exceptions to httpx exceptions for consistent retry handling
        if "timeout" in str(e).lower():
            import httpx
            raise httpx.TimeoutException(str(e)) from e
        elif any(code in str(e) for code in ["400", "401", "403", "404", "500", "502", "503"]):
            import httpx
            raise httpx.HTTPStatusError(str(e), request=None, response=None) from e
        else:
            raise  # Re-raise as-is for other exceptions

async def analyse_tables(tables_data: List[Dict], disease: str, target: str):
    """
    Process and analyze each table with enhanced error handling for retry mechanism
    Handles both timeout errors (continue to next record) and critical errors (stop pipeline)
    """
    total_tables = len(tables_data)
    processed = 0
    timeout_errors = 0
    critical_errors = 0
    
    prefix = log_prefix(disease, target)
    
    logger.info("=" * 50)
    logger.info("STARTING TABLE ANALYSIS PIPELINE")
    logger.info("=" * 50)
    
    for idx, table_data in enumerate(tables_data, 1):
        pmcid = table_data.get('pmcid', 'unknown')
        
        try:
            logger.info(f"\n{prefix} Processing {idx}/{total_tables}: {pmcid}")
            logger.info(f"Processing table from PMCID: {pmcid} - {table_data.get('table_description', 'No description')[:100]}...")
            
            # Analyze the table with retry mechanism
            # This may raise RuntimeError for critical errors
            table_analysis = await analyze_single_table_with_retry(analyzer, table_data)
            
            # Update the database
            await update_table_analysis(table_analysis, table_data)
            logger.debug("Updated Database with Table Analysis")
            
            processed += 1
            logger.info(f"{prefix} Success: {pmcid}")
            
            # Add delay between tables
            if idx < total_tables:
                await asyncio.sleep(1.0)
                     
        except ContinueToNextRecordException as e:
            # Timeout errors - record continues but log the timeout
            timeout_errors += 1
            logger.warning(f"{prefix} Timeout error: {pmcid} - continuing to next record")
            
            # Store timeout error information in the analysis field for debugging
            error_analysis = {
                "analysis": f"TIMEOUT: Analysis timed out after retries - {str(e)}",
                "keywords": "timeout_error"
            }
            
            try:
                await update_table_analysis(error_analysis, table_data)
                logger.info("Marked record with timeout information")
            except Exception as update_error:
                logger.error(f"Failed to update timeout information: {update_error}")
            
            continue  # Continue to next record
            
        except PipelineStopException as e:
            # Critical errors that should stop the entire pipeline
            logger.error(f"{prefix} CRITICAL ERROR - Stopping pipeline: {pmcid} - {str(e)}")
            critical_errors += 1
            
            # Update database with error status for current record
            error_analysis = {
                "analysis": f"CRITICAL ERROR: Pipeline stopped - {str(e)}",
                "keywords": "critical_error"
            }
            
            try:
                await update_table_analysis(error_analysis, table_data)
            except Exception as update_error:
                logger.error(f"Failed to update error information: {update_error}")
            
            # Re-raise to stop the entire pipeline
            raise RuntimeError(f"Pipeline stopped due to critical error at record {pmcid}: {str(e)}") from e
            
        except Exception as e:
            # Unexpected errors - also stop the pipeline for safety
            logger.error(f"{prefix} UNEXPECTED ERROR - Stopping pipeline: {pmcid} - {str(e)}")
            critical_errors += 1
            
            # Store error information in the analysis field for debugging
            error_analysis = {
                "analysis": f"UNEXPECTED ERROR: Pipeline stopped - {str(e)}",
                "keywords": "unexpected_error"
            }
            
            try:
                await update_table_analysis(error_analysis, table_data)
                logger.info("Marked record with error information")
            except Exception as update_error:
                logger.error(f"Failed to update error information: {update_error}")
            
            # Raise as RuntimeError to indicate pipeline should stop
            raise RuntimeError(f"Pipeline stopped due to unexpected error at record {pmcid}: {str(e)}") from e
    
    # Summary - only reached if no critical errors occurred
    logger.info("\n" + "=" * 50)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total: {total_tables}")
    logger.info(f"Processed: {processed}")
    logger.info(f"Timeout errors: {timeout_errors}")
    logger.info(f"Critical errors: {critical_errors}")
    logger.info("=" * 50)

async def update_table_analysis(table_analysis_data: Dict, table_metadata: Dict):
    """
    Update the analysis results in the database
    Enhanced with better error handling for database operations
    Only updates columns that exist in the LiteratureTablesAnalysis table
    """
    try:
        # Prepare the data to update (only columns that exist in the database table)
        update_data = {
            "analysis": table_analysis_data.get("analysis", ""),
            "keywords": table_analysis_data.get("keywords", "")
        }
        
        # Handle error cases by storing error info in the analysis field
        # since status and error_message columns don't exist in the table
        if table_analysis_data.get("error_message"):
            error_status = table_analysis_data.get("status", "error")
            error_msg = table_analysis_data.get("error_message", "Unknown error")
            update_data["analysis"] = f"ERROR ({error_status}): {error_msg}"
            update_data["keywords"] = f"error_{error_status}"
        
        # Filter conditions to identify the specific row
        filter_conditions = {
            "pmcid": table_metadata.get("pmcid"),
            "disease": table_metadata.get("disease"),
            "target": table_metadata.get("target")
        }
        
        # If there's an index, use it as primary identifier (more reliable)
        if "index" in table_metadata:
            filter_conditions = {"index": table_metadata["index"]}
        
        await aupdate_table_rows(LiteratureTablesAnalysis, update_data, filter_conditions)
        logger.debug("Updated table analysis in DB.")
        
    except Exception as e:
        logger.error(f"Error updating the Table Analysis data to the DB: {e}")
        # Re-raise database errors as they might indicate bigger issues
        raise RuntimeError(f"Database update failed: {str(e)}") from e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: Optional[str] = None):
    """
    Main function to run the table analysis pipeline
    Enhanced with comprehensive error handling following literature extraction pattern
    Properly handles both timeout errors (continue) and critical errors (stop pipeline)
    Only creates pipeline status record if successful
    """
    # Normalize inputs
    disease, target = get_normalized_values(disease, target)
    prefix = log_prefix(disease, target)
    
    logger.info(f"{prefix} Starting table analysis pipeline")
    
    try:
        # FIRST: Check if pipeline is already completed - skip if yes
        if await should_skip_analysis(disease, target):
            return True

        # # SECOND: Check prerequisites (extraction and segregation must be completed)
        # if not await check_prerequisites(disease, target):
        #     raise RuntimeError("Prerequisites not met - extraction and segregation must be completed first")
        
        # THIRD: Perform Table Analysis
        logger.info(f"{prefix} Performing Table Analysis...")
        
        # Fetch tables that need analysis (where analysis or keywords are null/empty)
        tables = await fetch_tables(disease, target)
        logger.info(f"{prefix} Found {len(tables)} unprocessed tables for analysis")
        
        if tables:
            logger.info(f"{prefix} Analyzing Tables...")
            # Process tables through the analysis pipeline
            # This may raise RuntimeError for critical errors
            await analyse_tables(tables, disease, target)
            logger.info(f"{prefix} Table analysis completed successfully!")
        else:
            logger.info(f"{prefix} No unprocessed tables found matching the criteria.")
        
        # ONLY create pipeline status if successful
        await create_pipeline_status(disease, target, "table-analysis", "completed")
        logger.info(f"{prefix} Pipeline status updated: completed")
        return True
        
    except RuntimeError as e:
        # Critical errors from the pipeline (API failures, etc.)
        error_message = str(e)
        logger.error(f"{prefix} Pipeline failed due to critical error: {error_message}")
        
        # Log final error summary
        logger.error("\n" + "=" * 50)
        logger.error("PIPELINE FAILED")
        logger.error("=" * 50)
        logger.error(f"Reason: {error_message}")
        logger.error("=" * 50)
        
        # DO NOT create pipeline status for failures - let retry mechanism handle it
        # Re-raise so build_dossier can handle the error
        raise RuntimeError(f"Table analysis failed for {disease}-{target}: {error_message}") from e
        
    except Exception as e:
        # Unexpected errors in main function
        error_message = f"Unexpected pipeline error: {str(e)}"
        logger.error(f"{prefix} Pipeline failed due to unexpected error: {error_message}")
        
        # DO NOT create pipeline status for failures
        # Re-raise so build_dossier can handle the error
        raise RuntimeError(f"Table analysis failed for {disease}-{target}: {error_message}") from e

# -------------------------
# CLI execution examples
# -------------------------
if __name__ == "__main__":
    try:
        # Default execution with new defaults: no-disease and glp1r
        # asyncio.run(main())
        
        # Example 1: Analyze tables for a specific disease (target is optional)
        asyncio.run(main("cardiovascular disease"))
        
        # Example 2: Analyze tables for a specific disease and target
        # asyncio.run(main("diabetes", "insulin"))
        
        # Example 3: Re-process records that had errors (where analysis contains "ERROR:")
        # You could create a separate function for this:
        # asyncio.run(reprocess_errors("alzheimer"))
        
    except RuntimeError as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)  # Exit with error code
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {str(e)}")
        sys.exit(1)