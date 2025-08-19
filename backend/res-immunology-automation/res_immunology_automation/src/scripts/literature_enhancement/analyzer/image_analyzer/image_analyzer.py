import os
import sys
import asyncio
from typing import Dict, List, Optional, Any

sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows
from openai_filter_client import OpenAIPathwayFilter
from analyzer_client import MedGemmaAnalyzer
from db.models import LiteratureImagesAnalysis
from gene_validator import validate_genes_async

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TwoStageHybridAnalysisPipeline:
    """
    Three-stage hybrid analysis pipeline:
    Stage 1: OpenAI GPT-4o-mini caption filtering
    Stage 2: MedGemma content analysis 
    Stage 3: Gene validation with NCBI
    """
    
    def __init__(self):
        self.openai_filter = OpenAIPathwayFilter()
        self.medgemma_analyzer = MedGemmaAnalyzer()
    
    async def process_single_image(self, image_data: Dict) -> Dict:
        """Process a single image through the three-stage pipeline"""
        pmcid = image_data.get('pmcid', 'unknown')
        caption = image_data.get('image_caption', '')
        
        logger.info(f"Starting analysis for PMCID: {pmcid}")
        
        # STAGE 1: OpenAI filtering
        try:
            filter_result = self.openai_filter.filter_caption(caption)
            
            if filter_result.get("status") == "filter_error":
                return {
                    "keywords": "not mentioned", "insights": "not mentioned", 
                    "genes": "not mentioned", "drugs": "not mentioned",
                    "process": "not mentioned", "is_disease_pathway": False,
                    "error_message": f"OpenAI filtering failed: {filter_result.get('error_message')}",
                    "status": "filter_error"
                }
            
            if not filter_result.get("is_disease_pathway", False):
                logger.info(f"🚫 Filtered out: {pmcid}")
                return {
                    "keywords": "not mentioned", "insights": "not mentioned",
                    "genes": "not mentioned", "drugs": "not mentioned", 
                    "process": "not mentioned", "is_disease_pathway": False,
                    "error_message": "Not disease pathway relevant",
                    "status": "filtered_openai"
                }
            
            logger.info(f"✅ Stage 1 passed: {pmcid}")
            
        except Exception as e:
            logger.error(f"❌ Stage 1 error: {pmcid} - {str(e)}")
            return {
                "keywords": "not mentioned", "insights": "not mentioned",
                "genes": "not mentioned", "drugs": "not mentioned",
                "process": "not mentioned", "is_disease_pathway": False,
                "error_message": f"Stage 1 exception: {str(e)}",
                "status": "filter_error"
            }
        
        # STAGE 2: MedGemma analysis
        try:
            logger.info(f"🔬 Stage 2 analyzing: {pmcid}")
            analysis_result = await self.medgemma_analyzer.analyze_content(image_data)
            analysis_result["is_disease_pathway"] = True
            
            if analysis_result.get("status") == "analyzed":
                analysis_result["status"] = "processed"
                analysis_result["error_message"] = None
                logger.info(f"✅ Stage 2 completed: {pmcid}")
            else:
                logger.warning(f"⚠️ Stage 2 partial: {pmcid}")
            
            # STAGE 3: Gene validation (integrated directly)
            genes_text = analysis_result.get("genes", "not mentioned")
            if genes_text and genes_text.lower() != "not mentioned":
                logger.info(f"🧬 Stage 3 validating genes: {pmcid}")
                try:
                    validated_genes = await validate_genes_async(genes_text, delay=1.5)
                    analysis_result["genes"] = validated_genes
                    logger.info(f"✅ genes validated: {pmcid} -> {validated_genes}")
                except Exception as e:
                    logger.error(f"❌ Gene validation failed: {pmcid} - {str(e)}")
                    # Keep original genes if validation fails
            else:
                logger.info(f"🧬 Stage 3 skipped - no genes: {pmcid}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Stage 2 error: {pmcid} - {str(e)}")
            return {
                "keywords": "not mentioned", "insights": "not mentioned",
                "genes": "not mentioned", "drugs": "not mentioned",
                "process": "not mentioned", "is_disease_pathway": True,
                "error_message": f"Stage 2 analysis exception: {str(e)}",
                "status": "analysis_error"
            }

async def fetch_images(disease: str, target: Optional[str], status: str = "extracted"):
    """Fetch images from database that need analysis"""
    return await afetch_rows(LiteratureImagesAnalysis, disease, target, status)

async def process_images_hybrid(images_data: List[Dict]):
    """Process images through the pipeline"""
    total_images = len(images_data)
    filtered = 0
    processed = 0
    genes_validated = 0
    errors = 0
    
    pipeline = TwoStageHybridAnalysisPipeline()
    
    logger.info("=" * 50)
    logger.info("STARTING HYBRID ANALYSIS PIPELINE")
    logger.info("=" * 50)
    
    for idx, image_data in enumerate(images_data, 1):
        pmcid = image_data.get('pmcid', 'unknown')
        
        try:
            logger.info(f"\n📊 Processing {idx}/{total_images}: {pmcid}")
            
            result = await pipeline.process_single_image(image_data)
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

async def update_image_analysis(image_analysis_data: Dict, image_metadata: Dict):
    """Update the analysis results in the database"""
    try:
        if image_analysis_data.get('status') == 'processed' and not image_analysis_data.get('error_message'):
            image_analysis_data['error_message'] = None
        
        await aupdate_table_rows(LiteratureImagesAnalysis, image_analysis_data, image_metadata)
        
    except Exception as e:
        logger.error(f"Error updating DB: {str(e)}")
        raise e

async def main(disease: str, target: str = None, status: str = "extracted"):
    """Main function - does everything in one go"""
    logger.info(f"Starting pipeline for disease: {disease}")
    if target:
        logger.info(f"Target: {target}")
    
    try:
        images = await fetch_images(disease, target, status)
        logger.info(f"Found {len(images)} images")
        
        if images:
            await process_images_hybrid(images)
            logger.info("🏁 Pipeline completed!")
        else:
            logger.info("No images found")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise e

if __name__ == "__main__":
    asyncio.run(main("asthma"))