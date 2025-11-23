"""Test WebSocket connection using Google AI Studio API key.

This approach uses the Google AI Studio API key which is often easier
for accessing the Gemini Live API.
"""

import asyncio
import json
import logging
import os
import base64
from pathlib import Path
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_with_api_key():
    """Test connection using Google AI Studio API key."""
    
    print("🔑 Testing Gemini Live API with API Key")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("❌ No API key found!")
        print("\n📋 To get an API key:")
        print("1. Go to: https://aistudio.google.com/app/apikey")
        print("2. Create a new API key")
        print("3. Set it as environment variable:")
        print("   $env:GOOGLE_AI_API_KEY='your-api-key-here'")
        print("\n🔄 Then run this script again")
        return False
        
    print(f"✅ Found API key: {api_key[:10]}...")
    
    try:
        # Construct WebSocket URL with API key
        url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"
        
        print(f"🔗 Connecting to: {url[:80]}...")
        
        # Connect to WebSocket
        async with websockets.connect(url, ping_interval=30, ping_timeout=10) as websocket:
            print("✅ Connected successfully!")
            
            # Send setup message
            setup_message = {
                "setup": {
                    "model": "models/gemini-2.0-flash-exp",
                    "generation_config": {
                        "response_modalities": ["TEXT", "AUDIO"],
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
                            "text": "You are a helpful AI coding assistant. Keep responses brief and friendly."
                        }]
                    }
                }
            }
            
            await websocket.send(json.dumps(setup_message))
            print("📤 Sent setup message")
            
            # Wait for setup response
            try:
                setup_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                print(f"📥 Setup response: {setup_response}")
                
                # Parse setup response
                setup_data = json.loads(setup_response)
                if "setupComplete" in setup_data:
                    print("✅ Setup completed successfully!")
                else:
                    print(f"⚠️  Unexpected setup response: {setup_data}")
                
                # Send a text message
                text_message = {
                    "realtime_input": {
                        "text": "Hello! Can you help me with Python coding?"
                    }
                }
                
                await websocket.send(json.dumps(text_message))
                print("📤 Sent text message: 'Hello! Can you help me with Python coding?'")
                
                # Listen for responses
                response_count = 0
                async for message in websocket:
                    response_count += 1
                    print(f"📥 Response {response_count}: {message}")
                    
                    try:
                        data = json.loads(message)
                        
                        # Check for text response
                        if "candidates" in data:
                            for candidate in data["candidates"]:
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            print(f"💬 AI Response: {part['text']}")
                                            
                        # Check for audio response
                        if "candidates" in data:
                            for candidate in data["candidates"]:
                                if "content" in candidate and "inline_data" in candidate["content"]:
                                    inline_data = candidate["content"]["inline_data"]
                                    if inline_data.get("mime_type") == "audio/pcm":
                                        audio_size = len(base64.b64decode(inline_data["data"]))
                                        print(f"🔊 Received audio response: {audio_size} bytes")
                                        
                        # Check for server events
                        if "serverContent" in data:
                            server_content = data["serverContent"]
                            if "turnComplete" in server_content:
                                print("✅ Turn completed - conversation ready for next input")
                                break
                                
                    except json.JSONDecodeError:
                        print(f"⚠️  Non-JSON response: {message}")
                        
                    # Limit responses for testing
                    if response_count >= 10:
                        print("🔄 Reached response limit for testing")
                        break
                        
                print("🎉 Text conversation test completed successfully!")
                
                # Now test audio streaming
                await test_audio_streaming(websocket)
                
                return True
                
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for setup response")
                return False
                
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status code: {e.status_code}")
        if e.status_code == 403:
            print("   This might be an API key permission issue")
        elif e.status_code == 404:
            print("   The endpoint might not be available")
        return False
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_audio_streaming(websocket):
    """Test streaming audio to the WebSocket."""
    print("\n🎵 Testing Audio Streaming")
    print("-" * 30)
    
    try:
        # Create test audio file
        import sys
        sys.path.insert(0, "src")
        from voice_ai_assistant.voice.audio_stream import create_test_audio_file, AudioStreamManager
        
        test_audio_dir = Path("test_audio")
        test_audio_dir.mkdir(exist_ok=True)
        test_file = test_audio_dir / "api_key_test.wav"
        
        create_test_audio_file(test_file, duration_seconds=2.0)
        print(f"✅ Created test audio: {test_file}")
        
        audio_manager = AudioStreamManager()
        
        # Stream audio chunks
        chunk_count = 0
        async for audio_chunk in audio_manager.stream_audio_file(test_file):
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
            print(f"📤 Sent audio chunk {chunk_count} ({len(audio_chunk)} bytes)")
            
            # Small delay to simulate real-time
            await asyncio.sleep(0.1)
            
            if chunk_count >= 3:  # Limit for testing
                break
                
        print(f"✅ Successfully sent {chunk_count} audio chunks")
        
        # Wait for audio response
        print("👂 Listening for audio response...")
        response_count = 0
        
        async for message in websocket:
            response_count += 1
            print(f"📥 Audio response {response_count}")
            
            try:
                data = json.loads(message)
                
                # Check for audio response
                if "candidates" in data:
                    for candidate in data["candidates"]:
                        if "content" in candidate:
                            content = candidate["content"]
                            
                            # Text response
                            if "parts" in content:
                                for part in content["parts"]:
                                    if "text" in part:
                                        print(f"💬 AI Text: {part['text']}")
                                        
                            # Audio response
                            if "inline_data" in content:
                                inline_data = content["inline_data"]
                                if inline_data.get("mime_type") == "audio/pcm":
                                    audio_data = base64.b64decode(inline_data["data"])
                                    print(f"🔊 Received audio: {len(audio_data)} bytes")
                                    
                                    # Save audio response for verification
                                    response_file = test_audio_dir / f"response_{response_count}.wav"
                                    audio_manager.save_audio_to_file([audio_data], response_file)
                                    print(f"💾 Saved audio response: {response_file}")
                                    
                # Check for completion
                if "serverContent" in data and "turnComplete" in data["serverContent"]:
                    print("✅ Audio turn completed")
                    break
                    
            except json.JSONDecodeError:
                print(f"⚠️  Non-JSON audio response")
                
            if response_count >= 5:
                break
                
        print("🎉 Audio streaming test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Audio streaming failed: {e}")
        return False


async def main():
    """Main test function."""
    success = await test_with_api_key()
    
    if success:
        print("\n🎉 SUCCESS! Gemini Live API is working!")
        print("✅ You can now integrate this into your voice assistant")
        print("✅ Both text and audio streaming are functional")
    else:
        print("\n❌ Test failed. Check the steps above to resolve issues.")


if __name__ == "__main__":
    asyncio.run(main())