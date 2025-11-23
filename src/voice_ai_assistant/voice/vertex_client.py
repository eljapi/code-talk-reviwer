"""Google Vertex AI Live API client for bidirectional voice streaming."""

import asyncio
import json
import logging
import os
from typing import AsyncGenerator, Dict, Any, Optional, Callable, List
import uuid

import websockets
from google.auth.transport.requests import Request
from google.cloud import aiplatform

from .auth import VertexAuthManager
from .audio_stream import AudioStreamManager, AudioConfig

logger = logging.getLogger(__name__)


class VertexLiveAPIError(Exception):
    """Exception raised for Vertex AI Live API errors."""
    pass


class VertexLiveClient:
    """Client for Google Vertex AI Live API bidirectional streaming."""

    def __init__(self,
                 project_id: Optional[str] = None,
                 region: str = "us-central1",
                 model: str = "gemini-2.5-flash-native-audio-preview-09-2025",
                 auth_manager: Optional[VertexAuthManager] = None,
                 tools: Optional[List[Dict[str, Any]]] = None):
        """Initialize Vertex AI Live API client.

        Args:
            project_id: Google Cloud project ID
            region: Google Cloud region
            model: Gemini model to use for Live API
            auth_manager: Authentication manager instance
            tools: List of tool declarations for function calling
        """
        self.auth_manager = auth_manager or VertexAuthManager(project_id)
        self.project_id = self.auth_manager.get_project_id()
        self.region = region
        self.model = model
        self.tools = tools or []
        self.audio_manager = AudioStreamManager()

        # WebSocket connection
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._session_id: Optional[str] = None
        self._is_connected = False

        # Callbacks
        self._on_audio_response: Optional[Callable[[bytes], None]] = None
        self._on_text_response: Optional[Callable[[str], None]] = None
        self._on_tool_call: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None
        
    async def connect(self) -> None:
        """Establish connection to Vertex AI Live API.

        Raises:
            VertexLiveAPIError: If connection fails
        """
        try:
            # Generate session ID
            self._session_id = str(uuid.uuid4())

            # Get API key from environment
            api_key = os.getenv("GOOGLE_AI_API_KEY")
            if not api_key:
                raise VertexLiveAPIError("GOOGLE_AI_API_KEY environment variable not set")

            # Construct WebSocket URL for Generative Language Live API
            # Use API key for authentication (Google AI Studio endpoint)
            base_url = "wss://generativelanguage.googleapis.com"
            endpoint = "/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            url = f"{base_url}{endpoint}?key={api_key}"

            logger.info(f"Connecting to Vertex AI Live API: {base_url}{endpoint}")

            # Connect to WebSocket (no extra headers needed with API key in URL)
            self._websocket = await websockets.connect(
                url,
                ping_interval=30,
                ping_timeout=10
            )

            # Send initial configuration
            await self._send_initial_config()

            self._is_connected = True
            logger.info(f"Connected to Vertex AI Live API with session: {self._session_id}")

        except Exception as e:
            logger.error(f"Failed to connect to Vertex AI Live API: {e}")
            raise VertexLiveAPIError(f"Connection failed: {e}")
            
    async def disconnect(self) -> None:
        """Disconnect from Vertex AI Live API."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
            
        self._is_connected = False
        self._session_id = None
        logger.info("Disconnected from Vertex AI Live API")
        
    async def _send_initial_config(self) -> None:
        """Send initial configuration to the Live API."""
        # Setup with AUDIO response configuration (camelCase fields required!)
        config = {
            "model": "models/gemini-2.5-flash-native-audio-preview-09-2025",
            "generationConfig": {
                "responseModalities": "audio",  # Must be camelCase!
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": "Puck"
                        }
                    }
                }
            }
        }

        # Add tools if provided
        if self.tools:
            config["tools"] = self.tools
            logger.info(f"Registered {len(self.tools)} tools with Gemini Live API")

        message = {
            "setup": config
        }

        await self._websocket.send(json.dumps(message))
        logger.debug("Sent initial configuration")

        # Wait for setupComplete response
        try:
            async with asyncio.timeout(5):
                async for response in self._websocket:
                    data = json.loads(response)
                    if "setupComplete" in data:
                        logger.info("Setup completed successfully")
                        return
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for setupComplete response")
        
    async def send_audio_chunk(self, audio_data: bytes) -> None:
        """Send audio chunk to the Live API.
        
        Args:
            audio_data: PCM audio data (16-bit, 16kHz, mono)
            
        Raises:
            VertexLiveAPIError: If not connected or send fails
        """
        if not self._is_connected or not self._websocket:
            raise VertexLiveAPIError("Not connected to Live API")
            
        try:
            # Convert audio to base64 for JSON transmission
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            message = {
                "realtime_input": {
                    "media_chunks": [{
                        "mime_type": "audio/pcm",
                        "data": audio_b64
                    }]
                }
            }
            
            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent audio chunk: {len(audio_data)} bytes")
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}")
            raise VertexLiveAPIError(f"Send failed: {e}")
            
    async def send_text_message(self, text: str) -> None:
        """Send text message to the Live API.

        Args:
            text: Text message to send

        Raises:
            VertexLiveAPIError: If not connected or send fails
        """
        if not self._is_connected or not self._websocket:
            raise VertexLiveAPIError("Not connected to Live API")

        try:
            message = {
                "realtime_input": {
                    "text": text
                }
            }

            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent text message: {text}")

        except Exception as e:
            logger.error(f"Failed to send text message: {e}")
            raise VertexLiveAPIError(f"Send failed: {e}")

    async def send_tool_response(self, function_responses: List[Dict[str, Any]]) -> None:
        """Send tool/function call responses back to the Live API.

        Args:
            function_responses: List of function response objects, each containing:
                - id: The function call ID from the toolCall message
                - name: The function name
                - response: The function result (dict or any JSON-serializable value)

        Raises:
            VertexLiveAPIError: If not connected or send fails
        """
        if not self._is_connected or not self._websocket:
            raise VertexLiveAPIError("Not connected to Live API")

        try:
            message = {
                "tool_response": {
                    "function_responses": function_responses
                }
            }

            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent tool responses: {len(function_responses)} function(s)")

        except Exception as e:
            logger.error(f"Failed to send tool response: {e}")
            raise VertexLiveAPIError(f"Tool response send failed: {e}")

    async def listen_for_responses(self) -> None:
        """Listen for responses from the Live API.

        Raises:
            VertexLiveAPIError: If not connected
        """
        if not self._is_connected or not self._websocket:
            raise VertexLiveAPIError("Not connected to Live API")

        logger.info("Starting to listen for responses")

        try:
            async for message in self._websocket:
                await self._handle_response(message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self._is_connected = False

    async def _handle_response(self, message: str) -> None:
        """Handle response from Vertex AI Live API.

        Args:
            message: JSON message from the API
        """
        try:
            data = json.loads(message)
            logger.debug(f"Received message: {list(data.keys())}")

            # Handle toolCall - Gemini requests function execution
            if "toolCall" in data:
                tool_call = data["toolCall"]
                function_calls = tool_call.get("function_calls", [])

                if function_calls:
                    logger.info(f"Received tool call request: {len(function_calls)} function(s)")

                    # Call tool callback
                    if self._on_tool_call:
                        self._on_tool_call(function_calls)

            # Handle modelTurn with audio response
            elif "serverContent" in data:
                server_content = data["serverContent"]

                # Check for modelTurn with audio parts
                if "modelTurn" in server_content:
                    model_turn = server_content["modelTurn"]

                    if "parts" in model_turn:
                        for part in model_turn["parts"]:
                            # Handle audio response
                            if "inlineData" in part:
                                inline_data = part["inlineData"]
                                if inline_data.get("mimeType", "").startswith("audio/"):
                                    # Decode base64 audio data
                                    import base64
                                    audio_data = base64.b64decode(inline_data["data"])

                                    logger.debug(f"Received audio response: {len(audio_data)} bytes")

                                    # Call audio callback
                                    if self._on_audio_response:
                                        self._on_audio_response(audio_data)

                            # Handle text response
                            elif "text" in part:
                                text_data = part["text"]
                                logger.debug(f"Received text response: {text_data}")

                                # Call text callback
                                if self._on_text_response:
                                    self._on_text_response(text_data)

            # Handle turnComplete
            elif "turnComplete" in data:
                logger.debug("Turn complete")

            # Handle setupComplete
            elif "setupComplete" in data:
                logger.debug("Setup complete")

            # Handle toolCallCancellation
            elif "toolCallCancellation" in data:
                cancellation = data["toolCallCancellation"]
                cancelled_ids = cancellation.get("ids", [])
                logger.info(f"Tool calls cancelled: {cancelled_ids}")

        except Exception as e:
            logger.error(f"Error handling response: {e}")
            if self._on_error:
                self._on_error(e)

    def set_audio_response_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for audio responses.

        Args:
            callback: Function to call with audio data
        """
        self._on_audio_response = callback

    def set_text_response_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for text responses.

        Args:
            callback: Function to call with text data
        """
        self._on_text_response = callback

    def set_tool_call_callback(self, callback: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Set callback for tool/function call requests.

        Args:
            callback: Function to call with list of function call objects
        """
        self._on_tool_call = callback

    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for errors.

        Args:
            callback: Function to call with exceptions
        """
        self._on_error = callback
        
    @property
    def is_connected(self) -> bool:
        """Check if client is connected to Live API."""
        return self._is_connected
        
    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self._session_id
        
    async def stream_audio_file(self, file_path: str) -> None:
        """Stream an audio file to the Live API.
        
        Args:
            file_path: Path to the audio file
            
        Raises:
            VertexLiveAPIError: If not connected or streaming fails
        """
        if not self._is_connected:
            raise VertexLiveAPIError("Not connected to Live API")
            
        logger.info(f"Streaming audio file: {file_path}")
        
        try:
            async for audio_chunk in self.audio_manager.stream_audio_file(file_path):
                await self.send_audio_chunk(audio_chunk)
                
        except Exception as e:
            logger.error(f"Failed to stream audio file: {e}")
            raise VertexLiveAPIError(f"Audio streaming failed: {e}")
            
    async def reconnect(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """Attempt to reconnect to the Live API.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            True if reconnection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{max_retries}")
                await self.disconnect()
                await asyncio.sleep(retry_delay)
                await self.connect()
                return True
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    
        logger.error("All reconnection attempts failed")
        return False