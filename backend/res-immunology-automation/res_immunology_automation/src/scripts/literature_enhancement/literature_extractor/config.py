#config
"""
Configuration settings for literature extraction
Updated to reflect new database schema
"""
import os

# NCBI API Configuration
NCBI_API_KEY = os.getenv("NCBI_API_KEY")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "your_email@example.com")
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Rate limiting
RATE_LIMIT = 300  # seconds for 429 back-off
DEFAULT_REQUEST_DELAY = (2, 5)  # min, max seconds between requests

# Back-off and retry configuration
MAX_RETRIES = 5
BACKOFF_FACTOR = 2.0
BASE_DELAY = 1.0

# Processing limits
MAX_PMIDS_TO_PROCESS = 100

# Endpoints
LITERATURE_ENDPOINT = "/evidence/literature/"
TARGET_LITERATURE_ENDPOINT = "/evidence/target-literature/"

# Default values for database fields
DEFAULT_DISEASE = "no-disease"
DEFAULT_TARGET = "no-target"