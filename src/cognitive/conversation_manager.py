"""
Conversation Manager - Multi-turn dialogue and context management

Handles:
- Conversation state tracking (Idle/Active)
- 30-second timeout with periodic checks
- Conversation history (last 10 messages)
- Entity tracking for pronoun resolution
- Event publishing for conversation lifecycle
"""

import asyncio
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from src.core.event_bus import get_event_bus
except ImportError:
    # Fallback for testing
    def get_event_bus():
        return None


class ConversationState(Enum):
    """Conversation states"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class Message:
    """A single message in conversation history"""
    role: str  # "user" or "jarvis"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Entity:
    """Tracked entity for pronoun resolution"""
    type: str  # "app", "file", "url", "project"
    value: str
    timestamp: float = field(default_factory=time.time)


class ConversationManager:
    """
    Manages conversation state, history, and context for multi-turn dialogue.
    
    Features:
    - 30-second timeout mechanism
    - Rolling conversation history (last 10 messages)
    - Entity tracking for pronoun resolution
    - Event integration via Event Bus
    """
    
    def __init__(self, timeout_seconds: int = 30, max_history: int = 10):
        """
        Initialize ConversationManager
        
        Args:
            timeout_seconds: Seconds of inactivity before ending conversation
            max_history: Maximum number of messages to keep in history
        """
        self.timeout_seconds = timeout_seconds
        self.max_history = max_history
        
        self.state = ConversationState.IDLE
        self.history: List[Message] = []
        self.last_activity = time.time()
        
        # Entity tracking for pronoun resolution
        self.entities: Dict[str, Entity] = {
            "app": None,
            "file": None,
            "url": None,
            "project": None
        }
        
        # Event bus integration
        self.event_bus = get_event_bus()
        
        # Timeout task
        self._timeout_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the conversation manager"""
        self._running = True
        if self.event_bus:
            # Start timeout checker
            self._timeout_task = asyncio.create_task(self._check_timeout_loop())
    
    async def stop(self):
        """Stop the conversation manager"""
        self._running = False
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
    
    async def _check_timeout_loop(self):
        """Periodically check for conversation timeout"""
        while self._running:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            if self.state != ConversationState.IDLE:
                elapsed = time.time() - self.last_activity
                if elapsed >= self.timeout_seconds:
                    await self.end_conversation("timeout")
    
    async def start_conversation(self):
        """Start a new conversation"""
        if self.state == ConversationState.IDLE:
            self.state = ConversationState.LISTENING
            self.last_activity = time.time()
            
            if self.event_bus:
                await self.event_bus.publish("conversation.started", {})
    
    async def end_conversation(self, reason: str = "timeout"):
        """
        End the current conversation
        
        Args:
            reason: Reason for ending ("timeout", "manual", "error")
        """
        if self.state != ConversationState.IDLE:
            self.state = ConversationState.IDLE
            
            if self.event_bus:
                await self.event_bus.publish("conversation.ended", {
                    "reason": reason,
                    "message_count": len(self.history)
                })
    
    async def add_user_message(self, text: str):
        """
        Add a user message to history
        
        Args:
            text: User's message
        """
        message = Message(role="user", content=text)
        self.history.append(message)
        
        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Reset timeout
        self.last_activity = time.time()
        
        # Update state
        if self.state == ConversationState.LISTENING:
            self.state = ConversationState.PROCESSING
        
        # Publish event
        if self.event_bus:
            await self.event_bus.publish("conversation.user_message", {
                "text": text,
                "timestamp": message.timestamp
            })
    
    async def add_jarvis_message(self, text: str):
        """
        Add a Jarvis response to history
        
        Args:
            text: Jarvis's response
        """
        message = Message(role="jarvis", content=text)
        self.history.append(message)
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Reset timeout
        self.last_activity = time.time()
        
        # Update state
        self.state = ConversationState.SPEAKING
        
        # Publish event
        if self.event_bus:
            await self.event_bus.publish("conversation.jarvis_message", {
                "text": text,
                "timestamp": message.timestamp
            })
    
    def track_entity(self, entity_type: str, value: str):
        """
        Track an entity for pronoun resolution
        
        Args:
            entity_type: Type of entity ("app", "file", "url", "project")
            value: Entity value (e.g., "chrome", "readme.md")
        """
        if entity_type in self.entities:
            self.entities[entity_type] = Entity(type=entity_type, value=value)
    
    def get_entity(self, entity_type: str) -> Optional[str]:
        """
        Get tracked entity for pronoun resolution
        
        Args:
            entity_type: Type of entity to retrieve
            
        Returns:
            Entity value if tracked, None otherwise
        """
        entity = self.entities.get(entity_type)
        return entity.value if entity else None
    
    def get_last_entity(self) -> Optional[str]:
        """
        Get the most recently tracked entity (for "it", "that")
        
        Returns:
            Most recent entity value, None if no entities tracked
        """
        recent_entity = None
        recent_time = 0
        
        for entity in self.entities.values():
            if entity and entity.timestamp > recent_time:
                recent_entity = entity.value
                recent_time = entity.timestamp
        
        return recent_entity
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get current conversation context
        
        Returns:
            Dictionary with state, history, and entities
        """
        return {
            "state": self.state.value,
            "history": [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                for msg in self.history
            ],
            "entities": {
                k: v.value if v else None
                for k, v in self.entities.items()
            },
            "last_activity": self.last_activity,
            "is_active": self.state != ConversationState.IDLE
        }
    
    def set_state(self, state: ConversationState):
        """
        Set conversation state
        
        Args:
            state: New conversation state
        """
        self.state = state
        self.last_activity = time.time()


# Singleton instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager(timeout_seconds: int = 30) -> ConversationManager:
    """
    Get or create the global ConversationManager instance
    
    Args:
        timeout_seconds: Timeout duration (only used on first call)
        
    Returns:
        Global ConversationManager instance
    """
    global _conversation_manager
    
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(timeout_seconds=timeout_seconds)
    
    return _conversation_manager
