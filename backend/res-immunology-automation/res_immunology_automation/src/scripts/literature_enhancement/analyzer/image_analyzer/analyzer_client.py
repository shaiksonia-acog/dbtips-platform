import json
import re
import logging
import asyncio
import google.generativeai as genai
from typing import Dict, Optional, List
from enum import Enum
import httpx
from abc import ABC, abstractmethod
from pydantic import BaseModel
import os
from ..retry_decorators import async_api_retry, PipelineStopException, ContinueToNextRecordException
import requests
from PIL import Image
from io import BytesIO

module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
logger = logging.getLogger(module_name)
FIGURE_ANALYSIS_MODEL = os.getenv("FIGURE_ANALYSIS_MODEL")

class GPUMemoryException(Exception):
    """Exception for GPU memory related issues that require model reload"""
    pass

class ModelLoadException(Exception):
    """Exception for model loading failures"""
    pass

class ImageDataModel(BaseModel):
    pmcid: str
    pmid: str
    disease: str
    target: str
    image_url: str
    image_caption: Optional[str] = None

class ImageDataAnalysisResult(BaseModel):   
    keywords: str
    insights: str
    genes: str
    drugs: str
    process: str
    error_message: Optional[str] = None
    status: str

class FigureAnalyzer(Enum):
    MedGemma = "medgemma"
    GEMINI = "gemini"

class BaseFigureAnalyzer(ABC):
    """
    Abstract base class for figure analyzers
    """

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @abstractmethod
    def get_user_prompt(self, caption: str) -> str:
        pass

    @abstractmethod
    async def analyze_content(self, figure_data: ImageDataModel) -> Dict:
        pass

    @abstractmethod
    def parse_analysis_response(self, response_json: Dict, figure_data: Dict) -> Dict:
        pass

    def _error_response(self, error: str, status: str) -> Dict:
        return {
            "text_extraction": "",
            "insights": "",
            "gene": "",
            "drug": "",
            "cell_types": "",
            "process": "",
            "error": error,
            "status": status
        }


class GeminiAnalyzer(BaseFigureAnalyzer):
    """
    Simplified Gemini analyzer for biomedical image analysis
    Uses Google's Gemini 2.5 Flash multimodal API
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        if self.api_key is None:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

    def get_system_prompt(self) -> str:
        """System prompt for biomedical analysis"""
        return """Extract biomedical information from this pathway image in 5 categories:

            1. **genes**: Official human gene symbols only (HGNC format: PAH, TH, TPH1). Exclude metabolites, amino acids, proteins.
            2. **drugs**: Pharmaceutical compounds, therapeutic agents only.
            3. **keywords**: Disease names, metabolites, amino acids, techniques, biomarkers.
            4. **process**: Main biological process (e.g., "phenylalanine metabolism").
            5. **insights**: Brief clinical relevance visible in the image.

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
        """User prompt with caption context"""
        context = f"Caption: {caption}" if caption and caption != "No caption provided" else "No caption context"
        return f"""Extract comprehensive biomedical information from this pathway image.

                {context}

                Return analysis in the exact JSON format specified."""

    async def _load_image_from_url(self, image_url: str) -> Image.Image:
        """Load image from URL with basic error handling"""
        logger.debug(f"Loading image from: {image_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Add domain-specific headers
        if 'ncbi.nlm.nih.gov' in image_url:
            headers['Referer'] = 'https://www.ncbi.nlm.nih.gov/'
        elif 'europepmc.org' in image_url:
            headers['Referer'] = 'https://europepmc.org/'
        
        try:
            response = requests.get(image_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Convert to PIL Image
            image = Image.open(BytesIO(response.content))
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            logger.info(f"Successfully loaded image: {image.size}")
            return image
            
        except Exception as e:
            error_msg = f"Failed to load image: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    @async_api_retry(max_retries=2, base_delay=3.0, backoff_multiplier=2.0)
    async def _call_gemini_api(self, figure_data: ImageDataModel) -> Dict:
        """
        Core Gemini API call with retry logic
        """
        caption = figure_data.get("caption") or figure_data.get("image_caption", "No caption provided")
        pmcid = figure_data.get('pmcid', 'unknown')
        
        logger.info(f"Calling Gemini API for: {pmcid}")
        
        try:
            # Load image
            image = await self._load_image_from_url(figure_data["image_url"])
            
            # Prepare prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self.get_user_prompt(caption)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                [full_prompt, image],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 8192,
                }
            )

            # Check response
            if response.prompt_feedback.block_reason:
                logger.error(f"Gemini blocked response for {pmcid}: {response.prompt_feedback.block_reason}")
                raise Exception(f"Content blocked: {response.prompt_feedback.block_reason}")
            
            if not response.candidates:
                logger.error(f"No response candidates for {pmcid}")
                raise Exception("No response generated")
            
            generated_text = response.candidates[0].content.parts[0].text
            logger.debug(f"Gemini response: {generated_text[:200]}...")
            
            return {
                "status": "success",
                "content": generated_text
            }
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit/quota issues
            if any(indicator in error_str for indicator in ['quota', 'rate limit', 'too many requests']):
                logger.error(f"Rate limit for {pmcid}: {str(e)}")
                raise ContinueToNextRecordException(f"Rate limit: {str(e)}") from e
            
            # Check for authentication issues  
            if any(indicator in error_str for indicator in ['api key', 'unauthorized', 'authentication']):
                logger.error(f"Auth error for {pmcid}: {str(e)}")
                raise PipelineStopException(f"Authentication error: {str(e)}") from e
            
            # Re-raise other errors for retry
            raise e

    async def analyze_content(self, figure_data: ImageDataModel) -> Dict:
        """
        Main analysis method with error handling
        """
        logger.info(f"Analyzing content for: {figure_data.get('pmcid', 'unknown')}")
        
        try:
            result = await self._call_gemini_api(figure_data)
            parsed = self.parse_analysis_response(result, figure_data)
            logger.info(f"Analysis completed for: {figure_data.get('pmcid', 'unknown')}")
            return parsed
            
        except ContinueToNextRecordException as e:
            # Timeout/rate limit - skip record
            logger.error(f"Skipping record due to: {str(e)}")
            return self._error_response("Gemini API timeout/rate limit", "analysis_timeout")
            
        except PipelineStopException as e:
            # Critical error - stop pipeline
            logger.error(f"Critical Gemini error: {str(e)}")
            raise RuntimeError(f"Gemini analysis failed: {str(e)}") from e
                        
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected Gemini error: {str(e)}")
            raise RuntimeError(f"Unexpected Gemini error: {str(e)}") from e

    def parse_analysis_response(self, result: Dict, figure_data: Dict) -> Dict:
        """Parse Gemini response into database format"""
        extracted = {
            "keywords": "not mentioned",
            "insights": "not mentioned", 
            "genes": "not mentioned",
            "drugs": "not mentioned",
            "process": "not mentioned",
            "error_message": None,
            "status": "unknown"
        }

        pmcid = figure_data.get('pmcid', 'unknown')
        
        if result.get("status") == "success" and result.get("content"):
            # Try to parse JSON from content
            analysis = self._parse_json_from_string(result["content"], pmcid)
            
            if analysis and isinstance(analysis, dict):
                # Map fields from analysis to database format
                field_map = {
                    "genes": ["genes", "gene_symbols", "gene"],
                    "drugs": ["drugs", "drug_names", "medications"],
                    "keywords": ["keywords", "terms", "biomarkers"],
                    "process": ["process", "biological_process", "pathway"],
                    "insights": ["insights", "clinical_insights", "significance"]
                }
                
                found_fields = 0
                for db_field, api_fields in field_map.items():
                    for field in api_fields:
                        if field in analysis:
                            value = analysis[field]
                            if isinstance(value, list):
                                value = ", ".join([str(v).strip() for v in value if str(v).strip()])
                            extracted[db_field] = self._clean_field(str(value))
                            found_fields += 1
                            break
                
                if found_fields > 0:
                    extracted["status"] = "analyzed"
                    logger.info(f"Parsed {found_fields} fields for {pmcid}")
                else:
                    extracted["error_message"] = "No recognizable fields in response"
                    extracted["status"] = "analysis_error"
            else:
                extracted["error_message"] = "Failed to parse JSON response"
                extracted["status"] = "analysis_error"
        else:
            extracted["error_message"] = "Invalid response from Gemini"
            extracted["status"] = "analysis_error"

        return extracted

    def _parse_json_from_string(self, text: str, pmcid: str) -> Optional[Dict]:
        """Parse JSON from text with fallback strategies"""
        if not text or not isinstance(text, str):
            return None
        
        text = text.strip()
        
        # Try direct JSON parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Remove markdown code blocks
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        
        # Find JSON with regex
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Failed to parse JSON from response for {pmcid}")
        return None

    def _clean_field(self, field_value: str) -> str:
        """Clean and validate field values"""
        if not field_value or not isinstance(field_value, str):
            return "not mentioned"
        
        cleaned = field_value.strip()
        if not cleaned or cleaned.lower() in ["", "n/a", "none", "null", "not mentioned", "not available"]:
            return "not mentioned"
        
        # Remove quotes and clean up
        cleaned = re.sub(r'^["\']|["\']$', '', cleaned).strip()
        
        # Handle comma-separated values
        if ',' in cleaned:
            items = [item.strip() for item in cleaned.split(',') if item.strip()]
            unique_items = []
            seen = set()
            for item in items:
                if item.lower() not in seen and len(item) > 1:
                    unique_items.append(item)
                    seen.add(item.lower())
            
            return ", ".join(unique_items[:10]) if unique_items else "not mentioned"
        
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

class MedGemmaAnalyzer(BaseFigureAnalyzer):
    """
    Enhanced MedGemma analyzer with GPU memory management
    Handles CUDA OOM errors by triggering model reload before retry
    """
    
    def __init__(self):
        self.username = username or os.getenv('username')
        self.password = password or os.getenv('password')
        self.base_url = os.getenv('MEDGEMMA_MODEL_URL')

        if not self.username or not self.password or not self.base_url:
            raise ValueError("LDAP credentials or MedGemma model URL not found in environment variables")

    async def initialize(self):
        """Initialize the MedGemmaAnalyzer"""
        # First: Check MedGemma server health before proceeding
        is_healthy, health_message = await self.check_medgemma_server_health()
        if not is_healthy:
            logger.error(f"{prefix} MedGemma server is not healthy: {health_message}")
            if "timeout" in health_message.lower() or "memory" in health_message.lower():
                raise RuntimeError(f"MedGemma server is not ready for processing: {health_message}")
            else:
                logger.warning(f"{prefix} Server health check failed but continuing: {health_message}")

        # Second: Preload MedGemma model to avoid initial memory allocation issues
        logger.info(f"{prefix} Preloading MedGemma model...")
        preload_success = await self.preload_medgemma_model()
        if not preload_success:
            logger.error(f"{prefix} Model preload failed - this may cause processing issues")
            # Do a final health check after preload failure
            is_healthy, health_message = await check_medgemma_server_health()
            if not is_healthy:
                raise RuntimeError(f"MedGemma server not ready after preload failure: {health_message}")

    def get_system_prompt(self) -> str:
        """Optimized system prompt - shorter but precise - UNCHANGED"""
        prompt =  """Extract biomedical information from this pathway image in 5 categories:

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
        return prompt
        
    def get_user_prompt(self, caption: str) -> str:
        """Concise user prompt for content analysis - UNCHANGED"""
        context = f"Caption: {caption}" if caption and caption != "No caption provided" else "No caption context"
        
        user_prompt = f"""Extract comprehensive biomedical information from this pathway image.

        {context}

        Return analysis in the exact JSON format specified."""
        return user_prompt

    async def check_medgemma_server_health(self):
        """
        Check if MedGemma server is responsive and has available memory
        Returns tuple: (is_healthy, error_message)
        """
        try:
            import httpx
            
            # username = os.getenv('username')
            # password = os.getenv('password')
            
            # if not username or not password:
            #     return False, "LDAP credentials not found"
            
            # # base_url = "https://medgemma-server.own4.aganitha.ai:8443"
            auth = httpx.BasicAuth(self.username, self.password)
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:  # Short timeout for health check
                response = await client.get(f"{self.base_url}/health", auth=auth)
                response.raise_for_status()
                result = response.json()
                
                # Check memory status
                memory_info = result.get("memory_info", {})
                if memory_info:
                    allocated = memory_info.get("allocated_gb", 0)
                    reserved = memory_info.get("reserved_gb", 0)
                    total_used = allocated + reserved
                    
                    logger.info(f"GPU Memory Status - Allocated: {allocated}GB, Reserved: {reserved}GB, Total Used: {total_used}GB")
                    
                    # If GPU memory is very high (>22GB), it might be problematic
                    if total_used > 22:
                        return False, f"GPU memory critically high: {total_used}GB used"
                
                return True, "Server healthy"
                
        except httpx.TimeoutException:
            return False, "Server not responding (timeout)"
        except httpx.HTTPStatusError as e:
            return False, f"Server returned HTTP {e.response.status_code}"
        except Exception as e:
            return False, f"Server check failed: {str(e)}"

    async def preload_medgemma_model(self):
        """
        Preload the MedGemma model before starting processing
        This helps avoid initial GPU memory allocation issues
        """
        try:
            import httpx

            auth = httpx.BasicAuth(self.username, self.password)

            logger.info("Preloading MedGemma model before processing...")
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                response = await client.post(f"{self.base_url}/preload", auth=auth)
                response.raise_for_status()
                result = response.json()
                
                if result.get("status") == "success":
                    logger.info("MedGemma model preloaded successfully")
                    memory_info = result.get("memory_info", {})
                    if memory_info:
                        logger.info(f"GPU Memory Status: {memory_info}")
                    return True
                else:
                    logger.error(f"Model preload failed: {result}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to preload MedGemma model: {str(e)}")
            return False

    async def _check_model_status(self, client: httpx.AsyncClient) -> Dict:
        """Check if model is loaded and get memory status"""
        try:
            auth = httpx.BasicAuth(self.username, self.password)
            response = await client.get(f"{self.base_url}/health", auth=auth, timeout=10.0)  # Shorter timeout for health check
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to check model status: {str(e)}")
            return {"status": "unknown"}

    async def fetch_model_info(self) -> Dict:
        # SECOND: Check MedGemma server health before proceeding
        logger.info(f"{prefix} Checking MedGemma server health...")
        is_healthy, health_message = await self.check_medgemma_server_health()
        if not is_healthy:
            logger.error(f"{prefix} MedGemma server is not healthy: {health_message}")
            if "timeout" in health_message.lower() or "memory" in health_message.lower():
                raise RuntimeError(f"MedGemma server is not ready for processing: {health_message}")
            else:
                logger.warning(f"{prefix} Server health check failed but continuing: {health_message}")

        # THIRD: Preload MedGemma model to avoid initial memory allocation issues
        logger.info(f"{prefix} Preloading MedGemma model...")
        preload_success = await self.preload_medgemma_model()
        if not preload_success:
            logger.error(f"{prefix} Model preload failed - this may cause processing issues")
            # Do a final health check after preload failure
            is_healthy, health_message = await self.check_medgemma_server_health()
            if not is_healthy:
                raise RuntimeError(f"MedGemma server not ready after preload failure: {health_message}")

    async def _preload_model(self, client: httpx.AsyncClient) -> bool:
        """Preload the model to ensure it's ready"""
        try:
            auth = httpx.BasicAuth(self.username, self.password)
            logger.info("Triggering model preload...")
            response = await client.post(f"{self.base_url}/preload", auth=auth, timeout=120.0)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                logger.info("Model preloaded successfully")
                return True
            else:
                logger.error(f"Model preload failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Model preload failed: {str(e)}")
            return False

    async def _unload_model(self, client: httpx.AsyncClient) -> bool:
        """Force unload the model to free GPU memory"""
        try:
            auth = httpx.BasicAuth(self.username, self.password)
            logger.info("Forcing model unload to free GPU memory...")
            response = await client.post(f"{self.base_url}/unload", auth=auth, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "success":
                logger.info("Model unloaded successfully")
                return True
            else:
                logger.error(f"Model unload failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Model unload failed: {str(e)}")
            return False

    async def _handle_gpu_memory_error(self, client: httpx.AsyncClient, error_msg: str) -> bool:
        """Handle GPU memory errors by unloading and reloading the model"""
        logger.error(f"GPU Memory Error detected: {error_msg}")
        logger.info("Attempting to recover by unloading and reloading model...")
        
        # Step 1: Unload the model
        unload_success = await self._unload_model(client)
        if not unload_success:
            logger.error("Failed to unload model - cannot recover from GPU memory error")
            return False
        
        # Step 2: Wait a bit for memory to be freed
        await asyncio.sleep(5.0)
        
        # Step 3: Preload the model again
        preload_success = await self._preload_model(client)
        if not preload_success:
            logger.error("Failed to reload model after GPU memory error")
            return False
        
        logger.info("Successfully recovered from GPU memory error")
        return True

    def _is_gpu_memory_error(self, error_msg: str) -> bool:
        """Check if error message indicates GPU memory issues"""
        gpu_memory_indicators = [
            "CUDA out of memory",
            "out of memory",
            "Failed to allocate",
            "memory allocation",
            "insufficient GPU memory",
            "cuda memory error",
            "Model loading failed"
        ]
        error_lower = error_msg.lower()
        return any(indicator.lower() in error_lower for indicator in gpu_memory_indicators)

    @async_api_retry(max_retries=3, base_delay=2.0, backoff_multiplier=2.5)
    async def _call_medgemma_api(self, figure_data: ImageDataModel) -> Dict:
        """
        Enhanced MedGemma API call with GPU memory error handling
        This is the core API call that will be retried with memory management
        """
        caption = figure_data.get("caption") or figure_data.get("image_caption", "No caption provided")
        
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

        # Use a single client instance for the retry attempts with shorter timeout
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:  # Reduced from 300s to 120s
            pmcid = figure_data.get('pmcid', 'unknown')
            logger.info(f"Sending content analysis request for: {pmcid}")
            
            # Pre-check: Verify server health before making expensive request
            try:
                health_status = await self._check_model_status(client)
                if health_status.get("status") == "unknown":
                    logger.warning(f"MedGemma server health unknown for {pmcid} - proceeding anyway")
            except Exception as e:
                logger.warning(f"Health check failed for {pmcid}: {str(e)} - proceeding anyway")
            
            try:
                response = await client.post(
                    f"{self.base_url}/generate",
                    json=payload,
                    headers=headers,
                    auth=auth
                )

                # Raise HTTPStatusError for bad status codes - this will be caught by the retry decorator
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"MedGemma raw response: {result}")
                
                # Check if the response contains a GPU memory error
                response_text = json.dumps(result).lower()
                if self._is_gpu_memory_error(response_text):
                    logger.error("GPU memory error detected in API response")
                    raise GPUMemoryException(f"GPU memory error in response: {response_text[:200]}")
                
                return result
                
            except httpx.TimeoutException as e:
                # Log timeout immediately and check if it's likely due to GPU memory
                logger.error(f"MedGemma request timed out for {pmcid} after 120s - likely GPU memory issue")
                
                # Try to get server status to confirm
                try:
                    health_status = await self._check_model_status(client)
                    memory_info = health_status.get("memory_info", {})
                    if memory_info.get("allocated_gb", 0) > 20:  # High GPU usage
                        logger.error(f"High GPU memory usage detected: {memory_info}")
                        raise GPUMemoryException(f"Timeout likely due to GPU memory exhaustion: {memory_info}")
                except:
                    pass
                
                # Re-raise original timeout
                raise e
                
            except httpx.HTTPStatusError as e:
                # Check if the HTTP error is due to GPU memory issues
                try:
                    error_response = e.response.json()
                    error_detail = error_response.get('detail', str(e))
                    if self._is_gpu_memory_error(error_detail):
                        logger.error("GPU memory error detected in HTTP error response")
                        raise GPUMemoryException(f"GPU memory error: {error_detail}")
                except:
                    pass
                # Re-raise the original HTTP error if not GPU memory related
                raise e
                
            except GPUMemoryException:
                # Handle GPU memory errors with model reload
                logger.error(f"GPU memory error for {pmcid} - attempting recovery...")
                
                recovery_success = await self._handle_gpu_memory_error(client, str(e))
                if not recovery_success:
                    # If recovery fails, this is a critical error
                    raise PipelineStopException(f"Failed to recover from GPU memory error for {pmcid}")
                
                # If recovery succeeds, raise a special exception to trigger retry
                raise ModelLoadException(f"GPU memory recovered for {pmcid} - retrying")

    async def analyze_content(self, figure_data: ImageDataModel) -> Dict:
        """
        Enhanced analyze_content method with GPU memory error handling
        Handles GPU memory errors as recoverable issues that trigger model reload
        """
        
        logger.info(f"MedGemma analyzing content for PMCID: {figure_data.get('pmcid', 'unknown')}")
        
        max_gpu_retries = 2  # Allow up to 2 GPU memory recovery attempts
        
        for gpu_retry in range(max_gpu_retries + 1):
            try:
                # Use the retry-wrapped API call
                result = await self._call_medgemma_api(figure_data)
                
                # Parse the result using existing logic
                parsed = self.parse_analysis_response(result, figure_data)
                logger.info(f"Successfully analyzed content for: {figure_data.get('pmcid', 'unknown')}")
                return parsed
                
            except ModelLoadException as e:
                # GPU memory was recovered, retry the analysis
                if gpu_retry < max_gpu_retries:
                    logger.info(f"GPU memory recovered, retrying analysis (attempt {gpu_retry + 2}/{max_gpu_retries + 1})")
                    await asyncio.sleep(3.0)  # Brief pause before retry
                    continue
                else:
                    logger.error(f"Max GPU recovery attempts reached for {figure_data.get('pmcid', 'unknown')}")
                    return self._error_response("Max GPU memory recovery attempts exceeded", "gpu_memory_error")
                
            except ContinueToNextRecordException as e:
                # Timeout errors - skip current record and continue
                logger.error(f"MedGemma analysis timed out for {figure_data.get('pmcid', 'unknown')} - continuing to next record")
                return self._error_response("MedGemma API timeout after retries", "analysis_timeout")
                
            except PipelineStopException as e:
                # Critical errors - stop the entire pipeline
                logger.error(f"MedGemma analysis failed critically for {figure_data.get('pmcid', 'unknown')}: {str(e)}")
                raise RuntimeError(f"MedGemma analysis failed: {str(e)}") from e
                            
            except Exception as e:
                # Unexpected errors - also stop pipeline for safety
                logger.error(f"Unexpected MedGemma analysis error for {figure_data.get('pmcid', 'unknown')}: {str(e)}")
                raise RuntimeError(f"Unexpected MedGemma analysis error: {str(e)}") from e

    def parse_analysis_response(self, result: Dict, figure_data: Dict) -> ImageDataAnalysisResult:
        """Parse MedGemma response and return database-compatible fields - UNCHANGED"""
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
        """Attempt to parse JSON from a text string with multiple strategies - UNCHANGED"""
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
        """Clean and validate individual field values - UNCHANGED"""
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
        
        """Return error response for analysis failures - UNCHANGED"""
        return {
            "keywords": "not mentioned",
            "insights": "not mentioned", 
            "genes": "not mentioned",
            "drugs": "not mentioned",
            "process": "not mentioned",
            "error_message": error,
            "status": status
        }

class ModelClientFactory:
    """Factory class to create AI clients"""
    
    @staticmethod
    def create_client(model: str) -> Optional[BaseFigureAnalyzer]:
        """Create an AI client based on the model"""
        model = model.lower()
        if model == FigureAnalyzer.MedGemma.value:
            
            try:
                analyzer = MedGemmaAnalyzer()
                asyncio.run(analyzer.initialize())
                return analyzer
            except Exception as e:
                logger.error(f"Failed to initialize MedGemma client: {e}")
                raise e
            
        elif model == FigureAnalyzer.GEMINI.value:
            
            try:
                return GeminiAnalyzer()
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                return None

        else:
            logger.error(f"Unknown AI provider: {provider}")
            return None

_image_analyzer_client = None

def get_image_analyzer_client() -> Optional[BaseFigureAnalyzer]:
    """Get or create AI client instance (lazy initialization)"""
    global _image_analyzer_client
    try:
        if not FIGURE_ANALYSIS_MODEL:
            raise ValueError("FIGURE_ANALYSIS_MODEL not set in environment variables. Please set it to 'Gemini' or 'MedGemma' and provide necessary values.")

        if _image_analyzer_client is None:
            _image_analyzer_client = ModelClientFactory.create_client(FIGURE_ANALYSIS_MODEL)
            if _image_analyzer_client:
                logger.info(f"AI client ({FIGURE_ANALYSIS_MODEL}) initialized successfully")
            else:
                logger.warning(f"Failed to initialize AI client ({FIGURE_ANALYSIS_MODEL})")
        return _image_analyzer_client
    
    except Exception as e:
        logger.error(f"Error initializing AI client: {e}")
        raise e