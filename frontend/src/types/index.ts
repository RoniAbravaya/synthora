/**
 * TypeScript type definitions for the application.
 */

// =============================================================================
// User Types
// =============================================================================

export type UserRole = "admin" | "premium" | "free"

export interface User {
  id: string
  email: string
  display_name: string | null
  photo_url: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  last_login: string | null
}

export interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
}

// =============================================================================
// Integration Types
// =============================================================================

export type IntegrationCategory = "script" | "voice" | "media" | "video_ai" | "assembly"

export interface Integration {
  id: string
  provider: string
  category: IntegrationCategory
  api_key_masked: string
  is_active: boolean
  is_valid: boolean
  last_validated: string | null
  created_at: string
}

export interface AvailableIntegration {
  provider: string
  category: IntegrationCategory
  display_name: string
  description: string
  auth_type: "api_key" | "oauth"
  docs_url: string
  required: boolean
}

// =============================================================================
// Template Types
// =============================================================================

export interface Template {
  id: string
  name: string
  description: string | null
  category: string
  is_system: boolean
  is_public: boolean
  config: TemplateConfig
  created_at: string
  updated_at: string | null
}

export interface TemplateConfig {
  video_structure: {
    duration_seconds: number
    aspect_ratio: string
    segments: Array<{
      type: string
      duration_seconds: number
      description: string
    }>
  }
  visual_style: {
    color_scheme: string
    font_family: string
    transition_style: string
    overlay_style: string
  }
  audio: {
    voice_style: string
    background_music_genre: string
    sound_effects: boolean
  }
  script_prompt: {
    tone: string
    hook_style: string
    call_to_action: string
    content_structure: string[]
  }
  platform_optimization: {
    primary_platform: string
    hashtag_strategy: string
    caption_style: string
  }
}

// =============================================================================
// Video Types
// =============================================================================

export type VideoStatus = 
  | "pending"
  | "generating_script"
  | "generating_voice"
  | "fetching_media"
  | "generating_video"
  | "assembling"
  | "completed"
  | "failed"

export interface Video {
  id: string
  title: string | null
  description: string | null
  status: VideoStatus
  progress: number
  current_step: string | null
  error_message: string | null
  error_payload: Record<string, unknown> | null
  video_url: string | null
  thumbnail_url: string | null
  duration_seconds: number | null
  template_id: string | null
  created_at: string
  completed_at: string | null
  expires_at: string | null
}

export interface VideoGenerationRequest {
  template_id: string
  topic: string
  custom_instructions?: string
}

// =============================================================================
// Social Account Types
// =============================================================================

export type SocialPlatform = "youtube" | "tiktok" | "instagram" | "facebook"

export interface SocialAccount {
  id: string
  platform: SocialPlatform
  platform_user_id: string
  platform_username: string | null
  is_active: boolean
  token_expires_at: string | null
  created_at: string
}

// =============================================================================
// Post Types
// =============================================================================

export type PostStatus = "draft" | "scheduled" | "publishing" | "published" | "failed"

export interface Post {
  id: string
  video_id: string
  user_id: string
  title: string | null
  description: string | null
  hashtags: string[]
  platforms: string[]
  platform_status: Record<string, { status: string }>
  platform_overrides: Record<string, unknown>
  status: PostStatus
  scheduled_at: string | null
  published_at: string | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface PostCreate {
  video_id: string
  title?: string
  description?: string
  hashtags?: string[]
  platforms: SocialPlatform[]
  scheduled_at?: string
  platform_overrides?: Record<string, { title?: string; description?: string }>
}

// =============================================================================
// Analytics Types
// =============================================================================

export interface AnalyticsMetrics {
  views: number
  likes: number
  comments: number
  shares: number
  watch_time_seconds: number
  avg_view_duration: number
  retention_rate: number
  saves: number
  click_through_rate: number
  follower_growth: number
  reach: number
  impressions: number
}

export interface AnalyticsOverview {
  total_videos: number
  total_posts: number
  total_views: number
  total_likes: number
  total_shares: number
  engagement_rate: number
  top_platform: SocialPlatform | null
  metrics_by_platform: Record<string, AnalyticsMetrics>
}

export interface TimeSeriesDataPoint {
  date: string
  value: number
}

// =============================================================================
// Subscription Types
// =============================================================================

export type SubscriptionPlan = "monthly" | "annual"
export type SubscriptionStatus = "active" | "canceled" | "past_due" | "incomplete"

export interface Subscription {
  id: string
  plan: SubscriptionPlan
  status: SubscriptionStatus
  current_period_start: string
  current_period_end: string
  cancel_at_period_end: boolean
}

export interface PlanInfo {
  id: SubscriptionPlan
  name: string
  price: number
  interval: "month" | "year"
  features: string[]
}

// =============================================================================
// Notification Types
// =============================================================================

export type NotificationType = 
  | "video_completed"
  | "video_failed"
  | "post_published"
  | "post_failed"
  | "suggestion"
  | "subscription"
  | "system"

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  is_read: boolean
  action_url: string | null
  created_at: string
}

// =============================================================================
// AI Suggestion Types
// =============================================================================

export type SuggestionType = 
  | "posting_time"
  | "content"
  | "template"
  | "trend"
  | "prediction"
  | "improvement"

export interface Suggestion {
  id: string
  type: SuggestionType
  title: string
  description: string
  confidence: number
  data: Record<string, unknown>
  is_read: boolean
  is_dismissed: boolean
  created_at: string
  expires_at: string | null
}

// =============================================================================
// API Response Types
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface ApiError {
  detail: string
  status?: number
}

