#!/usr/bin/env python3
"""Curl-equivalent test for Vertex AI Live API authentication and connection."""

import json
import logging
import os
import sys
from pathlib import Path
import requests
from google.auth.transport.requests import Request

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from voice_ai_assistant.voice import VertexAuthManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_vertex_ai_rest_api():
    """Test Vertex AI REST API authentication (curl equivalent)."""
    logger.info("Testing Vertex AI REST API authentication...")
    
    try:
        # Get authentication
        auth_manager = VertexAuthManager()
        credentials = auth_manager.get_credentials()
        project_id = auth_manager.get_project_id()
        
        # Refresh credentials to get access token
        credentials.refresh(Request())
        access_token = credentials.token
        
        logger.info(f"✅ Got access token for project: {project_id}")
        
        # Test REST API endpoint (equivalent to curl)
        region = "us-central1"
        model = "gemini-2.0-flash-exp"
        
        url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/{model}:generateContent"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Simple test payload
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Hello, this is a test message."
                }]
            }],
            "generation_config": {
                "temperature": 0.1,
                "max_output_tokens": 100
            }
        }
        
        logger.info(f"Making REST API call to: {url}")
        
        # Make the request (equivalent to curl)
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✅ REST API call successful")
            
            # Check if we got a response
            if "candidates" in result:
                candidates = result["candidates"]
                if candidates and "content" in candidates[0]:
                    content = candidates[0]["content"]
                    if "parts" in content and content["parts"]:
                        text_response = content["parts"][0].get("text", "")
                        logger.info(f"✅ Received response: {text_response[:100]}...")
                        return True
                        
            logger.info("✅ API call successful but no text response received")
            return True
            
        else:
            logger.error(f"❌ REST API call failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ REST API test error: {e}")
        return False


def test_vertex_ai_streaming_endpoint():
    """Test Vertex AI streaming endpoint availability."""
    logger.info("Testing Vertex AI streaming endpoint...")
    
    try:
        # Get authentication
        auth_manager = VertexAuthManager()
        credentials = auth_manager.get_credentials()
        project_id = auth_manager.get_project_id()
        
        # Refresh credentials
        credentials.refresh(Request())
        access_token = credentials.token
        
        # Test streaming endpoint availability
        region = "us-central1"
        model = "gemini-2.0-flash-exp"
        
        url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/{model}:streamGenerateContent"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Simple test payload for streaming
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Say hello"
                }]
            }],
            "generation_config": {
                "temperature": 0.1,
                "max_output_tokens": 50
            }
        }
        
        logger.info(f"Testing streaming endpoint: {url}")
        
        # Make streaming request
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=30
        )
        
        logger.info(f"Streaming response status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Streaming endpoint accessible")
            
            # Read first few chunks
            chunk_count = 0
            for line in response.iter_lines():
                if line:
                    chunk_count += 1
                    if chunk_count <= 3:  # Log first few chunks
                        try:
                            # Parse JSON chunk
                            if line.startswith(b'data: '):
                                json_data = line[6:]  # Remove 'data: ' prefix
                                chunk_data = json.loads(json_data)
                                logger.info(f"Received streaming chunk: {json.dumps(chunk_data, indent=2)[:200]}...")
                        except json.JSONDecodeError:
                            logger.info(f"Received non-JSON chunk: {line[:100]}...")
                    
                    if chunk_count >= 5:  # Stop after a few chunks
                        break
                        
            logger.info(f"✅ Received {chunk_count} streaming chunks")
            return True
            
        else:
            logger.error(f"❌ Streaming endpoint failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Streaming endpoint test error: {e}")
        return False


def test_websocket_endpoint_info():
    """Test WebSocket endpoint information (Live API)."""
    logger.info("Testing WebSocket endpoint information...")
    
    try:
        # Get authentication
        auth_manager = VertexAuthManager()
        project_id = auth_manager.get_project_id()
        region = "us-central1"
        
        # WebSocket URL for Live API
        ws_url = f"wss://{region}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.PredictionService/GenerateContentStream"
        
        logger.info(f"WebSocket Live API URL: {ws_url}")
        logger.info("✅ WebSocket endpoint URL constructed")
        
        # Note: We can't easily test WebSocket with requests library
        # This would require websockets library which is tested in the main integration test
        logger.info("ℹ️  WebSocket connection testing requires websockets library (tested in main integration)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ WebSocket endpoint info error: {e}")
        return False


def main():
    """Run curl-equivalent tests."""
    logger.info("Starting curl-equivalent tests for Vertex AI authentication...")
    
    # Check environment
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        logger.error("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        logger.info("Please set: export GOOGLE_CLOUD_PROJECT=your-project-id")
        return 1
        
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warning("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set - using default credentials")
        
    tests = [
        ("REST API Authentication", test_vertex_ai_rest_api),
        ("Streaming Endpoint", test_vertex_ai_streaming_endpoint),
        ("WebSocket Endpoint Info", test_websocket_endpoint_info),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
            
        logger.info("")
        
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("CURL-EQUIVALENT TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All curl-equivalent tests passed!")
        return 0
    else:
        logger.error(f"💥 {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)