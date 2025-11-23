
import asyncio
import logging
import os
import sys
import time
from unittest.mock import MagicMock, patch, AsyncMock

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv()

# Mock dependencies that might cause issues if not present or configured
sys.modules['claude_agent_sdk'] = MagicMock()
# We need to mock strands library if it's not installed in this environment
# Assuming it is installed or we mock it
try:
    import strands
except ImportError:
    sys.modules['strands'] = MagicMock()
    sys.modules['strands'].Agent = MagicMock

from voice_ai_assistant.orchestration.voice_orchestrator import VoiceOrchestrator
from voice_ai_assistant.agent.strands_agent import StrandsAgent
from voice_ai_assistant.voice.tts_manager import TTSManager
from voice_ai_assistant.voice.audio_io_manager import AudioIOManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_strands_integration():
    logger.info("Starting Strands integration test...")
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("GOOGLE_CLOUD_PROJECT environment variable not set.")
        return

    # Initialize Real TTS Manager
    tts_manager = TTSManager(project_id=project_id)
    
    # Initialize Real Audio IO Manager
    audio_io = AudioIOManager()
    
    # Mock Strands Agent to avoid actual API calls to Claude/Strands
    mock_strands_agent = MagicMock(spec=StrandsAgent)
    
    # Define a generator for process_message
    async def mock_process_message(text):
        yield "I understood that you said: " + text
        yield "I am now checking the code."
        yield "Everything looks good."
        
    mock_strands_agent.process_message = mock_process_message
    mock_strands_agent.start = AsyncMock()
    mock_strands_agent.stop = AsyncMock()

    # Initialize Orchestrator but patch __init__ to avoid full setup
    with patch.object(VoiceOrchestrator, '__init__', return_value=None):
        orchestrator = VoiceOrchestrator()
        
        # Manually inject dependencies
        orchestrator.tts_manager = tts_manager
        orchestrator.audio_io_manager = audio_io
        orchestrator.strands_agent = mock_strands_agent
        orchestrator.flow_manager = MagicMock()
        orchestrator.flow_manager.process_user_input = AsyncMock()
        orchestrator._active_sessions = {"test_session"}
        
        # Mock callbacks
        orchestrator._on_error = MagicMock()
        orchestrator._on_conversation_turn = MagicMock()
        
        # Simulate receiving text from STT (Gemini)
        test_text = "Hello, can you check the main file?"
        logger.info(f"Simulating STT text input: '{test_text}'")
        
        # This should trigger Strands Agent -> TTS -> Audio Playback
        await orchestrator._on_text_response("test_session", test_text)
        
        logger.info("Waiting for audio playback to complete...")
        time.sleep(8) # Wait for 3 chunks to play
        
        # Cleanup
        audio_io.shutdown()
    
    print("\nTest Completed! You should have heard 3 sentences.")

if __name__ == "__main__":
    asyncio.run(test_strands_integration())
