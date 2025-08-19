"""
Utility functions for literature extraction
"""
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from .config import DEFAULT_REQUEST_DELAY

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


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


def get_top_100_literature(literature_data: List[Dict[str, Any]], max_pmids: int = 100) -> List[str]:
    """
    Extract top PMIDs by overall_score
    
    Args:
        literature_data: List of literature dictionaries
        max_pmids: Maximum number of PMIDs to return
        
    Returns:
        List of top PMIDs sorted by overall_score
    """
    if not literature_data:
        return []
    
    sorted_lit = sorted(
        literature_data, 
        key=lambda d: d.get("overall_score", 0), 
        reverse=True
    )

    pmids = [{"pmid": d.get("PMID", "").strip(), "title": d.get("Title", "").strip()} for d in sorted_lit[:max_pmids]]
    # # Filter out empty or invalid PMIDs
    # valid_pmids = [pmid for pmid in pmids if pmid and pmid.isdigit()]
    
    # log.info(f"Extracted {len(valid_pmids)} valid PMIDs from {len(literature_data)} literature entries")
    return pmids


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
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    log.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
            
        return wrapper
    return decorator