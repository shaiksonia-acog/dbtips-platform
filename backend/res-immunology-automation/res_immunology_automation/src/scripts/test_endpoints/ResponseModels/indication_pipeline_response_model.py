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

class IndicationPipelineItemModel(BaseModel):
    """Model for individual indication pipeline entry"""
    
    Disease: str = Field(..., description="Disease name")
    Disease_URL: str = Field(alias="Disease URL", description="Disease URL")
    Drug: str = Field(..., description="Drug name")
    Drug_URL: str = Field(alias="Drug URL", description="Drug URL")
    Type: str = Field(..., description="Drug type")
    Mechanism_of_Action: str = Field(alias="Mechanism of Action", description="Mechanism of action")
    Phase: str = Field(..., description="Clinical trial phase")
    Status: Optional[str] = Field(None, description="Trial status")
    Target: str = Field(..., description="Target gene/protein")
    Target_URL: str = Field(alias="Target URL", description="Target URL")
    Source_URLs: List[str] = Field(alias="Source URLs", default_factory=list, description="Source URLs")
    Sponsor: str = Field(..., description="Trial sponsor")
    WhyStopped: str = Field(default="", description="Reason if stopped")
    ApprovalStatus: str = Field(..., description="Approval status")
    NctIdTitleMapping: Dict[str, Any] = Field(default_factory=dict, description="NCT ID mapping")
    PMIDs: List[str] = Field(default_factory=list, description="PubMed IDs")
    OutcomeStatus: str = Field(..., description="Outcome status")
    
    @field_validator('Disease', 'Drug', 'Type', 'Mechanism_of_Action', 'Phase', 'Target', 'Sponsor', 'ApprovalStatus', 'OutcomeStatus', mode='before')
    @classmethod
    def validate_string_fields(cls, v):
        """Convert non-string values to string, handle 0/null as default"""
        if v == 0 or v is None:
            return "Unknown"
        return str(v)
    
    @field_validator('Disease_URL', 'Drug_URL', 'Target_URL', mode='before')
    @classmethod
    def validate_url_fields(cls, v):
        """Ensure URL fields are strings"""
        if v == 0 or v is None:
            return "https://unknown.url"
        return str(v)
    
    @field_validator('WhyStopped', mode='before')
    @classmethod
    def validate_why_stopped(cls, v):
        """Handle WhyStopped field"""
        if v is None or v == 0:
            return ""
        return str(v)


class IndicationPipelineDiseaseModel(BaseModel):
    """Model for disease-specific indication pipeline data"""
    
    # The disease data is a list of pipeline items
    pipeline_items: List[IndicationPipelineItemModel] = Field(..., description="List of indication pipeline items for this disease")
    
    def __init__(self, pipeline_items: List[dict], **data):
        """Custom init to handle the list format"""
        super().__init__(pipeline_items=pipeline_items, **data)

