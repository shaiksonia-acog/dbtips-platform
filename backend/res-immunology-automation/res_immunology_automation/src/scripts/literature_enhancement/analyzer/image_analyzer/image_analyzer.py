import os
import sys
import asyncio
from typing import Dict, List, Optional, Any

sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows
from figure_analyzer_abstract import AnalyzerFactory
from db.models import DiseaseImageAnalysis

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

analyzer = AnalyzerFactory.create_analyzer_client()

# -------------------------
# Fetch unprocessed images
# -------------------------
async def fetch_images(disease: str, target: Optional[str], status: str = "unprocessed"):
    return await afetch_rows(DiseaseImageAnalysis, disease, target, status)

# -------------------------
# Analyze each image
# -------------------------
async def analyse_images(images_data: List[Dict]):
    for image_data in images_data:
        try:
            logger.info(f"Processing image: {image_data.get('image_caption')} from PMCID: {image_data.get('PMCID')}")
            image_analysis = analyzer.analyze(image_data)
            await update_image_analysis(image_analysis, image_data)
        except Exception as e:
            logger.error(f"Error processing image: {image_data.get('image_caption')} from PMCID: {image_data.get('PMCID')}. Skipping. Error: {e}")
            continue

# -------------------------
# Update analysis to DB
# -------------------------
async def update_image_analysis(image_analysis_data: Dict, image_metadata: Dict):
    try:
        await aupdate_table_rows(DiseaseImageAnalysis, image_analysis_data, image_metadata)
        logger.info("Updated analysis in DB.")
    except Exception as e:
        logger.error("Error updating the Image Analysis data to the DB")
        raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: str = None, status: str = "unprocessed"):
    images = await fetch_images(disease, target, status)
    if len(images):
        logger.info("Analyzing Images")
        await analyse_images(images)

if __name__ == "__main__":
    asyncio.run(main("migraine disorder"))
