"""
Figure Data Segregation Module (Refactored)

This module extracts figure data from ArticlesMetadata.raw_full_text (NXML format) and populates 
the LiteratureImagesAnalysis table with image URLs and captions.
"""

import logging
import sys, os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import ArticlesMetadata, LiteratureImagesAnalysis
from literature_enhancement.data_segregation.utils.literature_processing_utils import LiteratureProcessingUtils
from literature_enhancement.data_segregation.utils.figures_utils import FiguresExtractor

module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
log = logging.getLogger(module_name)

class FigureDataSegregator:
    """Handles extraction and segregation of figure data from NXML articles"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.utils = LiteratureProcessingUtils()
        self.figure_extractor = FiguresExtractor()
    
    def extract_figures_from_article(self, article: ArticlesMetadata) -> List[Dict]:
        """
        Extract figures from a single article
        
        Args:
            article: ArticlesMetadata instance
            
        Returns:
            List of figure dictionaries
        """
        return self.figure_extractor.extract_figures_from_nxml(
            raw_nxml=article.raw_full_text,
            pmcid=article.pmcid,
            pmid=article.pmid,
            disease=article.disease or "no-disease",
            target=article.target or "no-target",
            url=article.url or ""
        )
    
    def check_existing_figures(self, article: ArticlesMetadata, db_session: Session) -> bool:
        """Check if figures for this article already exist"""
        existing_figures = (
            db_session.query(LiteratureImagesAnalysis)
            .filter(
                LiteratureImagesAnalysis.pmid == article.pmid,
                LiteratureImagesAnalysis.disease == article.disease,
                LiteratureImagesAnalysis.target == article.target
            )
            .first()
        )
        return existing_figures is not None
    
    def save_figures(self, figures_data: List[Dict], db_session: Session) -> int:
        """Save extracted figures to database"""
        if not figures_data:
            return 0
        
        for figure_data in figures_data:
            literature_image = LiteratureImagesAnalysis(
                pmid=figure_data["pmid"],
                disease=figure_data["disease"],
                target=figure_data["target"],
                url=figure_data["url"],
                pmcid=figure_data["pmcid"],
                image_url=figure_data["image_url"],
                image_caption=figure_data["image_caption"],
                is_disease_pathway=None,  # Will be determined during analysis
                status="extracted"
            )
            db_session.add(literature_image)
        
        return len(figures_data)
    
    
    def process_articles(self, target: Optional[str] = None, disease: Optional[str] = None, batch_size: int = 50) -> int:
        """Process articles filtered by target and disease to extract figures"""
        return self.utils.process_articles(
            db_session=self.db,
            extraction_func=self.extract_figures_from_article,
            check_existing_func=self.check_existing_figures,
            save_func=self.save_figures,
            target=target,
            disease=disease,
            batch_size=batch_size
        )
    
def main():
    """Main function to run figure data segregation"""
    # Get database session
    db = next(get_db())
    
    try:
        segregator = FigureDataSegregator(db)
        
        print("Figure data segregation complete. All figures extracted without caption filtering.")
        
    except Exception as e:
        log.error("Error during figure data segregation: %s", e)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()