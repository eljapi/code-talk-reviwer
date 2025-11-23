"""Streaming pipeline management for real-time voice processing.

Manages the streaming pipeline between voice input, agent processing,
and voice output with latency optimization and performance monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger(__name__)


@dataclass
class StreamingMetrics:
    """Metrics for streaming pipeline performance."""
    
    session_id: str
    total_chunks_processed: int = 0
    total_processing_time_ms: float = 0.0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    throughput_samples: deque = field(default_factory=lambda: deque(maxlen=50))
    error_count: int = 0
    last_activity: float = field(default_factory=time.time)
    
    def add_latency_sample(self, latency_ms: float) -> None:
        """Add a latency measurement sample."""
        self.latency_samples.append(latency_ms)
        self.total_processing_time_ms += latency_ms
        self.last_activity = time.time()
        
    def add_throughput_sample(self, chunks_per_second: float) -> None:
        """Add a throughput measurement sample."""
        self.throughput_samples.append(chunks_per_second)
        
    def get_avg_latency_ms(self) -> float:
        """Get average latency in milliseconds."""
        return statistics.mean(self.latency_samples) if self.latency_samples else 0.0
        
    def get_p95_latency_ms(self) -> float:
        """Get 95th percentile latency in milliseconds."""
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        index = int(0.95 * len(sorted_samples))
        return sorted_samples[min(index, len(sorted_samples) - 1)]
        
    def get_avg_throughput(self) -> float:
        """Get average throughput in chunks per second."""
        return statistics.mean(self.throughput_samples) if self.throughput_samples else 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'session_id': self.session_id,
            'total_chunks_processed': self.total_chunks_processed,
            'total_processing_time_ms': self.total_processing_time_ms,
            'avg_latency_ms': self.get_avg_latency_ms(),
            'p95_latency_ms': self.get_p95_latency_ms(),
            'avg_throughput_cps': self.get_avg_throughput(),
            'error_count': self.error_count,
            'uptime_seconds': time.time() - (self.last_activity - self.total_processing_time_ms / 1000)
        }


@dataclass
class PipelineBuffer:
    """Buffer for streaming audio chunks."""
    
    max_size: int = 1000
    chunks: deque = field(default_factory=deque)
    total_bytes: int = 0
    
    def add_chunk(self, chunk: bytes) -> None:
        """Add audio chunk to buffer."""
        if len(self.chunks) >= self.max_size:
            removed_chunk = self.chunks.popleft()
            self.total_bytes -= len(removed_chunk)
            
        self.chunks.append(chunk)
        self.total_bytes += len(chunk)
        
    def get_chunks(self, count: Optional[int] = None) -> List[bytes]:
        """Get chunks from buffer."""
        if count is None:
            return list(self.chunks)
        return list(self.chunks)[-count:] if count > 0 else []
        
    def clear(self) -> None:
        """Clear the buffer."""
        self.chunks.clear()
        self.total_bytes = 0


class StreamingPipelineManager:
    """Manages streaming pipeline for real-time voice processing.
    
    This class handles:
    - Audio chunk buffering and processing
    - Latency monitoring and optimization
    - Throughput measurement
    - Pipeline performance metrics
    - Stream interruption and recovery
    """
    
    def __init__(self, 
                 max_latency_ms: int = 300,
                 buffer_size: int = 1000,
                 metrics_window_size: int = 100):
        """Initialize streaming pipeline manager.
        
        Args:
            max_latency_ms: Maximum acceptable latency in milliseconds
            buffer_size: Maximum buffer size for audio chunks
            metrics_window_size: Size of metrics sampling window
        """
        self.max_latency_ms = max_latency_ms
        self.buffer_size = buffer_size
        self.metrics_window_size = metrics_window_size
        
        # Active pipeline sessions
        self._sessions: Dict[str, PipelineBuffer] = {}
        self._metrics: Dict[str, StreamingMetrics] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        
        self._is_running = False
        
        # Performance monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._performance_alerts: List[str] = []
        
        # Event callbacks
        self._on_latency_alert: Optional[Callable[[str, float], None]] = None
        self._on_throughput_alert: Optional[Callable[[str, float], None]] = None
        self._on_buffer_overflow: Optional[Callable[[str], None]] = None
        
    async def start(self) -> None:
        """Start the streaming pipeline manager."""
        if self._is_running:
            return
            
        logger.info("Starting streaming pipeline manager")
        self._is_running = True
        
        # Start performance monitoring
        self._monitor_task = asyncio.create_task(self._monitor_performance())
        
    async def stop(self) -> None:
        """Stop the streaming pipeline manager."""
        if not self._is_running:
            return
            
        logger.info("Stopping streaming pipeline manager")
        self._is_running = False
        
        # Cancel monitoring task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        # Clean up all sessions
        for session_id in list(self._sessions.keys()):
            await self.cleanup_session(session_id)
            
    async def initialize_session(self, session_id: str) -> None:
        """Initialize streaming pipeline for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._sessions:
            logger.warning(f"Pipeline session already exists: {session_id}")
            return
            
        # Create buffer and metrics
        self._sessions[session_id] = PipelineBuffer(max_size=self.buffer_size)
        self._metrics[session_id] = StreamingMetrics(session_id=session_id)
        
        logger.info(f"Initialized streaming pipeline for session: {session_id}")
        
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up streaming pipeline for a session.
        
        Args:
            session_id: Session to clean up
        """
        if session_id not in self._sessions:
            logger.warning(f"Pipeline session not found: {session_id}")
            return
            
        # Cancel processing task if exists
        if session_id in self._processing_tasks:
            task = self._processing_tasks[session_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._processing_tasks[session_id]
            
        # Clean up resources
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._metrics:
            metrics = self._metrics[session_id]
            logger.info(f"Final metrics for session {session_id}: {metrics.to_dict()}")
            del self._metrics[session_id]
            
        logger.info(f"Cleaned up streaming pipeline for session: {session_id}")
        
    async def process_audio_chunk(self, session_id: str, audio_data: bytes) -> None:
        """Process an audio chunk through the pipeline.
        
        Args:
            session_id: Session identifier
            audio_data: PCM audio data
        """
        if session_id not in self._sessions:
            logger.error(f"Pipeline session not found: {session_id}")
            return
            
        start_time = time.time()
        
        try:
            buffer = self._sessions[session_id]
            metrics = self._metrics[session_id]
            
            # Add chunk to buffer
            buffer.add_chunk(audio_data)
            
            # Process chunk (placeholder for actual processing)
            await self._process_chunk(session_id, audio_data)
            
            # Update metrics
            processing_time_ms = (time.time() - start_time) * 1000
            metrics.add_latency_sample(processing_time_ms)
            metrics.total_chunks_processed += 1
            
            # Check latency threshold
            if processing_time_ms > self.max_latency_ms:
                logger.warning(f"High latency detected for {session_id}: {processing_time_ms:.2f}ms")
                if self._on_latency_alert:
                    self._on_latency_alert(session_id, processing_time_ms)
                    
        except Exception as e:
            logger.error(f"Error processing audio chunk for {session_id}: {e}")
            if session_id in self._metrics:
                self._metrics[session_id].error_count += 1
                
    async def process_audio_response(self, session_id: str, audio_data: bytes) -> None:
        """Process audio response from agent back to voice output.
        
        Args:
            session_id: Session identifier
            audio_data: Generated audio response
        """
        if session_id not in self._sessions:
            logger.error(f"Pipeline session not found: {session_id}")
            return
            
        try:
            # Process response audio (placeholder)
            await self._process_response_audio(session_id, audio_data)
            
            logger.debug(f"Processed audio response for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error processing audio response for {session_id}: {e}")
            
    async def handle_interruption(self, session_id: str) -> None:
        """Handle pipeline interruption (barge-in).
        
        Args:
            session_id: Session being interrupted
        """
        if session_id not in self._sessions:
            logger.warning(f"Pipeline session not found for interruption: {session_id}")
            return
            
        try:
            # Cancel current processing task
            if session_id in self._processing_tasks:
                task = self._processing_tasks[session_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._processing_tasks[session_id]
                
            # Clear buffer
            buffer = self._sessions[session_id]
            buffer.clear()
            
            logger.info(f"Handled pipeline interruption for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling interruption for {session_id}: {e}")
            
    async def _process_chunk(self, session_id: str, audio_data: bytes) -> None:
        """Process individual audio chunk.

        Currently performs basic validation and logging.
        Future enhancements could include:
        - Audio preprocessing/filtering
        - Voice activity detection
        - Noise reduction

        Args:
            session_id: Session identifier
            audio_data: Audio chunk to process
        """
        # Basic validation
        if not audio_data:
            logger.warning(f"Empty audio chunk received for session {session_id}")
            return

        # Log chunk size for monitoring
        chunk_size = len(audio_data)
        logger.debug(f"Processing audio chunk for {session_id}: {chunk_size} bytes")

        # Future: Add audio preprocessing here
        # - Voice activity detection
        # - Noise reduction
        # - Echo cancellation
        
    async def _process_response_audio(self, session_id: str, audio_data: bytes) -> None:
        """Process response audio for output.

        Currently performs basic validation and passes through to output.
        The actual audio playback is handled by AudioIOManager in the orchestrator.

        Future enhancements could include:
        - Audio post-processing
        - Volume normalization
        - Quality optimization

        Args:
            session_id: Session identifier
            audio_data: Response audio data from Vertex AI
        """
        # Basic validation
        if not audio_data:
            logger.warning(f"Empty audio response received for session {session_id}")
            return

        # Log response size for monitoring
        response_size = len(audio_data)
        logger.debug(f"Processing audio response for {session_id}: {response_size} bytes")

        # Future: Add audio post-processing here
        # - Volume normalization
        # - Equalization
        # - Quality enhancement
        
    async def _monitor_performance(self) -> None:
        """Background task to monitor pipeline performance."""
        while self._is_running:
            try:
                current_time = time.time()
                
                for session_id, metrics in self._metrics.items():
                    # Check for performance issues
                    avg_latency = metrics.get_avg_latency_ms()
                    p95_latency = metrics.get_p95_latency_ms()
                    
                    # Alert on high latency
                    if p95_latency > self.max_latency_ms * 1.5:
                        alert_msg = f"High P95 latency for {session_id}: {p95_latency:.2f}ms"
                        if alert_msg not in self._performance_alerts:
                            self._performance_alerts.append(alert_msg)
                            logger.warning(alert_msg)
                            
                    # Calculate throughput
                    if metrics.latency_samples:
                        recent_samples = list(metrics.latency_samples)[-10:]
                        if recent_samples:
                            avg_processing_time = statistics.mean(recent_samples) / 1000  # Convert to seconds
                            throughput = 1.0 / avg_processing_time if avg_processing_time > 0 else 0
                            metrics.add_throughput_sample(throughput)
                            
                # Clean up old alerts
                self._performance_alerts = self._performance_alerts[-50:]  # Keep last 50 alerts
                
                # Sleep before next monitoring cycle
                await asyncio.sleep(5.0)  # Monitor every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(5.0)
                
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current pipeline state for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Pipeline state information or None if not found
        """
        if session_id not in self._sessions:
            return None
            
        buffer = self._sessions[session_id]
        metrics = self._metrics[session_id]
        
        return {
            'session_id': session_id,
            'buffer_size': len(buffer.chunks),
            'buffer_bytes': buffer.total_bytes,
            'metrics': metrics.to_dict(),
            'has_processing_task': session_id in self._processing_tasks,
            'is_active': True
        }
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary.
        
        Returns:
            Performance summary across all sessions
        """
        if not self._metrics:
            return {
                'active_sessions': 0,
                'total_chunks_processed': 0,
                'avg_latency_ms': 0.0,
                'avg_throughput_cps': 0.0,
                'total_errors': 0
            }
            
        total_chunks = sum(m.total_chunks_processed for m in self._metrics.values())
        total_errors = sum(m.error_count for m in self._metrics.values())
        
        all_latencies = []
        all_throughputs = []
        
        for metrics in self._metrics.values():
            all_latencies.extend(metrics.latency_samples)
            all_throughputs.extend(metrics.throughput_samples)
            
        return {
            'active_sessions': len(self._sessions),
            'total_chunks_processed': total_chunks,
            'avg_latency_ms': statistics.mean(all_latencies) if all_latencies else 0.0,
            'p95_latency_ms': (
                sorted(all_latencies)[int(0.95 * len(all_latencies))] 
                if all_latencies else 0.0
            ),
            'avg_throughput_cps': statistics.mean(all_throughputs) if all_throughputs else 0.0,
            'total_errors': total_errors,
            'recent_alerts': self._performance_alerts[-10:]  # Last 10 alerts
        }
        
    # Event callback setters
    
    def set_latency_alert_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set callback for latency alerts."""
        self._on_latency_alert = callback
        
    def set_throughput_alert_callback(self, callback: Callable[[str, float], None]) -> None:
        """Set callback for throughput alerts."""
        self._on_throughput_alert = callback
        
    def set_buffer_overflow_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for buffer overflow events."""
        self._on_buffer_overflow = callback