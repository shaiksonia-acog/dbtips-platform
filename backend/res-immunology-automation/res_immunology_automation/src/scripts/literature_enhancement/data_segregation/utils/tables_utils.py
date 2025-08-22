import os
from openai import OpenAI
import re
import json
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any
from datetime import datetime
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
log = logging.getLogger(module_name)


api_key = os.getenv('OPENAI_API_KEY')

LLM = 'gpt-4o-mini'

class TablesExtractor:
    def extract_tables_from_nxml(self, raw_nxml: str, pmcid: str, pmid: str, 
                                disease: str, target: str, url: str) -> List[Dict]:
        """
        Extract tables from raw NXML/XML content (JATS format from PMC)
        
        Args:
            raw_nxml: Raw NXML content from ArticlesMetadata
            pmcid: PMC ID
            pmid: PubMed ID  
            disease: Disease name
            target: Target name
            url: Article URL
            
        Returns:
            List of table dictionaries
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

        tables: List[Dict] = []
        
        # JATS XML table selectors - look for table-wrap elements
        table_elements = soup.find_all("table-wrap")
        
        if not table_elements:
            log.debug("No table-wrap elements found in NXML for PMCID: %s", pmcid)
            return []

        for idx, table_wrap in enumerate(table_elements, start=1):
            try:
                # Find the actual table element within table-wrap
                table_elem = table_wrap.find("table")
                if not table_elem:
                    log.debug("No table element found in table-wrap %d for PMCID: %s", idx, pmcid)
                    continue
                
                # Extract table HTML for LLM analysis
                table_html = str(table_elem)
                
                # Extract table title using the improved function
                table_title = self._extract_table_title(table_wrap, idx)
                
                # Extract table description/caption from JATS XML structure
                description = self._extract_nxml_table_caption(table_wrap)
                
                if not description:
                    log.debug("No caption found for table %d in PMCID: %s", idx, pmcid)
                    description = ""

                # Get table ID if available
                table_id = table_wrap.get("id", f"table-{idx}")
                
                # Use LLM to extract table schema (headers only)
                try:
                    table_schema = self._extract_table_schema_with_llm(table_html)
                    # Add the programmatically extracted title to the schema

                    # filter empty schemas

                    table_schema["title"] = table_title
                except Exception as e:
                    log.warning("Failed to extract schema for table %d in PMCID %s: %s", idx, pmcid, e)
                    table_schema = {
                        "title": table_title,  # Include title even in error case
                        "column_headers": [],
                        "row_headers": [],
                        "error": f"Schema extraction failed: {str(e)}"
                    }
                if not description and "error" in table_schema:
                    continue
                
                if not description and not len(table_schema.get("column_headers")) and not len(table_schema.get("row_headers")):
                    continue

                tables.append({
                    "pmcid": pmcid,
                    "pmid": pmid,
                    "disease": disease,
                    "target": target,
                    "url": url,
                    "table_title": table_title,
                    "table_description": description,
                    "table_schema": json.dumps(table_schema, indent=2),
                    "table_id": table_id,
                    "extraction_timestamp": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                log.warning("Error processing table %d from PMCID %s: %s", idx, pmcid, e)
                continue
        
        log.info("Extracted %d tables from PMCID: %s", len(tables), pmcid)
        return tables
    
    def _extract_table_title(self, table_wrap_element, table_index: int) -> str:
        """Extract table title from document structure (JATS XML)"""
        
        # First try to get from label element (e.g., "Table 1", "Table 2")
        label_elem = table_wrap_element.find("label")
        if label_elem:
            label_text = label_elem.get_text(strip=True)
            # Clean and normalize label (e.g., "Table 1" -> "Table 1")
            if label_text:
                return label_text
        
        # Fallback to table ID if it contains table number info
        table_id = table_wrap_element.get("id", "")
        if table_id:
            # Extract table number from IDs like "table1", "T1", "tab1", etc.
            import re
            match = re.search(r'(?:table|tab|t)[-_]?(\d+)', table_id, re.IGNORECASE)
            if match:
                return f"Table {match.group(1)}"
        
        # Final fallback to sequential numbering
        return f"Table {table_index}"

    def _extract_table_schema_with_llm(self, table_html: str) -> Dict:
        """Use OpenAI LLM to extract table schema from HTML"""
        table_schema_prompt = f"""
        You are an expert in HTML table analysis. Your task is to extract ONLY the header information from HTML tables, preserving hierarchical relationships.

        IMPORTANT REQUIREMENTS:
        1. Extract ONLY column headers and row headers - NO data values from table body
        2. For column headers: 
           - Look for headers in <thead>, <th> elements, or first rows
           - Handle hierarchical headers with colspan (parent headers spanning multiple sub-headers)
           - Flatten hierarchy using "Parent > Child" format for sub-headers
           - If a header has no parent, list it as-is
        3. For row headers: Look for headers in the first column of each row, especially text in <strong>, <b>, or <th> tags
        4. Do NOT extract table title - this will be handled separately from the document structure
        5. Do NOT count rows or analyze table structure beyond headers
        6. REMOVE ALL HTML TAGS from header text - extract only the plain text content (strip <sub>, <sup>, <b>, <strong>, etc.)

        HIERARCHICAL HEADER HANDLING:
        - If "PMIT" spans 2 columns with sub-headers "Sub1" and "Sub2", output: ["PMIT > Sub1", "PMIT > Sub2"]
        - If "Methods" spans 3 columns with sub-headers "A", "B", "C", output: ["Methods > A", "Methods > B", "Methods > C"]  
        - If a column has no parent header, output as-is: ["Single Header"]
        - Use " > " as the separator between parent and child headers

        WHAT TO EXTRACT:
        - Column headers: All column names preserving parent-child relationships (plain text only, no HTML tags)
        - Row headers: Only if the first column contains consistent header-like text (plain text only, no HTML tags)

        WHAT NOT TO EXTRACT:
        - Table data/values from body cells
        - Row counts, spans, or structural metadata
        - Table titles or captions
        - HTML formatting tags like <sub>, <sup>, <b>, <strong>, etc.

        OUTPUT FORMAT (simple JSON only):
        {{
            "column_headers": ["Header1", "Parent > Child1", "Parent > Child2", "Header4"],
            "row_headers": ["RowHeader1", "RowHeader2"] 
        }}

        If no clear row headers exist in first column, return empty array: "row_headers": []

        HTML to analyze: {table_html}
        """
        openai_client = OpenAI(api_key=api_key)
        response = openai_client.chat.completions.create(
            model=LLM,
            messages=[
                {"role": "system", "content": "You are an expert in analyzing HTML table structures. Extract header information preserving parent-child relationships using 'Parent > Child' format."},
                {"role": "user", "content": table_schema_prompt}
            ],
            max_tokens=2048,
            temperature=0.1
        )

        response_content = response.choices[0].message.content
        
        # Clean up markdown formatting if present
        if "```json" in response_content:
            log.debug("Received markdown response")
            response_content = response_content.strip("```").replace("json", "", 1).strip()
        elif "```" in response_content:
            response_content = response_content.strip("```").strip()
        
        try:
            table_schema = json.loads(response_content)
            
            # Validate and clean the schema structure
            cleaned_schema = {
                "title": "",  # Will be populated by caller with programmatically extracted title
                "column_headers": [],
                "row_headers": []
            }
            
            # Ensure column_headers is a flat list of strings
            if "column_headers" in table_schema:
                if isinstance(table_schema["column_headers"], list):
                    for header in table_schema["column_headers"]:
                        if isinstance(header, str):
                            cleaned_header = self._clean_html_tags(header.strip())
                            cleaned_schema["column_headers"].append(cleaned_header)
                        elif isinstance(header, dict) and "header" in header:
                            cleaned_header = self._clean_html_tags(header["header"].strip())
                            cleaned_schema["column_headers"].append(cleaned_header)
                        elif isinstance(header, dict) and "name" in header:
                            cleaned_header = self._clean_html_tags(header["name"].strip())
                            cleaned_schema["column_headers"].append(cleaned_header)
            
            # Ensure row_headers is a flat list of strings  
            if "row_headers" in table_schema:
                if isinstance(table_schema["row_headers"], list):
                    for header in table_schema["row_headers"]:
                        if isinstance(header, str):
                            cleaned_header = self._clean_html_tags(header.strip())
                            cleaned_schema["row_headers"].append(cleaned_header)
                        elif isinstance(header, dict) and "value" in header:
                            cleaned_header = self._clean_html_tags(header["value"].strip())
                            cleaned_schema["row_headers"].append(cleaned_header)
                        elif isinstance(header, dict) and "header" in header:
                            cleaned_header = self._clean_html_tags(header["header"].strip())
                            cleaned_schema["row_headers"].append(cleaned_header)
            
            return cleaned_schema
            
        except json.JSONDecodeError as e:
            log.info("Failed to parse LLM response as JSON: %s", e)
            return {
                "title": "",  # Will be populated by caller
                "column_headers": [],
                "row_headers": [],
                "error": f"JSON parsing failed: {str(e)}", 
                "raw_response": response_content
            }
    
    def _clean_html_tags(self, text: str) -> str:
        """Remove HTML tags from text and clean up formatting"""
        if not text:
            return ""
        
        # Remove common HTML tags while preserving content
        # This handles <sub>, <sup>, <b>, <strong>, <i>, <em>, etc.
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up any leftover whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text.strip())
        
        # Handle common Unicode characters that might appear
        # Convert common Unicode minus/dash characters to regular dash
        clean_text = clean_text.replace('\u2212', '-')  # Unicode minus sign
        clean_text = clean_text.replace('\u2013', '-')  # En dash
        clean_text = clean_text.replace('\u2014', '-')  # Em dash
        
        return clean_text
    
    def _extract_nxml_table_caption(self, table_wrap_element) -> str:
        """Extract caption from JATS XML table-wrap element"""
        caption = ""
        
        # In JATS XML, table captions are typically in <caption> element within table-wrap
        caption_elem = table_wrap_element.find("caption")
        if caption_elem:
            # Get all text content from caption
            caption = caption_elem.get_text(strip=True, separator=" ")
            
        # If no caption element, try label + title
        if not caption:
            label_elem = table_wrap_element.find("label")
            title_elem = table_wrap_element.find("title")
            
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
    
    def _clean_caption(self, caption: str) -> str:
        """Clean and normalize caption text"""
        if not caption:
            return ""
        
        # Remove extra whitespace and normalize
        caption = re.sub(r'\s+', ' ', caption.strip())
        
        # Remove common prefixes like "Table 1.", "Tab. 1:", etc.
        caption = re.sub(r'^(Table|Tab\.?)\s*\d+[.\:\-\s]*', '', caption, flags=re.IGNORECASE)
        
        return caption.strip()

