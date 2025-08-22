"""
Literature Processing Utilities

Shared utilities for processing literature data from NXML articles.
This module consolidates common functionality used across table, figure, 
and supplementary materials extraction modules.
"""
import os
import logging
from typing import List, Optional, Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models import ArticlesMetadata

from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)

class LiteratureProcessingUtils:
    """Common utilities for literature data processing"""
    
    @staticmethod
    def process_articles_by_filters(
        db_session: Session,
        extraction_func: Callable,
        check_existing_func: Callable,
        save_func: Callable,
        target: Optional[str] = None,
        disease: Optional[str] = None,
        batch_size: int = 50
        ) -> int:
        """
        Generic function to process articles with flexible filtering and extraction
        
        Args:
            db_session: Database session
            extraction_func: Function to extract data from article (takes article as param)
            check_existing_func: Function to check if data already exists (takes article as param)
            save_func: Function to save extracted data (takes extracted_data and db_session as params)
            target: Target name to filter articles (optional)
            disease: Disease name to filter articles (optional)
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of records extracted
        """
        
        # Fetch all metadata articles with full text
        query_conditions = [ArticlesMetadata.raw_full_text.isnot(None)]
        
        if target:
            query_conditions.append(ArticlesMetadata.target == target)
        if disease:
            query_conditions.append(ArticlesMetadata.disease == disease)
        
        # Build query
        stmt = (
            select(ArticlesMetadata)
            .where(*query_conditions)
            .limit(batch_size)
        )
        
        articles = db_session.execute(stmt).scalars().all()
        
        # Log filter info
        filter_desc = []
        if target:
            filter_desc.append(f"target: {target}")
        if disease:
            filter_desc.append(f"disease: {disease}")
        filter_str = ", ".join(filter_desc) if filter_desc else "no filters"
        
        if not articles:
            log.info(f"No articles to process for {filter_str}")
            return 0
        
        total_extracted = 0
        
        for article in articles:
            try:
                # Check if data for this article already exists
                if check_existing_func(article, db_session):
                    log.debug("Data already exists for PMID: %s, Target: %s, Disease: %s", 
                            article.pmid, article.target, article.disease)
                    continue
                
                # Extract data from the article
                extracted_data = extraction_func(article)
                
                # Save data if extraction was successful
                if extracted_data:
                    records_saved = save_func(extracted_data, db_session)
                    total_extracted += records_saved
                    
                    # Commit after each article
                    db_session.commit()
                    
                    log.info("Processed article PMID: %s for %s, extracted %d records", 
                            article.pmid, filter_str, records_saved)
                else:
                    log.debug("No data extracted for PMID: %s", article.pmid)
                
            except Exception as e:
                log.error("Error processing article PMID: %s for %s - %s", 
                         article.pmid, filter_str, e)
                db_session.rollback()
                continue
        
        log.info("Processing complete for %s. Extracted %d records from %d articles", 
                filter_str, total_extracted, len(articles))
        
        return total_extracted

    @staticmethod
    def process_articles(
        db_session: Session,
        extraction_func: Callable,
        check_existing_func: Callable,
        save_func: Callable,
        target: str,
        disease: Optional[str] = None,
        batch_size: int = 50
        ) -> int:
        """
        Process articles filtered by target and optionally disease
        
        Args:
            db_session: Database session
            extraction_func: Function to extract data from article
            check_existing_func: Function to check if data already exists
            save_func: Function to save extracted data
            target: Target name to filter articles
            disease: Disease name to filter articles (optional)
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of records extracted
        """
        return LiteratureProcessingUtils.process_articles_by_filters(
            db_session=db_session,
            extraction_func=extraction_func,
            check_existing_func=check_existing_func,
            save_func=save_func,
            target=target,
            disease=disease,
            batch_size=batch_size
        )

