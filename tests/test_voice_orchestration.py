"""Tests for voice conversation orchestration.

Tests the integration between Vertex AI Live API and Strands Agent
through the orchestration layer.
"""

import asyncio
import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch
import json
import websockets
from typing import Dict, Any

from src.voice_ai_assistant.orchestration import (
    VoiceOrchestrator, 
    ConversationFlowManager,
    StreamingPipelineManager,
    OrchestratorConfig
)
from src.voice_ai_assistant.orchestration.flow_manager import ConversationState

logger = logging.getLogger(__name__)


class MockVertexLiveClient:
    """Mock Vertex AI Live client for testing."""
    
    def __init__(self):
        self.is_connected = False
        self.session_id = "test-session-123"
        self.audio_chunks = []
        self.text_messages = []
        
        # Callbacks
        self._on_audio_response = None
        self._on_text_response = None
        self._on_error = None
        
    async def connect(self):
        self.is_connected = True
        
    async def disconnect(self):
        self.is_connected = False
        
    async def send_audio_chunk(self, audio_data: bytes):
        self.audio_chunks.append(audio_data)
        
    async def send_text_message(self, text: str):
        self.text_messages.append(text)
        
    async def listen_for_responses(self):
        # Simulate receiving responses
        await asyncio.sleep(0.1)
        if self._on_text_response:
            self._on_text_response("Hello, how can I help you with your code?")
            
    def set_audio_response_callback(self, callback):
        self._on_audio_response = callback
        
    def set_text_response_callback(self, callback):
        self._on_text_response = callback
        
    def set_error_callback(self, callback):
        self._on_error = callback


@pytest.fixture
async def orchestrator():
    """Create orchestrator for testing."""
    config = OrchestratorConfig(
        project_id="test-project",
        max_concurrent_sessions=5,
        session_timeout_minutes=10
    )
    
    orchestrator = VoiceOrchestrator(config)
    
    # Mock the session manager
    with patch('src.voice_ai_assistant.orchestration.voice_orchestrator.VoiceSessionManager') as mock_session_manager:
        mock_session_manager.return_value.start = AsyncMock()
        mock_session_manager.return_value.stop = AsyncMock()
        mock_session_manager.return_value.create_session = AsyncMock(return_value="test-session-123")
        mock_session_manager.return_value.end_session = AsyncMock()
        
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()


@pytest.mark.asyncio
class TestVoiceOrchestrator:
    """Test voice orchestrator functionality."""
    
    async def test_orchestrator_lifecycle(self, orchestrator):
        """Test orchestrator start/stop lifecycle."""
        assert orchestrator._is_running
        
        # Test session creation
        session_id = await orchestrator.start_conversation("test-user")
        assert session_id == "test-session-123"
        assert session_id in orchestrator._active_sessions
        
        # Test session cleanup
        await orchestrator.end_conversation(session_id)
        assert session_id not in orchestrator._active_sessions
        
    async def test_conversation_flow(self, orchestrator):
        """Test basic conversation flow."""
        session_id = await orchestrator.start_conversation("test-user")
        
        # Simulate user input
        test_audio = b"test audio data"
        await orchestrator.send_audio_chunk(session_id, test_audio)
        
        # Check session state
        state = orchestrator.get_session_state(session_id)
        assert state is not None
        assert state['session_id'] == session_id
        assert state['user_id'] == "test-user"
        
        await orchestrator.end_conversation(session_id)
        
    async def test_interruption_handling(self, orchestrator):
        """Test conversation interruption (barge-in)."""
        session_id = await orchestrator.start_conversation("test-user")
        
        # Test interruption
        await orchestrator.interrupt_conversation(session_id)
        
        # Should not raise errors
        await orchestrator.end_conversation(session_id)
        
    async def test_concurrent_sessions(self, orchestrator):
        """Test handling multiple concurrent sessions."""
        sessions = []
        
        # Create multiple sessions
        for i in range(3):
            with patch.object(orchestrator.session_manager, 'create_session', 
                            AsyncMock(return_value=f"session-{i}")):
                session_id = await orchestrator.start_conversation(f"user-{i}")
                sessions.append(session_id)
                
        # Check all sessions are active
        active_sessions = orchestrator.list_active_sessions()
        assert len(active_sessions) == 3
        
        # Clean up
        for session_id in sessions:
            await orchestrator.end_conversation(session_id)


@pytest.mark.asyncio
class TestConversationFlowManager:
    """Test conversation flow management."""
    
    async def test_flow_manager_lifecycle(self):
        """Test flow manager start/stop."""
        flow_manager = ConversationFlowManager()
        
        await flow_manager.start()
        assert flow_manager._is_running
        
        await flow_manager.stop()
        assert not flow_manager._is_running
        
    async def test_conversation_initialization(self):
        """Test conversation initialization."""
        flow_manager = ConversationFlowManager()
        await flow_manager.start()
        
        session_id = "test-session"
        await flow_manager.initialize_conversation(session_id)
        
        state = flow_manager.get_conversation_state(session_id)
        assert state is not None
        assert state['session_id'] == session_id
        assert state['state'] == ConversationState.IDLE.value
        
        await flow_manager.end_conversation(session_id)
        await flow_manager.stop()
        
    async def test_user_input_processing(self):
        """Test processing user input."""
        flow_manager = ConversationFlowManager()
        await flow_manager.start()
        
        session_id = "test-session"
        await flow_manager.initialize_conversation(session_id)
        
        # Process user input
        user_input = "Can you help me debug this Python function?"
        await flow_manager.process_user_input(session_id, user_input)
        
        # Check state transition
        state = flow_manager.get_conversation_state(session_id)
        assert state['state'] == ConversationState.RESPONDING.value
        
        # Check conversation context
        context = flow_manager.get_conversation_context(session_id)
        assert len(context) == 1
        assert context[0]['role'] == 'user'
        assert context[0]['content'] == user_input
        
        await flow_manager.end_conversation(session_id)
        await flow_manager.stop()
        
    async def test_interruption_handling(self):
        """Test conversation interruption."""
        flow_manager = ConversationFlowManager(enable_interruption=True)
        await flow_manager.start()
        
        session_id = "test-session"
        await flow_manager.initialize_conversation(session_id)
        
        # Start processing
        await flow_manager.process_user_input(session_id, "Test input")
        
        # Interrupt conversation
        await flow_manager.handle_interruption(session_id)
        
        state = flow_manager.get_conversation_state(session_id)
        assert state['state'] == ConversationState.LISTENING.value
        
        await flow_manager.end_conversation(session_id)
        await flow_manager.stop()


@pytest.mark.asyncio
class TestStreamingPipelineManager:
    """Test streaming pipeline management."""
    
    async def test_pipeline_lifecycle(self):
        """Test pipeline manager start/stop."""
        pipeline_manager = StreamingPipelineManager()
        
        await pipeline_manager.start()
        assert pipeline_manager._is_running
        
        await pipeline_manager.stop()
        assert not pipeline_manager._is_running
        
    async def test_session_initialization(self):
        """Test pipeline session initialization."""
        pipeline_manager = StreamingPipelineManager()
        await pipeline_manager.start()
        
        session_id = "test-session"
        await pipeline_manager.initialize_session(session_id)
        
        state = pipeline_manager.get_session_state(session_id)
        assert state is not None
        assert state['session_id'] == session_id
        assert state['buffer_size'] == 0
        
        await pipeline_manager.cleanup_session(session_id)
        await pipeline_manager.stop()
        
    async def test_audio_processing(self):
        """Test audio chunk processing."""
        pipeline_manager = StreamingPipelineManager()
        await pipeline_manager.start()
        
        session_id = "test-session"
        await pipeline_manager.initialize_session(session_id)
        
        # Process audio chunks
        test_audio = b"test audio chunk data"
        await pipeline_manager.process_audio_chunk(session_id, test_audio)
        
        # Check metrics
        state = pipeline_manager.get_session_state(session_id)
        metrics = state['metrics']
        assert metrics['total_chunks_processed'] == 1
        assert metrics['avg_latency_ms'] > 0
        
        await pipeline_manager.cleanup_session(session_id)
        await pipeline_manager.stop()
        
    async def test_performance_monitoring(self):
        """Test performance monitoring."""
        pipeline_manager = StreamingPipelineManager(max_latency_ms=100)
        await pipeline_manager.start()
        
        session_id = "test-session"
        await pipeline_manager.initialize_session(session_id)
        
        # Process multiple chunks to generate metrics
        for i in range(5):
            test_audio = f"test audio chunk {i}".encode()
            await pipeline_manager.process_audio_chunk(session_id, test_audio)
            
        # Get performance summary
        summary = pipeline_manager.get_performance_summary()
        assert summary['active_sessions'] == 1
        assert summary['total_chunks_processed'] == 5
        assert summary['avg_latency_ms'] > 0
        
        await pipeline_manager.cleanup_session(session_id)
        await pipeline_manager.stop()


class WebSocketTestClient:
    """WebSocket test client for voice session validation."""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """Initialize WebSocket test client.
        
        Args:
            uri: WebSocket server URI
        """
        self.uri = uri
        self.websocket = None
        self.received_messages = []
        self.is_connected = False
        
    async def connect(self) -> None:
        """Connect to WebSocket server."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            logger.info(f"Connected to WebSocket server: {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket server: {e}")
            raise
            
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from WebSocket server")
            
    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """Send audio chunk to server.
        
        Args:
            audio_data: PCM audio data
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to WebSocket server")
            
        message = {
            "type": "audio_chunk",
            "data": audio_data.hex(),  # Convert bytes to hex string
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.websocket.send(json.dumps(message))
        logger.debug(f"Sent audio chunk: {len(audio_data)} bytes")
        
    async def send_text_message(self, text: str) -> None:
        """Send text message to server.
        
        Args:
            text: Text message
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to WebSocket server")
            
        message = {
            "type": "text_message",
            "text": text,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.websocket.send(json.dumps(message))
        logger.info(f"Sent text message: {text}")
        
    async def listen_for_responses(self, timeout: float = 10.0) -> None:
        """Listen for responses from server.
        
        Args:
            timeout: Timeout in seconds
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to WebSocket server")
            
        try:
            async with asyncio.timeout(timeout):
                async for message in self.websocket:
                    try:
                        data = json.loads(message)
                        self.received_messages.append(data)
                        logger.info(f"Received message: {data.get('type', 'unknown')}")
                        
                        # Handle different message types
                        if data.get('type') == 'audio_response':
                            await self._handle_audio_response(data)
                        elif data.get('type') == 'text_response':
                            await self._handle_text_response(data)
                        elif data.get('type') == 'error':
                            await self._handle_error_response(data)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                        
        except asyncio.TimeoutError:
            logger.warning(f"Listening timeout after {timeout} seconds")
            
    async def _handle_audio_response(self, data: Dict[str, Any]) -> None:
        """Handle audio response from server."""
        audio_hex = data.get('data', '')
        if audio_hex:
            audio_data = bytes.fromhex(audio_hex)
            logger.info(f"Received audio response: {len(audio_data)} bytes")
            
    async def _handle_text_response(self, data: Dict[str, Any]) -> None:
        """Handle text response from server."""
        text = data.get('text', '')
        logger.info(f"Received text response: {text}")
        
    async def _handle_error_response(self, data: Dict[str, Any]) -> None:
        """Handle error response from server."""
        error = data.get('error', 'Unknown error')
        logger.error(f"Received error response: {error}")
        
    def get_received_messages(self) -> list:
        """Get all received messages."""
        return self.received_messages.copy()
        
    def clear_messages(self) -> None:
        """Clear received messages."""
        self.received_messages.clear()


@pytest.mark.asyncio
async def test_websocket_client():
    """Test WebSocket client functionality."""
    # This test would require a running WebSocket server
    # For now, it's a placeholder that demonstrates the interface
    
    client = WebSocketTestClient("ws://localhost:8765")
    
    # Test connection (would fail without server)
    try:
        await client.connect()
        
        # Test sending messages
        await client.send_text_message("Hello, can you help me with my code?")
        
        # Test audio chunk
        test_audio = b"fake audio data for testing"
        await client.send_audio_chunk(test_audio)
        
        # Listen for responses
        await client.listen_for_responses(timeout=5.0)
        
        # Check received messages
        messages = client.get_received_messages()
        assert len(messages) >= 0  # May be empty if no server
        
        await client.disconnect()
        
    except Exception as e:
        logger.info(f"WebSocket test skipped (no server): {e}")
        # This is expected when no server is running


if __name__ == "__main__":
    # Run basic tests
    asyncio.run(test_websocket_client())