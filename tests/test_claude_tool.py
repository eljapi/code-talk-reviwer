"""Test for Claude Code tool wrapper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from voice_ai_assistant.agent.tools import ClaudeCodeTool
from claude_agent_sdk import AssistantMessage, TextBlock

@pytest.mark.asyncio
async def test_claude_tool_execution():
    """Test that ClaudeCodeTool executes tasks using SDK client."""
    with patch('voice_ai_assistant.agent.tools.ClaudeSDKClient') as MockClient:
        # Setup mock client
        mock_client_instance = MockClient.return_value
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        mock_client_instance.query = AsyncMock()
        
        # Mock response streaming
        async def mock_receive():
            msg = AssistantMessage(
                content=[TextBlock(text="Analysis complete.")]
            )
            yield msg
            
        mock_client_instance.receive_response = mock_receive
        
        tool = ClaudeCodeTool()
        await tool.start()
        
        # Run task
        result = await tool.run_coding_task("Analyze code")
        
        # Verify client usage
        mock_client_instance.query.assert_called_with("Analyze code")
        assert result == "Analysis complete."
        
        await tool.stop()
