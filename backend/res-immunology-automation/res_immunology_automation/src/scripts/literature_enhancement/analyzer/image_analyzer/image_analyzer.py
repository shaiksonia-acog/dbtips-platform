#image_analyzer.py (Enhanced with proper pipeline status management and error handling)
import os
import sys
import asyncio
from typing import Dict, List, Optional
from literature_enhancement.analyzer.image_analyzer.analyzer_client import ImageDataModel, ImageDataAnalysisResult
from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows, check_pipeline_status, create_pipeline_status
from db.models import LiteratureImagesAnalysis
from literature_enhancement.analyzer.image_analyzer.analyzer_pipeline import ThreeStageHybridAnalysisPipeline

import logging
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)

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
    """Check if image analysis should be skipped (already completed)"""
    current_status = await check_pipeline_status(disease, target, "image-analysis")
    if current_status == "completed":
        logger.info(f"{log_prefix(disease, target)} Image analysis already completed - skipping")
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

async def fetch_images(disease: str, target: Optional[str], status: str = "extracted"):
    """Fetch images from database that need analysis"""
    return await afetch_rows(LiteratureImagesAnalysis, disease, target, status)

async def process_images_hybrid(images_data: List[ImageDataModel], disease: str, target: str):
    """
    Process images through the pipeline with enhanced error handling for retry mechanism
    Handles both timeout errors (continue to next record) and critical errors (stop pipeline)
    """
    total_images = len(images_data)
    filtered = 0
    processed = 0
    genes_validated = 0
    errors = 0
    timeout_errors = 0
    critical_errors = 0
    
    pipeline = ThreeStageHybridAnalysisPipeline()
    prefix = log_prefix(disease, target)
    
    
    for idx, image_data in enumerate(images_data, 1):
        pmcid = image_data.get('pmcid', 'unknown')
    
        try:
            logger.info(f"\n{prefix} Processing {idx}/{total_images}: {pmcid}")
            
            # Process through the pipeline - may raise RuntimeError for critical errors
            result: ImageDataAnalysisResult = await pipeline.process_single_image(image_data)
            status = result.get('status', 'unknown')
            
            # Handle different result statuses
            if is_disease_pathway == False:
                filtered += 1
                logger.debug(f"{prefix} Not a Pathway Figure: {pmcid}")
                
            elif status == "processed":
                processed += 1
                if result.get('genes', 'not mentioned') != 'not mentioned':
                    genes_validated += 1
                logger.debug(f"{prefix} Success: {pmcid}")
                
            elif error_type in ["OpenAI Timeout", "MedGemma Timeout"]:
                # Timeout errors - record continues but log the timeout
                timeout_errors += 1
                logger.warning(f"{prefix} Timeout error: {pmcid} - {status}")
                
            elif error_type in ["OpenAI Parsing Error"] or status == "analysis_error":
                # Critical errors that should have stopped the pipeline
                critical_errors += 1
                logger.error(f"{prefix} Critical error occurred but not raised: {pmcid} - {status}")
                # This shouldn't happen if pipeline is working correctly
                # but we'll treat it as a pipeline error
                raise RuntimeError(f"Critical error not properly handled by pipeline: {status} for {pmcid}")
                
            else:
                errors += 1
                logger.error(f"{prefix} Unknown status: {pmcid} - {status}")
            
            # Update database with result
            await update_image_analysis(result, image_data)
            
            # Delay between images
            if idx < total_images:
                await asyncio.sleep(2.0)
                
        except RuntimeError as e:
            # Critical errors that should stop the entire pipeline
            logger.error(f"{prefix} CRITICAL ERROR - Stopping pipeline: {pmcid} - {str(e)}")
            critical_errors += 1
            
            # Update database with error status for current record
            error_result = {
                "keywords": "not mentioned", 
                "insights": "not mentioned", 
                "genes": "not mentioned", 
                "drugs": "not mentioned",
                "process": "not mentioned", 
                "is_disease_pathway": False,
                "error_message": f"Pipeline stopped due to critical error: {str(e)}",
                "status": "pipeline_stopped"
            }
            
            try:
                await update_image_analysis(error_result, image_data)
            except Exception as db_error:
                logger.error(f"{prefix} Failed to update database with error status: {str(db_error)}")
            
            # Re-raise to stop the entire pipeline
            raise RuntimeError(f"Pipeline stopped due to critical error at record {pmcid}: {str(e)}") from e
            
        except Exception as e:
            # Unexpected errors - also stop the pipeline for safety
            logger.error(f"{prefix} UNEXPECTED ERROR - Stopping pipeline: {pmcid} - {str(e)}")
            critical_errors += 1
            
            # Update database with error status
            error_result = {
                "keywords": "not mentioned", 
                "insights": "not mentioned", 
                "genes": "not mentioned", 
                "drugs": "not mentioned",
                "process": "not mentioned", 
                "is_disease_pathway": False,
                "error_message": f"Pipeline stopped due to unexpected error: {str(e)}",
                "status": "pipeline_stopped"
            }
            
            try:
                await update_image_analysis(error_result, image_data)
            except Exception as db_error:
                logger.error(f"{prefix} Failed to update database with error status: {str(db_error)}")
            
            # Raise as RuntimeError to indicate pipeline should stop
            raise RuntimeError(f"Pipeline stopped due to unexpected error at record {pmcid}: {str(e)}") from e
    
    # Summary - only reached if no critical errors occurred
    logger.info("\n" + "=" * 50)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total: {total_images}")
    logger.info(f"Filtered: {filtered}")
    logger.info(f"Processed: {processed}")
    logger.info(f"Genes validated: {genes_validated}")
    logger.info(f"Timeout errors: {timeout_errors}")
    logger.info(f"Errors: {errors}")
    logger.info(f"Critical errors: {critical_errors}")
    logger.info("=" * 50)

async def update_image_analysis(image_analysis_data: ImageDataAnalysisResult, image_metadata: ImageDataModel):
    """
    Update the analysis results in the database
    Enhanced with better error handling for database operations
    """
    try:
        # Clean up error_message field for successful processed records
        if image_analysis_data.get('status') == 'processed' and not image_analysis_data.get('error_message'):
            image_analysis_data['error_message'] = None

        await aupdate_table_rows(LiteratureImagesAnalysis, image_analysis_data, image_metadata)
        
    except Exception as e:
        logger.error(f"Error updating database for PMCID {image_metadata.get('pmcid', 'unknown')}: {str(e)}")
        # Re-raise database errors as they might indicate bigger issues
        raise RuntimeError(f"Database update failed: {str(e)}") from e

async def main(disease: str, target: str = None, record_status: List[str] = ["extracted", "error"]):
    """
    Main function - enhanced with comprehensive error handling following literature extraction pattern
    Properly handles both timeout errors (continue) and critical errors (stop pipeline)
    Only creates pipeline status record if successful
    """
    # Normalize inputs
    disease, target = get_normalized_values(disease, target)
    prefix = log_prefix(disease, target)
    logger.info("=" * 80)
    logger.info(f"IMAGE ANALYSIS PIPELINE INITIATED for {prefix}")
    logger.info("=" * 80)

    try:
        # FIRST: Check if pipeline is already completed - skip if yes
        if await should_skip_analysis(disease, target):
            return True

        # # SECOND: Check prerequisites (extraction and segregation must be completed)
        # if not await check_prerequisites(disease, target):
        #     raise RuntimeError("Prerequisites not met - extraction and segregation must be completed first")
        
        # THIRD: Perform Image Analysis
        logger.info(f"{prefix} Performing Image Analysis...")
        
        # Fetch images that need processing
        images = await fetch_images(disease, target, record_status)
        logger.info(f"{prefix} Found {len(images)} images to process")
        
        if images:
            # Process images through the hybrid pipeline
            # This may raise RuntimeError for critical errors
            await process_images_hybrid(images, disease, target)
            logger.info(f"{prefix} Pipeline completed successfully!")
        else:
            logger.info(f"{prefix} No images found to process")
        
        # ONLY create pipeline status if successful
        await create_pipeline_status(disease, target, "image-analysis", "completed")
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
        raise RuntimeError(f"Image analysis failed for {disease}-{target}: {error_message}") from e
        
    except Exception as e:
        # Unexpected errors in main function
        error_message = f"Unexpected pipeline error: {str(e)}"
        logger.error(f"{prefix} Pipeline failed due to unexpected error: {error_message}")
        
        # DO NOT create pipeline status for failures
        # Re-raise so build_dossier can handle the error
        raise RuntimeError(f"Image analysis failed for {disease}-{target}: {error_message}") from e

if __name__ == "__main__":
    try:
        asyncio.run(main("phenylketonuria"))
    except RuntimeError as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)  # Exit with error code
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {str(e)}")
        sys.exit(1)