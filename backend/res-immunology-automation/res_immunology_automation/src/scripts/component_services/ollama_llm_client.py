import os
import time
import random
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from retry import retry
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
            logger.info(f"Full response: {response}")

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


# Usage
if __name__ == "__main__":
    try:
        client = LLMClient()
        result = client.extract_drugs(
            "List all drugs mentioned in the following text: Aspirin reduces fever. Paracetamol relieves pain."
        )
        print("\nExtracted drugs:", result)
    except Exception as e:
        print(f"Error: {e}")