import os
import sys
import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add the path to import modules
sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows, AsyncSessionLocal, afetch_rows_with_null_check
from supplementary_analyzer_client import SupplementaryAnalyzerFactory
from db.models import LiteratureSupplementaryMaterialsAnalysis

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize the analyzer
analyzer = SupplementaryAnalyzerFactory.create_analyzer_client()

# -------------------------
# Fetch unprocessed supplementary materials
# -------------------------
async def fetch_supplementary_materials(disease: str, target: Optional[str] = None):
    """Fetch supplementary materials from database that need processing (where analysis is null and both description and title are present)"""
    return await afetch_rows_with_null_check(LiteratureSupplementaryMaterialsAnalysis, disease, target)

# -------------------------
# Updated fetch function with null checks for supplementary materials
# -------------------------
async def afetch_rows_with_null_check(table_cls, disease: str, target: Optional[str] = None):
    """
    Fetch rows where:
    1. analysis OR keywords is null or empty (unprocessed/incomplete records)
    2. both description and title are present and not empty
    """
    if not disease:
        raise ValueError("Disease must be specified.")

    try:
        from sqlalchemy import and_, or_
        
        async with AsyncSessionLocal() as session:
            # First, let's debug what's in the database
            logger.info(f"Debugging: Checking records for disease='{disease}' and target='{target}'")
            
            # Count total records for this disease
            total_stmt = select(table_cls).where(table_cls.disease == disease)
            if target and target != "no-target":
                total_stmt = total_stmt.where(table_cls.target == target)
            
            total_result = await session.execute(total_stmt)
            total_records = total_result.scalars().all()
            logger.info(f"Total records found for disease '{disease}': {len(total_records)}")
            
            # Check records with null analysis/keywords
            null_analysis_stmt = select(table_cls).where(
                and_(
                    table_cls.disease == disease,
                    (table_cls.analysis.is_(None)) | (table_cls.analysis == '')
                )
            )
            if target and target != "no-target":
                null_analysis_stmt = null_analysis_stmt.where(table_cls.target == target)
                
            null_result = await session.execute(null_analysis_stmt)
            null_records = null_result.scalars().all()
            logger.info(f"Records with null/empty analysis: {len(null_records)}")
            
            # Check description and title status for these records
            if null_records:
                for i, record in enumerate(null_records[:3]):  # Check first 3 records
                    desc = getattr(record, 'description', None)
                    title = getattr(record, 'title', None)
                    logger.info(f"Record {i+1}: description='{desc}' (len={len(desc) if desc else 0}), title='{title}' (len={len(title) if title else 0})")

            # Now apply the full filter
            filters = [
                table_cls.disease == disease,
                # Check for unprocessed records (null or empty analysis OR keywords)
                ((table_cls.analysis.is_(None)) | (table_cls.analysis == '') |
                 (table_cls.keywords.is_(None)) | (table_cls.keywords == '')),
                # Ensure both description and title are present and not empty
                table_cls.description.is_not(None),
                table_cls.title.is_not(None),
                table_cls.description != '',
                table_cls.title != ''
            ]
            
            # Add target filter if provided
            if target and target != "no-target":
                filters.append(table_cls.target == target)

            stmt = select(table_cls).where(and_(*filters))
            result = await session.execute(stmt)
            rows = result.scalars().all()
            
            logger.info(f"Records matching all criteria (with valid description/title): {len(rows)}")
            
            return [
                {col.name: getattr(row, col.name) for col in table_cls.__table__.columns}
                for row in rows
            ] if rows else []
    
    except Exception as e:
        logger.error(f"Error while fetching unprocessed records from: {table_cls.__name__}")
        raise

async def analyse_supplementary_materials(suppl_data_list: List[Dict]):
    """Process and analyze each supplementary material - only if both description and title are present"""
    for suppl_data in suppl_data_list:
        try:
            # Double-check that we have both description and title
            description = suppl_data.get('description', '').strip()
            title = suppl_data.get('title', '').strip()
            
            if not description or not title:
                logger.info(f"Skipping PMCID {suppl_data.get('pmcid')} - missing description or title")
                continue
            
            # Check if description is "No description available"
            if description.lower() == "no description available":
                logger.info(f"Skipping LLM analysis for PMCID {suppl_data.get('pmcid')} - no proper description available")
                
                # Set default response for insufficient context
                default_response = {
                    "analysis": "there wasnt a proper context for this article to perform analysis",
                    "keywords": "there wasnt a proper context for this article to perform analysis"
                }
                
                await update_supplementary_analysis(default_response, suppl_data)
                logger.info("Updated Database with default response for insufficient context")
                continue
            
            logger.info(f"Processing supplementary material from PMCID: {suppl_data.get('pmcid')} - Title: {title[:100]}...")
            
            # Analyze the supplementary material
            suppl_analysis = await analyzer.analyze(suppl_data)
            logger.info("Generated Analysis from OpenAI GPT-4o-mini")
            
            # Update the database
            await update_supplementary_analysis(suppl_analysis, suppl_data)
            logger.info("Updated Database with Supplementary Material Analysis")
                     
        except Exception as e:
            logger.error(f"Error processing supplementary material from PMCID: {suppl_data.get('pmcid')}. Skipping. Error: {e}")
            # Store error information in the analysis field for debugging
            error_analysis = {
                "analysis": f"ERROR: {str(e)}",
                "keywords": f"ERROR: {str(e)}"
            }
            try:
                await update_supplementary_analysis(error_analysis, suppl_data)
                logger.info("Marked record with error information")
            except Exception as update_error:
                logger.error(f"Failed to update error information: {update_error}")


async def update_supplementary_analysis(suppl_analysis_data: Dict, suppl_metadata: Dict):
    """Update the analysis and keywords results in the database"""
    try:
        # Prepare the data to update (both analysis and keywords columns)
        update_data = {
            "analysis": suppl_analysis_data.get("analysis", ""),
            "keywords": suppl_analysis_data.get("keywords", "")
        }
        
        # Filter conditions to identify the specific row
        filter_conditions = {
            "pmcid": suppl_metadata.get("pmcid"),
            "disease": suppl_metadata.get("disease"),
            "target": suppl_metadata.get("target")
        }
        
        # If there's an index, use it as primary identifier (more reliable)
        if "index" in suppl_metadata:
            filter_conditions = {"index": suppl_metadata["index"]}
        
        await aupdate_table_rows(LiteratureSupplementaryMaterialsAnalysis, update_data, filter_conditions)
        logger.info("Updated supplementary material analysis and keywords in DB.")
        
    except Exception as e:
        logger.error(f"Error updating the Supplementary Material Analysis data to the DB: {e}")
        raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str = "no-disease", target: str = "no-target"):
    """Main function to run the supplementary materials analysis pipeline"""
    try:
        # Fetch supplementary materials that need analysis (where analysis is null and both description and title are present)
        suppl_materials = await fetch_supplementary_materials(disease, target)
        logger.info("Fetched unprocessed supplementary materials for analysis: %d", len(suppl_materials))
        
        if len(suppl_materials):
            logger.info("Analyzing Supplementary Materials...")
            await analyse_supplementary_materials(suppl_materials)
            logger.info("Supplementary materials analysis completed successfully!")
        else:
            logger.info("No unprocessed supplementary materials found matching the criteria (with both description and title present).")
            
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise e

# -------------------------
# CLI execution examples
# -------------------------
if __name__ == "__main__":
    # Default execution with new defaults: no-disease and no-target
    # asyncio.run(main())
    
    # Example 1: Analyze supplementary materials for a specific disease
    asyncio.run(main("phenylketonuria"))
    
    # Example 2: Analyze supplementary materials for a specific disease and target
    # asyncio.run(main("diabetes", "insulin"))
    
    # Example 3: Analyze all supplementary materials for a specific target across diseases
    # asyncio.run(main("no-disease", "glp1r"))
    
    # Example 4: Re-process records that had errors (where analysis contains "ERROR:")
    # You could create a separate function for this:
    # asyncio.run(reprocess_errors("alzheimer"))