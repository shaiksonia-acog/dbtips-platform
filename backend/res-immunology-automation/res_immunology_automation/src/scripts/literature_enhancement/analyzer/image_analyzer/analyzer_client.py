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

MEDGEMMA_MODEL_URL = os.getenv("MEDGEMMA_MODEL_URL")
FIGURE_ANALYSIS_MODEL = os.getenv("FIGURE_ANALYSIS_MODEL", "MedGemma").lower()

class BaseFigureAnalyzer(ABC):
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username or os.getenv('username')
        self.password = password or os.getenv('password')

        if not self.username or not self.password:
            raise ValueError("LDAP credentials not found in environment variables")

    @abstractmethod
    def get_api_url(self) -> str:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @abstractmethod
    def get_user_prompt(self, caption: str) -> str:
        pass

    @abstractmethod
    def parse_response(self, response_json: Dict, figure_data: Dict) -> Dict:
        pass

    def clean_text_extraction(self, text: str) -> str:
        text = re.sub(r',\s*\w*$', '', text)
        terms = [t.strip() for t in text.split(",") if t.strip()]
        unique_terms = []
        seen = set()
        for term in terms:
            term_lower = term.lower()
            if term_lower not in seen and len(term) > 2:
                unique_terms.append(term)
                seen.add(term_lower)
        return ", ".join(unique_terms[:15])

    async def analyze(self, figure_data: Dict) -> Dict:
        caption = figure_data.get("caption", "No caption provided")
        payload = {
            "img_url": figure_data["image_url"],
            "system": self.get_system_prompt(),
            "user": self.get_user_prompt(caption),
            "caption": caption
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "LiteratureFigureAnalyzer/1.0"
        }

        auth = httpx.BasicAuth(self.username, self.password)

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    # self.get_api_url(),
                    "https://medgemma-server.own4.aganitha.ai:8443/generate",
                    json=payload,
                    headers=headers,
                    auth=auth
                )

                if response.status_code == 200:
                    result = response.json()
                    parsed = self.parse_response(result, figure_data)
                    return parsed
                else:
                    logger.error("API returned status %d: %s", response.status_code, response.text[:200])
                    return self._error_response(f"HTTP {response.status_code} error", f"error_{response.status_code}")
        except httpx.TimeoutException:
            logger.error("API timeout for %s", figure_data.get("figure_label", "unknown"))
            return self._error_response("API timeout", "error")
        except Exception as exc:
            logger.error("Analysis failed for %s: %s", figure_data.get("figure_label", "unknown"), exc)
            return self._error_response(str(exc), "error")

        return figure_data

    def _error_response(self, error: str, status: str) -> Dict:
        return {
            "keywords": "",
            "insights": "",
            "Genes": "",
            "drugs": "",
            "process": "",
            "error_message": error,
            "status": status
        }


class MedGemmaAnalyzer(BaseFigureAnalyzer):
    def get_api_url(self) -> str:
        return os.getenv("MEDGEMMA_MODEL_URL")  # Define in env

    def get_system_prompt(self) -> str:
        return """
        Analyze this medical image and respond with ONLY a JSON object. 
        Required JSON format: 
        { 
        "keywords": "medical terms found in image", 
        "insights": "clinical insights from analysis", 
        "Genes": "gene names if any", 
        "drugs": "drug names if any", 
        "process": "biological process described" ,
        }
        Rules: 
        - ONLY return the JSON object 
        - No markdown, no code blocks, no extra text
        - Use empty string "" for missing information 
        - Keep responses concise
        """

    def get_user_prompt(self, caption: str) -> str:
        return f"""Provide a brief analysis of this medical/scientific figure. 
                   Image caption (if available): {caption}"""

    def parse_response(self, result: Dict, figure_data: Dict) -> Dict:
        extracted = {
            "keywords": "",
            "insights": "",
            "Genes": "",
            "drugs": "",
            "process": "",
            "error_message": "",
            "status": result.get("status", "unknown")
        }

        analysis = None
        if result.get("status") in ("success", "warning") and "analysis" in result:
            analysis = result["analysis"]
        elif any(k in result for k in ["keywords", "insights", "Genes", "drugs", "process"]):
            analysis = result
        elif "raw_response" in result:
            try:
                json_match = re.search(r'\{.*\}', result["raw_response"], re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    extracted["error_message"] = "No JSON found in raw response"
            except Exception as e:
                extracted["error_message"] = f"Failed to parse raw response: {str(e)}"
                extracted["raw_response"] = result["raw_response"][:500]

        if analysis:
            extracted.update({
                "keywords": self.clean_text_extraction(analysis.get("keywords", "")),
                "insights": analysis.get("insights", ""),
                "Genes": analysis.get("Genes", ""),
                "drugs": analysis.get("drugs", ""),
                "process": analysis.get("process", "")
            })

        return extracted

class AnalyzerFactory:
    def create_analyzer_client()->BaseFigureAnalyzer:
        if FIGURE_ANALYSIS_MODEL.lower() == 'medgemma':
            return MedGemmaAnalyzer()

