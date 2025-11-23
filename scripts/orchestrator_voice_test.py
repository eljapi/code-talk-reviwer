"""Orchestrator voice test script.

This script tests the full voice loop using the VoiceOrchestrator with Gemini function calling:
1. Uses AudioIOManager for mic capture and playback
2. Sends audio to Gemini 2.0 Live API via VoiceOrchestrator
3. Gemini handles conversation AND tool calling (Claude Code)
4. Tools are executed when Gemini requests them
5. Plays back synthesized voice responses from Gemini

This demonstrates native function calling with streaming voice.
"""

import asyncio
import logging
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print("Missing dependencies. Please run:")
    print("pip install python-dotenv")
    sys.exit(1)

from voice_ai_assistant.orchestration import VoiceOrchestrator, OrchestratorConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Also set debug for important modules
logging.getLogger('voice_ai_assistant.voice.vertex_client').setLevel(logging.DEBUG)
logging.getLogger('voice_ai_assistant.voice.audio_io_manager').setLevel(logging.INFO)
logging.getLogger('voice_ai_assistant.orchestration.voice_orchestrator').setLevel(logging.INFO)


class OrchestratorVoiceTester:
    """Test harness for VoiceOrchestrator with full audio I/O integration."""

    def __init__(self, input_device=None, output_device=None):
        """Initialize the tester.

        Args:
            input_device: Sounddevice input device index (None for default)
            output_device: Sounddevice output device index (None for default)
        """
        self.orchestrator = None
        self.session_id = None
        self.is_running = False
        self.input_device = input_device
        self.output_device = output_device

    async def setup(self):
        """Initialize the orchestrator."""
        load_dotenv()

        # Check required env vars
        required_vars = [
            "GOOGLE_AI_API_KEY",
            "CLAUDE_API_KEY"
        ]

        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            print(f"Missing environment variables: {', '.join(missing)}")
            print("Please check your .env file.")
            sys.exit(1)

        # Get audio settings from env or use defaults
        hardware_sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))

        # Get repository base path (parent directory of all projects)
        repository_base_path = os.getenv("REPOSITORY_BASE_PATH")
        if repository_base_path:
            logger.info(f"Using repository base path: {repository_base_path}")
        else:
            # Default to current directory if not specified
            repository_base_path = os.getcwd()
            logger.info(f"No REPOSITORY_BASE_PATH set, using current directory: {repository_base_path}")

        # Create orchestrator config
        config = OrchestratorConfig(
            model=os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash-native-audio-preview-09-2025"),
            hardware_sample_rate=hardware_sample_rate,
            vertex_input_rate=16000,
            vertex_output_rate=24000,
            input_device=self.input_device,
            output_device=self.output_device,
            repository_base_path=repository_base_path
        )

        # Create and start orchestrator
        self.orchestrator = VoiceOrchestrator(config)

        # Set up event callbacks for monitoring
        self.orchestrator.set_session_started_callback(
            lambda sid: logger.info(f"✅ Session started: {sid}")
        )
        self.orchestrator.set_session_ended_callback(
            lambda sid: logger.info(f"🛑 Session ended: {sid}")
        )
        self.orchestrator.set_conversation_turn_callback(
            self._on_conversation_turn
        )
        self.orchestrator.set_error_callback(
            lambda sid, err: logger.error(f"❌ Error in session {sid}: {err}")
        )

        # Start the orchestrator
        await self.orchestrator.start()
        logger.info("Orchestrator started successfully")

    def _on_conversation_turn(self, session_id: str, role: str, text: str):
        """Handle conversation turn events."""
        if role == "user":
            print(f"\n🎤 [YOU]: {text}")
        elif role == "agent":
            print(f"🤖 [AGENT]: {text}", end='', flush=True)

    async def run(self):
        """Run the voice test loop."""
        await self.setup()
        self.is_running = True

        print("\n" + "="*60)
        print("🎙️  Voice AI Coding Assistant - Orchestrator Test")
        print("="*60)
        print(f"Input Device: {self.input_device if self.input_device is not None else 'Default'}")
        print(f"Output Device: {self.output_device if self.output_device is not None else 'Default'}")
        print(f"Sample Rate: {self.orchestrator.config.hardware_sample_rate} Hz")
        print(f"Repository Base: {self.orchestrator.config.repository_base_path}")
        print("="*60)
        print("\nℹ️  The orchestrator will:")
        print("  1. Capture audio from your microphone (resampled 48kHz → 16kHz)")
        print("  2. Send to Gemini 2.0 Live API for transcription & conversation")
        print("  3. Gemini invokes Claude Code tool when needed (e.g., 'read this file')")
        print("  4. Tool results are sent back to Gemini")
        print("  5. Gemini synthesizes voice response with tool results")
        print("  6. Play back response (resampled 24kHz → 48kHz)")
        print("\n▶️  Starting... (Press Ctrl+C to stop)")
        print("🎤 Speak into your microphone.")
        print("💡 Try: 'What files are in this project?' or 'Read the main.py file'\n")

        try:
            # Start conversation session with audio capture enabled
            self.session_id = await self.orchestrator.start_conversation(
                user_id="test_user",
                enable_audio_capture=True
            )

            logger.info(f"Started conversation session: {self.session_id}")

            # Keep running until interrupted
            while self.is_running:
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info("Received cancellation signal")
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")
        self.is_running = False

        if self.orchestrator:
            # End conversation session
            if self.session_id:
                await self.orchestrator.end_conversation(self.session_id)

            # Stop orchestrator
            await self.orchestrator.stop()

        print("\n👋 Test stopped. Goodbye!")


async def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Voice AI Assistant Orchestrator Test')
    parser.add_argument('--input-device', type=int, help='Input device index')
    parser.add_argument('--output-device', type=int, help='Output device index')
    args = parser.parse_args()

    tester = OrchestratorVoiceTester(
        input_device=args.input_device,
        output_device=args.output_device
    )

    try:
        await tester.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
