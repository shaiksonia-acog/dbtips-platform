"""
Enhanced Supplementary Materials Utility Functions

This module contains improved helper functions for extracting and processing supplementary materials
from NXML/XML content with better section labeling.
"""

import logging
import re
from typing import List, Dict, Optional, Set
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


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
        
        # Sort by relevance score and return top contexts
        unique_descriptions.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
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
        if element.name in ['sec']:
            contexts.extend(self._extract_section_context_enhanced(element, section_type))
        elif element.name == 'abstract':
            context = self._extract_abstract_context(element, section_type)
            if context:
                contexts.append(context)
        elif element.name == 'p':
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
    
    def _extract_section_context_enhanced(self, section_element, section_type: str) -> List[Dict]:
        """
        Enhanced section context extraction with better subsection handling
        """
        contexts = []
        
        # Get section title
        title_elem = section_element.find('title')
        section_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Look for subsections first
        subsections = section_element.find_all('sec', recursive=False)
        if subsections:
            for subsec in subsections:
                subsec_contexts = self._extract_subsection_context(subsec, section_type, section_title)
                contexts.extend(subsec_contexts)
        
        # Then look for direct paragraphs in this section
        direct_paragraphs = []
        for child in section_element.children:
            if hasattr(child, 'name') and child.name == 'p':
                direct_paragraphs.append(child)
        
        for p in direct_paragraphs:
            p_text = p.get_text(separator=' ', strip=True)
            if self._contains_supplementary_mentions(p_text):
                context = {
                    'text': p_text,
                    'section_type': section_type,
                    'section_title': section_title,
                    'tag_name': 'p',
                    'relevance_score': self._calculate_relevance_score(p_text),
                    'char_length': len(p_text)
                }
                contexts.append(context)
        
        return contexts
    
    def _extract_subsection_context(self, subsection, parent_section_type: str, parent_title: str) -> List[Dict]:
        """
        Extract context from subsections with proper labeling
        """
        contexts = []
        
        # Get subsection title
        title_elem = subsection.find('title')
        subsection_title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Combine parent and subsection titles
        full_section_title = f"{parent_title} - {subsection_title}" if parent_title and subsection_title else (subsection_title or parent_title)
        
        # Find paragraphs in this subsection
        paragraphs = subsection.find_all('p')
        for p in paragraphs:
            p_text = p.get_text(separator=' ', strip=True)
            if self._contains_supplementary_mentions(p_text):
                context = {
                    'text': p_text,
                    'section_type': parent_section_type,
                    'section_title': full_section_title,
                    'tag_name': 'p',
                    'relevance_score': self._calculate_relevance_score(p_text),
                    'char_length': len(p_text)
                }
                contexts.append(context)
        
        return contexts
    
    def _extract_abstract_context(self, abstract_element, section_type: str) -> Optional[Dict]:
        """
        Extract context from abstract with special handling
        """
        abstract_text = abstract_element.get_text(separator=' ', strip=True)
        
        if not self._contains_supplementary_mentions(abstract_text):
            return None
        
        # For abstracts, extract only the relevant sentences
        sentences = re.split(r'[.!?]+', abstract_text)
        relevant_sentences = []
        
        for sentence in sentences:
            if self._contains_supplementary_mentions(sentence):
                relevant_sentences.append(sentence.strip())
        
        if not relevant_sentences:
            return None
        
        context_text = '. '.join(relevant_sentences) + '.'
        
        return {
            'text': context_text,
            'section_type': section_type,
            'section_title': 'Abstract',
            'tag_name': 'abstract',
            'relevance_score': self._calculate_relevance_score(context_text),
            'char_length': len(context_text)
        }
    
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
        
        # Get previous sibling if it's also a paragraph
        prev_sibling = paragraph_element.find_previous_sibling('p')
        if prev_sibling:
            prev_text = prev_sibling.get_text(separator=' ', strip=True)
            if len(prev_text) < 300:  # Only include if not too long
                context_parts.append(prev_text)
        
        # Add the main paragraph
        context_parts.append(para_text)
        
        # Get next sibling if it's also a paragraph
        next_sibling = paragraph_element.find_next_sibling('p')
        if next_sibling:
            next_text = next_sibling.get_text(separator=' ', strip=True)
            if len(next_text) < 300:  # Only include if not too long
                context_parts.append(next_text)
        
        context_text = " ".join(context_parts)
        
        return {
            'text': context_text,
            'section_type': section_type,
            'section_title': section_title,
            'tag_name': 'p',
            'relevance_score': self._calculate_relevance_score(para_text),
            'char_length': len(context_text)
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
            'tag_name': 'caption',
            'parent_element': parent_fig.name if parent_fig else None,
            'relevance_score': self._calculate_relevance_score(caption_text),
            'char_length': len(context_text)
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
            'relevance_score': self._calculate_relevance_score(element_text),
            'char_length': len(element_text)
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
    
    def _calculate_relevance_score(self, text: str) -> float:
        """
        Calculate a relevance score for the context based on content quality
        """
        if not text:
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # Base score for having supplementary mentions
        supplementary_keywords = [
            'supplementary material', 'supplementary materials', 'supplementary data',
            'supplemental material', 'supplemental materials', 'supplemental data',
            'supplementary information', 'supplemental information'
        ]
        
        for keyword in supplementary_keywords:
            if keyword in text_lower:
                score += 1.0
        
        # Bonus for descriptive content
        descriptive_terms = [
            'contains', 'includes', 'provides', 'presents', 'shows', 'describes',
            'details', 'analysis', 'results', 'data', 'methods', 'procedures'
        ]
        
        for term in descriptive_terms:
            if term in text_lower:
                score += 0.3
        
        # Bonus for mentioning specific file types or data types
        file_indicators = [
            'table', 'figure', 'dataset', 'spreadsheet', 'document',
            'protocol', 'guideline', 'questionnaire', 'survey'
        ]
        
        for indicator in file_indicators:
            if indicator in text_lower:
                score += 0.4
        
        # Length-based scoring
        text_length = len(text)
        if text_length < 30:
            score *= 0.3
        elif text_length > 1500:
            score *= 0.7
        elif 80 <= text_length <= 600:
            score *= 1.3
        
        return round(max(score, 0.0), 2)
    
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
                title = self._extract_clean_title(supp_mat_tag)
                url = self._build_supplementary_url_from_href(href, pmcid)
                return {'url': url, 'title': title, 'original_href': href}
        
        ext_link = supp_mat_tag.find('ext-link')
        if ext_link:
            href = ext_link.get('xlink:href') or ext_link.get('href')
            if href and self._is_supplementary_file_url(href):
                title = self._extract_clean_title(supp_mat_tag)
                return {'url': href, 'title': title, 'original_href': href}
        
        return None
    
    def _extract_materials_from_genuine_section(self, section, pmcid: str) -> List[Dict]:
        """Extract materials from sections that are genuinely about supplementary materials"""
        materials = []
        all_links = section.find_all(['ext-link', 'media'])
        for link in all_links:
            href = link.get('xlink:href') or link.get('href') or ''
            if href and self._is_supplementary_file_url(href):
                title = self._extract_clean_title(link.parent if link.parent else link)
                url = href if href.startswith('http') else self._build_supplementary_url_from_href(href, pmcid)
                materials.append({'url': url, 'title': title, 'original_href': href})
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
    
    def _extract_clean_title(self, element) -> str:
        """Extract a clean title for supplementary material"""
        title = ""
        caption_selectors = ['caption', 'title', 'label']
        for selector in caption_selectors:
            caption_elem = element.find(selector)
            if caption_elem:
                caption_text = caption_elem.get_text(strip=True)
                if caption_text and len(caption_text) > 5:
                    title = caption_text
                    break
        
        if not title:
            element_text = element.get_text(strip=True)
            if element_text and len(element_text) > 10 and not self._looks_like_filename(element_text):
                title = element_text[:200]
        
        if title:
            title = re.sub(r'\s+', ' ', title.strip())
            title = re.sub(r'(Download|View|Click here)[^.]*\.', '', title, flags=re.IGNORECASE)
            title = title.strip()
        
        return title or "Supplementary Material"
    
    def _looks_like_filename(self, text: str) -> bool:
        """Check if text looks like a filename rather than a title"""
        if not text:
            return False
        file_extensions = ['.xls', '.xlsx', '.doc', '.docx', '.pdf', '.zip', 
                          '.csv', '.txt', '.xml', '.json', '.png', '.jpg', '.tif']
        has_extension = any(ext in text.lower() for ext in file_extensions)
        is_short = len(text) < 50
        few_spaces = text.count(' ') < 3
        return has_extension and is_short and few_spaces