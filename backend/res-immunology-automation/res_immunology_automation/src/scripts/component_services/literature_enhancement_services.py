#literature_enhancement_services.py
"""
Literature Enhancement Services Module
Handles literature table analysis and supplementary materials data fetching and processing
"""
from sqlalchemy.orm import Session
from db.models import LiteratureTablesAnalysis, LiteratureSupplementaryMaterialsAnalysis
from typing import List, Dict, Any, Optional
import logging
import json


def fetch_literature_table_analysis(target: str = None, 
                                   diseases: Optional[List[str]] = None, 
                                   db: Session = None) -> List[Dict[str, Any]]:
    """
    Fetch literature table analysis data based on target and/or diseases with exact matching
    
    Args:
        target (str): Single target name
        diseases (Optional[List[str]]): List of disease names
        db (Session): Database session
        
    Returns:
        List[Dict[str, Any]]: List of literature table analysis records
    """
    try:
        # Start with base query
        query = db.query(LiteratureTablesAnalysis)
        
        # Apply exact matching logic - query separate columns
        # Always filter by target column
        target_filter = target.strip().lower()
        query = query.filter(LiteratureTablesAnalysis.target == target_filter)
        
        # Always filter by disease column
        if diseases and len(diseases) == 1:
            # Single disease - use exact match
            disease_filter = diseases[0].strip().lower()
            query = query.filter(LiteratureTablesAnalysis.disease == disease_filter)
        elif diseases and len(diseases) > 1:
            # Multiple diseases - use IN clause
            disease_filters = [disease.strip().lower() for disease in diseases]
            query = query.filter(LiteratureTablesAnalysis.disease.in_(disease_filters))
        else:
            # No diseases specified - this shouldn't happen in our use case
            pass
        
        records = query.all()
        
        # Convert to dictionary format with only required fields
        results = []
        for record in records:
            # Extract table title from table_schema
            table_title = ""
            if record.table_schema:
                try:
                    # Parse table_schema JSON to extract title
                    table_schema = json.loads(record.table_schema) if isinstance(record.table_schema, str) else record.table_schema
                    table_title = table_schema.get("title", "")
                except (json.JSONDecodeError, AttributeError) as e:
                    logging.warning(f"Error parsing table_schema for PMID {record.pmid}: {e}")
                    table_title = ""
            
            # Combine table title with analysis
            enhanced_analysis = record.analysis
            if table_title:
                enhanced_analysis = f"{table_title} | {record.analysis}"
            
            result_dict = {
                "pmid": record.pmid,
                "url": record.url,
                "pmcid": record.pmcid,
                "table_description": record.table_description,
                "analysis": enhanced_analysis,
                "keywords": record.keywords
            }
            results.append(result_dict)
        
        filter_info = f"target: {target}, diseases: {diseases}"
        # print(f"Found {len(results)} literature table analysis records for {filter_info}")
        return results
        
    except Exception as e:
        logging.error(f"Error fetching literature table analysis: {e}")
        raise e


def fetch_literature_supplementary_materials_analysis(target: str = None, 
                                                     diseases: Optional[List[str]] = None, 
                                                     db: Session = None) -> List[Dict[str, Any]]:
    """
    Fetch literature supplementary materials analysis data based on target and/or diseases with exact matching
    
    Args:
        target (str): Single target name
        diseases (Optional[List[str]]): List of disease names
        db (Session): Database session
        
    Returns:
        List[Dict[str, Any]]: List of literature supplementary materials analysis records
    """
    try:
        # Start with base query
        query = db.query(LiteratureSupplementaryMaterialsAnalysis)
        
        # Apply exact matching logic - query separate columns
        # Always filter by target column
        target_filter = target.strip().lower()
        query = query.filter(LiteratureSupplementaryMaterialsAnalysis.target == target_filter)
        
        # Always filter by disease column
        if diseases and len(diseases) == 1:
            # Single disease - use exact match
            disease_filter = diseases[0].strip().lower()
            query = query.filter(LiteratureSupplementaryMaterialsAnalysis.disease == disease_filter)
        elif diseases and len(diseases) > 1:
            # Multiple diseases - use IN clause
            disease_filters = [disease.strip().lower() for disease in diseases]
            query = query.filter(LiteratureSupplementaryMaterialsAnalysis.disease.in_(disease_filters))
        else:
            # No diseases specified - this shouldn't happen in our use case
            pass
        
        records = query.all()
        
        # Convert to dictionary format with only required fields
        results = []
        for record in records:
            result_dict = {
                "pmid": record.pmid,
                "pmcid": record.pmcid,
                "url": record.url,
                "analysis": record.analysis,
                "keywords": record.keywords,
                "description": record.description
            }
            results.append(result_dict)
        
        filter_info = f"target: {target}, diseases: {diseases}"
        # print(f"Found {len(results)} literature supplementary materials analysis records for {filter_info}")
        return results
        
    except Exception as e:
        logging.error(f"Error fetching literature supplementary materials analysis: {e}")
        raise e