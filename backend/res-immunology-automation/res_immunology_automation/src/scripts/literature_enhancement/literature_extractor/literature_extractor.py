#literature_extractor.py
"""
Updated literature extraction with optimized PMID checking
Refactored to use LiteratureExtractor class from extractor.py
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from sqlalchemy import and_
from db.models import (
    ArticlesMetadata,
    TargetDisease,
    Disease
)
from literature_enhancement.config import (
    LITERATURE_ENDPOINT, TARGET_LITERATURE_ENDPOINT, MAX_PMIDS_TO_PROCESS, CACHE_DIR_PATH
)
from literature_enhancement.literature_extractor.lit_utils import (
    normalize_disease_and_target_name,
    get_top_n_literature,
)
from literature_enhancement.literature_extractor.extractor import LiteratureExtractor
from utils import load_response_from_file
from literature_enhancement.db_utils.async_utils import create_pipeline_status, check_pipeline_status

module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logging = logging.getLogger(module_name)

POSTGRES_USER: str = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB: str = os.getenv("POSTGRES_DB")
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
engine = create_engine(
    DATABASE_URL,
    echo=False,       # True to log SQL queries
    future=True       # Use 2.x SQLAlchemy API
)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)

@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

# --- Helper Functions ---

def log_prefix(disease: str, target: str) -> str:
    """Generate consistent log prefix"""
    return f"[Disease: {disease}, Target: {target}]"

def get_normalized_values(disease: str, target: str) -> Tuple[str, str]:
    """Get normalized disease and target values with defaults"""
    return (
        disease or "no-disease",
        target or "no-target"
    )

def get_endpoint_type(target: str) -> str:
    """Get appropriate endpoint based on target"""
    return TARGET_LITERATURE_ENDPOINT if target != "no-target" else LITERATURE_ENDPOINT

def fetch_cache(file_path: str, endpoint: str) -> List[Dict[str, Any]]:
    """Load literature data from cache file"""
    file_path = os.path.join(CACHE_DIR_PATH, file_path)
    print("file_path: ", file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cache file not found: {file_path}")
    
      # Debugging line to check the file path
    cache = load_response_from_file(file_path)
    literature_data = cache.get(endpoint, {}).get("literature", [])
    
    if not literature_data:
        raise ValueError(f"No literature data found in cache for endpoint {endpoint}")
    
    return literature_data

def get_existing_pmids(db, disease: str, target: str) -> Set[str]:
    """Fetch existing PMIDs for disease-target combination"""
    try:
        rows = db.query(ArticlesMetadata.pmid).filter(
            and_(ArticlesMetadata.disease == disease, ArticlesMetadata.target == target)
        ).all()
        existing_pmids = {r.pmid for r in rows}
        logging.info(f"{log_prefix(disease, target)} Found {len(existing_pmids)} existing PMIDs in database")
        return existing_pmids
    except Exception as e:
        logging.error(f"{log_prefix(disease, target)} Error fetching existing PMIDs: {e}")
        raise

def get_cache_record(db, disease: str, target: str) -> Tuple[Any, str]:
    """Get cache record and endpoint for disease-target combination"""
    ndisease = normalize_disease_and_target_name(disease)
    
    if target != "no-target":
        ntarget = normalize_disease_and_target_name(target)
        record = db.query(TargetDisease).filter_by(id=f"{ntarget}-{ndisease}").first()
        endpoint = TARGET_LITERATURE_ENDPOINT
    else:
        record = db.query(Disease).filter_by(id=ndisease).first()
        endpoint = LITERATURE_ENDPOINT
    
    if not record:
        raise ValueError(f"CACHE not available for disease-target combination: {disease}-{target}...")

    
    return record, endpoint

async def should_skip_extraction(disease: str, target: str) -> bool:
    """Check if extraction should be skipped (already completed)"""
    current_status = await check_pipeline_status(disease, target, "extraction")
    if current_status == "completed":
        logging.info(f"{log_prefix(disease, target)} Literature extraction already completed - skipping")
        return True
    return False

def filter_new_pmids(pmid_title_pairs: List[Dict[str, Any]], existing_pmids: Set[str]) -> List[Dict[str, Any]]:
    """Filter out already processed PMIDs"""
    new_pmids = [p for p in pmid_title_pairs if p["pmid"] not in existing_pmids]
    logging.info(f"Filtered to {len(new_pmids)} new PMIDs from {len(pmid_title_pairs)} total PMIDs")
    return new_pmids

# --- Main Extraction Function ---

async def extract_literature(disease: str , target: str) -> bool:
    """
    Main literature extraction function with optimized PMID checking
    Refactored to use LiteratureExtractor class while preserving all existing functionality
    Raises exceptions on critical failures instead of returning False
    """
    # Normalize inputs
    disease, target = get_normalized_values(disease, target)
    prefix = log_prefix(disease, target)
    endpoint = get_endpoint_type(target)

    logging.info(f"{prefix} Starting extraction")

    # FIRST: Check if pipeline is already completed - skip if yes
    if await should_skip_extraction(disease, target):
        return True

    try:
        with get_session() as db:
            # Create LiteratureExtractor instance
            extractor = LiteratureExtractor(db)

            # Get cache record and validate (will raise exception if not found)
            record, endpoint = get_cache_record(db, disease, target)

            # Load and validate literature data (will raise exception if not found)
            literature = fetch_cache(record.file_path, endpoint)
            logging.info(f"{prefix} Loaded {len(literature)} literature entries from cache")

            # Get top PMID-title pairs
            top_pmid_title_pairs = get_top_n_literature(literature, MAX_PMIDS_TO_PROCESS)
            if not top_pmid_title_pairs:
                raise ValueError("No valid PMIDs found in literature data")

            logging.info(f"{prefix} Found {len(top_pmid_title_pairs)} valid PMID-title pairs")

            # Get existing PMIDs from database (will raise exception on DB error)
            existing_pmids = get_existing_pmids(db, disease, target)
            
            # Filter to only new PMIDs
            new_pmids_to_process = filter_new_pmids(top_pmid_title_pairs, existing_pmids)
            
            if not new_pmids_to_process:
                logging.info(f"{prefix} All PMIDs already exist in database - marking as completed")
                await create_pipeline_status(disease, target, "extraction", "completed")
                return True

            # Process only the new PMIDs using the LiteratureExtractor
            processing_stats = await extractor._process_pmids_to_articles(
                new_pmids_to_process, disease, target
            )

            # Extract individual stats from the tuple returned by _process_pmids_to_articles
            processed_count, success_count, error_count = processing_stats

            # Create stats dictionary to match the existing logic
            processing_stats_dict = {
                'processed': processed_count,
                'success': success_count,
                'errors': error_count,
                'skipped': 0  # The LiteratureExtractor handles skipped articles internally
            }

            # Mark as completed if we successfully processed at least some articles
            # or if all were skipped (meaning the PMIDs exist but have no content available)
            if processing_stats_dict['success'] > 0 or processing_stats_dict['skipped'] == processing_stats_dict['processed']:
                logging.info(f"{prefix} Literature extraction completed successfully")
                await create_pipeline_status(disease, target, "extraction", "completed")
                return True
            else:
                # If we had some successes but also errors, still mark as completed
                # since we made progress
                if processing_stats_dict['success'] > 0:
                    logging.warning(f"{prefix} Completed with partial success - "
                                f"Success: {processing_stats_dict['success']}, Errors: {processing_stats_dict['errors']}")
                    await create_pipeline_status(disease, target, "extraction", "completed")
                    return True
                else:
                    # No successes at all - this is a critical failure
                    error_msg = (f"Literature extraction failed completely - "
                            f"Processed: {processing_stats_dict['processed']}, "
                            f"Errors: {processing_stats_dict['errors']}, "
                            f"Success: {processing_stats_dict['success']}")
                    logging.error(f"{prefix} {error_msg}")
                    raise RuntimeError(error_msg)

    except Exception as e:
        # Log the error and re-raise so build_dossier can handle it
        error_msg = f"Literature extraction failed for {disease}-{target}: {str(e)}"
        logging.error(f"{prefix} {error_msg}")
        raise RuntimeError(error_msg) from e