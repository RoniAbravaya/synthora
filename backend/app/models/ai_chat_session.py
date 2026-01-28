"""
AI Chat Session Model

Stores chat conversation context for AI suggestions feature.
Sessions are used for conversational AI interaction where users
can refine suggestions, create video series, and plan content.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AIChatSession(Base):
    """
    Model for AI chat sessions.
    
    Each session represents a conversation between a user and the AI
    about a specific suggestion. The session stores:
    - The suggestion being discussed (context)
    - The full message history
    - Session state (active/ended)
    
    Attributes:
        id: Unique session identifier (UUID)
        user_id: Foreign key to user
        suggestion_context: The AI suggestion being discussed (JSON)
        messages: List of chat messages (JSON array)
        is_active: Whether the session is still active
        created_at: When the session was created
        updated_at: When the session was last updated
        
    Relationships:
        user: The user who owns this session
    """
    
    __tablename__ = "ai_chat_sessions"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique session identifier"
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user"
    )
    suggestion_context = Column(
        JSONB,
        nullable=True,
        doc="The AI suggestion being discussed"
    )
    messages = Column(
        JSONB,
        nullable=False,
        default=list,
        doc="List of chat messages [{role, content, timestamp, action_cards?}]"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether the session is still active"
    )
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
        doc="When the session was created"
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True,
        doc="When the session was last updated"
    )
    
    # Relationships
    user = relationship("User", back_populates="ai_chat_sessions")
    
    def __repr__(self) -> str:
        return f"<AIChatSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
    
    def add_message(
        self,
        role: str,
        content: str,
        action_cards: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Add a message to the session.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            action_cards: Optional list of action cards (for assistant messages)
        """
        if self.messages is None:
            self.messages = []
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if action_cards:
            message["action_cards"] = action_cards
        
        # Create new list to trigger SQLAlchemy change detection
        self.messages = self.messages + [message]
    
    def get_messages_for_ai(self) -> List[Dict[str, str]]:
        """
        Get messages formatted for OpenAI API.
        
        Returns:
            List of messages with role and content only
        """
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in (self.messages or [])
        ]
    
    @property
    def message_count(self) -> int:
        """Get the number of messages in the session."""
        return len(self.messages or [])
    
    @property
    def last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message in the session."""
        if not self.messages:
            return None
        return self.messages[-1]
    
    def end_session(self) -> None:
        """Mark the session as ended/inactive."""
        self.is_active = False
