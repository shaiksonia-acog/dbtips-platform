"""
Enhanced Supplementary Materials Data Segregation Module

This module extracts supplementary materials data from ArticlesMetadata.raw_full_text (NXML format) 
and populates the LiteratureSupplementaryMaterialsAnalysis table with file URLs, titles, and 
properly labeled contextual descriptions.
"""

import logging
import sys
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
from utils.literature_processing_utils import LiteratureProcessingUtils
from utils.supplementary_utils import SupplementaryMaterialsUtils

log = logging.getLogger(__name__)


class SupplementaryMaterialsSegregator:
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
            title=material_data["title"],
            description=material_data["description"],
            file_names=material_data["file_names"]
        )
        
        db_session.add(literature_material)
        return 1
    
    def extract_supplementary_materials_from_nxml(self, raw_nxml: str, pmcid: str, pmid: str, 
                                                disease: str, target: str, url: str) -> Optional[Dict]:
        """
        Extract supplementary materials from raw NXML/XML content (JATS format from PMC)
        Returns a single record with all supplementary materials grouped together
        
        Args:
            raw_nxml: Raw NXML content from ArticlesMetadata
            pmcid: PMC ID
            pmid: PubMed ID  
            disease: Disease name
            target: Target name
            url: Article URL
            
        Returns:
            Single dictionary with all supplementary materials or None if none found
        """
        if not raw_nxml:
            log.debug("No raw NXML content for PMCID: %s", pmcid)
            return None
            
        try:
            # Parse as XML instead of HTML
            soup = BeautifulSoup(raw_nxml, "xml")
        except Exception as e:
            log.error("Failed to parse NXML for PMCID %s: %s", pmcid, e)
            return None

        # Find all supplementary materials across the entire article
        all_materials = self.supplementary_utils.find_all_supplementary_materials(soup, pmcid)
        
        # Extract contextual descriptions with enhanced section labeling and post-processing
        contextual_descriptions = self.supplementary_utils.extract_contextual_descriptions(soup)
        
        if not all_materials and not contextual_descriptions:
            log.debug("No supplementary materials found in NXML for PMCID: %s", pmcid)
            return None

        # Group all materials into a single record
        titles = []
        file_urls = []
        
        for material in all_materials:
            if material['title'] and material['title'] not in titles:
                titles.append(material['title'])
            if material['url'] and material['url'] not in file_urls:
                file_urls.append(material['url'])
        
        # If no file URLs found but we have contextual descriptions, still create a record
        if not file_urls and not contextual_descriptions:
            return None
        
        # Enhanced description formatting with section labels and post-processing
        description = self._format_enhanced_description(contextual_descriptions)
            
        return {
            "pmcid": pmcid,
            "pmid": pmid,
            "disease": disease,
            "target": target,
            "url": url,
            "title": ", ".join(titles) if titles else "Supplementary Materials",
            "description": description,
            "file_names": ", ".join(file_urls) if file_urls else "",
            "extraction_timestamp": datetime.utcnow().isoformat()
        }
    
    def _format_enhanced_description(self, contextual_descriptions: List[str]) -> str:
        """
        Format the enhanced description with better structure and readability
        
        Args:
            contextual_descriptions: List of section-labeled and post-processed descriptions
            
        Returns:
            Formatted description string
        """
        if not contextual_descriptions:
            return "No description available"
        
        # Remove very similar descriptions to avoid redundancy
        unique_descriptions = self._remove_similar_descriptions(contextual_descriptions)
        
        # If we have multiple descriptions, separate them clearly
        if len(unique_descriptions) == 1:
            return unique_descriptions[0]
        elif len(unique_descriptions) <= 3:
            # For 2-3 descriptions, use bullet points
            return " • ".join(unique_descriptions)
        else:
            # For more than 3, use numbered format for better readability
            formatted = []
            for i, desc in enumerate(unique_descriptions[:4], 1):  # Limit to 4 descriptions
                formatted.append(f"{i}. {desc}")
            return " ".join(formatted)
    
    def _remove_similar_descriptions(self, descriptions: List[str]) -> List[str]:
        """
        Remove descriptions that are too similar to avoid redundancy
        
        Args:
            descriptions: List of description strings
            
        Returns:
            List of unique descriptions
        """
        if not descriptions:
            return descriptions
        
        unique_descriptions = []
        
        for desc in descriptions:
            # Check if this description is too similar to any existing one
            is_similar = False
            
            for existing_desc in unique_descriptions:
                # Remove section labels for comparison
                desc_clean = self._remove_section_label(desc)
                existing_clean = self._remove_section_label(existing_desc)
                
                # Calculate similarity based on word overlap
                if self._descriptions_are_similar(desc_clean, existing_clean):
                    is_similar = True
                    break
            
            if not is_similar:
                unique_descriptions.append(desc)
        
        return unique_descriptions
    
    def _remove_section_label(self, description: str) -> str:
        """
        Remove section label from description for similarity comparison
        
        Args:
            description: Description string potentially with section label
            
        Returns:
            Description without section label
        """
        import re
        # Remove section labels in format [Section Name] or [Section Name - Subsection]
        return re.sub(r'^\[([^\]]+)\]\s*', '', description)
    
    def _descriptions_are_similar(self, desc1: str, desc2: str, threshold: float = 0.7) -> bool:
        """
        Check if two descriptions are similar based on word overlap
        
        Args:
            desc1: First description
            desc2: Second description  
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if descriptions are similar
        """
        if not desc1 or not desc2:
            return False
        
        # Convert to word sets
        words1 = set(desc1.lower().split())
        words2 = set(desc2.lower().split())
        
        # Remove common words that don't contribute to meaning
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        words1 = words1 - common_words
        words2 = words2 - common_words
        
        if not words1 or not words2:
            return False
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union) if union else 0
        return similarity >= threshold
    
    def process_target_disease_articles(self, target: str, disease: Optional[str] = None, batch_size: int = 50) -> int:
        """Process articles filtered by target and disease to extract supplementary materials"""
        return self.utils.process_target_disease_articles(
            db_session=self.db,
            extraction_func=self.extract_supplementary_materials_from_article,
            check_existing_func=self.check_existing_supplementary_materials,
            save_func=self.save_supplementary_materials,
            target=target,
            disease=disease,
            batch_size=batch_size
        )

    def process_disease_articles(self, disease: str, batch_size: int = 50) -> int:
        """Process articles filtered by disease to extract supplementary materials"""
        return self.utils.process_disease_articles(
            db_session=self.db,
            extraction_func=self.extract_supplementary_materials_from_article,
            check_existing_func=self.check_existing_supplementary_materials,
            save_func=self.save_supplementary_materials,
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
                    "title": material_data["title"],
                    "file_count": len(material_data["file_names"].split(", ")) if material_data["file_names"] else 0,
                    "description_length": len(material_data["description"]),
                    "description_preview": material_data["description"][:200] + "..." if len(material_data["description"]) > 200 else material_data["description"]
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
    logging.basicConfig(level=logging.INFO)
    
    # Get database session
    db = next(get_db())
    
    try:
        segregator = SupplementaryMaterialsSegregator(db)
        
        print("Enhanced Supplementary Materials Data Segregation Module loaded successfully")
        print("\nAvailable methods:")
        print("1. segregator.process_disease_articles(disease) - Process all articles for a disease")
        print("2. segregator.process_target_disease_articles(target, disease) - Process articles for target/disease")
        print("3. segregator.preview_extraction(pmcid, pmid) - Preview extraction for a single article")
        print("\nEnhancements:")
        print("- Section names are included in descriptions (e.g., [Methods], [Results - Data Analysis])")
        print("- Disease keywords are filtered out from descriptions")
        print("- Duplicate and similar descriptions are removed")
        print("- Better formatting for multiple contextual descriptions")
        
        # Example usage
        print(f"\nExample usage:")
        print(f'preview = segregator.preview_extraction("PMC11318169")')
        print(f'total_materials = segregator.process_disease_articles("diabetes")')
        
    except Exception as e:
        log.error("Error during supplementary materials data segregation: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()