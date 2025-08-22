#!/usr/bin/env python3
"""
Simple Gene Validator - NCBI HGNC Approved Gene Names
Enhanced with robust retry mechanism for API calls
"""

import os
import requests
import time
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
import logging
from ..retry_decorators import sync_api_retry, PipelineStopException, ContinueToNextRecordException

load_dotenv()
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
logger = logging.getLogger(module_name)

class GeneValidator:
    """Simple gene validator using NCBI API with retry mechanism"""
    
    def __init__(self):
        self.api_key = os.getenv("NCBI_API_KEY")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    @sync_api_retry(max_retries=3, base_delay=1.0, backoff_multiplier=2.0)
    def _call_ncbi_search_api(self, gene_name: str) -> dict:
        """
        Wrapped NCBI search API call with retry mechanism
        This is the core API call that will be retried
        """
        query = f'(\"{gene_name}\"[Gene Full Name] OR \"{gene_name}\"[Protein Full Name] OR \"{gene_name}\"[Preferred Symbol]) AND (\"homo sapiens\"[Organism]) AND alive[prop]'
        
        search_params = {
            "db": "gene",
            "term": query,
            "retmode": "json",
            "retmax": "5"
        }
        if self.api_key:
            search_params["api_key"] = self.api_key

        try:
            logger.debug(f"Making NCBI search API call for gene: {gene_name}")
            
            response = requests.get(
                f"{self.base_url}/esearch.fcgi", 
                params=search_params, 
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout as e:
            # Convert to requests timeout for consistent handling
            raise requests.exceptions.Timeout(f"NCBI search timeout for gene {gene_name}") from e
        except requests.exceptions.HTTPError as e:
            # Re-raise HTTP errors for retry handling
            raise
        except Exception as e:
            # Convert other exceptions to RequestException for consistent handling
            raise requests.exceptions.RequestException(f"NCBI search error for gene {gene_name}: {str(e)}") from e

    @sync_api_retry(max_retries=3, base_delay=1.0, backoff_multiplier=2.0)
    def _call_ncbi_details_api(self, gene_id: str, gene_name: str) -> dict:
        """
        Wrapped NCBI details API call with retry mechanism
        This is the core API call that will be retried
        """
        details_params = {
            "db": "gene", 
            "id": gene_id,
            "retmode": "json"
        }
        if self.api_key:
            details_params["api_key"] = self.api_key

        try:
            logger.debug(f"Making NCBI details API call for gene ID: {gene_id}")
            
            response = requests.get(
                f"{self.base_url}/esummary.fcgi", 
                params=details_params, 
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout as e:
            # Convert to requests timeout for consistent handling
            raise requests.exceptions.Timeout(f"NCBI details timeout for gene {gene_name} (ID: {gene_id})") from e
        except requests.exceptions.HTTPError as e:
            # Re-raise HTTP errors for retry handling
            raise
        except Exception as e:
            # Convert other exceptions to RequestException for consistent handling
            raise requests.exceptions.RequestException(f"NCBI details error for gene {gene_name}: {str(e)}") from e
    
    def validate_single_gene(self, gene_name: str) -> Optional[str]:
        """
        Validate a single gene and return official HGNC symbol if valid
        Enhanced with retry mechanism and proper exception handling
        """
        if not gene_name or not gene_name.strip():
            return None
            
        gene_name = gene_name.strip()
        
        try:
            # Use retry-wrapped search API call
            time.sleep(0.4)  # NCBI rate limit
            search_result = self._call_ncbi_search_api(gene_name)
            
            gene_ids = search_result.get("esearchresult", {}).get("idlist", [])
            if not gene_ids:
                logger.debug(f"No gene IDs found for: {gene_name}")
                return None
                
            # Use retry-wrapped details API call
            time.sleep(0.4)  # NCBI rate limit
            details_result = self._call_ncbi_details_api(gene_ids[0], gene_name)
            
            gene_details = details_result.get("result", {}).get(gene_ids[0], {})
            official_symbol = gene_details.get("name", "").strip() if gene_details else None
            
            if official_symbol:
                logger.debug(f"Successfully validated gene: {gene_name} -> {official_symbol}")
            else:
                logger.debug(f"No official symbol found for gene: {gene_name}")
                
            return official_symbol
                
        except ContinueToNextRecordException:
            # NCBI timeout errors - continue with gene validation but log the failure
            logger.warning(f"NCBI API timeout for gene {gene_name} after retries - skipping this gene")
            return None
            
        except PipelineStopException as e:
            # Critical NCBI errors - stop the entire pipeline
            logger.error(f"NCBI gene validation failed critically for {gene_name}: {str(e)}")
            raise RuntimeError(f"NCBI gene validation failed: {str(e)}") from e
                        
        except Exception as e:
            # Unexpected errors - also stop pipeline for safety
            logger.error(f"Unexpected NCBI gene validation error for {gene_name}: {str(e)}")
            raise RuntimeError(f"Unexpected NCBI gene validation error: {str(e)}") from e
    
    def validate_genes_from_text(self, genes_text: str, delay: float = 1.5) -> str:
        """
        Parse and validate genes from text, return comma-separated valid genes
        Enhanced with proper exception handling for pipeline errors
        
        Args:
            genes_text: Text containing gene names to validate
            delay: Delay between gene validation calls
            
        Returns:
            Comma-separated string of valid gene symbols
            
        Raises:
            RuntimeError: For critical errors that should stop the pipeline
        """
        if not genes_text or genes_text.lower().strip() in ["not mentioned", "none", "", "n/a"]:
            return "not mentioned"
            
        # Parse genes from text
        genes = []
        for delimiter in [",", ";", "|", "\n", "\t"]:
            genes_text = genes_text.replace(delimiter, ",")
        
        for gene in genes_text.split(","):
            gene = gene.strip().strip('"\'')
            if gene and len(gene) > 1 and gene.lower() not in ["and", "or", "the", "a", "an"]:
                genes.append(gene)
        
        if not genes:
            return "not mentioned"
            
        # Validate each gene with delay and proper error handling
        valid_genes = []
        for i, gene in enumerate(genes):
            logger.debug(f"Validating gene {i+1}/{len(genes)}: {gene}")
            
            try:
                valid_symbol = self.validate_single_gene(gene)
                if valid_symbol:
                    valid_genes.append(valid_symbol)
                    logger.debug(f"✓ Valid: {gene} -> {valid_symbol}")
                else:
                    logger.debug(f"✗ Invalid: {gene}")
                
                # Delay between genes (except last)
                if i < len(genes) - 1:
                    time.sleep(delay)
                    
            except RuntimeError:
                # Re-raise pipeline stopping errors
                raise
            except Exception as e:
                logger.error(f"Error validating gene {gene}: {str(e)}")
                # For unexpected errors in gene validation, stop the pipeline
                raise RuntimeError(f"Gene validation failed for gene {gene}: {str(e)}") from e
        
        return ", ".join(sorted(set(valid_genes))) if valid_genes else "not mentioned"

# Simple async wrapper with proper exception handling
async def validate_genes_async(genes_text: str, delay: float = 1.5) -> str:
    """
    Async version of gene validation with proper exception handling
    
    Args:
        genes_text: Text containing gene names to validate
        delay: Delay between gene validation calls
        
    Returns:
        Comma-separated string of valid gene symbols
        
    Raises:
        RuntimeError: For critical errors that should stop the pipeline
    """
    try:
        validator = GeneValidator()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, validator.validate_genes_from_text, genes_text, delay)
        
    except RuntimeError:
        # Re-raise pipeline stopping errors
        raise
    except Exception as e:
        # Unexpected errors in async wrapper - also stop pipeline
        raise RuntimeError(f"Async gene validation failed: {str(e)}") from e