"""
Synthora Database Models

This module exports all SQLAlchemy models for the application.
Import models from here to ensure they're registered with SQLAlchemy.
"""

from app.models.user import User, UserRole
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.integration import (
    Integration,
    IntegrationProvider,
    IntegrationCategory,
    PROVIDER_CATEGORIES,
)
from app.models.template import (
    Template,
    TemplateCategory,
    AspectRatio,
    HookStyle,
    NarrativeStructure,
    Pacing,
    VisualAesthetic,
    VoiceTone,
    MusicMood,
    CTAType,
)
from app.models.video import Video, VideoStatus, GenerationStep
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.post import Post, PostStatus
from app.models.analytics import Analytics
from app.models.ai_suggestion import AISuggestion, SuggestionType
from app.models.notification import Notification, NotificationType
from app.models.job import Job, JobType, JobStatus
from app.models.app_settings import AppSettings

# Export all models and enums
__all__ = [
    # User
    "User",
    "UserRole",
    
    # Subscription
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    
    # Integration
    "Integration",
    "IntegrationProvider",
    "IntegrationCategory",
    "PROVIDER_CATEGORIES",
    
    # Template
    "Template",
    "TemplateCategory",
    "AspectRatio",
    "HookStyle",
    "NarrativeStructure",
    "Pacing",
    "VisualAesthetic",
    "VoiceTone",
    "MusicMood",
    "CTAType",
    
    # Video
    "Video",
    "VideoStatus",
    "GenerationStep",
    
    # Social Account
    "SocialAccount",
    "SocialPlatform",
    
    # Post
    "Post",
    "PostStatus",
    
    # Analytics
    "Analytics",
    
    # AI Suggestion
    "AISuggestion",
    "SuggestionType",
    
    # Notification
    "Notification",
    "NotificationType",
    
    # Job
    "Job",
    "JobType",
    "JobStatus",
    
    # App Settings
    "AppSettings",
]
