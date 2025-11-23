"""Main voice conversation orchestrator.

Coordinates between Vertex AI Live API and Strands Agent for real-time
voice-to-voice conversations with intelligent code assistance.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable

from ..voice.session_manager import VoiceSessionManager
from ..voice.audio_io_manager import AudioIOManager
from .orchestrator_config import OrchestratorConfig
from .orchestration_session import OrchestrationSession
from .flow_manager import ConversationFlowManager
from .pipeline import StreamingPipelineManager

logger = logging.getLogger(__name__)


class VoiceOrchestrator:
    """Main orchestrator for voice conversations with AI agent.
    
    This class coordinates the entire voice conversation pipeline:
    1. Manages Vertex AI Live API sessions
    2. Integrates with Strands Agent
    3. Handles real-time streaming between voice and agent
    4. Manages conversation flow and interruptions
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """Initialize voice orchestrator.
        
        Args:
            config: Orchestrator configuration
        """
        self.config = config or OrchestratorConfig()
        
        # Core components
        self.session_manager = VoiceSessionManager(
            project_id=self.config.project_id,
            region=self.config.region,
            model=self.config.model,
            session_timeout_minutes=self.config.session_timeout_minutes
        )
        
        self.flow_manager = ConversationFlowManager(
            max_turns=self.config.max_conversation_turns,
            enable_interruption=self.config.enable_interruption
        )
        
        self.pipeline_manager = StreamingPipelineManager(
            max_latency_ms=self.config.max_response_latency_ms
        )

        # Audio I/O Manager
        self.audio_io_manager = AudioIOManager(
            hardware_sample_rate=self.config.hardware_sample_rate,
            vertex_input_rate=self.config.vertex_input_rate,
            vertex_output_rate=self.config.vertex_output_rate,
            channels=1,
            block_size=self.config.audio_chunk_size,
            dtype='int16',
            input_device=self.config.input_device,
            output_device=self.config.output_device
        )

        # Active orchestration sessions
        self._active_sessions: Dict[str, 'OrchestrationSession'] = {}
        self._is_running = False
        
        # Event callbacks
        self._on_session_started: Optional[Callable[[str], None]] = None
        self._on_session_ended: Optional[Callable[[str], None]] = None
        self._on_conversation_turn: Optional[Callable[[str, str, str], None]] = None
        self._on_error: Optional[Callable[[str, Exception], None]] = None
        
    async def start(self) -> None:
        """Start the voice orchestrator."""
        if self._is_running:
            return
            
        logger.info("Starting voice orchestrator")
        
        # Start underlying components
        await self.session_manager.start()
        await self.flow_manager.start()
        await self.pipeline_manager.start()
        
        # Set up session manager callbacks
        self.session_manager.set_session_created_callback(self._on_voice_session_created)
        self.session_manager.set_session_ended_callback(self._on_voice_session_ended)
        self.session_manager.set_audio_response_callback(self._on_audio_response)
        self.session_manager.set_text_response_callback(self._on_text_response)
        self.session_manager.set_error_callback(self._on_voice_error)
        
        self._is_running = True
        logger.info("Voice orchestrator started successfully")
        
    async def stop(self) -> None:
        """Stop the voice orchestrator."""
        if not self._is_running:
            return

        logger.info("Stopping voice orchestrator")

        # Stop audio I/O
        self.stop_audio_capture()
        self.stop_audio_playback()

        # End all active sessions
        for session_id in list(self._active_sessions.keys()):
            await self.end_conversation(session_id)

        # Shutdown audio I/O manager
        self.audio_io_manager.shutdown()

        # Stop underlying components
        await self.session_manager.stop()
        await self.flow_manager.stop()
        await self.pipeline_manager.stop()

        self._is_running = False
        logger.info("Voice orchestrator stopped")
        
    async def start_conversation(self, user_id: Optional[str] = None, enable_audio_capture: bool = True) -> str:
        """Start a new voice conversation.

        Args:
            user_id: Optional user identifier
            enable_audio_capture: Whether to start microphone capture automatically

        Returns:
            Session ID for the conversation

        Raises:
            RuntimeError: If orchestrator not running or session limit reached
        """
        if not self._is_running:
            raise RuntimeError("Orchestrator not running")

        if len(self._active_sessions) >= self.config.max_concurrent_sessions:
            raise RuntimeError("Maximum concurrent sessions reached")

        try:
            # Create voice session
            voice_session_id = await self.session_manager.create_session(user_id)

            # Create orchestration session
            orchestration_session = OrchestrationSession(
                session_id=voice_session_id,
                user_id=user_id,
                orchestrator=self,
                agent_model=self.config.agent_model
            )

            # Initialize agent
            await orchestration_session.initialize_agent()

            # Initialize conversation flow
            await self.flow_manager.initialize_conversation(voice_session_id)

            # Initialize streaming pipeline
            await self.pipeline_manager.initialize_session(voice_session_id)

            # Store active session
            self._active_sessions[voice_session_id] = orchestration_session

            # Start audio capture if enabled
            if enable_audio_capture:
                await self.start_audio_capture(voice_session_id)

            logger.info(f"Started conversation session: {voice_session_id}")

            # Notify callback
            if self._on_session_started:
                self._on_session_started(voice_session_id)

            return voice_session_id

        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            raise
            
    async def end_conversation(self, session_id: str) -> None:
        """End a voice conversation.
        
        Args:
            session_id: Session to end
        """
        if session_id not in self._active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
            
        try:
            # Clean up orchestration session
            orchestration_session = self._active_sessions[session_id]
            await orchestration_session.cleanup()
            
            # Clean up flow manager
            await self.flow_manager.end_conversation(session_id)
            
            # Clean up pipeline manager
            await self.pipeline_manager.cleanup_session(session_id)
            
            # End voice session
            await self.session_manager.end_session(session_id)
            
            # Remove from active sessions
            del self._active_sessions[session_id]
            
            logger.info(f"Ended conversation session: {session_id}")
            
            # Notify callback
            if self._on_session_ended:
                self._on_session_ended(session_id)
                
        except Exception as e:
            logger.error(f"Error ending conversation {session_id}: {e}")
            
    async def send_audio_chunk(self, session_id: str, audio_data: bytes) -> None:
        """Send audio chunk to conversation session.
        
        Args:
            session_id: Target session
            audio_data: PCM audio data
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session not found: {session_id}")
            
        # Forward to session manager
        await self.session_manager.send_audio_chunk(session_id, audio_data)
        
    async def interrupt_conversation(self, session_id: str) -> None:
        """Interrupt current conversation (barge-in).
        
        Args:
            session_id: Session to interrupt
        """
        if session_id not in self._active_sessions:
            logger.warning(f"Session not found for interruption: {session_id}")
            return
            
        try:
            # Handle interruption in flow manager
            await self.flow_manager.handle_interruption(session_id)
            
            # Handle interruption in pipeline
            await self.pipeline_manager.handle_interruption(session_id)
            
            logger.info(f"Interrupted conversation: {session_id}")
            
        except Exception as e:
            logger.error(f"Error interrupting conversation {session_id}: {e}")
            
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session state.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session state information or None if not found
        """
        if session_id not in self._active_sessions:
            return None
            
        orchestration_session = self._active_sessions[session_id]
        voice_state = self.session_manager.get_session_state(session_id)
        flow_state = self.flow_manager.get_conversation_state(session_id)
        pipeline_state = self.pipeline_manager.get_session_state(session_id)
        
        return {
            'session_id': session_id,
            'user_id': orchestration_session.user_id,
            'voice_state': voice_state.__dict__ if voice_state else None,
            'flow_state': flow_state,
            'pipeline_state': pipeline_state,
            'is_active': True
        }
        
    def list_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active conversation sessions.

        Returns:
            Dictionary of session ID to session state
        """
        return {
            session_id: self.get_session_state(session_id)
            for session_id in self._active_sessions.keys()
        }

    async def start_audio_capture(self, session_id: str) -> None:
        """Start capturing audio from microphone for a session.

        Args:
            session_id: Session to capture audio for

        Raises:
            ValueError: If session not found
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session not found: {session_id}")

        # Create audio callback that sends to Vertex AI
        async def audio_callback(audio_data: bytes):
            await self.send_audio_chunk(session_id, audio_data)

        # Start capture with the callback
        event_loop = asyncio.get_running_loop()
        self.audio_io_manager.start_capture(audio_callback, event_loop)

        logger.info(f"Started audio capture for session: {session_id}")

    def stop_audio_capture(self) -> None:
        """Stop capturing audio from microphone."""
        self.audio_io_manager.stop_capture()
        logger.info("Stopped audio capture")

    def stop_audio_playback(self) -> None:
        """Stop audio playback and clear buffer."""
        self.audio_io_manager.stop_playback()
        logger.info("Stopped audio playback")

    # Internal event handlers
    
    async def _on_voice_session_created(self, session_id: str) -> None:
        """Handle voice session creation."""
        logger.debug(f"Voice session created: {session_id}")
        
    async def _on_voice_session_ended(self, session_id: str) -> None:
        """Handle voice session end."""
        logger.debug(f"Voice session ended: {session_id}")
        
        # Clean up orchestration session if exists
        if session_id in self._active_sessions:
            await self.end_conversation(session_id)
            
    async def _on_audio_response(self, session_id: str, audio_data: bytes) -> None:
        """Handle audio response from Vertex AI.

        Plays back audio through the AudioIOManager with proper resampling.
        """
        if session_id not in self._active_sessions:
            return

        try:
            # Process through pipeline manager
            await self.pipeline_manager.process_audio_response(session_id, audio_data)

            # Play back audio (with resampling from 24kHz to hardware rate)
            self.audio_io_manager.play_audio(audio_data)

            logger.debug(f"Processed and played audio response for session: {session_id}")

        except Exception as e:
            logger.error(f"Error processing audio response for {session_id}: {e}")
            if self._on_error:
                self._on_error(session_id, e)
                
    async def _on_text_response(self, session_id: str, text: str) -> None:
        """Handle text response from Vertex AI.
        
        This represents transcribed user speech that needs to be
        processed by the Strands Agent.
        """
        if session_id not in self._active_sessions:
            return
            
        try:
            # Process through flow manager
            await self.flow_manager.process_user_input(session_id, text)
            
            logger.info(f"Processing user input for session {session_id}: {text}")
            
            # Notify conversation turn callback
            if self._on_conversation_turn:
                self._on_conversation_turn(session_id, "user", text)
                
            # Send to Strands Agent
            session = self._active_sessions[session_id]
            if session.agent:
                # Stream agent response back to Vertex AI
                async for chunk in session.agent.process_message(text):
                    # Send text chunk to Vertex AI to be spoken
                    await self.session_manager.send_text_message(session_id, chunk)
                    
                    # Notify callback for agent response
                    if self._on_conversation_turn:
                        self._on_conversation_turn(session_id, "agent", chunk)
            
        except Exception as e:
            logger.error(f"Error processing text response for {session_id}: {e}")
            if self._on_error:
                self._on_error(session_id, e)
                
    async def _on_voice_error(self, session_id: str, error: Exception) -> None:
        """Handle voice session errors."""
        logger.error(f"Voice session error for {session_id}: {error}")
        
        if self._on_error:
            self._on_error(session_id, error)
            
    # Event callback setters
    
    def set_session_started_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for session start events."""
        self._on_session_started = callback
        
    def set_session_ended_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for session end events."""
        self._on_session_ended = callback
        
    def set_conversation_turn_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """Set callback for conversation turn events.
        
        Args:
            callback: Function that receives (session_id, speaker, message)
        """
        self._on_conversation_turn = callback
        
    def set_error_callback(self, callback: Callable[[str, Exception], None]) -> None:
        """Set callback for error events."""
        self._on_error = callback