"""Configuration settings for the voice AI assistant."""

import os
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Cloud Configuration
    google_application_credentials: Optional[str] = Field(
        default=None, env="GOOGLE_APPLICATION_CREDENTIALS"
    )
    google_cloud_project: str = Field(
        default="powerful-outlet-477200-f0", env="GOOGLE_CLOUD_PROJECT"
    )
    google_cloud_region: str = Field(default="us-central1", env="GOOGLE_CLOUD_REGION")
    
    # Vertex AI Configuration
    vertex_ai_model: str = Field(default="gemini-2.5-flash-native-audio-preview-09-2025", env="VERTEX_AI_MODEL")
    vertex_ai_region: str = Field(default="us-central1", env="VERTEX_AI_REGION")
    vertex_ai_voice: str = Field(default="Puck", env="VERTEX_AI_VOICE")
    
    # Voice Assistant Configuration
    max_concurrent_sessions: int = Field(default=10, env="MAX_CONCURRENT_SESSIONS")
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    max_response_latency_ms: int = Field(default=300, env="MAX_RESPONSE_LATENCY_MS")

    # Claude API Configuration
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")

    # Strands Configuration
    strands_model: str = Field(
        default="claude-sonnet-4-5-20250929", env="STRANDS_MODEL"
    )
    strands_max_turns: int = Field(default=10, env="STRANDS_MAX_TURNS")

    # Claude Code SDK Configuration
    claude_code_permission_mode: Literal["plan", "acceptEdits", "auto"] = Field(
        default="plan", env="CLAUDE_CODE_PERMISSION_MODE"
    )
    claude_code_repository_path: str = Field(default="./", env="CLAUDE_CODE_REPOSITORY_PATH")

    # Application Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")

    # Audio Configuration
    audio_sample_rate: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")
    audio_chunk_size: int = Field(default=1024, env="AUDIO_CHUNK_SIZE")

    # Server Configuration
    host: str = Field(default="localhost", env="HOST")
    port: int = Field(default=8000, env="PORT")

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()