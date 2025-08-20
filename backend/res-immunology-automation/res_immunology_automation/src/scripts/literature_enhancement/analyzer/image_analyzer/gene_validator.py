#!/usr/bin/env python3
"""
Simple Gene Validator - NCBI HGNC Approved Gene Names
"""

import os
import requests
import time
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
import logging

load_dotenv()
module_name = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(module_name)

class GeneValidator:
    """Simple gene validator using NCBI API"""
    
    def __init__(self):
        self.api_key = os.getenv("NCBI_API_KEY")
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def validate_single_gene(self, gene_name: str) -> Optional[str]:
        """Validate a single gene and return official HGNC symbol if valid"""
        if not gene_name or not gene_name.strip():
            return None
            
        gene_name = gene_name.strip()
        
        try:
            # Search for gene
            query = f'(\"{gene_name}\"[Gene Full Name] OR \"{gene_name}\"[Protein Full Name] OR \"{gene_name}\"[Preferred Symbol]) AND (\"homo sapiens\"[Organism]) AND alive[prop]'
            
            search_params = {
                "db": "gene",
                "term": query,
                "retmode": "json",
                "retmax": "5"
            }
            if self.api_key:
                search_params["api_key"] = self.api_key
                
            time.sleep(0.4)  # NCBI rate limit
            response = requests.get(f"{self.base_url}/esearch.fcgi", params=search_params, timeout=10)
            response.raise_for_status()
            
            gene_ids = response.json().get("esearchresult", {}).get("idlist", [])
            if not gene_ids:
                return None
                
            # Get gene details
            details_params = {
                "db": "gene", 
                "id": gene_ids[0],
                "retmode": "json"
            }
            if self.api_key:
                details_params["api_key"] = self.api_key
                
            time.sleep(0.4)  # NCBI rate limit
            response = requests.get(f"{self.base_url}/esummary.fcgi", params=details_params, timeout=10)
            response.raise_for_status()
            
            gene_details = response.json().get("result", {}).get(gene_ids[0], {})
            return gene_details.get("name", "").strip() if gene_details else None
                
        except Exception as e:
            logger.debug(f"Error validating gene {gene_name}: {str(e)}")
            return None
    
    def validate_genes_from_text(self, genes_text: str, delay: float = 1.5) -> str:
        """Parse and validate genes from text, return comma-separated valid genes"""
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
            
        # Validate each gene with delay
        valid_genes = []
        for i, gene in enumerate(genes):
            logger.debug(f"Validating gene {i+1}/{len(genes)}: {gene}")
            
            valid_symbol = self.validate_single_gene(gene)
            if valid_symbol:
                valid_genes.append(valid_symbol)
                logger.debug(f"✓ Valid: {gene} -> {valid_symbol}")
            else:
                logger.debug(f"✗ Invalid: {gene}")
            
            # Delay between genes (except last)
            if i < len(genes) - 1:
                time.sleep(delay)
        
        return ", ".join(sorted(set(valid_genes))) if valid_genes else "not mentioned"

# Simple async wrapper
async def validate_genes_async(genes_text: str, delay: float = 1.5) -> str:
    """Async version of gene validation"""
    validator = GeneValidator()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, validator.validate_genes_from_text, genes_text, delay)