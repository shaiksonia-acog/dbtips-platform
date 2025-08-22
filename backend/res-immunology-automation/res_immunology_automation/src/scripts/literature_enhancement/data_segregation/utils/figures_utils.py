from typing import List, Dict, Any
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os

from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


class FiguresExtractor:
    def __init__(self):
        pass

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
            List of figure dictionaries (ALL figures - no caption filtering)
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
                
                # NO CAPTION FILTERING HERE - Store all figures
                if not caption:
                    log.debug("No caption found for figure %d in PMCID: %s", idx, pmcid)
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
        
        log.info("Extracted %d figures from PMCID: %s (no filtering applied)", 
                len(figures), pmcid)
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
    
    def _clean_caption(self, caption: str) -> str:
        """Clean and normalize caption text"""
        if not caption:
            return ""
        
        # Remove extra whitespace and normalize
        caption = re.sub(r'\s+', ' ', caption.strip())
        
        # Remove common prefixes like "Figure 1.", "Fig. 1:", etc.
        caption = re.sub(r'^(Figure|Fig\.?)\s*\d+[.\:\-\s]*', '', caption, flags=re.IGNORECASE)
        
        # Remove download/view links text
        caption = re.sub(
            r'(Download|View)\s+(figure|image|larger version).*', 
             '', 
            caption, 
            flags=re.IGNORECASE
            )
        
        return caption.strip()
