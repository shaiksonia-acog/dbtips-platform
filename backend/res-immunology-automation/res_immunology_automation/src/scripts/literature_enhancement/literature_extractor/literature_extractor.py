import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Set

from sqlalchemy import and_
from db.models import (
    ArticlesMetadata,
    TargetDisease,
    Disease
)
from literature_enhancement.literature_extractor.config import (
    LITERATURE_ENDPOINT, TARGET_LITERATURE_ENDPOINT, MAX_PMIDS_TO_PROCESS
)
from literature_enhancement.literature_extractor.lit_utils import (
    normalize_disease_and_target_name,
    get_top_n_literature,
)
from literature_enhancement.literature_extractor.pmid_converter import PMIDConverter
from literature_enhancement.literature_extractor.data_storage import LiteratureStorage
from utils import load_response_from_file
from literature_enhancement.db_utils.async_utils import create_pipeline_status_completed, log_error_to_management, check_pipeline_status

# --- Helpers ---

def log_prefix(disease: str, target: str) -> str:
    return f"[Disease: {disease}, Target: {target}]"

def fetch_cache(file_path: str, endpoint: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        logging.error(f"Cache file not found: {file_path}")
        return []
    cache = load_response_from_file(file_path)
    return cache.get(endpoint, {}).get("literature", [])

def top_n(items: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    return items[:n] if items else []

def get_existing_pmids(db, disease: str, target: str) -> Set[str]:
    try:
        rows = db.query(ArticlesMetadata.pmid).filter(
            and_(ArticlesMetadata.disease == disease, ArticlesMetadata.target == target)
        ).all()
        return {r.pmid for r in rows}
    except Exception as e:
        logging.error(f"{log_prefix(disease, target)} Error fetching existing PMIDs: {e}")
        return set()

# --- Main Extraction ---

async def extract_literature(db, disease: str | None, target: str | None = None) -> bool:
    disease = disease or "no-disease"
    target = target or "no-target"
    prefix = log_prefix(disease, target)

    logging.info(f"{prefix} Starting extraction")

    # --- Checkpoint: Check if pipeline is already completed ---
    current_status = await check_pipeline_status(disease, target, "extraction")
    if current_status == "completed":
        logging.info(f"{prefix} Literature extraction already completed - skipping")
        return True

    storage = LiteratureStorage(db)

    # --- Resolve cache source ---
    ndisease = normalize_disease_and_target_name(disease)
    if target != "no-target":
        ntarget = normalize_disease_and_target_name(target)
        record = db.query(TargetDisease).filter_by(id=f"{ntarget}-{ndisease}").first()
        endpoint = TARGET_LITERATURE_ENDPOINT
    else:
        record = db.query(Disease).filter_by(id=ndisease).first()
        endpoint = LITERATURE_ENDPOINT

    if not record:
        error_msg = f"{prefix} No cache record found"
        logging.error(error_msg)
        # Log error to management table instead of updating pipeline status
        await log_error_to_management(
            job_details=f"literature_extraction_{disease}_{target}",
            endpoint=endpoint,
            error_description="No cache record found for disease/target combination"
        )
        return False

    # --- Load cache ---
    literature = fetch_cache(record.file_path, endpoint)
    if not literature:
        error_msg = f"{prefix} No literature in cache"
        logging.warning(error_msg)
        # Log error to management table
        await log_error_to_management(
            job_details=f"literature_extraction_{disease}_{target}",
            endpoint=endpoint,
            error_description="No literature data found in cache"
        )
        return False
    
    logging.info(f"{prefix} Loaded {len(literature)} entries")

    # Get top PMID-title pairs
    top_pmid_title_pairs = get_top_n_literature(literature, MAX_PMIDS_TO_PROCESS)
    if not top_pmid_title_pairs:
        error_msg = f"{prefix} No PMIDs found"
        logging.warning(error_msg)
        # Log error to management table
        await log_error_to_management(
            job_details=f"literature_extraction_{disease}_{target}",
            endpoint=endpoint,
            error_description="No valid PMIDs found in literature data"
        )
        return False

    existing = get_existing_pmids(db, disease, target)
    to_process = [p for p in top_pmid_title_pairs if p["pmid"] not in existing]
    if not to_process:
        logging.info(f"{prefix} All PMIDs already exist")
        # Update pipeline status to completed since no new processing needed
        await create_pipeline_status_completed(disease, target, "extraction")
        return True

    # --- Convert & Store ---
    processed, success, skipped, errors = 0, 0, 0, 0
    async with PMIDConverter() as conv:
        mapping = await conv.pmids_to_pmcids([p["pmid"] for p in to_process])

        for idx, item in enumerate(to_process, 1):
            pmid, title = item["pmid"], item["title"]
            processed += 1
            logging.info(f"{prefix} Processing PMID {pmid} ({idx}/{len(to_process)})")

            try:
                pmcid = mapping.get(pmid)
                if not pmcid:
                    skipped += 1
                    continue

                full_text = await conv.get_pmc_full_text(pmcid)
                if not full_text:
                    skipped += 1
                    continue

                url = await conv.get_pmc_url(pmcid)
                # Pass the title from literature cache to store_article
                if storage.store_article(disease, pmid, pmcid, title, url, full_text, target):
                    success += 1
                else:
                    errors += 1

                if idx < len(to_process):
                    await asyncio.sleep(0.2)

            except Exception as e:
                logging.error(f"{prefix} Error PMID {pmid}: {e}")
                errors += 1

    logging.info(f"{prefix} Done. Processed {processed}, Success {success}, Skipped {skipped}, Errors {errors}")

    # Only update pipeline status to completed if extraction was successful
    if success > 0 or skipped == processed:
        await create_pipeline_status_completed(disease, target, "extraction")
        return True
    else:
        # Log error but don't update pipeline status
        await log_error_to_management(
            job_details=f"literature_extraction_{disease}_{target}",
            endpoint=endpoint,
            error_description=f"Extraction failed: {errors} errors, {success} successes"
        )
        return False