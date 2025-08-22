import os
import sys
import asyncio
from typing import Dict, List, Optional
sys.path.append('/app/res-immunology-automation/res_immunology_automation/src/scripts/')
print("path: ", sys.path)
from literature_enhancement.analyzer.image_analyzer.analyzer_client import ImageDataModel, ImageDataAnalysisResult
from literature_enhancement.db_utils.async_utils import afetch_rows, aupdate_table_rows, check_pipeline_status, create_pipeline_status
from db.models import LiteratureImagesAnalysis
from literature_enhancement.analyzer.image_analyzer.analyzer_pipeline import ThreeStageHybridAnalysisPipeline

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def log_prefix(disease: str, target: str) -> str:
    """Generate consistent log prefix"""
    return f"[Disease: {disease}, Target: {target}]"

def get_normalized_values(disease: str, target: str) -> tuple:
    """Get normalized disease and target values with defaults"""
    return (
        disease or "no-disease",
        target or "no-target"
    )

async def should_skip_analysis(disease: str, target: str) -> bool:
    """Check if image analysis should be skipped (already completed)"""
    current_status = await check_pipeline_status(disease, target, "image-analysis")
    if current_status == "completed":
        logger.info(f"{log_prefix(disease, target)} Image analysis already completed - skipping")
        return True
    return False

async def check_prerequisites(disease: str, target: str) -> bool:
    """Check if prerequisite pipelines (extraction, segregation) are completed"""
    required_pipelines = ["extraction", "segregation"]
    
    for pipeline_type in required_pipelines:
        status = await check_pipeline_status(disease, target, pipeline_type)
        if status != "completed":
            logger.error(f"{log_prefix(disease, target)} Prerequisite pipeline '{pipeline_type}' not completed (status: {status})")
            return False
    
    logger.info(f"{log_prefix(disease, target)} All prerequisite pipelines completed")
    return True

async def fetch_images(disease: str, target: Optional[str], status: str = "extracted"):
    """Fetch images from database that need analysis"""
    return await afetch_rows(LiteratureImagesAnalysis, disease, target, status)

async def process_images_hybrid(images_data: List[ImageDataModel], disease: str, target: str):
    """
    Enhanced process images through the pipeline with GPU memory error handling
    Handles:
    - Timeout errors (continue to next record) 
    - GPU memory errors (attempt recovery and retry)
    - Critical errors (stop pipeline)
    """
    total_images = len(images_data)
    filtered = 0
    processed = 0
    genes_validated = 0
    errors = 0
    timeout_errors = 0
    gpu_memory_errors = 0
    critical_errors = 0
    
    pipeline = ThreeStageHybridAnalysisPipeline()
    prefix = log_prefix(disease, target)
    
    logger.info("=" * 50)
    logger.info("STARTING HYBRID ANALYSIS PIPELINE WITH GPU MEMORY HANDLING")
    logger.info("=" * 50)
    
    for idx, image_data in enumerate(images_data, 1):
        pmcid = image_data.get('pmcid', 'unknown')
    
        try:
            logger.info(f"\n{prefix} Processing {idx}/{total_images}: {pmcid}")
            
            # Process through the pipeline - may raise RuntimeError for critical errors
            result: ImageDataAnalysisResult = await pipeline.process_single_image(image_data)
            status = result.get('status', 'unknown')
            
            # Handle different result statuses
            if status == "filtered_openai":
                filtered += 1
                logger.info(f"{prefix} Filtered out (OpenAI): {pmcid}")
                
            elif status == "processed":
                processed += 1
                if result.get('genes', 'not mentioned') != 'not mentioned':
                    genes_validated += 1
                logger.info(f"{prefix} Success: {pmcid}")
                
            elif status in ["filter_timeout", "analysis_timeout"]:
                # Timeout errors - record continues but log the timeout
                timeout_errors += 1
                logger.warning(f"{prefix} Timeout error: {pmcid} - {status}")
                
            elif status == "gpu_memory_error":
                # GPU memory errors that were handled with recovery attempts
                gpu_memory_errors += 1
                logger.warning(f"{prefix} GPU memory error (recovery attempted): {pmcid}")
                
            elif status in ["filter_error", "analysis_error"]:
                # Critical errors that should have stopped the pipeline
                critical_errors += 1
                logger.error(f"{prefix} Critical error occurred but not raised: {pmcid} - {status}")
                # This shouldn't happen if pipeline is working correctly
                # but we'll treat it as a pipeline error
                raise RuntimeError(f"Critical error not properly handled by pipeline: {status} for {pmcid}")
                
            else:
                errors += 1
                logger.error(f"{prefix} Unknown status: {pmcid} - {status}")
            
            # Update database with result
            await update_image_analysis(result, image_data)
            
            # Delay between images - longer delay after GPU memory errors
            if idx < total_images:
                delay = 5.0 if status == "gpu_memory_error" else 2.0
                await asyncio.sleep(delay)
                
        except RuntimeError as e:
            # Critical errors that should stop the entire pipeline
            error_msg = str(e)
            
            # Check if this is a GPU memory error that couldn't be recovered
            if any(indicator in error_msg.lower() for indicator in 
                   ['gpu memory', 'cuda out of memory', 'model loading failed']):
                logger.error(f"{prefix} UNRECOVERABLE GPU MEMORY ERROR - Stopping pipeline: {pmcid}")
                critical_errors += 1
                
                # Try to get memory status for logging
                try:
                    # This would require adding a method to get memory info from the server
                    logger.error(f"{prefix} GPU memory exhausted - manual intervention required")
                except:
                    pass
            else:
                logger.error(f"{prefix} CRITICAL ERROR - Stopping pipeline: {pmcid} - {error_msg}")
                critical_errors += 1
            
            # Update database with error status for current record
            error_result = {
                "keywords": "not mentioned", 
                "insights": "not mentioned", 
                "genes": "not mentioned", 
                "drugs": "not mentioned",
                "process": "not mentioned", 
                "is_disease_pathway": False,
                "error_message": f"Pipeline stopped due to critical error: {error_msg}",
                "status": "pipeline_stopped"
            }
            
            try:
                await update_image_analysis(error_result, image_data)
            except Exception as db_error:
                logger.error(f"{prefix} Failed to update database with error status: {str(db_error)}")
            
            # Re-raise to stop the entire pipeline
            raise RuntimeError(f"Pipeline stopped due to critical error at record {pmcid}: {error_msg}") from e
            
        except Exception as e:
            # Unexpected errors - also stop the pipeline for safety
            logger.error(f"{prefix} UNEXPECTED ERROR - Stopping pipeline: {pmcid} - {str(e)}")
            critical_errors += 1
            
            # Update database with error status
            error_result = {
                "keywords": "not mentioned", 
                "insights": "not mentioned", 
                "genes": "not mentioned", 
                "drugs": "not mentioned",
                "process": "not mentioned", 
                "is_disease_pathway": False,
                "error_message": f"Pipeline stopped due to unexpected error: {str(e)}",
                "status": "pipeline_stopped"
            }
            
            try:
                await update_image_analysis(error_result, image_data)
            except Exception as db_error:
                logger.error(f"{prefix} Failed to update database with error status: {str(db_error)}")
            
            # Raise as RuntimeError to indicate pipeline should stop
            raise RuntimeError(f"Pipeline stopped due to unexpected error at record {pmcid}: {str(e)}") from e
    
    # Summary - only reached if no critical errors occurred
    logger.info("\n" + "=" * 50)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total: {total_images}")
    logger.info(f"Filtered: {filtered}")
    logger.info(f"Processed: {processed}")
    logger.info(f"Genes validated: {genes_validated}")
    logger.info(f"Timeout errors: {timeout_errors}")
    logger.info(f"GPU memory errors: {gpu_memory_errors}")
    logger.info(f"Other errors: {errors}")
    logger.info(f"Critical errors: {critical_errors}")
    logger.info("=" * 50)

async def update_image_analysis(image_analysis_data: ImageDataAnalysisResult, image_metadata: ImageDataModel):
    """
    Update the analysis results in the database
    Enhanced with better error handling for database operations
    """
    try:
        # Clean up error_message field for successful processed records
        if image_analysis_data.get('status') == 'processed' and not image_analysis_data.get('error_message'):
            image_analysis_data['error_message'] = None

        await aupdate_table_rows(LiteratureImagesAnalysis, image_analysis_data, image_metadata)
        
    except Exception as e:
        logger.error(f"Error updating database for PMCID {image_metadata.get('pmcid', 'unknown')}: {str(e)}")
        # Re-raise database errors as they might indicate bigger issues
        raise RuntimeError(f"Database update failed: {str(e)}") from e

async def check_medgemma_server_health():
    """
    Check if MedGemma server is responsive and has available memory
    Returns tuple: (is_healthy, error_message)
    """
    try:
        import httpx
        
        username = os.getenv('username')
        password = os.getenv('password')
        
        if not username or not password:
            return False, "LDAP credentials not found"
        
        base_url = "https://medgemma-server.own4.aganitha.ai:8443"
        auth = httpx.BasicAuth(username, password)
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:  # Short timeout for health check
            response = await client.get(f"{base_url}/health", auth=auth)
            response.raise_for_status()
            result = response.json()
            
            # Check memory status
            memory_info = result.get("memory_info", {})
            if memory_info:
                allocated = memory_info.get("allocated_gb", 0)
                reserved = memory_info.get("reserved_gb", 0)
                total_used = allocated + reserved
                
                logger.info(f"GPU Memory Status - Allocated: {allocated}GB, Reserved: {reserved}GB, Total Used: {total_used}GB")
                
                # If GPU memory is very high (>22GB), it might be problematic
                if total_used > 22:
                    return False, f"GPU memory critically high: {total_used}GB used"
            
            return True, "Server healthy"
            
    except httpx.TimeoutException:
        return False, "Server not responding (timeout)"
    except httpx.HTTPStatusError as e:
        return False, f"Server returned HTTP {e.response.status_code}"
    except Exception as e:
        return False, f"Server check failed: {str(e)}"
    """
    Preload the MedGemma model before starting processing
    This helps avoid initial GPU memory allocation issues
    """
    try:
        import httpx
        
        # Get credentials from environment
        username = os.getenv('username')
        password = os.getenv('password')
        
        if not username or not password:
            logger.warning("LDAP credentials not found - skipping model preload")
            return False
        
        base_url = "https://medgemma-server.own4.aganitha.ai:8443"
        auth = httpx.BasicAuth(username, password)
        
        logger.info("Preloading MedGemma model before processing...")
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            response = await client.post(f"{base_url}/preload", auth=auth)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                logger.info("MedGemma model preloaded successfully")
                memory_info = result.get("memory_info", {})
                if memory_info:
                    logger.info(f"GPU Memory Status: {memory_info}")
                return True
            else:
                logger.error(f"Model preload failed: {result}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to preload MedGemma model: {str(e)}")
        return False

async def main(disease: str, target: str = None, record_status: str = "extracted"):
    """
    Enhanced main function with GPU memory management
    - Preloads model before processing to avoid initial allocation issues
    - Properly handles both timeout errors (continue) and critical errors (stop pipeline)
    - Only creates pipeline status record if successful
    """
    # Normalize inputs
    disease, target = get_normalized_values(disease, target)
    prefix = log_prefix(disease, target)
    
    logger.info(f"{prefix} Starting hybrid analysis pipeline with GPU memory management")
    
    try:
        # FIRST: Check if pipeline is already completed - skip if yes
        if await should_skip_analysis(disease, target):
            return True

        # SECOND: Check MedGemma server health before proceeding
        logger.info(f"{prefix} Checking MedGemma server health...")
        is_healthy, health_message = await check_medgemma_server_health()
        if not is_healthy:
            logger.error(f"{prefix} MedGemma server is not healthy: {health_message}")
            if "timeout" in health_message.lower() or "memory" in health_message.lower():
                raise RuntimeError(f"MedGemma server is not ready for processing: {health_message}")
            else:
                logger.warning(f"{prefix} Server health check failed but continuing: {health_message}")

        # THIRD: Preload MedGemma model to avoid initial memory allocation issues
        logger.info(f"{prefix} Preloading MedGemma model...")
        preload_success = await preload_medgemma_model()
        if not preload_success:
            logger.error(f"{prefix} Model preload failed - this may cause processing issues")
            # Do a final health check after preload failure
            is_healthy, health_message = await check_medgemma_server_health()
            if not is_healthy:
                raise RuntimeError(f"MedGemma server not ready after preload failure: {health_message}")

        # # FOURTH: Check prerequisites (extraction and segregation must be completed)
        # if not await check_prerequisites(disease, target):
        #     raise RuntimeError("Prerequisites not met - extraction and segregation must be completed first")
        
        # FOURTH: Perform Image Analysis
        logger.info(f"{prefix} Performing Image Analysis...")
        
        # Fetch images that need processing
        images = await fetch_images(disease, target, record_status)
        logger.info(f"{prefix} Found {len(images)} images to process")
        
        if images:
            # Process images through the hybrid pipeline
            # This may raise RuntimeError for critical errors
            await process_images_hybrid(images, disease, target)
            logger.info(f"{prefix} Pipeline completed successfully!")
        else:
            logger.info(f"{prefix} No images found to process")
        
        # ONLY create pipeline status if successful
        await create_pipeline_status(disease, target, "image-analysis", "completed")
        logger.info(f"{prefix} Pipeline status updated: completed")
        return True
        
    except RuntimeError as e:
        # Critical errors from the pipeline (API failures, etc.)
        error_message = str(e)
        logger.error(f"{prefix} Pipeline failed due to critical error: {error_message}")
        
        # Check if this is a GPU memory related failure
        if any(indicator in error_message.lower() for indicator in 
               ['gpu memory', 'cuda out of memory', 'model loading failed']):
            logger.error("\n" + "=" * 60)
            logger.error("GPU MEMORY EXHAUSTION DETECTED")
            logger.error("=" * 60)
            logger.error("Possible solutions:")
            logger.error("1. Restart the MedGemma server to clear GPU memory")
            logger.error("2. Check for other processes using GPU memory")
            logger.error("3. Reduce batch size or model parameters")
            logger.error("4. Use model with smaller memory footprint")
            logger.error("=" * 60)
        
        # Log final error summary
        logger.error("\n" + "=" * 50)
        logger.error("PIPELINE FAILED")
        logger.error("=" * 50)
        logger.error(f"Reason: {error_message}")
        logger.error("=" * 50)
        
        # DO NOT create pipeline status for failures - let retry mechanism handle it
        # Re-raise so build_dossier can handle the error
        raise RuntimeError(f"Image analysis failed for {disease}-{target}: {error_message}") from e
        
    except Exception as e:
        # Unexpected errors in main function
        error_message = f"Unexpected pipeline error: {str(e)}"
        logger.error(f"{prefix} Pipeline failed due to unexpected error: {error_message}")
        
        # DO NOT create pipeline status for failures
        # Re-raise so build_dossier can handle the error
        raise RuntimeError(f"Image analysis failed for {disease}-{target}: {error_message}") from e

if __name__ == "__main__":
    try:
        asyncio.run(main("phenylketonuria"))
    except RuntimeError as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)  # Exit with error code
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {str(e)}")
        sys.exit(1)