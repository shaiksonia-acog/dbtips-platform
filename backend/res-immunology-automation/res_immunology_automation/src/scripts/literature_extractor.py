# Import literature extraction components
from literature_enhancement.literature_extractror.extractor import LiteratureExtractor
from literature_enhancement.literature_extractror.config import (
    LITERATURE_ENDPOINT, TARGET_LITERATURE_ENDPOINT, MAX_PMIDS_TO_PROCESS
)
from literature_enhancement.literature_extractror.lit_utils import (
    get_top_100_pmids, normalize_disease_name, normalize_target_name
)
from utils import load_response_from_file
from literature_enhancement.literature_extractror.pmid_converter import PMIDConverter
from literature_enhancement.literature_extractror.data_storage import LiteratureStorage

from db.database import get_db, Base # , engine, , SessionLocal
from db.models import DiseaseDossierStatus, ErrorManagement, TargetDossierStatus

import logging
import time
import asyncio
from graphrag_service import get_redis
from fastapi import HTTPException
from sqlalchemy.sql import func
from sqlalchemy import select, union_all, and_, literal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import update, String
import os, sys
import tzlocal
from datetime import datetime, timezone

async def extract_literature_with_titles(db, disease: str, target: str = None) -> bool:
    """
    Extract literature and store articles with titles in database
    Only stores articles that have raw_full_text content and are not already in database
    
    Args:
        db: Database session
        disease: Disease name (can be None for target-only)
        target: Target name (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Handle None disease for target-only processing
        if disease is None:
            disease = "no-disease"
        
        logging.info(f"Starting literature extraction for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
        
        # Check if literature data is already extracted for this disease/target combination
        already_extracted = check_literature_already_extracted(db, disease, target)
        
        if already_extracted:
            logging.info(f"Literature data already extracted for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease} - skipping extraction")
            return True
        
        # Create storage instance
        storage = LiteratureStorage(db)
        
        # Load literature data from cache
        normalized_disease = normalize_disease_name(disease)
        
        if target:
            # Target-disease combination
            normalized_target = normalize_target_name(target)
            from db.models import TargetDisease
            record = db.query(TargetDisease).filter_by(
                id=f"{normalized_target}-{normalized_disease}"
            ).first()
            endpoint = TARGET_LITERATURE_ENDPOINT
        else:
            # Disease only
            from db.models import Disease
            record = db.query(Disease).filter_by(id=normalized_disease).first()
            endpoint = LITERATURE_ENDPOINT
        
        if not record:
            logging.error(f"No cache record found for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            return False
        
        cache_data = load_response_from_file(record.file_path)
        literature_endpoint = cache_data.get(endpoint, {})
        literature_list = literature_endpoint.get("literature", [])
        
        if not literature_list:
            logging.warning(f"No literature data found for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            return True
        
        logging.info(f"Loaded {len(literature_list)} literature entries from cache")
        
        # Get top PMIDs
        pmids = get_top_100_pmids(literature_list, MAX_PMIDS_TO_PROCESS)
        if not pmids:
            logging.warning(f"No valid PMIDs found for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            return True
        
        logging.info(f"Processing {len(pmids)} PMIDs for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
        
        # Create PMID to title mapping from literature data
        pmid_to_title = {}
        for lit_entry in literature_list:
            pmid_val = lit_entry.get("PMID")  # Based on your sample, it's "PMID"
            title_val = lit_entry.get("Title")  # Based on your sample, it's "Title"
            
            if pmid_val and title_val:
                pmid_str = str(pmid_val).strip()
                title_str = str(title_val).strip()
                if pmid_str and title_str:
                    pmid_to_title[pmid_str] = title_str
                    logging.debug(f"Mapped PMID {pmid_str} to title: {title_str[:50]}...")
        
        logging.info(f"Created title mapping for {len(pmid_to_title)} PMIDs")
        
        # Debug: Check if our target PMIDs have titles
        missing_titles = [pmid for pmid in pmids if pmid not in pmid_to_title]
        if missing_titles:
            logging.warning(f"No titles found for {len(missing_titles)} PMIDs: {missing_titles[:5]}...")  # Show first 5
        
        # Process PMIDs to articles
        processed_count = 0
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        async with PMIDConverter() as converter:
            # Convert PMIDs to PMCIDs in batches
            logging.info(f"Converting {len(pmids)} PMIDs to PMCIDs")
            pmid_to_pmcid = await converter.pmids_to_pmcids_batch(pmids)
            
            # Process each PMID
            for idx, pmid in enumerate(pmids, 1):
                try:
                    logging.info(f"Processing PMID {pmid} ({idx}/{len(pmids)})")
                    processed_count += 1
                    
                    # Get title from literature data
                    title = pmid_to_title.get(pmid, None)
                    if title:
                        logging.debug(f"Found title for PMID {pmid}: {title[:50]}...")
                    else:
                        logging.warning(f"No title found for PMID {pmid}")
                    
                    # Get PMCID
                    pmcid = pmid_to_pmcid.get(pmid)
                    if not pmcid:
                        logging.debug(f"No PMCID found for PMID {pmid} - skipping (no full text available)")
                        skipped_count += 1
                        continue
                    
                    # Fetch full text content
                    logging.debug(f"Fetching full text for PMCID {pmcid}")
                    raw_full_text = await converter.get_pmc_full_text(pmcid)
                    
                    # Only store if we have raw_full_text content
                    if not raw_full_text or not raw_full_text.strip():
                        logging.debug(f"No full text content for PMCID {pmcid} - skipping")
                        skipped_count += 1
                        continue
                    
                    # Get PMC URL
                    pmc_url = await converter.get_pmc_url(pmcid)
                    
                    # Store article with full text and title
                    success = storage.store_article(
                        disease=disease,
                        pmid=pmid,
                        pmcid=pmcid,
                        title=title,
                        url=pmc_url,
                        raw_full_text=raw_full_text,
                        target=target
                    )
                    
                    if success:
                        success_count += 1
                        logging.info(f"Successfully stored article PMID {pmid} with title: {title[:30] if title else 'No title'}...")
                    else:
                        error_count += 1
                        logging.warning(f"Failed to store article PMID {pmid}")
                    
                    # Add delay between requests
                    if idx < len(pmids):
                        await asyncio.sleep(2)  # 2 second delay
                        
                except Exception as e:
                    error_count += 1
                    logging.error(f"Error processing PMID {pmid}: {e}")
        
        logging.info(f"Literature extraction completed for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
        logging.info(f"Results: {processed_count} processed, {success_count} successful (with full text), {skipped_count} skipped (no full text), {error_count} errors")
        
        return True
        
    except Exception as e:
        logging.error(f"Literature extraction failed for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}: {e}")
        return False


def check_literature_already_extracted(db, disease: str, target: str = None):
    """
    Check if literature data is already extracted for the given disease/target combination
    
    Args:
        db: Database session
        disease: Disease name (already normalized to "no-disease" if None)
        target: Target name (optional)
        
    Returns:
        True if data already exists, False otherwise
    """
    try:
        from db.models import ArticlesMetadata  # Assuming this is your articles table model
        
        # Ensure we use "no-target" as default for target if None
        target_value = target if target else "no-target"
        
        if target:
            # Check for target-disease combination
            existing_record = db.query(ArticlesMetadata).filter(
                and_(
                    ArticlesMetadata.disease == disease,
                    ArticlesMetadata.target == target_value
                )
            ).first()
        else:
            # Check for disease only
            existing_record = db.query(ArticlesMetadata).filter(
                and_(
                    ArticlesMetadata.disease == disease,
                    ArticlesMetadata.target == "no-target"
                )
            ).first()
        
        if existing_record:
            logging.info(f"Literature data already exists for {'target-' if target else ''}disease: {target_value + '-' if target else ''}{disease}")
            return True
        else:
            logging.info(f"No existing literature data found for {'target-' if target else ''}disease: {target_value + '-' if target else ''}{disease}")
            return False
        
    except Exception as e:
        logging.error(f"Error checking existing literature data: {e}")
        return False