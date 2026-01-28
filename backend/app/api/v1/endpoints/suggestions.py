"""
AI Suggestions API Endpoints

Endpoints for AI-powered suggestions and recommendations.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_premium
from app.models.user import User
from app.models.ai_suggestion import SuggestionType
from app.services.suggestions import SuggestionsService
from app.services.ai_analysis.posting_time import PostingTimeAnalyzer
from app.services.ai_analysis.content import ContentAnalyzer
from app.services.ai_analysis.trends import TrendAnalyzer
from app.services.ai_analysis.predictions import PerformancePredictor
from app.services.ai_analysis.improvements import ImprovementAnalyzer
from app.workers.suggestions_worker import queue_suggestions_generation
from app.schemas.suggestion import (
    SuggestionResponse,
    SuggestionListItem,
    SuggestionListResponse,
    UnreadCountResponse,
    PostingTimeResponse,
    PostingTimeAnalysis,
    ContentIdeasResponse,
    ContentIdea,
    TrendsResponse,
    TrendItem,
    PerformancePredictionResponse,
    PerformancePrediction,
    ImprovementsResponse,
    UnderperformingPost,
    ImprovementItem,
    GenerateSuggestionsResponse,
    DismissRequest,
)
from app.schemas.ai_suggestion_data import SmartSuggestionResponse
from app.services.ai_suggestion_generator import AISuggestionGenerator
from app.services.integration import IntegrationService
from app.models.integration import IntegrationProvider
from app.models.ai_chat_session import AIChatSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["AI Suggestions"])


# =============================================================================
# Suggestions List Endpoints
# =============================================================================

@router.get("", response_model=SuggestionListResponse)
async def get_suggestions(
    suggestion_type: Optional[str] = Query(default=None, description="Filter by type"),
    include_read: bool = Query(default=False, description="Include read suggestions"),
    include_dismissed: bool = Query(default=False, description="Include dismissed suggestions"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Get AI suggestions for the current user.
    
    Premium feature only.
    """
    service = SuggestionsService(db)
    
    # Parse suggestion type
    type_filter = None
    if suggestion_type:
        try:
            type_filter = SuggestionType(suggestion_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid suggestion type: {suggestion_type}",
            )
    
    suggestions = service.get_user_suggestions(
        current_user.id,
        suggestion_type=type_filter,
        include_read=include_read,
        include_dismissed=include_dismissed,
        limit=limit,
    )
    
    unread_count = service.get_unread_count(current_user.id)
    
    return SuggestionListResponse(
        suggestions=[
            SuggestionListItem(
                id=s.id,
                suggestion_type=s.suggestion_type.value,
                title=s.title,
                description=s.description,
                priority=s.priority.value,
                is_read=s.is_read,
                action_type=s.action_type,
                expires_at=s.expires_at,
                created_at=s.created_at,
            )
            for s in suggestions
        ],
        total=len(suggestions),
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get count of unread suggestions."""
    service = SuggestionsService(db)
    count = service.get_unread_count(current_user.id)
    return UnreadCountResponse(count=count)


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Get a specific suggestion by ID."""
    service = SuggestionsService(db)
    suggestion = service.get_suggestion_by_id(suggestion_id, current_user.id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )
    
    return SuggestionResponse(
        id=suggestion.id,
        suggestion_type=suggestion.suggestion_type.value,
        title=suggestion.title,
        description=suggestion.description,
        priority=suggestion.priority.value,
        action_type=suggestion.action_type,
        action_data=suggestion.action_data or {},
        is_read=suggestion.is_read,
        is_dismissed=suggestion.is_dismissed,
        is_acted=suggestion.is_acted,
        read_at=suggestion.read_at,
        dismissed_at=suggestion.dismissed_at,
        acted_at=suggestion.acted_at,
        expires_at=suggestion.expires_at,
        related_video_id=suggestion.related_video_id,
        related_post_id=suggestion.related_post_id,
        related_template_id=suggestion.related_template_id,
        metadata=suggestion.extra_data or {},
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


# =============================================================================
# Suggestion Actions
# =============================================================================

@router.post("/{suggestion_id}/read", response_model=SuggestionResponse)
async def mark_suggestion_read(
    suggestion_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Mark a suggestion as read."""
    service = SuggestionsService(db)
    suggestion = service.mark_as_read(suggestion_id, current_user.id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )
    
    return SuggestionResponse(
        id=suggestion.id,
        suggestion_type=suggestion.suggestion_type.value,
        title=suggestion.title,
        description=suggestion.description,
        priority=suggestion.priority.value,
        action_type=suggestion.action_type,
        action_data=suggestion.action_data or {},
        is_read=suggestion.is_read,
        is_dismissed=suggestion.is_dismissed,
        is_acted=suggestion.is_acted,
        read_at=suggestion.read_at,
        dismissed_at=suggestion.dismissed_at,
        acted_at=suggestion.acted_at,
        expires_at=suggestion.expires_at,
        related_video_id=suggestion.related_video_id,
        related_post_id=suggestion.related_post_id,
        related_template_id=suggestion.related_template_id,
        metadata=suggestion.extra_data or {},
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Mark all suggestions as read."""
    service = SuggestionsService(db)
    count = service.mark_all_as_read(current_user.id)
    return {"message": f"Marked {count} suggestions as read"}


@router.post("/{suggestion_id}/dismiss", response_model=SuggestionResponse)
async def dismiss_suggestion(
    suggestion_id: UUID,
    request: DismissRequest,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Dismiss a suggestion."""
    service = SuggestionsService(db)
    suggestion = service.dismiss_suggestion(suggestion_id, current_user.id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )
    
    return SuggestionResponse(
        id=suggestion.id,
        suggestion_type=suggestion.suggestion_type.value,
        title=suggestion.title,
        description=suggestion.description,
        priority=suggestion.priority.value,
        action_type=suggestion.action_type,
        action_data=suggestion.action_data or {},
        is_read=suggestion.is_read,
        is_dismissed=suggestion.is_dismissed,
        is_acted=suggestion.is_acted,
        read_at=suggestion.read_at,
        dismissed_at=suggestion.dismissed_at,
        acted_at=suggestion.acted_at,
        expires_at=suggestion.expires_at,
        related_video_id=suggestion.related_video_id,
        related_post_id=suggestion.related_post_id,
        related_template_id=suggestion.related_template_id,
        metadata=suggestion.extra_data or {},
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


@router.post("/{suggestion_id}/acted", response_model=SuggestionResponse)
async def mark_suggestion_acted(
    suggestion_id: UUID,
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """Mark that the user acted on a suggestion."""
    service = SuggestionsService(db)
    suggestion = service.mark_as_acted(suggestion_id, current_user.id)
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )
    
    return SuggestionResponse(
        id=suggestion.id,
        suggestion_type=suggestion.suggestion_type.value,
        title=suggestion.title,
        description=suggestion.description,
        priority=suggestion.priority.value,
        action_type=suggestion.action_type,
        action_data=suggestion.action_data or {},
        is_read=suggestion.is_read,
        is_dismissed=suggestion.is_dismissed,
        is_acted=suggestion.is_acted,
        read_at=suggestion.read_at,
        dismissed_at=suggestion.dismissed_at,
        acted_at=suggestion.acted_at,
        expires_at=suggestion.expires_at,
        related_video_id=suggestion.related_video_id,
        related_post_id=suggestion.related_post_id,
        related_template_id=suggestion.related_template_id,
        metadata=suggestion.extra_data or {},
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


# =============================================================================
# Analysis Endpoints
# =============================================================================

@router.get("/analysis/posting-times", response_model=PostingTimeResponse)
async def analyze_posting_times(
    days: int = Query(default=90, ge=30, le=365, description="Days to analyze"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Analyze posting times and get recommendations.
    
    Returns optimal posting times based on historical performance.
    """
    analyzer = PostingTimeAnalyzer(db)
    result = analyzer.analyze_user_posting_times(current_user.id, days)
    
    overall = None
    if result.get("overall"):
        overall = PostingTimeAnalysis(**result["overall"])
    
    return PostingTimeResponse(
        success=result.get("success", False),
        posts_analyzed=result.get("posts_analyzed", 0),
        period_days=result.get("period_days", days),
        overall=overall,
        by_platform=result.get("by_platform", {}),
        error=result.get("reason"),
    )


@router.get("/analysis/content-ideas", response_model=ContentIdeasResponse)
async def get_content_ideas(
    count: int = Query(default=5, ge=1, le=10, description="Number of ideas"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Get AI-generated content ideas based on performance data.
    """
    analyzer = ContentAnalyzer(db)
    ideas = await analyzer.generate_content_ideas(current_user.id, count)
    
    return ContentIdeasResponse(
        ideas=[
            ContentIdea(
                topic=idea.get("topic", ""),
                hook=idea.get("hook", ""),
                description=idea.get("description", ""),
                suggested_hashtags=idea.get("suggested_hashtags", []),
                estimated_engagement=idea.get("estimated_engagement", "medium"),
            )
            for idea in ideas
        ]
    )


@router.get("/analysis/trends", response_model=TrendsResponse)
async def get_trending_topics(
    category: Optional[str] = Query(default=None, description="Category filter"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Get trending topics matched to user's content niche.
    """
    analyzer = TrendAnalyzer(db)
    trends = await analyzer.fetch_trending_topics(category)
    matched = await analyzer.match_trends_to_user(current_user.id, trends)
    
    return TrendsResponse(
        trends=[
            TrendItem(
                topic=t.get("topic", ""),
                description=t.get("description", ""),
                platforms=t.get("platforms", []),
                virality_score=t.get("virality_score", 5),
                suggested_angle=t.get("suggested_angle", ""),
                relevance_score=t.get("relevance_score"),
            )
            for t in matched
        ]
    )


@router.get("/analysis/predict/{video_id}", response_model=PerformancePredictionResponse)
async def predict_video_performance(
    video_id: UUID,
    platforms: str = Query(description="Comma-separated platforms"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Predict performance for a video before posting.
    """
    target_platforms = [p.strip() for p in platforms.split(",")]
    
    predictor = PerformancePredictor(db)
    result = predictor.predict_video_performance(
        current_user.id,
        video_id,
        target_platforms,
    )
    
    if not result.get("success"):
        return PerformancePredictionResponse(
            success=False,
            error=result.get("error"),
        )
    
    return PerformancePredictionResponse(
        success=True,
        prediction=PerformancePrediction(
            video_id=str(video_id),
            predictions=result["predictions"],
            total_predicted_views=result["total_predicted_views"],
            avg_predicted_engagement=result["avg_predicted_engagement"],
            confidence=result["confidence"],
            factors=result["factors"],
            based_on_posts=result["based_on_posts"],
        ),
    )


@router.get("/analysis/improvements", response_model=ImprovementsResponse)
async def analyze_improvements(
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Analyze underperforming content and suggest improvements.
    """
    analyzer = ImprovementAnalyzer(db)
    underperforming = await analyzer.analyze_underperforming_content(current_user.id)
    
    return ImprovementsResponse(
        underperforming_posts=[
            UnderperformingPost(
                post_id=item["post_id"],
                title=item.get("title"),
                current_engagement=item["current_engagement"],
                improvements=[
                    ImprovementItem(
                        category=imp.get("category", "general"),
                        issue=imp.get("issue", ""),
                        suggestion=imp.get("suggestion", ""),
                        impact=imp.get("impact", "medium"),
                    )
                    for imp in item.get("improvements", [])
                ],
            )
            for item in underperforming
        ]
    )


# =============================================================================
# Generation Endpoints
# =============================================================================

@router.post("/generate", response_model=GenerateSuggestionsResponse)
async def generate_suggestions(
    current_user: User = Depends(require_premium),
):
    """
    Trigger generation of all AI suggestions.
    
    Queues a background job to generate suggestions based on user data.
    """
    job_id = queue_suggestions_generation(current_user.id)
    
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue suggestions generation",
        )
    
    return GenerateSuggestionsResponse(
        message="Suggestions generation queued successfully",
        job_id=job_id,
        estimated_time="2-5 minutes",
    )


@router.post("/generate-smart", response_model=SmartSuggestionResponse)
async def generate_smart_suggestion(
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db),
):
    """
    Generate a smart AI suggestion based on user data.
    
    This endpoint:
    1. Checks data sufficiency (≥3 posts, ≥3 days history, ≥20 engagement)
    2. If sufficient: analyzes user's analytics for personalized suggestion
    3. If insufficient: uses trending topics and general ideas
    4. Creates a chat session for follow-up conversation
    5. Returns complete suggestion with all video generation details
    
    Requires OpenAI integration to be configured.
    """
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
    
    # Generate suggestion
    generator = AISuggestionGenerator(db, openai_key)
    
    try:
        suggestion, data_source, data_stats = await generator.generate_suggestion(current_user.id)
    except Exception as e:
        logger.exception(f"Smart suggestion generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestion: {str(e)}",
        )
    
    # Create chat session with this suggestion as context
    import uuid
    chat_session = AIChatSession(
        id=uuid.uuid4(),
        user_id=current_user.id,
        suggestion_context=suggestion.model_dump(),
        messages=[
            {
                "role": "assistant",
                "content": f"I've created a video suggestion for you based on {'your analytics data' if data_source == 'analytics' else 'current trends'}. The idea is: **{suggestion.title}**\n\n{suggestion.description}\n\nWould you like to:\n- Generate this video now\n- Schedule it for later\n- Refine the idea\n- Create a video series on this topic\n- Create a monthly content plan",
                "timestamp": str(uuid.uuid4()),  # Will be replaced with actual timestamp
            }
        ],
        is_active=True,
    )
    
    from datetime import datetime
    chat_session.messages[0]["timestamp"] = datetime.utcnow().isoformat()
    
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    
    return SmartSuggestionResponse(
        suggestion=suggestion,
        chat_session_id=chat_session.id,
        data_source=data_source,
        data_stats=data_stats,
    )
