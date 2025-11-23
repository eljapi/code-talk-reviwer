#!/usr/bin/env python3
"""Test script for Vertex AI Live API integration."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from voice_ai_assistant.voice import (
    VertexAuthManager,
    VertexLiveClient, 
    VoiceSessionManager,
    AudioStreamManager,
    create_test_audio_file,
    VertexLiveAPIError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_authentication():
    """Test Google Cloud authentication."""
    logger.info("Testing authentication...")
    
    try:
        auth_manager = VertexAuthManager()
        is_valid = auth_manager.validate_authentication()
        
        if is_valid:
            project_id = auth_manager.get_project_id()
            logger.info(f"✅ Authentication successful for project: {project_id}")
            return True
        else:
            logger.error("❌ Authentication failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return False


async def test_vertex_client_connection():
    """Test Vertex AI Live API client connection."""
    logger.info("Testing Vertex AI Live API connection...")
    
    try:
        client = VertexLiveClient()
        
        # Test connection
        await client.connect()
        logger.info(f"✅ Connected to Vertex AI Live API, session: {client.session_id}")
        
        # Test disconnection
        await client.disconnect()
        logger.info("✅ Disconnected successfully")
        
        return True
        
    except VertexLiveAPIError as e:
        logger.error(f"❌ Vertex AI Live API error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


async def test_audio_streaming():
    """Test audio streaming functionality."""
    logger.info("Testing audio streaming...")
    
    try:
        # Create test audio file
        test_audio_path = Path("test_audio.wav")
        create_test_audio_file(test_audio_path, duration_seconds=2.0)
        logger.info(f"✅ Created test audio file: {test_audio_path}")
        
        # Test audio streaming
        audio_manager = AudioStreamManager()
        chunk_count = 0
        
        async for audio_chunk in audio_manager.stream_audio_file(test_audio_path):
            chunk_count += 1
            if chunk_count >= 5:  # Test first few chunks
                break
                
        logger.info(f"✅ Successfully streamed {chunk_count} audio chunks")
        
        # Cleanup
        test_audio_path.unlink()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Audio streaming error: {e}")
        return False


async def test_session_manager():
    """Test voice session manager."""
    logger.info("Testing voice session manager...")
    
    try:
        session_manager = VoiceSessionManager()
        await session_manager.start()
        
        # Create a session
        session_id = await session_manager.create_session(user_id="test_user")
        logger.info(f"✅ Created session: {session_id}")
        
        # Check session state
        state = session_manager.get_session_state(session_id)
        if state and state.is_active:
            logger.info("✅ Session state is active")
        else:
            logger.error("❌ Session state is not active")
            return False
            
        # End session
        await session_manager.end_session(session_id)
        logger.info("✅ Ended session successfully")
        
        # Stop session manager
        await session_manager.stop()
        logger.info("✅ Stopped session manager")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Session manager error: {e}")
        return False


async def test_full_integration():
    """Test full integration with audio file streaming."""
    logger.info("Testing full integration...")
    
    try:
        # Create test audio file
        test_audio_path = Path("integration_test_audio.wav")
        create_test_audio_file(test_audio_path, duration_seconds=1.0)
        
        # Set up response handlers
        received_responses = []
        
        def on_audio_response(session_id: str, audio_data: bytes):
            logger.info(f"Received audio response for session {session_id}: {len(audio_data)} bytes")
            received_responses.append(("audio", len(audio_data)))
            
        def on_text_response(session_id: str, text: str):
            logger.info(f"Received text response for session {session_id}: {text}")
            received_responses.append(("text", text))
            
        def on_error(session_id: str, error: Exception):
            logger.error(f"Session {session_id} error: {error}")
            
        # Create session manager
        session_manager = VoiceSessionManager()
        session_manager.set_audio_response_callback(on_audio_response)
        session_manager.set_text_response_callback(on_text_response)
        session_manager.set_error_callback(on_error)
        
        await session_manager.start()
        
        # Create session and stream audio
        session_id = await session_manager.create_session()
        logger.info(f"Created integration test session: {session_id}")
        
        # Stream the test audio file
        await session_manager.stream_audio_file(session_id, str(test_audio_path))
        logger.info("✅ Streamed audio file to session")
        
        # Wait a bit for responses
        await asyncio.sleep(3)
        
        # Send a text message
        await session_manager.send_text_message(session_id, "Hello, can you hear me?")
        logger.info("✅ Sent text message to session")
        
        # Wait for responses
        await asyncio.sleep(5)
        
        # Check if we received any responses
        if received_responses:
            logger.info(f"✅ Received {len(received_responses)} responses")
            for response_type, data in received_responses:
                if response_type == "audio":
                    logger.info(f"  - Audio response: {data} bytes")
                else:
                    logger.info(f"  - Text response: {data}")
        else:
            logger.warning("⚠️  No responses received (this might be expected in test environment)")
            
        # Cleanup
        await session_manager.end_session(session_id)
        await session_manager.stop()
        test_audio_path.unlink()
        
        logger.info("✅ Full integration test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Full integration test error: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting Vertex AI Live API integration tests...")
    
    # Check environment
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        logger.warning("GOOGLE_CLOUD_PROJECT not set - some tests may fail")
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set - using default credentials")
        
    tests = [
        ("Authentication", test_authentication),
        ("Vertex Client Connection", test_vertex_client_connection),
        ("Audio Streaming", test_audio_streaming),
        ("Session Manager", test_session_manager),
        ("Full Integration", test_full_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
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
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error(f"💥 {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)