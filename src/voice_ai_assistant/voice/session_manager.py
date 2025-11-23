"""Session management for Vertex AI Live API connections."""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

from .vertex_client import VertexLiveClient, VertexLiveAPIError
from .auth import VertexAuthManager

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Represents the state of a voice session."""
    
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    is_listening: bool = False
    is_speaking: bool = False
    interruption_count: int = 0
    total_audio_chunks: int = 0
    total_responses: int = 0
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()
        
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired.
        
        Args:
            timeout_minutes: Session timeout in minutes
            
        Returns:
            True if session has expired
        """
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.now() - self.last_activity > timeout


class VoiceSessionManager:
    """Manages multiple voice sessions with automatic reconnection."""
    
    def __init__(self, 
                 project_id: Optional[str] = None,
                 region: str = "us-central1",
                 model: str = "gemini-2.0-flash-exp",
                 session_timeout_minutes: int = 30,
                 max_reconnect_attempts: int = 3):
        """Initialize session manager.
        
        Args:
            project_id: Google Cloud project ID
            region: Google Cloud region
            model: Gemini model for Live API
            session_timeout_minutes: Session timeout in minutes
            max_reconnect_attempts: Maximum reconnection attempts
        """
        self.auth_manager = VertexAuthManager(project_id)
        self.region = region
        self.model = model
        self.session_timeout_minutes = session_timeout_minutes
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Active sessions
        self._sessions: Dict[str, VertexLiveClient] = {}
        self._session_states: Dict[str, SessionState] = {}
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Event callbacks
        self._on_session_created: Optional[Callable[[str], None]] = None
        self._on_session_ended: Optional[Callable[[str], None]] = None
        self._on_audio_response: Optional[Callable[[str, bytes], None]] = None
        self._on_text_response: Optional[Callable[[str, str], None]] = None
        self._on_error: Optional[Callable[[str, Exception], None]] = None
        
    async def start(self) -> None:
        """Start the session manager."""
        if self._is_running:
            return
            
        logger.info("Starting voice session manager")
        self._is_running = True
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        
    async def stop(self) -> None:
        """Stop the session manager and close all sessions."""
        if not self._is_running:
            return
            
        logger.info("Stopping voice session manager")
        self._is_running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
        # Close all active sessions
        for session_id in list(self._sessions.keys()):
            await self.end_session(session_id)
            
    async def create_session(self, user_id: Optional[str] = None) -> str:
        """Create a new voice session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            Session ID
            
        Raises:
            VertexLiveAPIError: If session creation fails
        """
        session_id = str(uuid.uuid4())
        
        try:
            # Create Vertex AI client
            client = VertexLiveClient(
                project_id=self.auth_manager.project_id,
                region=self.region,
                model=self.model,
                auth_manager=self.auth_manager
            )
            
            # Set up callbacks
            client.set_audio_response_callback(
                lambda audio_data: self._handle_audio_response(session_id, audio_data)
            )
            client.set_text_response_callback(
                lambda text: self._handle_text_response(session_id, text)
            )
            client.set_error_callback(
                lambda error: self._handle_error(session_id, error)
            )
            
            # Connect to Live API
            await client.connect()
            
            # Store session
            self._sessions[session_id] = client
            self._session_states[session_id] = SessionState(
                session_id=session_id,
                user_id=user_id
            )
            
            logger.info(f"Created voice session: {session_id}")
            
            # Start listening for responses
            asyncio.create_task(self._listen_for_responses(session_id))
            
            # Notify callback
            if self._on_session_created:
                if asyncio.iscoroutinefunction(self._on_session_created):
                    await self._on_session_created(session_id)
                else:
                    self._on_session_created(session_id)
                
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise VertexLiveAPIError(f"Session creation failed: {e}")
            
    async def end_session(self, session_id: str) -> None:
        """End a voice session.

        Args:
            session_id: Session to end
        """
        if session_id not in self._sessions:
            logger.warning(f"Session not found: {session_id}")
            return

        try:
            # Disconnect client
            client = self._sessions[session_id]
            await client.disconnect()

            # Update session state
            if session_id in self._session_states:
                self._session_states[session_id].is_active = False

            # Remove from active sessions
            del self._sessions[session_id]

            logger.info(f"Ended voice session: {session_id}")

            # Notify callback
            if self._on_session_ended:
                if asyncio.iscoroutinefunction(self._on_session_ended):
                    await self._on_session_ended(session_id)
                else:
                    self._on_session_ended(session_id)

        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")

    async def send_audio_chunk(self, session_id: str, audio_data: bytes) -> None:
        """Send audio chunk to a session.

        Args:
            session_id: Target session
            audio_data: PCM audio data

        Raises:
            VertexLiveAPIError: If session not found or send fails
        """
        client = self._get_session_client(session_id)
        state = self._session_states[session_id]
        
        try:
            await client.send_audio_chunk(audio_data)
            state.total_audio_chunks += 1
            state.update_activity()
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk to session {session_id}: {e}")
            await self._handle_connection_error(session_id, e)
            
    async def send_text_message(self, session_id: str, text: str) -> None:
        """Send text message to a session.
        
        Args:
            session_id: Target session
            text: Text message
            
        Raises:
            VertexLiveAPIError: If session not found or send fails
        """
        client = self._get_session_client(session_id)
        state = self._session_states[session_id]
        
        try:
            await client.send_text_message(text)
            state.update_activity()
            
        except Exception as e:
            logger.error(f"Failed to send text message to session {session_id}: {e}")
            await self._handle_connection_error(session_id, e)
            
    async def stream_audio_file(self, session_id: str, file_path: str) -> None:
        """Stream audio file to a session.
        
        Args:
            session_id: Target session
            file_path: Path to audio file
            
        Raises:
            VertexLiveAPIError: If session not found or streaming fails
        """
        client = self._get_session_client(session_id)
        state = self._session_states[session_id]
        
        try:
            await client.stream_audio_file(file_path)
            state.update_activity()
            
        except Exception as e:
            logger.error(f"Failed to stream audio file to session {session_id}: {e}")
            await self._handle_connection_error(session_id, e)
            
    def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """Get session state.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session state or None if not found
        """
        return self._session_states.get(session_id)
        
    def list_active_sessions(self) -> Dict[str, SessionState]:
        """List all active sessions.
        
        Returns:
            Dictionary of session ID to session state
        """
        return {
            session_id: state 
            for session_id, state in self._session_states.items()
            if state.is_active
        }
        
    def _get_session_client(self, session_id: str) -> VertexLiveClient:
        """Get client for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Vertex AI client
            
        Raises:
            VertexLiveAPIError: If session not found
        """
        if session_id not in self._sessions:
            raise VertexLiveAPIError(f"Session not found: {session_id}")
        return self._sessions[session_id]
        
    async def _listen_for_responses(self, session_id: str) -> None:
        """Listen for responses from a session.
        
        Args:
            session_id: Session to listen to
        """
        try:
            client = self._get_session_client(session_id)
            await client.listen_for_responses()
            
        except Exception as e:
            logger.error(f"Error listening to session {session_id}: {e}")
            await self._handle_connection_error(session_id, e)
            
    async def _handle_connection_error(self, session_id: str, error: Exception) -> None:
        """Handle connection errors with automatic reconnection.
        
        Args:
            session_id: Session with error
            error: The error that occurred
        """
        if session_id not in self._sessions:
            return
            
        client = self._sessions[session_id]
        state = self._session_states[session_id]
        
        logger.warning(f"Connection error in session {session_id}: {error}")
        
        # Attempt reconnection
        if await client.reconnect(self.max_reconnect_attempts):
            logger.info(f"Successfully reconnected session {session_id}")
            # Restart listening
            asyncio.create_task(self._listen_for_responses(session_id))
        else:
            logger.error(f"Failed to reconnect session {session_id}, ending session")
            await self.end_session(session_id)
            
    def _handle_audio_response(self, session_id: str, audio_data: bytes) -> None:
        """Handle audio response from session.
        
        Args:
            session_id: Session ID
            audio_data: Audio response data
        """
        if session_id in self._session_states:
            state = self._session_states[session_id]
            state.total_responses += 1
            state.update_activity()
            
        if self._on_audio_response:
            self._on_audio_response(session_id, audio_data)
            
    def _handle_text_response(self, session_id: str, text: str) -> None:
        """Handle text response from session.
        
        Args:
            session_id: Session ID
            text: Text response
        """
        if session_id in self._session_states:
            state = self._session_states[session_id]
            state.total_responses += 1
            state.update_activity()
            
        if self._on_text_response:
            self._on_text_response(session_id, text)
            
    def _handle_error(self, session_id: str, error: Exception) -> None:
        """Handle error from session.
        
        Args:
            session_id: Session ID
            error: The error that occurred
        """
        if self._on_error:
            self._on_error(session_id, error)
            
    async def _cleanup_expired_sessions(self) -> None:
        """Background task to clean up expired sessions."""
        while self._is_running:
            try:
                expired_sessions = []
                
                for session_id, state in self._session_states.items():
                    if state.is_expired(self.session_timeout_minutes):
                        expired_sessions.append(session_id)
                        
                for session_id in expired_sessions:
                    logger.info(f"Cleaning up expired session: {session_id}")
                    await self.end_session(session_id)
                    
                # Clean up session states
                for session_id in expired_sessions:
                    if session_id in self._session_states:
                        del self._session_states[session_id]
                        
                # Sleep before next cleanup
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                await asyncio.sleep(60)
                
    # Event callback setters
    def set_session_created_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for session creation events."""
        self._on_session_created = callback
        
    def set_session_ended_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for session end events."""
        self._on_session_ended = callback
        
    def set_audio_response_callback(self, callback: Callable[[str, bytes], None]) -> None:
        """Set callback for audio response events."""
        self._on_audio_response = callback
        
    def set_text_response_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for text response events."""
        self._on_text_response = callback
        
    def set_error_callback(self, callback: Callable[[str, Exception], None]) -> None:
        """Set callback for error events."""
        self._on_error = callback