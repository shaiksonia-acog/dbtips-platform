"""
Main literature extraction orchestrator with improved rate limiting
Updated to use new schema and handle default values
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from db.models import Disease, TargetDisease
from .config import (
    LITERATURE_ENDPOINT, TARGET_LITERATURE_ENDPOINT, 
    MAX_PMIDS_TO_PROCESS, FIGURE_ANALYSIS_ENDPOINT
)
from .lit_utils import (
    get_top_100_pmids,
    normalize_disease_name, normalize_target_name, get_random_latency
)
from utils import load_response_from_file, save_response_to_file
from .pmid_converter import PMIDConverter
from .data_storage import LiteratureStorage

log = logging.getLogger(__name__)


class LiteratureExtractor:
    """Main class for orchestrating literature extraction process"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.storage = LiteratureStorage(db_session)
    
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
    
    def _should_skip_extraction(self, disease: str, target: Optional[str] = None) -> bool:
        """
        Check if extraction should be skipped (already completed)
        
        Args:
            disease: Disease name
            target: Target name (optional)
            
        Returns:
            True if should skip, False otherwise
        """
        normalized_disease = normalize_disease_name(disease)
        
        if target:
            normalized_target = normalize_target_name(target)
            record = self.db.query(TargetDisease).filter_by(
                id=f"{normalized_target}-{normalized_disease}"
            ).first()
        else:
            record = self.db.query(Disease).filter_by(id=normalized_disease).first()
        
        if not record:
            return False
        
        cache_data = load_response_from_file(record.file_path)
        return FIGURE_ANALYSIS_ENDPOINT in cache_data
    
    async def _process_pmids_to_articles(self, 
                                       pmids: List[str], 
                                       disease: str, 
                                       target: Optional[str] = None) -> Tuple[int, int, int]:
        """
        Process PMIDs: convert to PMCIDs, fetch content, store in database
        
        Args:
            pmids: List of PMIDs to process
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
        
        # Track PMIDs without PMCIDs for logging
        pmids_without_pmcid = []
        
        async with PMIDConverter() as converter:
            # Convert PMIDs to PMCIDs in batches
            log.info(f"Converting {len(pmids)} PMIDs to PMCIDs")
            pmid_to_pmcid = await converter.pmids_to_pmcids_batch(pmids)
            
            # Log PMIDs without PMCIDs
            for pmid, pmcid in pmid_to_pmcid.items():
                if not pmcid:
                    pmids_without_pmcid.append(pmid)
            
            if pmids_without_pmcid:
                log.warning(f"PMIDs without PMCIDs ({len(pmids_without_pmcid)}): {', '.join(pmids_without_pmcid)}")
            
            # Process each PMID with longer delays for NCBI API
            for idx, pmid in enumerate(pmids, 1):
                try:
                    log.info(f"Processing PMID {pmid} ({idx}/{len(pmids)})")
                    processed_count += 1
                    
                    # Get PMCID
                    pmcid = pmid_to_pmcid.get(pmid)
                    if not pmcid:
                        log.debug(f"No PMCID found for PMID {pmid} - skipping (no full text available)")
                        # Don't store articles without full text capability
                        continue
                    
                    # Fetch full text content with longer delay to avoid rate limits
                    log.debug(f"Fetching full text for PMCID {pmcid}")
                    full_text = await converter.get_pmc_full_text(pmcid)
                    
                    # Only proceed if we have full text
                    if not full_text or not full_text.strip():
                        log.debug(f"No full text content retrieved for PMCID {pmcid} - skipping")
                        continue
                    
                    pmc_url = await converter.get_pmc_url(pmcid)
                    
                    # Store article with full text
                    success = self.storage.store_article(
                        disease=disease_value,
                        pmid=pmid,
                        pmcid=pmcid,
                        url=pmc_url,
                        raw_full_text=full_text,
                        target=target_value
                    )
                    
                    if success:
                        success_count += 1
                        log.debug(f"Successfully stored article PMID {pmid}")
                    else:
                        error_count += 1
                        log.warning(f"Failed to store article PMID {pmid}")
                    
                    # Add longer delay between NCBI API requests (5-10 seconds)
                    if idx < len(pmids):
                        delay = get_random_latency(5, 10)  # Increased from 1-3 to 5-10 seconds
                        log.debug(f"Waiting {delay:.1f}s before next API request to respect NCBI rate limits...")
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    error_count += 1
                    log.error(f"Error processing PMID {pmid}: {e}")
                    # Even on error, add delay to avoid hammering the API
                    if idx < len(pmids):
                        delay = get_random_latency(5, 10)
                        await asyncio.sleep(delay)
        
        log.info(f"Processing complete: {processed_count} processed, {success_count} successful, {error_count} errors")
        return processed_count, success_count, error_count
    
    def _update_cache_with_extraction_status(self, disease: str, target: Optional[str] = None, 
                                           status: str = "completed") -> None:
        """
        Update cache file to indicate extraction completion
        
        Args:
            disease: Disease name
            target: Target name (optional)
            status: Extraction status
        """
        try:
            normalized_disease = normalize_disease_name(disease)
            
            # Use default values consistent with database schema
            disease_value = disease if disease else "no-disease"
            target_value = target if target else "no-target"
            
            if target:
                normalized_target = normalize_target_name(target)
                record = self.db.query(TargetDisease).filter_by(
                    id=f"{normalized_target}-{normalized_disease}"
                ).first()
            else:
                record = self.db.query(Disease).filter_by(id=normalized_disease).first()
            
            if not record:
                log.warning(f"No cache record found to update for {'target-' if target else ''}disease")
                return
            
            cache_data = load_response_from_file(record.file_path)
            cache_data[FIGURE_ANALYSIS_ENDPOINT] = {
                "status": status,
                "extraction_completed": True,
                "articles_count": self.storage.get_article_count(disease_value, target_value)
            }
            
            save_response_to_file(record.file_path, cache_data)
            log.info(f"Updated cache with extraction status: {status}")
            
        except Exception as e:
            log.error(f"Failed to update cache with extraction status: {e}")
    
    async def extract_literature_for_disease(self, disease: str, target: Optional[str] = None) -> bool:
        """
        Main function that orchestrates the literature extraction process:
        1. Load existing disease cache
        2. Extract top 100 PMIDs
        3. Convert PMIDs to PMCIDs
        4. Extract the full text as XML response via eutils utility
        5. Store the raw text along with metadata in the database table
        
        Args:
            disease: Disease name
            target: Target name (optional, for target-disease combinations)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            log.info(f"Starting literature extraction for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            
            # Check if extraction already completed
            if self._should_skip_extraction(disease, target):
                log.info(f"Literature extraction already completed for {'target-' if target else ''}disease - skipping")
                return True
            
            # Load literature data from cache
            literature_data = self._get_literature_data_from_cache(disease, target)
            
            if not literature_data:
                log.warning(f"No literature data found for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
                self._update_cache_with_extraction_status(disease, target, "no_data")
                return True
            
            # Get top PMIDs
            pmids = get_top_100_pmids(literature_data, MAX_PMIDS_TO_PROCESS)
            if not pmids:
                log.warning(f"No valid PMIDs found for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
                self._update_cache_with_extraction_status(disease, target, "no_pmids")
                return True
            
            log.info(f"Processing {len(pmids)} PMIDs for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            log.info(f"Using 5-10 second delays between API calls to respect NCBI rate limits")
            
            # Process PMIDs to articles
            processed, successful, errors = await self._process_pmids_to_articles(pmids, disease, target)
            
            # Update cache with completion status
            self._update_cache_with_extraction_status(disease, target, "completed")
            
            log.info(f"Literature extraction completed for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}")
            log.info(f"Results: {processed} processed, {successful} successful, {errors} errors")
            
            return True
            
        except Exception as e:
            log.error(f"Literature extraction failed for {'target-' if target else ''}disease: {target + '-' if target else ''}{disease}: {e}")
            self._update_cache_with_extraction_status(disease, target, "failed")
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