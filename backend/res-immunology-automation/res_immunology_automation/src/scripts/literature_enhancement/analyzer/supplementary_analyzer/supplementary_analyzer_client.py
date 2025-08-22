import os
import re
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional
import httpx
import logging
from literature_enhancement.config import LOGGING_LEVEL
logging.basicConfig(level=LOGGING_LEVEL)
module_name = os.path.splitext(os.path.basename(__file__))[0].upper()
logger = logging.getLogger(module_name)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class BaseSupplementaryAnalyzer(ABC):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENAI_API_KEY
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")

    @abstractmethod
    def get_api_url(self) -> str:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @abstractmethod
    def get_user_prompt(self, title: str, description: str, file_names: str, url: str = None) -> str:
        pass

    @abstractmethod
    def parse_response(self, response_json: Dict, suppl_data: Dict) -> Dict:
        pass

    async def analyze(self, suppl_data: Dict) -> Dict:
        """Analyze supplementary material data using the configured model"""
        title = suppl_data.get("title", "").strip()
        description = suppl_data.get("description", "").strip()
        file_names = suppl_data.get("file_names", "")
        url = suppl_data.get("url", "")
        
        # Ensure both title and description are present
        if not title or not description:
            return self._error_response("Missing title or description", "error")
        
        # Check if description indicates no proper content
        if description.lower() == "no description available":
            return {
                "analysis": "there wasnt a proper context for this article to perform analysis",
                "keywords": "there wasnt a proper context for this article to perform analysis",
                "status": "insufficient_context"
            }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": self.get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": self.get_user_prompt(title, description, file_names, url)
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "LiteratureSupplementaryAnalyzer/1.0"
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.get_api_url(),
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    result = response.json()
                    parsed = self.parse_response(result, suppl_data)
                    return parsed
                else:
                    logger.error("API returned status %d: %s", response.status_code, response.text[:200])
                    return self._error_response(f"HTTP {response.status_code} error", f"error_{response.status_code}")
        except httpx.TimeoutException:
            logger.error("API timeout for supplementary material %s", suppl_data.get("pmcid", "unknown"))
            return self._error_response("API timeout", "error")
        except Exception as exc:
            logger.error("Analysis failed for supplementary material %s: %s", suppl_data.get("pmcid", "unknown"), exc)
            return self._error_response(str(exc), "error")

    def _error_response(self, error: str, status: str) -> Dict:
        """Generate error response format"""
        return {
            "analysis": f"ERROR: {error}",
            "keywords": f"ERROR: {error}",
            "error_message": error,
            "status": status
        }


class OpenAISupplementaryAnalyzer(BaseSupplementaryAnalyzer):
    def get_api_url(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    def get_system_prompt(self) -> str:
        return """You are a specialized biomedical researcher with expertise in analyzing supplementary materials from scientific publications. Your role is to provide detailed medical and scientific insights about supplementary materials based on their titles and chunks of texts which discuss or describe.

                Focus on:
                    - Areas that talks about supplementary informations and additional data attached to the article
                    - Clinical relevance and therapeutic implications
                    - Study methodology and data types
                    - Biomedical significance and research context
                    - Potential translational applications
                    - Quality and comprehensiveness of the data

                For keywords, extract 5-8 specific clinical, medical, or biomedical terms that are crucial for understanding the content. These should be:
                    - Specific medical/clinical terminology (not generic words)
                    - Drug names, biomarkers, molecular targets, protein names
                    - Technical methodologies or assay types
                    - Pathways, mechanisms, or biological processes
                    - Therapeutic approaches or clinical interventions

                IMPORTANT: DO NOT include disease names or condition names in the keywords. Focus on:
                    - Molecular mechanisms and pathways
                    - Therapeutic targets and interventions
                    - Methodological approaches
                    - Biomarkers and diagnostic tools
                    - Drug classes and compounds

                Provide a comprehensive analysis (3-5 sentences) that demonstrates deep biomedical understanding and clinical insight.

                Return only a JSON object in this exact format:
                {       
                    "analysis": "detailed biomedical analysis with clinical insights and scientific context",
                    "keywords": "keyword1, keyword2, keyword3, keyword4, keyword5"
                }

                Rules:
                    - ONLY return the JSON object, no markdown, no code blocks, no extra text
                    - Provide substantial medical insight, not generic descriptions
                    - Keywords should be comma-separated, specific medical terms only
                    - DO NOT include disease names, condition names, or disorder names in keywords
                    - Focus on underlying mechanisms, treatments, and methodological aspects
                    - Use professional biomedical terminology appropriately
                    - Be specific about the type of data and its scientific value"""

    def get_user_prompt(self, title: str, description: str, file_names: str, url: str = None) -> str:
        file_info = f"\n\nFile Names: {file_names}" if file_names else ""
        url_info = f"\nURL: {url}" if url else ""
        
        return f"""Analyze this supplementary material from a biomedical research publication. Provide detailed medical and scientific insights about its content and significance, along with crucial clinical/medical keywords.

Title: {title}

Description: {description}{file_info}{url_info}

Provide:
1. A comprehensive biomedical analysis focusing on clinical relevance, study methodology, therapeutic implications, and research significance
2. 5-8 specific clinical/medical keywords that are crucial for understanding this content (not generic terms)

What specific medical insights can be derived from this supplementary material, and what are the key clinical/biomedical terms that define its content?"""

    def parse_response(self, result: Dict, suppl_data: Dict) -> Dict:
        """Parse the OpenAI API response and extract structured data"""
        extracted = {
            "analysis": "",
            "keywords": "",
            "error_message": "",
            "status": "success"
        }

        try:
            # Extract content from OpenAI response
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"].strip()
                
                # Try to parse as JSON
                try:
                    # Remove potential markdown code blocks
                    content = re.sub(r'```json\s*', '', content)
                    content = re.sub(r'```\s*$', '', content)
                    
                    analysis_json = json.loads(content)
                    
                    # Extract the analysis and keywords
                    analysis_text = analysis_json.get("analysis", "")
                    keywords_text = analysis_json.get("keywords", "")
                    
                    extracted.update({
                        "analysis": analysis_text,
                        "keywords": keywords_text
                    })
                    
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract content anyway
                    extracted["analysis"] = content[:1500]  # Store raw content
                    extracted["keywords"] = ""  # Empty keywords if parsing fails
                    extracted["error_message"] = "JSON parsing warning - used raw content"
                    extracted["status"] = "warning"
            else:
                extracted["error_message"] = "No content in API response"
                extracted["analysis"] = "ERROR: No content received from API"
                extracted["keywords"] = "ERROR: No content received from API"
                extracted["status"] = "error"
                
        except Exception as e:
            extracted["error_message"] = f"Error parsing response: {str(e)}"
            extracted["analysis"] = f"ERROR: {str(e)}"
            extracted["keywords"] = f"ERROR: {str(e)}"
            extracted["status"] = "error"

        return extracted


class SupplementaryAnalyzerFactory:
    @staticmethod
    def create_analyzer_client() -> BaseSupplementaryAnalyzer:
        return OpenAISupplementaryAnalyzer()