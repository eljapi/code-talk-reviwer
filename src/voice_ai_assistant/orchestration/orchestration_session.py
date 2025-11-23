"""Orchestration session management.

Manages individual conversation session state and lifecycle.
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from ..agent.strands_agent import StrandsAgent

if TYPE_CHECKING:
    from .voice_orchestrator import VoiceOrchestrator

logger = logging.getLogger(__name__)


class OrchestrationSession:
    """Represents an active orchestration session.

    This class manages the state and lifecycle of a single voice conversation
    session, coordinating between voice, agent, and streaming components.
    """

    def __init__(
        self,
        session_id: str,
        user_id: Optional[str],
        orchestrator: 'VoiceOrchestrator',
        agent_model: str
    ):
        """Initialize orchestration session.

        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            orchestrator: Parent orchestrator instance
            agent_model: Model identifier for the agent
        """
        self.session_id = session_id
        self.user_id = user_id
        self.orchestrator = orchestrator
        self.agent_model = agent_model
        self.created_at = asyncio.get_event_loop().time()

        # Session state
        self.is_active = True
        self.conversation_turns = 0
        self.last_activity = self.created_at

        # Strands Agent
        self.agent: Optional[StrandsAgent] = None

    async def initialize_agent(self) -> None:
        """Initialize and start the Strands Agent."""
        self.agent = StrandsAgent(model=self.agent_model)
        await self.agent.start()

    async def cleanup(self) -> None:
        """Clean up session resources."""
        self.is_active = False

        # Clean up Strands Agent resources
        if self.agent:
            await self.agent.stop()

        logger.debug(f"Cleaned up orchestration session: {self.session_id}")

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = asyncio.get_event_loop().time()

    def get_session_duration(self) -> float:
        """Get session duration in seconds."""
        return asyncio.get_event_loop().time() - self.created_at
