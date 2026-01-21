# Synthora - Implementation Checklist

**Project:** Synthora - AI Video Generator Platform  
**Created:** January 21, 2026  
**Reference:** [ai-overview.md](./ai-overview.md)

---

## Table of Contents

1. [Project Setup & Infrastructure](#1-project-setup--infrastructure)
2. [Backend Foundation](#2-backend-foundation)
3. [Database & Models](#3-database--models)
4. [Authentication System](#4-authentication-system)
5. [User Management & Roles](#5-user-management--roles)
6. [Integration Management](#6-integration-management)
7. [Template System](#7-template-system)
8. [Video Generation Pipeline](#8-video-generation-pipeline)
9. [Social Media Connections](#9-social-media-connections)
10. [Posting & Scheduling](#10-posting--scheduling)
11. [Analytics System](#11-analytics-system)
12. [AI Suggestions Engine](#12-ai-suggestions-engine)
13. [Subscription & Billing](#13-subscription--billing)
14. [Notification System](#14-notification-system)
15. [Admin Panel](#15-admin-panel)
16. [Frontend Foundation](#16-frontend-foundation)
17. [Frontend Pages](#17-frontend-pages)
18. [Testing & Quality](#18-testing--quality)
19. [Deployment & CI/CD](#19-deployment--cicd)
20. [Final Polish](#20-final-polish)

---

## 1. Project Setup & Infrastructure

### 1.1 Repository Setup
- [x] 1.1.1 Initialize Git repository
- [x] 1.1.2 Create `.gitignore` file (Python, Node, IDE files, env files)
- [x] 1.1.3 Create `README.md` with project overview and setup instructions
- [ ] 1.1.4 Set up branch protection rules on GitHub (main branch)

### 1.2 Monorepo Structure
- [x] 1.2.1 Create `/backend` directory
- [x] 1.2.2 Create `/frontend` directory
- [x] 1.2.3 Create `/ai-planning` directory (already done)
- [x] 1.2.4 Create `/.github/workflows` directory

### 1.3 Environment Configuration
- [x] 1.3.1 Create `.env.example` with all placeholder variables
  - App configuration variables
  - Database URL placeholder
  - Redis URL placeholder
  - Firebase configuration placeholders
  - Stripe configuration placeholders
  - Google Cloud Storage placeholders
  - Social media OAuth placeholders
  - CORS configuration
- [x] 1.3.2 Document each environment variable with comments

### 1.4 Railway Configuration
- [x] 1.4.1 Create `railway.json` or configure via Railway dashboard
- [x] 1.4.2 Configure backend service (Nixpacks auto-detect Python)
- [x] 1.4.3 Configure frontend service (Nixpacks auto-detect Node)
- [x] 1.4.4 Configure worker service (same codebase, different start command)
- [ ] 1.4.5 Add PostgreSQL plugin *(do in Railway dashboard)*
- [ ] 1.4.6 Configure environment variables in Railway dashboard *(do in Railway dashboard)*
- [ ] 1.4.7 Set up Upstash Redis and add `REDIS_URL` to Railway *(do in Upstash/Railway)*

### 1.5 External Services Setup
> **See [docs/SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) for detailed instructions**

- [ ] 1.5.1 Create Firebase project
  - Enable Google Sign-In authentication
  - Generate service account credentials
  - Note Web SDK configuration
- [ ] 1.5.2 Create Stripe account
  - Create products: Monthly ($5), Annual ($50)
  - Note API keys (publishable + secret)
  - Set up webhook endpoint
- [ ] 1.5.3 Create Google Cloud Storage bucket
  - Create service account with Storage Admin role
  - Generate JSON key file
  - Configure CORS for bucket
- [ ] 1.5.4 Create Upstash Redis database
  - Note connection URL

---

## 2. Backend Foundation

### 2.1 Python Project Setup
- [x] 2.1.1 Create `backend/requirements.txt` with dependencies:
  ```
  fastapi>=0.109.0
  uvicorn[standard]>=0.27.0
  sqlalchemy>=2.0.0
  alembic>=1.13.0
  psycopg2-binary>=2.9.9
  python-dotenv>=1.0.0
  pydantic>=2.5.0
  pydantic-settings>=2.1.0
  python-jose[cryptography]>=3.3.0
  passlib[bcrypt]>=1.7.4
  cryptography>=41.0.0
  firebase-admin>=6.3.0
  stripe>=7.0.0
  google-cloud-storage>=2.14.0
  rq>=1.15.0
  redis>=5.0.0
  httpx>=0.26.0
  python-multipart>=0.0.6
  aiofiles>=23.2.0
  Pillow>=10.2.0
  ```
- [x] 2.1.2 Create `backend/Procfile` for Railway:
  ```
  web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- [x] 2.1.3 Create `backend/Procfile.worker` for worker service:
  ```
  worker: rq worker --url $REDIS_URL
  ```

### 2.2 FastAPI Application Structure
- [x] 2.2.1 Create `backend/app/__init__.py`
- [x] 2.2.2 Create `backend/app/main.py` with FastAPI app initialization
  - CORS middleware configuration (strict, Railway-aware)
  - Exception handlers
  - Router includes
  - Startup/shutdown events
- [x] 2.2.3 Create `backend/app/core/__init__.py`
- [x] 2.2.4 Create `backend/app/core/config.py` with Pydantic Settings
  - All environment variable definitions
  - Validation and defaults
- [x] 2.2.5 Create `backend/app/core/security.py`
  - Encryption utilities (Fernet)
  - Password hashing (if needed)
  - Token utilities
- [x] 2.2.6 Create `backend/app/core/dependencies.py`
  - Database session dependency
  - Current user dependency
  - Role-based access dependencies
  - Rate limiting dependency

### 2.3 Database Connection
- [x] 2.3.1 Create `backend/app/core/database.py`
  - SQLAlchemy engine configuration
  - Session factory
  - Base model class
- [ ] 2.3.2 Enable pgcrypto extension in PostgreSQL *(done at runtime)*
- [ ] 2.3.3 Test database connection *(requires database)*

### 2.4 API Router Structure
- [x] 2.4.1 Create `backend/app/api/__init__.py`
- [x] 2.4.2 Create `backend/app/api/v1/__init__.py`
- [x] 2.4.3 Create `backend/app/api/v1/router.py` (main router)
- [x] 2.4.4 Create placeholder routers for each module:
  - `auth.py`
  - `users.py`
  - `templates.py`
  - `integrations.py`
  - `videos.py`
  - `social_accounts.py`
  - `posts.py`
  - `analytics.py`
  - `suggestions.py`
  - `notifications.py`
  - `subscriptions.py`
  - `admin.py`
  - `health.py`

> ✅ **Section 2 Complete** - All backend foundation files created with full implementations

---

## 3. Database & Models

### 3.1 SQLAlchemy Models
- [x] 3.1.1 Create `backend/app/models/__init__.py`
- [x] 3.1.2 Create `backend/app/models/user.py`
  - User model with UserRole enum (ADMIN, PREMIUM, FREE)
  - Properties: is_admin, is_premium, can_schedule, can_access_ai_suggestions
  - Properties: daily_video_limit, video_retention_days
- [x] 3.1.3 Create `backend/app/models/subscription.py`
  - Subscription model with SubscriptionPlan and SubscriptionStatus enums
  - Properties: is_active, is_valid, days_until_renewal, price
- [x] 3.1.4 Create `backend/app/models/integration.py`
  - Integration model with IntegrationProvider and IntegrationCategory enums
  - PROVIDER_CATEGORIES mapping for categorization
  - Methods: mark_used, mark_validated
- [x] 3.1.5 Create `backend/app/models/template.py`
  - Comprehensive template model with all configuration enums
  - Enums: TemplateCategory, AspectRatio, HookStyle, NarrativeStructure, Pacing
  - Enums: VisualAesthetic, VoiceTone, MusicMood, CTAType
  - Method: to_config_dict for video generation pipeline
- [x] 3.1.6 Create `backend/app/models/video.py`
  - Video model with VideoStatus and GenerationStep enums
  - Methods: get_step_status, update_step, get_last_successful_step, set_error
- [x] 3.1.7 Create `backend/app/models/social_account.py`
  - SocialAccount model with SocialPlatform enum
  - Properties: is_token_expired, needs_refresh, display_name
  - Methods: mark_used, update_tokens
- [x] 3.1.8 Create `backend/app/models/post.py`
  - Post model with PostStatus enum
  - Properties: is_published, is_scheduled, is_due, can_edit, can_cancel
  - Methods: mark_publishing, mark_published, mark_failed, cancel
- [x] 3.1.9 Create `backend/app/models/analytics.py`
  - Analytics model with all metrics (views, likes, shares, comments, etc.)
  - Properties: engagement_count, engagement_rate
  - Method: update_metrics, to_dict
- [x] 3.1.10 Create `backend/app/models/ai_suggestion.py`
  - AISuggestion model with SuggestionType enum
  - Factory methods: create_posting_time_suggestion, create_content_suggestion
  - Factory methods: create_trend_alert, create_improvement_tip
- [x] 3.1.11 Create `backend/app/models/notification.py`
  - Notification model with NotificationType enum
  - Factory methods for all notification types
- [x] 3.1.12 Create `backend/app/models/job.py`
  - Job model with JobType and JobStatus enums
  - Methods: start, update_progress, complete, fail, cancel, retry
- [x] 3.1.13 Create `backend/app/models/app_settings.py`
  - AppSettings model for system-wide configuration
  - Default feature flags and limits

### 3.2 Pydantic Schemas
- [x] 3.2.1 Create `backend/app/schemas/__init__.py`
- [x] 3.2.2 Create schemas for each model (Create, Update, Response variants):
  - `user.py` - UserCreate, UserUpdate, UserResponse, UserProfileResponse, LoginResponse
  - `subscription.py` - SubscriptionResponse, SubscriptionStatusResponse, PlansResponse
  - `integration.py` - IntegrationCreate, IntegrationResponse, UserIntegrationsResponse
  - `template.py` - TemplateCreate, TemplateUpdate, TemplateResponse with nested configs
  - `video.py` - VideoGenerationRequest, VideoStatusResponse, VideoResponse
  - `social_account.py` - SocialAccountResponse, OAuthInitResponse, OAuthCallbackResponse
  - `post.py` - PostCreate, PostUpdate, PostResponse, CalendarResponse
  - `analytics.py` - AnalyticsResponse, OverviewResponse, TimeSeriesResponse, HeatmapResponse
  - `suggestion.py` - SuggestionResponse, PostingTimeResponse, ContentResponse
  - `notification.py` - NotificationResponse, NotificationListResponse
  - `admin.py` - PlatformStatsResponse, RevenueMetrics, SystemSettingsResponse
- [x] 3.2.3 Create common schemas in `common.py`:
  - BaseSchema, TimestampSchema, IDSchema
  - PaginationParams, PaginatedResponse (generic)
  - ErrorDetail, ErrorResponse, SuccessResponse, HealthResponse

### 3.3 Alembic Migrations
- [x] 3.3.1 Create `alembic.ini` with database URL configuration
- [x] 3.3.2 Create `alembic/env.py` with model imports
- [x] 3.3.3 Create `alembic/script.py.mako` template
- [x] 3.3.4 Create `alembic/versions/` directory with .gitkeep
- [x] 3.3.5 Create `alembic/README` with migration instructions
- [ ] 3.3.6 Generate initial migration: `alembic revision --autogenerate -m "Initial schema"` *(requires database)*
- [ ] 3.3.7 Apply migration: `alembic upgrade head` *(requires database)*

> ✅ **Section 3 Complete** - All SQLAlchemy models, Pydantic schemas, and Alembic configuration created

---

## 4. Authentication System

### 4.1 Firebase Integration
- [x] 4.1.1 Create `backend/app/services/firebase.py`
  - Initialize Firebase Admin SDK with credentials path or JSON
  - Token verification function (`verify_id_token`)
  - User info extraction (`UserInfo` class)
  - Helper functions: `get_firebase_user`, `revoke_refresh_tokens`, `set_custom_claims`
- [x] 4.1.2 Create `backend/app/core/auth.py`
  - `get_current_user` dependency - gets user from DB by Firebase UID
  - `get_current_active_user` dependency - verifies user is active
  - `get_optional_user` dependency - for optional auth endpoints
  - `require_role` dependency factory - checks user role
  - `require_admin` and `require_premium` convenience dependencies
  - `AuthenticationError` and `AuthorizationError` exceptions

### 4.2 Auth API Endpoints
- [x] 4.2.1 Implement `POST /api/v1/auth/login`
  - Receive Firebase ID token, verify with Firebase Admin SDK
  - Create/update user in database via UserService
  - Return user profile with subscription and feature access
  - `is_new_user` and `setup_required` flags for onboarding
- [x] 4.2.2 Implement `POST /api/v1/auth/logout`
  - Revoke Firebase refresh tokens
- [x] 4.2.3 Implement `GET /api/v1/auth/me`
  - Return current user profile with all feature access info
- [x] 4.2.4 Implement `POST /api/v1/auth/verify-token`
  - Verify token without creating/updating user
- [x] 4.2.5 Implement `POST /api/v1/auth/refresh`
  - Update last_login_at timestamp

### 4.3 First User Setup Wizard
- [x] 4.3.1 Create `GET /api/v1/auth/setup-status`
  - Check if setup is completed (any admin exists)
  - Return appropriate message for new installations
- [x] 4.3.2 Modify login flow:
  - First user automatically becomes admin
  - Implemented in `UserService.create_or_update_from_firebase()`

> ✅ **Section 4 Complete** - Firebase integration, auth dependencies, and all auth endpoints implemented

---

## 5. User Management & Roles

### 5.1 User Service
- [x] 5.1.1 Create `backend/app/services/user.py`
  - `get_by_id`, `get_by_email`, `get_by_firebase_uid`
  - `create_user`, `create_or_update_from_firebase`
  - `update_user`, `update_role`, `set_active_status`
  - `get_all` (with pagination, filtering, search)
  - `get_user_stats`, `get_user_profile_data`
  - `admin_exists`, `_should_be_first_admin`

### 5.2 User API Endpoints
- [x] 5.2.1 Implement `GET /api/v1/users` (Admin only)
  - List all users with pagination
  - Filter by role, status
  - Search by email/name
- [x] 5.2.2 Implement `GET /api/v1/users/{id}` (Admin only)
  - Get user details
- [x] 5.2.3 Implement `PATCH /api/v1/users/{id}/role` (Admin only)
  - Change user role (free/premium/admin)
  - Prevent admin from demoting themselves
- [x] 5.2.4 Implement `PATCH /api/v1/users/{id}/status` (Admin only)
  - Enable/disable user account
  - Prevent admin from disabling themselves
- [x] 5.2.5 Implement `POST /api/v1/users/{id}/grant-premium` (Admin only)
  - Grant premium access without Stripe
- [x] 5.2.6 Implement `POST /api/v1/users/{id}/revoke-premium` (Admin only)
  - Revoke premium access
- [x] 5.2.7 Implement `GET /api/v1/users/stats` (Admin only)
  - Platform-wide user statistics
- [x] 5.2.8 Implement `GET /api/v1/users/profile` (Self)
  - Get own profile with full details
- [x] 5.2.9 Implement `PATCH /api/v1/users/profile` (Self)
  - Update own profile (name, avatar)

### 5.3 Role-Based Access Control
- [x] 5.3.1 Create role checking dependencies in `auth.py`
  - `require_role(*roles)` factory
  - `require_admin`, `require_premium` shortcuts
  - `AdminUser`, `PremiumUser`, `CurrentUser` dependency aliases
- [x] 5.3.2 Implement feature flags based on role:
  - Properties on User model: `is_premium`, `can_schedule`, `can_access_ai_suggestions`
  - `daily_video_limit`, `video_retention_days` properties
- [ ] 5.3.3 Create `backend/app/services/limits.py`
  - `check_video_generation_limit`
  - `check_concurrent_generation`
  - `check_scheduling_access`
  - `check_ai_suggestions_access`

> ✅ **Section 5 Mostly Complete** - User service and endpoints implemented, limits service pending

---

## 6. Integration Management

### 6.1 Integration Service
- [x] 6.1.1 Create `backend/app/services/integration.py`
  - `get_by_id`, `get_user_integrations`, `get_active_integrations`
  - `get_by_provider`, `get_by_category`
  - `add_integration`, `update_api_key`, `delete_integration`
  - `set_validation_status`, `set_active_status`, `mark_used`
  - `get_decrypted_api_key`, `get_masked_api_key`
  - `get_configured_categories`, `get_missing_categories`
  - `can_generate_videos`, `get_integration_status`
  - Static methods: `get_provider_info`, `get_all_providers_info`, `get_providers_by_category`

### 6.2 Integration Validators
- [x] 6.2.1 Create `backend/app/integrations/__init__.py`
- [x] 6.2.2 Create base validator class `backend/app/integrations/base.py`
  - `BaseValidator` abstract class with `validate()` method
  - `ValidationResult` dataclass for validation results
  - HTTP error handling helpers
- [x] 6.2.3 Create validators in `backend/app/integrations/validators.py`:
  - `OpenAIValidator` - Validate OpenAI API key (list models)
  - `ElevenLabsValidator` - Validate ElevenLabs API key (get user)
  - `PexelsValidator` - Validate Pexels API key (search videos)
  - `UnsplashValidator` - Validate Unsplash API key (random photo)
  - `RunwayValidator` - Validate Runway API key
  - `SoraValidator` - Validate OpenAI Sora (via OpenAI API)
  - `VeoValidator` - Validate Google Veo 3
  - `LumaValidator` - Validate Luma Dream Machine
  - `ImagineArtValidator`, `PixVerseValidator`, `SeedanceValidator`
  - `WanValidator`, `HailuoValidator`, `LTXValidator`
  - `FFmpegValidator` - Check local FFmpeg installation
  - `CreatomateValidator` - Validate Creatomate API key
  - `ShotstackValidator` - Validate Shotstack API key
  - `RemotionValidator` - Validate Remotion setup
  - `EditframeValidator` - Validate Editframe API key
- [x] 6.2.4 Create `backend/app/integrations/factory.py`
  - `get_validator()` - Factory to get validator by provider
  - `validate_integration()` - Convenience function for validation
  - `VALIDATOR_MAP` - Provider to validator mapping

### 6.3 Integration API Endpoints
- [x] 6.3.1 Implement `GET /api/v1/integrations`
  - List user's configured integrations with masked keys
  - Include validation status, categories, can_generate flag
- [x] 6.3.2 Implement `GET /api/v1/integrations/available`
  - List all available integrations
  - Include category, auth method, docs URL
  - Include whether user has configured each
- [x] 6.3.3 Implement `GET /api/v1/integrations/providers`
  - Get providers grouped by category (public)
- [x] 6.3.4 Implement `GET /api/v1/integrations/status`
  - Quick status check for video generation readiness
- [x] 6.3.5 Implement `POST /api/v1/integrations`
  - Add new integration with encrypted API key
  - Background validation after save
- [x] 6.3.6 Implement `PATCH /api/v1/integrations/{id}`
  - Update integration API key
  - Re-validate in background
- [x] 6.3.7 Implement `DELETE /api/v1/integrations/{id}`
  - Remove integration
- [x] 6.3.8 Implement `POST /api/v1/integrations/{id}/validate`
  - Manually trigger validation
- [x] 6.3.9 Implement `POST /api/v1/integrations/{id}/reveal`
  - Return full decrypted API key (with security logging)
- [x] 6.3.10 Implement `PATCH /api/v1/integrations/{id}/toggle`
  - Toggle active status

### 6.4 OAuth Integrations (Future Enhancement)
- [ ] 6.4.1 Research which integrations support OAuth
- [ ] 6.4.2 Implement OAuth flow for supported integrations
- [ ] 6.4.3 Create callback handlers

> ✅ **Section 6 Complete** - Integration service, validators for all 19 providers, and full API endpoints implemented

---

## 7. Template System

### 7.1 Template Service
- [x] 7.1.1 Create `backend/app/services/template.py`
  - `get_by_id`, `get_system_templates`, `get_user_templates`
  - `get_accessible_templates` with filtering, search, pagination
  - `can_access_template`, `can_edit_template` permission checks
  - `create_template`, `update_template`, `delete_template`
  - `duplicate_template` - creates personal copy
  - `get_template_config`, `apply_config_to_template`
  - `get_template_stats` for admin dashboard

### 7.2 Template Schema Definition
- [x] 7.2.1 Template model with comprehensive config fields:
  - Video structure: hook_style, narrative_structure, num_scenes, duration, pacing
  - Visual style: aspect_ratio, color_palette, visual_aesthetic, transitions
  - Text/Captions: caption_style, font_style, text_position, hook_text_overlay
  - Audio: voice_gender, voice_tone, voice_speed, music_mood, sound_effects
  - Script/Prompt: script_structure_prompt, tone_instructions, cta_type
  - Platform: thumbnail_style, suggested_hashtags
- [x] 7.2.2 Create `backend/app/services/template_validator.py`
  - `TemplateValidator` class with comprehensive validation
  - Validates all enum values, ranges, string lengths
  - `ValidationResult` with detailed error reporting

### 7.3 Seed Data - System Templates
- [x] 7.3.1 Create `backend/app/data/seed_templates.py`
- [x] 7.3.2 Define 5 general-purpose templates:
  1. **Viral Hook** - Fast-paced, bold, 15-30s, TikTok/Instagram optimized
  2. **Educational Explainer** - Problem-solution structure, 30-90s, professional tone
  3. **Product Showcase** - Cinematic demo format, 20-60s, aspirational style
  4. **Storytelling** - Narrative-driven, 45-120s, emotional connection
  5. **Trending Challenge** - Ultra-short, 10-30s, participation-focused
- [x] 7.3.3 Create `seed_system_templates()` function (idempotent)

### 7.4 Template API Endpoints
- [x] 7.4.1 Implement `GET /api/v1/templates`
  - List all accessible templates (system + personal + public)
  - Filter by category, platform, search
- [x] 7.4.2 Implement `GET /api/v1/templates/system`
  - List system templates only
- [x] 7.4.3 Implement `GET /api/v1/templates/my`
  - List user's personal templates
- [x] 7.4.4 Implement `POST /api/v1/templates`
  - Create personal template (or system for admin)
  - Nested config support
- [x] 7.4.5 Implement `GET /api/v1/templates/{id}`
  - Get template details with full config
- [x] 7.4.6 Implement `GET /api/v1/templates/{id}/config`
  - Get template config for video generation pipeline
- [x] 7.4.7 Implement `PATCH /api/v1/templates/{id}`
  - Update template with version increment
- [x] 7.4.8 Implement `DELETE /api/v1/templates/{id}`
  - Delete template (permission checked)
- [x] 7.4.9 Implement `POST /api/v1/templates/{id}/duplicate`
  - Duplicate template to personal collection
- [x] 7.4.10 Implement `POST /api/v1/templates/seed` (Admin)
  - Seed system templates
- [x] 7.4.11 Implement `GET /api/v1/templates/stats` (Admin)
  - Template statistics

> ✅ **Section 7 Complete** - Template service, validation, 5 seed templates, and full API endpoints implemented

---

## 8. Video Generation Pipeline

### 8.1 Video Generation Service
- [x] 8.1.1 Create `backend/app/services/video.py`
  - `get_by_id`, `get_user_videos`, `get_active_generation`
  - `count_videos_today` for daily limit enforcement
  - `create_video`, `create_generation_job`
  - `update_status`, `update_step`, `complete_video`, `fail_video`
  - `get_last_successful_step`, `can_swap_integration`
  - `set_expiration`, `get_expired_videos`, `cleanup_expired_videos`
  - `get_user_video_stats`, `get_platform_video_stats`

### 8.2 Generation Pipeline Components
- [x] 8.2.1 Create `backend/app/services/generation/__init__.py`
- [x] 8.2.2 Create `backend/app/services/generation/pipeline.py`
  - `GenerationPipeline` - Main orchestrator
  - `PipelineConfig` - Configuration dataclass
  - Step-by-step execution with progress tracking
  - State persistence for resume capability
  - Error handling with full payload capture
  - Integration swapping on failure
- [x] 8.2.3 Create `backend/app/services/generation/script.py`
  - `ScriptGenerator` - OpenAI GPT-4 integration
  - Template-based prompt construction
  - `VideoScript` and `ScriptScene` dataclasses
  - JSON response parsing with validation
- [x] 8.2.4 Create `backend/app/services/generation/voice.py`
  - `VoiceGenerator` - ElevenLabs integration
  - Voice selection by gender and tone
  - `ELEVENLABS_VOICES` mapping
  - Audio base64 encoding
- [x] 8.2.5 Create `backend/app/services/generation/media.py`
  - `MediaFetcher` - Pexels and Unsplash integration
  - Keyword extraction from visual descriptions
  - Video and image search with orientation
  - `MediaItem` dataclass
- [x] 8.2.6 Create `backend/app/services/generation/video_ai.py`
  - `VideoAIGenerator` - Multiple provider support
  - Runway, Sora, Veo, Luma implementations
  - Graceful handling of unavailable APIs
  - `GeneratedClip` dataclass
- [x] 8.2.7 Create `backend/app/services/generation/assembly.py`
  - `VideoAssembler` - FFmpeg and cloud API support
  - FFmpeg command building with filters
  - Creatomate, Shotstack, Remotion, Editframe placeholders
  - Resolution handling for aspect ratios

### 8.3 Background Workers
- [x] 8.3.1 Create `backend/app/workers/__init__.py`
- [x] 8.3.2 Create `backend/app/workers/video_worker.py`
  - `process_video_generation` - Main RQ job
  - `retry_video_generation` - Retry with swap
  - `update_job_progress` - Progress tracking
- [x] 8.3.3 Create `backend/app/workers/scheduler.py`
  - `JobScheduler` - RQ queue management
  - Multiple queues: video, analytics, posts, cleanup
  - `enqueue_video_generation`, `enqueue_video_retry`
  - `get_job_status`, `cancel_job`, `get_queue_stats`
- [x] 8.3.4 Create `backend/app/workers/cleanup_worker.py`
  - `run_cleanup` - Expired videos, orphaned jobs, old notifications

### 8.4 Limits Service
- [x] 8.4.1 Create `backend/app/services/limits.py`
  - Role-based limit configuration
  - `can_generate_video` - Daily limit check
  - `can_use_ai_suggestions` - Feature access
  - `get_video_retention_days` - Expiration policy
  - `get_remaining_daily_videos`, `get_usage_stats`

### 8.5 Video API Endpoints
- [x] 8.5.1 Implement `GET /api/v1/videos`
  - List user's videos with status filter
  - Pagination support
- [x] 8.5.2 Implement `POST /api/v1/videos`
  - Validate minimum integrations
  - Check daily limit and concurrent limit
  - Create video record and queue job
- [x] 8.5.3 Implement `GET /api/v1/videos/{id}`
  - Get video details with ownership check
- [x] 8.5.4 Implement `GET /api/v1/videos/{id}/status`
  - Real-time generation status for polling
  - Progress, current step, error details
- [x] 8.5.5 Implement `POST /api/v1/videos/{id}/retry`
  - Retry failed generation with optional integration swap
- [x] 8.5.6 Implement `DELETE /api/v1/videos/{id}`
  - Delete video (not while generating)
- [x] 8.5.7 Implement `GET /api/v1/videos/stats/me`
  - User video statistics
- [x] 8.5.8 Implement `GET /api/v1/videos/admin/stats` (Admin)
  - Platform-wide video statistics

> ✅ **Section 8 Complete** - Full video generation pipeline with orchestrator, 5 generation components, background workers, limits service, and API endpoints

---

## 9. Social Media Connections

### 9.1 OAuth Service
- [x] 9.1.1 Create `backend/app/services/social_oauth.py`
  - `generate_oauth_state`, `validate_oauth_state` - CSRF protection
  - `get_user_accounts`, `get_account_by_id`, `get_account_by_platform_id`
  - `create_or_update_account` - Token storage (encrypted with Fernet)
  - `disconnect_account`
  - `get_access_token` - Auto-refresh if expired
  - `mark_account_error` - Error handling

### 9.2 Platform-Specific OAuth
- [x] 9.2.1 Create `backend/app/integrations/social/__init__.py`
  - `get_platform_client()` factory function
- [x] 9.2.2 Create `backend/app/integrations/social/base.py`
  - `BaseSocialClient` abstract class
  - `OAuthConfig`, `UserProfile`, `PostResult`, `AnalyticsData` dataclasses
  - Abstract methods: `get_authorization_url`, `exchange_code`, `refresh_access_token`
  - Abstract methods: `get_user_profile`, `upload_video`, `get_video_analytics`
- [x] 9.2.3 Create `backend/app/integrations/social/youtube.py`
  - Google OAuth 2.0 with offline access
  - YouTube Data API v3 integration
  - Video upload (resumable), channel info, analytics
- [x] 9.2.4 Create `backend/app/integrations/social/tiktok.py`
  - TikTok OAuth 2.0 flow
  - Content Posting API (init, upload, publish)
  - User profile and video analytics
- [x] 9.2.5 Create `backend/app/integrations/social/instagram.py`
  - Meta Graph API OAuth (long-lived tokens)
  - Instagram Business/Creator account support
  - Reels upload via media container API
- [x] 9.2.6 Create `backend/app/integrations/social/facebook.py`
  - Meta Graph API OAuth
  - Facebook Page video upload (resumable)
  - Page insights and video analytics

### 9.3 Social Account API Endpoints
- [x] 9.3.1 Implement `GET /api/v1/social-accounts`
  - List connected accounts with platform filter
- [x] 9.3.2 Implement `GET /api/v1/social-accounts/{id}`
  - Get specific account details
- [x] 9.3.3 Implement `POST /api/v1/social-accounts/connect/{platform}`
  - Initiate OAuth flow, return authorization URL
- [x] 9.3.4 Implement `GET /api/v1/social-accounts/callback/{platform}`
  - Handle OAuth callback, redirect to frontend
- [x] 9.3.5 Implement `POST /api/v1/social-accounts/callback/{platform}/manual`
  - SPA-friendly manual callback endpoint
- [x] 9.3.6 Implement `DELETE /api/v1/social-accounts/{id}`
  - Disconnect social account
- [x] 9.3.7 Implement `POST /api/v1/social-accounts/{id}/refresh`
  - Manual token refresh

> ✅ **Section 9 Complete** - OAuth service with encrypted token storage, 4 platform clients (YouTube, TikTok, Instagram, Facebook), and full API endpoints

---

## 10. Posting & Scheduling

### 10.1 Posting Service
- [x] 10.1.1 Create `backend/app/services/post.py`
  - `get_by_id`, `get_user_posts` with filters
  - `get_scheduled_posts`, `get_pending_scheduled_posts`
  - `get_calendar_data` - Monthly calendar view
  - `create_post`, `update_post`, `delete_post`
  - `start_publishing`, `update_platform_status`, `complete_publishing`
  - `get_user_post_stats`

### 10.2 Platform Publishers
- [x] 10.2.1 Create `backend/app/services/publishers/__init__.py`
  - `get_publisher()` factory function
- [x] 10.2.2 Create `backend/app/services/publishers/base.py`
  - `BasePublisher` abstract class
  - `PublishRequest`, `PublishResult` dataclasses
  - Content validation and formatting helpers
- [x] 10.2.3 Create `backend/app/services/publishers/youtube.py`
  - Upload via YouTube Data API
  - Title, description, tags, privacy settings
- [x] 10.2.4 Create `backend/app/services/publishers/tiktok.py`
  - Upload via TikTok Content Posting API
  - Caption with hashtags, privacy settings
- [x] 10.2.5 Create `backend/app/services/publishers/instagram.py`
  - Upload Reels via Meta Graph API
  - Requires public video URL
- [x] 10.2.6 Create `backend/app/services/publishers/facebook.py`
  - Upload to Facebook Page via Graph API
  - Resumable upload protocol

### 10.3 Scheduling Workers
- [x] 10.3.1 Create `backend/app/workers/post_worker.py`
  - `publish_scheduled_post` - RQ job for scheduled posts
  - `publish_post_now` - Immediate publish job
  - `process_scheduled_posts` - Batch processing
  - Cross-platform publishing with per-platform status tracking

### 10.4 Post API Endpoints
- [x] 10.4.1 Implement `GET /api/v1/posts`
  - List all posts with status/platform filters
- [x] 10.4.2 Implement `GET /api/v1/posts/scheduled`
  - List scheduled posts with date range filter
- [x] 10.4.3 Implement `GET /api/v1/posts/calendar/{year}/{month}`
  - Calendar view data grouped by day
- [x] 10.4.4 Implement `POST /api/v1/posts`
  - Create post with cross-posting support
  - Platform-specific overrides
  - Automatic job scheduling
- [x] 10.4.5 Implement `GET /api/v1/posts/{id}`
  - Get post details with platform statuses
- [x] 10.4.6 Implement `PATCH /api/v1/posts/{id}`
  - Update post (reschedule, change content)
- [x] 10.4.7 Implement `DELETE /api/v1/posts/{id}`
  - Delete post (not while publishing)
- [x] 10.4.8 Implement `POST /api/v1/posts/{id}/publish`
  - Publish immediately
- [x] 10.4.9 Implement `GET /api/v1/posts/stats/me`
  - User post statistics

> ✅ **Section 10 Complete** - Post service with cross-posting, 4 platform publishers, scheduling workers, and full API endpoints with calendar view

---

## 11. Analytics System

### 11.1 Analytics Service
- [x] 11.1.1 Create `backend/app/services/analytics.py`
  - `get_post_analytics` - Get analytics for a specific post
  - `get_latest_post_analytics` - Get most recent analytics
  - `get_user_analytics_overview` - Aggregated metrics overview
  - `get_time_series` - Time series data for charts
  - `get_top_performing` - Top performing posts by metric
  - `get_posting_heatmap` - Heatmap data for optimal posting times
  - `store_analytics` - Store fetched analytics data
  - `get_platform_comparison` - Compare performance across platforms

### 11.2 Platform Analytics Fetchers
- [x] 11.2.1 Create `backend/app/services/analytics_fetchers/__init__.py`
  - Factory function `get_fetcher()` for platform-specific fetchers
- [x] 11.2.2 Create `backend/app/services/analytics_fetchers/base.py`
  - `BaseFetcher` abstract class with `FetchResult` dataclass
- [x] 11.2.3 Create `backend/app/services/analytics_fetchers/youtube.py`
  - YouTube Data API v3 + YouTube Analytics API integration
- [x] 11.2.4 Create `backend/app/services/analytics_fetchers/tiktok.py`
  - TikTok Content Posting API integration
- [x] 11.2.5 Create `backend/app/services/analytics_fetchers/instagram.py`
  - Meta Graph API for Instagram Insights
- [x] 11.2.6 Create `backend/app/services/analytics_fetchers/facebook.py`
  - Meta Graph API for Facebook video insights

### 11.3 Analytics Workers
- [x] 11.3.1 Create `backend/app/workers/analytics_worker.py`
  - `sync_post_analytics_job` - Sync single post analytics
  - `sync_user_analytics_job` - Sync all user posts
  - `daily_analytics_sync_job` - Daily scheduled sync for all users
  - `sync_channel_analytics_job` - Fetch channel-level analytics
  - Queue helper functions for job management

### 11.4 Analytics API Endpoints
- [x] 11.4.1 Implement `GET /api/v1/analytics/overview`
  - Dashboard overview stats with period selection
  - Total views, likes, shares across all platforms
- [x] 11.4.2 Implement `GET /api/v1/analytics/posts/{post_id}`
  - Detailed analytics for specific post by platform
- [x] 11.4.3 Implement `GET /api/v1/analytics/platforms`
  - Platform comparison data
- [x] 11.4.4 Implement `GET /api/v1/analytics/time-series`
  - Time series data for charts
  - Configurable metric, days, and platform filter
- [x] 11.4.5 Implement `GET /api/v1/analytics/top-performing`
  - Top performing videos/posts
  - Sortable by metric (views, likes, comments, shares)
- [x] 11.4.6 Implement `GET /api/v1/analytics/heatmap`
  - Posting time heatmap data
  - Best times to post recommendations
- [x] 11.4.7 Implement `POST /api/v1/analytics/sync`
  - Trigger manual analytics sync for all posts
- [x] 11.4.8 Implement `POST /api/v1/analytics/sync/{post_id}`
  - Trigger analytics sync for specific post
- [x] 11.4.9 Implement `GET /api/v1/analytics/channels` (Premium)
  - Channel/account-level analytics across platforms

---

## 12. AI Suggestions Engine

### 12.1 Suggestions Service
- [x] 12.1.1 Create `backend/app/services/suggestions.py`
  - `get_user_suggestions` - Retrieve suggestions with filters
  - `get_suggestion_by_id` - Get specific suggestion
  - `get_unread_count` - Count unread suggestions
  - `create_suggestion` - Generic suggestion creation
  - `create_posting_time_suggestion` - Optimal posting time suggestions
  - `create_content_suggestion` - Content idea suggestions
  - `create_template_suggestion` - Template recommendations
  - `create_trend_alert` - Trending topic alerts
  - `create_performance_prediction` - Performance predictions
  - `create_improvement_tip` - Content improvement tips
  - `mark_as_read` / `mark_all_as_read` - Mark suggestions read
  - `dismiss_suggestion` - Dismiss suggestions
  - `mark_as_acted` - Track user actions
  - `cleanup_expired_suggestions` - Remove expired suggestions

### 12.2 AI Analysis Components
- [x] 12.2.1 Create `backend/app/services/ai_analysis/__init__.py`
  - Package initialization with exports
- [x] 12.2.2 Create `backend/app/services/ai_analysis/posting_time.py`
  - `PostingTimeAnalyzer` class
  - Analyze historical performance by posting time
  - Recommend optimal times per platform
  - Generate posting time suggestions
- [x] 12.2.3 Create `backend/app/services/ai_analysis/content.py`
  - `ContentAnalyzer` class
  - Analyze top performing content patterns
  - Use OpenAI GPT-4 to generate content ideas
  - Fallback ideas when AI unavailable
- [x] 12.2.4 Create `backend/app/services/ai_analysis/trends.py`
  - `TrendAnalyzer` class
  - Fetch trending topics (AI-generated, extensible for real APIs)
  - Match trends to user's content niche
  - Generate trend alert suggestions
- [x] 12.2.5 Create `backend/app/services/ai_analysis/predictions.py`
  - `PerformancePredictor` class
  - Predict video performance based on historical data
  - Template performance factors
  - Trend analysis (improving/declining/stable)
- [x] 12.2.6 Create `backend/app/services/ai_analysis/improvements.py`
  - `ImprovementAnalyzer` class
  - Analyze underperforming content
  - Title, description, hashtag analysis
  - AI-powered improvement suggestions

### 12.3 Suggestions Workers
- [x] 12.3.1 Create `backend/app/workers/suggestions_worker.py`
  - `generate_posting_time_suggestions_job`
  - `generate_content_suggestions_job`
  - `generate_trend_suggestions_job`
  - `generate_improvement_suggestions_job`
  - `generate_all_suggestions_job` - Generate all types
  - `daily_suggestions_job` - Daily job for all premium users
  - `cleanup_suggestions_job` - Cleanup expired suggestions
  - `queue_suggestions_generation` - Queue helper

### 12.4 Suggestions API Endpoints (Premium only)
- [x] 12.4.1 Implement `GET /api/v1/suggestions`
  - Get all suggestions for user
  - Filter by type, read status, dismissed status
- [x] 12.4.2 Implement `GET /api/v1/suggestions/unread-count`
  - Get unread suggestions count
- [x] 12.4.3 Implement `GET /api/v1/suggestions/{id}`
  - Get specific suggestion details
- [x] 12.4.4 Implement `POST /api/v1/suggestions/{id}/read`
  - Mark suggestion as read
- [x] 12.4.5 Implement `POST /api/v1/suggestions/read-all`
  - Mark all suggestions as read
- [x] 12.4.6 Implement `POST /api/v1/suggestions/{id}/dismiss`
  - Dismiss suggestion
- [x] 12.4.7 Implement `POST /api/v1/suggestions/{id}/acted`
  - Mark suggestion as acted upon
- [x] 12.4.8 Implement `GET /api/v1/suggestions/analysis/posting-times`
  - Get posting time analysis
- [x] 12.4.9 Implement `GET /api/v1/suggestions/analysis/content-ideas`
  - Get AI-generated content ideas
- [x] 12.4.10 Implement `GET /api/v1/suggestions/analysis/trends`
  - Get trending topics matched to user
- [x] 12.4.11 Implement `GET /api/v1/suggestions/analysis/predict/{video_id}`
  - Get performance prediction for a video
- [x] 12.4.12 Implement `GET /api/v1/suggestions/analysis/improvements`
  - Get improvement suggestions for underperforming content
- [x] 12.4.13 Implement `POST /api/v1/suggestions/generate`
  - Trigger background suggestion generation

---

## 13. Subscription & Billing

### 13.1 Stripe Service
- [x] 13.1.1 Create `backend/app/services/stripe_service.py`
  - `get_or_create_customer` - Stripe customer management
  - `create_checkout_session` - Create Stripe Checkout for subscription
  - `create_portal_session` - Create Customer Portal session
  - `get_subscription_status` - Get user's subscription details
  - `cancel_subscription` - Cancel subscription (immediate or at period end)
  - `reactivate_subscription` - Reactivate cancelled subscription
  - `change_plan` - Upgrade/downgrade subscription plan
  - `get_invoices` - Get invoice history
  - `get_upcoming_invoice` - Get next invoice details
  - `grant_premium` - Admin: Grant premium without payment
  - `revoke_premium` - Admin: Revoke premium access
  - `get_subscription_stats` - Admin: Get subscription statistics

### 13.2 Stripe Products Setup
- [ ] 13.2.1 Create Stripe products and prices (in Stripe Dashboard):
  - Monthly: $5/month recurring
  - Annual: $50/year recurring
- [ ] 13.2.2 Note price IDs for `STRIPE_MONTHLY_PRICE_ID` and `STRIPE_ANNUAL_PRICE_ID`

### 13.3 Webhook Handlers
- [x] 13.3.1 Create `backend/app/services/stripe_webhooks.py`
  - `verify_webhook` - Verify Stripe signature
  - `handle_event` - Route events to handlers
- [x] 13.3.2 Handle `checkout.session.completed`
  - Create/update subscription record
  - Update user role to Premium
- [x] 13.3.3 Handle `customer.subscription.created`
  - Update subscription period dates
- [x] 13.3.4 Handle `customer.subscription.updated`
  - Handle plan changes and cancellation status
  - Update user role based on status
- [x] 13.3.5 Handle `customer.subscription.deleted`
  - Mark subscription as cancelled
  - Downgrade user to Free
- [x] 13.3.6 Handle `invoice.payment_succeeded`
  - Update subscription period
  - Ensure user is premium
- [x] 13.3.7 Handle `invoice.payment_failed`
  - Mark subscription as past_due
  - Log for notification
- [x] 13.3.8 Handle `customer.updated`
  - Log customer updates

### 13.4 Subscription API Endpoints
- [x] 13.4.1 Implement `GET /api/v1/subscriptions/plans`
  - Get available subscription plans with features
- [x] 13.4.2 Implement `GET /api/v1/subscriptions/status`
  - Get current subscription status summary
- [x] 13.4.3 Implement `GET /api/v1/subscriptions/details`
  - Get detailed subscription information
- [x] 13.4.4 Implement `POST /api/v1/subscriptions/checkout`
  - Create Stripe Checkout session
  - Accept plan selection (monthly/annual)
  - Return checkout URL
- [x] 13.4.5 Implement `POST /api/v1/subscriptions/portal`
  - Create Stripe Customer Portal session
  - Return portal URL
- [x] 13.4.6 Implement `POST /api/v1/subscriptions/cancel`
  - Cancel subscription (immediate or at period end)
- [x] 13.4.7 Implement `POST /api/v1/subscriptions/reactivate`
  - Reactivate cancelled subscription
- [x] 13.4.8 Implement `POST /api/v1/subscriptions/change-plan`
  - Upgrade/downgrade subscription plan
- [x] 13.4.9 Implement `GET /api/v1/subscriptions/invoices`
  - Get invoice history
- [x] 13.4.10 Implement `GET /api/v1/subscriptions/invoices/upcoming`
  - Get upcoming invoice details
- [x] 13.4.11 Implement `POST /api/v1/subscriptions/webhook`
  - Stripe webhook handler with signature verification
- [x] 13.4.12 Implement `POST /api/v1/subscriptions/admin/grant-premium`
  - Admin: Grant premium access
- [x] 13.4.13 Implement `POST /api/v1/subscriptions/admin/revoke-premium`
  - Admin: Revoke premium access
- [x] 13.4.14 Implement `GET /api/v1/subscriptions/admin/stats`
  - Admin: Get subscription statistics (MRR, ARR, counts)

---

## 14. Notification System

### 14.1 Notification Service
- [x] 14.1.1 Create `backend/app/services/notification.py`
  - `get_user_notifications` - Get notifications with filters
  - `get_notification_by_id` - Get specific notification
  - `get_unread_count` - Count unread notifications
  - `get_unread_count_by_type` - Count by notification type
  - `create_notification` - Generic notification creation
  - Convenience methods for specific notification types:
    - `notify_video_completed`
    - `notify_video_failed`
    - `notify_post_published`
    - `notify_post_failed`
    - `notify_scheduled_post_reminder`
    - `notify_payment_success`
    - `notify_payment_failed`
    - `notify_subscription_expiring`
    - `notify_subscription_cancelled`
    - `notify_integration_error`
    - `notify_social_account_disconnected`
    - `notify_welcome`
    - `notify_system_announcement`
  - `mark_as_read` / `mark_all_as_read`
  - `dismiss_notification` / `dismiss_all`
  - `cleanup_old_notifications`
  - `broadcast_to_all_users`

### 14.2 Notification Types
- [x] 14.2.1 Notification types defined in model:
  - `video_complete` - Video generation complete
  - `video_failed` - Video generation failed
  - `post_published` - Post published successfully
  - `post_failed` - Post publishing failed
  - `scheduled_post` - Scheduled post reminder
  - `payment_success` - Payment successful
  - `payment_failed` - Payment failed
  - `subscription_expiring` - Subscription expiring soon
  - `subscription_cancelled` - Subscription cancelled
  - `integration_error` - Integration issue
  - `social_disconnect` - Social account disconnected
  - `system` - System announcements

### 14.3 Notification Triggers
- [x] 14.3.1 Service methods ready for integration with:
  - Video generation completion/failure (video_worker.py)
  - Post publishing completion/failure (post_worker.py)
  - Subscription events (stripe_webhooks.py)
  - Integration errors (validators)
  - Social account disconnection (oauth flows)

### 14.4 Notification API Endpoints
- [x] 14.4.1 Implement `GET /api/v1/notifications`
  - Get user notifications with filters (type, read, dismissed)
  - Pagination with offset/limit
  - Include unread count and has_more flag
- [x] 14.4.2 Implement `GET /api/v1/notifications/unread-count`
  - Get unread count total and by type
- [x] 14.4.3 Implement `GET /api/v1/notifications/{id}`
  - Get specific notification details
- [x] 14.4.4 Implement `POST /api/v1/notifications/{id}/read`
  - Mark single notification as read
- [x] 14.4.5 Implement `POST /api/v1/notifications/read-all`
  - Mark all notifications as read
- [x] 14.4.6 Implement `POST /api/v1/notifications/{id}/dismiss`
  - Dismiss single notification
- [x] 14.4.7 Implement `POST /api/v1/notifications/dismiss-all`
  - Dismiss all notifications
- [x] 14.4.8 Implement `POST /api/v1/notifications/admin/broadcast`
  - Admin: Broadcast notification to all users

---

## 15. Admin Panel

### 15.1 Admin Service
- [x] 15.1.1 Create `backend/app/services/admin.py`
  - User management:
    - `get_users` - List users with filters and pagination
    - `get_user_details` - Get detailed user info with stats
    - `update_user_role` - Change user role
    - `update_user_status` - Enable/disable user
    - `delete_user` - Soft or hard delete user
  - Platform statistics:
    - `get_platform_stats` - Overall platform stats
    - `get_activity_stats` - Activity over time (signups, videos, posts)
    - `get_top_users` - Top users by metric
  - System settings:
    - `get_app_settings` - Get all settings
    - `get_setting` / `set_setting` / `delete_setting` - CRUD for settings
  - Content management:
    - `get_recent_videos` - Recently created videos
    - `get_recent_posts` - Recently created posts
    - `get_failed_jobs` - Failed background jobs
  - Template stats:
    - `get_template_stats` - Template usage statistics

### 15.2 Admin API Endpoints
- [x] 15.2.1 User Management:
  - `GET /api/v1/admin/users` - List users with search, filters, pagination
  - `GET /api/v1/admin/users/{id}` - Get user details with stats
  - `PATCH /api/v1/admin/users/{id}/role` - Update user role
  - `PATCH /api/v1/admin/users/{id}/status` - Enable/disable user
  - `DELETE /api/v1/admin/users/{id}` - Delete user (soft/hard)
- [x] 15.2.2 Platform Statistics:
  - `GET /api/v1/admin/stats` - Platform-wide statistics
  - `GET /api/v1/admin/stats/activity` - Activity over time
  - `GET /api/v1/admin/stats/top-users` - Top users by metric
  - `GET /api/v1/admin/stats/templates` - Template usage stats
- [x] 15.2.3 System Settings:
  - `GET /api/v1/admin/settings` - Get all settings
  - `GET /api/v1/admin/settings/{key}` - Get specific setting
  - `POST /api/v1/admin/settings` - Set a setting
  - `DELETE /api/v1/admin/settings/{key}` - Delete setting
- [x] 15.2.4 Content Management:
  - `GET /api/v1/admin/content/videos` - Recent videos
  - `GET /api/v1/admin/content/posts` - Recent posts
  - `GET /api/v1/admin/content/failed-jobs` - Failed jobs

---

## 16. Frontend Foundation

### 16.1 React Project Setup
- [x] 16.1.1 Create Vite React project with TypeScript
  - `package.json` with all dependencies
  - `vite.config.ts` with path aliases and proxy
  - `tsconfig.json` and `tsconfig.node.json`
- [x] 16.1.2 Install dependencies (defined in package.json):
  - react-router-dom, @tanstack/react-query, axios
  - tailwindcss, postcss, autoprefixer
  - lucide-react, recharts
  - react-i18next, i18next
  - date-fns, zod, react-hook-form
  - firebase
  - All Radix UI primitives for shadcn/ui

### 16.2 Tailwind CSS & shadcn/ui
- [x] 16.2.1 Configure Tailwind CSS:
  - `tailwind.config.js` with custom theme
  - `postcss.config.js`
  - CSS variables in `src/index.css`
  - Dark mode as default
  - Synthora brand colors (cyan, violet, fuchsia gradient)
  - Custom animations (fade, slide, glow, shimmer)
- [x] 16.2.2 Create shadcn/ui components:
  - Button, Input, Label, Card
  - Dialog, DropdownMenu, Select
  - Tabs, Switch, Progress
  - Avatar, Separator, ScrollArea, Tooltip
  - `components.json` for shadcn CLI

### 16.3 Project Structure & Routing
- [x] 16.3.1 Create folder structure:
  ```
  frontend/src/
  ├── components/ui/    # shadcn components
  ├── contexts/         # Auth, Theme contexts
  ├── hooks/            # Custom hooks
  ├── layouts/          # Auth, Dashboard layouts
  ├── lib/              # api, firebase, utils
  ├── pages/            # All page components
  ├── router/           # React Router config
  └── types/            # TypeScript types
  ```
- [x] 16.3.2 Create `src/router/index.tsx`:
  - Lazy-loaded pages
  - RequireAuth guard
  - RequireAdmin guard
  - RedirectIfAuth guard
  - All routes defined

### 16.4 Core Libraries & Contexts
- [x] 16.4.1 Create `src/lib/api.ts`:
  - Axios instance with auth interceptor
  - Token injection from Firebase
  - Error handling with redirect on 401
- [x] 16.4.2 Create `src/lib/firebase.ts`:
  - Firebase initialization
  - Google Sign-In
  - Auth state subscription
  - Token retrieval
- [x] 16.4.3 Create `src/lib/utils.ts`:
  - cn() for class merging
  - Date formatting utilities
  - Number formatting utilities
  - Platform helpers
- [x] 16.4.4 Create `src/contexts/AuthContext.tsx`:
  - Firebase auth state management
  - User role tracking (useHasRole, useIsPremium, useIsAdmin)
  - Login/logout functions
  - User refresh
- [x] 16.4.5 Create `src/contexts/ThemeContext.tsx`:
  - Dark/light/system mode
  - LocalStorage persistence

### 16.5 Layouts & Pages
- [x] 16.5.1 Create `src/layouts/AuthLayout.tsx`:
  - Gradient background with grid pattern
  - Glowing orbs effect
- [x] 16.5.2 Create `src/layouts/DashboardLayout.tsx`:
  - Sidebar navigation (CapCut-inspired)
  - Header with notifications and user menu
  - Responsive mobile menu
  - User tier badge
- [x] 16.5.3 Create placeholder pages:
  - Auth: LoginPage, SetupPage
  - Dashboard: DashboardPage, CreateVideoPage, VideosPage, VideoDetailPage
  - Templates, Posts, Calendar, Analytics
  - Integrations, SocialAccounts, Suggestions, Settings
  - Admin: AdminDashboardPage, AdminUsersPage, AdminSettingsPage
  - Errors: NotFoundPage

### 16.6 Entry Point & Types
- [x] 16.6.1 Create `src/main.tsx`:
  - QueryClientProvider
  - ThemeProvider
  - AuthProvider
  - TooltipProvider
  - RouterProvider
  - Toast notifications
- [x] 16.6.2 Create `src/types/index.ts`:
  - User, Integration, Template types
  - Video, Post, SocialAccount types
  - Analytics, Subscription types
  - Notification, Suggestion types
  - API response types

### 16.7 Layout Components
- [ ] 16.7.1 Create `Sidebar.tsx` - Main navigation sidebar
- [ ] 16.7.2 Create `Header.tsx` - Top header with notifications, user menu
- [ ] 16.7.3 Create `MainLayout.tsx` - Dashboard layout wrapper
- [ ] 16.7.4 Create `NotificationBell.tsx` - Notification dropdown

### 16.8 i18n Setup
- [ ] 16.8.1 Create `frontend/src/i18n/index.ts` - i18next configuration
- [ ] 16.8.2 Create `frontend/src/i18n/locales/en.json` - English translations
- [ ] 16.8.3 Set up translation keys structure

---

## 17. Frontend Pages

### 17.1 API Services Layer
- [x] 17.1.1 Create API service files:
  - `src/services/auth.ts` - Login, logout, setup
  - `src/services/integrations.ts` - CRUD, validation, readiness
  - `src/services/templates.ts` - CRUD, duplicate, categories
  - `src/services/videos.ts` - CRUD, generate, status, daily limit
  - `src/services/socialAccounts.ts` - OAuth, disconnect
  - `src/services/posts.ts` - CRUD, publish, calendar
  - `src/services/analytics.ts` - Overview, time series, heatmap
  - `src/services/suggestions.ts` - AI recommendations
  - `src/services/subscriptions.ts` - Stripe checkout, portal
  - `src/services/notifications.ts` - CRUD, mark read
  - `src/services/admin.ts` - User management, stats, settings

### 17.2 React Query Hooks
- [x] 17.2.1 Create `src/hooks/useIntegrations.ts`:
  - `useIntegrations`, `useAvailableIntegrations`
  - `useAddIntegration`, `useDeleteIntegration`
  - `useValidateIntegration`, `useToggleIntegration`
  - `useIntegrationReadiness`
- [x] 17.2.2 Create `src/hooks/useTemplates.ts`:
  - `useTemplates`, `useTemplate`
  - `useCreateTemplate`, `useUpdateTemplate`
  - `useDeleteTemplate`, `useDuplicateTemplate`
- [x] 17.2.3 Create `src/hooks/useVideos.ts`:
  - `useVideos`, `useVideo`, `useVideoStatus`
  - `useDailyLimit`, `useGenerateVideo`
  - `useRetryVideo`, `useSwapIntegration`

### 17.3 Integrations Page
- [x] 17.3.1 Create full `IntegrationsPage.tsx`:
  - Integration cards with status, validation, toggle
  - Add integration dialog with provider selection
  - Category tabs (Script, Voice, Media, Video AI, Assembly)
  - Readiness progress card
  - API key reveal with eye icon
  - Delete/validate/toggle actions

### 17.4 Video Creation Page
- [x] 17.4.1 Create full `CreateVideoPage.tsx`:
  - Two-step wizard (template → topic)
  - Template selection with system/user tabs
  - Topic input with custom instructions
  - Daily limit display for free users
  - Integration readiness check
  - Progress steps indicator

### 17.5 Videos Pages
- [x] 17.5.1 Create full `VideosPage.tsx`:
  - Video grid with thumbnails
  - Status badges (processing, completed, failed)
  - Progress overlay for processing videos
  - Filter by status
  - Delete confirmation dialog
- [x] 17.5.2 Create full `VideoDetailPage.tsx`:
  - Video player for completed videos
  - Progress steps visualization
  - Error display with full payload
  - Retry/swap integration for failures
  - Download and share actions
  - Status sidebar with details

### 17.6 Remaining Pages (Placeholders)
- [x] 17.6.1 Dashboard with quick stats and actions
- [x] 17.6.2 Templates page (placeholder)
- [x] 17.6.3 Posts page (placeholder)
- [x] 17.6.4 Calendar page (placeholder)
- [x] 17.6.5 Analytics page (placeholder)
- [x] 17.6.6 Social Accounts page (placeholder)
- [x] 17.6.7 Suggestions page with premium gate
- [x] 17.6.8 Settings page (placeholder)
- [x] 17.6.9 Admin pages (Dashboard, Users, Settings)

### 17.9 AI Suggestions (Premium)
- [ ] 17.9.1 Create `SuggestionsPanel.tsx`
  - Display in dashboard or separate page
  - Categorized suggestions
  - Mark as read/dismiss

### 17.10 Settings
- [ ] 17.10.1 Create `SettingsPage.tsx`
  - Tabs layout
- [ ] 17.10.2 Create settings tabs:
  - `ProfileSettings.tsx`
  - `IntegrationsSettings.tsx`
  - `SocialAccountsSettings.tsx`
  - `SubscriptionSettings.tsx`
  - `AppearanceSettings.tsx` (theme toggle)
  - `NotificationSettings.tsx`

### 17.11 Admin Pages
- [ ] 17.11.1 Create `AdminDashboard.tsx`
  - Platform statistics
  - Revenue overview
- [ ] 17.11.2 Create `AdminUsersPage.tsx`
  - User list with search/filter
  - User detail modal
  - Role management
- [ ] 17.11.3 Create `AdminTemplatesPage.tsx`
  - System template management
- [ ] 17.11.4 Create `AdminSettingsPage.tsx`
  - System settings
  - Feature flags

### 17.12 Error Pages
- [ ] 17.12.1 Create `NotFoundPage.tsx` (404)
- [ ] 17.12.2 Create `ErrorPage.tsx` (500)
- [ ] 17.12.3 Create `UnauthorizedPage.tsx` (403)

---

## 18. Settings & Subscription Pages

### 18.1 Subscription Hooks
- [x] 18.1.1 Create `src/hooks/useSubscription.ts`:
  - `usePlans` - Fetch available plans
  - `useSubscriptionStatus` - Get current status
  - `useSubscriptionDetails` - Get full details
  - `useInvoices` - Get invoice history
  - `useCreateCheckout` - Start Stripe checkout
  - `useCreatePortal` - Open billing portal
  - `useCancelSubscription` - Cancel subscription
  - `useReactivateSubscription` - Reactivate
  - `useChangePlan` - Switch plans
- [x] 18.1.2 Create `src/hooks/useSocialAccounts.ts`:
  - `useSocialAccounts` - List connected accounts
  - `useInitiateOAuth` - Start OAuth flow
  - `useDisconnectAccount` - Disconnect account
  - `useRefreshToken` - Refresh expired token

### 18.2 Settings Page
- [x] 18.2.1 Create full `SettingsPage.tsx` with tabs:
  - **Profile Tab**: User info from Google, avatar, member since
  - **Subscription Tab**: Current plan, upgrade options, cancel/reactivate
  - **Appearance Tab**: Theme toggle (dark/light/system)
  - **Notifications Tab**: Email and in-app notification preferences
- [x] 18.2.2 Stripe integration:
  - Checkout redirect for upgrades
  - Billing portal for management
  - Cancel with confirmation dialog
  - Reactivate for canceled subscriptions

### 18.3 Social Accounts Page
- [x] 18.3.1 Create full `SocialAccountsPage.tsx`:
  - Connected account cards with status
  - Platform icons and colors (YouTube, TikTok, Instagram, Facebook)
  - Token expiration display
  - Reconnect for expired tokens
  - Disconnect with confirmation
  - Connect cards for available platforms

### 18.4 Templates Page
- [x] 18.4.1 Create full `TemplatesPage.tsx`:
  - Template cards with config preview
  - System vs Personal tabs
  - Search functionality
  - Quick stats (duration, aspect ratio, voice, colors)
  - Use template → navigate to create
  - Duplicate template
  - Delete personal templates
  - Template detail dialog

---

## 19. Testing & Quality ✅

### 19.1 Backend Testing
- [x] 19.1.1 Set up pytest configuration (`backend/pytest.ini`)
- [x] 19.1.2 Create test database fixtures (`backend/tests/conftest.py`)
- [x] 19.1.3 Write unit tests for services:
  - Security tests (`test_security.py`)
  - Limits service tests (`test_limits.py`)
  - Template validator tests (`test_template_validator.py`)
  - Utility tests (`test_utils.py`)
- [x] 19.1.4 Write API endpoint tests:
  - Health endpoint tests (`test_health.py`)
  - Templates API tests (`test_templates_api.py`)
- [x] 19.1.5 Set up test coverage reporting (pytest-cov)

### 19.2 Frontend Testing
- [x] 19.2.1 Set up Vitest configuration (`frontend/vitest.config.ts`)
- [x] 19.2.2 Write component tests:
  - Button component tests (`Button.test.tsx`)
  - Test utilities (`src/test/utils.tsx`)
- [x] 19.2.3 Write hook tests (`useAuth.test.ts`)
- [x] 19.2.4 Write utility tests (`utils.test.ts`)
- [x] 19.2.5 Set up test coverage reporting (@vitest/coverage-v8)

### 19.3 Code Quality
- [x] 19.3.1 Set up backend linting (`backend/ruff.toml`)
- [x] 19.3.2 Set up backend type checking (`backend/mypy.ini`)
- [x] 19.3.3 Set up frontend linting (`frontend/.eslintrc.cjs`)
- [x] 19.3.4 Set up frontend type checking (tsc via package.json)
- [x] 19.3.5 Create pre-commit hooks (`.pre-commit-config.yaml`)

---

## 20. Deployment & CI/CD

### 19.1 GitHub Actions
- [ ] 19.1.1 Create `.github/workflows/ci.yml`:
  ```yaml
  - Backend lint (ruff)
  - Backend type check (mypy)
  - Backend tests (pytest)
  - Frontend lint (eslint)
  - Frontend type check (tsc)
  - Frontend tests (vitest)
  - Build check
  ```
- [ ] 19.1.2 Configure workflow triggers (PR, push to main)

### 19.2 Railway Deployment
- [ ] 19.2.1 Connect GitHub repository to Railway
- [ ] 19.2.2 Configure backend service
  - Set build command
  - Set start command
  - Configure environment variables
- [ ] 19.2.3 Configure frontend service
  - Set build command
  - Configure static file serving
- [ ] 19.2.4 Configure worker service
  - Same codebase, different start command
- [ ] 19.2.5 Add PostgreSQL plugin
- [ ] 19.2.6 Configure all environment variables
- [ ] 19.2.7 Set up custom domain (optional, later)
- [ ] 19.2.8 Configure CORS with Railway URLs

### 19.3 Database Migrations
- [ ] 19.3.1 Configure Alembic to run on deploy
- [ ] 19.3.2 Test migration rollback procedures

---

## 20. Final Polish

### 20.1 Logo & Branding
- [ ] 20.1.1 Generate abstract/geometric logo for Synthora
- [ ] 20.1.2 Create favicon (multiple sizes)
- [ ] 20.1.3 Create social media preview image (og:image)
- [ ] 20.1.4 Update landing page with final branding

### 20.2 SEO & Meta
- [ ] 20.2.1 Add meta tags to landing page
- [ ] 20.2.2 Create robots.txt
- [ ] 20.2.3 Create sitemap (if needed)

### 20.3 Performance
- [ ] 20.3.1 Implement lazy loading for routes
- [ ] 20.3.2 Optimize images
- [ ] 20.3.3 Configure caching headers
- [ ] 20.3.4 Test and optimize API response times

### 20.4 Documentation
- [ ] 20.4.1 Update README with final setup instructions
- [ ] 20.4.2 Document API endpoints (OpenAPI/Swagger)
- [ ] 20.4.3 Create user guide (optional)

### 20.5 Security Audit
- [ ] 20.5.1 Review authentication flow
- [ ] 20.5.2 Verify encryption implementation
- [ ] 20.5.3 Test rate limiting
- [ ] 20.5.4 Check for common vulnerabilities (OWASP)
- [ ] 20.5.5 Verify CORS configuration

### 20.6 Final Testing
- [ ] 20.6.1 End-to-end user flow testing
- [ ] 20.6.2 Cross-browser testing
- [ ] 20.6.3 Mobile responsiveness testing
- [ ] 20.6.4 Load testing (basic)

---

## Progress Tracking

| Section | Status | Completion |
|---------|--------|------------|
| 1. Project Setup | ⬜ Not Started | 0% |
| 2. Backend Foundation | ⬜ Not Started | 0% |
| 3. Database & Models | ⬜ Not Started | 0% |
| 4. Authentication | ⬜ Not Started | 0% |
| 5. User Management | ⬜ Not Started | 0% |
| 6. Integration Management | ⬜ Not Started | 0% |
| 7. Template System | ⬜ Not Started | 0% |
| 8. Video Generation | ⬜ Not Started | 0% |
| 9. Social Media | ⬜ Not Started | 0% |
| 10. Posting & Scheduling | ⬜ Not Started | 0% |
| 11. Analytics | ⬜ Not Started | 0% |
| 12. AI Suggestions | ⬜ Not Started | 0% |
| 13. Subscription | ⬜ Not Started | 0% |
| 14. Notifications | ⬜ Not Started | 0% |
| 15. Admin Panel | ⬜ Not Started | 0% |
| 16. Frontend Foundation | ⬜ Not Started | 0% |
| 17. Frontend Pages | ⬜ Not Started | 0% |
| 18. Testing | ⬜ Not Started | 0% |
| 19. Deployment | ⬜ Not Started | 0% |
| 20. Final Polish | ⬜ Not Started | 0% |

**Overall Progress: 0%**

---

## Notes

- Reference `ai-overview.md` for detailed specifications
- Update this checklist as tasks are completed
- Add new tasks as needed during implementation
- Each checkbox represents a discrete, completable task

