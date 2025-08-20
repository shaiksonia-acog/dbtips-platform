import os
import sys
import asyncio
from typing import Dict, List, Optional
from literature_enhancement.analyzer.image_analyzer.analyzer_client import ImageDataModel, ImageDataAnalysisResult
from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows, check_pipeline_status, create_pipeline_status
from db.models import LiteratureImagesAnalysis
from literature_enhancement.analyzer.image_analyzer.analyzer_pipeline import ThreeStageHybridAnalysisPipeline

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def fetch_images(disease: str, target: Optional[str], status: str = "extracted"):
    """Fetch images from database that need analysis"""
    return await afetch_rows(LiteratureImagesAnalysis, disease, target, status)

async def process_images_hybrid(images_data: List[ImageDataModel]):
    """Process images through the pipeline"""
    total_images = len(images_data)
    filtered = 0
    processed = 0
    genes_validated = 0
    errors = 0
    
    pipeline = ThreeStageHybridAnalysisPipeline()
    
    logger.info("=" * 50)
    logger.info("STARTING HYBRID ANALYSIS PIPELINE")
    logger.info("=" * 50)
    
    for idx, image_data in enumerate(images_data, 1):
        pmcid = image_data.get('pmcid', 'unknown')
    
        try:
            logger.info(f"\n📊 Processing {idx}/{total_images}: {pmcid}")
            
            result: ImageDataAnalysisResult = await pipeline.process_single_image(image_data)
            status = result.get('status', 'unknown')
            if status == "filtered_openai":
                filtered += 1
            elif status == "processed":
                processed += 1
                if result.get('genes', 'not mentioned') != 'not mentioned':
                    genes_validated += 1
                logger.info(f"🎉 Success: {pmcid}")
            else:
                errors += 1
                logger.error(f"❌ Error: {pmcid} - {status}")
            
            # Update database
            await update_image_analysis(result, image_data)
            
            # Delay between images
            if idx < total_images:
                await asyncio.sleep(2.0)
                
        except Exception as e:
            logger.error(f"❌ Exception: {pmcid} - {str(e)}")
            errors += 1
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total: {total_images}")
    logger.info(f"Filtered: {filtered}")
    logger.info(f"Processed: {processed}")
    logger.info(f"genes validated: {genes_validated}")
    logger.info(f"Errors: {errors}")
    logger.info("=" * 50)

async def update_image_analysis(image_analysis_data: ImageDataAnalysisResult, image_metadata: ImageDataModel):
    """Update the analysis results in the database"""
    try:
        if image_analysis_data.get('status') == 'processed' and not image_analysis_data.get('error_message'):
            image_analysis_data['error_message'] = None

        await aupdate_table_rows(LiteratureImagesAnalysis, image_analysis_data, image_metadata)
        
    except Exception as e:
        logger.error(f"Error updating DB: {str(e)}")
        raise e

async def main(disease: str, target: str = None, record_status: str = "extracted"):
    """Main function - does everything in one go"""
    logger.info(f"Starting pipeline for disease: {disease}")
    if target:
        logger.info(f"Target: {target}")
    
    try:
        # Check pipeline status
       
        logger.info("✅ Performing Image Analysis..")
        images = await fetch_images(disease, target, record_status)
        logger.info(f"Found {len(images)} images")
        
        if images:
            await process_images_hybrid(images)
            logger.info("🏁 Pipeline completed!")
        else:
            logger.info("No images found")
        await create_pipeline_status(disease, target, "image-analysis", "completed")

        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise e

if __name__ == "__main__":
    asyncio.run(main("asthma"))