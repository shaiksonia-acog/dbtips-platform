"""
Literature Enhancement Services Module
Handles literature table analysis and supplementary materials data fetching and processing
"""
from sqlalchemy.orm import Session
from db.models import LiteratureTablesAnalysis, LiteratureSupplementaryMaterialsAnalysis
from typing import List, Dict, Any, Optional
import logging


def fetch_literature_table_analysis(targets: Optional[List[str]] = None, 
                                   diseases: Optional[List[str]] = None, 
                                   db: Session = None) -> List[Dict[str, Any]]:
    """
    Fetch literature table analysis data based on targets and/or diseases
    
    Args:
        targets (Optional[List[str]]): List of target names
        diseases (Optional[List[str]]): List of disease names
        db (Session): Database session
        
    Returns:
        List[Dict[str, Any]]: List of literature table analysis records
    """
    try:
        # Start with base query
        query = db.query(LiteratureTablesAnalysis)
        
        # Apply filters based on provided parameters
        filters = []
        
        if targets and targets != ["no-target"]:
            # Convert targets to lowercase
            target_filters = [target.strip().lower() for target in targets]
            filters.append(LiteratureTablesAnalysis.target.in_(target_filters))
        
        if diseases and diseases != ["no-disease"]:
            # Convert diseases to lowercase and replace spaces with underscores
            disease_filters = [disease.strip().lower().replace(" ", "_") for disease in diseases]
            filters.append(LiteratureTablesAnalysis.disease.in_(disease_filters))
        
        # Apply all filters
        if filters:
            query = query.filter(*filters)
        
        records = query.all()
        
        # Convert to dictionary format with only required fields
        results = []
        for record in records:
            result_dict = {
                "pmid": record.pmid,
                "url": record.url,
                "pmcid": record.pmcid,
                "table_description": record.table_description,
                "analysis": record.analysis,
                "keywords": record.keywords
            }
            results.append(result_dict)
        
        filter_info = f"targets: {targets}, diseases: {diseases}"
        logging.info(f"Found {len(results)} literature table analysis records for {filter_info}")
        return results
        
    except Exception as e:
        logging.error(f"Error fetching literature table analysis: {e}")
        raise e


def fetch_literature_supplementary_materials_analysis(targets: Optional[List[str]] = None, 
                                                     diseases: Optional[List[str]] = None, 
                                                     db: Session = None) -> List[Dict[str, Any]]:
    """
    Fetch literature supplementary materials analysis data based on targets and/or diseases
    
    Args:
        targets (Optional[List[str]]): List of target names
        diseases (Optional[List[str]]): List of disease names
        db (Session): Database session
        
    Returns:
        List[Dict[str, Any]]: List of literature supplementary materials analysis records
    """
    try:
        # Start with base query
        query = db.query(LiteratureSupplementaryMaterialsAnalysis)
        
        # Apply filters based on provided parameters
        filters = []
        
        if targets and targets != ["no-target"]:
            # Convert targets to lowercase
            target_filters = [target.strip().lower() for target in targets]
            filters.append(LiteratureSupplementaryMaterialsAnalysis.target.in_(target_filters))
        
        if diseases and diseases != ["no-disease"]:
            # Convert diseases to lowercase and replace spaces with underscores
            disease_filters = [disease.strip().lower().replace(" ", "_") for disease in diseases]
            filters.append(LiteratureSupplementaryMaterialsAnalysis.disease.in_(disease_filters))
        
        # Apply all filters
        if filters:
            query = query.filter(*filters)
        
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
        
        filter_info = f"targets: {targets}, diseases: {diseases}"
        logging.info(f"Found {len(results)} literature supplementary materials analysis records for {filter_info}")
        return results
        
    except Exception as e:
        logging.error(f"Error fetching literature supplementary materials analysis: {e}")
        raise e