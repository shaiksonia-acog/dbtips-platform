
from literature_enhancement.analyzer.image_analyzer.image_analyzer import main as image_analyzer_main
from literature_enhancement.analyzer.supplementary_analyzer.supplementary_analyzer import main as supplementary_analyzer_main
from literature_enhancement.analyzer.table_analyzer.table_analyzer import main as table_analyzer_main
from typing import Optional, List
from literature_enhancement.db_utils.async_utils import check_pipeline_status
import logging
import asyncio
import os
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)


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
            logger.info(f"{pipeline_type.upper()} already completed - SKIPPING")
        
    elif status == "terminate":
        logger.info(f"Previous stages for {pipeline_type.upper()} not completed - TERMINATING")
        raise Exception(f"Previous stages for {pipeline_type.upper()} not completed - TERMINATING")

# async def run_analyzers(disease: str, target: str = "no-target", pipeline_status: str = "completed"):
#     try:

#         pipelines_details = {
#             "image-analysis": image_analyzer_main,
#             "table-analysis": table_analyzer_main,
#             "supplementary-data-analysis": supplementary_analyzer_main
#         }
#         """Run all analyzers sequentially"""
#         # for pipeline_type, pipeline_runner in pipelines_details.items():
#         #     if pipeline_type == "supplementary-analysis":
#         #         await check_status_and_run(disease, target, pipeline_type, pipeline_runner, pipeline_status)
#         #         break

#         tasks = [
#             check_status_and_run(disease, target, pipeline_type, pipeline_runner, pipeline_status)
#             for pipeline_type, pipeline_runner in pipelines_details.items()
#         ]
#         # Run them in parallel
#         results = await asyncio.gather(*tasks, return_exceptions=True)

#         successful_results = []
#         failed_pipelines = []
        
#         for i, result in enumerate(results):
#             pipeline_type = list(pipelines_details.keys())[i]
            
#             if isinstance(result, Exception):
#                 logging.error(f"Pipeline '{pipeline_type}' failed: {str(result)}")
#                 failed_pipelines.append((pipeline_type, result))
#             else:
#                 successful_results.append((pipeline_type, result))
#                 logging.info(f"Pipeline '{pipeline_type}' completed successfully")

#         # Log summary
#         logging.info(f"Completed {len(successful_results)}/{len(pipelines_details)} pipelines successfully")
        
#         if failed_pipelines:
#             logging.warning(f"Failed pipelines: {[name for name, _ in failed_pipelines]}")
#             # Optionally re-raise the first exception or handle differently based on requirements
#             raise failed_pipelines[0][1]
        
#         return {
#             "successful": successful_results,
#             "failed": failed_pipelines,
#             "total_pipelines": len(pipelines_details)
#         }

#     except Exception as e:
#         logging.error(f"Critical error in run_analyzers: {str(e)}")
#         raise


# if __name__ == "__main__":
#     disease = "phenylketonuria"
#     target = "no-target"
#     asyncio.run(run_analyzers(disease, target))

async def run_analyzers(disease: str, target: str = "no-target", pipeline_status: str = "completed"):
    try:
        pipelines_details = {
            "image-analysis": image_analyzer_main,
            "table-analysis": table_analyzer_main,
            "supplementary-data-analysis": supplementary_analyzer_main
        }
        
        logger.info(f"Starting analysis pipelines for disease: {disease}, target: {target}")
        
        # Create tasks for all pipelines
        tasks = [
            check_status_and_run(disease, target, pipeline_type, pipeline_runner, pipeline_status)
            for pipeline_type, pipeline_runner in pipelines_details.items()
        ]
        
        # Run them in parallel and wait for all to complete (even if some fail)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_results = []
        failed_pipelines = []
        
        # Process results
        for i, result in enumerate(results):
            pipeline_type = list(pipelines_details.keys())[i]
            
            if isinstance(result, Exception):
                logger.error(f"Pipeline '{pipeline_type}' failed: {str(result)}")
                failed_pipelines.append((pipeline_type, result))
            else:
                successful_results.append((pipeline_type, result))
                logger.info(f"Pipeline '{pipeline_type}' completed successfully")

        # Log summary
        logger.info(f"Pipeline execution summary:")
        logger.info(f"  - Successful: {len(successful_results)}/{len(pipelines_details)} pipelines")
        logger.info(f"  - Failed: {len(failed_pipelines)}/{len(pipelines_details)} pipelines")
        
        if failed_pipelines:
            logger.warning(f"Failed pipelines: {[name for name, _ in failed_pipelines]}")
            
            # Prepare detailed error message
            failed_count = len(failed_pipelines)
            total_count = len(pipelines_details)
            
            error_details = []
            for analyzer_name, error in failed_pipelines:
                error_details.append(f"  - {analyzer_name}: {str(error)}")
                logger.error(f"  - {analyzer_name}: {str(error)}")
            
            error_msg = (f"Analysis pipeline failed: {failed_count}/{total_count} analyzers failed.\n"
                        f"Failed analyzers:\n" + "\n".join(error_details))
            
            raise Exception(error_msg)
        
        logger.info("All analyzers completed successfully")
        return {
            "successful": successful_results,
            "failed": failed_pipelines,
            "total_pipelines": len(pipelines_details),
            "success_rate": 1.0
        }

    except Exception as e:
        logger.error(f"Critical error in run_analyzers: {str(e)}")
        # Re-raise the exception instead of returning error info
        raise