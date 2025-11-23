"""Voice orchestration demonstration script.

Shows how to use the voice conversation orchestration system
to coordinate between Vertex AI Live API and Strands Agent.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from voice_ai_assistant.orchestration import VoiceOrchestrator, OrchestratorConfig
from voice_ai_assistant.voice.audio_stream import create_test_audio_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VoiceOrchestrationDemo:
    """Demonstration of voice orchestration capabilities."""
    
    def __init__(self):
        """Initialize the demo."""
        self.orchestrator = None
        self.is_running = False
        
    async def setup(self) -> None:
        """Set up the orchestration system."""
        logger.info("Setting up voice orchestration demo")
        
        # Create orchestrator configuration
        config = OrchestratorConfig(
            project_id="your-gcp-project-id",  # Replace with actual project ID
            region="us-central1",
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            max_concurrent_sessions=3,
            session_timeout_minutes=15,
            max_response_latency_ms=300,
            enable_interruption=True
        )
        
        # Create orchestrator
        self.orchestrator = VoiceOrchestrator(config)
        
        # Set up event callbacks
        self.orchestrator.set_session_started_callback(self._on_session_started)
        self.orchestrator.set_session_ended_callback(self._on_session_ended)
        self.orchestrator.set_conversation_turn_callback(self._on_conversation_turn)
        self.orchestrator.set_error_callback(self._on_error)
        
        # Start orchestrator
        await self.orchestrator.start()
        self.is_running = True
        
        logger.info("Voice orchestration demo setup complete")
        
    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up voice orchestration demo")
        
        if self.orchestrator:
            await self.orchestrator.stop()
            
        self.is_running = False
        logger.info("Cleanup complete")
        
    async def demo_basic_conversation(self) -> None:
        """Demonstrate basic voice conversation flow."""
        logger.info("=== Demo: Basic Voice Conversation ===")
        
        try:
            # Start a conversation session
            session_id = await self.orchestrator.start_conversation("demo-user")
            logger.info(f"Started conversation session: {session_id}")
            
            # Simulate voice interactions
            await self._simulate_voice_interaction(session_id, "Hello, can you help me with my Python code?")
            await asyncio.sleep(1)
            
            await self._simulate_voice_interaction(session_id, "I have a function that's running slowly. Can you analyze it?")
            await asyncio.sleep(1)
            
            await self._simulate_voice_interaction(session_id, "Thank you for your help!")
            await asyncio.sleep(1)
            
            # End conversation
            await self.orchestrator.end_conversation(session_id)
            logger.info(f"Ended conversation session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error in basic conversation demo: {e}")
            
    async def demo_concurrent_sessions(self) -> None:
        """Demonstrate handling multiple concurrent sessions."""
        logger.info("=== Demo: Concurrent Voice Sessions ===")
        
        sessions = []
        
        try:
            # Create multiple concurrent sessions
            for i in range(3):
                session_id = await self.orchestrator.start_conversation(f"user-{i}")
                sessions.append(session_id)
                logger.info(f"Created session {i + 1}: {session_id}")
                
            # Simulate concurrent interactions
            tasks = []
            for i, session_id in enumerate(sessions):
                task = asyncio.create_task(
                    self._simulate_voice_interaction(
                        session_id, 
                        f"User {i + 1}: Can you help me debug my code?"
                    )
                )
                tasks.append(task)
                
            # Wait for all interactions to complete
            await asyncio.gather(*tasks)
            
            # Show session states
            active_sessions = self.orchestrator.list_active_sessions()
            logger.info(f"Active sessions: {len(active_sessions)}")
            
            for session_id, state in active_sessions.items():
                logger.info(f"Session {session_id}: {state['flow_state']['state'] if state['flow_state'] else 'unknown'}")
                
        except Exception as e:
            logger.error(f"Error in concurrent sessions demo: {e}")
            
        finally:
            # Clean up sessions
            for session_id in sessions:
                try:
                    await self.orchestrator.end_conversation(session_id)
                except Exception as e:
                    logger.error(f"Error ending session {session_id}: {e}")
                    
    async def demo_interruption_handling(self) -> None:
        """Demonstrate conversation interruption (barge-in)."""
        logger.info("=== Demo: Conversation Interruption ===")
        
        try:
            session_id = await self.orchestrator.start_conversation("interruption-user")
            
            # Start a conversation
            await self._simulate_voice_interaction(
                session_id, 
                "Can you explain how to optimize this complex algorithm?"
            )
            
            # Simulate interruption after a short delay
            await asyncio.sleep(0.5)
            logger.info("Simulating user interruption (barge-in)")
            await self.orchestrator.interrupt_conversation(session_id)
            
            # Continue with new input after interruption
            await self._simulate_voice_interaction(
                session_id, 
                "Actually, let me ask about something else first."
            )
            
            await self.orchestrator.end_conversation(session_id)
            
        except Exception as e:
            logger.error(f"Error in interruption demo: {e}")
            
    async def demo_audio_file_processing(self) -> None:
        """Demonstrate processing audio files."""
        logger.info("=== Demo: Audio File Processing ===")
        
        try:
            # Create test audio file
            audio_dir = Path("demo_audio")
            audio_dir.mkdir(exist_ok=True)
            
            test_file = audio_dir / "test_query.wav"
            create_test_audio_file(test_file, duration_seconds=2.0)
            logger.info(f"Created test audio file: {test_file}")
            
            # Start session and process audio file
            session_id = await self.orchestrator.start_conversation("audio-user")
            
            # Simulate streaming the audio file
            await self._simulate_audio_file_streaming(session_id, test_file)
            
            await self.orchestrator.end_conversation(session_id)
            
        except Exception as e:
            logger.error(f"Error in audio file demo: {e}")
            
    async def _simulate_voice_interaction(self, session_id: str, user_input: str) -> None:
        """Simulate a voice interaction.
        
        Args:
            session_id: Session ID
            user_input: Simulated user speech input
        """
        logger.info(f"User says: '{user_input}'")
        
        # Simulate audio chunks for the text input
        # In real implementation, this would be actual audio data
        fake_audio_chunks = [
            f"audio_chunk_{i}_{user_input[:10]}".encode()
            for i in range(3)
        ]
        
        for chunk in fake_audio_chunks:
            await self.orchestrator.send_audio_chunk(session_id, chunk)
            await asyncio.sleep(0.1)  # Simulate streaming delay
            
    async def _simulate_audio_file_streaming(self, session_id: str, audio_file: Path) -> None:
        """Simulate streaming an audio file.
        
        Args:
            session_id: Session ID
            audio_file: Path to audio file
        """
        logger.info(f"Streaming audio file: {audio_file}")
        
        # In real implementation, this would use AudioStreamManager
        # For demo, we'll simulate with fake chunks
        for i in range(5):
            fake_chunk = f"audio_file_chunk_{i}".encode()
            await self.orchestrator.send_audio_chunk(session_id, fake_chunk)
            await asyncio.sleep(0.2)  # Simulate file streaming
            
    # Event callbacks
    
    def _on_session_started(self, session_id: str) -> None:
        """Handle session start event."""
        logger.info(f"🎤 Session started: {session_id}")
        
    def _on_session_ended(self, session_id: str) -> None:
        """Handle session end event."""
        logger.info(f"🔇 Session ended: {session_id}")
        
    def _on_conversation_turn(self, session_id: str, speaker: str, message: str) -> None:
        """Handle conversation turn event."""
        emoji = "👤" if speaker == "user" else "🤖"
        logger.info(f"{emoji} [{session_id}] {speaker}: {message}")
        
    def _on_error(self, session_id: str, error: Exception) -> None:
        """Handle error event."""
        logger.error(f"❌ Error in session {session_id}: {error}")
        
    async def run_demo(self) -> None:
        """Run the complete demonstration."""
        logger.info("🚀 Starting Voice Orchestration Demo")
        
        try:
            await self.setup()
            
            # Run demonstration scenarios
            await self.demo_basic_conversation()
            await asyncio.sleep(2)
            
            await self.demo_concurrent_sessions()
            await asyncio.sleep(2)
            
            await self.demo_interruption_handling()
            await asyncio.sleep(2)
            
            await self.demo_audio_file_processing()
            
            logger.info("✅ Demo completed successfully")
            
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        except Exception as e:
            logger.error(f"Demo failed: {e}")
        finally:
            await self.cleanup()


async def main():
    """Main demo function."""
    demo = VoiceOrchestrationDemo()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(demo.cleanup())
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the demo
    await demo.run_demo()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())