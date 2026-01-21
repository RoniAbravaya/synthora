"""
Synthora Pydantic Schemas

This module exports all Pydantic schemas for request/response validation.
"""

from app.schemas.common import (
    BaseSchema,
    TimestampSchema,
    IDSchema,
    PaginationParams,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    SuccessResponse,
    HealthResponse,
    MessageResponse,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    RoleUpdate,
    StatusUpdate,
    UserResponse,
    UserProfileResponse,
    UserListResponse,
    UserStatsResponse,
    FirebaseTokenRequest,
    LoginResponse,
    SetupStatusResponse,
)
from app.schemas.subscription import (
    SubscriptionResponse,
    SubscriptionStatusResponse,
    PlanFeatures,
    PlanInfo,
    PlansResponse,
    CheckoutRequest,
    CheckoutResponse,
    PortalResponse,
    WebhookResponse,
)
from app.schemas.integration import (
    IntegrationResponse,
    IntegrationRevealResponse,
    AvailableIntegration,
    AvailableIntegrationsResponse,
    UserIntegrationsResponse,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationValidateResponse,
)
from app.schemas.template import (
    VideoStructureConfig,
    VisualStyleConfig,
    TextCaptionsConfig,
    AudioConfig,
    ScriptPromptConfig,
    PlatformOptimizationConfig,
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListItem,
    TemplateListResponse,
    TemplateConfigResponse,
)
from app.schemas.video import (
    VideoGenerationRequest,
    SwapIntegrationRequest,
    StepStatus,
    VideoStatusResponse,
    VideoResponse,
    VideoListItem,
    VideoListResponse,
    VideoGenerationResponse,
)
from app.schemas.social_account import (
    SocialAccountResponse,
    SocialAccountListResponse,
    OAuthInitResponse,
    OAuthCallbackResponse,
    DisconnectRequest,
)
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostResponse,
    PostListResponse,
    CalendarDayItem,
    CalendarResponse,
    PostCreateResponse,
    PublishNowRequest,
)
from app.schemas.analytics import (
    AnalyticsMetrics,
    AnalyticsResponse,
    OverviewResponse,
    PlatformMetrics,
    PlatformComparisonResponse,
    PostAnalyticsResponse,
    TimeSeriesDataPoint,
    TimeSeriesResponse,
    TopPerformingItem,
    TopPerformingResponse,
    HeatmapResponse,
    SyncResponse,
    AnalyticsSyncRequest,
)
from app.schemas.suggestion import (
    SuggestionResponse,
    SuggestionListResponse,
    PostingTimeSuggestion,
    PostingTimeResponse,
    ContentSuggestion,
    ContentResponse,
    TrendAlert,
    TrendsResponse,
    MarkReadRequest,
    DismissRequest,
)
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    MarkReadResponse,
)
from app.schemas.admin import (
    UserStats,
    VideoStats,
    PostStats,
    IntegrationUsageStats,
    PlatformStatsResponse,
    SubscriberStats,
    RevenueMetrics,
    FeatureFlags,
    SystemLimits,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)

__all__ = [
    # Common
    "BaseSchema",
    "TimestampSchema",
    "IDSchema",
    "PaginationParams",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "SuccessResponse",
    "HealthResponse",
    "MessageResponse",
    
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "RoleUpdate",
    "StatusUpdate",
    "UserResponse",
    "UserProfileResponse",
    "UserListResponse",
    "UserStatsResponse",
    "FirebaseTokenRequest",
    "LoginResponse",
    "SetupStatusResponse",
    
    # Subscription
    "SubscriptionResponse",
    "SubscriptionStatusResponse",
    "PlanFeatures",
    "PlanInfo",
    "PlansResponse",
    "CheckoutRequest",
    "CheckoutResponse",
    "PortalResponse",
    "WebhookResponse",
    
    # Integration
    "IntegrationResponse",
    "IntegrationRevealResponse",
    "AvailableIntegration",
    "AvailableIntegrationsResponse",
    "UserIntegrationsResponse",
    "IntegrationCreate",
    "IntegrationUpdate",
    "IntegrationValidateResponse",
    
    # Template
    "VideoStructureConfig",
    "VisualStyleConfig",
    "TextCaptionsConfig",
    "AudioConfig",
    "ScriptPromptConfig",
    "PlatformOptimizationConfig",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "TemplateListItem",
    "TemplateListResponse",
    "TemplateConfigResponse",
    
    # Video
    "VideoGenerationRequest",
    "SwapIntegrationRequest",
    "StepStatus",
    "VideoStatusResponse",
    "VideoResponse",
    "VideoListItem",
    "VideoListResponse",
    "VideoGenerationResponse",
    
    # Social Account
    "SocialAccountResponse",
    "SocialAccountListResponse",
    "OAuthInitResponse",
    "OAuthCallbackResponse",
    "DisconnectRequest",
    
    # Post
    "PostCreate",
    "PostUpdate",
    "PostResponse",
    "PostListResponse",
    "CalendarDayItem",
    "CalendarResponse",
    "PostCreateResponse",
    "PublishNowRequest",
    
    # Analytics
    "AnalyticsMetrics",
    "AnalyticsResponse",
    "OverviewResponse",
    "PlatformMetrics",
    "PlatformComparisonResponse",
    "PostAnalyticsResponse",
    "TimeSeriesDataPoint",
    "TimeSeriesResponse",
    "TopPerformingItem",
    "TopPerformingResponse",
    "HeatmapResponse",
    "SyncResponse",
    "AnalyticsSyncRequest",
    
    # Suggestion
    "SuggestionResponse",
    "SuggestionListResponse",
    "PostingTimeSuggestion",
    "PostingTimeResponse",
    "ContentSuggestion",
    "ContentResponse",
    "TrendAlert",
    "TrendsResponse",
    "MarkReadRequest",
    "DismissRequest",
    
    # Notification
    "NotificationResponse",
    "NotificationListResponse",
    "MarkReadResponse",
    
    # Admin
    "UserStats",
    "VideoStats",
    "PostStats",
    "IntegrationUsageStats",
    "PlatformStatsResponse",
    "SubscriberStats",
    "RevenueMetrics",
    "FeatureFlags",
    "SystemLimits",
    "SystemSettingsResponse",
    "SystemSettingsUpdate",
]
