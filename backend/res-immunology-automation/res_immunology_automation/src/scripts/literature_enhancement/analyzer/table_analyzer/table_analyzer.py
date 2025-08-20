import os
import sys
import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from literature_enhancement.db_utils.async_utils import (
    afetch_rows, 
    aupdate_table_rows, 
    AsyncSessionLocal, 
    create_pipeline_status,
    afetch_rows_with_null_check  # Now imported from utils
)
from literature_enhancement.analyzer.table_analyzer.table_analyzer_client import TableAnalyzerFactory
from db.models import LiteratureTablesAnalysis

import logging
module_name = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(module_name)


# Initialize the analyzer
analyzer = TableAnalyzerFactory.create_analyzer_client()


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


async def analyse_tables(tables_data: List[Dict]):
    """Process and analyze each table"""
    for table_data in tables_data:
        print("table data:", table_data)
        try:
            logger.info(f"Processing table from PMCID: {table_data.get('pmcid')} - {table_data.get('table_description', 'No description')[:100]}...")
            
            # Analyze the table
            table_analysis = await analyzer.analyze(table_data)
            logger.debug("Generated Analysis from OpenAI GPT-4o-mini")
            
            # Update the database
            await update_table_analysis(table_analysis, table_data)
            logger.debug("Updated Database with Table Analysis")
                     
        except Exception as e:
            logger.error(f"Error processing table from PMCID: {table_data.get('pmcid')}. Skipping. Error: {e}")
            # Store error information in the analysis field for debugging
            error_analysis = {
                "analysis": f"ERROR: {str(e)}",
                "keywords": "error"
            }
            try:
                await update_table_analysis(error_analysis, table_data)
                logger.info("Marked record with error information")
            except Exception as update_error:
                logger.error(f"Failed to update error information: {update_error}")
        break

async def update_table_analysis(table_analysis_data: Dict, table_metadata: Dict):
    """Update the analysis results in the database"""
    try:
        # Prepare the data to update (only the analysis and keywords columns)
        update_data = {
            "analysis": table_analysis_data.get("analysis", ""),
            "keywords": table_analysis_data.get("keywords", "")
        }
        
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
        raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: str):
    """Main function to run the table analysis pipeline"""
    try:
        # Fetch tables that need analysis (where analysis or keywords are null/empty)
        tables = await fetch_tables(disease, target)
        logger.info("Fetched unprocessed tables for analysis: %d", len(tables))
        
        if len(tables):
            logger.info("Analyzing Tables...")
            await analyse_tables(tables)
            logger.info("Table analysis completed successfully!")
        else:
            logger.info("No unprocessed tables found matching the criteria.")
        await create_pipeline_status(disease, target, "table-analysis", "completed")  
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise e

# -------------------------
# CLI execution examples
# -------------------------
if __name__ == "__main__":
    # Default execution with new defaults: no-disease and glp1r
    # asyncio.run(main())
    
    # Example 1: Analyze tables for a specific disease
    asyncio.run(main("asthma"))
    
    # Example 2: Analyze tables for a specific disease and target
    # asyncio.run(main("diabetes", "insulin"))
    
    # Example 3: Re-process records that had errors (where analysis contains "ERROR:")
    # You could create a separate function for this:
    # asyncio.run(reprocess_errors("alzheimer"))