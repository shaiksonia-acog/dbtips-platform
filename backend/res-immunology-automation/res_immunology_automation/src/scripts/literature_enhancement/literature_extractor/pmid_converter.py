#pmid_converter.py
"""
PMID to PMCID conversion utilities using NCBI E-utilities with improved rate limiting
Updated with enhanced logging for PMIDs without PMCIDs
"""
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set
import aiohttp

from literature_enhancement.config import NCBI_API_KEY, NCBI_EMAIL, NCBI_BASE_URL
from .lit_utils import get_random_latency, retry_with_backoff
import os
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


class PMIDConverter:
    """Handles conversion of PMIDs to PMCIDs using NCBI E-utilities"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = NCBI_BASE_URL
        self.api_key = NCBI_API_KEY
        self.email = NCBI_EMAIL
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _build_eutils_params(self, **kwargs) -> Dict[str, str]:
        """Build common E-utilities parameters"""
        params = {
            'email': self.email,
            'tool': 'literature_extractor'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        params.update(kwargs)
        return params
    
    @retry_with_backoff(max_retries=3)
    async def _make_request(self, url: str, params: Dict[str, str]) -> str:
        """Make HTTP request with error handling"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            log.error(f"Request failed for URL {url} with params {params}: {e}")
            raise
    
    async def pmid_to_pmcid(self, pmid: str) -> Optional[str]:
        """
        Convert a single PMID to PMCID using pubmed_pmc linkname
    
        Args:
            pmid: PubMed ID
        
        Returns:
            PMC ID if available, None otherwise
        """
        url = f"{self.base_url}/elink.fcgi"
        params = self._build_eutils_params(
            dbfrom='pubmed',
            linkname='pubmed_pmc',
            id=pmid,
            retmode='xml'
        )
    
        try:
            response_text = await self._make_request(url, params)
            root = ET.fromstring(response_text)
        
            # Look for PMC links with the specific linkname
            for link_set in root.findall('.//LinkSet'):
                for link_set_db in link_set.findall('.//LinkSetDb'):
                    link_name = link_set_db.find('LinkName')
                    if link_name is not None and link_name.text == 'pubmed_pmc':
                        pmc_ids = link_set_db.findall('.//Id')
                        if pmc_ids:
                            pmc_id = pmc_ids[0].text
                            log.debug(f"✓ Converted PMID {pmid} to PMCID {pmc_id}")
                            return pmc_id
        
            log.debug(f"✗ No PMCID found for PMID {pmid}")
            return None
        
        except Exception as e:
            log.warning(f"Failed to convert PMID {pmid} to PMCID: {e}")
            return None

    async def pmids_to_pmcids(self, pmids: List[str]) -> Dict[str, Optional[str]]:
        """
        Convert multiple PMIDs to PMCIDs 
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            Dictionary mapping PMIDs to PMCIDs (None if not available)
        """
        results = {}
        pmids_without_pmcid = []
        
        for pmid in pmids:
            
            results[pmid] = await self.pmid_to_pmcid(pmid)            
            await asyncio.sleep(0.2)
        
        successful_conversions = sum(1 for v in results.values() if v is not None)
        pmids_without_pmcid = sum(1 for v in results.values() if v is None)
        # Log summary with PMIDs without PMCIDs
        log.info(f"PMCID Conversion Summary:")
        log.info(f"  - Successfully converted: {successful_conversions}/{len(pmids)} PMIDs")
        log.info(f"  - PMIDs without PMCIDs: {pmids_without_pmcid}/{len(pmids)}")
        
        return results
    
    async def get_pmc_full_text(self, pmcid: str) -> Optional[str]:
        """
        Fetch full text XML from PMC with retry logic for rate limits
        
        Args:
            pmcid: PMC ID (with or without PMC prefix)
            
        Returns:
            XML content as string, None if failed
        """
        # Ensure PMC prefix
        if not pmcid.startswith('PMC'):
            pmcid = f'PMC{pmcid}'
        
        url = f"{self.base_url}/efetch.fcgi"
        params = self._build_eutils_params(
            db='pmc',
            id=pmcid,
            retmode='xml'
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response_text = await self._make_request(url, params)
                
                # Basic validation that we got XML content
                if response_text and response_text.strip().startswith('<'):
                    log.debug(f"✓ Successfully fetched full text for {pmcid}")
                    return response_text
                else:
                    log.warning(f"✗ Invalid or empty response for {pmcid}")
                    return None
                    
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    if attempt < max_retries - 1:
                        # For rate limit errors, wait longer before retry
                        retry_delay = get_random_latency(10, 15)
                        log.warning(f"Rate limit hit for {pmcid}, waiting {retry_delay:.1f}s before retry {attempt + 2}/{max_retries}")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        log.error(f"Rate limit exceeded for {pmcid} after {max_retries} attempts")
                        return None
                else:
                    log.warning(f"Failed to fetch full text for {pmcid}: {e}")
                    return None
        
        return None
    
    async def get_pmc_url(self, pmcid: str) -> str:
        """
        Generate PMC URL for given PMCID
        
        Args:
            pmcid: PMC ID
            
        Returns:
            PMC URL
        """
        if not pmcid.startswith('PMC'):
            pmcid = f'PMC{pmcid}'
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"

    async def pmids_to_full_texts(self, pmids: List[str]) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Convert multiple PMIDs to PMCIDs and fetch their full text XML in one operation
        
        Args:
            pmids: List of PubMed IDs
            
        Returns:
            Dictionary mapping PMIDs to:
            {
                'pmcid': Optional[str],     # PMCID if available, None otherwise
                'full_text': Optional[str], # Full text XML if available, None otherwise
                'url': Optional[str]        # PMC URL if PMCID available, None otherwise
            }
        """
        results = {}
        conversion_stats = {'converted': 0, 'no_pmcid': 0, 'full_text_fetched': 0, 'no_full_text': 0}
        
        # Step 1: Convert all PMIDs to PMCIDs first
        log.info(f"Starting PMCID conversion for {len(pmids)} PMIDs...")
        pmcid_mapping = {}
        
        for pmid in pmids:
            pmcid = await self.pmid_to_pmcid(pmid)
            pmcid_mapping[pmid] = pmcid
            
            if pmcid:
                conversion_stats['converted'] += 1
            else:
                conversion_stats['no_pmcid'] += 1
                
            await asyncio.sleep(0.2)  # Rate limiting between conversions
        
        log.info(f"PMCID Conversion Summary:")
        log.info(f"  - PMCIDs Availability: {conversion_stats['converted']}/{len(pmids)} PMIDs")
        log.info(f"  - PMIDs without PMCIDs: {conversion_stats['no_pmcid']}/{len(pmids)}")
        
        # Step 2: Fetch full text for PMCIDs that were successfully converted
        log.info(f"Starting full text retrieval for {conversion_stats['converted']} PMCIDs...")
        
        for pmid, pmcid in pmcid_mapping.items():
            result_entry = {
                'pmcid': pmcid,
                'full_text': None,
                'url': None
            }
            
            if pmcid:
                # Generate URL
                result_entry['url'] = await self.get_pmc_url(pmcid)
                
                # Fetch full text
                full_text = await self.get_pmc_full_text(pmcid)
                result_entry['full_text'] = full_text
                
                if full_text:
                    conversion_stats['full_text_fetched'] += 1
                    log.debug(f"✓ Successfully fetched full text for PMID {pmid} -> PMCID {pmcid}")
                else:
                    conversion_stats['no_full_text'] += 1
                    log.debug(f"✗ No full text available for PMID {pmid} -> PMCID {pmcid}")
                
                # Rate limiting between full text requests
                await asyncio.sleep(0.2)
            
            results[pmid] = result_entry
        
        # Final summary
        log.info(f"Full Text Retrieval Summary:")
        log.info(f"  - Full text retrieved: {conversion_stats['full_text_fetched']}/{conversion_stats['converted']} PMCIDs")
        log.info(f"  - PMCIDs without full text: {conversion_stats['no_full_text']}/{conversion_stats['converted']}")
        log.info(f"Overall Success Rate: {conversion_stats['full_text_fetched']}/{len(pmids)} ({conversion_stats['full_text_fetched']/len(pmids)*100:.1f}%) PMIDs with full text")
        
        return results


# Convenience functions for backward compatibility
# async def pubmed_to_pmc(pmid: str) -> Optional[str]:
#     """
#     Convert single PMID to PMCID (convenience function)
    
#     Args:
#         pmid: PubMed ID
        
#     Returns:
#         PMC ID if available, None otherwise
#     """
#     async with PMIDConverter() as converter:
#         return await converter.pmid_to_pmcid_single(pmid)


# async def fetch_pmc_content(pmcid: str) -> Optional[str]:
#     """
#     Fetch PMC full text content (convenience function)
    
#     Args:
#         pmcid: PMC ID
        
#     Returns:
#         XML content as string, None if failed
#     """
#     async with PMIDConverter() as converter:
#         return await converter.get_pmc_full_text(pmcid)



# async def fetch_full_texts_from_pmids(self, pmids: List[str]) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
#     """
#     Convenience function: Convert PMIDs to PMCIDs and fetch full texts
    
#     Args:
#         pmids: List of PubMed IDs
        
#     Returns:
#         Dictionary mapping PMID -> (PMCID, full text XML)
#         - PMCID is None if not available
#         - full text is None if not available
#     """
#     results: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

#     # Step 1: Convert PMIDs → PMCIDs
#     pmid_to_pmcid = await self.pmids_to_pmcids(pmids)

#     # Step 2: Fetch full text for each PMCID
#     for pmid, pmcid in pmid_to_pmcid.items():
#         if not pmcid:
#             results[pmid] = (None, None)
#             continue

#         full_text = await self.get_pmc_full_text(pmcid)
#         results[pmid] = (pmcid, full_text)

#         # Respect API rate limits
#         await asyncio.sleep(0.2)

#     return results
