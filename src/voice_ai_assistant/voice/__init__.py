"""Voice interface layer for handling audio streaming and Vertex AI Live API integration."""

from .auth import VertexAuthManager
from .audio_stream import AudioStreamManager, AudioConfig, create_test_audio_file
from .vertex_client import VertexLiveClient, VertexLiveAPIError
from .session_manager import VoiceSessionManager, SessionState

__all__ = [
    "VertexAuthManager",
    "AudioStreamManager", 
    "AudioConfig",
    "create_test_audio_file",
    "VertexLiveClient",
    "VertexLiveAPIError", 
    "VoiceSessionManager",
    "SessionState"
]