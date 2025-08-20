import sys
sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
from image_analyzer.image_analyzer import main as image_analyzer_main
from supplementary_analyzer.supplementary_analyzer import main as supplementary_analyzer_main
from table_analyzer.table_analyzer import main as table_analyzer_main
from typing import Optional, List
from literature_enhancement.db_utils.async_utils import check_pipeline_status
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def fetch_pipeline_status(disease: str, target: Optional[str], status: str, current_pipeline:str)->str:
    """Check if the pipeline status is completed for given disease and target"""
    pipeline_types = ["extraction", "segregation"]
    pipeline_types.append(current_pipeline)
    for pipeline_type in pipeline_types:
        status = await check_pipeline_status(disease, target, pipeline_type)
        if status is None:
            if pipeline_type != current_pipeline:
                return "terminate"
            else:
                return "proceed"
        if status == "completed" and pipeline_type == "analysis":
            return "skip"

async def check_status_and_run(disease: str, target: str, 
        pipeline_type:str, analysis_pipeline_runner: callable ,
        pipeline_status: str = "completed"):
    """Check pipeline status and run analyzers if appropriate"""
    
    status = await fetch_pipeline_status(disease, target, pipeline_status, pipeline_type)
    if status == "proceed":
        await analysis_pipeline_runner(disease, target)
    
    elif status == "skip":
            logger.info(f"{pipeline_type} already completed - SKIPPING")
        
    elif status == "terminate":
        logger.info(f"Previous stages for {pipeline_type} not completed - TERMINATING")
        raise Exception(f"Previous stages for {pipeline_type} not completed - TERMINATING")

async def run_analyzers(disease: str, target: str = "no-target", pipeline_status: str = "completed"):
    pipelines_details = {
        "image-analysis": image_analyzer_main,
        "table-analysis": table_analyzer_main,
        "supplementary-analysis": supplementary_analyzer_main
    }
    """Run all analyzers sequentially"""
    for pipeline_type, pipeline_runner in pipelines_details.items():
        if pipeline_type == "table-analysis":
            await check_status_and_run(disease, target, pipeline_type, pipeline_runner, pipeline_status)
            break

if __name__ == "__main__":
    import asyncio
    disease = "phenylketonuria"
    target = "no-target"
    asyncio.run(run_analyzers(disease, target))