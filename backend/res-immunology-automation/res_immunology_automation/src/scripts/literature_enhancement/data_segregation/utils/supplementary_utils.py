"""
Enhanced Supplementary Materials Utility Functions

This module contains improved helper functions for extracting and processing supplementary materials
from NXML/XML content with better section labeling.
"""

import logging
import re
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup
from datetime import datetime
import os

from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


class SupplementaryMaterialsUtils:
    """Utility class containing helper functions for supplementary materials extraction"""
    
    def __init__(self):
        pass
    
    def extract_contextual_descriptions(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract contextual paragraphs/sections about supplementary materials from the full text
        Now includes section names
        """
        contextual_descriptions = []
        
        # Target elements that could contain supplementary material context
        target_elements = [
            # Main content elements with section identification
            ('abstract', soup.find('abstract')),
            ('methods', soup.find_all('sec', {'sec-type': ['methods', 'materials-methods']})),
            ('results', soup.find_all('sec', {'sec-type': ['results']})),
            ('discussion', soup.find_all('sec', {'sec-type': ['discussion']})),
            ('body_paragraphs', soup.find_all('p') if soup.find('body') else []),
            ('caption_elements', soup.find_all('caption')),
            ('back_paragraphs', soup.find_all('p') if soup.find('back') else []),
        ]
        
        # Process each element type
        for element_type, elements in target_elements:
            if element_type == 'abstract' and elements:
                elements = [elements]  # Make it a list for uniform processing
            elif not elements:
                continue
                
            if not isinstance(elements, list):
                elements = [elements]
                
            for element in elements:
                if element:
                    contexts = self._extract_context_from_element(element, element_type)
                    if contexts:
                        contextual_descriptions.extend(contexts)
        
        # Remove duplicates while preserving order
        unique_descriptions = []
        seen = set()
        for desc in contextual_descriptions:
            desc_key = desc.get('text', '')[:100]  # Use first 100 chars as key
            if desc_key not in seen and desc.get('text'):
                seen.add(desc_key)
                unique_descriptions.append(desc)
        
        # Return formatted descriptions with section names
        formatted_descriptions = []
        for desc in unique_descriptions[:5]:  # Top 5 most relevant
            formatted_text = self._format_description_with_section(desc)
            if formatted_text:
                formatted_descriptions.append(formatted_text)
        
        return formatted_descriptions
    
    def _format_description_with_section(self, desc_dict: Dict) -> str:
        """
        Format description with section name
        """
        text = desc_dict.get('text', '')
        section_type = desc_dict.get('section_type', '')
        section_title = desc_dict.get('section_title', '')
        
        if not text:
            return ""
        
        # Basic cleanup only - remove excessive whitespace
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        if not cleaned_text or len(cleaned_text.strip()) < 20:
            return ""
        
        # Format with section information
        section_label = self._get_section_label(section_type, section_title)
        
        if section_label:
            return f"[{section_label}] {cleaned_text}"
        else:
            return cleaned_text
    
    def _get_section_label(self, section_type: str, section_title: str = "") -> str:
        """
        Get a clean section label for the description
        """
        # Use section title if it's meaningful and not too long
        if section_title and len(section_title) < 50 and not self._is_generic_title(section_title):
            return section_title
        
        # Map section types to readable labels
        section_mapping = {
            'abstract': 'Abstract',
            'methods': 'Methods',
            'materials-methods': 'Methods',
            'results': 'Results',
            'discussion': 'Discussion',
            'body_paragraphs': 'Main Text',
            'caption_elements': 'Figure/Table Caption',
            'back_paragraphs': 'Appendix'
        }
        
        return section_mapping.get(section_type, section_type.title())
    
    def _is_generic_title(self, title: str) -> bool:
        """
        Check if title is too generic to be useful
        """
        generic_titles = {
            'methods', 'results', 'discussion', 'introduction', 'conclusion',
            'background', 'abstract', 'summary', 'overview', 'analysis'
        }
        return title.lower().strip() in generic_titles
    
    def _extract_context_from_element(self, element, section_type: str) -> List[Dict]:
        """
        Extract contextual information from a specific element with enhanced section handling
        """
        contexts = []
        
        # Get the full text content of the element
        element_text = element.get_text(separator=' ', strip=True)
        
        # Check if this element contains supplementary material mentions
        if not self._contains_supplementary_mentions(element_text):
            return contexts
        
        # Enhanced section handling based on element type
        if element.name == 'p':
            context = self._extract_paragraph_context(element, section_type)
            if context:
                contexts.append(context)
        elif element.name == 'caption':
            context = self._extract_caption_context(element, section_type)
            if context:
                contexts.append(context)
        else:
            context = self._extract_generic_context(element, section_type)
            if context:
                contexts.append(context)
        
        return contexts
    
    def _extract_paragraph_context(self, paragraph_element, section_type: str) -> Optional[Dict]:
        """
        Extract context from a paragraph element, including surrounding context
        """
        para_text = paragraph_element.get_text(separator=' ', strip=True)
        
        # Get parent section title if available
        parent_section = paragraph_element.find_parent('sec')
        section_title = ""
        if parent_section:
            title_elem = parent_section.find('title')
            section_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Get surrounding context (previous and next siblings)
        context_parts = []
        
        # Add the main paragraph
        if self._contains_supplementary_mentions(para_text):
            context_parts.append(para_text)
        
        context_text = " ".join(context_parts)
        
        return {
            'text': context_text,
            'section_type': section_type,
            'section_title': section_title,
        }
    
    def _extract_caption_context(self, caption_element, section_type: str) -> Optional[Dict]:
        """
        Extract context from a caption element and its associated figure/table
        """
        caption_text = caption_element.get_text(separator=' ', strip=True)
        
        # Try to find the parent figure or table
        parent_fig = caption_element.find_parent(['fig', 'table-wrap'])
        
        context_parts = [caption_text]
        section_title = "Figure/Table Caption"
        
        if parent_fig:
            # Get figure/table label and title if available
            label_elem = parent_fig.find('label')
            title_elem = parent_fig.find('title')
            
            if label_elem:
                label_text = label_elem.get_text(strip=True)
                context_parts.insert(0, label_text)
                section_title = f"{label_text} Caption"
            if title_elem and title_elem != caption_element:
                context_parts.insert(-1, title_elem.get_text(strip=True))
        
        context_text = " ".join(context_parts)
        
        return {
            'text': context_text,
            'section_type': section_type,
            'section_title': section_title,
            'parent_element': parent_fig.name if parent_fig else None,
            
        }
    
    def _extract_generic_context(self, element, section_type: str) -> Optional[Dict]:
        """
        Extract context from other types of elements
        """
        element_text = element.get_text(separator=' ', strip=True)
        
        # Only proceed if the text contains supplementary mentions
        if not self._contains_supplementary_mentions(element_text):
            return None
        
        # Truncate if too long
        if len(element_text) > 800:
            element_text = element_text[:800] + "..."
        
        return {
            'text': element_text,
            'section_type': section_type,
            'section_title': "",
            'tag_name': element.name,
        }
    
    def _contains_supplementary_mentions(self, text: str) -> bool:
        """
        Check if text contains mentions of supplementary materials
        """
        if not text or len(text) < 20:
            return False
        
        text_lower = text.lower()
        
        # Keywords that indicate supplementary material mentions
        supplementary_keywords = [
            'supplementary material', 'supplementary materials', 'supplementary data',
            'supplemental material', 'supplemental materials', 'supplemental data',
            'supplementary information', 'supplemental information',
            'additional file', 'additional files', 'additional material',
            'supporting information', 'supporting materials',
            'online supplementary', 'online supplemental',
            'additional data', 'additional information',
            'provided as supplementary', 'provided as supplemental',
            'available as supplementary', 'available as supplemental',
            'detailed in supplementary', 'detailed in supplemental',
            'shown in supplementary', 'shown in supplemental',
            'described in supplementary', 'described in supplemental'
        ]
        
        return any(keyword in text_lower for keyword in supplementary_keywords)
    
    # Keep the existing methods for finding supplementary materials
    def find_all_supplementary_materials(self, soup: BeautifulSoup, pmcid: str) -> List[Dict]:
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
                if self._is_genuine_supplementary_title(title_text):
                    sections.append(section)
        
        return sections
    
    def _is_genuine_supplementary_title(self, title: str) -> bool:
        """
        Check if a section title genuinely indicates supplementary materials
        """
        title = title.lower().strip()
        
        genuine_indicators = [
            'supplementary material', 'supplementary materials', 
            'supplementary information', 'supplemental material',
            'supplemental materials', 'supplemental information',
            'additional files', 'supporting information'
        ]
        
        exclusions = [
            'figure', 'table', 'data availability', 'funding',
            'acknowledgment', 'reference', 'method', 'result',
            'discussion', 'conclusion', 'introduction', 'background'
        ]
        
        has_genuine_indicator = any(indicator in title for indicator in genuine_indicators)
        has_exclusion = any(exclusion in title for exclusion in exclusions)
        
        return has_genuine_indicator and not has_exclusion
    
    def _extract_from_supplementary_material_tag(self, supp_mat_tag, pmcid: str) -> Optional[Dict]:
        """Extract material from explicit supplementary-material XML tags"""
        media_elem = supp_mat_tag.find('media')
        if media_elem:
            href = media_elem.get('xlink:href') or media_elem.get('href')
            if href:
                description = self._extract_clean_description(supp_mat_tag)
                url = self._build_supplementary_url_from_href(href, pmcid)
                return {'url': url, 'description': description, 'original_href': href}
        
        ext_link = supp_mat_tag.find('ext-link')
        if ext_link:
            href = ext_link.get('xlink:href') or ext_link.get('href')
            if href and self._is_supplementary_file_url(href):
                description = self._extract_clean_description(supp_mat_tag)
                return {'url': href, 'description': description, 'original_href': href}
        
        return None
    
    def _extract_materials_from_genuine_section(self, section, pmcid: str) -> List[Dict]:
        """Extract materials from sections that are genuinely about supplementary materials"""
        materials = []
        all_links = section.find_all(['ext-link', 'media'])
        for link in all_links:
            href = link.get('xlink:href') or link.get('href') or ''
            if href and self._is_supplementary_file_url(href):
                description = self._extract_clean_description(link.parent if link.parent else link)
                url = href if href.startswith('http') else self._build_supplementary_url_from_href(href, pmcid)
                materials.append({'url': url, 'description': description, 'original_href': href})
        return materials
    
    def _extract_from_back_matter(self, back_elem, pmcid: str) -> List[Dict]:
        """Extract supplementary materials from back matter"""
        materials = []
        supp_materials = back_elem.find_all('supplementary-material')
        for supp_mat in supp_materials:
            material = self._extract_from_supplementary_material_tag(supp_mat, pmcid)
            if material:
                materials.append(material)
        return materials
    
    def _is_supplementary_file_url(self, href: str) -> bool:
        """Check if URL/href actually points to a supplementary file"""
        if not href:
            return False
        href_lower = href.lower()
        supplementary_indicators = ['supplement', 'additional', 'supporting']
        file_extensions = ['.xls', '.xlsx', '.doc', '.docx', '.pdf', '.zip', '.csv', '.txt', '.xml']
        has_supp_indicator = any(indicator in href_lower for indicator in supplementary_indicators)
        has_file_extension = any(ext in href_lower for ext in file_extensions)
        if 'pmc.ncbi.nlm.nih.gov' in href_lower:
            return '/bin/' in href_lower and has_file_extension
        return has_supp_indicator and has_file_extension
    
    def _build_supplementary_url_from_href(self, href: str, pmcid: str) -> str:
        """Build proper supplementary material URL from href"""
        if href.startswith('http'):
            return href
        if "/" in href:
            file_name = href.split("/")[-1]
        else:
            file_name = href
        clean_pmcid = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
        return f"https://pmc.ncbi.nlm.nih.gov/articles/instance/{clean_pmcid}/bin/{file_name}"
    
    def _extract_clean_description(self, element) -> str:
        """Extract a clean description for supplementary material"""
        description = ""
        caption_selectors = ['caption', 'title', 'label']
        for selector in caption_selectors:
            caption_elem = element.find(selector)
            if caption_elem:
                caption_text = caption_elem.get_text(strip=True)
                if caption_text and len(caption_text) > 5:
                    description = caption_text
                    break
        
        if not description:
            element_text = element.get_text(strip=True)
            if element_text and len(element_text) > 10 and not self._looks_like_filename(element_text):
                description = element_text[:200]
        
        if description:
            description = re.sub(r'\s+', ' ', description.strip())
            description = re.sub(r'(Download|View|Click here)[^.]*\.', '', description, flags=re.IGNORECASE)
            description = description.strip()
        
        return description or "Supplementary Material"
    
    def _looks_like_filename(self, text: str) -> bool:
        """Check if text looks like a filename rather than a description"""
        if not text:
            return False
        file_extensions = ['.xls', '.xlsx', '.doc', '.docx', '.pdf', '.zip', 
                          '.csv', '.txt', '.xml', '.json', '.png', '.jpg', '.tif']
        has_extension = any(ext in text.lower() for ext in file_extensions)
        is_short = len(text) < 50
        few_spaces = text.count(' ') < 3
        return has_extension and is_short and few_spaces

class SupplementaryMaterialsExtractor:
    def __init__(self):
        self.supplementary_utils = SupplementaryMaterialsUtils()

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
        descriptions = []
        file_urls = []
        
        for material in all_materials:
            if material['description'] and material['description'] not in descriptions:
                descriptions.append(material['description'])
            if material['url'] and material['url'] not in file_urls:
                file_urls.append(material['url'])
        
        # If no file URLs found but we have contextual descriptions, still create a record
        if not file_urls and not contextual_descriptions:
            return None
        
        # Enhanced context_chunks formatting with section labels and post-processing
        context_chunks = self._format_enhanced_context_chunks(contextual_descriptions)
        if context_chunks:
            return {
                "pmcid": pmcid,
                "pmid": pmid,
                "disease": disease,
                "target": target,
                "url": url,
                "description": ", ".join(descriptions) if descriptions else "Supplementary Materials",
                "context_chunks": context_chunks,
                "file_names": ", ".join(file_urls) if file_urls else "",
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
        return None
    
    def _format_enhanced_context_chunks(self, contextual_descriptions: List[str]) -> str:
        """
        Format the enhanced context_chunks with better structure and readability
        
        Args:
            contextual_descriptions: List of section-labeled and post-processed descriptions
            
        Returns:
            Formatted context_chunks string
        """
        if not contextual_descriptions:
            return None
        
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