"""Test actual WebSocket connection to Gemini Live API.

This script tests different approaches to connect to the real Gemini Live API
and send actual audio data.
"""

import asyncio
import json
import logging
import os
import sys
import base64
from pathlib import Path
import websockets
from google.auth.transport.requests import Request

# Add src to path
sys.path.insert(0, "src")

from voice_ai_assistant.voice.auth import VertexAuthManager
from voice_ai_assistant.voice.audio_stream import create_test_audio_file, AudioStreamManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LiveAPITester:
    """Test different approaches to connect to Gemini Live API."""
    
    def __init__(self):
        """Initialize the tester."""
        self.project_id = "powerful-outlet-477200-f0"
        self.region = "us-central1"
        
        # Set up credentials
        credentials_file = "voice-ai-service-account-key.json"
        if os.path.exists(credentials_file):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
            logger.info(f"Using credentials: {credentials_file}")
        else:
            logger.error(f"Credentials file not found: {credentials_file}")
            
        self.auth_manager = VertexAuthManager(self.project_id)
        self.audio_manager = AudioStreamManager()
        
    async def test_approach_1_google_ai_studio(self):
        """Test approach 1: Google AI Studio endpoint with service account."""
        logger.info("🔍 Testing Approach 1: Google AI Studio endpoint")
        
        try:
            # Get authentication token
            credentials = self.auth_manager.get_credentials()
            credentials.refresh(Request())
            access_token = credentials.token
            
            # Google AI Studio Live API endpoint
            url = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Connecting to: {url}")
            logger.info(f"Using project: {self.project_id}")
            
            # Try to connect
            async with websockets.connect(url, extra_headers=headers, ping_interval=30) as websocket:
                logger.info("✅ Connected successfully!")
                
                # Send setup message
                setup_message = {
                    "setup": {
                        "model": "models/gemini-2.0-flash-exp",
                        "generation_config": {
                            "response_modalities": ["AUDIO", "TEXT"],
                            "speech_config": {
                                "voice_config": {
                                    "prebuilt_voice_config": {
                                        "voice_name": "Puck"
                                    }
                                }
                            }
                        },
                        "system_instruction": {
                            "parts": [{
                                "text": "You are a helpful AI assistant. Respond briefly."
                            }]
                        }
                    }
                }
                
                await websocket.send(json.dumps(setup_message))
                logger.info("📤 Sent setup message")
                
                # Wait for setup response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    logger.info(f"📥 Received setup response: {response}")
                    
                    # Send a simple text message
                    text_message = {
                        "realtime_input": {
                            "text": "Hello! Can you hear me?"
                        }
                    }
                    
                    await websocket.send(json.dumps(text_message))
                    logger.info("📤 Sent text message")
                    
                    # Wait for response
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    logger.info(f"📥 Received response: {response}")
                    
                    return True
                    
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout waiting for response")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Approach 1 failed: {e}")
            return False
            
    async def test_approach_2_vertex_ai_endpoint(self):
        """Test approach 2: Vertex AI endpoint."""
        logger.info("🔍 Testing Approach 2: Vertex AI endpoint")
        
        try:
            # Get authentication token
            credentials = self.auth_manager.get_credentials()
            credentials.refresh(Request())
            access_token = credentials.token
            
            # Vertex AI Live API endpoint (if it exists)
            url = f"wss://{self.region}-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.PredictionService.BidiGenerateContent"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Connecting to: {url}")
            
            # Try to connect
            async with websockets.connect(url, extra_headers=headers, ping_interval=30) as websocket:
                logger.info("✅ Connected successfully!")
                
                # Send setup message with Vertex AI format
                setup_message = {
                    "setup": {
                        "model": f"projects/{self.project_id}/locations/{self.region}/models/gemini-2.0-flash-exp",
                        "generation_config": {
                            "response_modalities": ["AUDIO", "TEXT"]
                        }
                    }
                }
                
                await websocket.send(json.dumps(setup_message))
                logger.info("📤 Sent setup message")
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"📥 Received response: {response}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Approach 2 failed: {e}")
            return False
            
    async def test_approach_3_with_api_key(self):
        """Test approach 3: Using API key instead of service account."""
        logger.info("🔍 Testing Approach 3: API Key authentication")
        
        # Note: This would require a Google AI Studio API key
        # For now, we'll show the structure but skip actual testing
        logger.info("⚠️  This approach requires a Google AI Studio API key")
        logger.info("   You can get one from: https://aistudio.google.com/app/apikey")
        
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            logger.info("   Set GOOGLE_AI_API_KEY environment variable to test this approach")
            return False
            
        try:
            url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"
            
            logger.info(f"Connecting to: {url}")
            
            async with websockets.connect(url, ping_interval=30) as websocket:
                logger.info("✅ Connected with API key!")
                
                setup_message = {
                    "setup": {
                        "model": "models/gemini-2.0-flash-exp",
                        "generation_config": {
                            "response_modalities": ["TEXT"]
                        }
                    }
                }
                
                await websocket.send(json.dumps(setup_message))
                logger.info("📤 Sent setup message")
                
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                logger.info(f"📥 Received response: {response}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Approach 3 failed: {e}")
            return False
            
    async def test_audio_streaming(self, websocket):
        """Test streaming audio data to the WebSocket."""
        logger.info("🎵 Testing audio streaming...")
        
        try:
            # Create a test audio file
            test_audio_dir = Path("test_audio")
            test_audio_dir.mkdir(exist_ok=True)
            test_file = test_audio_dir / "websocket_test.wav"
            create_test_audio_file(test_file, duration_seconds=2.0)
            
            logger.info(f"Created test audio: {test_file}")
            
            # Stream audio chunks
            chunk_count = 0
            async for audio_chunk in self.audio_manager.stream_audio_file(test_file):
                # Convert to base64
                audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
                
                message = {
                    "realtime_input": {
                        "media_chunks": [{
                            "mime_type": "audio/pcm",
                            "data": audio_b64
                        }]
                    }
                }
                
                await websocket.send(json.dumps(message))
                chunk_count += 1
                logger.debug(f"Sent audio chunk {chunk_count}")
                
                # Small delay
                await asyncio.sleep(0.1)
                
                if chunk_count >= 5:  # Limit for testing
                    break
                    
            logger.info(f"✅ Sent {chunk_count} audio chunks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Audio streaming failed: {e}")
            return False
            
    async def run_all_tests(self):
        """Run all connection tests."""
        logger.info("🚀 Starting WebSocket Connection Tests")
        logger.info("=" * 60)
        
        results = {}
        
        # Test different approaches
        approaches = [
            ("Google AI Studio + Service Account", self.test_approach_1_google_ai_studio),
            ("Vertex AI Endpoint", self.test_approach_2_vertex_ai_endpoint),
            ("API Key Authentication", self.test_approach_3_with_api_key),
        ]
        
        for name, test_func in approaches:
            logger.info(f"\n🧪 Testing: {name}")
            logger.info("-" * 40)
            
            try:
                success = await test_func()
                results[name] = success
                
                if success:
                    logger.info(f"✅ {name}: SUCCESS")
                else:
                    logger.info(f"❌ {name}: FAILED")
                    
            except Exception as e:
                logger.error(f"❌ {name}: ERROR - {e}")
                results[name] = False
                
        # Summary
        logger.info("\n📊 Test Results Summary")
        logger.info("=" * 40)
        
        successful_approaches = []
        for approach, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"  {approach}: {status}")
            if success:
                successful_approaches.append(approach)
                
        if successful_approaches:
            logger.info(f"\n🎉 Working approaches: {len(successful_approaches)}")
            for approach in successful_approaches:
                logger.info(f"  ✅ {approach}")
        else:
            logger.info("\n⚠️  No approaches worked. Possible issues:")
            logger.info("  1. Gemini Live API may not be available in your region")
            logger.info("  2. Service account may need additional permissions")
            logger.info("  3. API endpoints may have changed")
            logger.info("  4. You may need a Google AI Studio API key")
            
        return results


async def main():
    """Main test function."""
    print("🌐 Gemini Live API WebSocket Connection Test")
    print("=" * 50)
    
    tester = LiveAPITester()
    results = await tester.run_all_tests()
    
    # Provide next steps based on results
    print("\n🔗 Next Steps:")
    
    if any(results.values()):
        print("✅ Great! At least one connection method worked.")
        print("   You can now integrate this into your voice assistant!")
        print("   Next: Test with real audio streaming and responses.")
    else:
        print("⚠️  No connections succeeded. Here's what to try:")
        print("   1. Get a Google AI Studio API key: https://aistudio.google.com/app/apikey")
        print("   2. Check if Gemini Live API is available in your region")
        print("   3. Verify your service account has the right permissions")
        print("   4. Try the Vertex AI Studio interface first to test Live API")


if __name__ == "__main__":
    asyncio.run(main())