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
PMC_FETCH_DELAY = (1, 3)  # delay for PMC content fetching

# Processing limits
MAX_PMIDS_TO_PROCESS = 100
BATCH_SIZE = 10

# Endpoints
LITERATURE_ENDPOINT = "/evidence/literature/"
TARGET_LITERATURE_ENDPOINT = "/evidence/target-literature/"
FIGURE_ANALYSIS_ENDPOINT = "/evidence/literature/figure-analysis"

# Database table names (updated to match new schema)
ARTICLES_METADATA_TABLE = "articles_metadata"

# Default values for database fields
DEFAULT_DISEASE = "no-disease"
DEFAULT_TARGET = "no-target"

# Cache directories
CACHE_DIR_DISEASE = "cached_data_json/disease"
CACHE_DIR_TARGET_DISEASE = "cached_data_json/target_disease"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"