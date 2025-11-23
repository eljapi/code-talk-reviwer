
import asyncio
import logging
import os
import sys
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed. Please install it.")
    sys.exit(1)

from voice_ai_assistant.orchestration.voice_orchestrator import VoiceOrchestrator, OrchestratorConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_text_to_audio_flow():
    load_dotenv()
    
    # Check for API keys
    if not os.getenv("CLAUDE_API_KEY"):
        logger.error("CLAUDE_API_KEY not found in environment variables.")
        return
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
        logger.error("GOOGLE_CLOUD_PROJECT not found in environment variables.")
        return

    logger.info("Starting Text-to-Audio Flow Test...")
    
    # Configure Orchestrator
    # We use defaults, but ensure we have a valid project_id
    config = OrchestratorConfig(
        project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
        agent_model="claude-haiku-4-5-20251001", # Use a known valid model for Strands if needed, or default
        repository_base_path=os.getcwd()
    )
    
    orchestrator = VoiceOrchestrator(config)
    
    try:
        # Start the orchestrator (starts StrandsAgent, TTS, AudioIO)
        await orchestrator.start()
        
        # Manually register a test session
        session_id = "test_session_manual"
        orchestrator._active_sessions.add(session_id)
        
        # Define the test prompt
        # This prompt should trigger a tool call
        test_prompt = "Please read the README.md file in infor backend project and summarize it in one sentence."
        
        logger.info(f"Sending text input: '{test_prompt}'")
        
        # Simulate receiving text from STT
        # This will trigger:
        # 1. StrandsAgent.process_message(text)
        # 2. Agent -> Text Chunks -> TTS -> Audio
        # 3. Agent -> Tool Call (Claude Code) -> Status Updates -> TTS -> Audio
        # 4. Agent -> Final Response -> TTS -> Audio
        await orchestrator._on_text_response(session_id, test_prompt)
        
        # Wait for processing to complete
        # Since _on_text_response is async but the agent processing might yield and run,
        # we need to keep the loop alive.
        # The _on_text_response awaits the agent's generator, so it should block until the initial response is done.
        # However, if the agent does background work, we might need to wait.
        # StrandsAgent.process_message yields chunks.
        
        logger.info("Waiting for audio playback to finish...")
        # Give it enough time for the full flow (tool execution can take seconds)
        await asyncio.sleep(20) 
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        
    finally:
        logger.info("Stopping orchestrator...")
        await orchestrator.stop()

if __name__ == "__main__":
    try:
        asyncio.run(test_text_to_audio_flow())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
