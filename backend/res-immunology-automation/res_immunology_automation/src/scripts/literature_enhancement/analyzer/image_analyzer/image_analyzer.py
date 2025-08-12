import os
import sys
import asyncio
from typing import Dict, List, Optional, Any

sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows
from analyzer_client import AnalyzerFactory
from db.models import LiteratureImagesAnalysis

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

analyzer = AnalyzerFactory.create_analyzer_client()

# -------------------------
# Fetch unprocessed images
# -------------------------
async def fetch_images(disease: str, target: Optional[str], status: str = "unprocessed"):
    return await afetch_rows(LiteratureImagesAnalysis, disease, target, status)

# -------------------------
# Analyze each image
# -------------------------
async def analyse_images(images_data: List[Dict]):
    for image_data in images_data:
        try:
            logger.info(f"Processing image: {image_data.get('image_caption')} from PMCID: {image_data.get('pmcid')}")
            image_analysis = await analyzer.analyze(image_data)
            logger.info(f"Generated Analysis from MedGemma")
            logger.info("Updating Database with Image Analysis")
            
        except Exception as e:
            logger.error(f"Error processing image: {image_data.get('image_caption')} from PMCID: {image_data.get('pmcid')}. Skipping. Error: {e}")
            # continue
        await update_image_analysis(image_analysis, image_data)

# -------------------------
# Update analysis to DB
# -------------------------
async def update_image_analysis(image_analysis_data: Dict, image_metadata: Dict):
    try:
        await aupdate_table_rows(LiteratureImagesAnalysis, image_analysis_data, image_metadata)
        logger.info("Updated analysis in DB.")
    except Exception as e:
        logger.error("Error updating the Image Analysis data to the DB")
        raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: str = None, status: str = "warning"):
    images = await fetch_images(disease, target, status)
    logger.info("Fetched images for analysis: %d", len(images))
    if len(images):
        logger.info("Analyzing Images")
        await analyse_images(images)

if __name__ == "__main__":
    asyncio.run(main("phenylketonuria"))
