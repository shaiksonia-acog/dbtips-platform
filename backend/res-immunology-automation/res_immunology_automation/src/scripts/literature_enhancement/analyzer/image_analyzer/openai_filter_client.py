import os
import json
import re
import logging
import asyncio
import base64
import requests
from typing import Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIPathwayFilter:
    """
    OpenAI GPT-4o-mini based filter to determine if images show disease pathways or mechanisms
    This replaces the MedGemmaPathwayFilter for filtering stage only
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"

    def get_classification_system_prompt(self) -> str:
        """System prompt for pathway classification"""
        return """You are an expert biomedical image classifier specialized in identifying disease pathway diagrams.

Analyze BOTH the image content and caption text to determine if this shows **disease pathways or mechanisms**.

Consider VISUAL elements AND textual context together:

TRUE (Disease Pathways):
- Pathway diagrams with arrows/flow connections
- Drug/molecular mechanisms with directional flow
- Metabolic/signaling cascades
- Disease process flowcharts
- Network diagrams showing biological relationships
- Caption mentions: "pathway", "mechanism", "cascade", "signaling", "process"

FALSE (Not Pathways):
- Radiology: MRI, CT, PET, X-ray, ultrasound images
- Histology/microscopy slides
- Clinical photographs
- Data plots: bar/line/scatter/pie charts, survival curves
- Tables, demographic data, statistical comparisons
- Isolated anatomical structures without process flow
- Caption mentions: "scan", "image", "histology", "microscopy", "data", "results"

KEY: Look for PROCESS FLOW (arrows, connections) in image AND pathway-related terms in caption.

Return only JSON:
{
  "is_disease_pathway": true/false,
  "confidence": "high/medium/low",
  "reasoning": "Brief explanation citing both visual and textual evidence"
}"""

    def get_classification_user_prompt(self, caption: str) -> str:
        """User prompt for pathway classification"""
        caption_text = f"Caption: {caption.strip()}" if caption and caption.strip() and caption.lower() not in ["no caption provided", "no caption", "n/a"] else "No caption available"
    
        return f"""Analyze this biomedical content for disease pathways/mechanisms.

{caption_text}

INSTRUCTIONS:
1. Examine the IMAGE for: arrows, flow diagrams, network connections, process steps
2. Examine the CAPTION for: pathway terminology, mechanism descriptions, process words
3. Combine both visual and textual evidence

EXCLUDE: Clinical scans (MRI/CT/X-ray), histology slides, data charts, tables, isolated structures

Focus on: Process diagrams with directional flow showing biological mechanisms

Return exact JSON format with reasoning that references both image content and caption analysis."""

    def download_and_encode_image(self, image_url: str) -> str:
        """Download image from URL and encode to base64"""
        try:
            # Headers to mimic a browser request and avoid 403 errors
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site"
            }
            
            # Add referer if it's an NCBI/PMC URL
            if "ncbi.nlm.nih.gov" in image_url or "pmc.ncbi.nlm.nih.gov" in image_url:
                headers["Referer"] = "https://www.ncbi.nlm.nih.gov/"
            
            # Use requests instead of httpx
            response = requests.get(image_url, headers=headers, timeout=60, allow_redirects=True)
            response.raise_for_status()
            
            # Verify we got image content
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning(f"Unexpected content type '{content_type}' for image {image_url}")
            
            # Encode image to base64
            image_data = response.content
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            logger.debug(f"Successfully downloaded and encoded image from {image_url} (size: {len(image_data)} bytes)")
            return encoded_image
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"403 Forbidden error for {image_url}. Server may be blocking automated requests.")
                # Try a different approach for 403 errors
                try:
                    # Brief delay before retry
                    import time
                    time.sleep(1)
                    
                    # Retry with minimal headers
                    simple_headers = {
                        "User-Agent": "Mozilla/5.0 (compatible; Academic Research Bot)",
                        "Accept": "*/*"
                    }
                    retry_response = requests.get(image_url, headers=simple_headers, timeout=60, allow_redirects=True)
                    retry_response.raise_for_status()
                    image_data = retry_response.content
                    encoded_image = base64.b64encode(image_data).decode('utf-8')
                    logger.info(f"Successfully downloaded image on retry: {image_url}")
                    return encoded_image
                except Exception as retry_e:
                    logger.error(f"Retry also failed for {image_url}: {str(retry_e)}")
                    raise e
            else:
                raise e
        except requests.exceptions.TooManyRedirects as e:
            logger.error(f"Too many redirects for image {image_url}: {str(e)}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error downloading image {image_url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error downloading/encoding image {image_url}: {str(e)}")
            raise

    def filter_image(self, image_url: str, caption: str = "") -> Dict:
        """
        Filter image using OpenAI GPT-4o-mini to determine if it shows disease pathways
        
        Args:
            image_url: URL of the image to analyze
            caption: Image caption text for context
            
        Returns:
            Dict with filtering results matching pipeline expectations
        """
        try:
            logger.info(f"OpenAI filtering image: {image_url[:50]}{'...' if len(image_url) > 50 else ''}")
            logger.debug(f"Caption context: '{caption[:100]}{'...' if len(caption) > 100 else ''}'")
            
            # Download and encode image
            encoded_image = self.download_and_encode_image(image_url)
            
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
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": self.get_classification_user_prompt(caption)},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                                ],
                            },
                        ],
                    )

                    result_text = response.choices[0].message.content.strip()
                    parsed = self.parse_filter_response(result_text, image_url)
                    logger.info(f"Successfully filtered image: {image_url[:50]}... - Result: {parsed.get('is_disease_pathway')}")
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
            logger.error(f"OpenAI filtering failed for {image_url[:50]}...: {str(e)}")
            return self._error_response(str(e))

    def parse_filter_response(self, result_text: str, image_url: str) -> Dict:
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
                
                logger.info(f"OpenAI filter result: {is_pathway} (confidence: {confidence})")
                logger.debug(f"Reasoning: {reasoning}")
                
                return {
                    "is_disease_pathway": bool(is_pathway),
                    "confidence": str(confidence),
                    "reasoning": str(reasoning),
                    "status": "filtered_success",
                    "error_message": None,
                    "filter_method": "openai_gpt4omini"
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
            "filter_method": "openai_gpt4omini"
        }

    def batch_filter_images(self, images_data: list) -> list:
        """
        Filter multiple images in batch with rate limiting
        
        Args:
            images_data: List of image data dictionaries
            
        Returns:
            List of filtering results
        """
        results = []
        
        for i, image_data in enumerate(images_data):
            try:
                image_url = image_data.get("image_url", "")
                caption = image_data.get("image_caption", "")
                
                # Filter the image
                filter_result = self.filter_image(image_url, caption)
                results.append(filter_result)
                
                # Add delay to respect OpenAI rate limits
                if i < len(images_data) - 1:  # Don't delay after last item
                    import time
                    time.sleep(1.0)  # 1 second delay for OpenAI
                    
            except Exception as e:
                logger.error(f"Error filtering image {i}: {str(e)}")
                results.append(self._error_response(str(e)))
        
        return results