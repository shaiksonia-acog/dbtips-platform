"""
PMID to PMCID conversion utilities using NCBI E-utilities with improved rate limiting
Updated with enhanced logging for PMIDs without PMCIDs
"""
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set
import aiohttp

from .config import NCBI_API_KEY, NCBI_EMAIL, NCBI_BASE_URL
from .lit_utils import get_random_latency, retry_with_backoff

log = logging.getLogger(__name__)


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