"""Strands Agent implementation for Voice AI Assistant.

This module implements the main agent that orchestrates the conversation
and leverages the Claude Code tool for coding tasks.
"""

import logging
import os
from typing import AsyncGenerator, Optional, Callable, Awaitable

from strands import Agent
from strands.models.anthropic import AnthropicModel
from .tools import ClaudeCodeTool

logger = logging.getLogger(__name__)

class StrandsAgent:
    """Intelligent agent using Strands framework."""
    
    def __init__(
        self, 
        model: str = "claude-sonnet-4-5-20250929",
        repository_path: Optional[str] = None,
        status_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """Initialize Strands agent.
        
        Args:
            model: Model identifier to use.
            repository_path: Base path to repositories for Claude Code.
            status_callback: Async callback for streaming status updates.
        """
        self.model_name = model
        self.repository_path = repository_path
        self.status_callback = status_callback
        
        # Initialize Claude Code tool with repository path and status callback
        self.claude_tool = ClaudeCodeTool(
            repository_path=self.repository_path,
            status_callback=self.status_callback
        )
        self.agent: Optional[Agent] = None
        
    async def start(self) -> None:
        """Start the agent and its tools."""
        await self.claude_tool.start()
        
        # Initialize Strands Agent with the Claude Code tool
        # Use AnthropicModel to avoid defaulting to Bedrock
        # Pass API key from environment in client_args
        api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("CLAUDE_API_KEY or ANTHROPIC_API_KEY environment variable must be set")
        
        anthropic_model = AnthropicModel(
            client_args={"api_key": api_key},
            model_id=self.model_name,
            max_tokens=4096
        )
        
        self.agent = Agent(
            model=anthropic_model,
            tools=[self.claude_tool.run_coding_task],
            system_prompt=(
                "You are a Voice-Enabled AI Coding Assistant. "
                "Your goal is to help developers by analyzing code and answering questions. "
                "You have access to a powerful coding tool called 'run_coding_task' which uses Claude Code. "
                "ALWAYS use 'run_coding_task' for any request involving reading files, searching code, "
                "or understanding the repository structure. "
                "Do not try to hallucinate code content. "
                "\n\n"
                "CRITICAL: Your responses will be converted to speech. "
                "DO NOT use markdown formatting (no **, ##, -, *, etc.). "
                "Use plain conversational text only. "
                "Keep your voice responses concise and natural. "
                "When summarizing results, speak naturally as if talking to someone. "
                "If the user asks to do something, briefly confirm you are doing it, call the tool, "
                "and then provide a concise spoken summary of the result."
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
            # Use Strands Agent stream_async method
            # This returns an async generator yielding chunks
            async for chunk in self.agent.stream_async(text):
                # Filter out event dictionaries and metadata
                # Only process actual text content
                if isinstance(chunk, dict):
                    # Check if it's a data chunk with text
                    if 'data' in chunk and isinstance(chunk['data'], str):
                        yield chunk['data']
                    # Skip event metadata chunks
                    elif 'event' in chunk:
                        continue
                    # Skip other metadata
                    else:
                        continue
                elif hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text
                elif isinstance(chunk, str):
                    yield chunk

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            yield f"I encountered an error: {str(e)}"
