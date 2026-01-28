# Synthora - AI Video Generator Platform

## Project Overview

**Synthora** is a SaaS web application that enables users to generate viral videos using multiple AI integrations, post them to social media platforms, and analyze performance with AI-powered suggestions for improvement.

**Created:** January 21, 2026  
**Status:** Planning Phase  
**Deployment Target:** Railway with GitHub Integration

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Architecture Overview](#architecture-overview)
3. [User System & Roles](#user-system--roles)
4. [Core Features](#core-features)
5. [AI Integrations](#ai-integrations)
6. [Social Media Integrations](#social-media-integrations)
7. [Database Schema](#database-schema)
8. [API Structure](#api-structure)
9. [Frontend Architecture](#frontend-architecture)
10. [Security Considerations](#security-considerations)
11. [Deployment Configuration](#deployment-configuration)
12. [Environment Variables](#environment-variables)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | Python 3.11+ / FastAPI | REST API, business logic |
| **Frontend** | React 18 (Vite) | Single Page Application |
| **UI Library** | shadcn/ui + Tailwind CSS | Component library & styling |
| **Database** | PostgreSQL 15+ | Primary data store |
| **Queue System** | RQ (Redis Queue) | Background job processing |
| **Cache/Queue Backend** | Upstash Redis | Serverless Redis |
| **File Storage** | Google Cloud Storage | Video & media storage |
| **Authentication** | Firebase Authentication | Google Sign-In, session management |
| **Payments** | Stripe | Subscription billing |
| **Deployment** | Railway | Hosting & infrastructure |
| **CI/CD** | GitHub Actions + Railway | Testing & auto-deployment |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAILWAY PROJECT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │   Frontend      │    │    Backend      │    │    Worker       │        │
│  │   (React)       │───▶│   (FastAPI)     │───▶│   (RQ)          │        │
│  │                 │    │                 │    │                 │        │
│  │  - Dashboard    │    │  - REST API     │    │  - Video Gen    │        │
│  │  - Templates    │    │  - Auth         │    │  - Post Publish │        │
│  │  - Analytics    │    │  - Business     │    │  - Analytics    │        │
│  │  - Settings     │    │    Logic        │    │    Sync         │        │
│  └─────────────────┘    └────────┬────────┘    └────────┬────────┘        │
│                                  │                      │                  │
│                                  ▼                      │                  │
│                         ┌─────────────────┐             │                  │
│                         │   PostgreSQL    │◀────────────┘                  │
│                         │   (Railway)     │                                │
│                         └─────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ Upstash Redis │          │ Google Cloud  │          │   External    │
│ (Serverless)  │          │   Storage     │          │   APIs        │
│               │          │               │          │               │
│ - Job Queue   │          │ - Videos      │          │ - OpenAI      │
│ - Rate Limit  │          │ - Thumbnails  │          │ - ElevenLabs  │
│   Cache       │          │ - Media       │          │ - Pexels      │
└───────────────┘          └───────────────┘          │ - Video AIs   │
                                                      │ - Social APIs │
                                                      └───────────────┘
```

### Monorepo Structure

```
Videogenerator/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── core/              # Config, security, dependencies
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   │   └── generation/    # Video generation pipeline
│   │   │       ├── modular_pipeline.py
│   │   │       └── state_manager.py
│   │   ├── integrations/      # External API integrations
│   │   │   └── providers/     # Modular provider implementations
│   │   │       ├── base.py    # Abstract base classes
│   │   │       ├── factory.py # Provider factory
│   │   │       ├── script/    # Script providers (OpenAI, Anthropic)
│   │   │       ├── voice/     # Voice providers (ElevenLabs, OpenAI TTS)
│   │   │       ├── media/     # Media providers (Pexels)
│   │   │       ├── video_ai/  # Video AI providers (stubs)
│   │   │       └── assembly/  # Assembly providers (FFmpeg)
│   │   ├── workers/           # RQ job definitions
│   │   │   ├── video_worker.py
│   │   │   ├── video_scheduler.py
│   │   │   └── stuck_job_monitor.py
│   │   └── utils/             # Helpers & utilities
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Backend tests
│   ├── requirements.txt
│   └── Procfile
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API client services
│   │   ├── stores/            # State management
│   │   ├── lib/               # Utilities
│   │   └── i18n/              # Internationalization
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── ai-planning/               # Planning documents
│   ├── ai-overview.md         # This file
│   └── todo-synthora.md       # Implementation checklist
│
├── .github/
│   └── workflows/             # GitHub Actions
│       └── ci.yml
│
├── .env.example               # Environment template
├── railway.json               # Railway configuration
└── README.md
```

---

## User System & Roles

### Roles & Permissions

| Role | Description | Permissions |
|------|-------------|-------------|
| **Admin** | System administrator | Full access, user management, system templates, revenue dashboard |
| **Free** | Free tier user | Limited features, 1 video/day |
| **Premium** | Paid subscriber | Full access to all features |

### Feature Comparison

| Feature | Free | Premium | Admin |
|---------|------|---------|-------|
| Video Generation | 1/day | Unlimited | Unlimited |
| Concurrent Generation | 1 | 1 | 1 |
| Video Retention | 30 days | Indefinite | Indefinite |
| Scheduling | ❌ | ✅ | ✅ |
| AI Suggestions | ❌ | ✅ | ✅ |
| All Integrations | ✅ | ✅ | ✅ |
| Personal Templates | ✅ | ✅ | ✅ |
| System Templates Management | ❌ | ❌ | ✅ |
| User Management | ❌ | ❌ | ✅ |
| Revenue Dashboard | ❌ | ❌ | ✅ |

### Subscription Pricing

| Plan | Price | Billing |
|------|-------|---------|
| Monthly | $5/month | Recurring |
| Annual | $50/year | Recurring (saves ~17%) |

- No free trial
- Managed via Stripe
- First user becomes Admin (setup wizard)

---

## Core Features

### 1. Dashboard
- Overview statistics (videos created, posts published, engagement)
- Recent videos gallery
- Quick actions (create video, schedule post)
- Notification center

### 2. Templates Page
- Browse system templates (5 pre-built general-purpose)
- Browse/manage personal templates
- Full template customization
- Template versioning

#### Template Schema

| Category | Parameters |
|----------|------------|
| **Basic Info** | name, description, category, target_platforms, tags |
| **Video Structure** | hook_style, narrative_structure, num_scenes, duration_range, pacing |
| **Visual Style** | aspect_ratio, color_palette, visual_aesthetic, transitions, filter_mood |
| **Text & Captions** | caption_style, font_style, text_position, hook_text_overlay |
| **Audio** | voice_gender, voice_tone, voice_speed, music_mood, sound_effects |
| **Script/Prompt** | script_structure_prompt, tone_instructions, cta_type, cta_placement |
| **Platform Optimization** | thumbnail_style, suggested_hashtags, optimal_post_times |
| **Ownership** | is_system, owner_user_id, is_public, version |

### 3. Video Generation Page
6-step flow:
1. Select Template
2. Customize Settings
3. Enter Prompt/Topic
4. Preview & Confirm
5. Generation Progress (real-time)
6. Review & Download

#### Generation Pipeline States

```
PENDING → QUEUED → PROCESSING → [Step States] → COMPLETED
                              ↓                    ↑
                           FAILED ──────────────────┘ (retry)
                              ↓
                          CANCELLED
```

#### Step States (sequential)
1. `script_generating` → `script_completed`
2. `voice_generating` → `voice_completed`
3. `media_fetching` → `media_completed`
4. `video_ai_generating` → `video_ai_completed` (optional)
5. `assembly_processing` → `assembly_completed`

#### Pipeline Features
- **State Machine:** `PipelineStateManager` tracks step progress
- **Concurrency:** Max 1 active generation per user
- **Resume:** Failed videos can resume from last completed step
- **Cancel:** Users can cancel in-progress generations
- **Stuck Detection:** Auto-cancel after 30 minutes of no progress
- **Subtitle Sync:** Voice timing data used to generate ASS subtitles

#### Error Handling
- Immediate fail on step error
- Full error payload saved to `generation_state`
- Manual retry with optional provider swap
- Graceful skip if scheduled video is deleted

#### API Logging
All external API requests are logged to `api_request_logs`:
- Full request/response bodies (sensitive data masked)
- Duration, status code, error details
- Linked to user, video, and generation step

### 4. Posting Page
- Video selection gallery
- Multi-platform selection (YouTube, TikTok, Instagram, Facebook)
- Unified captions with per-platform overrides
- Post now or schedule (Premium)
- AI-suggested optimal times (Premium)

### 5. Scheduled Posts Management
- Calendar view
- List view
- Toggle between views
- Post statuses: draft, scheduled, publishing, published, failed, cancelled

### 6. Analytics Page
**Metrics tracked:**
- Views, Likes, Shares (high priority)
- Comments, Watch Time, Avg View Duration, Retention Rate (medium)
- Saves, CTR, Follower Growth, Reach/Impressions (low)

**Visualizations:**
- Summary cards
- Time-series charts
- Platform comparison
- Top performing videos
- Engagement rate trends
- Posting time heatmap

**Sync frequency:** Daily auto-sync + user-triggered refresh

### 7. AI Suggestions (Premium)
- Optimal posting time recommendations
- Content recommendations based on performance
- Template suggestions
- Trend alerts
- Performance predictions
- Improvement tips (hook retention, etc.)

### 8. Settings Page
- Profile management
- Integration management (API keys)
- Social account connections
- Subscription management (Stripe)
- Theme toggle (dark/light)
- Notification preferences

### 9. Admin Panel
- User management (view, edit roles, ban)
- System templates management
- Platform-wide analytics
- Revenue dashboard (subscribers, MRR, churn)
- System settings & feature flags

---

## AI Integrations

### Modular Provider Architecture (Updated Jan 2026)

The video generation system uses a **modular provider pattern** that allows:
- Independent, swappable providers per category
- User-configurable default providers
- Runtime provider selection
- Easy addition of new providers

### Provider Categories

| # | Category | Purpose | Available Providers |
|---|----------|---------|-------------------|
| 1 | **Script/Text AI** | Generate video scripts | `openai_gpt` (GPT-4o), `anthropic` (Claude) |
| 2 | **Voice AI** | Generate voiceover with timing | `elevenlabs`, `openai_tts` |
| 3 | **Stock Media** | Background videos/images | `pexels` |
| 4 | **Video AI** | AI-generated video clips (optional) | `openai_sora` (stub), `runway` (stub), `luma` (stub) |
| 5 | **Video Assembly** | Compile final video with subtitles | `ffmpeg` (local) |

### Provider Class Hierarchy

```
BaseProvider (abstract)
├── ScriptProvider
│   ├── OpenAIGPTProvider
│   └── AnthropicProvider
├── VoiceProvider
│   ├── ElevenLabsProvider
│   └── OpenAITTSProvider
├── MediaProvider
│   └── PexelsProvider
├── VideoAIProvider
│   ├── OpenAISoraProvider (stub)
│   ├── RunwayProvider (stub)
│   └── LumaProvider (stub)
└── AssemblyProvider
    └── FFmpegProvider
```

### Provider Factory Pattern

```python
# Get provider by name
provider = factory.get_provider("openai_gpt", api_key, config)

# Get available providers for category
providers = factory.get_providers_for_category(IntegrationCategory.SCRIPT)

# Get provider info with pricing
info = ProviderFactory.get_provider_info("elevenlabs")
```

### User Generation Settings

Users can configure default providers per category in Settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `default_script_provider` | AI for script generation | Auto (first available) |
| `default_voice_provider` | TTS provider | Auto (first available) |
| `default_media_provider` | Stock media source | Auto (first available) |
| `default_video_ai_provider` | AI video generation | None (skip step) |
| `default_assembly_provider` | Video assembly engine | `ffmpeg` |
| `subtitle_style` | Subtitle appearance | `modern` |

### Subtitle Styles

| Style | Description |
|-------|-------------|
| `classic` | White text on black background |
| `modern` | Semi-transparent dark background |
| `bold` | Yellow text with black outline |
| `minimal` | White text with shadow, no background |

### Integration Authentication

| Provider | Auth Type | API Key Format |
|----------|-----------|----------------|
| `openai_gpt` | API Key | `sk-...` |
| `openai_tts` | API Key | `sk-...` |
| `openai_sora` | API Key | `sk-...` |
| `anthropic` | API Key | `sk-ant-...` |
| `elevenlabs` | API Key | Any |
| `pexels` | API Key | Any |
| `ffmpeg` | None | Local binary |

### Cost Estimation

Provider pricing is tracked for cost estimates (per typical 60s video):

| Provider | Unit | Cost |
|----------|------|------|
| `openai_gpt` | per 1K tokens | $0.005 input, $0.015 output |
| `anthropic` | per 1K tokens | $0.003 input, $0.015 output |
| `elevenlabs` | per 1K chars | $0.30 |
| `openai_tts` | per 1K chars | $0.015 |
| `pexels` | per request | Free |
| `ffmpeg` | per video | Free |

- OAuth where available (one-click auth)
- API Key + documentation link as fallback
- Key validation before saving
- Masked display (last 4 chars) with eye icon to reveal

---

## Social Media Integrations

### Supported Platforms

| Platform | Posting | Analytics | Auth |
|----------|---------|-----------|------|
| YouTube | ✅ | ✅ | OAuth 2.0 |
| TikTok | ✅ | ✅ | OAuth 2.0 |
| Instagram | ✅ | ✅ | OAuth 2.0 (Meta Graph API) |
| Facebook | ✅ | ✅ | OAuth 2.0 (Graph API) |

### Features
- Single account per platform per user
- Cross-post to multiple platforms simultaneously
- Platform-specific caption/hashtag overrides
- OAuth connection flow for each platform

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   users     │────▶│  subscriptions   │     │   templates     │
├─────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)     │     │ id (PK)          │     │ id (PK)         │
│ email       │     │ user_id (FK)     │     │ user_id (FK)    │
│ name        │     │ stripe_*         │     │ name            │
│ avatar_url  │     │ plan             │     │ config (JSON)   │
│ role        │     │ status           │     │ is_system       │
│ firebase_uid│     │ current_period_  │     │ is_public       │
│ created_at  │     │   end            │     │ version         │
└─────────────┘     └──────────────────┘     └─────────────────┘
       │                                            │
       │     ┌──────────────────┐                   │
       ├────▶│  integrations    │                   │
       │     ├──────────────────┤                   │
       │     │ id (PK)          │                   │
       │     │ user_id (FK)     │                   │
       │     │ provider         │                   │
       │     │ api_key (enc)    │                   │
       │     │ is_active        │                   │
       │     └──────────────────┘                   │
       │                                            │
       │     ┌──────────────────┐                   │
       ├────▶│ social_accounts  │                   │
       │     ├──────────────────┤                   │
       │     │ id (PK)          │                   │
       │     │ user_id (FK)     │                   │
       │     │ platform         │                   │
       │     │ access_token(enc)│                   │
       │     │ refresh_token    │                   │
       │     │ account_name     │                   │
       │     │ account_id       │                   │
       │     └──────────────────┘                   │
       │                                            │
       │     ┌──────────────────┐                   │
       └────▶│     videos       │◀──────────────────┘
             ├──────────────────┤
             │ id (PK)          │
             │ user_id (FK)     │
             │ template_id (FK) │
             │ title            │
             │ prompt           │
             │ status           │
             │ video_url        │
             │ thumbnail_url    │
             │ duration         │
             │ generation_state │
             │ expires_at       │
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐     ┌─────────────────┐
             │     posts        │────▶│   analytics     │
             ├──────────────────┤     ├─────────────────┤
             │ id (PK)          │     │ id (PK)         │
             │ user_id (FK)     │     │ post_id (FK)    │
             │ video_id (FK)    │     │ platform        │
             │ social_account_id│     │ views           │
             │ platform         │     │ likes           │
             │ status           │     │ shares          │
             │ scheduled_at     │     │ comments        │
             │ published_at     │     │ watch_time      │
             │ post_url         │     │ ... more        │
             │ caption          │     │ fetched_at      │
             │ hashtags         │     └─────────────────┘
             └──────────────────┘

┌──────────────────┐     ┌──────────────────┐
│ ai_suggestions   │     │  notifications   │
├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)          │
│ user_id (FK)     │     │ user_id (FK)     │
│ type             │     │ type             │
│ suggestion (JSON)│     │ title            │
│ is_read          │     │ message          │
│ created_at       │     │ is_read          │
└──────────────────┘     │ data (JSON)      │
                         │ created_at       │
┌──────────────────┐     └──────────────────┘
│      jobs        │
├──────────────────┤
│ id (PK)          │
│ user_id (FK)     │
│ type             │
│ status           │
│ payload (JSON)   │
│ result (JSON)    │
│ error            │
│ created_at       │
│ completed_at     │
└──────────────────┘

┌────────────────────────┐     ┌─────────────────────────┐
│ user_generation_       │     │   api_request_logs      │
│     settings           │     ├─────────────────────────┤
├────────────────────────┤     │ id (PK)                 │
│ id (PK)                │     │ user_id (FK)            │
│ user_id (FK, unique)   │     │ video_id (FK)           │
│ default_script_provider│     │ provider                │
│ default_voice_provider │     │ endpoint                │
│ default_media_provider │     │ method                  │
│ default_video_ai_prov. │     │ request_body (JSON)     │
│ default_assembly_prov. │     │ status_code             │
│ subtitle_style         │     │ response_body (JSON)    │
│ created_at             │     │ duration_ms             │
│ updated_at             │     │ error_message           │
└────────────────────────┘     │ error_details (JSON)    │
                               │ generation_step         │
                               │ created_at              │
                               └─────────────────────────┘
```

### Data Encryption

- **Application Level:** Python `cryptography` library (Fernet) with master key
- **Database Level:** PostgreSQL `pgcrypto` extension
- **Encrypted Fields:** api_key, access_token, refresh_token

---

## API Structure

### Authentication
- Firebase ID Token in `Authorization: Bearer <token>` header
- Backend validates token with Firebase Admin SDK

### Base URL
- Development: `http://localhost:8000/api/v1`
- Production: `https://synthora-api.up.railway.app/api/v1`

### Endpoints Overview

```
/api/v1
├── /auth
│   ├── POST   /login              # Exchange Firebase token
│   ├── POST   /logout             # Invalidate session
│   └── GET    /me                 # Get current user
│
├── /users (Admin)
│   ├── GET    /                   # List all users
│   ├── GET    /{id}               # Get user details
│   ├── PATCH  /{id}/role          # Update user role
│   └── PATCH  /{id}/status        # Enable/disable user
│
├── /templates
│   ├── GET    /                   # List templates
│   ├── GET    /system             # List system templates
│   ├── GET    /personal           # List user's templates
│   ├── POST   /                   # Create template
│   ├── GET    /{id}               # Get template
│   ├── PUT    /{id}               # Update template
│   └── DELETE /{id}               # Delete template
│
├── /integrations
│   ├── GET    /                   # List user's integrations
│   ├── GET    /available          # List all available integrations
│   ├── POST   /                   # Add integration
│   ├── PUT    /{id}               # Update integration
│   ├── DELETE /{id}               # Remove integration
│   └── POST   /{id}/validate      # Validate API key
│
├── /videos
│   ├── GET    /                   # List user's videos
│   ├── GET    /scheduled          # List scheduled videos
│   ├── POST   /generate           # Start video generation
│   ├── GET    /{id}               # Get video details
│   ├── GET    /{id}/status        # Get generation status
│   ├── POST   /{id}/retry         # Retry failed generation
│   ├── POST   /{id}/swap          # Swap integration & retry
│   ├── POST   /{id}/generate-now  # Trigger immediate generation
│   ├── POST   /{id}/cancel        # Cancel in-progress generation
│   ├── PUT    /{id}/reschedule    # Reschedule planned video
│   ├── PUT    /{id}/edit          # Edit planned video details
│   └── DELETE /{id}               # Delete video
│
├── /settings/generation
│   ├── GET    /                   # Get generation settings
│   ├── PUT    /                   # Update generation settings
│   ├── GET    /cost-estimate      # Get cost estimate per video
│   ├── GET    /available-providers# Get available providers
│   ├── GET    /effective-providers# Get effective provider for each category
│   └── GET    /subtitle-config    # Get subtitle style config
│
├── /social-accounts
│   ├── GET    /                   # List connected accounts
│   ├── POST   /connect/{platform} # Start OAuth flow
│   ├── GET    /callback/{platform}# OAuth callback
│   └── DELETE /{id}               # Disconnect account
│
├── /posts
│   ├── GET    /                   # List posts
│   ├── GET    /scheduled          # List scheduled posts
│   ├── GET    /calendar           # Get calendar view data
│   ├── POST   /                   # Create post (immediate or scheduled)
│   ├── GET    /{id}               # Get post details
│   ├── PATCH  /{id}               # Update scheduled post
│   ├── DELETE /{id}               # Cancel/delete post
│   └── POST   /{id}/publish       # Publish now
│
├── /analytics
│   ├── GET    /overview           # Dashboard overview
│   ├── GET    /posts/{post_id}    # Post analytics
│   ├── GET    /videos/{video_id}  # Video analytics (all posts)
│   ├── GET    /platform/{platform}# Platform-specific analytics
│   ├── GET    /time-series        # Time series data
│   ├── GET    /top-performing     # Top videos/posts
│   ├── GET    /heatmap            # Posting time heatmap
│   └── POST   /sync               # Trigger manual sync
│
├── /suggestions (Premium)
│   ├── GET    /                   # Get all suggestions
│   ├── GET    /posting-time       # Optimal posting times
│   ├── GET    /content            # Content recommendations
│   ├── GET    /trends             # Trend alerts
│   └── PATCH  /{id}/read          # Mark as read
│
├── /notifications
│   ├── GET    /                   # List notifications
│   ├── PATCH  /{id}/read          # Mark as read
│   └── PATCH  /read-all           # Mark all as read
│
├── /subscriptions
│   ├── GET    /                   # Get subscription status
│   ├── POST   /checkout           # Create Stripe checkout
│   ├── POST   /portal             # Create Stripe portal session
│   └── POST   /webhook            # Stripe webhook handler
│
├── /admin
│   ├── GET    /stats              # Platform statistics
│   ├── GET    /revenue            # Revenue metrics
│   └── PATCH  /settings           # System settings
│
├── /admin/api-logs
│   ├── GET    /                   # List API logs (filterable)
│   ├── GET    /stats              # Provider statistics
│   ├── GET    /{id}               # Get log detail
│   ├── GET    /video/{id}         # Get logs for a video
│   └── DELETE /cleanup            # Delete old logs
│
└── /health
    └── GET    /                   # Health check
```

---

## Frontend Architecture

### Pages

| Route | Page | Access |
|-------|------|--------|
| `/` | Landing (simple) | Public |
| `/login` | Login (Google Sign-In) | Public |
| `/onboarding` | Onboarding Wizard | New users |
| `/dashboard` | Dashboard | Authenticated |
| `/templates` | Templates | Authenticated |
| `/generate` | Video Generation | Authenticated |
| `/videos` | Video Library | Authenticated |
| `/posts` | Posting & Scheduling | Authenticated |
| `/analytics` | Analytics | Authenticated |
| `/settings` | Settings | Authenticated |
| `/settings/integrations` | Integrations | Authenticated |
| `/settings/social` | Social Accounts | Authenticated |
| `/settings/subscription` | Subscription | Authenticated |
| `/admin` | Admin Dashboard | Admin only |
| `/admin/users` | User Management | Admin only |
| `/admin/templates` | System Templates | Admin only |

### State Management
- React Context for auth state
- React Query (TanStack Query) for server state
- Local state for UI

### Design System
- **Theme:** Dark mode primary, user-selectable
- **Layout:** Sidebar navigation (CapCut-inspired)
- **Components:** shadcn/ui
- **Styling:** Tailwind CSS
- **Icons:** Lucide React
- **Charts:** Recharts

### Responsiveness
- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Collapsible sidebar on mobile

### i18n
- Architecture ready for multiple languages
- English only for initial launch
- Using `react-i18next`

---

## Security Considerations

### Authentication & Authorization
- Firebase Authentication for identity
- JWT validation on every API request
- Role-based access control (RBAC)

### Rate Limiting
- 100 requests/minute per user
- Implemented at API gateway level

### Video Generation Limits
- Max 1 concurrent generation per user
- Daily limits enforced (1/day for Free)

### Data Protection
- API keys encrypted (application + database level)
- Masked display in UI (last 4 chars)
- Eye icon to reveal (temporary)
- Key validation before saving

### CORS
- Strict policy (frontend domain only)
- Configured for Railway deployment

### Input Validation
- Pydantic schemas for all inputs
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (React default escaping)

---

## Deployment Configuration

### Railway Services

| Service | Type | Source |
|---------|------|--------|
| `synthora-api` | Web Service | `/backend` |
| `synthora-web` | Static Site | `/frontend` |
| `synthora-worker` | Worker | `/backend` (different start command) |
| `postgres` | Database | Railway Plugin |

### External Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| Upstash Redis | Job queue | `REDIS_URL` env var |
| Google Cloud Storage | File storage | Service account JSON |
| Firebase | Authentication | Firebase config |
| Stripe | Payments | API keys + webhook |

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
- Lint (backend: ruff, frontend: eslint)
- Type check (backend: mypy, frontend: tsc)
- Unit tests (backend: pytest, frontend: vitest)
- Build check
```

### Railway Auto-Deploy
- Triggered on push to `main` branch
- Automatic rollback on failure

---

## Environment Variables

See `.env.example` for complete list with placeholders.

### Categories

1. **App Configuration**
   - `APP_NAME`, `APP_ENV`, `DEBUG`, `SECRET_KEY`

2. **Database**
   - `DATABASE_URL` (provided by Railway)

3. **Redis**
   - `REDIS_URL` (Upstash)

4. **Firebase**
   - `FIREBASE_*` credentials

5. **Stripe**
   - `STRIPE_*` keys and webhook secret

6. **Google Cloud Storage**
   - `GCS_*` credentials

7. **AI Integrations (System-level, optional)**
   - Placeholders for each service

8. **Social Media OAuth**
   - Client IDs and secrets for each platform

9. **CORS**
   - `CORS_ORIGINS`

---

## Next Steps

1. Review `todo-synthora.md` for implementation checklist
2. Set up GitHub repository
3. Connect to Railway
4. Begin implementation phase

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [shadcn/ui](https://ui.shadcn.com/)
- [Railway Documentation](https://docs.railway.app/)
- [Firebase Auth](https://firebase.google.com/docs/auth)
- [Stripe Documentation](https://stripe.com/docs)

