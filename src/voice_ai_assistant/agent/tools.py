"""Claude Code tool integration for Strands Agent.

This module provides the tool wrapper that allows Strands agents to interact
with the Claude Code SDK for repository operations.
"""

import logging
from typing import Optional, Any, Dict, List
import asyncio

# Assuming strands package structure based on docs
from strands import tool

from claude_agent_sdk import ClaudeSDKClient, AssistantMessage, TextBlock
from ..code.repository_manager import RepositoryManager, RepositoryConfig

logger = logging.getLogger(__name__)

class ClaudeCodeTool:
    """Wrapper for Claude Code SDK to be used as a Strands tool.
    
    This class manages the Claude SDK client session and exposes
    a tool method that Strands agents can call.
    """
    
    def __init__(self, repository_path: Optional[str] = None):
        """Initialize Claude Code tool.
        
        Args:
            repository_path: Path to the repository to operate on.
        """
        self.repo_manager = RepositoryManager(repository_path)
        self.options = self.repo_manager.get_options()
        self.client: Optional[ClaudeSDKClient] = None
        self._lock = asyncio.Lock()
        
    async def start(self) -> None:
        """Start the Claude Code SDK client session."""
        if self.client:
            return
            
        self.client = ClaudeSDKClient(options=self.options)
        await self.client.__aenter__()
        logger.info("Claude Code SDK client started")
        
    async def stop(self) -> None:
        """Stop the Claude Code SDK client session."""
        if self.client:
            await self.client.__aexit__(None, None, None)
            self.client = None
            logger.info("Claude Code SDK client stopped")

    @tool
    async def run_coding_task(self, task_description: str) -> str:
        """Perform a coding task or query on the repository.
        
        Use this tool to read files, search code, run commands, or analyze the codebase.
        The tool uses an intelligent coding agent (Claude Code) to execute the task.
        
        Args:
            task_description: A clear description of what to do (e.g., "Find usage of X", "Read file Y").
            
        Returns:
            The result of the operation as a string.
        """
        if not self.client:
            await self.start()
            
        if not self.client:
            return "Error: Claude Code client could not be started."

        logger.info(f"Running coding task: {task_description}")
        
        response_text = []
        
        try:
            async with self._lock:
                # Send query to Claude Code
                await self.client.query(task_description)
                
                # Process streamed response
                async for msg in self.client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                response_text.append(block.text)
                                
            result = "".join(response_text)
            return result if result else "Task completed with no output."
            
        except Exception as e:
            logger.error(f"Error running coding task: {e}")
            return f"Error executing task: {str(e)}"
