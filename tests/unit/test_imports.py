"""Test that all modules can be imported correctly."""

import pytest


def test_import_main_package():
    """Test importing the main package."""
    import voice_ai_assistant
    assert voice_ai_assistant.__version__ == "0.1.0"


def test_import_submodules():
    """Test importing all submodules."""
    import voice_ai_assistant.voice
    import voice_ai_assistant.agent
    import voice_ai_assistant.code
    import voice_ai_assistant.config


def test_import_settings():
    """Test importing settings."""
    from voice_ai_assistant.config.settings import settings, Settings
    
    assert isinstance(settings, Settings)
    assert settings.strands_model == "claude-haiku-4-5-20251001"