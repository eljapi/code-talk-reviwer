
import asyncio
import logging
import os
import sys
import time
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

# We still need to mock some dependencies that VoiceOrchestrator imports but we don't want to fully initialize
# However, we want to import the real classes for TTS and Audio
# So we will mock the modules that we DON'T need, but keep the ones we DO need.

# Mock dependencies that might cause issues if not present or configured
sys.modules['claude_agent_sdk'] = MagicMock()
sys.modules['strands'] = MagicMock()

from voice_ai_assistant.orchestration.voice_orchestrator import VoiceOrchestrator
from voice_ai_assistant.agent.tools import ClaudeCodeTool
from voice_ai_assistant.voice.tts_manager import TTSManager
from voice_ai_assistant.voice.audio_io_manager import AudioIOManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_tts_integration_real_audio():
    logger.info("Starting Real Audio TTS integration test...")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT environment variable not set.")
        return

    # Initialize Real TTS Manager
    logger.info(f"Initializing TTSManager with project_id: {project_id}")
    tts_manager = TTSManager(project_id=project_id)
    
    # Initialize Real Audio IO Manager
    # We use default devices
    logger.info("Initializing AudioIOManager...")
    audio_io = AudioIOManager()
    
    # Initialize Orchestrator but patch __init__ to avoid full setup
    with patch.object(VoiceOrchestrator, '__init__', return_value=None):
        orchestrator = VoiceOrchestrator()
        
        # Manually inject dependencies
        orchestrator.tts_manager = tts_manager
        orchestrator.audio_io_manager = audio_io
        
        # Simulate a tool status update
        test_status = "I am reading the file main.py to understand the code structure."
        logger.info(f"Simulating tool status update: '{test_status}'")
        
        # This should trigger TTS and Audio Playback
        await orchestrator._on_tool_status_update(test_status)
        
        logger.info("Waiting for audio playback to complete...")
        # Wait enough time for the audio to play
        time.sleep(5) 
        
        # Cleanup
        audio_io.shutdown()
    
    print("\nTest Completed! You should have heard the voice.")

if __name__ == "__main__":
    asyncio.run(test_tts_integration_real_audio())
