#data_storage.py
"""
Database storage operations for literature data
Modified for synchronous database operations compatible with build_dossier.py
Updated to use new schema with articles_metadata table
"""
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import ArticlesMetadata
import os
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


class LiteratureStorage:
    """Handles storage operations for literature data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def article_exists(self, disease: str = "no-disease", pmid: str = "", target: str = "no-target") -> bool:
        """
        Check if article already exists in database
        
        Args:
            disease: Disease name (default: "no-disease")
            pmid: PubMed ID
            target: Target name (default: "no-target")
            
        Returns:
            True if article exists, False otherwise
        """
        try:
            conditions = [
                ArticlesMetadata.disease == disease,
                ArticlesMetadata.pmid == pmid,
                ArticlesMetadata.target == target
            ]
            
            existing = self.db.query(ArticlesMetadata).filter(and_(*conditions)).first()
            return existing is not None
        except Exception as e:
            log.error(f"Error checking if article exists: {e}")
            return False
    
    def store_article(self, 
                     disease: str = "no-disease",
                     pmid: str = "",
                     pmcid: Optional[str] = None,
                     title: Optional[str] = None,
                     url: Optional[str] = None,
                     raw_full_text: Optional[str] = None,
                     target: str = "no-target") -> bool:
        """
        Store article data in database
        Only stores articles that have raw_full_text content, but includes titles
        
        Args:
            disease: Disease name (default: "no-disease")
            pmid: PubMed ID
            pmcid: PMC ID (optional)
            title: Article title (optional)
            url: PMC URL (optional)  
            raw_full_text: Full text XML content (required for storage)
            target: Target name (default: "no-target")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip storage if no raw_full_text content (as per your requirement)
            if not raw_full_text or not raw_full_text.strip():
                log.debug(f"Skipping storage of PMID {pmid} - no raw_full_text content")
                return False
        
            # Check if article already exists
            if self.article_exists(disease, pmid, target):
                log.info(f"Article PMID {pmid} for disease {disease} and target {target} already exists - updating")
                return self.update_article(disease, pmid, pmcid, title, url, raw_full_text, target)
        
            # Create new article record
            article = ArticlesMetadata(
                disease=disease,
                target=target,
                pmid=pmid,
                pmcid=pmcid if pmcid else "",  # Store empty string instead of None
                title=title,
                url=url,
                raw_full_text=raw_full_text
            )
        
            self.db.add(article)
            self.db.commit()
            self.db.refresh(article)
        
            log.debug(f"Stored article PMID {pmid} for disease {disease} and target {target} with title: {title[:50] + '...' if title and len(title) > 50 else title}")
            return True
        
        except Exception as e:
            log.error(f"Failed to store article PMID {pmid} for disease {disease} and target {target}: {e}")
            self.db.rollback()
            return False
    
    def update_article(self,
                      disease: str = "no-disease",
                      pmid: str = "",
                      pmcid: Optional[str] = None,
                      title: Optional[str] = None,
                      url: Optional[str] = None,
                      raw_full_text: Optional[str] = None,
                      target: str = "no-target") -> bool:
        """
        Update existing article in database
        
        Args:
            disease: Disease name (default: "no-disease")
            pmid: PubMed ID
            pmcid: PMC ID (optional)
            title: Article title (optional)
            url: PMC URL (optional)
            raw_full_text: Full text XML content (optional)
            target: Target name (default: "no-target")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conditions = [
                ArticlesMetadata.disease == disease,
                ArticlesMetadata.pmid == pmid,
                ArticlesMetadata.target == target
            ]
            
            article = self.db.query(ArticlesMetadata).filter(and_(*conditions)).first()
            
            if not article:
                log.warning(f"Article PMID {pmid} for disease {disease} and target {target} not found for update")
                return False
            
            # Update fields if provided
            if pmcid is not None:
                article.pmcid = pmcid
            if title is not None:
                article.title = title
            if url is not None:
                article.url = url
            if raw_full_text is not None:
                article.raw_full_text = raw_full_text
            
            self.db.commit()
            log.debug(f"Updated article PMID {pmid} for disease {disease} and target {target}")
            return True
            
        except Exception as e:
            log.error(f"Failed to update article PMID {pmid} for disease {disease} and target {target}: {e}")
            self.db.rollback()
            return False
    
    def get_articles_for_disease(self, disease: str = "no-disease", target: str = "no-target") -> List[ArticlesMetadata]:
        """
        Retrieve all articles for a disease and target combination
        
        Args:
            disease: Disease name (default: "no-disease")
            target: Target name (default: "no-target")
            
        Returns:
            List of ArticlesMetadata objects
        """
        try:
            query = self.db.query(ArticlesMetadata).filter(
                ArticlesMetadata.disease == disease,
                ArticlesMetadata.target == target
            )
            
            articles = query.all()
            log.info(f"Retrieved {len(articles)} articles for disease {disease} and target {target}")
            return articles
            
        except Exception as e:
            log.error(f"Failed to retrieve articles for disease {disease} and target {target}: {e}")
            return []
    
    def get_article_count(self, disease: str = "no-disease", target: str = "no-target") -> int:
        """
        Get count of articles for a disease and target combination
        
        Args:
            disease: Disease name (default: "no-disease")
            target: Target name (default: "no-target")
            
        Returns:
            Number of articles
        """
        try:
            query = self.db.query(ArticlesMetadata).filter(
                ArticlesMetadata.disease == disease,
                ArticlesMetadata.target == target
            )
            
            count = query.count()
            return count
            
        except Exception as e:
            log.error(f"Failed to get article count for disease {disease} and target {target}: {e}")
            return 0
    
    def store_articles_batch(self, articles_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Store multiple articles in batch
        
        Args:
            articles_data: List of dictionaries containing article data
            
        Returns:
            Dictionary with counts of successful/failed operations
        """
        results = {'successful': 0, 'failed': 0, 'skipped': 0}
        
        for article_data in articles_data:
            try:
                disease = article_data.get('disease', 'no-disease')
                pmid = article_data.get('pmid', '')
                target = article_data.get('target', 'no-target')
                raw_full_text = article_data.get('raw_full_text')
                
                if not pmid:
                    log.warning(f"Missing PMID in article data: {article_data}")
                    results['failed'] += 1
                    continue
                
                # Skip if no raw_full_text
                if not raw_full_text or not raw_full_text.strip():
                    log.debug(f"Skipping PMID {pmid} - no raw_full_text content")
                    results['skipped'] += 1
                    continue
                
                if self.article_exists(disease, pmid, target):
                    log.debug(f"Article PMID {pmid} for disease {disease} and target {target} already exists - skipping")
                    results['skipped'] += 1
                    continue
                
                success = self.store_article(
                    disease=disease,
                    pmid=pmid,
                    pmcid=article_data.get('pmcid'),
                    title=article_data.get('title'),
                    url=article_data.get('url'),
                    raw_full_text=raw_full_text,
                    target=target
                )
                
                if success:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                log.error(f"Error in batch processing article: {e}")
                results['failed'] += 1
        
        log.info(f"Batch storage results: {results}")
        return results
    
    def cleanup_incomplete_articles(self, disease: str = "no-disease", target: str = "no-target") -> int:
        """
        Remove articles that don't have full text content
        
        Args:
            disease: Disease name (default: "no-disease")
            target: Target name (default: "no-target")
            
        Returns:
            Number of articles removed
        """
        try:
            conditions = [
                ArticlesMetadata.disease == disease,
                ArticlesMetadata.target == target,
                ArticlesMetadata.raw_full_text.is_(None)
            ]
            
            query = self.db.query(ArticlesMetadata).filter(and_(*conditions))
            
            articles_to_delete = query.all()
            count = len(articles_to_delete)
            
            for article in articles_to_delete:
                self.db.delete(article)
            
            self.db.commit()
            log.info(f"Cleaned up {count} incomplete articles for disease {disease} and target {target}")
            return count
            
        except Exception as e:
            log.error(f"Failed to cleanup incomplete articles for disease {disease} and target {target}: {e}")
            self.db.rollback()
            return 0