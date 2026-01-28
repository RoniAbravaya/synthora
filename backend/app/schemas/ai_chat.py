"""
AI Chat Pydantic Schemas

Request and response schemas for AI chat functionality.
Supports conversational interaction for refining suggestions,
creating series, and planning content.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, IDSchema


# =============================================================================
# Action Cards
# =============================================================================

class ActionCard(BaseSchema):
    """
    Actionable card within chat responses.
    
    Action cards allow users to execute actions directly from chat,
    such as scheduling videos, creating series, or saving plans.
    """
    
    type: Literal["single_video", "series", "monthly_plan", "schedule"] = Field(
        description="Type of action card"
    )
    title: str = Field(description="Action card title")
    description: str = Field(default="", description="Action card description")
    data: Dict[str, Any] = Field(default_factory=dict, description="Action-specific data")


# =============================================================================
# Chat Messages
# =============================================================================

class ChatMessage(BaseSchema):
    """A single chat message."""
    
    role: Literal["user", "assistant"] = Field(description="Message sender role")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(description="When the message was sent")
    action_cards: Optional[List[ActionCard]] = Field(
        default=None,
        description="Action cards (for assistant messages)"
    )


# =============================================================================
# Request Schemas
# =============================================================================

class ChatMessageRequest(BaseSchema):
    """Request to send a chat message."""
    
    message: str = Field(
        min_length=1,
        max_length=2000,
        description="User's message"
    )


class ExecuteActionRequest(BaseSchema):
    """Request to execute an action from an action card."""
    
    action_type: str = Field(description="Type of action to execute")
    action_data: Dict[str, Any] = Field(description="Action data from the card")
    
    # Optional overrides
    scheduled_time: Optional[datetime] = Field(
        default=None,
        description="Override scheduled time"
    )
    target_platforms: Optional[List[str]] = Field(
        default=None,
        description="Override target platforms"
    )


# =============================================================================
# Response Schemas
# =============================================================================

class ChatMessageResponse(BaseSchema):
    """Response from sending a chat message."""
    
    message: str = Field(description="AI's response message")
    action_cards: List[ActionCard] = Field(
        default_factory=list,
        description="Action cards for user to execute"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether AI needs more information"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Clarification question if needs_clarification is True"
    )


class ChatSessionResponse(IDSchema):
    """Full chat session response."""
    
    user_id: UUID
    suggestion_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The suggestion being discussed"
    )
    messages: List[ChatMessage] = Field(
        default_factory=list,
        description="Chat message history"
    )
    is_active: bool = Field(description="Whether session is still active")
    created_at: datetime
    updated_at: Optional[datetime] = None


class ChatSessionListItem(BaseSchema):
    """Chat session list item."""
    
    id: UUID
    is_active: bool
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime


class ChatSessionListResponse(BaseSchema):
    """List of chat sessions."""
    
    sessions: List[ChatSessionListItem]
    total: int


class ExecuteActionResponse(BaseSchema):
    """Response from executing an action."""
    
    success: bool
    message: str
    created_video_ids: Optional[List[UUID]] = Field(
        default=None,
        description="IDs of created/scheduled videos"
    )
    redirect_url: Optional[str] = Field(
        default=None,
        description="URL to redirect to (e.g., /create page)"
    )
