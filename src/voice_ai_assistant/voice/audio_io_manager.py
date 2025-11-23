"""Audio I/O Manager for voice interface.

Handles microphone input and speaker output with sample rate conversion.
Supports multi-rate audio system:
- Hardware (Scarlett): 48kHz
- Vertex AI Input: 16kHz
- Vertex AI Output: 24kHz
"""

import asyncio
import logging
import threading
from typing import Optional, Callable
import queue

try:
    import sounddevice as sd
    import numpy as np
    from scipy import signal
except ImportError as e:
    raise ImportError(
        "Audio dependencies not installed. Please run: "
        "pip install sounddevice numpy scipy"
    ) from e

logger = logging.getLogger(__name__)


class AudioIOManager:
    """Manages audio input/output with sample rate conversion."""

    def __init__(
        self,
        hardware_sample_rate: int = 48000,
        vertex_input_rate: int = 16000,
        vertex_output_rate: int = 24000,
        channels: int = 1,
        block_size: int = 1024,
        dtype: str = 'int16',
        input_device: Optional[int] = None,
        output_device: Optional[int] = None,
    ):
        """Initialize audio I/O manager.

        Args:
            hardware_sample_rate: Hardware audio interface sample rate (e.g., 48000 for Scarlett)
            vertex_input_rate: Sample rate Vertex AI expects for input (16000)
            vertex_output_rate: Sample rate Vertex AI sends for output (24000)
            channels: Number of audio channels (1 for mono)
            block_size: Audio block size for streaming
            dtype: Audio data type
            input_device: Sounddevice input device index (None for default)
            output_device: Sounddevice output device index (None for default)
        """
        self.hardware_sample_rate = hardware_sample_rate
        self.vertex_input_rate = vertex_input_rate
        self.vertex_output_rate = vertex_output_rate
        self.channels = channels
        self.block_size = block_size
        self.dtype = dtype
        self.input_device = input_device
        self.output_device = output_device

        # Audio capture
        self._input_stream: Optional[sd.InputStream] = None
        self._audio_callback: Optional[Callable[[bytes], None]] = None
        self._is_capturing = False
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Audio playback
        self._audio_buffer = []  # Accumulate audio chunks for current turn
        self._is_playing = False  # Flag to prevent overlapping playback
        self._playback_thread: Optional[threading.Thread] = None

        logger.info(
            f"AudioIOManager initialized: "
            f"Hardware={hardware_sample_rate}Hz, "
            f"Vertex Input={vertex_input_rate}Hz, "
            f"Vertex Output={vertex_output_rate}Hz"
        )

    def start_capture(
        self,
        audio_callback: Callable[[bytes], None],
        event_loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Start capturing audio from microphone.

        Args:
            audio_callback: Async callback to handle captured audio chunks (resampled to vertex_input_rate)
            event_loop: Event loop for async callback (defaults to current running loop)
        """
        if self._is_capturing:
            logger.warning("Audio capture already running")
            return

        self._audio_callback = audio_callback
        self._event_loop = event_loop or asyncio.get_running_loop()
        self._is_capturing = True

        logger.info(f"Starting audio capture from device {self.input_device or 'default'}")

        self._input_stream = sd.InputStream(
            device=self.input_device,
            samplerate=self.hardware_sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.block_size,
            callback=self._audio_input_callback
        )
        self._input_stream.start()

        logger.info("Audio capture started")

    def stop_capture(self) -> None:
        """Stop capturing audio from microphone."""
        if not self._is_capturing:
            return

        self._is_capturing = False

        if self._input_stream:
            self._input_stream.stop()
            self._input_stream.close()
            self._input_stream = None

        logger.info("Audio capture stopped")

    def play_audio(self, data: bytes) -> None:
        """Play back received audio with resampling and buffering.

        Args:
            data: Audio data from Vertex AI (PCM int16 at vertex_output_rate)
        """
        try:
            # Convert bytes to numpy array (Vertex AI sends at 24kHz)
            audio_np = np.frombuffer(data, dtype=np.int16)

            # Resample from vertex_output_rate to hardware_sample_rate
            num_samples_output = int(
                len(audio_np) * self.hardware_sample_rate / self.vertex_output_rate
            )
            resampled = signal.resample(audio_np, num_samples_output)

            # Convert back to int16
            resampled_int16 = resampled.astype(np.int16)

            logger.debug(
                f"Resampled audio: {len(audio_np)} @ {self.vertex_output_rate}Hz -> "
                f"{len(resampled_int16)} @ {self.hardware_sample_rate}Hz samples"
            )

            # Accumulate chunks in buffer
            self._audio_buffer.append(resampled_int16)

            # If we're not currently playing, start playback in a thread
            if not self._is_playing:
                self._is_playing = True
                self._playback_thread = threading.Thread(
                    target=self._play_buffered_audio,
                    daemon=True
                )
                self._playback_thread.start()

        except Exception as e:
            logger.error(f"Error processing audio for playback: {e}", exc_info=True)

    def stop_playback(self) -> None:
        """Stop audio playback and clear buffer."""
        self._is_playing = False
        self._audio_buffer = []

        # Wait for playback thread to finish
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)

        logger.info("Audio playback stopped")

    def _play_buffered_audio(self) -> None:
        """Play all accumulated audio chunks in a separate thread.

        This runs in a background thread to avoid blocking the async event loop.
        It continuously plays accumulated chunks until playback is stopped.
        """
        try:
            while self._is_playing or len(self._audio_buffer) > 0:
                if len(self._audio_buffer) > 0:
                    # Concatenate all buffered chunks
                    full_audio = np.concatenate(self._audio_buffer)
                    duration = len(full_audio) / self.hardware_sample_rate

                    logger.info(
                        f"Playing {len(full_audio)} samples ({duration:.2f}s) "
                        f"@ {self.hardware_sample_rate}Hz"
                    )

                    # Clear buffer before playing
                    self._audio_buffer = []

                    # Play the full audio (blocking in this thread)
                    sd.play(full_audio, self.hardware_sample_rate, device=self.output_device)
                    sd.wait()  # Wait for playback to complete
                else:
                    # Small delay to avoid busy waiting
                    import time
                    time.sleep(0.01)

        except Exception as e:
            logger.error(f"Error playing buffered audio: {e}", exc_info=True)
        finally:
            self._is_playing = False

    def _audio_input_callback(self, indata, frames, time, status) -> None:
        """Callback for sounddevice input with resampling.

        This runs in a background thread managed by sounddevice.
        It resamples audio from hardware_sample_rate to vertex_input_rate
        and sends it to the async callback.

        Args:
            indata: Input audio data from sounddevice
            frames: Number of frames
            time: Timestamp info
            status: Status flags
        """
        if status:
            logger.warning(f"Audio input status: {status}")

        if not self._is_capturing or not self._audio_callback or not self._event_loop:
            return

        try:
            # Convert to numpy array for resampling
            audio_np = indata.flatten()

            # Log audio level for debugging
            audio_level = np.abs(audio_np).mean()

            # Resample from hardware_sample_rate to vertex_input_rate
            num_samples_output = int(
                len(audio_np) * self.vertex_input_rate / self.hardware_sample_rate
            )
            resampled = signal.resample(audio_np, num_samples_output)

            # Convert back to int16 and then to bytes
            resampled_int16 = resampled.astype(np.int16)
            data = resampled_int16.tobytes()

            if audio_level > 0.01:  # Only log if there's significant audio
                logger.debug(
                    f"Audio captured: {frames} frames @ {self.hardware_sample_rate}Hz -> "
                    f"{len(resampled_int16)} samples @ {self.vertex_input_rate}Hz, "
                    f"level: {audio_level:.4f}"
                )

            # Send resampled audio to async callback
            # If callback is async, schedule it on the event loop
            if asyncio.iscoroutinefunction(self._audio_callback):
                asyncio.run_coroutine_threadsafe(
                    self._audio_callback(data),
                    self._event_loop
                )
            else:
                # If callback is sync, call it directly
                self._audio_callback(data)

        except Exception as e:
            logger.error(f"Error in audio input callback: {e}", exc_info=True)

    def shutdown(self) -> None:
        """Shutdown audio I/O manager and cleanup resources."""
        logger.info("Shutting down AudioIOManager")
        self.stop_capture()
        self.stop_playback()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
