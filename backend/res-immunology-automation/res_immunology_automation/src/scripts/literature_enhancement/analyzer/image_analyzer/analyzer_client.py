import os
import json
import re
import logging
import asyncio
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)

class MedGemmaPathwayFilter:
    """
    MedGemma-based filter to determine if images show disease pathways or mechanisms
    This is the filtering stage before detailed content analysis
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.getenv('username')
        self.password = password or os.getenv('password')

        if not self.username or not self.password:
            raise ValueError("LDAP credentials not found in environment variables")

    def get_system_prompt(self) -> str:
        """Concise system prompt for pathway filtering"""
        return """You are a biomedical image expert. Determine if this image shows disease pathways or mechanisms.

RETURN TRUE for:
- Disease pathway diagrams with arrows/connections
- Drug mechanism flowcharts  
- Metabolic/signaling pathway maps
- Network diagrams showing biological interactions
- Schematic disease processes with directional flow

RETURN FALSE for:
- Data plots, bar charts, statistical graphs
- Basic microscopy without pathway annotations
- Simple experimental procedures
- Patient demographic tables
- Individual protein structures without interactions

Look for visual pathway indicators: arrows, connecting lines, flow diagrams, network structures.

Return only this JSON format:
{
  "is_disease_pathway": true/false,
  "confidence": "high/medium/low", 
  "reasoning": "Brief explanation"
}"""

    def get_user_prompt(self, caption: str) -> str:
        """Concise user prompt for pathway filtering"""
        caption_text = f"Caption: {caption.strip()}" if caption and caption.strip() else "No caption available"
        
        return f"""Analyze if this medical image shows disease pathways or mechanisms.

{caption_text}

Focus on pathway visual elements like arrows, connections, flow diagrams. Return the exact JSON format from system prompt."""

    # ... rest of the methods remain the same as original


class MedGemmaAnalyzer:
    """
    Optimized MedGemma analyzer for detailed content analysis
    This is used ONLY after images have been confirmed as pathway-relevant by the filter
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.getenv('username')
        self.password = password or os.getenv('password')

        if not self.username or not self.password:
            raise ValueError("LDAP credentials not found in environment variables")

    def get_system_prompt(self) -> str:
        """Concise system prompt for content analysis"""
        return """Extract biomedical information from this confirmed pathway image.

Extract in 5 categories:

1. **Genes**: Only official human gene symbols (HGNC format like PAH, TH, TPH1). Not metabolites or amino acids.

2. **drugs**: Pharmaceutical compounds, therapeutic agents, drug names.

3. **keywords**: All other medical terms - diseases, metabolites, amino acids, techniques, biomarkers.

4. **process**: Main biological process shown (e.g., "phenylalanine metabolism", "insulin signaling").

5. **insights**: Clinical relevance, therapeutic implications, key findings from the image.

Rules:
- Extract only what's visible in the image
- Use "not mentioned" if category is empty
- Be thorough but concise

Return only this JSON:
{
  "Genes": "comma-separated gene symbols or 'not mentioned'",
  "drugs": "comma-separated drug names or 'not mentioned'",
  "keywords": "comma-separated medical terms or 'not mentioned'",
  "process": "biological process description or 'not mentioned'",
  "insights": "clinical insights or 'not mentioned'"
}"""

    def get_user_prompt(self, caption: str) -> str:
        """Concise user prompt for content analysis"""
        context = f"Caption: {caption}" if caption and caption != "No caption provided" else "No caption context"
        
        return f"""Extract comprehensive biomedical information from this pathway image.

{context}

Return analysis in the exact JSON format specified."""

    async def analyze_content(self, figure_data: Dict) -> Dict:
        """
        Analyze image content (assumes image has already passed filtering)
        
        Args:
            figure_data: Dictionary containing image information
            
        Returns:
            Dictionary with analysis results
        """
        caption = figure_data.get("caption") or figure_data.get("image_caption", "No caption provided")
        
        logger.info(f"MedGemma analyzing content for PMCID: {figure_data.get('pmcid', 'unknown')}")
        
        payload = {
            "img_url": figure_data["image_url"],
            "system": self.get_system_prompt(),
            "user": self.get_user_prompt(caption),
            "caption": ""  # Empty string as in working example
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LiteratureFigureAnalyzer/1.0"
        }

        auth = httpx.BasicAuth(self.username, self.password)

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
                logger.info(f"Sending content analysis request for: {figure_data.get('pmcid', 'unknown')}")
                
                response = await client.post(
                    "https://medgemma-server.own4.aganitha.ai:8443/generate",
                    json=payload,
                    headers=headers,
                    auth=auth
                )

                if response.status_code == 200:
                    result = response.json()
                    parsed = self.parse_analysis_response(result, figure_data)
                    logger.info(f"Successfully analyzed content for: {figure_data.get('pmcid', 'unknown')}")
                    return parsed
                else:
                    logger.error("MedGemma API returned status %d: %s", response.status_code, response.text[:200])
                    return self._error_response(f"HTTP {response.status_code} error", "analysis_error")
                    
        except httpx.TimeoutException:
            logger.error("MedGemma API timeout for %s after 300 seconds", figure_data.get("pmcid", "unknown"))
            return self._error_response("MedGemma API timeout after 300 seconds", "analysis_error")
        except httpx.ConnectError:
            logger.error("MedGemma connection error for %s", figure_data.get("pmcid", "unknown"))
            return self._error_response("MedGemma connection error", "analysis_error")
        except Exception as exc:
            logger.error("MedGemma analysis failed for %s: %s", figure_data.get("pmcid", "unknown"), exc)
            return self._error_response(str(exc), "analysis_error")

    def parse_analysis_response(self, result: Dict, figure_data: Dict) -> Dict:
        """Parse MedGemma response and return database-compatible fields"""
        # Initialize with "not mentioned" defaults
        extracted = {
            "keywords": "not mentioned",
            "insights": "not mentioned", 
            "Genes": "not mentioned",
            "drugs": "not mentioned",
            "process": "not mentioned",
            "error_message": None,
            "status": result.get("status", "unknown")
        }

        analysis = None
        
        # Handle the response structure
        if result.get("status") == "success":
            # Try content field first
            if "content" in result:
                content = result["content"]
                if isinstance(content, dict):
                    analysis = content
                    logger.info("Using content field from MedGemma response")
            
            # Then try raw_response field
            elif "raw_response" in result:
                try:
                    raw_response = result["raw_response"].strip()
                    
                    # Remove markdown code blocks if present
                    if raw_response.startswith("```json") and raw_response.endswith("```"):
                        raw_response = raw_response[7:-3].strip()
                    elif raw_response.startswith("```") and raw_response.endswith("```"):
                        raw_response = raw_response[3:-3].strip()
                    
                    # Try to parse as JSON
                    analysis = json.loads(raw_response)
                    logger.info("Successfully parsed JSON from MedGemma raw_response")
                    
                except json.JSONDecodeError as e:
                    # Try to extract JSON object from the raw response
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw_response, re.DOTALL)
                    if json_match:
                        try:
                            json_str = json_match.group()
                            analysis = json.loads(json_str)
                            logger.info("Successfully extracted and parsed JSON from raw response")
                        except json.JSONDecodeError:
                            extracted["error_message"] = f"Failed to parse extracted JSON: {str(e)}"
                            extracted["status"] = "analysis_error"
                            logger.error(f"JSON parsing error: {str(e)}")
                    else:
                        extracted["error_message"] = "No valid JSON found in response"
                        extracted["status"] = "analysis_error"
                        logger.warning("No valid JSON found in raw response")

        # Update extracted data with analysis results
        if analysis and isinstance(analysis, dict):
            try:
                # Handle different possible field names from the API
                field_mappings = {
                    "Genes": ["Genes", "genes", "gene_names", "gene"],
                    "drugs": ["drugs", "drug_names", "drug", "medications"],
                    "keywords": ["keywords", "terms", "medical_terms"],
                    "process": ["process", "biological_process", "pathway"],
                    "insights": ["insights", "clinical_insights", "findings", "significance"]
                }
                
                for db_field, possible_fields in field_mappings.items():
                    value = None
                    for field in possible_fields:
                        if field in analysis:
                            value = analysis[field]
                            break
                    
                    if value:
                        if isinstance(value, list):
                            # Convert list to comma-separated string
                            cleaned_value = ", ".join([str(v).strip() for v in value if str(v).strip()])
                            extracted[db_field] = self._clean_field(cleaned_value)
                        else:
                            extracted[db_field] = self._clean_field(str(value))
                    else:
                        extracted[db_field] = "not mentioned"
                
                # Set status to analyzed if successful and no error message
                if not extracted.get("error_message"):
                    extracted["status"] = "analyzed"
                    logger.info("Content analysis completed successfully")
                    
                logger.debug(f"Extracted genes: {extracted['Genes']}")
                logger.debug(f"Extracted keywords: {extracted['keywords']}")
                
            except Exception as e:
                extracted["error_message"] = f"Error processing analysis fields: {str(e)}"
                extracted["status"] = "analysis_error"
                logger.error(f"Error processing analysis fields: {str(e)}")
        else:
            if not extracted.get("error_message"):
                extracted["error_message"] = "Invalid or empty analysis data"
                extracted["status"] = "analysis_error"

        return extracted

    def _clean_field(self, field_value: str) -> str:
        """Clean and validate individual field values"""
        if not field_value or not isinstance(field_value, str):
            return "not mentioned"
        
        cleaned = field_value.strip()
        if not cleaned or cleaned.lower() in ["", "n/a", "none", "null", "not mentioned"]:
            return "not mentioned"
        
        # Remove quotes and extra whitespace
        cleaned = re.sub(r'^["\']|["\']$', '', cleaned).strip()
        
        # For comma-separated values, clean each item
        if ',' in cleaned:
            items = [item.strip() for item in cleaned.split(',') if item.strip()]
            # Remove duplicates while preserving order
            unique_items = []
            seen = set()
            for item in items:
                item_lower = item.lower()
                if item_lower not in seen and len(item) > 1:
                    unique_items.append(item)
                    seen.add(item_lower)
            
            if unique_items:
                return ", ".join(unique_items[:10])  # Limit to 10 items
            else:
                return "not mentioned"
        else:
            return cleaned if len(cleaned) > 1 else "not mentioned"

    def _error_response(self, error: str, status: str) -> Dict:
        """Return error response for analysis failures"""
        return {
            "keywords": "not mentioned",
            "insights": "not mentioned", 
            "Genes": "not mentioned",
            "drugs": "not mentioned",
            "process": "not mentioned",
            "error_message": error,
            "status": status
        }