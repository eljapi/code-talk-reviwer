"""Conversation flow management for voice interactions.

Manages the flow of conversation between user voice input and AI agent responses,
including turn-taking, interruption handling, and conversation state.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """States of a conversation flow."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation."""
    
    turn_id: str
    session_id: str
    speaker: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    processing_time_ms: Optional[float] = None
    interrupted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'turn_id': self.turn_id,
            'session_id': self.session_id,
            'speaker': self.speaker,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'processing_time_ms': self.processing_time_ms,
            'interrupted': self.interrupted
        }


@dataclass
class ConversationContext:
    """Maintains context for a conversation session."""
    
    session_id: str
    state: ConversationState = ConversationState.IDLE
    turns: List[ConversationTurn] = field(default_factory=list)
    current_turn_id: Optional[str] = None
    interruption_count: int = 0
    total_processing_time_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def add_turn(self, turn: ConversationTurn) -> None:
        """Add a conversation turn."""
        self.turns.append(turn)
        self.last_activity = datetime.now()
        
    def get_recent_turns(self, count: int = 5) -> List[ConversationTurn]:
        """Get the most recent conversation turns."""
        return self.turns[-count:] if self.turns else []
        
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation statistics."""
        user_turns = sum(1 for turn in self.turns if turn.speaker == "user")
        assistant_turns = sum(1 for turn in self.turns if turn.speaker == "assistant")
        
        return {
            'session_id': self.session_id,
            'state': self.state.value,
            'total_turns': len(self.turns),
            'user_turns': user_turns,
            'assistant_turns': assistant_turns,
            'interruption_count': self.interruption_count,
            'avg_processing_time_ms': (
                self.total_processing_time_ms / len(self.turns) 
                if self.turns else 0
            ),
            'duration_minutes': (
                (self.last_activity - self.created_at).total_seconds() / 60
            )
        }


class ConversationFlowManager:
    """Manages conversation flow and turn-taking for voice sessions.
    
    This class handles:
    - Conversation state transitions
    - Turn-taking coordination
    - Interruption handling (barge-in)
    - Conversation history and context
    - Flow control between voice input and agent processing
    """
    
    def __init__(self, 
                 max_turns: int = 50,
                 enable_interruption: bool = True,
                 context_window_size: int = 10):
        """Initialize conversation flow manager.
        
        Args:
            max_turns: Maximum turns per conversation
            enable_interruption: Whether to allow interruptions
            context_window_size: Number of recent turns to keep in context
        """
        self.max_turns = max_turns
        self.enable_interruption = enable_interruption
        self.context_window_size = context_window_size
        
        # Active conversation contexts
        self._conversations: Dict[str, ConversationContext] = {}
        self._is_running = False
        
        # Event callbacks
        self._on_state_change: Optional[Callable[[str, ConversationState], None]] = None
        self._on_turn_complete: Optional[Callable[[str, ConversationTurn], None]] = None
        self._on_interruption: Optional[Callable[[str], None]] = None
        
    async def start(self) -> None:
        """Start the conversation flow manager."""
        if self._is_running:
            return
            
        logger.info("Starting conversation flow manager")
        self._is_running = True
        
    async def stop(self) -> None:
        """Stop the conversation flow manager."""
        if not self._is_running:
            return
            
        logger.info("Stopping conversation flow manager")
        
        # Clean up all conversations
        for session_id in list(self._conversations.keys()):
            await self.end_conversation(session_id)
            
        self._is_running = False
        
    async def initialize_conversation(self, session_id: str) -> None:
        """Initialize a new conversation.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._conversations:
            logger.warning(f"Conversation already exists: {session_id}")
            return
            
        context = ConversationContext(session_id=session_id)
        self._conversations[session_id] = context
        
        logger.info(f"Initialized conversation: {session_id}")
        await self._transition_state(session_id, ConversationState.IDLE)
        
    async def end_conversation(self, session_id: str) -> None:
        """End a conversation and clean up resources.
        
        Args:
            session_id: Session to end
        """
        if session_id not in self._conversations:
            logger.warning(f"Conversation not found: {session_id}")
            return
            
        context = self._conversations[session_id]
        summary = context.get_conversation_summary()
        
        logger.info(f"Ending conversation {session_id}: {summary}")
        
        del self._conversations[session_id]
        
    async def process_user_input(self, session_id: str, user_input: str) -> None:
        """Process user voice input and manage conversation flow.
        
        Args:
            session_id: Session identifier
            user_input: Transcribed user speech
        """
        if session_id not in self._conversations:
            logger.error(f"Conversation not found: {session_id}")
            return
            
        context = self._conversations[session_id]
        
        # Check if we can accept input in current state
        if context.state not in [ConversationState.IDLE, ConversationState.LISTENING]:
            if self.enable_interruption and context.state == ConversationState.RESPONDING:
                await self.handle_interruption(session_id)
            else:
                logger.warning(f"Cannot process input in state {context.state}")
                return
                
        try:
            # Transition to processing state
            await self._transition_state(session_id, ConversationState.PROCESSING)
            
            # Create user turn
            turn_id = f"{session_id}_{len(context.turns)}"
            user_turn = ConversationTurn(
                turn_id=turn_id,
                session_id=session_id,
                speaker="user",
                content=user_input
            )
            
            context.add_turn(user_turn)
            context.current_turn_id = turn_id
            
            logger.info(f"Processing user input for {session_id}: {user_input}")
            
            # Notify turn completion
            if self._on_turn_complete:
                self._on_turn_complete(session_id, user_turn)
                
            # TODO: This is where we would trigger Strands Agent processing
            # For now, we'll simulate the flow by transitioning to responding
            await asyncio.sleep(0.1)  # Simulate processing delay
            await self._transition_state(session_id, ConversationState.RESPONDING)
            
        except Exception as e:
            logger.error(f"Error processing user input for {session_id}: {e}")
            await self._transition_state(session_id, ConversationState.ERROR)
            
    async def process_agent_response(self, session_id: str, agent_response: str) -> None:
        """Process agent response and complete the conversation turn.
        
        Args:
            session_id: Session identifier
            agent_response: Agent's response text
        """
        if session_id not in self._conversations:
            logger.error(f"Conversation not found: {session_id}")
            return
            
        context = self._conversations[session_id]
        
        if context.state != ConversationState.RESPONDING:
            logger.warning(f"Unexpected agent response in state {context.state}")
            return
            
        try:
            # Create assistant turn
            turn_id = f"{session_id}_{len(context.turns)}"
            assistant_turn = ConversationTurn(
                turn_id=turn_id,
                session_id=session_id,
                speaker="assistant",
                content=agent_response
            )
            
            context.add_turn(assistant_turn)
            
            logger.info(f"Processing agent response for {session_id}: {agent_response}")
            
            # Notify turn completion
            if self._on_turn_complete:
                self._on_turn_complete(session_id, assistant_turn)
                
            # Check conversation limits
            if len(context.turns) >= self.max_turns:
                logger.info(f"Conversation {session_id} reached max turns limit")
                await self.end_conversation(session_id)
                return
                
            # Transition back to listening
            await self._transition_state(session_id, ConversationState.LISTENING)
            
        except Exception as e:
            logger.error(f"Error processing agent response for {session_id}: {e}")
            await self._transition_state(session_id, ConversationState.ERROR)
            
    async def handle_interruption(self, session_id: str) -> None:
        """Handle conversation interruption (barge-in).
        
        Args:
            session_id: Session being interrupted
        """
        if session_id not in self._conversations:
            logger.error(f"Conversation not found: {session_id}")
            return
            
        if not self.enable_interruption:
            logger.warning(f"Interruption disabled for session: {session_id}")
            return
            
        context = self._conversations[session_id]
        context.interruption_count += 1
        
        # Mark current turn as interrupted if exists
        if context.turns and context.turns[-1].speaker == "assistant":
            context.turns[-1].interrupted = True
            
        logger.info(f"Handling interruption for session {session_id} (count: {context.interruption_count})")
        
        # Transition to interrupted state
        await self._transition_state(session_id, ConversationState.INTERRUPTED)
        
        # Notify interruption callback
        if self._on_interruption:
            self._on_interruption(session_id)
            
        # Quickly transition to listening for new input
        await asyncio.sleep(0.05)  # Brief pause
        await self._transition_state(session_id, ConversationState.LISTENING)
        
    async def _transition_state(self, session_id: str, new_state: ConversationState) -> None:
        """Transition conversation to new state.
        
        Args:
            session_id: Session identifier
            new_state: Target state
        """
        if session_id not in self._conversations:
            return
            
        context = self._conversations[session_id]
        old_state = context.state
        context.state = new_state
        context.last_activity = datetime.now()
        
        logger.debug(f"State transition for {session_id}: {old_state.value} -> {new_state.value}")
        
        # Notify state change callback
        if self._on_state_change:
            self._on_state_change(session_id, new_state)
            
    def get_conversation_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversation state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation state information or None if not found
        """
        if session_id not in self._conversations:
            return None
            
        context = self._conversations[session_id]
        return {
            'session_id': session_id,
            'state': context.state.value,
            'current_turn_id': context.current_turn_id,
            'recent_turns': [turn.to_dict() for turn in context.get_recent_turns()],
            'summary': context.get_conversation_summary()
        }
        
    def get_conversation_context(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get conversation context for agent processing.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of recent conversation turns for context
        """
        if session_id not in self._conversations:
            return None
            
        context = self._conversations[session_id]
        recent_turns = context.get_recent_turns(self.context_window_size)
        
        return [
            {
                'role': 'user' if turn.speaker == 'user' else 'assistant',
                'content': turn.content,
                'timestamp': turn.timestamp.isoformat()
            }
            for turn in recent_turns
        ]
        
    def list_active_conversations(self) -> Dict[str, Dict[str, Any]]:
        """List all active conversations.
        
        Returns:
            Dictionary of session ID to conversation state
        """
        return {
            session_id: self.get_conversation_state(session_id)
            for session_id in self._conversations.keys()
        }
        
    # Event callback setters
    
    def set_state_change_callback(self, callback: Callable[[str, ConversationState], None]) -> None:
        """Set callback for state change events."""
        self._on_state_change = callback
        
    def set_turn_complete_callback(self, callback: Callable[[str, ConversationTurn], None]) -> None:
        """Set callback for turn completion events."""
        self._on_turn_complete = callback
        
    def set_interruption_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for interruption events."""
        self._on_interruption = callback