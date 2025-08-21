import os
import re
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class BaseTableAnalyzer(ABC):
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
    def get_user_prompt(self, table_description: str, table_schema: str) -> str:
        pass

    @abstractmethod
    def parse_response(self, response_json: Dict, table_data: Dict) -> Dict:
        pass

    def clean_text_extraction(self, text: str) -> str:
        """Clean and process extracted keywords"""
        if not text:
            return ""
        
        text = re.sub(r',\s*\w*$', '', text)
        terms = [t.strip() for t in text.split(",") if t.strip()]
        unique_terms = []
        seen = set()
        for term in terms:
            term_lower = term.lower()
            if term_lower not in seen and len(term) > 2:
                unique_terms.append(term)
                seen.add(term_lower)
        return ", ".join(unique_terms[:20])  # Allow more keywords for tables

    async def analyze(self, table_data: Dict) -> Dict:
        """
        Analyze table data using the configured model
        Enhanced to throw appropriate exceptions for retry mechanism
        """
        table_description = table_data.get("table_description", "No description provided")
        table_schema = table_data.get("table_schema", "No schema provided")
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": self.get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": self.get_user_prompt(table_description, table_schema)
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "LiteratureTableAnalyzer/1.0"
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
                    parsed = self.parse_response(result, table_data)
                    return parsed
                else:
                    logger.error("API returned status %d: %s", response.status_code, response.text[:200])
                    # Raise HTTPStatusError for retry mechanism to handle
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code} error: {response.text[:200]}",
                        request=response.request,
                        response=response
                    )
                    
        except httpx.TimeoutException as e:
            logger.error("API timeout for table %s", table_data.get("pmcid", "unknown"))
            # Re-raise timeout exception for retry mechanism
            raise httpx.TimeoutException(f"API timeout for table {table_data.get('pmcid', 'unknown')}") from e
            
        except httpx.HTTPStatusError:
            # Re-raise HTTP status errors for retry mechanism
            raise
            
        except httpx.RequestError as e:
            logger.error("Request error for table %s: %s", table_data.get("pmcid", "unknown"), str(e))
            # Raise as connection error for retry mechanism
            raise httpx.ConnectError(f"Request error for table {table_data.get('pmcid', 'unknown')}: {str(e)}") from e
            
        except Exception as e:
            logger.error("Analysis failed for table %s: %s", table_data.get("pmcid", "unknown"), str(e))
            # Re-raise unexpected errors
            raise Exception(f"Analysis failed for table {table_data.get('pmcid', 'unknown')}: {str(e)}") from e

    def _error_response(self, error: str, status: str) -> Dict:
        """Generate error response format"""
        return {
            "analysis": "",
            "keywords": "",
            "table_intent": "",
            "description": "",
            "inference": "",
            "error_message": error,
            "status": status
        }


class OpenAITableAnalyzer(BaseTableAnalyzer):
    def get_api_url(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    def get_system_prompt(self) -> str:
        return """You are a biomedical researcher analyzing structured tables extracted from research articles. 
Analyze the table and respond with ONLY a JSON object containing your analysis.

Required JSON format: 
{ 
    "description": "2-4 short sentences describing the purpose and cover what the table reports (populations, data points, assays/doses/timepoints, variables etc.)",
    "inference": "1-2 short sentences stating the main conclusion supported by the table",
    "keywords": "relevant biomedical keywords extracted from the table analysis"
}

Rules: 
- ONLY return the JSON object 
- No markdown, no code blocks, no extra text
- Use empty string "" for missing information 
- Be concise, conservative, and evidence-first
- Do not invent numbers or study details
- Keep all text plain and brief
- Resolve multi-row headers into final column names"""

    def get_user_prompt(self, table_description: str, table_schema: str) -> str:
        return f"""Analyze this structured table extracted from a research article through the perspective of a biomedical researcher.
Understand and interpret the intent of the table and provide insights.

Table Description: {table_description}

Table Schema: {table_schema}

Please analyze what the table is trying to convey and provide the analysis in the specified JSON format."""

    def parse_response(self, result: Dict, table_data: Dict) -> Dict:
        """Parse the OpenAI API response and extract structured data"""
        extracted = {
            "analysis": "",
            "keywords": "",
            "table_intent": "",
            "description": "",
            "inference": "",
            "error_message": None,
            "status": "processed"
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
                    
                    analysis = json.loads(content)
                    
                    # Extract and clean the analysis components
                    table_intent = analysis.get("table_intent", "")
                    description = analysis.get("description", "")
                    inference = analysis.get("inference", "")
                    keywords = self.clean_text_extraction(analysis.get("keywords", ""))
                    
                    # Combine all text for the analysis field
                    analysis_text_parts = []
                    if table_intent:
                        analysis_text_parts.append(f"Intent: {table_intent}")
                    if description:
                        analysis_text_parts.append(f"Description: {description}")
                    if inference:
                        analysis_text_parts.append(f"Inference: {inference}")
                    
                    extracted.update({
                        "analysis": " | ".join(analysis_text_parts),
                        "keywords": keywords,
                        "table_intent": table_intent,
                        "description": description,
                        "inference": inference
                    })
                    
                except json.JSONDecodeError:
                    # If JSON parsing fails, store the raw content
                    extracted["error_message"] = "Failed to parse JSON response"
                    extracted["analysis"] = content[:1000]
                    extracted["status"] = "warning"
            else:
                extracted["error_message"] = "No content in API response"
                extracted["status"] = "error"
                
        except Exception as e:
            extracted["error_message"] = f"Error parsing response: {str(e)}"
            extracted["status"] = "error"

        return extracted


class TableAnalyzerFactory:
    @staticmethod
    def create_analyzer_client() -> BaseTableAnalyzer:
        return OpenAITableAnalyzer()