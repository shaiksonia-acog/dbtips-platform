"""
Supplementary Materials Data Segregation Module

This module extracts supplementary materials data from ArticlesMetadata.raw_full_text (NXML format) 
and populates the LiteratureSupplementaryMaterialsAnalysis table with file URLs and descriptions.
"""

import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy import select

# Add the scripts directory to sys.path to import modules (same as CLI)
scripts_dir = Path(__file__).parent.parent.parent
sys.path.append(str(scripts_dir))

from db.database import get_db
from db.models import ArticlesMetadata, LiteratureSupplementaryMaterialsAnalysis

log = logging.getLogger(__name__)


class SupplementaryMaterialsSegregator:
    """Handles extraction and segregation of supplementary materials data from NXML articles"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
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
        all_materials = self._find_all_supplementary_materials(soup, pmcid)
        
        if not all_materials:
            log.debug("No supplementary materials found in NXML for PMCID: %s", pmcid)
            return None

        # Group all materials into a single record
        descriptions = []
        file_urls = []
        
        for material in all_materials:
            if material['description'] and material['description'] not in descriptions:
                descriptions.append(material['description'])
            if material['url'] and material['url'] not in file_urls:
                file_urls.append(material['url'])
        
        if not file_urls:
            return None
            
        return {
            "pmcid": pmcid,
            "pmid": pmid,
            "disease": disease,
            "target": target,
            "url": url,
            "description": ", ".join(descriptions),
            "file_names": ", ".join(file_urls),
            "extraction_timestamp": datetime.utcnow().isoformat()
        }
    
    def _find_all_supplementary_materials(self, soup: BeautifulSoup, pmcid: str) -> List[Dict]:
        """
        Find all supplementary materials in the entire JATS XML document
        Only looks for actual supplementary materials, not regular figures/tables
        """
        materials = []
        
        # 1. Look for explicit supplementary-material tags
        supp_materials = soup.find_all('supplementary-material')
        for supp_mat in supp_materials:
            material = self._extract_from_supplementary_material_tag(supp_mat, pmcid)
            if material:
                materials.append(material)
        
        # 2. Look for sections specifically about supplementary materials
        supp_sections = self._find_genuine_supplementary_sections(soup)
        for section in supp_sections:
            section_materials = self._extract_materials_from_genuine_section(section, pmcid)
            materials.extend(section_materials)
        
        # 3. Look for back matter with supplementary materials
        back_matter = soup.find('back')
        if back_matter:
            back_materials = self._extract_from_back_matter(back_matter, pmcid)
            materials.extend(back_materials)
        
        # Remove duplicates
        unique_materials = []
        seen_urls = set()
        for material in materials:
            if material['url'] not in seen_urls:
                seen_urls.add(material['url'])
                unique_materials.append(material)
        
        return unique_materials
    
    def _find_genuine_supplementary_sections(self, soup: BeautifulSoup) -> List:
        """
        Find sections that are genuinely about supplementary materials
        More restrictive than the original method
        """
        sections = []
        
        # Look for sections with explicit supplementary material types
        section_selectors = [
            "sec[sec-type='supplementary-material']",
            "sec[sec-type='additional-information']",
        ]
        
        for selector in section_selectors:
            try:
                found_sections = soup.select(selector)
                sections.extend(found_sections)
            except Exception as e:
                log.debug("Error with selector '%s': %s", selector, e)
                continue
        
        # Look for sections with titles that explicitly mention supplementary materials
        all_sections = soup.find_all('sec')
        for section in all_sections:
            title_elem = section.find('title')
            if title_elem:
                title_text = title_elem.get_text(strip=True).lower()
                # Be more specific about what constitutes a supplementary section
                if self._is_genuine_supplementary_title(title_text):
                    sections.append(section)
        
        return sections
    
    def _is_genuine_supplementary_title(self, title: str) -> bool:
        """
        Check if a section title genuinely indicates supplementary materials
        """
        title = title.lower().strip()
        
        # Genuine supplementary material indicators
        genuine_indicators = [
            'supplementary material',
            'supplementary materials', 
            'supplementary information',
            'supplemental material',
            'supplemental materials',
            'supplemental information',
            'additional files',
            'supporting information',
            'appendix', # Only if it contains supplementary files
        ]
        
        # Exclude regular content that's not supplementary
        exclusions = [
            'figure',
            'table', 
            'data availability',
            'funding',
            'acknowledgment',
            'reference',
            'method',
            'result',
            'discussion',
            'conclusion',
            'introduction',
            'background'
        ]
        
        # Check for genuine indicators
        has_genuine_indicator = any(indicator in title for indicator in genuine_indicators)
        
        # Check for exclusions
        has_exclusion = any(exclusion in title for exclusion in exclusions)
        
        return has_genuine_indicator and not has_exclusion
    
    def _extract_from_supplementary_material_tag(self, supp_mat_tag, pmcid: str) -> Optional[Dict]:
        """
        Extract material from explicit supplementary-material XML tags
        """
        # Look for media or links within the supplementary material
        media_elem = supp_mat_tag.find('media')
        if media_elem:
            href = media_elem.get('xlink:href') or media_elem.get('href')
            if href:
                description = self._extract_clean_description(supp_mat_tag)
                url = self._build_supplementary_url_from_href(href, pmcid)
                return {
                    'url': url,
                    'description': description,
                    'original_href': href
                }
        
        # Look for external links
        ext_link = supp_mat_tag.find('ext-link')
        if ext_link:
            href = ext_link.get('xlink:href') or ext_link.get('href')
            if href and self._is_supplementary_file_url(href):
                description = self._extract_clean_description(supp_mat_tag)
                return {
                    'url': href,
                    'description': description,
                    'original_href': href
                }
        
        return None
    
    def _extract_materials_from_genuine_section(self, section, pmcid: str) -> List[Dict]:
        """
        Extract materials from sections that are genuinely about supplementary materials
        """
        materials = []
        
        # Look for links that point to actual supplementary files
        all_links = section.find_all(['ext-link', 'media'])
        for link in all_links:
            href = link.get('xlink:href') or link.get('href') or ''
            if href and self._is_supplementary_file_url(href):
                description = self._extract_clean_description(link.parent if link.parent else link)
                url = href if href.startswith('http') else self._build_supplementary_url_from_href(href, pmcid)
                materials.append({
                    'url': url,
                    'description': description,
                    'original_href': href
                })
        
        return materials
    
    def _extract_from_back_matter(self, back_elem, pmcid: str) -> List[Dict]:
        """
        Extract supplementary materials from back matter
        """
        materials = []
        
        # Look specifically for supplementary-material tags in back matter
        supp_materials = back_elem.find_all('supplementary-material')
        for supp_mat in supp_materials:
            material = self._extract_from_supplementary_material_tag(supp_mat, pmcid)
            if material:
                materials.append(material)
        
        return materials
    
    def _is_supplementary_file_url(self, href: str) -> bool:
        """
        Check if URL/href actually points to a supplementary file
        More restrictive than original method
        """
        if not href:
            return False
            
        href_lower = href.lower()
        
        # Must contain supplementary indicators AND file extensions
        supplementary_indicators = ['supplement', 'additional', 'supporting']
        file_extensions = ['.xls', '.xlsx', '.doc', '.docx', '.pdf', '.zip', '.csv', '.txt', '.xml']
        
        has_supp_indicator = any(indicator in href_lower for indicator in supplementary_indicators)
        has_file_extension = any(ext in href_lower for ext in file_extensions)
        
        # For PMC URLs, be more specific
        if 'pmc.ncbi.nlm.nih.gov' in href_lower:
            return '/bin/' in href_lower and has_file_extension
        
        return has_supp_indicator and has_file_extension
    
    def _build_supplementary_url_from_href(self, href: str, pmcid: str) -> str:
        """
        Build proper supplementary material URL from href
        """
        # If it's already a full URL, return as is
        if href.startswith('http'):
            return href
        
        # Clean the href - get just the filename
        if "/" in href:
            file_name = href.split("/")[-1]
        else:
            file_name = href
        
        # Clean PMC ID
        clean_pmcid = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
        
        # Build the URL
        full_url = f"https://pmc.ncbi.nlm.nih.gov/articles/instance/{clean_pmcid}/bin/{file_name}"
        
        return full_url
    
    def _extract_clean_description(self, element) -> str:
        """
        Extract a clean description for supplementary material
        """
        description = ""
        
        # Try to get caption or title
        caption_selectors = ['caption', 'title', 'label']
        for selector in caption_selectors:
            caption_elem = element.find(selector)
            if caption_elem:
                caption_text = caption_elem.get_text(strip=True)
                if caption_text and len(caption_text) > 5:  # Avoid very short descriptions
                    description = caption_text
                    break
        
        # If no caption, try element text but be selective
        if not description:
            element_text = element.get_text(strip=True)
            # Only use if it looks like a proper description, not a filename
            if element_text and len(element_text) > 10 and not self._looks_like_filename(element_text):
                description = element_text[:200]  # Truncate long descriptions
        
        # Clean the description
        if description:
            description = re.sub(r'\s+', ' ', description.strip())
            description = re.sub(r'(Download|View|Click here).*$', '', description, flags=re.IGNORECASE)
            description = description.strip()
        
        return description or "Supplementary Material"
    
    def _looks_like_filename(self, text: str) -> bool:
        """
        Check if text looks like a filename rather than a description
        """
        if not text:
            return False
            
        # Check for file extensions
        file_extensions = ['.xls', '.xlsx', '.doc', '.docx', '.pdf', '.zip', 
                          '.csv', '.txt', '.xml', '.json', '.png', '.jpg', '.tif']
        
        # Check if it's mostly a filename (short, has extension, no spaces)
        has_extension = any(ext in text.lower() for ext in file_extensions)
        is_short = len(text) < 50
        few_spaces = text.count(' ') < 3
        
        return has_extension and is_short and few_spaces
    
   
    def process_disease_articles(self, disease: str, batch_size: int = 50) -> int:
        """
        Process articles filtered by disease to extract supplementary materials
        
        Args:
            disease: Disease name to filter articles
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of supplementary material records extracted
        """
        # Get articles for the specific disease that haven't been processed yet
        stmt = (
            select(ArticlesMetadata)
            .where(
                ArticlesMetadata.raw_full_text.isnot(None),
                ArticlesMetadata.disease == disease
            )
            .limit(batch_size)
        )
        
        articles = self.db.execute(stmt).scalars().all()
        
        if not articles:
            log.info(f"No articles to process for disease: {disease}")
            return 0
        
        total_materials_extracted = 0
        
        for article in articles:
            try:
                # Check if supplementary materials for this article already exist
                existing_materials = (
                    self.db.query(LiteratureSupplementaryMaterialsAnalysis)
                    .filter(
                        LiteratureSupplementaryMaterialsAnalysis.pmid == article.pmid,
                        LiteratureSupplementaryMaterialsAnalysis.disease == article.disease
                    )
                    .first()
                )
                
                if existing_materials:
                    log.debug("Supplementary materials already exist for PMID: %s, Disease: %s", 
                            article.pmid, article.disease)
                    continue
                
                # Extract supplementary materials from the article
                material_data = self.extract_supplementary_materials_from_nxml(
                    raw_nxml=article.raw_full_text,
                    pmcid=article.pmcid,
                    pmid=article.pmid,
                    disease=article.disease or "no-disease",
                    target=article.target or "no-target",
                    url=article.url or ""
                )
                
                # Save to database if materials found
                if material_data:
                    literature_material = LiteratureSupplementaryMaterialsAnalysis(
                        pmid=material_data["pmid"],
                        disease=material_data["disease"],
                        target=material_data["target"],
                        url=material_data["url"],
                        pmcid=material_data["pmcid"],
                        description=material_data["description"],
                        file_names=material_data["file_names"]
                    )
                    
                    self.db.add(literature_material)
                    total_materials_extracted += 1
                    
                    # Commit after each article
                    self.db.commit()
                    
                    log.info("Processed article PMID: %s for disease %s, found supplementary materials", 
                            article.pmid, disease)
                else:
                    log.debug("No supplementary materials found for PMID: %s", article.pmid)
                
            except Exception as e:
                log.error("Error processing article PMID: %s for disease %s - %s", article.pmid, disease, e)
                self.db.rollback()
                continue
        
        log.info("Disease processing complete for %s. Extracted %d supplementary material records from %d articles", 
                disease, total_materials_extracted, len(articles))
        
        return total_materials_extracted

    def process_target_disease_articles(self, target: str, disease: Optional[str], batch_size: int = 50) -> int:
        """
        Process articles filtered by target and disease to extract supplementary materials
        
        Args:
            target: Target name to filter articles
            disease: Disease name to filter articles (optional)
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of supplementary material records extracted
        """
        # Build query based on whether disease is provided
        query_conditions = [
            ArticlesMetadata.raw_full_text.isnot(None),
            ArticlesMetadata.target == target
        ]
        
        if disease:
            query_conditions.append(ArticlesMetadata.disease == disease)
        
        stmt = (
            select(ArticlesMetadata)
            .where(*query_conditions)
            .limit(batch_size)
        )
        
        articles = self.db.execute(stmt).scalars().all()
        
        if not articles:
            log.info(f"No articles to process for target-disease: {target}-{disease}")
            return 0
        
        total_materials_extracted = 0
        
        for article in articles:
            try:
                # Check if supplementary materials for this article already exist
                existing_materials = (
                    self.db.query(LiteratureSupplementaryMaterialsAnalysis)
                    .filter(
                        LiteratureSupplementaryMaterialsAnalysis.pmid == article.pmid,
                        LiteratureSupplementaryMaterialsAnalysis.disease == article.disease,
                        LiteratureSupplementaryMaterialsAnalysis.target == article.target
                    )
                    .first()
                )
                
                if existing_materials:
                    log.debug("Supplementary materials already exist for PMID: %s, Target: %s, Disease: %s", 
                            article.pmid, article.target, article.disease)
                    continue
                
                # Extract supplementary materials from the article
                material_data = self.extract_supplementary_materials_from_nxml(
                    raw_nxml=article.raw_full_text,
                    pmcid=article.pmcid,
                    pmid=article.pmid,
                    disease=article.disease or "no-disease",
                    target=article.target or "no-target",
                    url=article.url or ""
                )
                
                # Save to database if materials found
                if material_data:
                    literature_material = LiteratureSupplementaryMaterialsAnalysis(
                        pmid=material_data["pmid"],
                        disease=material_data["disease"],
                        target=material_data["target"],
                        url=material_data["url"],
                        pmcid=material_data["pmcid"],
                        description=material_data["description"],
                        file_names=material_data["file_names"]
                    )
                    
                    self.db.add(literature_material)
                    total_materials_extracted += 1
                    
                    # Commit after each article
                    self.db.commit()
                    
                    log.info("Processed article PMID: %s for target-disease %s-%s, found supplementary materials", 
                            article.pmid, target, disease)
                else:
                    log.debug("No supplementary materials found for PMID: %s", article.pmid)
                
            except Exception as e:
                log.error("Error processing article PMID: %s for target-disease %s-%s - %s", 
                         article.pmid, target, disease, e)
                self.db.rollback()
                continue
        
        log.info("Target-disease processing complete for %s-%s. Extracted %d supplementary material records from %d articles", 
                target, disease, total_materials_extracted, len(articles))
        
        return total_materials_extracted


def main():
    """Main function to run supplementary materials data segregation"""
    logging.basicConfig(level=logging.INFO)
    
    # Get database session
    db = next(get_db())
    
    try:
        segregator = SupplementaryMaterialsSegregator(db)
        total_materials = segregator.process_all_articles()
        
        print(f"Supplementary materials data segregation complete. Total records extracted: {total_materials}")
        
    except Exception as e:
        log.error("Error during supplementary materials data segregation: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()