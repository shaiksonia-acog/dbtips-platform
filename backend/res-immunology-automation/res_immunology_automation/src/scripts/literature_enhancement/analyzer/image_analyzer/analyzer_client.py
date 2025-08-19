#analyzer_client (using med gemma model via httpx and different codebase)
import os
import json
import re
import logging
import asyncio
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)

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
        """Optimized system prompt - shorter but precise"""
        return """Extract biomedical information from this pathway image in 5 categories:

1. **genes**: Official human gene symbols only (HGNC format: PAH, TH, TPH1). Exclude metabolites, amino acids, proteins.

2. **drugs**: Pharmaceutical compounds, therapeutic agents only.

3. **keywords**: Disease names, metabolites, amino acids, techniques, biomarkers.

4. **process**: Main biological process (e.g., "phenylalanine metabolism").

5. **insights**: Clinical relevance visible in the image.

Rules: Extract only visible terms. Use "not mentioned" if empty. No guessing.

Return JSON:
{
  "genes": "gene symbols or 'not mentioned'",
  "drugs": "drug names or 'not mentioned'", 
  "keywords": "medical terms or 'not mentioned'",
  "process": "biological process or 'not mentioned'",
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
            "system": self.get_system_prompt(),
            "user": self.get_user_prompt(caption),
            "img_url": figure_data["image_url"],
            "caption": caption if caption != "No caption provided" else None,
            "max_tokens": 128000
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
                    logger.debug(f"MedGemma raw response: {result}")
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
            "genes": "not mentioned",
            "drugs": "not mentioned",
            "process": "not mentioned",
            "error_message": None,
            "status": result.get("status", "unknown")
        }

        analysis = None
        pmcid = figure_data.get('pmcid', 'unknown')
        
        # Handle the response structure based on your server's format
        if result.get("status") == "success":
            logger.info(f"MedGemma returned success status for {pmcid}")
            
            # Check for 'content' field first (direct structured response)
            if "content" in result and result["content"]:
                content = result["content"]
                logger.debug(f"Found content field: {type(content)} - {str(content)[:200]}")
                
                if isinstance(content, dict):
                    analysis = content
                    logger.info(f"Using structured content dict for {pmcid}")
                elif isinstance(content, str):
                    # Try to parse string content as JSON
                    analysis = self._parse_json_from_string(content, pmcid)
                else:
                    logger.warning(f"Unexpected content type: {type(content)} for {pmcid}")
            
            # Fallback to raw_response field
            if not analysis and "raw_response" in result and result["raw_response"]:
                logger.info(f"Attempting to parse raw_response for {pmcid}")
                analysis = self._parse_json_from_string(result["raw_response"], pmcid)
            
            # Last resort: check other possible response fields
            if not analysis:
                for field in ["generated_text", "text", "output", "response"]:
                    if field in result and result[field]:
                        logger.info(f"Attempting to parse {field} field for {pmcid}")
                        analysis = self._parse_json_from_string(result[field], pmcid)
                        if analysis:
                            break

        # Update extracted data with analysis results
        if analysis and isinstance(analysis, dict):
            try:
                # Handle different possible field names from the API
                field_mappings = {
                    "genes": ["genes", "genes", "gene_names", "gene", "gene_symbols"],
                    "drugs": ["drugs", "drug_names", "drug", "medications", "compounds"],
                    "keywords": ["keywords", "terms", "medical_terms", "biomarkers"],
                    "process": ["process", "biological_process", "pathway", "mechanism"],
                    "insights": ["insights", "clinical_insights", "findings", "significance", "clinical_relevance"]
                }
                
                found_fields = 0
                for db_field, possible_fields in field_mappings.items():
                    value = None
                    for field in possible_fields:
                        if field in analysis:
                            value = analysis[field]
                            found_fields += 1
                            break
                    
                    if value:
                        if isinstance(value, list):
                            # Convert list to comma-separated string
                            cleaned_value = ", ".join([str(v).strip() for v in value if str(v).strip()])
                            extracted[db_field] = self._clean_field(cleaned_value)
                        else:
                            extracted[db_field] = self._clean_field(str(value))
                    
                    # Log what we found
                    logger.debug(f"Field {db_field}: {extracted[db_field]}")
                
                # Set status to analyzed if we found at least some fields
                if found_fields > 0 and not extracted.get("error_message"):
                    extracted["status"] = "analyzed"
                    logger.info(f"Content analysis completed successfully for {pmcid} ({found_fields} fields found)")
                else:
                    extracted["error_message"] = f"No recognizable fields found in analysis response (found keys: {list(analysis.keys())})"
                    extracted["status"] = "analysis_error"
                    logger.warning(f"No recognizable analysis fields found for {pmcid}")
                    
            except Exception as e:
                extracted["error_message"] = f"Error processing analysis fields: {str(e)}"
                extracted["status"] = "analysis_error"
                logger.error(f"Error processing analysis fields for {pmcid}: {str(e)}")
        else:
            if not extracted.get("error_message"):
                extracted["error_message"] = f"Invalid or empty analysis data. Response keys: {list(result.keys()) if isinstance(result, dict) else 'not dict'}"
                extracted["status"] = "analysis_error"
                logger.error(f"Invalid analysis data for {pmcid}: {extracted['error_message']}")

        return extracted

    def _parse_json_from_string(self, text: str, pmcid: str) -> Optional[Dict]:
        """Attempt to parse JSON from a text string with multiple strategies"""
        if not text or not isinstance(text, str):
            return None
        
        text = text.strip()
        logger.debug(f"Attempting to parse JSON from text for {pmcid}: {text[:200]}...")
        
        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Remove markdown code blocks
        cleaned_text = text
        if text.startswith("```json") and text.endswith("```"):
            cleaned_text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            cleaned_text = text[3:-3].strip()
        
        if cleaned_text != text:
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find JSON object with regex
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Simple nested braces
            r'\{.*?\}',  # Greedy match
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    result = json.loads(match.strip())
                    logger.info(f"Successfully extracted JSON using regex for {pmcid}")
                    return result
                except json.JSONDecodeError:
                    continue
        
        logger.warning(f"Failed to parse any JSON from response for {pmcid}")
        return None

    def _clean_field(self, field_value: str) -> str:
        """Clean and validate individual field values"""
        if not field_value or not isinstance(field_value, str):
            return "not mentioned"
        
        cleaned = field_value.strip()
        if not cleaned or cleaned.lower() in ["", "n/a", "none", "null", "not mentioned", "not available"]:
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
            "genes": "not mentioned",
            "drugs": "not mentioned",
            "process": "not mentioned",
            "error_message": error,
            "status": status
        }