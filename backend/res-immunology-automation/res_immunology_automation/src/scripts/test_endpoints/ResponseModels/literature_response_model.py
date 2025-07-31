import os
import sys
import time
import requests
import json
import subprocess
import signal
import threading
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, HttpUrl, field_validator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PublicationModel(BaseModel):
    """Model for individual publication/literature entry with flexible validation"""
    
    PMID: str = Field(..., description="PubMed ID")
    Title: str = Field(..., description="Publication title")
    Abstract: str = Field(..., description="Publication abstract")
    Year: int = Field(..., description="Publication year")
    PublicationType: List[str] = Field(..., description="Types of publication")
    PubMedLink: HttpUrl = Field(..., description="Link to PubMed entry")
    Qualifers: List[str] = Field(..., description="MeSH qualifiers")
    citedby: int = Field(..., description="Number of citations")
    last_author: str = Field(..., description="Last author name")
    authors: List[str] = Field(..., description="List of all authors")
    journal_name: str = Field(..., description="Journal name")
    journal_issn: str = Field(..., description="Journal ISSN")
    journal_rank: int = Field(..., description="Journal ranking")
    recency_score: float = Field(..., description="Recency score (0-1)")
    citedby_score: float = Field(..., description="Citation score (0-1)")
    journal_rank_score: float = Field(..., description="Journal rank score (0-1)")
    overall_score: float = Field(..., description="Overall relevance score (0-1)")
    hindex: int = Field(..., description="H-index of the journal/author")
    hindex_score: float = Field(..., description="H-index score (0-1)")

    @field_validator('last_author', mode='before')
    @classmethod
    def validate_last_author(cls, v):
        """Convert non-string values to string, handle 0 as empty"""
        if v == 0 or v is None:
            return "Unknown"
        return str(v)
    
    @field_validator('Abstract', mode='before')
    @classmethod
    def validate_abstract(cls, v):
        """Convert non-string values to string, handle 0 as empty"""
        if v == 0 or v is None:
            return "No abstract available"
        return str(v)
    
    @field_validator('Title', mode='before')
    @classmethod
    def validate_title(cls, v):
        """Ensure title is always a string"""
        if v == 0 or v is None:
            return "No title available"
        return str(v)
    
    @field_validator('journal_name', mode='before')
    @classmethod
    def validate_journal_name(cls, v):
        """Ensure journal name is always a string"""
        if v == 0 or v is None:
            return "Unknown Journal"
        return str(v)
    
    @field_validator('journal_issn', mode='before')
    @classmethod
    def validate_journal_issn(cls, v):
        """Ensure journal ISSN is always a string"""
        if v == 0 or v is None:
            return "Unknown"
        return str(v)


class DiseaseModel(BaseModel):
    """Model for disease-specific literature data"""
    
    literature: List[PublicationModel] = Field(..., description="List of publications for this disease")

