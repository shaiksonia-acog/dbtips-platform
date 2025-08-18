import os
import sys
import asyncio
from typing import Dict, List, Optional, Any

sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)

from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows
from openai_filter_client import OpenAIPathwayFilter  # New OpenAI filter
from analyzer_client import MedGemmaAnalyzer  # Original MedGemma analyzer unchanged
from db.models import LiteratureImagesAnalysis

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Caption inclusion keywords for stage 1 filtering
CAPTION_INCLUSION_KEYWORDS = [
    "metabolism", "anabolism", "catabolism", "catalysis", "catalyse", "synthesis", 
    "biosynthesis", "pathway", "pathophysiology", "mechanism of action", "moa", 
    "gene regulatory network", "signal transduction", "cascade", "axis", "target", 
    "interaction", "inhibitor", "inhibits", "modulates", "modulator", "activator", 
    "activates", "antagonist", "agonist", "pharmacodynamics", "disease mechanism", 
    "pathogenesis", "etiology", "dysregulation", "immune response", "signaling", 
    "signalling", "overview", "schematic representation", "mechanism", "network",
    "regulation", "regulatory", "biochemical", "molecular", "cellular", "enzymatic",
    "metabolic", "therapeutic", "treatment", "drug action", "pharmacology", "kinetics",
    "dynamics", "binding", "receptor", "ligand", "protein", "enzyme", "substrate"
]

class TwoStageHybridAnalysisPipeline:
    """
    Two-stage hybrid analysis pipeline:
    Stage 1: Caption keyword filtering
    Stage 2: OpenAI GPT-4o-mini visual filtering (disease pathway identification)
    Stage 3: MedGemma content analysis (unchanged - only for images that pass both filters)
    """
    
    def __init__(self):
        self.openai_filter = OpenAIPathwayFilter()  # New OpenAI filter
        self.medgemma_analyzer = MedGemmaAnalyzer()  # Original MedGemma analyzer
    
    def _contains_caption_keywords(self, caption: str) -> bool:
        """Stage 1: Caption keyword filtering"""
        if not caption:
            return False
            
        caption_lower = caption.lower()
        return any(keyword.lower() in caption_lower for keyword in CAPTION_INCLUSION_KEYWORDS)
    
    async def process_single_image(self, image_data: Dict) -> Dict:
        """
        Process a single image through the two-stage hybrid pipeline
        
        Args:
            image_data: Dictionary containing image information
            
        Returns:
            Dictionary with final analysis results
        """
        pmcid = image_data.get('pmcid', 'unknown')
        caption = image_data.get('image_caption', '')
        
        logger.info(f"Starting two-stage hybrid analysis for PMCID: {pmcid}")
        
        # STAGE 1: Caption keyword filtering
        if not self._contains_caption_keywords(caption):
            logger.info(f"🔍 Stage 1 FILTERED (caption keywords): PMCID {pmcid}")
            return {
                "keywords": "not mentioned",
                "insights": "not mentioned", 
                "Genes": "not mentioned",
                "drugs": "not mentioned",
                "process": "not mentioned",
                "is_disease_pathway": False,
                "error_message": "Stage 1: Caption doesn't contain pathway keywords",
                "status": "filtered_caption"
            }
        
        logger.info(f"✅ Stage 1 PASSED (caption keywords): PMCID {pmcid}")
        
        # STAGE 2: OpenAI GPT-4o-mini visual filtering (now synchronous)
        try:
            filter_result = self.openai_filter.filter_image(
                image_data["image_url"], 
                caption
            )
            
            if filter_result.get("status") == "filter_error":
                logger.warning(f"⚠️ Stage 2 ERROR (OpenAI filtering): PMCID {pmcid}")
                return {
                    "keywords": "not mentioned",
                    "insights": "not mentioned", 
                    "Genes": "not mentioned",
                    "drugs": "not mentioned",
                    "process": "not mentioned",
                    "is_disease_pathway": False,
                    "error_message": f"Stage 2: {filter_result.get('error_message', 'OpenAI filtering failed')}",
                    "status": "filter_error"
                }
            
            is_pathway = filter_result.get("is_disease_pathway", False)
            confidence = filter_result.get("confidence", "unknown")
            
            if not is_pathway:
                logger.info(f"🚫 Stage 2 FILTERED (OpenAI - {confidence} confidence): PMCID {pmcid}")
                return {
                    "keywords": "not mentioned",
                    "insights": "not mentioned", 
                    "Genes": "not mentioned",
                    "drugs": "not mentioned",
                    "process": "not mentioned",
                    "is_disease_pathway": False,
                    "error_message": f"Stage 2: OpenAI determined not disease pathway relevant ({confidence} confidence)",
                    "status": "filtered_openai"
                }
            
            logger.info(f"✅ Stage 2 PASSED (OpenAI - {confidence} confidence): PMCID {pmcid}")
            
        except Exception as e:
            logger.error(f"❌ Stage 2 EXCEPTION (OpenAI): PMCID {pmcid} - {str(e)}")
            return {
                "keywords": "not mentioned",
                "insights": "not mentioned", 
                "Genes": "not mentioned",
                "drugs": "not mentioned",
                "process": "not mentioned",
                "is_disease_pathway": False,
                "error_message": f"Stage 2 exception: {str(e)}",
                "status": "filter_error"
            }
        
        # STAGE 3: MedGemma content analysis (original analyzer unchanged)
        try:
            logger.info(f"🔬 Stage 3 ANALYZING (MedGemma): PMCID {pmcid}")
            analysis_result = await self.medgemma_analyzer.analyze_content(image_data)
            
            # Add pathway information from filtering stage
            analysis_result["is_disease_pathway"] = True  # Confirmed by OpenAI filter
            
            # Update status based on analysis success
            if analysis_result.get("status") == "analyzed":
                analysis_result["status"] = "processed"  # Final successful status
                analysis_result["error_message"] = None  # Clear any previous error messages
                logger.info(f"✅ Stage 3 COMPLETED (MedGemma): PMCID {pmcid}")
            else:
                logger.warning(f"⚠️ Stage 3 PARTIAL (MedGemma issues): PMCID {pmcid}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Stage 3 EXCEPTION (MedGemma): PMCID {pmcid} - {str(e)}")
            return {
                "keywords": "not mentioned",
                "insights": "not mentioned", 
                "Genes": "not mentioned",
                "drugs": "not mentioned",
                "process": "not mentioned",
                "is_disease_pathway": True,  # Passed OpenAI filter but analysis failed
                "error_message": f"Stage 3 analysis exception: {str(e)}",
                "status": "analysis_error"
            }

# -------------------------
# Main pipeline functions
# -------------------------
async def fetch_images(disease: str, target: Optional[str], status: str = "extracted"):
    """Fetch images from database that need analysis"""
    return await afetch_rows(LiteratureImagesAnalysis, disease, target, status)

async def process_images_hybrid(images_data: List[Dict]):
    """Process images through the two-stage hybrid pipeline (OpenAI filter + MedGemma analyzer)"""
    total_images = len(images_data)
    stage1_filtered = 0  # Caption keyword filtering
    stage2_filtered = 0  # OpenAI filtering  
    stage3_processed = 0  # Successfully analyzed by MedGemma
    errors = 0
    
    pipeline = TwoStageHybridAnalysisPipeline()
    
    logger.info("=" * 70)
    logger.info("TWO-STAGE HYBRID ANALYSIS PIPELINE STARTING")
    logger.info("Stage 1: Caption keyword filtering")
    logger.info("Stage 2: OpenAI GPT-4o-mini visual pathway filtering")
    logger.info("Stage 3: MedGemma content analysis (unchanged)")
    logger.info("=" * 70)
    
    for idx, image_data in enumerate(images_data, 1):
        pmcid = image_data.get('pmcid', 'unknown')
        
        try:
            logger.info(f"\n📊 Processing {idx}/{total_images}: PMCID {pmcid}")
            logger.debug(f"Image URL: {image_data.get('image_url', 'No URL')[:100]}...")
            logger.debug(f"Caption: {image_data.get('image_caption', 'No caption')[:100]}...")
            
            # Run through two-stage pipeline
            result = await pipeline.process_single_image(image_data)
            
            # Categorize results with detailed logging
            status = result.get('status', 'unknown')
            error_msg = result.get('error_message', '')
            
            if status == "filtered_caption":
                stage1_filtered += 1
                logger.debug(f"🔍 Stage 1 filtered: {pmcid}")
            elif status == "filtered_openai":
                stage2_filtered += 1
                logger.info(f"🚫 Stage 2 filtered: {pmcid} - {result.get('reasoning', 'No reasoning')}")
            elif status == "processed":
                stage3_processed += 1
                logger.info(f"🎉 SUCCESS: {pmcid} - Keywords: {result.get('keywords', 'not mentioned')[:50]}...")
            elif status in ["filter_error", "analysis_error"]:
                errors += 1
                logger.error(f"❌ ERROR: {pmcid} - Status: {status} - {error_msg}")
                
                # Log more details for debugging
                if "OpenAI" in error_msg or "filter" in status:
                    logger.error(f"OpenAI filtering error details for {pmcid}: {error_msg}")
                elif "analysis" in status:
                    logger.error(f"MedGemma analysis error details for {pmcid}: {error_msg}")
            else:
                logger.warning(f"⚠️ Unknown status '{status}': {pmcid} - {error_msg}")
                errors += 1
            
            # Update database
            await update_image_analysis(result, image_data)
            logger.debug(f"✅ Database updated for PMCID {pmcid}")
            
            # Delay to avoid overwhelming APIs
            if idx < total_images:
                await asyncio.sleep(2.0)  # 2 seconds delay
                
        except Exception as e:
            logger.error(f"❌ Exception processing PMCID {pmcid}: {str(e)}")
            errors += 1
            
            # Create error analysis data
            error_result = {
                "keywords": "not mentioned",
                "insights": "not mentioned", 
                "Genes": "not mentioned",
                "drugs": "not mentioned",
                "process": "not mentioned",
                "is_disease_pathway": None,  # None for error cases
                "error_message": f"Processing exception: {str(e)}",
                "status": "error"
            }
            
            try:
                await update_image_analysis(error_result, image_data)
            except Exception as db_error:
                logger.error(f"❌ Database update failed for PMCID {pmcid}: {str(db_error)}")
    
    # Summary statistics
    logger.info("\n" + "=" * 70)
    logger.info("TWO-STAGE HYBRID ANALYSIS PIPELINE SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total images processed: {total_images}")
    logger.info(f"🔍 Stage 1 filtered (caption keywords): {stage1_filtered}")
    logger.info(f"🚫 Stage 2 filtered (OpenAI): {stage2_filtered}")
    logger.info(f"✅ Stage 3 processed (MedGemma): {stage3_processed}")
    logger.info(f"❌ Errors: {errors}")
    logger.info(f"Overall pipeline success rate: {(stage3_processed/total_images)*100:.1f}%")
    logger.info(f"Filter efficiency: {((stage1_filtered + stage2_filtered)/total_images)*100:.1f}% filtered out")
    logger.info("=" * 70)

async def update_image_analysis(image_analysis_data: Dict, image_metadata: Dict):
    """Update the analysis results in the database"""
    try:
        # Ensure error_message is None for successfully processed records
        if image_analysis_data.get('status') == 'processed' and not image_analysis_data.get('error_message'):
            image_analysis_data['error_message'] = None
        
        await aupdate_table_rows(LiteratureImagesAnalysis, image_analysis_data, image_metadata)
        
        status = image_analysis_data.get('status', 'unknown')
        is_pathway = image_analysis_data.get('is_disease_pathway')
        logger.debug(f"Updated analysis in DB - Status: {status}, Disease pathway: {is_pathway}")
        
    except Exception as e:
        logger.error(f"Error updating analysis data to DB: {str(e)}")
        raise e

# -------------------------
# Main entrypoint
# -------------------------
async def main(disease: str, target: str = None, status: str = "extracted"):
    """Main function to run the two-stage hybrid image analysis pipeline"""
    logger.info("=" * 70)
    logger.info("TWO-STAGE HYBRID IMAGE ANALYSIS PIPELINE")
    logger.info("OpenAI GPT-4o-mini Filter + MedGemma Analyzer")
    logger.info("=" * 70)
    logger.info(f"Disease filter: {disease}")
    if target:
        logger.info(f"Target filter: {target}")
    logger.info(f"Status filter: {status}")
    logger.info("\nPipeline stages:")
    logger.info("  Stage 1: Caption keyword filtering")
    logger.info("  Stage 2: OpenAI GPT-4o-mini visual pathway filtering")
    logger.info("  Stage 3: MedGemma content extraction (unchanged)")
    logger.info("=" * 70)
    
    try:
        # Fetch images for analysis
        images = await fetch_images(disease, target, status)
        image_count = len(images)
        
        logger.info(f"Found {image_count} images for analysis")
        
        if image_count > 0:
            logger.info("🚀 STARTING TWO-STAGE HYBRID PIPELINE")
            
            await process_images_hybrid(images)
            
            logger.info("🏁 TWO-STAGE HYBRID PIPELINE COMPLETED")
        else:
            logger.info("ℹ️  No images found matching the criteria")
            
    except Exception as e:
        logger.error(f"Main process failed: {str(e)}")
        raise e

if __name__ == "__main__":
    # Run with phenylketonuria as default
    asyncio.run(main("phenylketonuria"))