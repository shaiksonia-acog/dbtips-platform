"""
Enhanced Supplementary Materials Data Segregation Module

This module extracts supplementary materials data from ArticlesMetadata.raw_full_text (NXML format) 
and populates the LiteratureSupplementaryMaterialsAnalysis table with file URLs, descriptions, and 
properly labeled contextual context_chunks.
"""

import logging
import sys, os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

# Add the scripts directory to sys.path to import modules (same as CLI)
scripts_dir = Path(__file__).parent.parent.parent
sys.path.append(str(scripts_dir))

from db.database import get_db
from db.models import ArticlesMetadata, LiteratureSupplementaryMaterialsAnalysis
from literature_enhancement.data_segregation.utils.literature_processing_utils import LiteratureProcessingUtils
from literature_enhancement.data_segregation.utils.supplementary_utils import SupplementaryMaterialsUtils, SupplementaryMaterialsExtractor

module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
log = logging.getLogger(module_name)

class SupplementaryMaterialsSegregator(SupplementaryMaterialsExtractor):
    """Handles extraction and segregation of supplementary materials data from NXML articles"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.utils = LiteratureProcessingUtils()
        self.supplementary_utils = SupplementaryMaterialsUtils()
    
    def extract_supplementary_materials_from_article(self, article: ArticlesMetadata) -> Optional[Dict]:
        """
        Extract supplementary materials from a single article
        
        Args:
            article: ArticlesMetadata instance
            
        Returns:
            Single dictionary with all supplementary materials or None if none found
        """
        return self.extract_supplementary_materials_from_nxml(
            raw_nxml=article.raw_full_text,
            pmcid=article.pmcid,
            pmid=article.pmid,
            disease=article.disease or "no-disease",
            target=article.target or "no-target",
            url=article.url or ""
        )
    
    def check_existing_supplementary_materials(self, article: ArticlesMetadata, db_session: Session) -> bool:
        """Check if supplementary materials for this article already exist"""
        existing_materials = (
            db_session.query(LiteratureSupplementaryMaterialsAnalysis)
            .filter(
                LiteratureSupplementaryMaterialsAnalysis.pmid == article.pmid,
                LiteratureSupplementaryMaterialsAnalysis.disease == article.disease,
                LiteratureSupplementaryMaterialsAnalysis.target == article.target
            )
            .first()
        )
        return existing_materials is not None
    
    def save_supplementary_materials(self, material_data: Optional[Dict], db_session: Session) -> int:
        """Save extracted supplementary materials to database"""
        if not material_data:
            return 0
        
        literature_material = LiteratureSupplementaryMaterialsAnalysis(
            pmid=material_data["pmid"],
            disease=material_data["disease"],
            target=material_data["target"],
            url=material_data["url"],
            pmcid=material_data["pmcid"],
            description=material_data["description"],
            context_chunks=material_data["context_chunks"],
            file_names=material_data["file_names"]
        )
        
        db_session.add(literature_material)
        return 1
    
    def process_articles(self, target: Optional[str] = None, disease: Optional[str] = None, batch_size: int = 50) -> int:
        """Process articles filtered by target and disease to extract supplementary materials"""
        return self.utils.process_articles(
            db_session=self.db,
            extraction_func=self.extract_supplementary_materials_from_article,
            check_existing_func=self.check_existing_supplementary_materials,
            save_func=self.save_supplementary_materials,
            target=target,
            disease=disease,
            batch_size=batch_size
        )
    
    def preview_extraction(self, pmcid: str, pmid: str = None) -> Dict:
        """
        Preview the extraction results for a single article without saving to database
        Useful for testing and debugging
        
        Args:
            pmcid: PMC ID of the article
            pmid: Optional PubMed ID
            
        Returns:
            Dictionary with extraction preview results
        """
        try:
            # Find the article
            query = self.db.query(ArticlesMetadata).filter(ArticlesMetadata.pmcid == pmcid)
            if pmid:
                query = query.filter(ArticlesMetadata.pmid == pmid)
            
            article = query.first()
            
            if not article:
                return {
                    "status": "error",
                    "message": f"Article not found: PMCID={pmcid}, PMID={pmid}",
                    "pmcid": pmcid,
                    "pmid": pmid
                }
            
            # Extract supplementary materials
            material_data = self.extract_supplementary_materials_from_article(article)
            
            if not material_data:
                return {
                    "status": "no_materials",
                    "message": "No supplementary materials found",
                    "pmcid": pmcid,
                    "pmid": article.pmid,
                    "disease": article.disease,
                    "target": article.target
                }
            
            return {
                "status": "success",
                "message": "Supplementary materials extracted successfully",
                "data": material_data,
                "preview": {
                    "description": material_data["description"],
                    "file_count": len(material_data["file_names"].split(", ")) if material_data["file_names"] else 0,
                    "context_chunks_length": len(material_data["context_chunks"]),
                    "context_chunks_preview": material_data["context_chunks"][:200] + "..." if len(material_data["context_chunks"]) > 200 else material_data["context_chunks"]
                }
            }
            
        except Exception as e:
            log.error("Error during preview extraction for PMCID %s: %s", pmcid, e)
            return {
                "status": "error",
                "message": f"Extraction error: {str(e)}",
                "pmcid": pmcid,
                "pmid": pmid
            }
    

def main():
    """Main function to run supplementary materials data segregation"""
    
    # Get database session
    db = next(get_db())
    
    try:
        segregator = SupplementaryMaterialsSegregator(db)
        
        print("Enhanced Supplementary Materials Data Segregation Module loaded successfully")
        print("\nAvailable methods:")
        print("2. segregator.process_articles(target, disease) - Process articles for target/disease")
        print("3. segregator.preview_extraction(pmcid, pmid) - Preview extraction for a single article")
        print("\nEnhancements:")
        print("- Section names are included in context_chunks (e.g., [Methods], [Results - Data Analysis])")
        print("- Disease keywords are filtered out from context_chunks")
        print("- Duplicate and similar context_chunks are removed")
        print("- Better formatting for multiple contextual context_chunks")
        
        # Example usage
        print(f"\nExample usage:")
        print(f'preview = segregator.preview_extraction("PMC11318169")')
        print(f'total_materials = segregator.process_articles("diabetes")')
        
    except Exception as e:
        log.error("Error during supplementary materials data segregation: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()