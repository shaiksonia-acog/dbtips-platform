import json
import re
import logging
import asyncio
from typing import Dict, Optional
import httpx
from pydantic import BaseModel
import os
from ..retry_decorators import async_api_retry, PipelineStopException, ContinueToNextRecordException

module_name = os.path.splitext(os.path.basename(__file__))[0]
logger = logging.getLogger(module_name)

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

class MedGemmaAnalyzer:
    """
    Enhanced MedGemma analyzer with GPU memory management
    Handles CUDA OOM errors by triggering model reload before retry
    """
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.getenv('username')
        self.password = password or os.getenv('password')
        self.base_url = "https://medgemma-server.own4.aganitha.ai:8443"

        if not self.username or not self.password:
            raise ValueError("LDAP credentials not found in environment variables")

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
                raise
                
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
                raise
                
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