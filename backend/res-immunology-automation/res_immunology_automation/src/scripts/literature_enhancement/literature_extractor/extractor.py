"""
Main literature extraction orchestrator with improved rate limiting
Updated to use new schema and handle default values
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from db.models import Disease, TargetDisease
from .config import (
    LITERATURE_ENDPOINT, TARGET_LITERATURE_ENDPOINT, 
    MAX_PMIDS_TO_PROCESS, RATE_LIMIT, MAX_RETRIES, BACKOFF_FACTOR, BASE_DELAY
)
from .lit_utils import (
    get_top_n_literature,
    normalize_disease_name, normalize_target_name, get_random_latency
)
from utils import load_response_from_file, save_response_to_file
from .pmid_converter import PMIDConverter
from .data_storage import LiteratureStorage
from literature_enhancement.db_utils.async_utils import create_pipeline_status_completed, log_error_to_management, check_pipeline_status

log = logging.getLogger(__name__)


class LiteratureExtractor:
    """Main class for orchestrating literature extraction process"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.storage = LiteratureStorage(db_session)
    
    async def _rate_limit_handler(self, attempt: int = 0) -> None:
        """
        Handle rate limiting with 300 second delay and exponential backoff
        
        Args:
            attempt: Current retry attempt number
        """
        if attempt == 0:
            # First rate limit hit - wait 300 seconds
            log.warning(f"Rate limit hit. Waiting {RATE_LIMIT} seconds...")
            await asyncio.sleep(RATE_LIMIT)
        else:
            # Additional backoff for subsequent rate limits
            backoff_delay = BASE_DELAY * (BACKOFF_FACTOR ** attempt)
            total_delay = RATE_LIMIT + backoff_delay
            log.warning(f"Rate limit hit again (attempt {attempt + 1}). Waiting {total_delay:.1f} seconds...")
            await asyncio.sleep(total_delay)
    
    def _get_literature_data_from_cache(self, disease: str, target: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load literature data from cached files
        
        Args:
            disease: Disease name
            target: Target name (optional)
            
        Returns:
            List of literature entries
        """
        normalized_disease = normalize_disease_name(disease)
        
        if target:
            # Target-disease combination
            normalized_target = normalize_target_name(target)
            record = self.db.query(TargetDisease).filter_by(
                id=f"{normalized_target}-{normalized_disease}"
            ).first()
            endpoint = TARGET_LITERATURE_ENDPOINT
        else:
            # Disease only
            record = self.db.query(Disease).filter_by(id=normalized_disease).first()
            endpoint = LITERATURE_ENDPOINT
        
        if not record:
            log.error(f"No cache record found for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            return []
        
        cache_data = load_response_from_file(record.file_path)
        literature_endpoint = cache_data.get(endpoint, {})
        literature_list = literature_endpoint.get("literature", [])
        
        log.info(f"Loaded {len(literature_list)} literature entries from cache")
        return literature_list
    
    async def _process_pmids_to_articles(self, 
                                   pmid_title_pairs: List[Dict[str, str]],
                                   disease: str, 
                                   target: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Process PMID-title pairs: convert to PMCIDs, fetch content, store in database
        With enhanced rate limiting and retry logic.

        Args:
            pmid_title_pairs: List of dicts with pmid and title
            disease: Disease name
            target: Target name (optional)
        
        Returns:
            Tuple of (processed_count, success_count, error_count)
        """
        processed_count = 0
        success_count = 0
        error_count = 0

        # Use default values consistent with database schema
        disease_value = disease if disease else "no-disease"
        target_value = target if target else "no-target"

        # Extract just PMIDs for conversion
        pmids = [pair["pmid"] for pair in pmid_title_pairs]

        async with PMIDConverter() as converter:
            # Convert PMIDs to PMCIDs in batches with rate limiting
            log.info(f"Converting {len(pmids)} PMIDs to PMCIDs")
            
            for attempt in range(MAX_RETRIES):
                try:
                    pmid_to_pmcid = await converter.pmids_to_pmcids(pmids)
                    break
                except Exception as e:
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        await self._rate_limit_handler(attempt)
                        if attempt == MAX_RETRIES - 1:
                            log.error(f"Failed to convert PMIDs after {MAX_RETRIES} attempts due to rate limiting")
                            return processed_count, success_count, error_count
                    else:
                        log.error(f"Error converting PMIDs: {e}")
                        if attempt == MAX_RETRIES - 1:
                            return processed_count, success_count, error_count
        
            # Process each PMID with its title
            for idx, pair in enumerate(pmid_title_pairs, 1):
                try:
                    pmid = pair["pmid"]
                    title = pair["title"]  # Get title from literature cache
                
                    log.info(f"Processing PMID {pmid} ({idx}/{len(pmid_title_pairs)})")
                    processed_count += 1
                
                    # Get PMCID
                    pmcid = pmid_to_pmcid.get(pmid)
                    if not pmcid:
                        log.debug(f"No PMCID found for PMID {pmid} - skipping")
                        continue
                
                    # Fetch full text content with rate limiting
                    log.debug(f"Fetching full text for PMCID {pmcid}")
                    full_text = None
                    
                    for attempt in range(MAX_RETRIES):
                        try:
                            full_text = await converter.get_pmc_full_text(pmcid)
                            break
                        except Exception as e:
                            if "429" in str(e) or "Too Many Requests" in str(e):
                                await self._rate_limit_handler(attempt)
                                if attempt == MAX_RETRIES - 1:
                                    log.error(f"Failed to fetch full text for {pmcid} after {MAX_RETRIES} attempts")
                            else:
                                if attempt == MAX_RETRIES - 1:
                                    log.error(f"Error fetching full text for {pmcid}: {e}")
                
                    # Only proceed if we have full text
                    if not full_text or not full_text.strip():
                        log.debug(f"No full text content retrieved for PMCID {pmcid} - skipping")
                        continue
                
                    pmc_url = await converter.get_pmc_url(pmcid)
                
                    # Store article with full text AND title
                    success = self.storage.store_article(
                        disease=disease_value,
                        pmid=pmid,
                        pmcid=pmcid,
                        title=title,  # Pass the title from literature cache
                        url=pmc_url,
                        raw_full_text=full_text,
                        target=target_value
                    )
                
                    if success:
                        success_count += 1
                        log.debug(f"Successfully stored article PMID {pmid} with title: {title[:50]}...")
                    else:
                        error_count += 1
                        log.warning(f"Failed to store article PMID {pmid}")
                
                    # Add delay between requests
                    if idx < len(pmid_title_pairs):
                        delay = get_random_latency(5, 10)
                        log.debug(f"Waiting {delay:.1f}s before next API request...")
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    error_count += 1
                    log.error(f"Error processing PMID {pmid}: {e}")
                    if idx < len(pmid_title_pairs):
                        delay = get_random_latency(5, 10)
                        await asyncio.sleep(delay)

        log.info(f"Processing complete: {processed_count} processed, {success_count} successful, {error_count} errors")
        return processed_count, success_count, error_count

    async def extract_literature_for_disease(self, disease: str, target: Optional[str] = None) -> bool:
        """
        Main function that orchestrates the literature extraction process
        """
        try:
            log.info(f"Starting literature extraction for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")

            # Use default values consistent with database schema
            disease_value = disease if disease else "no-disease"
            target_value = target if target else "no-target"

            # --- Checkpoint: Check if pipeline is already completed ---
            current_status = await check_pipeline_status(disease_value, target_value, "extraction")
            if current_status == "completed":
                log.info(f"Literature extraction already completed for {disease_value}-{target_value} - skipping")
                return True

            # Load literature data from cache
            literature_data = self._get_literature_data_from_cache(disease, target)

            if not literature_data:
                log.warning(f"No literature data found")
                await log_error_to_management(
                    job_details=f"literature_extraction_{disease_value}_{target_value}",
                    endpoint=TARGET_LITERATURE_ENDPOINT if target else LITERATURE_ENDPOINT,
                    error_description="No literature data found in cache"
                )
                return False

            # Get top PMID-title pairs
            pmid_title_pairs = get_top_n_literature(literature_data, MAX_PMIDS_TO_PROCESS)
            if not pmid_title_pairs:
                log.warning(f"No valid PMIDs found")
                await log_error_to_management(
                    job_details=f"literature_extraction_{disease_value}_{target_value}",
                    endpoint=TARGET_LITERATURE_ENDPOINT if target else LITERATURE_ENDPOINT,
                    error_description="No valid PMIDs found in literature data"
                )
                return False

            log.info(f"Processing {len(pmid_title_pairs)} PMID-title pairs")

            # Process PMID-title pairs
            processed, successful, errors = await self._process_pmids_to_articles(pmid_title_pairs, disease, target)

            log.info(f"Literature extraction completed. Results: {processed} processed, {successful} successful, {errors} errors")

            # Only update pipeline status to completed if extraction was successful
            if successful > 0:
                await create_pipeline_status_completed(disease_value, target_value, "extraction")
                return True
            else:
                # Log error but don't update pipeline status
                await log_error_to_management(
                    job_details=f"literature_extraction_{disease_value}_{target_value}",
                    endpoint=TARGET_LITERATURE_ENDPOINT if target else LITERATURE_ENDPOINT,
                    error_description=f"Extraction failed: {errors} errors, {successful} successes"
                )
                return False

        except Exception as e:
            log.error(f"Literature extraction failed: {e}")
            # Log error but don't update pipeline status
            disease_value = disease if disease else "no-disease"
            target_value = target if target else "no-target"
            await log_error_to_management(
                job_details=f"literature_extraction_{disease_value}_{target_value}",
                endpoint=TARGET_LITERATURE_ENDPOINT if target else LITERATURE_ENDPOINT,
                error_description=f"Exception during extraction: {str(e)}"
            )
            return False

    async def extract_literature_batch(self, diseases: List[str], target: Optional[str] = None) -> Dict[str, bool]:
        """
        Extract literature for multiple diseases with longer delays between diseases

        Args:
            diseases: List of disease names
            target: Target name (optional)
            
        Returns:
            Dictionary mapping diseases to success status
        """
        results = {}

        for i, disease in enumerate(diseases, 1):
            try:
                log.info(f"Processing disease {i}/{len(diseases)}: {disease}")
                success = await self.extract_literature_for_disease(disease, target)
                results[disease] = success
                
                # Add longer delay between diseases to be extra safe
                if i < len(diseases):
                    delay = get_random_latency(10, 15)  # Increased from 5-10 to 10-15 seconds
                    log.info(f"Waiting {delay:.1f}s before processing next disease...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                log.error(f"Error processing disease {disease}: {e}")
                results[disease] = False

        successful_count = sum(1 for success in results.values() if success)
        log.info(f"Batch processing complete: {successful_count}/{len(diseases)} successful")

        return results
    
    def get_extraction_summary(self, disease: str, target: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary of extraction results
        
        Args:
            disease: Disease name
            target: Target name (optional)
            
        Returns:
            Dictionary with extraction summary
        """
        # Use default values consistent with database schema
        disease_value = disease if disease else "no-disease"
        target_value = target if target else "no-target"
        
        article_count = self.storage.get_article_count(disease_value, target_value)
        articles = self.storage.get_articles_for_disease(disease_value, target_value)
        
        articles_with_full_text = sum(1 for article in articles if article.raw_full_text)
        articles_with_pmcid = sum(1 for article in articles if article.pmcid)
        
        return {
            "disease": disease_value,
            "target": target_value,
            "total_articles": article_count,
            "articles_with_full_text": articles_with_full_text,
            "articles_with_pmcid": articles_with_pmcid,
            "full_text_percentage": round((articles_with_full_text / article_count * 100) if article_count > 0 else 0, 2),
            "pmcid_percentage": round((articles_with_pmcid / article_count * 100) if article_count > 0 else 0, 2)
        }