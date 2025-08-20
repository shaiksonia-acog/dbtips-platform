import os
import json
import re
import logging
from typing import Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIPathwayFilter:
    """
    OpenAI GPT-4o-mini based filter to determine if captions describe disease pathways or mechanisms
    Caption-only filtering without image processing
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"

    def get_classification_system_prompt(self) -> str:
        """System prompt for pathway classification based on captions only"""
        return """You are given captions of figures from biomedical/clinical publications. Your task is to classify each caption into one of the following categories:

* **Pathway figures** → captions describing molecular mechanisms, biological signaling pathways, disease mechanisms, or interactions between genes, proteins, metabolites, or drugs (e.g., "Proposed signaling pathway of TGF-β in fibrosis").

* **Others** → captions that do not describe pathways (e.g., imaging data, clinical results, charts, survival curves, histology, structural models, etc.).

Examples:
* Caption: "Schematic representation of the NF-κB signaling pathway in inflammatory bowel disease." → **Pathway figures**
* Caption: "Kaplan–Meier survival curve of patients with stage III colorectal cancer." → **Others**
* Caption: "Diagram illustrating the crosstalk between PI3K/AKT and MAPK pathways in breast cancer." → **Pathway figures**
* Caption: "Representative MRI scans showing liver fibrosis progression." → **Others**

Return only JSON:
{
  "is_disease_pathway": true/false,
  "confidence": "high/medium/low",
  "reasoning": "Brief explanation based on caption analysis"
}"""

    def get_classification_user_prompt(self, caption: str) -> str:
        """User prompt for pathway classification"""
        caption_text = caption.strip() if caption and caption.strip() and caption.lower() not in ["no caption provided", "no caption", "n/a"] else "No caption available"
    
        return f"""Analyze this biomedical caption for disease pathways/mechanisms.

Caption: {caption_text}

INSTRUCTIONS:
1. Examine the caption for pathway terminology, mechanism descriptions, process words
2. Look for terms indicating molecular mechanisms, signaling pathways, disease processes
3. Distinguish between pathway descriptions vs. clinical data, imaging, histology, charts

INCLUDE: Pathway figures - captions describing mechanisms, signaling, interactions, processes
EXCLUDE: Clinical scans, histology, data charts, survival curves, structural models without mechanisms

Return exact JSON format with reasoning based on caption analysis."""

    def filter_caption(self, caption: str) -> Dict:
        """
        Filter caption using OpenAI GPT-4o-mini to determine if it describes disease pathways
        
        Args:
            caption: Caption text to analyze
            
        Returns:
            Dict with filtering results matching pipeline expectations
        """
        try:
            logger.info("Determining if caption describes disease pathway using OpenAI...")
            
            # Call OpenAI API with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug(f"OpenAI API filtering attempt {attempt + 1}/{max_retries}")
                    
                    response = self.client.chat.completions.create(
                        model=self.model,
                        temperature=0,
                        max_tokens=300,
                        messages=[
                            {"role": "system", "content": self.get_classification_system_prompt()},
                            {"role": "user", "content": self.get_classification_user_prompt(caption)}
                        ],
                    )

                    result_text = response.choices[0].message.content.strip()
                    parsed = self.parse_filter_response(result_text, caption)
                    logger.info(f"Is Pathway figure?: {parsed.get('is_disease_pathway')}")
                    return parsed
                
                except Exception as e:
                    error_msg = f"OpenAI API error: {str(e)} (attempt {attempt + 1})"
                    logger.warning(error_msg)
                    if attempt == max_retries - 1:
                        return self._error_response(error_msg)
                    else:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.info(f"Retrying in {wait_time} seconds...")
                        import time
                        time.sleep(wait_time)
                        continue
                        
        except Exception as e:
            logger.error(f"OpenAI filtering failed for caption: {str(e)}")
            return self._error_response(str(e))

    def parse_filter_response(self, result_text: str, caption: str) -> Dict:
        """Parse OpenAI filtering response"""
        try:
            # Try direct JSON parse first
            try:
                content = json.loads(result_text)
                logger.debug("Successfully parsed JSON from OpenAI response")
            except json.JSONDecodeError:
                # Try to extract JSON object from the response
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_text, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group()
                        content = json.loads(json_str)
                        logger.debug("Successfully extracted and parsed JSON from response")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON extraction parsing error: {str(e)}")
                        return self._error_response(f"Failed to parse extracted JSON: {str(e)}")
                else:
                    logger.error("No valid JSON found in OpenAI response")
                    return self._error_response("No valid JSON found in response")

            # Process the extracted content
            if content and isinstance(content, dict):
                is_pathway = content.get("is_disease_pathway", False)
                confidence = content.get("confidence", "low")
                reasoning = content.get("reasoning", "No reasoning provided")
                
                # Validate boolean value
                if isinstance(is_pathway, str):
                    is_pathway = is_pathway.lower() in ["true", "yes", "1"]
                
                logger.debug(f"OpenAI filter result: {is_pathway} (confidence: {confidence})")
                logger.debug(f"Reasoning: {reasoning}")
                
                return {
                    "is_disease_pathway": bool(is_pathway),
                    "confidence": str(confidence),
                    "reasoning": str(reasoning),
                    "status": "filtered_success",
                    "error_message": None,
                    "filter_method": "openai_gpt4omini_caption"
                }
            else:
                logger.error("Invalid or empty content from OpenAI response")
                return self._error_response("Invalid or empty content from OpenAI response")
                
        except Exception as e:
            logger.error(f"Error parsing OpenAI filter response: {str(e)}")
            return self._error_response(f"Response parsing error: {str(e)}")
    
    def _error_response(self, error: str) -> Dict:
        """Return error response for filtering failures"""
        return {
            "is_disease_pathway": False,  # Conservative approach - default to False on error
            "confidence": "error",
            "reasoning": f"OpenAI filtering failed: {error}",
            "status": "filter_error", 
            "error_message": error,
            "filter_method": "openai_gpt4omini_caption"
        }

    def batch_filter_captions(self, captions_data: list) -> list:
        """
        Filter multiple captions in batch with rate limiting
        
        Args:
            captions_data: List of caption strings or image data dictionaries
            
        Returns:
            List of filtering results
        """
        results = []
        
        for i, item in enumerate(captions_data):
            try:
                # Handle both string captions and dict with caption
                if isinstance(item, str):
                    caption = item
                elif isinstance(item, dict):
                    caption = item.get("image_caption", "")
                else:
                    caption = str(item)
                
                # Filter the caption
                filter_result = self.filter_caption(caption)
                results.append(filter_result)
                
                # Add delay to respect OpenAI rate limits
                if i < len(captions_data) - 1:  # Don't delay after last item
                    import time
                    time.sleep(1.0)  # 1 second delay for OpenAI
                    
            except Exception as e:
                logger.error(f"Error filtering caption {i}: {str(e)}")
                results.append(self._error_response(str(e)))
        
        return results