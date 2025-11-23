"""End-to-end voice test script.

This script tests the full voice loop:
1. Captures audio from microphone
2. Sends to Voice Orchestrator
3. Receives audio response from Agent
4. Plays back response

Requires:
- sounddevice
- numpy
- python-dotenv
"""

import asyncio
import logging
import os
import sys
import signal
import threading
from typing import Optional
import queue

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import sounddevice as sd
    import numpy as np
    from dotenv import load_dotenv
    from scipy import signal
except ImportError as e:
    print("Missing dependencies. Please run:")
    print("pip install sounddevice numpy python-dotenv scipy")
    sys.exit(1)

from voice_ai_assistant.orchestration.voice_orchestrator import VoiceOrchestrator, OrchestratorConfig

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Also set debug for vertex_client
logging.getLogger('voice_ai_assistant.voice.vertex_client').setLevel(logging.DEBUG)

# Audio settings
HARDWARE_SAMPLE_RATE = 48000  # Scarlett interface sample rate
VERTEX_INPUT_RATE = 16000     # What Vertex AI expects for input
VERTEX_OUTPUT_RATE = 24000    # What Vertex AI sends for output
CHANNELS = 1
BLOCK_SIZE = 1024
DTYPE = 'int16'

class VoiceLoopTester:
    def __init__(self):
        self.orchestrator: Optional[VoiceOrchestrator] = None
        self.session_id: Optional[str] = None
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.loop = None
        self.audio_buffer = []  # Accumulate audio chunks for current turn
        self.is_playing = False  # Flag to prevent overlapping playback
        
    async def setup(self):
        """Initialize the system."""
        load_dotenv()
        
        # Check env vars
        required_vars = [
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT",
            "CLAUDE_API_KEY"
        ]
        
        missing = [v for v in required_vars if not os.getenv(v)]
        if missing:
            print(f"Missing environment variables: {', '.join(missing)}")
            print("Please check your .env file.")
            sys.exit(1)
            
        # Config
        config = OrchestratorConfig(
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            region=os.getenv("GOOGLE_CLOUD_REGION", "us-central1"),
            model=os.getenv("VERTEX_AI_MODEL", "gemini-2.0-flash-exp"),
            agent_model=os.getenv("STRANDS_MODEL", "claude-sonnet-4-5-20250929")
        )
        
        self.orchestrator = VoiceOrchestrator(config)
        
        # Set callbacks
        self.orchestrator.set_session_started_callback(
            lambda sid: logger.info(f"Session started: {sid}")
        )
        self.orchestrator.set_conversation_turn_callback(
            lambda sid, role, text: print(f"\n[{role.upper()}]: {text}")
        )
        self.orchestrator.set_error_callback(
            lambda sid, err: logger.error(f"Error: {err}")
        )
        
        # We need to handle audio output here
        # The orchestrator sends audio bytes to the session manager's callback
        # But currently VoiceOrchestrator._on_audio_response just logs it
        # We need to hook into the session manager directly or modify orchestrator to expose it
        # For this test, we'll hook into the session manager's callback via the orchestrator
        
        await self.orchestrator.start()
        self.session_id = await self.orchestrator.start_conversation()
        
        # Hack: Override the session manager's audio callback to play audio
        # In a real app, the orchestrator would likely pass this to a client
        original_callback = self.orchestrator.session_manager._on_audio_response
        
        def audio_callback(sid, data):
            if original_callback:
                original_callback(sid, data)
            self.play_audio(data)
            
        self.orchestrator.session_manager.set_audio_response_callback(audio_callback)
        
    def play_audio(self, data: bytes):
        """Play back received audio with resampling."""
        try:
            # Convert bytes to numpy array (Vertex AI sends at 24kHz)
            audio_np = np.frombuffer(data, dtype=np.int16)

            # Resample from 24kHz to 48kHz for Scarlett
            num_samples_output = int(len(audio_np) * HARDWARE_SAMPLE_RATE / VERTEX_OUTPUT_RATE)
            resampled = signal.resample(audio_np, num_samples_output)

            # Convert back to int16
            resampled_int16 = resampled.astype(np.int16)

            logger.debug(f"Resampled audio: {len(audio_np)} @ 24kHz -> {len(resampled_int16)} @ 48kHz samples")

            # Accumulate chunks in buffer
            self.audio_buffer.append(resampled_int16)

            # If we're not currently playing, start playback in a thread
            if not self.is_playing:
                self.is_playing = True
                threading.Thread(target=self._play_buffered_audio, daemon=True).start()

        except Exception as e:
            logger.error(f"Error processing audio for playback: {e}")

    def _play_buffered_audio(self):
        """Play all accumulated audio chunks in a separate thread."""
        try:
            while self.is_running and (len(self.audio_buffer) > 0 or self.is_playing):
                if len(self.audio_buffer) > 0:
                    # Concatenate all buffered chunks
                    full_audio = np.concatenate(self.audio_buffer)
                    logger.info(f"Playing {len(full_audio)} samples ({len(full_audio)/HARDWARE_SAMPLE_RATE:.2f}s)")

                    # Clear buffer before playing
                    self.audio_buffer = []

                    # Play the full audio (blocking in this thread)
                    sd.play(full_audio, HARDWARE_SAMPLE_RATE)
                    sd.wait()  # Wait for playback to complete
                else:
                    # Small delay to avoid busy waiting
                    import time
                    time.sleep(0.01)

        except Exception as e:
            logger.error(f"Error playing buffered audio: {e}")
        finally:
            self.is_playing = False

    def audio_input_callback(self, indata, frames, time, status):
        """Callback for sounddevice input with resampling."""
        if status:
            print(status, file=sys.stderr)

        if self.is_running and self.loop and self.session_id:
            # Convert to numpy array for resampling
            audio_np = indata.flatten()

            # Log audio level for debugging
            audio_level = np.abs(audio_np).mean()

            # Resample from 48kHz to 16kHz for Vertex AI
            num_samples_output = int(len(audio_np) * VERTEX_INPUT_RATE / HARDWARE_SAMPLE_RATE)
            resampled = signal.resample(audio_np, num_samples_output)

            # Convert back to int16 and then to bytes
            resampled_int16 = resampled.astype(np.int16)
            data = resampled_int16.tobytes()

            if audio_level > 0.01:  # Only log if there's significant audio
                logger.debug(f"Audio captured: {frames} frames @ 48kHz -> {len(resampled_int16)} samples @ 16kHz, level: {audio_level:.4f}")

            # Send resampled audio to Vertex AI
            asyncio.run_coroutine_threadsafe(
                self.orchestrator.send_audio_chunk(self.session_id, data),
                self.loop
            )

    async def run(self, input_device=None, output_device=None):
        """Run the voice loop."""
        await self.setup()
        self.is_running = True
        self.loop = asyncio.get_running_loop()

        print("\n=== Voice AI Assistant Test ===")
        print(f"Input Device: {input_device if input_device is not None else 'Default'}")
        print(f"Output Device: {output_device if output_device is not None else 'Default'}")
        print(f"Hardware Sample Rate: {HARDWARE_SAMPLE_RATE} Hz")
        print(f"Vertex AI Input: {VERTEX_INPUT_RATE} Hz, Output: {VERTEX_OUTPUT_RATE} Hz")
        print("Listening... (Press Ctrl+C to stop)")
        print("Speak into your microphone.")

        try:
            # Create input stream only - output is handled by sd.play() in play_audio()
            with sd.InputStream(
                device=input_device,
                samplerate=HARDWARE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_SIZE,
                callback=self.audio_input_callback
            ):
                while self.is_running:
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        self.is_running = False
        if self.orchestrator:
            await self.orchestrator.stop()
        print("\nTest stopped.")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Voice AI Assistant E2E Test')
    parser.add_argument('--input-device', type=int, help='Input device index')
    parser.add_argument('--output-device', type=int, help='Output device index')
    args = parser.parse_args()

    tester = VoiceLoopTester()
    
    # Handle Ctrl+C
    loop = asyncio.get_running_loop()
    
    try:
        await tester.run(input_device=args.input_device, output_device=args.output_device)
    except KeyboardInterrupt:
        await tester.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
