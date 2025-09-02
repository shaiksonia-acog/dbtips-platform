#openai_filter.py (Refactored with new retry mechanism)
import os
import json
import re
import logging
from typing import Dict, Optional
from openai import OpenAI
from ..retry_decorators import sync_api_retry, PipelineStopException, ContinueToNextRecordException
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)

class OpenAIPathwayFilter:
    """
    OpenAI GPT-4o-mini based filter to determine if captions describe disease pathways or mechanisms
    Caption-only filtering without image processing
    Enhanced with robust retry mechanism and pipeline error handling
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

* **Others** → captions that do not describe pathways (e.g., imaging data, clinical results, charts, survival curves, histology, structural models, experimental results, graphs, plots, bar graph, box plot, panels, etc.).

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
}

Important clarification:
- If the caption mainly reports **data, measurements, expression levels, statistical tests, or results shown as bar graphs, box plots, or panels**, classify as **Others** (even if specific proteins or signaling molecules are mentioned).
- Only classify as **Pathway figures** if the caption explicitly describes a **mechanism, pathway diagram, molecular interactions, or proposed disease model**.
"""


    def get_classification_user_prompt(self, caption: str) -> str:
        """User prompt for pathway classification"""
        caption_text = caption.strip() if caption and caption.strip() and caption.lower() not in ["no caption provided", "no caption", "n/a"] else "No caption available"
    
        return f"""Analyze this biomedical caption for disease pathways/mechanisms.

Caption: {caption_text}

INSTRUCTIONS:
1. Examine the caption for pathway terminology, mechanism descriptions, process words
2. Look for terms indicating molecular mechanisms, signaling pathways, disease processes
3. Distinguish between pathway descriptions vs. clinical data, imaging, histology, charts, graphs, plots, panels

INCLUDE: Pathway figures - captions describing mechanisms, signaling, interactions, processes
EXCLUDE: Clinical scans, histology, data charts, survival curves, structural models without mechanisms, experimental results, graphs, plots, bar graphs, box plots, panels

Additional clarification:
- Mentions of proteins, receptors, cytokines, or signaling molecules **in the context of expression levels, assays, or experimental measurements** should be classified as **Others** unless a pathway/interaction is explicitly described.
- Only classify as **Pathway figures** when the caption presents a mechanistic or pathway-level explanation (e.g., "proposed mechanism", "signaling cascade", "schematic diagram of interactions").
"""


    @sync_api_retry(max_retries=3, base_delay=1.0, backoff_multiplier=2.0)
    def _call_openai_api(self, caption: str) -> dict:
        """
        Wrapped OpenAI API call with retry mechanism
        This is the core API call that will be retried
        """
        try:
            logger.debug(f"Making OpenAI API call for caption analysis")
            
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
            return self.parse_filter_response(result_text, caption)
            
        except Exception as e:
            # Convert OpenAI specific exceptions to requests exceptions for consistent handling
            if "timeout" in str(e).lower():
                import requests
                raise requests.exceptions.Timeout(str(e)) from e
            elif any(code in str(e) for code in ["400", "401", "403", "404", "500", "502", "503"]):
                import requests
                raise requests.exceptions.HTTPError(str(e)) from e
            else:
                raise  # Re-raise as-is for other exceptions

    def filter_caption(self, caption: str) -> Dict:
        """
        Filter caption using OpenAI GPT-4o-mini to determine if it describes disease pathways
        Enhanced with retry mechanism and proper exception handling
        
        Args:
            caption: Caption text to analyze
            
        Returns:
            Dict with filtering results matching pipeline expectations
            
        Raises:
            PipelineStopException: For critical errors that should stop the pipeline
            ContinueToNextRecordException: For timeout errors that should skip current record
        """
        try:
            logger.debug("Determining if caption describes disease pathway using OpenAI...")
            
            # Use the retry-wrapped API call
            parsed = self._call_openai_api(caption)
            logger.info(f"Is Pathway figure?: {parsed.get('is_disease_pathway')}")
            return parsed
            
        except ContinueToNextRecordException:
            # Timeout errors - skip current record and continue
            logger.error("OpenAI filtering timed out after retries - continuing to next record")
            return self._error_response("OpenAI API timeout after retries", "filter_timeout")
            
        except PipelineStopException as e:
            # Critical errors - stop the entire pipeline
            logger.error(f"OpenAI filtering failed critically: {str(e)}")
            raise RuntimeError(f"OpenAI filtering failed: {str(e)}") from e
                        
        except Exception as e:
            # Unexpected errors - also stop pipeline for safety
            logger.error(f"Unexpected OpenAI filtering error: {str(e)}")
            raise RuntimeError(f"Unexpected OpenAI filtering error: {str(e)}") from e

    def parse_filter_response(self, result_text: str, caption: str) -> Dict:
        """Parse OpenAI filtering response - UNCHANGED"""
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
    
    def _error_response(self, error: str, status: str = "filter_error") -> Dict:
        """Return error response for filtering failures - UNCHANGED"""
        return {
            "is_disease_pathway": False,  # Conservative approach - default to False on error
            "confidence": "error",
            "reasoning": f"OpenAI filtering failed: {error}",
            "status": status, 
            "error_message": error,
            "filter_method": "openai_gpt4omini_caption"
        }

    def batch_filter_captions(self, captions_data: list) -> list:
        """
        Filter multiple captions in batch with rate limiting
        Enhanced with proper exception handling
        
        Args:
            captions_data: List of caption strings or image data dictionaries
            
        Returns:
            List of filtering results
            
        Raises:
            RuntimeError: If critical errors occur that should stop the pipeline
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
                
                # Filter the caption - this may raise exceptions
                filter_result = self.filter_caption(caption)
                results.append(filter_result)
                
                # Add delay to respect OpenAI rate limits
                if i < len(captions_data) - 1:  # Don't delay after last item
                    import time
                    time.sleep(1.0)  # 1 second delay for OpenAI
                    
            except RuntimeError:
                # Re-raise pipeline stopping errors
                raise
            except Exception as e:
                logger.error(f"Error filtering caption {i}: {str(e)}")
                # For unexpected errors in batch processing, stop the pipeline
                raise RuntimeError(f"Batch filtering failed at item {i}: {str(e)}") from e
        
        return results