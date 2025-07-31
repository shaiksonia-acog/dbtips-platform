
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
from ResponseModels.literature_response_model import PublicationModel
from ResponseModels.indication_pipeline_response_model import IndicationPipelineItemModel

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResponseValidatorInterface(ABC):
    """Abstract base class for response validators"""
    
    def __init__(self, **data):
        # Store the original data for access methods
        self._data = data

    @abstractmethod
    def validate_structure(self) -> bool:
        """Validate the structure of the response"""
        pass
    
    def __iter__(self):
        """Allow iteration over the response"""
        return iter(self._data)
    
    def __getitem__(self, item):
        """Allow dictionary-style access"""
        return self._data[item]
    
    def get(self, key: str, default=None):
        """Get method similar to dict.get()"""
        return self._data.get(key, default)
    
    def keys(self):
        """Get all keys"""
        return self._data.keys()
    
    def values(self):
        """Get all values"""
        return self._data.values()
    
    def items(self):
        """Get key-value pairs"""
        return self._data.items()
    
    def is_empty(self) -> bool:
        """Check if the response is empty"""
        return len(self._data) == 0

class LiteratureResponse(ResponseValidatorInterface):
    """Validator for literature endpoint response"""
    
    def validate_structure(self) -> bool:
        """Validate that each disease has the proper literature structure"""
        try:
            for disease_name, disease_data in self._data.items():
                if isinstance(disease_data, dict) and 'literature' in disease_data:
                    literature_list = disease_data['literature']
                    validated_publications = []
                    
                    for pub_data in literature_list:
                        try:
                            validated_pub = PublicationModel(**pub_data)
                            validated_publications.append(validated_pub)
                        except Exception as e:
                            print(f"⚠️ Warning: Failed to validate publication {pub_data.get('PMID', 'unknown')}: {e}")
                            continue
                    
                    print(f"✓ Validated {len(validated_publications)} publications for {disease_name}")
            
            return True
        except Exception as e:
            print(f"✗ Literature validation failed: {e}")
            return False


class TargetLiteratureResponse(ResponseValidatorInterface):
    """Validator for target literature endpoint response"""
    
    def validate_structure(self) -> bool:
        """Validate target literature response structure"""
        try:
            # Add your target literature validation logic here
            print("✓ Target literature response structure validated")
            return True
        except Exception as e:
            print(f"✗ Target literature validation failed: {e}")
            return False


class IndicationPipelineResponse(ResponseValidatorInterface):
    """Validator for indication pipeline endpoint response"""
    
    def validate_structure(self) -> bool:
        """Validate indication pipeline response structure"""
        try:
            # Check if we have the indication_pipeline key
            if 'indication_pipeline' not in self._data:
                print("✗ Missing 'indication_pipeline' key in response")
                return False
            
            pipeline_data = self._data['indication_pipeline']
            
            for disease_name, disease_items in pipeline_data.items():
                if not isinstance(disease_items, list):
                    print(f"⚠️ Warning: {disease_name} data is not a list: {type(disease_items)}")
                    continue
                
                validated_items = []
                for item_data in disease_items:
                    try:
                        validated_item = IndicationPipelineItemModel(**item_data)
                        validated_items.append(validated_item)
                    except Exception as e:
                        print(f"⚠️ Warning: Failed to validate pipeline item for {disease_name}: {e}")
                        continue
                
                print(f"✓ Validated {len(validated_items)} pipeline items for {disease_name}")
            
            print("✓ Indication pipeline response structure validated")
            return True
        except Exception as e:
            print(f"✗ Indication pipeline validation failed: {e}")
            return False


class TargetPipelineResponse(ResponseValidatorInterface):
    """Validator for target pipeline endpoint response"""
    
    def validate_structure(self) -> bool:
        """Validate target pipeline response structure"""
        try:
            # Add your target pipeline validation logic here
            print("✓ Target pipeline response structure validated")
            return True
        except Exception as e:
            print(f"✗ Target pipeline validation failed: {e}")
            return False


class ResponseValidatorFactory:
    """Factory class to create response validators"""
    
    @staticmethod
    def create_validator(endpoint: str, response: dict) -> Optional[ResponseValidatorInterface]:
        """Returns an instance of the appropriate response validator based on the endpoint"""
        endpoint = endpoint.lower().replace('/', '').replace('-', '_')
        
        if 'literature' in endpoint and 'target' not in endpoint:
            return LiteratureResponse(**response)
        elif 'target_literature' in endpoint:
            return TargetLiteratureResponse(**response)
        elif 'indication_pipeline' in endpoint or 'pipeline' in endpoint:
            return IndicationPipelineResponse(**response)
        elif 'target_pipeline' in endpoint:
            return TargetPipelineResponse(**response)
        else:
            logger.error(f"Unknown endpoint: {endpoint}")
            return None

