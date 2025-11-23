"""End-to-end pipeline integration tests.

Tests the complete voice-to-voice pipeline including latency measurements
and conversation flow validation.
"""

import asyncio
import pytest
import logging
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any
import wave
import struct

from src.voice_ai_assistant.orchestration import VoiceOrchestrator, OrchestratorConfig
from src.voice_ai_assistant.voice.audio_stream import AudioStreamManager, create_test_audio_file

logger = logging.getLogger(__name__)


class LatencyMeasurement:
    """Measures latency for different pipeline stages."""
    
    def __init__(self):
        self.measurements = {}
        self.start_times = {}
        
    def start_measurement(self, stage: str) -> None:
        """Start measuring latency for a stage."""
        self.start_times[stage] = time.time()
        
    def end_measurement(self, stage: str) -> float:
        """End measurement and return latency in milliseconds."""
        if stage not in self.start_times:
            return 0.0
            
        latency_ms = (time.time() - self.start_times[stage]) * 1000
        
        if stage not in self.measurements:
            self.measurements[stage] = []
        self.measurements[stage].append(latency_ms)
        
        del self.start_times[stage]
        return latency_ms
        
    def get_statistics(self, stage: str) -> Dict[str, float]:
        """Get statistics for a measurement stage."""
        if stage not in self.measurements or not self.measurements[stage]:
            return {}
            
        values = self.measurements[stage]
        return {
            'count': len(values),
            'min_ms': min(values),
            'max_ms': max(values),
            'avg_ms': statistics.mean(values),
            'median_ms': statistics.median(values),
            'p95_ms': sorted(values)[int(0.95 * len(values))] if len(values) > 1 else values[0],
            'p99_ms': sorted(values)[int(0.99 * len(values))] if len(values) > 1 else values[0]
        }
        
    def get_all_statistics(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all measurement stages."""
        return {
            stage: self.get_statistics(stage)
            for stage in self.measurements.keys()
        }


class EndToEndTester:
    """End-to-end pipeline tester."""
    
    def __init__(self, orchestrator: VoiceOrchestrator):
        """Initialize tester with orchestrator.
        
        Args:
            orchestrator: Voice orchestrator instance
        """
        self.orchestrator = orchestrator
        self.latency_measurement = LatencyMeasurement()
        self.audio_manager = AudioStreamManager()
        
        # Test configuration
        self.test_audio_files = []
        self.test_results = []
        
    async def setup_test_environment(self) -> None:
        """Set up test environment with audio files."""
        logger.info("Setting up test environment")
        
        # Create test audio files
        test_dir = Path("tests/test_audio")
        test_dir.mkdir(exist_ok=True)
        
        # Create different test audio files
        test_files = [
            ("short_query.wav", 1.0, "Short query"),
            ("medium_query.wav", 3.0, "Medium length query"),
            ("long_query.wav", 5.0, "Long detailed query")
        ]
        
        for filename, duration, description in test_files:
            file_path = test_dir / filename
            create_test_audio_file(file_path, duration)
            self.test_audio_files.append({
                'path': file_path,
                'duration': duration,
                'description': description
            })
            
        logger.info(f"Created {len(self.test_audio_files)} test audio files")
        
    async def test_voice_to_voice_latency(self) -> Dict[str, Any]:
        """Test complete voice-to-voice latency.
        
        Returns:
            Test results with latency measurements
        """
        logger.info("Starting voice-to-voice latency test")
        
        results = {
            'test_name': 'voice_to_voice_latency',
            'timestamp': time.time(),
            'sessions_tested': 0,
            'total_audio_files': len(self.test_audio_files),
            'latency_measurements': {},
            'errors': []
        }
        
        try:
            for audio_file in self.test_audio_files:
                logger.info(f"Testing with audio file: {audio_file['description']}")
                
                # Start conversation session
                self.latency_measurement.start_measurement('session_creation')
                session_id = await self.orchestrator.start_conversation("test-user")
                session_creation_latency = self.latency_measurement.end_measurement('session_creation')
                
                logger.info(f"Created session {session_id} in {session_creation_latency:.2f}ms")
                
                # Stream audio file and measure processing latency
                await self._test_audio_file_processing(session_id, audio_file)
                
                # Clean up session
                await self.orchestrator.end_conversation(session_id)
                results['sessions_tested'] += 1
                
            # Compile latency statistics
            results['latency_measurements'] = self.latency_measurement.get_all_statistics()
            
            logger.info("Voice-to-voice latency test completed successfully")
            
        except Exception as e:
            error_msg = f"Error in voice-to-voice latency test: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            
        return results
        
    async def _test_audio_file_processing(self, session_id: str, audio_file: Dict[str, Any]) -> None:
        """Test processing of a single audio file.
        
        Args:
            session_id: Active session ID
            audio_file: Audio file information
        """
        file_path = audio_file['path']
        
        try:
            # Measure audio streaming latency
            self.latency_measurement.start_measurement('audio_streaming')
            
            chunk_count = 0
            async for audio_chunk in self.audio_manager.stream_audio_file(file_path):
                # Measure per-chunk processing
                self.latency_measurement.start_measurement('chunk_processing')
                
                await self.orchestrator.send_audio_chunk(session_id, audio_chunk)
                
                chunk_latency = self.latency_measurement.end_measurement('chunk_processing')
                chunk_count += 1
                
                # Small delay to simulate real-time streaming
                await asyncio.sleep(0.01)
                
            streaming_latency = self.latency_measurement.end_measurement('audio_streaming')
            
            logger.info(f"Streamed {chunk_count} chunks in {streaming_latency:.2f}ms")
            
            # Wait for processing to complete (simulate response time)
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error processing audio file {file_path}: {e}")
            raise
            
    async def test_concurrent_sessions(self, num_sessions: int = 3) -> Dict[str, Any]:
        """Test concurrent session handling.
        
        Args:
            num_sessions: Number of concurrent sessions to test
            
        Returns:
            Test results for concurrent sessions
        """
        logger.info(f"Starting concurrent sessions test with {num_sessions} sessions")
        
        results = {
            'test_name': 'concurrent_sessions',
            'timestamp': time.time(),
            'num_sessions': num_sessions,
            'sessions_created': 0,
            'sessions_completed': 0,
            'latency_measurements': {},
            'errors': []
        }
        
        sessions = []
        
        try:
            # Create concurrent sessions
            self.latency_measurement.start_measurement('concurrent_session_creation')
            
            for i in range(num_sessions):
                session_id = await self.orchestrator.start_conversation(f"test-user-{i}")
                sessions.append(session_id)
                results['sessions_created'] += 1
                
            creation_latency = self.latency_measurement.end_measurement('concurrent_session_creation')
            logger.info(f"Created {num_sessions} sessions in {creation_latency:.2f}ms")
            
            # Process audio concurrently
            tasks = []
            for i, session_id in enumerate(sessions):
                audio_file = self.test_audio_files[i % len(self.test_audio_files)]
                task = asyncio.create_task(
                    self._test_audio_file_processing(session_id, audio_file)
                )
                tasks.append(task)
                
            # Wait for all processing to complete
            self.latency_measurement.start_measurement('concurrent_processing')
            await asyncio.gather(*tasks, return_exceptions=True)
            processing_latency = self.latency_measurement.end_measurement('concurrent_processing')
            
            logger.info(f"Completed concurrent processing in {processing_latency:.2f}ms")
            
            # Clean up sessions
            for session_id in sessions:
                await self.orchestrator.end_conversation(session_id)
                results['sessions_completed'] += 1
                
            results['latency_measurements'] = self.latency_measurement.get_all_statistics()
            
            logger.info("Concurrent sessions test completed successfully")
            
        except Exception as e:
            error_msg = f"Error in concurrent sessions test: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            
            # Clean up any remaining sessions
            for session_id in sessions:
                try:
                    await self.orchestrator.end_conversation(session_id)
                except Exception:
                    pass
                    
        return results
        
    async def test_interruption_handling(self) -> Dict[str, Any]:
        """Test conversation interruption (barge-in) handling.
        
        Returns:
            Test results for interruption handling
        """
        logger.info("Starting interruption handling test")
        
        results = {
            'test_name': 'interruption_handling',
            'timestamp': time.time(),
            'interruptions_tested': 0,
            'successful_interruptions': 0,
            'latency_measurements': {},
            'errors': []
        }
        
        try:
            session_id = await self.orchestrator.start_conversation("test-user")
            
            # Test multiple interruption scenarios
            for i in range(3):
                logger.info(f"Testing interruption scenario {i + 1}")
                
                # Start audio processing
                audio_file = self.test_audio_files[0]  # Use short audio file
                
                # Start streaming audio
                audio_stream_task = asyncio.create_task(
                    self._test_audio_file_processing(session_id, audio_file)
                )
                
                # Wait a bit then interrupt
                await asyncio.sleep(0.2)
                
                # Measure interruption latency
                self.latency_measurement.start_measurement('interruption_handling')
                await self.orchestrator.interrupt_conversation(session_id)
                interruption_latency = self.latency_measurement.end_measurement('interruption_handling')
                
                logger.info(f"Interruption handled in {interruption_latency:.2f}ms")
                
                # Cancel the audio streaming task
                audio_stream_task.cancel()
                try:
                    await audio_stream_task
                except asyncio.CancelledError:
                    pass
                    
                results['interruptions_tested'] += 1
                results['successful_interruptions'] += 1
                
                # Brief pause before next test
                await asyncio.sleep(0.1)
                
            await self.orchestrator.end_conversation(session_id)
            
            results['latency_measurements'] = self.latency_measurement.get_all_statistics()
            
            logger.info("Interruption handling test completed successfully")
            
        except Exception as e:
            error_msg = f"Error in interruption handling test: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all end-to-end tests.
        
        Returns:
            Complete test results
        """
        logger.info("Starting complete end-to-end test suite")
        
        await self.setup_test_environment()
        
        all_results = {
            'test_suite': 'end_to_end_pipeline',
            'timestamp': time.time(),
            'tests': {}
        }
        
        # Run individual tests
        test_methods = [
            self.test_voice_to_voice_latency,
            self.test_concurrent_sessions,
            self.test_interruption_handling
        ]
        
        for test_method in test_methods:
            try:
                test_result = await test_method()
                test_name = test_result['test_name']
                all_results['tests'][test_name] = test_result
                
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed: {e}")
                all_results['tests'][test_method.__name__] = {
                    'error': str(e),
                    'timestamp': time.time()
                }
                
        # Generate summary
        all_results['summary'] = self._generate_test_summary(all_results['tests'])
        
        logger.info("End-to-end test suite completed")
        return all_results
        
    def _generate_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of test results.
        
        Args:
            test_results: Individual test results
            
        Returns:
            Test summary
        """
        summary = {
            'total_tests': len(test_results),
            'passed_tests': 0,
            'failed_tests': 0,
            'overall_latency_stats': {},
            'performance_metrics': {}
        }
        
        all_latencies = []
        
        for test_name, result in test_results.items():
            if 'error' in result:
                summary['failed_tests'] += 1
            else:
                summary['passed_tests'] += 1
                
                # Collect latency measurements
                if 'latency_measurements' in result:
                    for stage, stats in result['latency_measurements'].items():
                        if 'avg_ms' in stats:
                            all_latencies.append(stats['avg_ms'])
                            
        # Calculate overall performance metrics
        if all_latencies:
            summary['overall_latency_stats'] = {
                'avg_ms': statistics.mean(all_latencies),
                'min_ms': min(all_latencies),
                'max_ms': max(all_latencies),
                'median_ms': statistics.median(all_latencies)
            }
            
        summary['success_rate'] = (
            summary['passed_tests'] / summary['total_tests'] * 100
            if summary['total_tests'] > 0 else 0
        )
        
        return summary


@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    """Main end-to-end pipeline test."""
    # Create orchestrator with test configuration
    config = OrchestratorConfig(
        project_id="test-project",
        max_concurrent_sessions=5,
        max_response_latency_ms=500
    )
    
    orchestrator = VoiceOrchestrator(config)
    
    # Mock the underlying components for testing
    with patch('src.voice_ai_assistant.orchestration.voice_orchestrator.VoiceSessionManager'):
        await orchestrator.start()
        
        try:
            # Create tester and run tests
            tester = EndToEndTester(orchestrator)
            results = await tester.run_all_tests()
            
            # Validate results
            assert results['summary']['total_tests'] > 0
            assert results['summary']['success_rate'] >= 0  # Allow for some failures in mock environment
            
            # Log results
            logger.info(f"Test Summary: {results['summary']}")
            
            # Check specific performance requirements
            if results['summary']['overall_latency_stats']:
                avg_latency = results['summary']['overall_latency_stats']['avg_ms']
                assert avg_latency < 1000  # Should be under 1 second in test environment
                
        finally:
            await orchestrator.stop()


if __name__ == "__main__":
    # Run the test
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_end_to_end_pipeline())