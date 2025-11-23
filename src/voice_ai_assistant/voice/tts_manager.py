"""Text-to-Speech Manager using Google Cloud TTS.

This module handles converting text to speech for system status updates
and other non-conversational feedback.
"""

import logging
import os
from typing import Optional
import asyncio

from google.cloud import texttospeech

logger = logging.getLogger(__name__)

class TTSManager:
    """Manages Text-to-Speech generation."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize TTS Manager.

        Args:
            project_id: Google Cloud project ID.
        """
        self.client = texttospeech.TextToSpeechClient()
        
        # Use a 'Journey' voice if available, otherwise fallback to standard Neural2 or WaveNet
        # Journey voices are expressive and low latency
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-D", 
            ssml_gender=texttospeech.SsmlVoiceGender.MALE
        )

        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000, # Match the output rate of the system
            speaking_rate=1.0 
        )

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize text to audio bytes.

        Args:
            text: Text to synthesize.

        Returns:
            Audio bytes (PCM) or None if failed.
        """
        if not text:
            return None

        try:
            # Run blocking API call in executor
            loop = asyncio.get_running_loop()
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=self.voice,
                    audio_config=self.audio_config
                )
            )
            
            return response.audio_content

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            return None
