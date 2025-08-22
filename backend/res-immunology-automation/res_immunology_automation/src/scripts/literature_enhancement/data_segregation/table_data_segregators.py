"""
Table Data Segregation Module (Refactored)

This module extracts table data from ArticlesMetadata.raw_full_text (NXML format) and populates 
the LiteratureTablesAnalysis table with table schemas and descriptions using LLM analysis.
"""

import logging
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ArticlesMetadata, LiteratureTablesAnalysis
from literature_enhancement.data_segregation.utils.literature_processing_utils import LiteratureProcessingUtils
from literature_enhancement.data_segregation.utils.tables_utils import TablesExtractor

module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
logger = logging.getLogger(module_name)


class TableDataSegregator:
    """Handles extraction and segregation of table data from NXML articles"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.utils = LiteratureProcessingUtils()
        self.tables_extractor = TablesExtractor()
    
    def extract_tables_from_article(self, article: ArticlesMetadata) -> List[Dict]:
        """
        Extract tables from a single article
        
        Args:
            article: ArticlesMetadata instance
            
        Returns:
            List of table dictionaries
        """
        return self.tables_extractor.extract_tables_from_nxml(
            raw_nxml=article.raw_full_text,
            pmcid=article.pmcid,
            pmid=article.pmid,
            disease=article.disease or "no-disease",
            target=article.target or "no-target",
            url=article.url or ""
        )
    
    def check_existing_tables(self, article: ArticlesMetadata, db_session: Session) -> bool:
        """Check if tables for this article already exist"""
        existing_tables = (
            db_session.query(LiteratureTablesAnalysis)
            .filter(
                LiteratureTablesAnalysis.pmid == article.pmid,
                LiteratureTablesAnalysis.disease == article.disease,
                LiteratureTablesAnalysis.target == article.target
            )
            .first()
        )
        return existing_tables is not None
    
    def save_tables(self, tables_data: List[Dict], db_session: Session) -> int:
        """Save extracted tables to database"""
        if not tables_data:
            return 0
        
        for table_data in tables_data:
            literature_table = LiteratureTablesAnalysis(
                pmid=table_data["pmid"],
                disease=table_data["disease"],
                target=table_data["target"],
                url=table_data["url"],
                pmcid=table_data["pmcid"],
                table_description=table_data["table_description"],
                table_schema=table_data["table_schema"]
            )
            db_session.add(literature_table)
        
        return len(tables_data)
    
    def process_articles(self, target: str, disease: str, batch_size: int = 50) -> int:
        """Process articles filtered by target and disease to extract tables"""
        return self.utils.process_articles(
            db_session=self.db,
            extraction_func=self.extract_tables_from_article,
            check_existing_func=self.check_existing_tables,
            save_func=self.save_tables,
            target=target,
            disease=disease if disease else "no-disease",
            batch_size=batch_size
        )

    # Keep all the existing private methods for table-specific logic
    
def main():
    """Main function to run table data segregation"""
    # Get database session
    db = next(get_db())
    
    try:
        # Initialize segregator with API key from environment
        segregator = TableDataSegregator(db)
        
        print(f"Table data segregation complete. Total tables extracted: {total_tables}")
        
    except Exception as e:
        log.error("Error during table data segregation: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()