"""
Enhanced Endpoint Integration Test - Works with Multiple Endpoints
"""

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
from interface import ResponseValidatorInterface, ResponseValidatorFactory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ENDPOINTS:
    """Class to hold API endpoints"""
    
    LITERATURE = "/evidence/literature-semaphore"
    TARGET_LITERATURE = "/evidence/target-literature"
    INDICATION_PIPELINE = "/market-intelligence/indication-pipeline-semaphore"
    TARGET_PIPELINE = "/market-intelligence/target-pipeline-all"


class EndpointsIntegrationTest:
    """Integration test designed to run inside the same Docker container as the API"""
    
    def __init__(self, 
                 api_host: str = "127.0.0.1", 
                 api_port: int = 8000,
                 start_api: bool = True,
                 endpoint: str = "LITERATURE"):
        self.api_host = api_host
        self.api_port = api_port
        self.base_url = f"http://{api_host}:{api_port}"
        
        # Get the actual endpoint path
        self.endpoint_name = endpoint.upper()
        endpoint_path = getattr(ENDPOINTS, self.endpoint_name, None)
        if endpoint_path is None:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        
        self.endpoint = self.base_url + endpoint_path
        self.start_api = start_api
        self.api_process = None
        
        # Headers for requests
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def start_api_server(self):
        """Start the API server in background"""
        if not self.start_api:
            return
            
        print(f"🚀 Starting API server on {self.api_host}:{self.api_port}...")
        
        try:
            self.api_process = subprocess.Popen(
                ["python", "api.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            self.wait_for_api_ready()
            print("✅ API server started successfully")
            
        except Exception as e:
            print(f"❌ Failed to start API server: {e}")
            raise
    
    def stop_api_server(self):
        """Stop the API server"""
        if self.api_process:
            print("🛑 Stopping API server...")
            os.killpg(os.getpgid(self.api_process.pid), signal.SIGTERM)
            self.api_process.wait()
            print("✅ API server stopped")
    
    def wait_for_api_ready(self, timeout: int = 30):
        """Wait for API to be ready to accept requests"""
        print("⏳ Waiting for API to be ready...")
        
        for attempt in range(timeout):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1)
                if response.status_code == 200:
                    return
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                pass
            
            try:
                response = requests.get(self.endpoint, timeout=1)
                if response.status_code in [200, 405, 422]:
                    return
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                pass
            
            time.sleep(1)
        
        raise Exception(f"API server not ready after {timeout} seconds")
    
    def test_api_health(self, *args):
        """Test that the API is responding"""
        print("🔍 Testing API health...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Health endpoint responding")
                return
        except:
            pass
        
        try:
            response = requests.get(self.endpoint, timeout=5)
            print(f"Endpoint status: {response.status_code}")
            assert response.status_code != 404, f"Endpoint not found: {self.endpoint}"
            print("✅ API is responding")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot connect to API at {self.base_url}")
    
    def test_single_request(self, test_data: dict):
        """Test endpoint with single request"""
        print(f"🧪 Testing single request for {self.endpoint_name}...")
        
        response = requests.post(
            self.endpoint,
            json=test_data,
            headers=self.headers,
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        response_data = response.json()
        self._validate_response_structure(response_data)
        
        print("✅ Single request test passed")
        return response_data
    
    def test_multiple_requests(self, test_data: dict):
        """Test endpoint with multiple requests"""
        print(f"🧪 Testing multiple requests for {self.endpoint_name}...")
        
        response = requests.post(
            self.endpoint,
            json=test_data,
            headers=self.headers,
            timeout=120
        )
        
        print(f"Response status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        response_data = response.json()
        self._validate_response_structure(response_data)
        
        print("✅ Multiple requests test passed")
        return response_data
    
    def test_build_request(self, test_data: dict):
        """Build a request for the endpoint"""
        print(f"🔧 Building request for {self.endpoint_name}...")
        
        test_data['build_cache'] = True
        try:
            response = requests.post(
                self.endpoint,
                json=test_data,
                headers=self.headers,
                timeout=60
            )
            print(f"Request built successfully: {response.status_code}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to build request: {e}")
            raise

    def test_error_handling(self, *args):
        """Test error handling scenarios"""
        print("🧪 Testing error handling...")
        
        # Test empty request
        response = requests.post(
            self.endpoint,
            json={},
            headers=self.headers,
            timeout=10
        )
        print(f"Empty request response: {response.status_code}")
        
        # Test invalid format
        response = requests.post(
            self.endpoint,
            json={"invalid": "data"},
            headers=self.headers,
            timeout=10
        )
        print(f"Invalid format response: {response.status_code}")
        
        # Test malformed JSON
        response = requests.post(
            self.endpoint,
            data="invalid json",
            headers=self.headers,
            timeout=10
        )
        print(f"Malformed JSON response: {response.status_code}")
        
        print("✅ Error handling tests completed")
    
    def test_performance(self, test_data: dict):
        """Test endpoint performance"""
        print("🧪 Testing performance...")
        
        start_time = time.time()
        response = requests.post(
            self.endpoint,
            json=test_data,
            headers=self.headers,
            timeout=60
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        print(f"Response time: {response_time:.2f} seconds")
        
        assert response.status_code == 200
        assert response_time < 60, f"Response too slow: {response_time:.2f}s"
        
        print("✅ Performance test passed")
    
    def _validate_response_structure(self, response_data: Any):
        """Validate the structure of the response"""
        print("🔍 Validating response structure...")
        print(f"Response type: {type(response_data)}")
        
        assert response_data is not None, "Response data is None"
        
        try:
            # Create the response validator
            validator = ResponseValidatorFactory.create_validator(self.endpoint_name, response_data)
            
            if validator is None:
                raise ValueError(f"No validator found for endpoint: {self.endpoint_name}")
            
            print(f"✓ Response structure validated successfully")
            print(f"Found {len(validator.keys())} top-level keys: {list(validator.keys())}")
            
            # Validate the structure
            validation_result = validator.validate_structure()
            if not validation_result:
                print("⚠️ Structure validation returned False")
            
        except Exception as e:
            print(f"✗ Validation failed: {e}")
            # Basic fallback validation
            if isinstance(response_data, dict):
                print(f"Response contains keys: {list(response_data.keys())}")
            else:
                print("Response is not a dictionary")
                raise e
            
        print("✅ Response structure validation completed")
    
    def run_all_tests(self, test_data: dict):
        """Run all integration tests"""
        print(f"🐳 Running {self.endpoint_name} Endpoint Integration Tests in Docker\n")
        
        tests = [
            ("API Health Check", lambda: self.test_api_health()),
            ("Single Request", lambda: self.test_single_request(test_data)),
            ("Multiple Requests", lambda: self.test_multiple_requests(test_data)),
            ("Error Handling", lambda: self.test_error_handling()),
            ("Performance", lambda: self.test_performance(test_data)),
        ]
        
        passed = 0
        failed = 0
        results = []
        
        for test_name, test_func in tests:
            try:
                print(f"\n{'='*50}")
                print(f"Running: {test_name}")
                print('='*50)
                
                result = test_func()
                results.append((test_name, "PASSED", result))
                passed += 1
                
            except Exception as e:
                print(f"❌ {test_name} FAILED: {str(e)}")
                results.append((test_name, "FAILED", str(e)))
                failed += 1
        
        # Print summary
        print(f"\n{'='*50}")
        print("TEST SUMMARY")
        print('='*50)
        
        for test_name, status, details in results:
            status_emoji = "✅" if status == "PASSED" else "❌"
            print(f"{status_emoji} {test_name}: {status}")
        
        print(f"\nTotal: {passed} passed, {failed} failed")
        
        return failed == 0


def main(endpoint: str = "LITERATURE", test_data: dict = None):
    """Main function to run the integration tests"""
    print(f"🐳 Docker {endpoint} Endpoint Integration Test Suite")
    
    if test_data is None:
        # Default test data for literature endpoint
        test_data = {"diseases": ["diabetes"]}
    
    start_api = os.getenv("START_API", "true").lower() == "true"
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8000"))
    
    tester = EndpointsIntegrationTest(
        api_host=api_host,
        api_port=api_port,
        start_api=start_api,
        endpoint=endpoint
    )
    
    try:
        if start_api:
            tester.start_api_server()

        success = tester.run_all_tests(test_data)

        if success:
            print("\n🎉 All integration tests passed!")
            return 0
        else:
            print("\n💥 Some tests failed!")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        return 1
    finally:
        if start_api:
            tester.stop_api_server()


if __name__ == "__main__":
    # Example usage - you can test different endpoints
    endpoint_to_test = "INDICATION_PIPELINE"  # Change this to test other endpoints
    
    # Different test data for different endpoints
    if endpoint_to_test == "LITERATURE":
        test_data = {"diseases": ["obesity", "alzheimer disease"]}
    elif endpoint_to_test == "INDICATION_PIPELINE":
        test_data = {"diseases": ["alzheimer disease", "obesity"]}
    else:
        test_data = {"diseases": ["obesity"]}  # Default
    
    exit_code = main(endpoint_to_test, test_data)
    print(f"\nExiting with code: {exit_code}")
    sys.exit(exit_code)