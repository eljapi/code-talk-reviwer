"""Integration test for Strands Agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from voice_ai_assistant.agent.strands_agent import StrandsAgent
from voice_ai_assistant.agent.tools import ClaudeCodeTool

@pytest.mark.asyncio
async def test_strands_agent_initialization():
    """Test that StrandsAgent initializes correctly."""
    with patch('voice_ai_assistant.agent.strands_agent.ClaudeCodeTool') as MockTool, \
         patch('voice_ai_assistant.agent.strands_agent.Agent') as MockStrandsAgent:
        
        mock_tool_instance = MockTool.return_value
        mock_tool_instance.start = AsyncMock()
        mock_tool_instance.stop = AsyncMock()
        mock_tool_instance.run_coding_task = MagicMock()
        
        agent = StrandsAgent()
        await agent.start()
        
        # Verify tool started
        mock_tool_instance.start.assert_called_once()
        
        # Verify Strands Agent initialized with tool
        MockStrandsAgent.assert_called_once()
        call_args = MockStrandsAgent.call_args
        assert mock_tool_instance.run_coding_task in call_args.kwargs['tools']
        
        await agent.stop()
        mock_tool_instance.stop.assert_called_once()

@pytest.mark.asyncio
async def test_strands_agent_processing():
    """Test that StrandsAgent processes messages and streams responses."""
    with patch('voice_ai_assistant.agent.strands_agent.ClaudeCodeTool'), \
         patch('voice_ai_assistant.agent.strands_agent.Agent') as MockStrandsAgent:
        
        # Setup mock agent streaming
        mock_agent_instance = MockStrandsAgent.return_value
        
        async def mock_stream(text):
            yield {"data": "Hello "}
            yield {"data": "World"}
            
        mock_agent_instance.stream_async = mock_stream
        
        agent = StrandsAgent()
        await agent.start()
        
        # Process message
        responses = []
        async for chunk in agent.process_message("Hi"):
            responses.append(chunk)
            
        assert responses == ["Hello ", "World"]
