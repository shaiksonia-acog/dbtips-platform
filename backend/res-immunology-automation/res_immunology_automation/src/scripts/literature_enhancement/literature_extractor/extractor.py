#extractor.py
"""
Main literature extraction orchestrator with improved rate limiting and DRY principles
Updated to use new schema and handle default values
Updated to use combined pmids_to_full_texts method with proper delays
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from db.models import Disease, TargetDisease
from .lit_utils import (
    get_top_n_literature,
    normalize_disease_and_target_name, get_random_latency
)
from utils import load_response_from_file, save_response_to_file
from .pmid_converter import PMIDConverter
from .data_storage import LiteratureStorage
from literature_enhancement.db_utils.async_utils import create_pipeline_status, log_error_to_management, check_pipeline_status
import os
from literature_enhancement.config import (LOGGING_LEVEL, LITERATURE_ENDPOINT, TARGET_LITERATURE_ENDPOINT, 
    MAX_PMIDS_TO_PROCESS, RATE_LIMIT, MAX_RETRIES, BACKOFF_FACTOR, BASE_DELAY)
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


class LiteratureExtractor:
    """Main class for orchestrating literature extraction process"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.storage = LiteratureStorage(db_session)
    
    # -----------------------------
    # Helper Methods (DRY Abstractions)
    # -----------------------------
    
    def _get_disease_target_values(self, disease: str, target: Optional[str] = None) -> Tuple[str, str]:
        """Get normalized disease and target values with defaults"""
        return disease or "no-disease", target or "no-target"
    
    def _get_job_identifier(self, disease: str, target: str) -> str:
        """Generate consistent job identifier for logging"""
        return f"literature_extraction_{disease}_{target}"
    
    def _get_endpoint_type(self, target: str) -> str:
        """Get appropriate endpoint based on target presence"""
        return TARGET_LITERATURE_ENDPOINT if target != "no-target" else LITERATURE_ENDPOINT
    
    async def _log_and_handle_error(self, disease: str, target: str, error_msg: str, 
                                  exception: Optional[Exception] = None) -> bool:
        """Centralized error logging and handling"""
        endpoint = self._get_endpoint_type(target)
        job_id = self._get_job_identifier(disease, target)
        
        if exception:
            log.error(f"Error for {disease}-{target}: {exception}")
            error_description = f"{error_msg}: {str(exception)}"
        else:
            log.warning(f"Warning for {disease}-{target}: {error_msg}")
            error_description = error_msg
            
        await log_error_to_management(job_id, endpoint, error_description)
        return False
    
    async def _check_pipeline_completion(self, disease: str, target: str) -> bool:
        """Check if pipeline is already completed"""
        current_status = await check_pipeline_status(disease, target, "extraction")
        if current_status == "completed":
            log.info(f"Literature extraction already completed for {disease}-{target} - skipping")
            return True
        return False
    
    async def _rate_limit_handler(self, attempt: int = 0) -> None:
        """Handle rate limiting with exponential backoff"""
        if attempt == 0:
            log.warning(f"Rate limit hit. Waiting {RATE_LIMIT} seconds...")
            await asyncio.sleep(RATE_LIMIT)
        else:
            backoff_delay = BASE_DELAY * (BACKOFF_FACTOR ** attempt)
            total_delay = RATE_LIMIT + backoff_delay
            log.warning(f"Rate limit hit again (attempt {attempt + 1}). Waiting {total_delay:.1f} seconds...")
            await asyncio.sleep(total_delay)
    
    async def _execute_with_retry_and_rate_limit(self, operation, *args, **kwargs):
        """Execute operation with retry logic and rate limiting"""
        for attempt in range(MAX_RETRIES):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    await self._rate_limit_handler(attempt)
                    if attempt == MAX_RETRIES - 1:
                        raise Exception(f"Failed after {MAX_RETRIES} attempts due to rate limiting")
                else:
                    if attempt == MAX_RETRIES - 1:
                        raise e
                    log.warning(f"Attempt {attempt + 1} failed: {e}")
    
    def _get_cache_record_and_endpoint(self, disease: str, target: str) -> Tuple[Any, str]:
        """Get cache record and appropriate endpoint"""
        normalized_disease = normalize_disease_and_target_name(disease)
        
        if target != "no-target":
            normalized_target = normalize_disease_and_target_name(target)
            record = self.db.query(TargetDisease).filter_by(
                id=f"{normalized_target}-{normalized_disease}"
            ).first()
            endpoint = TARGET_LITERATURE_ENDPOINT
        else:
            record = self.db.query(Disease).filter_by(id=normalized_disease).first()
            endpoint = LITERATURE_ENDPOINT
        
        return record, endpoint
    
    def _load_literature_from_cache(self, record: Any, endpoint: str) -> List[Dict[str, Any]]:
        """Load literature data from cached files"""
        if not record:
            return []
        
        cache_data = load_response_from_file(record.file_path)
        literature_endpoint = cache_data.get(endpoint, {})
        literature_list = literature_endpoint.get("literature", [])
        
        log.info(f"Loaded {len(literature_list)} literature entries from cache")
        return literature_list
    
    async def _finalize_extraction(self, disease: str, target: str, successful: int, 
                                 errors: int, processed: int) -> bool:
        """Handle extraction completion logic"""
        log.info(f"Literature extraction completed. Results: {processed} processed, {successful} successful, {errors} errors")
        
        if successful > 0:
            await create_pipeline_status(disease, target, "extraction", "completed")
            return True
        else:
            await self._log_and_handle_error(
                disease, target, 
                f"Extraction failed: {errors} errors, {successful} successes"
            )
            return False
    
    # -----------------------------
    # Core Processing Methods
    # -----------------------------
    
    async def _process_pmids_to_articles(self, 
                                   pmid_title_pairs: List[Dict[str, str]],
                                   disease: str, 
                                   target: str) -> Tuple[int, int, int]:
        """
        Process PMID-title pairs: convert to PMCIDs, fetch content, store in database
        Updated to use the new combined pmids_to_full_texts method with proper delays:
        - 0.2 seconds between PMID to PMCID conversions
        - Proper delay for PMC full text API calls (handled in PMIDConverter)
        """
        processed_count = success_count = error_count = 0
        pmids = [pair["pmid"] for pair in pmid_title_pairs]
        
        # Create title mapping for easy lookup
        pmid_to_title = {pair["pmid"]: pair["title"] for pair in pmid_title_pairs}

        async with PMIDConverter() as converter:
            # Use the new combined method to get PMCIDs and full texts in one operation
            # This method handles all the proper delays internally:
            # - 0.2 seconds between PMID to PMCID conversions
            # - 0.2 seconds between PMC full text fetches
            log.info(f"Converting {len(pmids)} PMIDs to PMCIDs and fetching full texts with proper rate limiting")
            
            try:
                pmid_results = await self._execute_with_retry_and_rate_limit(
                    converter.pmids_to_full_texts, pmids
                )
                
                # Process each result
                for pmid, result_data in pmid_results.items():
                    try:
                        processed_count += 1
                        title = pmid_to_title.get(pmid, "Unknown Title")
                        
                        log.info(f"Processing PMID {pmid} ({processed_count}/{len(pmids)})")
                        
                        pmcid = result_data.get('pmcid')
                        full_text = result_data.get('full_text')
                        pmc_url = result_data.get('url')
                        
                        if not pmcid:
                            log.debug(f"No PMCID found for PMID {pmid} - skipping")
                            continue
                        
                        if not full_text or not full_text.strip():
                            log.debug(f"No full text content retrieved for PMCID {pmcid} - skipping")
                            continue
                        
                        # Store article
                        success = self.storage.store_article(
                            disease=disease, pmid=pmid, pmcid=pmcid, title=title,
                            url=pmc_url, raw_full_text=full_text, target=target
                        )
                        
                        if success:
                            success_count += 1
                            log.debug(f"Successfully stored article PMID {pmid} with title: {title[:50]}...")
                        else:
                            error_count += 1
                            error_msg = f"LITERATURE EXTRACTOR: Failed to store article PMID {pmid}"
                            log.error(msg, exc_info=True)
                            raise RuntimeError(msg) from e
                            
                    except Exception as e:
                        error_count += 1
                        error_msg = f"LITERATURE EXTRACTOR: Error processing PMID {pmid}: {e}"
                        log.error(msg, exc_info=True)
                        raise RuntimeError(msg) from e

            except Exception as e:
                error_count = len(pmids)
                msg = f"LITERATURE EXTRACTOR: Error in combined PMID processing (count={error_count}, pmids={pmids}): {e}"
                log.error(msg, exc_info=True)
                raise RuntimeError(msg) from e

        return processed_count, success_count, error_count

    # -----------------------------
    # Main Extraction Method
    # -----------------------------
    
    async def extract_literature_for_disease(self, disease: str, target: Optional[str] = None) -> bool:
        """Main function that orchestrates the literature extraction process"""
        try:
            disease_value, target_value = self._get_disease_target_values(disease, target)
            log.info(f"Starting literature extraction for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")

            # Check if pipeline is already completed
            if await self._check_pipeline_completion(disease_value, target_value):
                return True

            # Get cache record and load literature data
            record, endpoint = self._get_cache_record_and_endpoint(disease, target)
            if not record:
                return await self._log_and_handle_error(
                    disease_value, target_value, "No cache record found"
                )

            literature_data = self._load_literature_from_cache(record, endpoint)
            if not literature_data:
                return await self._log_and_handle_error(
                    disease_value, target_value, "No literature data found in cache"
                )

            # Get top PMID-title pairs
            pmid_title_pairs = get_top_n_literature(literature_data, MAX_PMIDS_TO_PROCESS)
            if not pmid_title_pairs:
                return await self._log_and_handle_error(
                    disease_value, target_value, "No valid PMIDs found in literature data"
                )

            log.info(f"Processing {len(pmid_title_pairs)} PMID-title pairs")

            # Process PMID-title pairs with proper rate limiting
            processed, successful, errors = await self._process_pmids_to_articles(
                pmid_title_pairs, disease_value, target_value
            )

            # Finalize extraction
            return await self._finalize_extraction(disease_value, target_value, successful, errors, processed)

        except Exception as e:
            disease_value, target_value = self._get_disease_target_values(disease, target)
            return await self._log_and_handle_error(
                disease_value, target_value, "Exception during extraction", e
            )

    async def extract_literature_batch(self, diseases: List[str], target: Optional[str] = None) -> Dict[str, bool]:
        """Extract literature for multiple diseases with delays between diseases"""
        results = {}

        for i, disease in enumerate(diseases, 1):
            try:
                log.info(f"Processing disease {i}/{len(diseases)}: {disease}")
                success = await self.extract_literature_for_disease(disease, target)
                results[disease] = success
                
                # Add delay between diseases
                if i < len(diseases):
                    delay = get_random_latency(10, 15)
                    log.info(f"Waiting {delay:.1f}s before processing next disease...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                log.error(f"Error processing disease {disease}: {e}")
                results[disease] = False

        successful_count = sum(1 for success in results.values() if success)
        log.info(f"Batch processing complete: {successful_count}/{len(diseases)} successful")
        return results
    
    def get_extraction_summary(self, disease: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of extraction results"""
        disease_value, target_value = self._get_disease_target_values(disease, target)
        
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