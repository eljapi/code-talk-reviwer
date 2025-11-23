"""Strands Agent implementation for Voice AI Assistant.

This module implements the main agent that orchestrates the conversation
and leverages the Claude Code tool for coding tasks.
"""

import logging
from typing import AsyncGenerator, Optional

from strands import Agent
from .tools import ClaudeCodeTool

logger = logging.getLogger(__name__)

class StrandsAgent:
    """Intelligent agent using Strands framework."""
    
    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize Strands agent.
        
        Args:
            model: Model identifier to use.
        """
        self.model_name = model
        self.claude_tool = ClaudeCodeTool()
        self.agent: Optional[Agent] = None
        
    async def start(self) -> None:
        """Start the agent and its tools."""
        await self.claude_tool.start()
        
        # Initialize Strands Agent with the Claude Code tool
        # Note: We bind the tool method to the instance
        self.agent = Agent(
            model=self.model_name,
            tools=[self.claude_tool.run_coding_task],
            system_prompt=(
                "You are a Voice-Enabled AI Coding Assistant. "
                "Your goal is to help developers by analyzing code and answering questions. "
                "You have access to a powerful coding tool called 'run_coding_task' which uses Claude Code. "
                "ALWAYS use 'run_coding_task' for any request involving reading files, searching code, "
                "or understanding the repository structure. "
                "Do not try to hallucinate code content. "
                "Keep your voice responses concise and conversational. "
                "If the user asks to do something, confirm you are doing it, call the tool, "
                "and then summarize the result."
            )
        )
        logger.info("Strands Agent started")
        
    async def stop(self) -> None:
        """Stop the agent and cleanup."""
        await self.claude_tool.stop()
        logger.info("Strands Agent stopped")
        
    async def process_message(self, text: str) -> AsyncGenerator[str, None]:
        """Process a user message and stream the response.
        
        Args:
            text: User input text.
            
        Yields:
            Chunks of the agent's response text.
        """
        if not self.agent:
            raise RuntimeError("Agent not started")
            
        logger.info(f"Processing message: {text}")
        
        try:
            # Use Strands' async streaming interface
            # Note: The exact API depends on Strands version, assuming stream_async based on docs
            async for event in self.agent.stream_async(text):
                if "data" in event:
                    yield event["data"]
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            yield f"I encountered an error: {str(e)}"
