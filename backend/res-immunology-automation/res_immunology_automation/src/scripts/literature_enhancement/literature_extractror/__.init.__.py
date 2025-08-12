"""
Literature Extractor Package

This package provides functionality to extract and store literature data
from PubMed/PMC for disease and target-disease combinations.
"""

from .extractor import LiteratureExtractor
from .pmid_converter import PMIDConverter
from .data_storage import LiteratureStorage
from .utils import get_random_latency, get_top_100_pmids

__all__ = [
    'LiteratureExtractor',
    'PMIDConverter', 
    'LiteratureStorage',
    'get_random_latency',
    'get_top_100_pmids'
]

__version__ = "1.0.0"