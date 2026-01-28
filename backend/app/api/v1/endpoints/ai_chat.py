"""
AI Chat API Endpoints

Endpoints for conversational AI interaction on the suggestions page.
Supports refining ideas, creating series, and planning content.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import require_premium
from app.models.user import User
from app.models.ai_chat_session import AIChatSession
from app.services.ai_chat import AIChatService
from app.services.integration import IntegrationService
from app.models.integration import IntegrationProvider
from app.schemas.ai_chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatSessionListItem,
    ExecuteActionRequest,
    ExecuteActionResponse,
    ChatMessage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])


# =============================================================================
# Session Management
# =============================================================================

@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    include_inactive: bool = False,
    limit: int = 10,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    List user's chat sessions.
    
    By default, only returns active sessions.
    """
    query = db.query(AIChatSession).filter(
        AIChatSession.user_id == current_user.id
    )
    
    if not include_inactive:
        query = query.filter(AIChatSession.is_active == True)
    
    query = query.order_by(AIChatSession.created_at.desc())
    sessions = query.limit(limit).all()
    
    return ChatSessionListResponse(
        sessions=[
            ChatSessionListItem(
                id=s.id,
                is_active=s.is_active,
                message_count=s.message_count,
                last_message_at=s.last_message.get("timestamp") if s.last_message else None,
                created_at=s.created_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get chat session details and full message history."""
    session = db.query(AIChatSession).filter(
        AIChatSession.id == session_id,
        AIChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        suggestion_context=session.suggestion_context,
        messages=[
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                action_cards=msg.get("action_cards"),
            )
            for msg in (session.messages or [])
        ],
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/end")
async def end_chat_session(
    session_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """End/close a chat session."""
    session = db.query(AIChatSession).filter(
        AIChatSession.id == session_id,
        AIChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    
    session.end_session()
    db.commit()
    
    return {"message": "Session ended successfully"}


# =============================================================================
# Chat Messages
# =============================================================================

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    request: ChatMessageRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Send a message in an AI chat session.
    
    The AI will respond based on:
    - Current suggestion context
    - Conversation history
    - User's analytics, videos, posts, templates
    - Current trends
    
    AI can respond with:
    - Text responses
    - Action cards (create video, schedule, save plan)
    - Clarifying questions for series/plans
    """
    # Verify session exists and belongs to user
    session = db.query(AIChatSession).filter(
        AIChatSession.id == session_id,
        AIChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    
    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat session is no longer active",
        )
    
    # Check OpenAI integration
    integration_service = IntegrationService(db)
    openai_integration = integration_service.get_by_provider(
        current_user.id, IntegrationProvider.OPENAI
    )
    
    if not openai_integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI integration not configured. Please add your API key in Settings > Integrations.",
        )
    
    if not openai_integration.is_active or not openai_integration.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI integration is not active or validated. Please check Settings > Integrations.",
        )
    
    # Get API key
    try:
        openai_key = integration_service.get_decrypted_api_key(openai_integration)
    except Exception as e:
        logger.error(f"Failed to decrypt OpenAI key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access OpenAI integration",
        )
    
    # Process message
    chat_service = AIChatService(db, openai_key)
    
    try:
        response = await chat_service.process_message(
            session=session,
            user_id=current_user.id,
            message=request.message,
        )
        return response
    except Exception as e:
        logger.exception(f"Chat message processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


# =============================================================================
# Action Execution
# =============================================================================

@router.post("/sessions/{session_id}/execute-action", response_model=ExecuteActionResponse)
async def execute_action(
    session_id: UUID,
    request: ExecuteActionRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Execute an action from an action card.
    
    Supported actions:
    - single_video: Create/schedule a single video
    - series: Create a video series
    - monthly_plan: Create a monthly content plan
    - schedule: Schedule a video for a specific time
    """
    # Verify session exists
    session = db.query(AIChatSession).filter(
        AIChatSession.id == session_id,
        AIChatSession.user_id == current_user.id,
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    
    # Import here to avoid circular imports
    from app.services.video_planning import VideoPlanningService
    
    planning_service = VideoPlanningService(db)
    
    try:
        if request.action_type == "single_video":
            # Navigate to create page with pre-filled data
            return ExecuteActionResponse(
                success=True,
                message="Ready to create video",
                redirect_url=f"/create?suggestion={session_id}",
            )
        
        elif request.action_type == "schedule":
            # Schedule a single video
            if not request.scheduled_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="scheduled_time is required for schedule action",
                )
            
            video = await planning_service.schedule_video(
                user_id=current_user.id,
                suggestion_data=request.action_data.get("suggestion"),
                scheduled_post_time=request.scheduled_time,
                target_platforms=request.target_platforms or request.action_data.get("target_platforms", []),
            )
            
            return ExecuteActionResponse(
                success=True,
                message="Video scheduled successfully",
                created_video_ids=[video.id],
            )
        
        elif request.action_type == "series":
            # Create a video series
            # Handle different formats the AI might return
            action_data = request.action_data
            
            # Get series name from different possible locations
            series_name = (
                action_data.get("series_name") or 
                action_data.get("title") or 
                "Untitled Series"
            )
            
            # Get videos/parts - AI may use "parts" or "videos"
            videos_data = (
                action_data.get("videos") or 
                action_data.get("parts") or 
                []
            )
            
            # Transform parts format to videos format if needed
            transformed_videos = []
            for i, part in enumerate(videos_data):
                video_data = {
                    "title": part.get("title", f"Part {i + 1}"),
                    "description": part.get("description", ""),
                    "hook": part.get("hook", ""),
                    "script_outline": part.get("script_outline", ""),
                    "estimated_duration_seconds": part.get("estimated_duration_seconds", 60),
                    "visual_style": action_data.get("visual_style", part.get("visual_style", "")),
                    "tone": action_data.get("tone", part.get("tone", "")),
                    "hashtags": action_data.get("hashtags", part.get("hashtags", [])),
                    "target_audience": action_data.get("target_audience", part.get("target_audience", "")),
                    "recommended_platforms": action_data.get("recommended_platforms", part.get("recommended_platforms", [])),
                }
                transformed_videos.append(video_data)
            
            # Get schedule - if not provided, create default schedule
            schedule = action_data.get("schedule", [])
            if not schedule and transformed_videos:
                # Create a default schedule - 1 video per day starting tomorrow
                from datetime import datetime, timedelta, timezone
                start_date = datetime.now(timezone.utc) + timedelta(days=1)
                schedule = []
                for i in range(len(transformed_videos)):
                    post_time = start_date + timedelta(days=i)
                    # Set time to 10:00 AM
                    post_time = post_time.replace(hour=10, minute=0, second=0, microsecond=0)
                    schedule.append({
                        "video_index": i,
                        "scheduled_time": post_time.isoformat(),
                    })
            
            # Get target platforms
            target_platforms = (
                request.target_platforms or 
                action_data.get("target_platforms") or 
                action_data.get("recommended_platforms") or 
                ["youtube", "tiktok", "instagram"]
            )
            
            videos = await planning_service.create_series(
                user_id=current_user.id,
                series_name=series_name,
                videos=transformed_videos,
                schedule=schedule,
                target_platforms=target_platforms,
            )
            
            return ExecuteActionResponse(
                success=True,
                message=f"Series '{series_name}' created with {len(videos)} videos",
                created_video_ids=[v.id for v in videos],
                redirect_url="/calendar",
            )
        
        elif request.action_type == "monthly_plan":
            # Create a monthly plan
            videos = await planning_service.create_monthly_plan(
                user_id=current_user.id,
                plan=request.action_data.get("plan"),
            )
            
            return ExecuteActionResponse(
                success=True,
                message=f"Monthly plan created with {len(videos)} videos",
                created_video_ids=[v.id for v in videos],
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action type: {request.action_type}",
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Action execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute action: {str(e)}",
        )
