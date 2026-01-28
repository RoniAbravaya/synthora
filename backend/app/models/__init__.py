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
    PROVIDER_RECOMMENDED_MODELS,
    PROVIDER_PRICING,
    PROVIDER_INFO,
    get_category_for_provider,
    get_providers_for_category,
)
from app.models.template import Template, TemplateCategory
from app.models.video import Video, VideoStatus, GenerationStep, PlanningStatus
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.post import Post, PostStatus
from app.models.analytics import Analytics
from app.models.ai_suggestion import AISuggestion, SuggestionType
from app.models.ai_chat_session import AIChatSession
from app.models.notification import Notification, NotificationType
from app.models.job import Job, JobType, JobStatus
from app.models.app_settings import AppSettings
from app.models.user_generation_settings import (
    UserGenerationSettings,
    SubtitleStyle,
    SUBTITLE_STYLE_CONFIGS,
)
from app.models.api_request_log import (
    APIRequestLog,
    mask_api_key,
    mask_sensitive_data,
    truncate_response,
)

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
    "PROVIDER_RECOMMENDED_MODELS",
    "PROVIDER_PRICING",
    "PROVIDER_INFO",
    "get_category_for_provider",
    "get_providers_for_category",
    
    # Template
    "Template",
    "TemplateCategory",
    
    # Video
    "Video",
    "VideoStatus",
    "GenerationStep",
    "PlanningStatus",
    
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
    
    # AI Chat Session
    "AIChatSession",
    
    # Notification
    "Notification",
    "NotificationType",
    
    # Job
    "Job",
    "JobType",
    "JobStatus",
    
    # App Settings
    "AppSettings",
    
    # User Generation Settings
    "UserGenerationSettings",
    "SubtitleStyle",
    "SUBTITLE_STYLE_CONFIGS",
    
    # API Request Log
    "APIRequestLog",
    "mask_api_key",
    "mask_sensitive_data",
    "truncate_response",
]
