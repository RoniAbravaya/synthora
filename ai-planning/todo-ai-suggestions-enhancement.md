# AI Suggestions Page Enhancement - Implementation Checklist

**Feature**: Enhanced AI Suggestions with Chat, Series Planning, and Auto-Generation  
**Created**: January 28, 2026  
**Status**: Planning Complete  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Database Changes](#2-database-changes)
3. [Backend API Changes](#3-backend-api-changes)
4. [AI Service Implementation](#4-ai-service-implementation)
5. [Background Job System](#5-background-job-system)
6. [Frontend Changes](#6-frontend-changes)
7. [Calendar Page Updates](#7-calendar-page-updates)
8. [Notification System](#8-notification-system)
9. [Testing](#9-testing)
10. [Deployment](#10-deployment)

---

## 1. Overview

### 1.1 Feature Description

Enhance the AI Suggestions page to provide intelligent video recommendations with an interactive chat interface. Users can generate suggestions, refine them through conversation, create video series, plan monthly content, and schedule automated video generation and posting.

### 1.2 User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER CLICKS "GENERATE SUGGESTION"                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CHECK DATA SUFFICIENCY                                │
│  - ≥3 published posts?                                                       │
│  - ≥3 days analytics history?                                                │
│  - ≥20 total engagement (views/likes/shares)?                               │
└─────────────────────────────────────────────────────────────────────────────┘
                          │                    │
                    YES (all met)         NO (any fails)
                          │                    │
                          ▼                    ▼
              ┌──────────────────┐  ┌──────────────────────┐
              │ ANALYZE ANALYTICS │  │ USE TRENDS/GENERAL   │
              │ - Performance     │  │ - Trending topics    │
              │ - Engagement      │  │ - Platform trends    │
              │ - Best patterns   │  │ - General ideas      │
              └──────────────────┘  └──────────────────────┘
                          │                    │
                          └────────┬───────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GENERATE COMPLETE SUGGESTION                            │
│  - Title, Description, Hook                                                  │
│  - Script outline, Hashtags                                                  │
│  - Duration, Visual style, Tone                                              │
│  - Target platform recommendations                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DISPLAY SUGGESTION + CHAT                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  SUGGESTION CARD                              [Generate Another]     │    │
│  │  Title: "10 Python Tips for Beginners"                              │    │
│  │  Description: ...                                                    │    │
│  │  Hook: "Did you know 90% of developers..."                          │    │
│  │  [Generate Video Now] [Schedule for Later] [Refine This Idea]       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  CHAT INTERFACE                                                      │    │
│  │  AI: "I've created a video suggestion based on your analytics..."   │    │
│  │  User: "Can you create a 5-part series on this topic?"              │    │
│  │  AI: "Sure! How would you like to schedule them?"                   │    │
│  │  ...                                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
        ┌─────────────────────┐      ┌─────────────────────────┐
        │ GENERATE VIDEO NOW  │      │ SCHEDULE / CREATE PLAN  │
        │ → /create page      │      │ → Save to Calendar      │
        │   with pre-filled   │      │ → video status=planned  │
        └─────────────────────┘      └─────────────────────────┘
                                                  │
                                                  ▼
                              ┌─────────────────────────────────┐
                              │      BACKGROUND JOB             │
                              │  - Runs every 15 minutes        │
                              │  - Checks for videos due in 1hr │
                              │  - Triggers generation          │
                              │  - Auto-posts when ready        │
                              │  - Notifies on success/failure  │
                              └─────────────────────────────────┘
```

### 1.3 Prerequisites

- [x] User must be Premium (existing gate)
- [ ] User must have OpenAI API key configured in integrations
- [ ] OpenAI integration validation before chat features

### 1.4 Data Sufficiency Thresholds

| Condition | Threshold | Fallback |
|-----------|-----------|----------|
| Published posts | < 3 | Use trends |
| Analytics history | < 3 days | Use trends |
| Total engagement | < 20 | Use trends |

---

## 2. Database Changes

### 2.1 Extend `videos` Table

- [ ] **2.1.1** Add new columns to `videos` table via Alembic migration

```python
# File: backend/alembic/versions/xxx_extend_videos_for_planning.py
# Type: NEW FILE

"""
Migration: Extend videos table for planning and scheduling

Adds columns for:
- Planned/scheduled video workflow
- Series management
- AI suggestion data storage
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

def upgrade():
    # Add scheduling columns
    op.add_column('videos', sa.Column('scheduled_post_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('videos', sa.Column('generation_triggered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('videos', sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add series columns
    op.add_column('videos', sa.Column('series_name', sa.String(255), nullable=True))
    op.add_column('videos', sa.Column('series_order', sa.Integer, nullable=True))
    
    # Add platform targeting
    op.add_column('videos', sa.Column('target_platforms', ARRAY(sa.String), nullable=True))
    
    # Add AI suggestion data (stores complete suggestion details)
    op.add_column('videos', sa.Column('ai_suggestion_data', JSONB, nullable=True))
    
    # Add planning status tracking
    # Modify existing status enum or add new column
    op.add_column('videos', sa.Column('planning_status', sa.String(50), nullable=True, server_default='none'))
    
    # Add indexes for efficient querying
    op.create_index('ix_videos_scheduled_post_time', 'videos', ['scheduled_post_time'])
    op.create_index('ix_videos_planning_status', 'videos', ['planning_status'])
    op.create_index('ix_videos_series_name', 'videos', ['series_name'])

def downgrade():
    op.drop_index('ix_videos_series_name')
    op.drop_index('ix_videos_planning_status')
    op.drop_index('ix_videos_scheduled_post_time')
    op.drop_column('videos', 'planning_status')
    op.drop_column('videos', 'ai_suggestion_data')
    op.drop_column('videos', 'target_platforms')
    op.drop_column('videos', 'series_order')
    op.drop_column('videos', 'series_name')
    op.drop_column('videos', 'posted_at')
    op.drop_column('videos', 'generation_triggered_at')
    op.drop_column('videos', 'scheduled_post_time')
```

### 2.2 Update Video Model

- [ ] **2.2.1** Update SQLAlchemy model with new fields

```python
# File: backend/app/models/video.py
# Type: MODIFY EXISTING

# Add to Video class:

class PlanningStatus(str, Enum):
    """Planning status for scheduled videos."""
    NONE = "none"              # Regular video, not scheduled
    PLANNED = "planned"        # Scheduled but not generated
    GENERATING = "generating"  # Generation in progress
    READY = "ready"           # Generated, waiting for post time
    POSTING = "posting"       # Posting in progress
    POSTED = "posted"         # Successfully posted
    FAILED = "failed"         # Generation or posting failed

# Add columns to Video model:
scheduled_post_time = Column(DateTime(timezone=True), nullable=True, index=True)
generation_triggered_at = Column(DateTime(timezone=True), nullable=True)
posted_at = Column(DateTime(timezone=True), nullable=True)
series_name = Column(String(255), nullable=True, index=True)
series_order = Column(Integer, nullable=True)
target_platforms = Column(ARRAY(String), nullable=True)
ai_suggestion_data = Column(JSONB, nullable=True)
planning_status = Column(String(50), default=PlanningStatus.NONE.value, index=True)
```

### 2.3 AI Suggestion Data Schema

- [ ] **2.3.1** Define the JSON schema for `ai_suggestion_data`

```python
# File: backend/app/schemas/ai_suggestion_data.py
# Type: NEW FILE

"""
Schema for AI-generated suggestion data stored in videos.ai_suggestion_data
"""

from typing import Optional, List
from pydantic import BaseModel

class AISuggestionData(BaseModel):
    """Complete AI-generated suggestion stored with planned video."""
    
    # Core content
    title: str
    description: str
    hook: str
    script_outline: str
    
    # Metadata
    hashtags: List[str]
    estimated_duration_seconds: int
    
    # Style guidance
    visual_style: str           # e.g., "modern, fast-paced, colorful"
    tone: str                   # e.g., "educational, friendly, energetic"
    target_audience: str        # e.g., "beginner developers, 18-35"
    
    # Platform recommendations
    recommended_platforms: List[str]
    platform_specific_notes: Optional[dict] = None
    
    # Generation context
    based_on_analytics: bool    # True if analytics-based, False if trend-based
    source_data: Optional[dict] = None  # Analytics or trend data used
    
    # Series info (if part of series)
    is_series: bool = False
    series_total_parts: Optional[int] = None
    series_theme: Optional[str] = None

class VideoSeriesPlan(BaseModel):
    """Plan for a video series."""
    series_name: str
    series_description: str
    total_parts: int
    videos: List[AISuggestionData]
    schedule: List[dict]  # [{video_index: 0, scheduled_time: datetime}, ...]

class MonthlyContentPlan(BaseModel):
    """Monthly content plan with multiple videos."""
    month: str  # e.g., "February 2026"
    plan_type: str  # "variety", "single_series", "multiple_series"
    total_videos: int
    videos: List[AISuggestionData]
    schedule: List[dict]
```

### 2.4 Create AI Chat Session Table

- [ ] **2.4.1** Create table to store chat sessions (for context within session)

```python
# File: backend/alembic/versions/xxx_create_ai_chat_sessions.py
# Type: NEW FILE

"""
Migration: Create AI chat sessions table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

def upgrade():
    op.create_table(
        'ai_chat_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('suggestion_context', JSONB, nullable=True),  # Current suggestion being discussed
        sa.Column('messages', JSONB, default=[]),  # Chat history
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_ai_chat_sessions_user_id', 'ai_chat_sessions', ['user_id'])
    op.create_index('ix_ai_chat_sessions_is_active', 'ai_chat_sessions', ['is_active'])

def downgrade():
    op.drop_table('ai_chat_sessions')
```

- [ ] **2.4.2** Create SQLAlchemy model for chat sessions

```python
# File: backend/app/models/ai_chat_session.py
# Type: NEW FILE

"""
AI Chat Session Model

Stores chat conversation context for AI suggestions feature.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

class AIChatSession(Base):
    """Model for AI chat sessions."""
    
    __tablename__ = "ai_chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    suggestion_context = Column(JSONB, nullable=True)  # Current suggestion
    messages = Column(JSONB, default=[])  # List of {role, content, timestamp}
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="ai_chat_sessions")
```

---

## 3. Backend API Changes

### 3.1 New Suggestion Generation Endpoint

- [ ] **3.1.1** Create endpoint to generate AI suggestion with data check

```python
# File: backend/app/api/v1/endpoints/suggestions.py
# Type: MODIFY EXISTING - Add new endpoint

@router.post("/generate-smart", response_model=SmartSuggestionResponse)
async def generate_smart_suggestion(
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Generate a smart AI suggestion based on user data.
    
    - Checks data sufficiency (≥3 posts, ≥3 days, ≥20 engagement)
    - If sufficient: analyzes user's analytics for personalized suggestion
    - If insufficient: uses trending topics and general ideas
    
    Returns complete suggestion with all video generation details.
    """
    # Check OpenAI integration
    integration_service = IntegrationsService(db)
    openai_key = await integration_service.get_user_api_key(current_user.id, "openai")
    if not openai_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI integration not configured. Please add your API key in Settings > Integrations."
        )
    
    # Generate suggestion
    ai_service = AISuggestionGenerator(db, openai_key)
    suggestion = await ai_service.generate_suggestion(current_user.id)
    
    # Create chat session with this suggestion as context
    chat_session = create_chat_session(db, current_user.id, suggestion)
    
    return SmartSuggestionResponse(
        suggestion=suggestion,
        chat_session_id=chat_session.id,
        data_source=suggestion.based_on_analytics and "analytics" or "trends",
    )
```

### 3.2 Chat Endpoints

- [ ] **3.2.1** Create chat message endpoint

```python
# File: backend/app/api/v1/endpoints/ai_chat.py
# Type: NEW FILE

"""
AI Chat API Endpoints

Endpoints for conversational AI interaction on suggestions page.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.auth import require_premium
from app.models.user import User
from app.services.ai_chat import AIChatService
from app.schemas.ai_chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
)

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])


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
    - Clarifying questions
    """
    chat_service = AIChatService(db)
    response = await chat_service.process_message(
        session_id=session_id,
        user_id=current_user.id,
        message=request.message,
    )
    return response


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get chat session details and history."""
    chat_service = AIChatService(db)
    session = chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.post("/sessions/{session_id}/end")
async def end_chat_session(
    session_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """End/close a chat session."""
    chat_service = AIChatService(db)
    chat_service.end_session(session_id, current_user.id)
    return {"message": "Session ended"}
```

### 3.3 Video Planning Endpoints

- [ ] **3.3.1** Create endpoints for scheduling and planning

```python
# File: backend/app/api/v1/endpoints/video_planning.py
# Type: NEW FILE

"""
Video Planning API Endpoints

Endpoints for scheduling videos and creating content plans.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.core.auth import require_premium
from app.models.user import User
from app.services.video_planning import VideoPlanningService
from app.schemas.video_planning import (
    ScheduleVideoRequest,
    ScheduleVideoResponse,
    CreateSeriesRequest,
    CreateSeriesResponse,
    CreateMonthlyPlanRequest,
    CreateMonthlyPlanResponse,
    PlannedVideoResponse,
    UpdatePlannedVideoRequest,
)

router = APIRouter(prefix="/video-planning", tags=["Video Planning"])


@router.post("/schedule", response_model=ScheduleVideoResponse)
async def schedule_video(
    request: ScheduleVideoRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Schedule a single video for future generation and posting.
    
    Creates a planned video entry that will be:
    1. Generated 1 hour before scheduled_post_time
    2. Posted at scheduled_post_time to specified platforms
    """
    service = VideoPlanningService(db)
    video = await service.schedule_video(
        user_id=current_user.id,
        suggestion_data=request.suggestion_data,
        scheduled_post_time=request.scheduled_post_time,
        target_platforms=request.target_platforms,
    )
    return ScheduleVideoResponse(video=video)


@router.post("/series", response_model=CreateSeriesResponse)
async def create_video_series(
    request: CreateSeriesRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Create a video series with multiple scheduled parts.
    
    Creates multiple planned video entries with:
    - Shared series_name
    - Sequential series_order (1, 2, 3...)
    - Individual scheduled times
    """
    service = VideoPlanningService(db)
    videos = await service.create_series(
        user_id=current_user.id,
        series_name=request.series_name,
        videos=request.videos,
        schedule=request.schedule,
    )
    return CreateSeriesResponse(series_name=request.series_name, videos=videos)


@router.post("/monthly-plan", response_model=CreateMonthlyPlanResponse)
async def create_monthly_plan(
    request: CreateMonthlyPlanRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Create a monthly content plan with multiple videos.
    """
    service = VideoPlanningService(db)
    videos = await service.create_monthly_plan(
        user_id=current_user.id,
        plan=request.plan,
    )
    return CreateMonthlyPlanResponse(month=request.plan.month, videos=videos)


@router.get("/planned", response_model=List[PlannedVideoResponse])
async def get_planned_videos(
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get all planned/scheduled videos for the user."""
    service = VideoPlanningService(db)
    return service.get_planned_videos(current_user.id)


@router.patch("/planned/{video_id}", response_model=PlannedVideoResponse)
async def update_planned_video(
    video_id: UUID,
    request: UpdatePlannedVideoRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Update a planned video (reschedule, edit details, change platforms)."""
    service = VideoPlanningService(db)
    video = await service.update_planned_video(
        video_id=video_id,
        user_id=current_user.id,
        updates=request,
    )
    return video


@router.delete("/planned/{video_id}")
async def delete_planned_video(
    video_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Delete a planned video."""
    service = VideoPlanningService(db)
    await service.delete_planned_video(video_id, current_user.id)
    return {"message": "Planned video deleted"}


@router.post("/planned/{video_id}/generate-now")
async def trigger_generation_now(
    video_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Manually trigger generation for a planned video."""
    service = VideoPlanningService(db)
    job_id = await service.trigger_generation(video_id, current_user.id)
    return {"message": "Generation started", "job_id": job_id}
```

### 3.4 Register New Routers

- [ ] **3.4.1** Add new routers to API

```python
# File: backend/app/api/v1/api.py
# Type: MODIFY EXISTING

from app.api.v1.endpoints import ai_chat, video_planning

# Add to router includes:
api_router.include_router(ai_chat.router)
api_router.include_router(video_planning.router)
```

---

## 4. AI Service Implementation

### 4.1 AI Suggestion Generator Service

- [ ] **4.1.1** Create comprehensive AI suggestion generator

```python
# File: backend/app/services/ai_suggestion_generator.py
# Type: NEW FILE

"""
AI Suggestion Generator Service

Generates intelligent video suggestions using OpenAI API.
Analyzes user analytics when available, falls back to trends otherwise.
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.models.post import Post
from app.models.analytics import Analytics
from app.models.video import Video
from app.schemas.ai_suggestion_data import AISuggestionData

logger = logging.getLogger(__name__)


class AISuggestionGenerator:
    """
    Service for generating AI-powered video suggestions.
    
    Checks data sufficiency and generates personalized suggestions
    based on analytics or falls back to trend-based suggestions.
    """
    
    # Data sufficiency thresholds
    MIN_POSTS = 3
    MIN_DAYS_HISTORY = 3
    MIN_TOTAL_ENGAGEMENT = 20
    
    def __init__(self, db: Session, openai_api_key: str):
        self.db = db
        self.client = AsyncOpenAI(api_key=openai_api_key)
    
    async def generate_suggestion(self, user_id: UUID) -> AISuggestionData:
        """
        Generate a complete video suggestion for the user.
        
        1. Check data sufficiency
        2. If sufficient: analyze analytics and generate personalized suggestion
        3. If insufficient: use trends for general suggestion
        4. Return complete suggestion with all video details
        """
        has_sufficient_data, data_stats = self._check_data_sufficiency(user_id)
        
        if has_sufficient_data:
            return await self._generate_analytics_based_suggestion(user_id, data_stats)
        else:
            return await self._generate_trend_based_suggestion(user_id)
    
    def _check_data_sufficiency(self, user_id: UUID) -> tuple[bool, dict]:
        """
        Check if user has sufficient data for analytics-based suggestions.
        
        Returns (is_sufficient, stats_dict)
        """
        # Count published posts
        post_count = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == "published"
        ).count()
        
        # Get earliest post date
        earliest_post = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == "published"
        ).order_by(Post.published_at.asc()).first()
        
        days_history = 0
        if earliest_post and earliest_post.published_at:
            days_history = (datetime.utcnow() - earliest_post.published_at).days
        
        # Sum total engagement
        total_engagement = self.db.query(
            func.coalesce(func.sum(Analytics.views), 0) +
            func.coalesce(func.sum(Analytics.likes), 0) +
            func.coalesce(func.sum(Analytics.shares), 0)
        ).join(Post).filter(Post.user_id == user_id).scalar() or 0
        
        stats = {
            "post_count": post_count,
            "days_history": days_history,
            "total_engagement": total_engagement,
        }
        
        is_sufficient = (
            post_count >= self.MIN_POSTS and
            days_history >= self.MIN_DAYS_HISTORY and
            total_engagement >= self.MIN_TOTAL_ENGAGEMENT
        )
        
        return is_sufficient, stats
    
    async def _generate_analytics_based_suggestion(
        self, user_id: UUID, stats: dict
    ) -> AISuggestionData:
        """Generate suggestion based on user's analytics data."""
        
        # Gather user's performance data
        performance_data = self._gather_performance_data(user_id)
        
        prompt = self._build_analytics_prompt(performance_data)
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        
        suggestion_data = self._parse_suggestion_response(response)
        suggestion_data.based_on_analytics = True
        suggestion_data.source_data = performance_data
        
        return suggestion_data
    
    async def _generate_trend_based_suggestion(self, user_id: UUID) -> AISuggestionData:
        """Generate suggestion based on current trends."""
        
        # Fetch trending topics
        trends = await self._fetch_trends()
        
        prompt = self._build_trends_prompt(trends)
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        
        suggestion_data = self._parse_suggestion_response(response)
        suggestion_data.based_on_analytics = False
        suggestion_data.source_data = {"trends": trends}
        
        return suggestion_data
    
    def _get_system_prompt(self) -> str:
        """System prompt for suggestion generation."""
        return """You are an expert content strategist specializing in viral video content.
Your task is to generate a complete, actionable video suggestion.

You must respond with a JSON object containing:
{
    "title": "Compelling video title",
    "description": "Detailed description of what the video should cover",
    "hook": "Attention-grabbing opening line or concept (first 3 seconds)",
    "script_outline": "Bullet-point outline of the video script",
    "hashtags": ["relevant", "hashtags", "for", "discovery"],
    "estimated_duration_seconds": 60,
    "visual_style": "Description of visual style (e.g., 'fast-paced, modern, bright colors')",
    "tone": "Tone of the video (e.g., 'educational, friendly, energetic')",
    "target_audience": "Who this video is for",
    "recommended_platforms": ["youtube", "tiktok", "instagram"],
    "platform_specific_notes": {
        "youtube": "Specific notes for YouTube",
        "tiktok": "Specific notes for TikTok"
    }
}

Make suggestions that are:
- Specific and actionable
- Optimized for engagement
- Realistic to produce
- Aligned with current best practices"""
    
    def _gather_performance_data(self, user_id: UUID) -> dict:
        """Gather user's performance data for analysis."""
        # Implementation: query posts, analytics, videos
        # Return structured data about what performs well
        pass
    
    def _build_analytics_prompt(self, performance_data: dict) -> str:
        """Build prompt for analytics-based suggestion."""
        pass
    
    def _build_trends_prompt(self, trends: list) -> str:
        """Build prompt for trend-based suggestion."""
        pass
    
    async def _fetch_trends(self) -> list:
        """Fetch current trending topics."""
        pass
    
    def _parse_suggestion_response(self, response) -> AISuggestionData:
        """Parse OpenAI response into AISuggestionData."""
        pass
```

### 4.2 AI Chat Service

- [ ] **4.2.1** Create AI chat service for conversational interaction

```python
# File: backend/app/services/ai_chat.py
# Type: NEW FILE

"""
AI Chat Service

Handles conversational AI interactions for the suggestions page.
Supports refining ideas, creating series, and planning content.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.models.ai_chat_session import AIChatSession
from app.models.user import User
from app.services.integrations import IntegrationsService
from app.schemas.ai_chat import ChatMessageResponse, ActionCard

logger = logging.getLogger(__name__)


class AIChatService:
    """
    Service for AI chat functionality.
    
    Handles:
    - Processing user messages
    - Generating AI responses with context
    - Detecting intents (refine, create series, create plan)
    - Creating actionable response cards
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_message(
        self,
        session_id: UUID,
        user_id: UUID,
        message: str,
    ) -> ChatMessageResponse:
        """
        Process a user message and generate AI response.
        
        1. Load session and context
        2. Gather user data (analytics, videos, templates, trends)
        3. Detect intent from message
        4. Generate appropriate response
        5. Include action cards if applicable
        """
        # Get session
        session = self.db.query(AIChatSession).filter(
            AIChatSession.id == session_id,
            AIChatSession.user_id == user_id,
            AIChatSession.is_active == True,
        ).first()
        
        if not session:
            raise ValueError("Chat session not found or expired")
        
        # Get OpenAI key
        integration_service = IntegrationsService(self.db)
        openai_key = await integration_service.get_user_api_key(user_id, "openai")
        
        # Gather context
        context = await self._gather_user_context(user_id)
        
        # Build messages for OpenAI
        messages = self._build_chat_messages(session, message, context)
        
        # Call OpenAI
        client = AsyncOpenAI(api_key=openai_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        # Parse response
        ai_response = self._parse_chat_response(response)
        
        # Update session with new messages
        self._update_session_messages(session, message, ai_response)
        
        return ai_response
    
    async def _gather_user_context(self, user_id: UUID) -> dict:
        """Gather all relevant user context for AI."""
        return {
            "analytics": await self._get_analytics_summary(user_id),
            "recent_videos": await self._get_recent_videos(user_id),
            "templates": await self._get_user_templates(user_id),
            "trends": await self._get_current_trends(),
        }
    
    def _build_chat_messages(
        self,
        session: AIChatSession,
        new_message: str,
        context: dict,
    ) -> list:
        """Build message list for OpenAI API."""
        
        system_prompt = self._get_chat_system_prompt(session.suggestion_context, context)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in session.messages:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add new user message
        messages.append({"role": "user", "content": new_message})
        
        return messages
    
    def _get_chat_system_prompt(self, suggestion_context: dict, user_context: dict) -> str:
        """Generate system prompt for chat."""
        return f"""You are an AI content strategist assistant helping a user plan their video content.

CURRENT SUGGESTION BEING DISCUSSED:
{json.dumps(suggestion_context, indent=2)}

USER'S ANALYTICS SUMMARY:
{json.dumps(user_context.get('analytics', {}), indent=2)}

USER'S RECENT VIDEOS:
{json.dumps(user_context.get('recent_videos', []), indent=2)}

CURRENT TRENDS:
{json.dumps(user_context.get('trends', []), indent=2)}

YOUR CAPABILITIES:
1. Refine and improve the current video idea
2. Create video series (Part 1, 2, 3...) - ask clarifying questions first
3. Create monthly content plans - ask about variety vs series, number of videos
4. Schedule videos for specific times
5. Suggest optimal posting times based on analytics

RESPONSE FORMAT:
Always respond with JSON:
{{
    "message": "Your conversational response to the user",
    "action_cards": [
        {{
            "type": "single_video|series|monthly_plan|schedule",
            "title": "Action title",
            "description": "What this action does",
            "data": {{...action-specific data...}}
        }}
    ],
    "needs_clarification": true/false,
    "clarification_question": "Question if needs_clarification is true"
}}

When creating series or plans, always ask clarifying questions first:
- For series: "How many parts would you like?" "What should the focus of each part be?"
- For monthly plans: "Would you like variety or a continuous series?" "How many videos per month?"

Include action_cards only when you have enough information to create actionable items."""
    
    def _parse_chat_response(self, response) -> ChatMessageResponse:
        """Parse OpenAI response into ChatMessageResponse."""
        content = json.loads(response.choices[0].message.content)
        
        action_cards = []
        for card_data in content.get("action_cards", []):
            action_cards.append(ActionCard(
                type=card_data["type"],
                title=card_data["title"],
                description=card_data.get("description", ""),
                data=card_data.get("data", {}),
            ))
        
        return ChatMessageResponse(
            message=content["message"],
            action_cards=action_cards,
            needs_clarification=content.get("needs_clarification", False),
            clarification_question=content.get("clarification_question"),
        )
    
    def _update_session_messages(
        self,
        session: AIChatSession,
        user_message: str,
        ai_response: ChatMessageResponse,
    ):
        """Update session with new messages."""
        messages = session.messages or []
        
        messages.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        messages.append({
            "role": "assistant",
            "content": ai_response.message,
            "action_cards": [card.dict() for card in ai_response.action_cards],
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        session.messages = messages
        self.db.commit()
```

---

## 5. Background Job System

### 5.1 Video Generation Scheduler Job

- [ ] **5.1.1** Create scheduled job for video generation

```python
# File: backend/app/workers/video_scheduler.py
# Type: NEW FILE

"""
Video Scheduler Worker

Background job that:
1. Runs every 15 minutes
2. Finds videos scheduled within the next hour
3. Triggers video generation for them
4. Handles failures and notifications
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import SessionLocal
from app.models.video import Video, PlanningStatus
from app.models.user import User
from app.services.video_generation import VideoGenerationService
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)


def check_and_trigger_scheduled_videos() -> dict:
    """
    Main job: Check for videos due within 1 hour and trigger generation.
    
    This job runs every 15 minutes.
    
    Returns:
        Dictionary with job results
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        one_hour_ahead = now + timedelta(hours=1)
        
        # Find videos that:
        # - Have planning_status = 'planned'
        # - Have scheduled_post_time within the next hour
        # - Haven't had generation triggered yet
        videos_to_generate = db.query(Video).filter(
            and_(
                Video.planning_status == PlanningStatus.PLANNED.value,
                Video.scheduled_post_time <= one_hour_ahead,
                Video.scheduled_post_time > now,
                Video.generation_triggered_at.is_(None),
            )
        ).all()
        
        results = {
            "checked_at": now.isoformat(),
            "videos_found": len(videos_to_generate),
            "triggered": 0,
            "failed": 0,
            "details": [],
        }
        
        for video in videos_to_generate:
            try:
                # Mark generation as triggered
                video.planning_status = PlanningStatus.GENERATING.value
                video.generation_triggered_at = now
                db.commit()
                
                # Queue video generation job
                job_id = queue_video_generation(
                    video_id=str(video.id),
                    user_id=str(video.user_id),
                    ai_suggestion_data=video.ai_suggestion_data,
                )
                
                results["triggered"] += 1
                results["details"].append({
                    "video_id": str(video.id),
                    "scheduled_for": video.scheduled_post_time.isoformat(),
                    "job_id": job_id,
                })
                
                logger.info(f"Triggered generation for video {video.id}, job {job_id}")
                
            except Exception as e:
                logger.error(f"Failed to trigger generation for video {video.id}: {e}")
                video.planning_status = PlanningStatus.FAILED.value
                db.commit()
                
                # Notify user of failure
                notify_generation_failure(db, video, str(e))
                
                results["failed"] += 1
                results["details"].append({
                    "video_id": str(video.id),
                    "error": str(e),
                })
        
        logger.info(f"Scheduler job completed: {results}")
        return results
        
    except Exception as e:
        logger.exception(f"Scheduler job failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def queue_video_generation(video_id: str, user_id: str, ai_suggestion_data: dict) -> str:
    """Queue a video generation job."""
    from redis import Redis
    from rq import Queue
    from app.core.config import get_settings
    from app.workers.video_generation_worker import generate_planned_video_job
    
    settings = get_settings()
    redis_conn = Redis.from_url(settings.REDIS_URL)
    queue = Queue("video_generation", connection=redis_conn)
    
    job = queue.enqueue(
        generate_planned_video_job,
        video_id,
        user_id,
        ai_suggestion_data,
        job_timeout=1800,  # 30 minutes
    )
    
    return job.id


def notify_generation_failure(db: Session, video: Video, error: str):
    """Send notification for generation failure."""
    notification_service = NotificationService(db)
    notification_service.create_notification(
        user_id=video.user_id,
        type="video_generation_failed",
        title="Video Generation Failed",
        message=f"Failed to generate scheduled video '{video.ai_suggestion_data.get('title', 'Untitled')}'. Error: {error}",
        data={
            "video_id": str(video.id),
            "scheduled_time": video.scheduled_post_time.isoformat() if video.scheduled_post_time else None,
        },
    )


def check_and_post_ready_videos() -> dict:
    """
    Secondary job: Check for generated videos ready to post.
    
    Finds videos that:
    - Have planning_status = 'ready'
    - Have scheduled_post_time <= now
    - Posts them to target platforms
    """
    db = SessionLocal()
    
    try:
        now = datetime.utcnow()
        
        videos_to_post = db.query(Video).filter(
            and_(
                Video.planning_status == PlanningStatus.READY.value,
                Video.scheduled_post_time <= now,
            )
        ).all()
        
        results = {
            "videos_to_post": len(videos_to_post),
            "posted": 0,
            "failed": 0,
        }
        
        for video in videos_to_post:
            try:
                video.planning_status = PlanningStatus.POSTING.value
                db.commit()
                
                # Queue posting job
                queue_video_posting(
                    video_id=str(video.id),
                    user_id=str(video.user_id),
                    target_platforms=video.target_platforms,
                )
                
                results["posted"] += 1
                
            except Exception as e:
                logger.error(f"Failed to queue posting for video {video.id}: {e}")
                video.planning_status = PlanningStatus.FAILED.value
                db.commit()
                notify_posting_failure(db, video, str(e))
                results["failed"] += 1
        
        return results
        
    finally:
        db.close()
```

### 5.2 Video Generation Worker for Planned Videos

- [ ] **5.2.1** Create worker for generating planned videos

```python
# File: backend/app/workers/video_generation_worker.py
# Type: MODIFY EXISTING - Add new function

def generate_planned_video_job(video_id: str, user_id: str, ai_suggestion_data: dict) -> dict:
    """
    Generate a planned/scheduled video.
    
    This is called by the scheduler when a video is due within 1 hour.
    Uses the ai_suggestion_data to drive the generation process.
    
    Args:
        video_id: UUID of the planned video
        user_id: UUID of the user
        ai_suggestion_data: Complete suggestion data for generation
        
    Returns:
        Dictionary with generation results
    """
    db = SessionLocal()
    
    try:
        video_uuid = UUID(video_id)
        user_uuid = UUID(user_id)
        
        # Get video record
        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            return {"success": False, "error": "Video not found"}
        
        # Get user's integrations for generation
        user = db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Use existing video generation pipeline with ai_suggestion_data
        generation_service = VideoGenerationService(db)
        result = await generation_service.generate_from_suggestion(
            video=video,
            user=user,
            suggestion_data=ai_suggestion_data,
        )
        
        if result["success"]:
            video.planning_status = PlanningStatus.READY.value
            video.video_url = result["video_url"]
            video.thumbnail_url = result.get("thumbnail_url")
            video.duration = result.get("duration")
            db.commit()
            
            return {
                "success": True,
                "video_id": video_id,
                "video_url": result["video_url"],
            }
        else:
            video.planning_status = PlanningStatus.FAILED.value
            db.commit()
            
            # Notify user
            notify_generation_failure(db, video, result.get("error", "Unknown error"))
            
            return {
                "success": False,
                "video_id": video_id,
                "error": result.get("error"),
            }
            
    except Exception as e:
        logger.exception(f"Planned video generation failed: {e}")
        
        # Update video status
        try:
            video = db.query(Video).filter(Video.id == UUID(video_id)).first()
            if video:
                video.planning_status = PlanningStatus.FAILED.value
                db.commit()
                notify_generation_failure(db, video, str(e))
        except:
            pass
        
        return {"success": False, "error": str(e)}
    finally:
        db.close()
```

### 5.3 Register Scheduled Jobs

- [ ] **5.3.1** Configure periodic job execution

```python
# File: backend/app/workers/scheduler_config.py
# Type: NEW FILE

"""
Scheduler Configuration

Configures periodic jobs using RQ Scheduler or similar.
"""

from datetime import timedelta
from rq_scheduler import Scheduler
from redis import Redis
from app.core.config import get_settings

def setup_scheduler():
    """Set up periodic jobs."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.REDIS_URL)
    scheduler = Scheduler(connection=redis_conn)
    
    # Clear existing jobs (for redeployment)
    for job in scheduler.get_jobs():
        scheduler.cancel(job)
    
    # Schedule video generation check - every 15 minutes
    scheduler.schedule(
        scheduled_time=timedelta(minutes=15),
        func='app.workers.video_scheduler:check_and_trigger_scheduled_videos',
        interval=900,  # 15 minutes in seconds
        repeat=None,  # Repeat forever
        queue_name='scheduler',
    )
    
    # Schedule posting check - every 5 minutes
    scheduler.schedule(
        scheduled_time=timedelta(minutes=5),
        func='app.workers.video_scheduler:check_and_post_ready_videos',
        interval=300,  # 5 minutes in seconds
        repeat=None,
        queue_name='scheduler',
    )
    
    return scheduler
```

---

## 6. Frontend Changes

### 6.1 New Types and Interfaces

- [ ] **6.1.1** Add TypeScript types for new features

```typescript
// File: frontend/src/types/index.ts
// Type: MODIFY EXISTING - Add new types

// AI Suggestion types
export interface AISuggestionData {
  title: string;
  description: string;
  hook: string;
  script_outline: string;
  hashtags: string[];
  estimated_duration_seconds: number;
  visual_style: string;
  tone: string;
  target_audience: string;
  recommended_platforms: string[];
  platform_specific_notes?: Record<string, string>;
  based_on_analytics: boolean;
  source_data?: Record<string, any>;
  is_series?: boolean;
  series_total_parts?: number;
  series_theme?: string;
}

export interface SmartSuggestionResponse {
  suggestion: AISuggestionData;
  chat_session_id: string;
  data_source: 'analytics' | 'trends';
}

// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  action_cards?: ActionCard[];
}

export interface ActionCard {
  type: 'single_video' | 'series' | 'monthly_plan' | 'schedule';
  title: string;
  description: string;
  data: Record<string, any>;
}

export interface ChatMessageResponse {
  message: string;
  action_cards: ActionCard[];
  needs_clarification: boolean;
  clarification_question?: string;
}

// Planning types
export type PlanningStatus = 'none' | 'planned' | 'generating' | 'ready' | 'posting' | 'posted' | 'failed';

export interface PlannedVideo {
  id: string;
  title: string;
  planning_status: PlanningStatus;
  scheduled_post_time: string;
  target_platforms: string[];
  series_name?: string;
  series_order?: number;
  ai_suggestion_data: AISuggestionData;
  created_at: string;
}
```

### 6.2 New API Services

- [ ] **6.2.1** Create AI chat service

```typescript
// File: frontend/src/services/aiChat.ts
// Type: NEW FILE

/**
 * AI Chat Service
 * 
 * API client for AI chat functionality.
 */

import { apiClient } from "@/lib/api";
import type { ChatMessageResponse, ChatMessage } from "@/types";

export interface ChatSession {
  id: string;
  suggestion_context: Record<string, any>;
  messages: ChatMessage[];
  is_active: boolean;
  created_at: string;
}

export const aiChatService = {
  /**
   * Send a message in a chat session.
   */
  sendMessage: (sessionId: string, message: string) =>
    apiClient.post<ChatMessageResponse>(`/ai-chat/sessions/${sessionId}/messages`, {
      message,
    }),

  /**
   * Get chat session details.
   */
  getSession: (sessionId: string) =>
    apiClient.get<ChatSession>(`/ai-chat/sessions/${sessionId}`),

  /**
   * End a chat session.
   */
  endSession: (sessionId: string) =>
    apiClient.post<{ message: string }>(`/ai-chat/sessions/${sessionId}/end`),
};
```

- [ ] **6.2.2** Create video planning service

```typescript
// File: frontend/src/services/videoPlanning.ts
// Type: NEW FILE

/**
 * Video Planning Service
 * 
 * API client for video scheduling and planning.
 */

import { apiClient } from "@/lib/api";
import type { AISuggestionData, PlannedVideo } from "@/types";

export interface ScheduleVideoRequest {
  suggestion_data: AISuggestionData;
  scheduled_post_time: string;
  target_platforms: string[];
}

export interface CreateSeriesRequest {
  series_name: string;
  videos: AISuggestionData[];
  schedule: Array<{ video_index: number; scheduled_time: string }>;
}

export const videoPlanningService = {
  /**
   * Schedule a single video.
   */
  scheduleVideo: (request: ScheduleVideoRequest) =>
    apiClient.post<{ video: PlannedVideo }>("/video-planning/schedule", request),

  /**
   * Create a video series.
   */
  createSeries: (request: CreateSeriesRequest) =>
    apiClient.post<{ series_name: string; videos: PlannedVideo[] }>(
      "/video-planning/series",
      request
    ),

  /**
   * Get all planned videos.
   */
  getPlannedVideos: () =>
    apiClient.get<PlannedVideo[]>("/video-planning/planned"),

  /**
   * Update a planned video.
   */
  updatePlannedVideo: (videoId: string, updates: Partial<PlannedVideo>) =>
    apiClient.patch<PlannedVideo>(`/video-planning/planned/${videoId}`, updates),

  /**
   * Delete a planned video.
   */
  deletePlannedVideo: (videoId: string) =>
    apiClient.delete(`/video-planning/planned/${videoId}`),

  /**
   * Trigger immediate generation.
   */
  generateNow: (videoId: string) =>
    apiClient.post<{ message: string; job_id: string }>(
      `/video-planning/planned/${videoId}/generate-now`
    ),
};
```

- [ ] **6.2.3** Update suggestions service

```typescript
// File: frontend/src/services/suggestions.ts
// Type: MODIFY EXISTING - Add new method

/**
 * Generate a smart AI suggestion.
 */
generateSmart: () =>
  apiClient.post<SmartSuggestionResponse>("/suggestions/generate-smart"),
```

### 6.3 New React Hooks

- [ ] **6.3.1** Create hooks for new features

```typescript
// File: frontend/src/hooks/useAIChat.ts
// Type: NEW FILE

/**
 * AI Chat Hooks
 * 
 * React Query hooks for AI chat functionality.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiChatService } from "@/services/aiChat";

export const aiChatKeys = {
  all: ["ai-chat"] as const,
  session: (id: string) => [...aiChatKeys.all, "session", id] as const,
};

export function useChatSession(sessionId: string | null) {
  return useQuery({
    queryKey: aiChatKeys.session(sessionId || ""),
    queryFn: () => aiChatService.getSession(sessionId!),
    enabled: !!sessionId,
  });
}

export function useSendChatMessage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (message: string) => aiChatService.sendMessage(sessionId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiChatKeys.session(sessionId) });
    },
  });
}

export function useEndChatSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => aiChatService.endSession(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: aiChatKeys.session(sessionId) });
    },
  });
}
```

- [ ] **6.3.2** Create hooks for video planning

```typescript
// File: frontend/src/hooks/useVideoPlanning.ts
// Type: NEW FILE

/**
 * Video Planning Hooks
 * 
 * React Query hooks for video scheduling and planning.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { videoPlanningService } from "@/services/videoPlanning";
import type { ScheduleVideoRequest, CreateSeriesRequest } from "@/services/videoPlanning";

export const videoPlanningKeys = {
  all: ["video-planning"] as const,
  planned: () => [...videoPlanningKeys.all, "planned"] as const,
};

export function usePlannedVideos() {
  return useQuery({
    queryKey: videoPlanningKeys.planned(),
    queryFn: () => videoPlanningService.getPlannedVideos(),
    staleTime: 30 * 1000,
  });
}

export function useScheduleVideo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ScheduleVideoRequest) =>
      videoPlanningService.scheduleVideo(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.planned() });
    },
  });
}

export function useCreateSeries() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateSeriesRequest) =>
      videoPlanningService.createSeries(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.planned() });
    },
  });
}

export function useDeletePlannedVideo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (videoId: string) => videoPlanningService.deletePlannedVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.planned() });
    },
  });
}

export function useGenerateVideoNow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (videoId: string) => videoPlanningService.generateNow(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: videoPlanningKeys.planned() });
    },
  });
}
```

### 6.4 Update Suggestions Page

- [ ] **6.4.1** Create new SuggestionsPage with chat interface

```tsx
// File: frontend/src/pages/dashboard/SuggestionsPage.tsx
// Type: REWRITE - Major changes

/**
 * Suggestions Page
 * 
 * Enhanced AI-powered suggestions with:
 * - Smart suggestion generation (analytics or trends based)
 * - Interactive chat interface
 * - Video series and monthly plan creation
 * - Direct scheduling capabilities
 */

import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
// ... imports ...

export default function SuggestionsPage() {
  const isPremium = useIsPremium();
  const [currentSuggestion, setCurrentSuggestion] = useState<AISuggestionData | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<'analytics' | 'trends' | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Check OpenAI integration
  const { data: integrations } = useIntegrations();
  const hasOpenAI = integrations?.some(i => i.provider === 'openai' && i.is_active);

  if (!isPremium) {
    return <PremiumGate />;
  }

  if (!hasOpenAI) {
    return <OpenAISetupPrompt />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Suggestions</h1>
          <p className="text-muted-foreground">
            Get personalized video ideas powered by AI
          </p>
        </div>
        <Button
          onClick={handleGenerateSuggestion}
          disabled={isGenerating}
          size="lg"
        >
          {isGenerating ? (
            <AIThinkingIndicator />
          ) : (
            <>
              <Sparkles className="mr-2 h-5 w-5" />
              Generate Suggestion
            </>
          )}
        </Button>
      </div>

      {/* Suggestion Card */}
      {currentSuggestion && (
        <SuggestionCard
          suggestion={currentSuggestion}
          dataSource={dataSource}
          onGenerateAnother={handleGenerateSuggestion}
          onGenerateVideo={handleGenerateVideo}
          onSchedule={handleSchedule}
        />
      )}

      {/* Chat Interface */}
      {chatSessionId && currentSuggestion && (
        <ChatInterface
          sessionId={chatSessionId}
          suggestion={currentSuggestion}
          onActionExecute={handleActionExecute}
        />
      )}
    </div>
  );
}
```

### 6.5 New Components

- [ ] **6.5.1** Create AI Thinking Indicator component

```tsx
// File: frontend/src/components/ai/AIThinkingIndicator.tsx
// Type: NEW FILE

/**
 * AI Thinking Indicator
 * 
 * Animated indicator shown while AI is generating.
 */

export function AIThinkingIndicator() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
        <span className="h-2 w-2 rounded-full bg-primary animate-bounce" />
      </div>
      <span className="text-sm">AI is thinking...</span>
    </div>
  );
}
```

- [ ] **6.5.2** Create Suggestion Card component

```tsx
// File: frontend/src/components/ai/SuggestionCard.tsx
// Type: NEW FILE

/**
 * Suggestion Card
 * 
 * Displays a complete AI suggestion with action buttons.
 */

// Full implementation with:
// - Title, description, hook display
// - Script outline (expandable)
// - Hashtags, duration, visual style, tone
// - Platform recommendations
// - Data source indicator (analytics vs trends)
// - Action buttons: Generate Video Now, Schedule for Later, Refine This Idea
// - Generate Another button
```

- [ ] **6.5.3** Create Chat Interface component

```tsx
// File: frontend/src/components/ai/ChatInterface.tsx
// Type: NEW FILE

/**
 * Chat Interface
 * 
 * Conversational AI interface for refining suggestions.
 */

// Full implementation with:
// - Chat message bubbles
// - AI responses with action cards
// - Message input
// - Loading state during AI response
// - Action card buttons (Schedule, Save to Calendar, etc.)
```

- [ ] **6.5.4** Create Action Card component

```tsx
// File: frontend/src/components/ai/ActionCard.tsx
// Type: NEW FILE

/**
 * Action Card
 * 
 * Actionable card within chat responses.
 */

// Full implementation with:
// - Different layouts for single_video, series, monthly_plan, schedule
// - Execute buttons
// - Preview of content
// - Expandable details
```

- [ ] **6.5.5** Create Schedule Modal component

```tsx
// File: frontend/src/components/ai/ScheduleModal.tsx
// Type: NEW FILE

/**
 * Schedule Modal
 * 
 * Modal for scheduling a video or editing schedule.
 */

// Full implementation with:
// - Date/time picker
// - Platform selection
// - Series info (if applicable)
// - Confirm/cancel buttons
```

- [ ] **6.5.6** Create OpenAI Setup Prompt component

```tsx
// File: frontend/src/components/ai/OpenAISetupPrompt.tsx
// Type: NEW FILE

/**
 * OpenAI Setup Prompt
 * 
 * Shown when user hasn't configured OpenAI integration.
 */

export function OpenAISetupPrompt() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-md text-center">
        <CardHeader>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Key className="h-8 w-8 text-muted-foreground" />
          </div>
          <CardTitle>OpenAI Integration Required</CardTitle>
          <CardDescription>
            To use AI Suggestions, please configure your OpenAI API key.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link to="/settings">
            <Button className="w-full gap-2">
              <Settings className="h-4 w-4" />
              Go to Integrations
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## 7. Calendar Page Updates

### 7.1 Update Calendar to Show Planned Videos

- [ ] **7.1.1** Modify CalendarPage to include planned videos

```tsx
// File: frontend/src/pages/dashboard/CalendarPage.tsx
// Type: MODIFY EXISTING

// Add:
// - Fetch planned videos alongside scheduled posts
// - Display planned videos with status indicators
// - Different colors/icons for planning_status
// - Click to edit planned video details
// - Drag-and-drop to reschedule
// - Quick action buttons (Generate Now, Delete, Edit)
```

- [ ] **7.1.2** Create PlannedVideoCalendarItem component

```tsx
// File: frontend/src/components/calendar/PlannedVideoCalendarItem.tsx
// Type: NEW FILE

/**
 * Planned Video Calendar Item
 * 
 * Calendar item for a planned/scheduled video.
 */

// Full implementation with:
// - Status indicator (planned, generating, ready, posting, posted, failed)
// - Series badge if part of series
// - Platform icons
// - Quick actions on hover/click
// - Drag handle for rescheduling
```

### 7.2 Add Calendar Quick Actions

- [ ] **7.2.1** Add quick action menu for planned videos

```tsx
// File: frontend/src/components/calendar/PlannedVideoActions.tsx
// Type: NEW FILE

/**
 * Quick actions for planned videos on calendar.
 */

// Actions:
// - Generate Now (if status is 'planned')
// - Edit Details
// - Reschedule
// - Delete
// - View in Suggestions (link back)
```

---

## 8. Notification System

### 8.1 Add New Notification Types

- [ ] **8.1.1** Update notification service for new types

```python
# File: backend/app/services/notifications.py
# Type: MODIFY EXISTING

# Add notification types:
# - video_posted_successfully
# - video_generation_failed
# - video_posting_failed
```

- [ ] **8.1.2** Create notification handlers for scheduled videos

```python
# File: backend/app/services/video_notifications.py
# Type: NEW FILE

"""
Video Notification Handlers

Send notifications for scheduled video events.
"""

def notify_video_posted(db: Session, video: Video, post_urls: dict):
    """Notify user when video is successfully posted."""
    notification_service = NotificationService(db)
    
    platforms_str = ", ".join(video.target_platforms)
    
    notification_service.create_notification(
        user_id=video.user_id,
        type="video_posted_successfully",
        title="Video Posted Successfully",
        message=f"Your video '{video.ai_suggestion_data.get('title')}' has been posted to {platforms_str}.",
        data={
            "video_id": str(video.id),
            "post_urls": post_urls,
        },
    )


def notify_video_failed(db: Session, video: Video, error: str, failure_type: str):
    """Notify user when video generation or posting fails."""
    notification_service = NotificationService(db)
    
    title = "Video Generation Failed" if failure_type == "generation" else "Video Posting Failed"
    
    notification_service.create_notification(
        user_id=video.user_id,
        type=f"video_{failure_type}_failed",
        title=title,
        message=f"Failed to {failure_type} your scheduled video '{video.ai_suggestion_data.get('title')}'. Error: {error}",
        data={
            "video_id": str(video.id),
            "error": error,
            "failure_type": failure_type,
        },
    )
```

---

## 9. Testing

### 9.1 Backend Tests

- [ ] **9.1.1** Test data sufficiency check

```python
# File: backend/tests/services/test_ai_suggestion_generator.py
# Type: NEW FILE

# Test cases:
# - User with sufficient data gets analytics-based suggestion
# - User with insufficient posts gets trend-based suggestion
# - User with insufficient history gets trend-based suggestion
# - User with insufficient engagement gets trend-based suggestion
```

- [ ] **9.1.2** Test AI chat service

```python
# File: backend/tests/services/test_ai_chat.py
# Type: NEW FILE

# Test cases:
# - Message processing
# - Context gathering
# - Intent detection
# - Action card generation
```

- [ ] **9.1.3** Test video scheduling

```python
# File: backend/tests/services/test_video_planning.py
# Type: NEW FILE

# Test cases:
# - Schedule single video
# - Create video series
# - Update scheduled video
# - Delete scheduled video
```

- [ ] **9.1.4** Test scheduler job

```python
# File: backend/tests/workers/test_video_scheduler.py
# Type: NEW FILE

# Test cases:
# - Job finds videos due within 1 hour
# - Job triggers generation correctly
# - Job handles failures properly
# - Posting job posts ready videos
```

### 9.2 Frontend Tests

- [ ] **9.2.1** Test SuggestionsPage

```typescript
// File: frontend/src/pages/dashboard/SuggestionsPage.test.tsx
// Type: NEW FILE

// Test cases:
// - Shows premium gate for non-premium users
// - Shows OpenAI setup prompt when not configured
// - Generate button triggers suggestion generation
// - Suggestion card displays correctly
// - Chat interface appears after generation
```

- [ ] **9.2.2** Test ChatInterface

```typescript
// File: frontend/src/components/ai/ChatInterface.test.tsx
// Type: NEW FILE

// Test cases:
// - Sends messages correctly
// - Displays responses
// - Renders action cards
// - Executes actions
```

---

## 10. Deployment

### 10.1 Database Migration

- [ ] **10.1.1** Run Alembic migrations on production

```bash
# Commands to run:
alembic upgrade head
```

### 10.2 Environment Variables

- [ ] **10.2.1** Ensure no new env vars needed (uses existing OpenAI from integrations)

### 10.3 Worker Configuration

- [ ] **10.3.1** Add new queue workers

```yaml
# Update Railway/Procfile for workers:
# - scheduler queue for periodic jobs
# - video_generation queue for generation jobs
```

- [ ] **10.3.2** Start RQ Scheduler process

```bash
# New process needed:
rqscheduler --host redis --port 6379 --db 0
```

### 10.4 Monitoring

- [ ] **10.4.1** Add logging for scheduler jobs
- [ ] **10.4.2** Monitor job queue depth
- [ ] **10.4.3** Alert on failed scheduled videos

---

## Summary

This implementation checklist covers:

1. **Database**: Extended videos table + new chat sessions table
2. **Backend APIs**: Smart suggestion, AI chat, video planning endpoints
3. **AI Services**: Suggestion generator, chat service with context
4. **Background Jobs**: 15-minute scheduler, generation triggers, posting
5. **Frontend**: New suggestion UI, chat interface, action cards
6. **Calendar**: Planned video display, drag-drop, quick actions
7. **Notifications**: Posted success, generation/posting failures
8. **Testing**: Comprehensive test coverage
9. **Deployment**: Migrations, workers, monitoring

**Estimated complexity**: Large feature (~2-3 weeks for full implementation)

**Key dependencies**:
- User must have OpenAI API key configured
- User must be premium
- Existing video generation pipeline must support suggestion-based generation
