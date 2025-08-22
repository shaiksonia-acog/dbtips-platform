#!/usr/bin/env python3
"""
Enhanced retry decorators for API calls with exponential backoff
Handles different error types with appropriate pipeline stopping logic
Now includes GPU memory error handling for MedGemma
"""

import asyncio
import time
import logging
import functools
from typing import Callable, Any, Optional
import httpx
import requests
import os
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)

class PipelineStopException(Exception):
    """Exception to stop the entire pipeline"""
    pass

class ContinueToNextRecordException(Exception):
    """Exception to skip current record and continue with next"""
    pass

class GPUMemoryException(Exception):
    """Exception for GPU memory related issues that require model reload"""
    pass

class ModelLoadException(Exception):
    """Exception for model loading failures that can be retried"""
    pass

def sync_api_retry(max_retries: int = 3, base_delay: float = 1.0, backoff_multiplier: float = 2.0):
    """
    Retry decorator for synchronous API calls (NCBI, OpenAI)
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        backoff_multiplier: Multiplier for exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return func(*args, **kwargs)
                    
                except requests.exceptions.Timeout as e:
                    last_exception = e
                    if attempt == max_retries:
                        # For timeout errors, we continue to next record
                        logger.error(f"API timeout after {max_retries} retries: {str(e)}")
                        raise ContinueToNextRecordException(f"API timeout after {max_retries} retries") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with timeout, retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                    
                except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, 
                        requests.exceptions.RequestException) as e:
                    last_exception = e
                    if attempt == max_retries:
                        # For other API errors, stop the pipeline
                        logger.error(f"API error after {max_retries} retries, stopping pipeline: {str(e)}")
                        raise PipelineStopException(f"API error after {max_retries} retries: {str(e)}") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                    
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries:
                        # For unexpected errors, stop the pipeline
                        logger.error(f"Unexpected error after {max_retries} retries, stopping pipeline: {str(e)}")
                        raise PipelineStopException(f"Unexpected error after {max_retries} retries: {str(e)}") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with unexpected error, retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise PipelineStopException(f"Maximum retries exceeded") from last_exception
            
        return wrapper
    return decorator

def async_api_retry(max_retries: int = 3, base_delay: float = 10.0, backoff_multiplier: float = 2.5):
    """
    Enhanced retry decorator for async API calls (MedGemma)
    Now includes special handling for GPU memory errors
    Uses longer delays for MedGemma as requested
    
    Args:
        max_retries: Maximum number of retry attempts  
        base_delay: Base delay in seconds (longer for MedGemma)
        backoff_multiplier: Multiplier for exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return await func(*args, **kwargs)
                
                except ModelLoadException as e:
                    # GPU memory was recovered - allow retry
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Model loading still failed after {max_retries} retries: {str(e)}")
                        raise ContinueToNextRecordException(f"Model loading failed after {max_retries} retries") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} - model loading issue, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
                    
                except GPUMemoryException as e:
                    # GPU memory errors should not be retried by this decorator
                    # They are handled by the calling function
                    last_exception = e
                    logger.error(f"GPU memory error - not retrying at this level: {str(e)}")
                    raise e
                    
                except httpx.TimeoutException as e:
                    last_exception = e
                    if attempt == max_retries:
                        # For timeout errors, we continue to next record
                        logger.error(f"MedGemma timeout after {max_retries} retries: {str(e)}")
                        raise ContinueToNextRecordException(f"MedGemma timeout after {max_retries} retries") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with timeout, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
                    
                except httpx.HTTPStatusError as e:
                    last_exception = e
                    status_code = e.response.status_code
                    
                    # Check if the HTTP error contains GPU memory issues
                    try:
                        error_response = e.response.json()
                        error_detail = str(error_response.get('detail', ''))
                        if any(indicator in error_detail.lower() for indicator in 
                               ['cuda out of memory', 'out of memory', 'failed to allocate', 'model loading failed']):
                            logger.error(f"HTTP error contains GPU memory issue: {error_detail}")
                            raise GPUMemoryException(f"GPU memory error via HTTP {status_code}: {error_detail}") from e
                    except (ValueError, TypeError, AttributeError):
                        pass  # Not JSON or doesn't contain detail
                    
                    if attempt == max_retries:
                        # For HTTP errors (404, 500, etc.), stop the pipeline
                        logger.error(f"MedGemma HTTP {status_code} after {max_retries} retries, stopping pipeline: {str(e)}")
                        raise PipelineStopException(f"MedGemma HTTP {status_code} after {max_retries} retries") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with HTTP {status_code}, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
                    
                except (httpx.ConnectError, httpx.RequestError) as e:
                    last_exception = e
                    if attempt == max_retries:
                        # For connection errors, stop the pipeline
                        logger.error(f"MedGemma connection error after {max_retries} retries, stopping pipeline: {str(e)}")
                        raise PipelineStopException(f"MedGemma connection error after {max_retries} retries") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with connection error, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if the general exception contains GPU memory error indicators
                    error_str = str(e).lower()
                    if any(indicator in error_str for indicator in 
                           ['cuda out of memory', 'out of memory', 'failed to allocate', 'model loading failed']):
                        logger.error(f"General exception contains GPU memory issue: {str(e)}")
                        raise GPUMemoryException(f"GPU memory error: {str(e)}") from e
                    
                    if attempt == max_retries:
                        # For unexpected errors, stop the pipeline
                        logger.error(f"Unexpected MedGemma error after {max_retries} retries, stopping pipeline: {str(e)}")
                        raise PipelineStopException(f"Unexpected MedGemma error after {max_retries} retries") from e
                    
                    delay = base_delay * (backoff_multiplier ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed with unexpected error, retrying in {delay}s: {str(e)}")
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise PipelineStopException(f"Maximum retries exceeded") from last_exception
            
        return async_wrapper
    return decorator