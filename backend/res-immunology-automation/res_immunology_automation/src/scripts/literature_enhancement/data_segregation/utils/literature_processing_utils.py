"""
Literature Processing Utilities

Shared utilities for processing literature data from NXML articles.
This module consolidates common functionality used across table, figure, 
and supplementary materials extraction modules.
"""

import logging
from typing import List, Optional, Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.models import ArticlesMetadata

log = logging.getLogger(__name__)


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
        # Check whether the Extraction is completed for the given target and disease
        query_conditions = [LiteratureEnhancementPipelineStatus.pipeline_type == "extraction", 
                            LiteratureEnhancementPipelineStatus.status= "completed"]
        if target:
            query_conditions.append(LiteratureEnhancementPipelineStatus.target == target)
        if disease:
            query_conditions.append(LiteratureEnhancementPipelineStatus.disease == disease)
        
        stmt = (
            select(LiteratureEnhancementPipelineStatus)
            .where(*query_conditions)
            .limit(batch_size)
        )

        status = db_session.execute(stmt).scalars().all()
        if not status:
            log.info(f"Extraction is not completed for target: {target}, disease: {disease}")
            return "error"

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
    def process_disease_articles(
        db_session: Session,
        extraction_func: Callable,
        check_existing_func: Callable,
        save_func: Callable,
        disease: str,
        batch_size: int = 50
    ) -> int:
        """
        Process articles filtered by disease
        
        Args:
            db_session: Database session
            extraction_func: Function to extract data from article
            check_existing_func: Function to check if data already exists
            save_func: Function to save extracted data
            disease: Disease name to filter articles
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of records extracted
        """
        return LiteratureProcessingUtils.process_articles_by_filters(
            db_session=db_session,
            extraction_func=extraction_func,
            check_existing_func=check_existing_func,
            save_func=save_func,
            disease=disease,
            batch_size=batch_size
        )

    @staticmethod
    def process_target_disease_articles(
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

    @staticmethod
    def check_pipeline_status(
        db_session: Session,
        pipeline_types: List[str] 
        target: Optional[str] = None,
        disease: Optional[str] = None,
        
    ) -> bool:
        """
        Check if the current and previous pipelines are completed for the given target and disease
        
        Args:
            db_session: Database session
            target: Target name to filter articles 
            disease: Disease name to filter articles 
            pipeline_types: List of pipeline types to check status for
            
        Returns:
            True if extraction is completed, False otherwise
        """
        query_conditions = [LiteratureEnhancementPipelineStatus.pipeline_type == pipeline_type,
                                        LiteratureEnhancementPipelineStatus.status == "completed"]
        if target:
            query_conditions.append(LiteratureEnhancementPipelineStatus.target == target)
        if disease:
        query_conditions.append(LiteratureEnhancementPipelineStatus.disease == disease)
    
        stmt = (
            select(LiteratureEnhancementPipelineStatus)
            .where(*_query_conditions)
            .limit(batch_size)
        )

        return stmt

        #     pipeline_status[pipeline_type] = db_session.execute(stmt).scalars().all()

        # logs = []
        # all_completed = True

        # for ptype, status_obj in pipeline_status.items():
        #     if status_obj is None:
        #         logs.append(f"No status found for pipeline type: {ptype}")
        #         all_completed = False
        #     elif status_obj.status != "completed":
        #         logs.append(f"Pipeline '{ptype}' is in '{status_obj.status}' state, not completed yet")
        #         all_completed = False

        # return all_completed, logs