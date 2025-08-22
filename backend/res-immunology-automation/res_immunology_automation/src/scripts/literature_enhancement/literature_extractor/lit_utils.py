#lit_utils.py
"""
Utility functions for literature extraction
"""
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional
from pathlib import Path
# Set up logging
from literature_enhancement.config import LOGGING_LEVEL, DEFAULT_REQUEST_DELAY
logging.basicConfig(level=LOGGING_LEVEL)
import os
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


def get_random_latency(a: int = DEFAULT_REQUEST_DELAY[0], b: int = DEFAULT_REQUEST_DELAY[1]) -> float:
    """
    Generate random delay to be respectful to APIs
    
    Args:
        a: Minimum delay in seconds
        b: Maximum delay in seconds
        
    Returns:
        Random float between a and b
    """
    return random.uniform(a, b)


def get_top_n_literature(literature_data: List[Dict[str, Any]], n: int) -> List[Dict[str, str]]:
    """
    Extract top n PMIDs by overall_score WITH titles
    
    Args:
        literature_data: List of literature dictionaries
        n: Number of PMIDs to return
        
    Returns:
        List of dicts with pmid and title
    """
    if not literature_data:
        return []
    
    sorted_lit = sorted(
        literature_data, 
        key=lambda d: d.get("overall_score", 0), 
        reverse=True
    )

    # Return both PMID and title - FIXED: Check "Title" key from literature endpoint
    pmid_title_pairs = []
    for d in sorted_lit[:n]:
        pmid = str(d.get("PMID", "")).strip()
        title = d.get("Title", "")  # Use "Title" key from literature endpoint cache
        if pmid and pmid.isdigit():
            pmid_title_pairs.append({"pmid": pmid, "title": title.strip()})
    
    log.info(f"Extracted {len(pmid_title_pairs)} valid PMIDs with titles from {len(literature_data)} literature entries")
    return pmid_title_pairs

def normalize_disease_and_target_name(disease_or_target_str: str) -> str:
    """
    Normalize disease or target name for database storage

    Args:
        disease_or_target_str: Raw disease or target name
        
    Returns:
        Normalized disease or target name (lowercase, underscores)
    """
    return disease_or_target_str.strip().lower().replace(" ", "_")


# def normalize_target_name(target: str) -> str:
#     """
#     Normalize target name for database storage
    
#     Args:
#         target: Raw target name
        
#     Returns:
#         Normalized target name (lowercase)
#     """
#     return target.strip().lower()


def create_target_disease_id(target: str, disease: str) -> str:
    """
    Create a unique ID for target-disease combinations
    
    Args:
        target: Target name
        disease: Disease name
        
    Returns:
        Combined ID string
    """
    normalized_target = normalize_disease_and_target_name(target)
    normalized_disease = normalize_disease_and_target_name(disease)
    return f"{normalized_target}-{normalized_disease}"


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        log.error(f"Failed after {max_retries} retries: {e}")
                        raise e
                    
                    delay = base_delay * (2 ** attempt)
                    log.debug(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
            
        return wrapper
    return decorator