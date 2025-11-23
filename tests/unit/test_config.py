"""Test configuration module."""

import pytest

from voice_ai_assistant.config.settings import Settings


def test_settings_default_values():
    """Test that settings have correct default values."""
    settings = Settings()
    
    assert settings.google_cloud_region == "us-central1"
    assert settings.strands_model == "claude-haiku-4-5-20251001"
    assert settings.strands_max_turns == 10
    assert settings.claude_code_permission_mode == "plan"
    assert settings.claude_code_repository_path == "./"
    assert settings.log_level == "INFO"
    assert settings.debug is False
    assert settings.audio_sample_rate == 16000
    assert settings.audio_chunk_size == 1024
    assert settings.host == "localhost"
    assert settings.port == 8000


def test_settings_env_override(monkeypatch):
    """Test that environment variables override default values."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("CLAUDE_CODE_PERMISSION_MODE", "auto")
    
    settings = Settings()
    
    assert settings.log_level == "DEBUG"
    assert settings.port == 9000
    assert settings.claude_code_permission_mode == "auto"