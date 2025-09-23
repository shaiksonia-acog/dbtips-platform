import os
import time
import random
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted # Import the specific exception

load_dotenv()

class LLMClient:
    def __init__(self, model=None, api_key=None):
        # Correctly load the API key from the environment variable
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in an environment file or passed in")

        # Note: 'gemini-2.5-flash' is not a valid model name as of now.
        # I'm using 'gemini-1.5-flash' which is a common and valid model.
        self.model =  "gemini-2.5-flash"

        # Configure Gemini client
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)

    def extract_drugs(self, prompt: str) -> str:
        max_retries = 5  # Maximum number of times to retry
        base_wait_time = 2  # Initial wait time in seconds

        for attempt in range(max_retries):
            try:
                # This is the original API call
                response = self.client.generate_content(prompt)

                # Safely parse the response (your original logic)
                try:
                    return response.text.strip()
                except AttributeError:
                # Handles cases where the response might be empty or malformed
                    return ""

            except ResourceExhausted as e:
                # This exception is raised for 429 errors (rate limiting)
                print(f"Rate limit exceeded. Retrying in {base_wait_time ** attempt}s... (Attempt {attempt + 1}/{max_retries})")
                
                # Exponential backoff with jitter
                wait_time = (base_wait_time ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)

            except Exception as e:
                # Handle other potential errors
                print(f"An unexpected error occurred: {e}")
                break # Exit loop on other errors

        # If all retries fail, raise the last exception or a custom one
        raise Exception("Failed to get a response from the API after several retries.")


# Usage
if __name__ == "__main__":
    client = LLMClient()
    result = client.extract_drugs(
        "List all drugs mentioned in the following text: Aspirin reduces fever. Paracetamol relieves pain."
    )
    print("\nExtracted drugs:", result)