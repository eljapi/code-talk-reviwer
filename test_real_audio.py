"""Test script to send real audio file to Vertex AI Live API."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, "src")

from voice_ai_assistant.voice.vertex_client import VertexLiveClient
from voice_ai_assistant.voice.audio_stream import AudioStreamManager, create_test_audio_file
from voice_ai_assistant.voice.auth import VertexAuthManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AudioTestRunner:
    """Test runner for real audio file processing."""
    
    def __init__(self):
        """Initialize test runner."""
        self.project_id = "powerful-outlet-477200-f0"
        self.region = "us-central1"
        self.model = "gemini-2.0-flash-exp"
        
        # Set up credentials
        credentials_file = "voice-ai-service-account-key.json"
        if os.path.exists(credentials_file):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_file
            logger.info(f"Using credentials: {credentials_file}")
        else:
            logger.error(f"Credentials file not found: {credentials_file}")
            
        self.client = None
        self.audio_manager = AudioStreamManager()
        self.received_responses = []
        
    async def setup_client(self):
        """Set up Vertex AI Live client."""
        logger.info("Setting up Vertex AI Live client...")
        
        auth_manager = VertexAuthManager(self.project_id)
        self.client = VertexLiveClient(
            project_id=self.project_id,
            region=self.region,
            model=self.model,
            auth_manager=auth_manager
        )
        
        # Set up response callbacks
        self.client.set_audio_response_callback(self._on_audio_response)
        self.client.set_text_response_callback(self._on_text_response)
        self.client.set_error_callback(self._on_error)
        
        logger.info("Client setup complete")
        
    async def create_test_audio(self):
        """Create test audio files."""
        logger.info("Creating test audio files...")
        
        audio_dir = Path("test_audio")
        audio_dir.mkdir(exist_ok=True)
        
        # Create different test audio files
        test_files = [
            ("hello.wav", 2.0, "Hello, can you help me with my code?"),
            ("question.wav", 3.0, "What's the best way to optimize this function?"),
            ("short.wav", 1.0, "Thanks!")
        ]
        
        created_files = []
        for filename, duration, description in test_files:
            file_path = audio_dir / filename
            create_test_audio_file(file_path, duration)
            created_files.append({
                'path': file_path,
                'duration': duration,
                'description': description
            })
            logger.info(f"Created: {filename} ({duration}s) - {description}")
            
        return created_files
        
    async def test_connection(self):
        """Test basic connection to Vertex AI Live API."""
        logger.info("Testing connection to Vertex AI Live API...")
        
        try:
            await self.client.connect()
            logger.info("✅ Successfully connected to Vertex AI Live API")
            
            # Test if we can send a simple text message
            await self.client.send_text_message("Hello, this is a test message.")
            logger.info("✅ Successfully sent text message")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
            
    async def test_audio_streaming(self, audio_file):
        """Test streaming an audio file."""
        logger.info(f"Testing audio streaming: {audio_file['description']}")
        
        try:
            # Start listening for responses in background
            listen_task = asyncio.create_task(self.client.listen_for_responses())
            
            # Stream the audio file
            chunk_count = 0
            async for audio_chunk in self.audio_manager.stream_audio_file(audio_file['path']):
                await self.client.send_audio_chunk(audio_chunk)
                chunk_count += 1
                logger.debug(f"Sent audio chunk {chunk_count}: {len(audio_chunk)} bytes")
                
                # Small delay to simulate real-time streaming
                await asyncio.sleep(0.1)
                
            logger.info(f"✅ Streamed {chunk_count} audio chunks")
            
            # Wait a bit for responses
            await asyncio.sleep(2.0)
            
            # Cancel listening task
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Audio streaming test failed: {e}")
            return False
            
    async def test_interruption(self, audio_file):
        """Test interruption during audio streaming."""
        logger.info("Testing interruption (barge-in) functionality...")
        
        try:
            # Start streaming audio
            stream_task = asyncio.create_task(self._stream_with_interruption(audio_file))
            
            # Wait a bit then simulate interruption
            await asyncio.sleep(0.5)
            logger.info("🛑 Simulating user interruption...")
            
            # Cancel the streaming task (simulates interruption)
            stream_task.cancel()
            
            try:
                await stream_task
            except asyncio.CancelledError:
                logger.info("✅ Successfully handled interruption")
                
            # Send new input after interruption
            await self.client.send_text_message("Actually, let me ask something else.")
            logger.info("✅ Successfully sent new input after interruption")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Interruption test failed: {e}")
            return False
            
    async def _stream_with_interruption(self, audio_file):
        """Helper method to stream audio that can be interrupted."""
        async for audio_chunk in self.audio_manager.stream_audio_file(audio_file['path']):
            await self.client.send_audio_chunk(audio_chunk)
            await asyncio.sleep(0.1)
            
    def _on_audio_response(self, audio_data: bytes):
        """Handle audio response from Vertex AI."""
        logger.info(f"🔊 Received audio response: {len(audio_data)} bytes")
        self.received_responses.append({
            'type': 'audio',
            'size': len(audio_data),
            'data': audio_data[:100]  # Store first 100 bytes for inspection
        })
        
    def _on_text_response(self, text: str):
        """Handle text response from Vertex AI."""
        logger.info(f"💬 Received text response: {text}")
        self.received_responses.append({
            'type': 'text',
            'content': text
        })
        
    def _on_error(self, error: Exception):
        """Handle errors from Vertex AI."""
        logger.error(f"❌ Vertex AI error: {error}")
        self.received_responses.append({
            'type': 'error',
            'error': str(error)
        })
        
    async def run_complete_test(self):
        """Run complete audio testing suite."""
        logger.info("🚀 Starting complete audio test suite")
        logger.info("=" * 60)
        
        try:
            # Setup
            await self.setup_client()
            audio_files = await self.create_test_audio()
            
            # Test 1: Basic connection
            logger.info("\n📡 Test 1: Basic Connection")
            connection_ok = await self.test_connection()
            if not connection_ok:
                logger.error("Connection test failed, aborting remaining tests")
                return False
                
            # Test 2: Audio streaming
            logger.info("\n🎵 Test 2: Audio Streaming")
            for audio_file in audio_files:
                streaming_ok = await self.test_audio_streaming(audio_file)
                if not streaming_ok:
                    logger.warning(f"Audio streaming failed for {audio_file['description']}")
                    
            # Test 3: Interruption handling
            logger.info("\n🛑 Test 3: Interruption Handling")
            interruption_ok = await self.test_interruption(audio_files[0])
            
            # Summary
            logger.info("\n📊 Test Summary")
            logger.info("=" * 40)
            logger.info(f"Total responses received: {len(self.received_responses)}")
            
            for i, response in enumerate(self.received_responses):
                if response['type'] == 'text':
                    logger.info(f"  {i+1}. Text: {response['content'][:50]}...")
                elif response['type'] == 'audio':
                    logger.info(f"  {i+1}. Audio: {response['size']} bytes")
                elif response['type'] == 'error':
                    logger.info(f"  {i+1}. Error: {response['error']}")
                    
            logger.info("\n🎉 Complete test suite finished!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test suite failed: {e}")
            return False
            
        finally:
            # Cleanup
            if self.client:
                await self.client.disconnect()
                logger.info("🧹 Cleaned up client connection")


async def main():
    """Main test function."""
    print("🎤 Vertex AI Live API Audio Test")
    print("=" * 50)
    
    # Check credentials
    credentials_file = "voice-ai-service-account-key.json"
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("Please run: python scripts/setup_environment.py")
        return
        
    # Run tests
    test_runner = AudioTestRunner()
    success = await test_runner.run_complete_test()
    
    if success:
        print("\n✅ All tests completed successfully!")
        print("Your Vertex AI Live API integration is working! 🎉")
    else:
        print("\n❌ Some tests failed.")
        print("Check the logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())