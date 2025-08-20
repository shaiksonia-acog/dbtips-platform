
import asyncio
from typing import Dict
from literature_enhancement.analyzer.image_analyzer.openai_filter_client import OpenAIPathwayFilter
from literature_enhancement.analyzer.image_analyzer.analyzer_client import MedGemmaAnalyzer, ImageDataModel, ImageDataAnalysisResult
from literature_enhancement.analyzer.image_analyzer.gene_validator import validate_genes_async
import logging
import os
module_name = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(module_name)

class ThreeStageHybridAnalysisPipeline:
    """
    Three-stage hybrid analysis pipeline:
    Stage 1: OpenAI GPT-4o-mini caption filtering
    Stage 2: MedGemma content analysis 
    Stage 3: Gene validation with NCBI
    """
    
    def __init__(self):
        self.openai_filter = OpenAIPathwayFilter()
        self.medgemma_analyzer = MedGemmaAnalyzer()
    
    async def process_single_image(self, image_data: ImageDataModel) -> Dict:
        """Process a single image through the three-stage pipeline"""
        pmcid = image_data.get("pmcid")
        caption = image_data.get("image_caption")
        
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