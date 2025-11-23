"""Audio streaming utilities for Vertex AI Live API."""

import asyncio
import logging
import struct
import wave
from typing import AsyncGenerator, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioConfig:
    """Audio configuration constants."""
    
    SAMPLE_RATE = 16000  # 16 kHz as required by Vertex AI Live API
    CHANNELS = 1  # Mono audio
    SAMPLE_WIDTH = 2  # 16-bit PCM
    CHUNK_SIZE = 1024  # Audio chunk size in samples
    BYTES_PER_SAMPLE = 2  # 16-bit = 2 bytes per sample


class AudioStreamManager:
    """Manages PCM audio streaming for Vertex AI Live API."""
    
    def __init__(self, sample_rate: int = AudioConfig.SAMPLE_RATE, 
                 chunk_size: int = AudioConfig.CHUNK_SIZE):
        """Initialize audio stream manager.
        
        Args:
            sample_rate: Audio sample rate in Hz
            chunk_size: Size of audio chunks in samples
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.bytes_per_chunk = chunk_size * AudioConfig.BYTES_PER_SAMPLE
        self._is_streaming = False
        
    async def stream_audio_file(self, file_path: Union[str, Path]) -> AsyncGenerator[bytes, None]:
        """Stream audio data from a WAV file.
        
        Args:
            file_path: Path to the audio file
            
        Yields:
            Audio data chunks as bytes
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio format is incompatible
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
            
        logger.info(f"Streaming audio file: {file_path}")
        
        try:
            with wave.open(str(file_path), 'rb') as wav_file:
                # Validate audio format
                if wav_file.getnchannels() != AudioConfig.CHANNELS:
                    raise ValueError(f"Expected {AudioConfig.CHANNELS} channel(s), got {wav_file.getnchannels()}")
                if wav_file.getsampwidth() != AudioConfig.SAMPLE_WIDTH:
                    raise ValueError(f"Expected {AudioConfig.SAMPLE_WIDTH} bytes per sample, got {wav_file.getsampwidth()}")
                if wav_file.getframerate() != self.sample_rate:
                    logger.warning(f"Sample rate mismatch: expected {self.sample_rate}, got {wav_file.getframerate()}")
                
                self._is_streaming = True
                frames_read = 0
                total_frames = wav_file.getnframes()
                
                while self._is_streaming and frames_read < total_frames:
                    # Read chunk of audio data
                    audio_data = wav_file.readframes(self.chunk_size)
                    if not audio_data:
                        break
                        
                    frames_read += len(audio_data) // AudioConfig.BYTES_PER_SAMPLE
                    yield audio_data
                    
                    # Small delay to simulate real-time streaming
                    await asyncio.sleep(self.chunk_size / self.sample_rate)
                    
                logger.info(f"Finished streaming {frames_read} frames from {file_path}")
                
        except wave.Error as e:
            raise ValueError(f"Invalid WAV file format: {e}")
            
    async def stream_microphone(self) -> AsyncGenerator[bytes, None]:
        """Stream audio data from microphone (placeholder implementation).
        
        Note: This is a placeholder. Real implementation would use pyaudio
        or similar library to capture microphone input.
        
        Yields:
            Audio data chunks as bytes
        """
        logger.warning("Microphone streaming not implemented - using silence")
        
        self._is_streaming = True
        while self._is_streaming:
            # Generate silence (zeros) as placeholder
            silence = b'\x00' * self.bytes_per_chunk
            yield silence
            await asyncio.sleep(self.chunk_size / self.sample_rate)
            
    def stop_streaming(self) -> None:
        """Stop the current audio stream."""
        logger.info("Stopping audio stream")
        self._is_streaming = False
        
    def create_pcm_audio_chunk(self, samples: list[int]) -> bytes:
        """Create PCM audio chunk from sample values.
        
        Args:
            samples: List of 16-bit integer samples
            
        Returns:
            PCM audio data as bytes
        """
        return struct.pack(f'<{len(samples)}h', *samples)
        
    def parse_pcm_audio_chunk(self, audio_data: bytes) -> list[int]:
        """Parse PCM audio chunk into sample values.
        
        Args:
            audio_data: PCM audio data as bytes
            
        Returns:
            List of 16-bit integer samples
        """
        num_samples = len(audio_data) // AudioConfig.BYTES_PER_SAMPLE
        return list(struct.unpack(f'<{num_samples}h', audio_data))
        
    def save_audio_to_file(self, audio_chunks: list[bytes], output_path: Union[str, Path]) -> None:
        """Save audio chunks to a WAV file.
        
        Args:
            audio_chunks: List of PCM audio chunks
            output_path: Path to save the audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(AudioConfig.CHANNELS)
            wav_file.setsampwidth(AudioConfig.SAMPLE_WIDTH)
            wav_file.setframerate(self.sample_rate)
            
            for chunk in audio_chunks:
                wav_file.writeframes(chunk)
                
        logger.info(f"Saved audio to {output_path}")


def create_test_audio_file(output_path: Union[str, Path], duration_seconds: float = 2.0) -> None:
    """Create a test audio file with a simple tone.
    
    Args:
        output_path: Path to save the test audio file
        duration_seconds: Duration of the audio in seconds
    """
    import math
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    sample_rate = AudioConfig.SAMPLE_RATE
    frequency = 440.0  # A4 note
    amplitude = 16384  # Half of max 16-bit value
    
    num_samples = int(sample_rate * duration_seconds)
    samples = []
    
    for i in range(num_samples):
        # Generate sine wave
        t = i / sample_rate
        sample = int(amplitude * math.sin(2 * math.pi * frequency * t))
        samples.append(sample)
    
    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(AudioConfig.CHANNELS)
        wav_file.setsampwidth(AudioConfig.SAMPLE_WIDTH)
        wav_file.setframerate(sample_rate)
        
        # Convert samples to bytes and write
        audio_data = struct.pack(f'<{len(samples)}h', *samples)
        wav_file.writeframes(audio_data)
    
    logger.info(f"Created test audio file: {output_path}")