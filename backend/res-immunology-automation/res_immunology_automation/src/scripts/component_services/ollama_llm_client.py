import os
import time
import random
import re, json
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from retry import retry
from typing import Dict
def is_rate_limit_error(exception):
    """Check if the exception is a rate limit error"""
    error_str = str(exception).lower()
    return any(keyword in error_str for keyword in ["429", "quota", "rate", "limit", "too many requests"])

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()

class LLMClient:
    def __init__(self, model=None, api_key=None):
        os.environ["GRPC_VERBOSITY"] = "ERROR"
        os.environ["GRPC_LOG_SEVERITY_LEVEL"] = "ERROR"
        
        # Load API key
        self.api_key =os.getenv("GEMINI_API_KEY") if api_key is None else api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in an environment file or passed in")

        # Use the latest model name
        self.model = model or "gemini-2.5-flash"  # Latest Gemini model

        # Configure Gemini client
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
        self.generation_config = {
        "temperature": 0.1,
        "max_output_tokens": 8192,
        }

    @retry(
    exceptions=Exception,
    tries=5,
    delay=10,        # Fixed delay of 10 seconds
    backoff=1,       # No exponential backoff
    jitter=0,        # No random jitter
    logger=logger
    )
    def extract_drugs(self, prompt: str) -> str:
        # logger.info("Waiting 10 seconds before first API call...")
        # time.sleep(10)  # Fixed latency before the first attempt

        try:
            response = self.client.generate_content(prompt, generation_config=self.generation_config)
            logger.info("LLM response received")
            # logger.info(f"Full response: {response}")

            if response and response.candidates:
                candidate = response.candidates[0]

                if hasattr(candidate, 'finish_reason'):
                    logger.info(f"Finish reason: {candidate.finish_reason}")
                    if candidate.finish_reason in [3, 4]:  # SAFETY, RECITATION
                        logger.warning("Response blocked by safety filters")
                        return "Response blocked due to safety concerns"

                if candidate.content and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)

                    if text_parts:
                        return response.text.strip()

                logger.warning("No text content found in response")
                return ""

            logger.warning("No candidates in response")
            return ""

        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(f"Rate limit or quota error: {e}")
            else:
                logger.error(f"Unexpected error occurred: {e}")
            raise  # Re-raise to trigger retry

    @retry(
    exceptions=Exception,
    tries=5,
    delay=10,        # Fixed delay of 10 seconds
    backoff=1,       # No exponential backoff
    jitter=0,        # No random jitter
    logger=logger
    )
    def identify_disease_efo_term(self, title: str, abstract: str) -> Dict[str, str]:
        prompt = f"""
        You are an expert biomedical and clinical researcher specializing in disease ontology and the analysis of biomedical literature.

        Objective: Your task is to accurately identify the primary disease focus from the provided title and abstract/description of a scientific study. 

        Instructions: 
        Analyze the [TITLE] and [ABSTRACT / DESCRIPTION] provided below and perform the following steps:
        Primary Disease Focus: Pinpoint the exact disease name used in the paper.
        Provide EFO Term:  Map the most relevant Experimental Factor Ontology (EFO) term for the above disease using Source: https://www.ebi.ac.uk/ols4/ontologies/efo. 
        
        Examples:
        1.  

        Convert the above disease name to the most relevant EFO name (e.g. kidney diseases, migraine disorder etc.)
        
        If no disease is found, return “null”.

        Title: {title}
        Abstract / Description: {abstract}

        Output Format: Present your findings exclusively in the following structured format. Do not add any conversational text outside of this structure.
        ```JSON
        {{
        "primary_disease_focus": "",
        "efo_term": "",
        }}
        ```
        """
        try:
            response = self.client.generate_content(prompt, generation_config=self.generation_config)
            logger.info("LLM response received")
            # logger.info(f"Full response: {response}")
            # return response.text.strip()    
            if response and response.candidates:
                candidate = response.candidates[0]

                if hasattr(candidate, 'finish_reason'):
                    logger.info(f"Finish reason: {candidate.finish_reason}")
                    if candidate.finish_reason in [3, 4]:  # SAFETY, RECITATION
                        logger.warning("Response blocked by safety filters")
                        return "Response blocked due to safety concerns"

                if candidate.content and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)

                    if text_parts:
                        parsed_response = self.parse_llm_json(response.text.strip())
                        return parsed_response

                logger.warning("No text content found in response")
                return ""

            logger.warning("No candidates in response")
            return ""

        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(f"Rate limit or quota error: {e}")
            else:
                logger.error(f"Unexpected error occurred: {e}")
            raise  # Re-raise to trigger retry

        return 

    def parse_llm_json(self, llm_response: str):
        # 1. Remove Markdown code fences like ```json or ```
        cleaned = re.sub(r"^```json\s*|\s*```$", "", llm_response.strip(), flags=re.IGNORECASE | re.MULTILINE)

        # 2. Remove any trailing commas before closing braces (invalid in JSON)
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

        # 3. Parse as JSON
        try:
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            print("Cleaned string was:", cleaned)
            return None

# Usage
if __name__ == "__main__":
    try:
        client = LLMClient()
        # result = client.extract_drugs(
        #     "List all drugs mentioned in the following text: Aspirin reduces fever. Paracetamol relieves pain."
        # )
        result = client.identify_disease_efo_term(
            title="Genome-wide expression profiling in the peripheral blood of patients with fibromyalgia",
            abstract="Fibromyalgia (FM) is a common pain disorder characterized by nociceptive dysregulation. The basic biology of FM is poorly understood. Herein we have used agnostic gene expression as a potential probe for informing its underlying biology and the development of a proof-of-concept diagnostic gene expression signature."
        )
        print("\nExtracted drugs:", type(result), result)
    except Exception as e:
        print(f"Error: {e}")