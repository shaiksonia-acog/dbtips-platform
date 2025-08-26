import os
import sys
sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
from literature_enhancement.analyzer.literature_analyzer import run_analyzers
from literature_enhancement.data_segregation.literature_segregation import run_literature_segregation
from literature_enhancement.literature_extractor.literature_extractor import extract_literature
import logging
import asyncio

from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)

# async def run_enhancement_pipeline(disease: str = "no-disease", target: str = "no-target"):
#     logger.info(f"Starting enhancement pipeline for disease: {disease}, target: {target}")
#     try:
#         await extract_literature(disease, target)
#         await run_literature_segregation(disease, target)
#         await run_analyzers(disease, target)
#     except Exception as e:
#         logger.error(f"Error occurred during enhancement pipeline: {e}")
#         raise e

# 
async def run_enhancement_pipeline(disease: str = "no-disease", target: str = "no-target"):
    logger.info(f"Starting enhancement pipeline for disease: {disease}, target: {target}")
    try:
        # Run extraction
        await extract_literature(disease, target)
        logger.info("Literature extraction completed successfully")
        
        # Run segregation
        await run_literature_segregation(disease, target)
        logger.info("Literature segregation completed successfully")
        
        # Run analyzers (will raise exception if any analyzer fails)
        analyzer_results = await run_analyzers(disease, target)
        logger.info("All analyzers completed successfully")
        
        logger.info("Enhancement pipeline completed successfully")
        return analyzer_results
        
    except Exception as e:
        logger.error(f"Error occurred during enhancement pipeline: {e}")
        raise e

if __name__ == "__main__":
    disease = "asthma"
    try:
        asyncio.run(run_enhancement_pipeline(disease))
    except Exception as e:
        logger.critical(f"Enhancement pipeline failed: {e}")