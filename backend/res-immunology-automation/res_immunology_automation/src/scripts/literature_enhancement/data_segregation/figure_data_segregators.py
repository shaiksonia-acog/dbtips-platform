"""
Figure Data Segregation Module

This module extracts figure data from ArticlesMetadata.raw_full_text (NXML format) and populates 
the LiteratureImagesAnalysis table with image URLs and captions.
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
from db.models import ArticlesMetadata, LiteratureImagesAnalysis

log = logging.getLogger(__name__)


class FigureDataSegregator:
    """Handles extraction and segregation of figure data from NXML articles"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def extract_figures_from_nxml(self, raw_nxml: str, pmcid: str, pmid: str, 
                                 disease: str, target: str, url: str) -> List[Dict]:
        """
        Extract figures from raw NXML/XML content (JATS format from PMC)
        
        Args:
            raw_nxml: Raw NXML content from ArticlesMetadata
            pmcid: PMC ID
            pmid: PubMed ID  
            disease: Disease name
            target: Target name
            url: Article URL
            
        Returns:
            List of figure dictionaries
        """
        if not raw_nxml:
            log.debug("No raw NXML content for PMCID: %s", pmcid)
            return []
            
        try:
            # Parse as XML instead of HTML
            soup = BeautifulSoup(raw_nxml, "xml")
        except Exception as e:
            log.error("Failed to parse NXML for PMCID %s: %s", pmcid, e)
            return []

        figures: List[Dict] = []
        
        # JATS XML figure selectors - different from HTML
        fig_elements = soup.find_all("fig")
        
        if not fig_elements:
            log.debug("No fig elements found in NXML for PMCID: %s", pmcid)
            return []

        for idx, fig in enumerate(fig_elements, start=1):
            try:
                # In JATS XML, graphics are in <graphic> elements, not <img>
                graphic = fig.find("graphic")
                if not graphic:
                    log.debug("No graphic element found in figure %d for PMCID: %s", idx, pmcid)
                    continue
                
                # Get the xlink:href attribute which contains the image filename
                img_href = graphic.get("xlink:href") or graphic.get("href")
                if not img_href:
                    log.debug("No xlink:href found in figure %d for PMCID: %s", idx, pmcid)
                    continue
                
                # Build the proper image URL using the template pattern
                img_url = self._build_image_url_from_href(img_href, pmcid)
                
                # Skip if not a valid image URL
                if not self._is_valid_image_url(img_url):
                    log.debug("Invalid image URL for figure %d in PMCID: %s - %s", idx, pmcid, img_url)
                    continue

                # Extract caption from JATS XML structure
                caption = self._extract_nxml_caption(fig)
                
                if not caption:
                    log.debug("No caption found for figure %d in PMCID: %s", idx, pmcid)
                    # Still include the figure even without caption
                    caption = ""

                # Get figure ID if available
                fig_id = fig.get("id", f"fig-{idx}")

                figures.append({
                    "pmcid": pmcid,
                    "pmid": pmid,
                    "disease": disease,
                    "target": target,
                    "url": url,
                    "image_url": img_url,
                    "image_caption": caption,
                    "figure_id": fig_id,
                    "extraction_timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                log.warning("Error processing figure %d from PMCID %s: %s", idx, pmcid, e)
                continue
        
        log.info("Extracted %d figures from PMCID: %s", len(figures), pmcid)
        return figures
    
    def _build_image_url_from_href(self, img_href: str, pmcid: str) -> str:
        """
        Build proper image URL from JATS XML xlink:href using the template pattern:
        https://www.ncbi.nlm.nih.gov/pmc/articles/instance/<pmcid>/bin/<image-name>
        """
        # Clean the href - it might be just the filename or a relative path
        if "/" in img_href:
            image_name = img_href.split("/")[-1]
        else:
            image_name = img_href
        
        # Clean PMC ID (remove PMC prefix if present, then add it back)
        clean_pmcid = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
        
        # Build the URL using the template
        img_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/instance/{clean_pmcid}/bin/{image_name}"
        
        return img_url
    
    def _extract_nxml_caption(self, fig_element) -> str:
        """Extract caption from JATS XML figure element"""
        caption = ""
        
        # In JATS XML, captions are typically in <caption> element
        caption_elem = fig_element.find("caption")
        if caption_elem:
            # Get all text content from caption
            caption = caption_elem.get_text(strip=True, separator=" ")
            
        # If no caption element, try label + title
        if not caption:
            label_elem = fig_element.find("label")
            title_elem = fig_element.find("title")
            
            if label_elem and title_elem:
                caption = f"{label_elem.get_text(strip=True)} {title_elem.get_text(strip=True)}"
            elif title_elem:
                caption = title_elem.get_text(strip=True)
            elif label_elem:
                caption = label_elem.get_text(strip=True)
        
        # Clean the caption
        if caption:
            caption = self._clean_caption(caption)
        
        return caption
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL points to a valid image file"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.tif', '.tiff']
        return any(ext in url.lower() for ext in image_extensions)
    
    def _extract_caption(self, fig_element) -> str:
        """Extract caption from figure element"""
        caption = ""
        
        # Try multiple approaches to find caption
        caption_selectors = [
            "figcaption", 
            ".caption", 
            "[class*='caption']", 
            ".fig-caption",
            ".fig-caption-text",
            "p"
        ]
        
        for selector in caption_selectors:
            caption_elem = fig_element.select_one(selector)
            if caption_elem:
                caption = caption_elem.get_text(strip=True)
                # Clean up the caption
                caption = self._clean_caption(caption)
                if caption:  # Only break if we found meaningful content
                    break
        
        return caption
    
    def _clean_caption(self, caption: str) -> str:
        """Clean and normalize caption text"""
        if not caption:
            return ""
        
        # Remove extra whitespace and normalize
        caption = re.sub(r'\s+', ' ', caption.strip())
        
        # Remove common prefixes like "Figure 1.", "Fig. 1:", etc.
        caption = re.sub(r'^(Figure|Fig\.?)\s*\d+[.\:\-\s]*', '', caption, flags=re.IGNORECASE)
        
        # Remove download/view links text
        caption = re.sub(r'(Download|View)\s+(figure|image|larger version).*$', '', caption, flags=re.IGNORECASE)
        
        return caption.strip()
    
    def process_articles_batch(self, batch_size: int = 100, offset: int = 0) -> int:
        """
        Process articles in batches to extract figure data
        
        Args:
            batch_size: Number of articles to process in each batch
            offset: Starting offset for processing
            
        Returns:
            Number of figures extracted and saved
        """
        # Get articles that haven't been processed yet
        stmt = (
            select(ArticlesMetadata)
            .where(ArticlesMetadata.raw_full_text.isnot(None))
            .offset(offset)
            .limit(batch_size)
        )
        
        articles = self.db.execute(stmt).scalars().all()
        
        if not articles:
            log.info("No more articles to process")
            return 0
        
        total_figures_extracted = 0
        
        for article in articles:
            try:
                # Check if figures for this article already exist
                existing_figures = (
                    self.db.query(LiteratureImagesAnalysis)
                    .filter(
                        LiteratureImagesAnalysis.pmid == article.pmid,
                        LiteratureImagesAnalysis.disease == article.disease
                    )
                    .first()
                )
                
                if existing_figures:
                    log.debug("Figures already exist for PMID: %s, Disease: %s", 
                            article.pmid, article.disease)
                    continue
                
                # Extract figures from the article
                figures = self.extract_figures_from_nxml(
                    raw_nxml=article.raw_full_text,
                    pmcid=article.pmcid,
                    pmid=article.pmid,
                    disease=article.disease or "no-disease",
                    target=article.target or "no-target",
                    url=article.url or ""
                )
                
                # Save figures to database
                for figure_data in figures:
                    literature_image = LiteratureImagesAnalysis(
                        pmid=figure_data["pmid"],
                        disease=figure_data["disease"],
                        target=figure_data["target"],
                        url=figure_data["url"],
                        pmcid=figure_data["pmcid"],
                        image_url=figure_data["image_url"],
                        image_caption=figure_data["image_caption"],
                        status="extracted"
                    )
                    
                    self.db.add(literature_image)
                
                total_figures_extracted += len(figures)
                
                # Commit after each article to avoid losing progress
                self.db.commit()
                
                log.info("Processed article PMID: %s, extracted %d figures", 
                        article.pmid, len(figures))
                
            except Exception as e:
                log.error("Error processing article PMID: %s - %s", article.pmid, e)
                self.db.rollback()
                continue
        
        log.info("Batch processing complete. Extracted %d figures from %d articles", 
                total_figures_extracted, len(articles))
        
        return total_figures_extracted
    
    def process_all_articles(self, batch_size: int = 100) -> int:
        """
        Process all articles in the database
        
        Args:
            batch_size: Size of each processing batch
            
        Returns:
            Total number of figures extracted
        """
        total_extracted = 0
        offset = 0
        
        log.info("Starting figure extraction from all articles")
        
        while True:
            batch_extracted = self.process_articles_batch(batch_size, offset)
            
            if batch_extracted == 0:
                break
                
            total_extracted += batch_extracted
            offset += batch_size
            
            log.info("Processed batch %d-%d, total figures extracted so far: %d", 
                    offset - batch_size + 1, offset, total_extracted)
        
        log.info("Figure extraction complete. Total figures extracted: %d", total_extracted)
        return total_extracted

    def process_disease_articles(self, disease: str, batch_size: int = 50) -> int:
        """
        Process articles filtered by disease to extract figures
        
        Args:
            disease: Disease name to filter articles
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of figures extracted
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
        
        total_figures_extracted = 0
        
        for article in articles:
            try:
                # Check if figures for this article already exist
                existing_figures = (
                    self.db.query(LiteratureImagesAnalysis)
                    .filter(
                        LiteratureImagesAnalysis.pmid == article.pmid,
                        LiteratureImagesAnalysis.disease == article.disease
                    )
                    .first()
                )
                
                if existing_figures:
                    log.debug("Figures already exist for PMID: %s, Disease: %s", 
                            article.pmid, article.disease)
                    continue
                
                # Extract figures from the article
                figures = self.extract_figures_from_nxml(
                    raw_nxml=article.raw_full_text,
                    pmcid=article.pmcid,
                    pmid=article.pmid,
                    disease=article.disease or "no-disease",
                    target=article.target or "no-target",
                    url=article.url or ""
                )
                
                # Save figures to database
                for figure_data in figures:
                    literature_image = LiteratureImagesAnalysis(
                        pmid=figure_data["pmid"],
                        disease=figure_data["disease"],
                        target=figure_data["target"],
                        url=figure_data["url"],
                        pmcid=figure_data["pmcid"],
                        image_url=figure_data["image_url"],
                        image_caption=figure_data["image_caption"],
                        status="extracted"
                    )
                    
                    self.db.add(literature_image)
                
                total_figures_extracted += len(figures)
                
                # Commit after each article
                self.db.commit()
                
                log.info("Processed article PMID: %s for disease %s, extracted %d figures", 
                        article.pmid, disease, len(figures))
                
            except Exception as e:
                log.error("Error processing article PMID: %s for disease %s - %s", article.pmid, disease, e)
                self.db.rollback()
                continue
        
        log.info("Disease processing complete for %s. Extracted %d figures from %d articles", 
                disease, total_figures_extracted, len(articles))
        
        return total_figures_extracted

    def process_target_disease_articles(self, target: str, disease: Optional[str], batch_size: int = 50) -> int:
        """
        Process articles filtered by target and disease to extract figures
        
        Args:
            target: Target name to filter articles
            disease: Disease name to filter articles (optional)
            batch_size: Number of articles to process in each batch
            
        Returns:
            Number of figures extracted
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
        
        total_figures_extracted = 0
        
        for article in articles:
            try:
                # Check if figures for this article already exist
                existing_figures = (
                    self.db.query(LiteratureImagesAnalysis)
                    .filter(
                        LiteratureImagesAnalysis.pmid == article.pmid,
                        LiteratureImagesAnalysis.disease == article.disease,
                        LiteratureImagesAnalysis.target == article.target
                    )
                    .first()
                )
                
                if existing_figures:
                    log.debug("Figures already exist for PMID: %s, Target: %s, Disease: %s", 
                            article.pmid, article.target, article.disease)
                    continue
                
                # Extract figures from the article
                figures = self.extract_figures_from_nxml(
                    raw_nxml=article.raw_full_text,
                    pmcid=article.pmcid,
                    pmid=article.pmid,
                    disease=article.disease or "no-disease",
                    target=article.target or "no-target",
                    url=article.url or ""
                )
                
                # Save figures to database
                for figure_data in figures:
                    literature_image = LiteratureImagesAnalysis(
                        pmid=figure_data["pmid"],
                        disease=figure_data["disease"],
                        target=figure_data["target"],
                        url=figure_data["url"],
                        pmcid=figure_data["pmcid"],
                        image_url=figure_data["image_url"],
                        image_caption=figure_data["image_caption"],
                        status="extracted"
                    )
                    
                    self.db.add(literature_image)
                
                total_figures_extracted += len(figures)
                
                # Commit after each article
                self.db.commit()
                
                log.info("Processed article PMID: %s for target-disease %s-%s, extracted %d figures", 
                        article.pmid, target, disease, len(figures))
                
            except Exception as e:
                log.error("Error processing article PMID: %s for target-disease %s-%s - %s", 
                         article.pmid, target, disease, e)
                self.db.rollback()
                continue
        
        log.info("Target-disease processing complete for %s-%s. Extracted %d figures from %d articles", 
                target, disease, total_figures_extracted, len(articles))
        
        return total_figures_extracted


def main():
    """Main function to run figure data segregation"""
    logging.basicConfig(level=logging.INFO)
    
    # Get database session
    db = next(get_db())
    
    try:
        segregator = FigureDataSegregator(db)
        total_figures = segregator.process_all_articles()
        
        print(f"Figure data segregation complete. Total figures extracted: {total_figures}")
        
    except Exception as e:
        log.error("Error during figure data segregation: %s", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()