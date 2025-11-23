"""Configuration for voice orchestrator."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OrchestratorConfig:
    """Configuration for voice orchestrator."""

    # Vertex AI settings
    project_id: Optional[str] = None
    region: str = "us-central1"
    model: str = "gemini-2.0-flash-exp"

    # Session settings
    session_timeout_minutes: int = 30
    max_concurrent_sessions: int = 10

    # Performance settings
    max_response_latency_ms: int = 300
    audio_chunk_size: int = 1024

    # Agent settings
    agent_model: str = "claude-sonnet-4-5-20250929"
    enable_code_tools: bool = True

    # Safety settings
    max_conversation_turns: int = 50
    enable_interruption: bool = True

    # Audio I/O settings
    hardware_sample_rate: int = 48000  # Hardware interface sample rate (e.g., Scarlett)
    vertex_input_rate: int = 16000     # Vertex AI expected input rate
    vertex_output_rate: int = 24000    # Vertex AI output rate
    input_device: Optional[int] = None  # Sounddevice input device index
    output_device: Optional[int] = None # Sounddevice output device index
