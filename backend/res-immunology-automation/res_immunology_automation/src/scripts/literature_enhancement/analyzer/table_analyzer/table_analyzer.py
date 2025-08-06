import os
import sys
import asyncio
from typing import Dict, List, Optional, Any

sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows
from analyzer import TablesAnalyzerFactory
from db.models import DiseaseTablesAnalysis

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

analyzer = TablesAnalyzerFactory.create_analyzer_client()

# -------------------------
# Fetch unprocessed images
# -------------------------
async def fetch_tables(disease: str, target: Optional[str]):
    return await afetch_rows(DiseaseTablesAnalysis, disease, target)

# -------------------------
# Analyze each image
# -------------------------
async def analyse_tables(tables_data: List[Dict]):
    for table_data in tables:
        try:
            logger.info(f"Processing image: {table_data.get('description')} from PMCID: {table_data.get('PMCID')}")
            table_analysis = analyzer.get_llm_response(table_data.get('table_schema'), table_data.get('table_description'))
            await update_table_analysis(table_analysis, table_data)
        except Exception as e:
            logger.error(f"Error processing image: {table_data.get('image_caption')} from PMCID: {table_data.get('PMCID')}. Skipping. Error: {e}")
            continue

# -------------------------
# Update analysis to DB
# -------------------------
async def update_tables_analysis(table_analysis_data: Dict, table_metadata: Dict):
    try:
        await aupdate_table_rows(DiseaseTablesAnalysis, table_analysis_data, table_metadata)
        logger.info("Updated analysis in DB.")
    except Exception as e:
        logger.error("Error updating the Image Analysis data to the DB")
        raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: str = None):
    tables = await fetch_tables(disease, target)
    if len(tables):
        logger.info("Analyzing Tables")
        await analyse_tables(images)

if __name__ == "__main__":
    asyncio.run(main("migraine disorder"))
