# Modular Video Generation System - Implementation Checklist

**Created:** January 28, 2026  
**Status:** Planning  
**Feature Branch:** `cursor/modular-video-generation-process-f829`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Database Schema Changes](#2-database-schema-changes)
3. [Backend - Integration System](#3-backend---integration-system)
4. [Backend - User Settings & Defaults](#4-backend---user-settings--defaults)
5. [Backend - Video Generation Pipeline](#5-backend---video-generation-pipeline)
6. [Backend - Subtitle System](#6-backend---subtitle-system)
7. [Backend - Logging System](#7-backend---logging-system)
8. [Backend - API Endpoints](#8-backend---api-endpoints)
9. [Backend - Scheduler & Workers](#9-backend---scheduler--workers)
10. [Frontend - User Settings Page](#10-frontend---user-settings-page)
11. [Frontend - Videos Page](#11-frontend---videos-page)
12. [Cost Estimation System](#12-cost-estimation-system)
13. [Error Handling & Fallbacks](#13-error-handling--fallbacks)
14. [Testing](#14-testing)
15. [Documentation](#15-documentation)

---

## 1. Overview

### 1.1 Goals
- [ ] Create modular integration system where each provider works independently
- [ ] Allow users to select default providers for each video generation step
- [ ] Add subtitle/caption system synchronized with voiceover
- [ ] Implement manual trigger for scheduled video generation
- [ ] Add comprehensive logging with full payloads
- [ ] Show cost estimation based on selected providers
- [ ] Robust error handling with 30-minute timeout and auto-cancel

### 1.2 Key Decisions
| Area | Decision |
|------|----------|
| Integration Design | Separate providers (OPENAI_GPT, OPENAI_SORA, OPENAI_TTS, etc.) |
| Model Selection | Best/recommended model per provider (automatic) |
| User Defaults | Global settings for each category + subtitle style preset |
| Subtitle System | Synced with voiceover, 4 preset styles, user configurable |
| Videos Page | Two tabs: "My Videos" / "Scheduled" with full action set |
| Error Handling | Immediate fail + notify, 30-min timeout + auto-cancel |
| Logging | Full payload logs (app + DB), API keys masked |
| Cost Estimation | Per-video estimate, hardcoded pricing, summary section |
| Concurrency | 1 active generation per user |
| Step Failure | Entire video fails if any step fails |

---

## 2. Database Schema Changes

### 2.1 New Migration: Update Integration Providers
**File:** `backend/alembic/versions/008_modular_integrations.py`

- [ ] 2.1.1 Update `IntegrationProvider` enum values:
  ```python
  # Script/Text AI
  OPENAI_GPT = "openai_gpt"
  ANTHROPIC = "anthropic"
  
  # Voice AI
  OPENAI_TTS = "openai_tts"
  ELEVENLABS = "elevenlabs"
  PLAYHT = "playht"
  
  # Stock Media
  PEXELS = "pexels"
  UNSPLASH = "unsplash"
  PIXABAY = "pixabay"
  
  # Video Generation AI
  OPENAI_SORA = "openai_sora"
  RUNWAY = "runway"
  VEO = "veo"
  LUMA = "luma"
  KLING = "kling"
  MINIMAX = "minimax"
  PIXVERSE = "pixverse"
  HAILUO = "hailuo"
  
  # Video Assembly
  FFMPEG = "ffmpeg"
  CREATOMATE = "creatomate"
  SHOTSTACK = "shotstack"
  ```

- [ ] 2.1.2 Migrate existing `openai` integrations to `openai_gpt`

### 2.2 New Migration: User Video Generation Settings
**File:** `backend/alembic/versions/009_user_generation_settings.py`

- [ ] 2.2.1 Add `user_generation_settings` table:
  ```sql
  CREATE TABLE user_generation_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Default providers per category
    default_script_provider VARCHAR(50),
    default_voice_provider VARCHAR(50),
    default_media_provider VARCHAR(50),
    default_video_ai_provider VARCHAR(50),
    default_assembly_provider VARCHAR(50),
    
    -- Subtitle settings
    subtitle_style VARCHAR(20) DEFAULT 'modern',  -- classic, modern, bold, minimal
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
  );
  ```

### 2.3 New Migration: API Request Logs Table
**File:** `backend/alembic/versions/010_api_request_logs.py`

- [ ] 2.3.1 Add `api_request_logs` table:
  ```sql
  CREATE TABLE api_request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    video_id UUID REFERENCES videos(id) ON DELETE SET NULL,
    
    -- Request info
    provider VARCHAR(50) NOT NULL,
    endpoint VARCHAR(500) NOT NULL,
    method VARCHAR(10) NOT NULL,
    
    -- Response info
    status_code INTEGER,
    response_body JSONB,
    duration_ms INTEGER,
    
    -- Error info
    error_message TEXT,
    error_details JSONB,
    
    -- Metadata
    generation_step VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for searching
    INDEX idx_api_logs_user_id (user_id),
    INDEX idx_api_logs_video_id (video_id),
    INDEX idx_api_logs_provider (provider),
    INDEX idx_api_logs_created_at (created_at)
  );
  ```

### 2.4 Update Videos Table
**File:** `backend/alembic/versions/011_update_videos_table.py`

- [ ] 2.4.1 Add new columns to `videos` table:
  ```sql
  ALTER TABLE videos ADD COLUMN IF NOT EXISTS 
    subtitle_file_url TEXT,
    generation_started_at TIMESTAMPTZ,
    last_step_updated_at TIMESTAMPTZ,
    selected_providers JSONB;  -- stores provider selections for this video
  ```

---

## 3. Backend - Integration System

### 3.1 Update Integration Model
**File:** `backend/app/models/integration.py`

- [ ] 3.1.1 Update `IntegrationProvider` enum with new providers:
  - OPENAI_GPT, OPENAI_TTS, OPENAI_SORA
  - ANTHROPIC
  - ELEVENLABS, PLAYHT
  - PEXELS, UNSPLASH, PIXABAY
  - RUNWAY, VEO, LUMA, KLING, MINIMAX, PIXVERSE, HAILUO
  - FFMPEG, CREATOMATE, SHOTSTACK

- [ ] 3.1.2 Update `PROVIDER_CATEGORIES` mapping:
  ```python
  PROVIDER_CATEGORIES = {
      IntegrationProvider.OPENAI_GPT: IntegrationCategory.SCRIPT,
      IntegrationProvider.ANTHROPIC: IntegrationCategory.SCRIPT,
      IntegrationProvider.OPENAI_TTS: IntegrationCategory.VOICE,
      IntegrationProvider.ELEVENLABS: IntegrationCategory.VOICE,
      IntegrationProvider.PLAYHT: IntegrationCategory.VOICE,
      IntegrationProvider.PEXELS: IntegrationCategory.MEDIA,
      IntegrationProvider.UNSPLASH: IntegrationCategory.MEDIA,
      IntegrationProvider.PIXABAY: IntegrationCategory.MEDIA,
      IntegrationProvider.OPENAI_SORA: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.RUNWAY: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.VEO: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.LUMA: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.KLING: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.MINIMAX: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.PIXVERSE: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.HAILUO: IntegrationCategory.VIDEO_AI,
      IntegrationProvider.FFMPEG: IntegrationCategory.ASSEMBLY,
      IntegrationProvider.CREATOMATE: IntegrationCategory.ASSEMBLY,
      IntegrationProvider.SHOTSTACK: IntegrationCategory.ASSEMBLY,
  }
  ```

- [ ] 3.1.3 Add `PROVIDER_RECOMMENDED_MODELS` mapping:
  ```python
  PROVIDER_RECOMMENDED_MODELS = {
      IntegrationProvider.OPENAI_GPT: "gpt-4o",
      IntegrationProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
      IntegrationProvider.OPENAI_TTS: "tts-1-hd",
      IntegrationProvider.ELEVENLABS: "eleven_multilingual_v2",
      IntegrationProvider.OPENAI_SORA: "sora-1.0",
      # ... etc
  }
  ```

- [ ] 3.1.4 Add `PROVIDER_PRICING` constant for cost estimation:
  ```python
  PROVIDER_PRICING = {
      IntegrationProvider.OPENAI_GPT: {
          "unit": "1K tokens",
          "input_cost": 0.0025,
          "output_cost": 0.01,
          "estimated_per_video": 0.05,  # ~5 scenes, ~2K tokens
      },
      IntegrationProvider.ELEVENLABS: {
          "unit": "1K characters",
          "cost": 0.30,
          "estimated_per_video": 0.15,  # ~500 chars for 30s
      },
      # ... etc for all providers
  }
  ```

### 3.2 Create Provider Base Classes
**File:** `backend/app/integrations/providers/base.py`

- [ ] 3.2.1 Create `BaseProvider` abstract class:
  ```python
  class BaseProvider(ABC):
      provider_name: str
      category: IntegrationCategory
      recommended_model: str
      
      @abstractmethod
      async def execute(self, input_data: Dict, config: Dict) -> ProviderResult
      
      @abstractmethod
      async def validate_api_key(self, api_key: str) -> bool
  ```

- [ ] 3.2.2 Create `ProviderResult` dataclass:
  ```python
  @dataclass
  class ProviderResult:
      success: bool
      data: Dict[str, Any]
      error: Optional[str] = None
      duration_ms: int = 0
      raw_response: Optional[Dict] = None
  ```

### 3.3 Implement Script Providers
**File:** `backend/app/integrations/providers/script/`

- [ ] 3.3.1 Create `OpenAIGPTProvider` class
- [ ] 3.3.2 Create `AnthropicProvider` class
- [ ] 3.3.3 Implement script generation with scene breakdown
- [ ] 3.3.4 Return timing estimates per scene for subtitle sync

### 3.4 Implement Voice Providers
**File:** `backend/app/integrations/providers/voice/`

- [ ] 3.4.1 Create `OpenAITTSProvider` class
- [ ] 3.4.2 Create `ElevenLabsProvider` class
- [ ] 3.4.3 Create `PlayHTProvider` class
- [ ] 3.4.4 Return word-level or sentence-level timestamps for subtitles

### 3.5 Implement Media Providers
**File:** `backend/app/integrations/providers/media/`

- [ ] 3.5.1 Create `PexelsProvider` class
- [ ] 3.5.2 Create `UnsplashProvider` class
- [ ] 3.5.3 Create `PixabayProvider` class

### 3.6 Implement Video AI Providers
**File:** `backend/app/integrations/providers/video_ai/`

- [ ] 3.6.1 Create `OpenAISoraProvider` class
- [ ] 3.6.2 Create `RunwayProvider` class
- [ ] 3.6.3 Create `VeoProvider` class
- [ ] 3.6.4 Create `LumaProvider` class
- [ ] 3.6.5 Create `KlingProvider` class
- [ ] 3.6.6 Create `MinimaxProvider` class
- [ ] 3.6.7 Create `PixverseProvider` class
- [ ] 3.6.8 Create `HailuoProvider` class

### 3.7 Implement Assembly Providers
**File:** `backend/app/integrations/providers/assembly/`

- [ ] 3.7.1 Create `FFmpegProvider` class with subtitle burning support
- [ ] 3.7.2 Create `CreatomateProvider` class
- [ ] 3.7.3 Create `ShotstackProvider` class

### 3.8 Provider Factory
**File:** `backend/app/integrations/providers/factory.py`

- [ ] 3.8.1 Create `ProviderFactory` class:
  ```python
  class ProviderFactory:
      @staticmethod
      def get_provider(provider_name: str, api_key: str) -> BaseProvider:
          """Returns the appropriate provider instance"""
          
      @staticmethod
      def get_providers_for_category(category: IntegrationCategory) -> List[str]:
          """Returns list of provider names for a category"""
  ```

---

## 4. Backend - User Settings & Defaults

### 4.1 Create User Generation Settings Model
**File:** `backend/app/models/user_generation_settings.py`

- [ ] 4.1.1 Create `UserGenerationSettings` model:
  ```python
  class UserGenerationSettings(Base, UUIDMixin, TimestampMixin):
      __tablename__ = "user_generation_settings"
      
      user_id = Column(UUID, ForeignKey("users.id"), unique=True)
      
      default_script_provider = Column(String(50), nullable=True)
      default_voice_provider = Column(String(50), nullable=True)
      default_media_provider = Column(String(50), nullable=True)
      default_video_ai_provider = Column(String(50), nullable=True)
      default_assembly_provider = Column(String(50), nullable=True)
      
      subtitle_style = Column(String(20), default="modern")
      
      user = relationship("User", back_populates="generation_settings")
  ```

- [ ] 4.1.2 Add relationship to User model

### 4.2 Create User Generation Settings Schema
**File:** `backend/app/schemas/user_generation_settings.py`

- [ ] 4.2.1 Create `UserGenerationSettingsResponse` schema
- [ ] 4.2.2 Create `UserGenerationSettingsUpdate` schema
- [ ] 4.2.3 Create `CostEstimateResponse` schema:
  ```python
  class CostEstimateResponse(BaseModel):
      script_cost: float
      voice_cost: float
      media_cost: float
      video_ai_cost: float
      assembly_cost: float
      total_estimated_cost: float
      currency: str = "USD"
  ```

### 4.3 Create User Generation Settings Service
**File:** `backend/app/services/user_generation_settings.py`

- [ ] 4.3.1 Create `UserGenerationSettingsService` class:
  - `get_settings(user_id)` - Get or create default settings
  - `update_settings(user_id, updates)` - Update settings
  - `get_effective_providers(user_id)` - Get providers to use (user defaults or first available)
  - `calculate_cost_estimate(user_id)` - Calculate cost based on selected providers

---

## 5. Backend - Video Generation Pipeline

### 5.1 Refactor Pipeline Architecture
**File:** `backend/app/services/generation/pipeline.py`

- [ ] 5.1.1 Create `VideoGenerationStateMachine`:
  ```python
  class VideoGenerationState(str, Enum):
      PLANNED = "planned"
      QUEUED = "queued"
      PROCESSING = "processing"
      SCRIPT = "script"
      VOICE = "voice"
      MEDIA = "media"
      VIDEO_AI = "video_ai"
      ASSEMBLY = "assembly"
      COMPLETED = "completed"
      FAILED = "failed"
      CANCELLED = "cancelled"
  ```

- [ ] 5.1.2 Refactor `GenerationPipeline` class:
  - Use provider factory to get providers
  - Load user's default provider settings
  - Track `generation_started_at` and `last_step_updated_at`
  - Implement proper state transitions
  - Pass subtitle data through pipeline

- [ ] 5.1.3 Add concurrency check:
  ```python
  def check_can_generate(user_id: UUID) -> bool:
      """Check if user has no active generation in progress"""
      active = db.query(Video).filter(
          Video.user_id == user_id,
          Video.status == "processing"
      ).count()
      return active == 0
  ```

- [ ] 5.1.4 Implement idempotency for each step

### 5.2 Update Step Executors
**File:** `backend/app/services/generation/steps/`

- [ ] 5.2.1 Refactor `ScriptStep` to use provider factory
- [ ] 5.2.2 Refactor `VoiceStep` to return timing data for subtitles
- [ ] 5.2.3 Refactor `MediaStep` to use provider factory
- [ ] 5.2.4 Refactor `VideoAIStep` to use provider factory
- [ ] 5.2.5 Refactor `AssemblyStep` to include subtitle burning

### 5.3 Pipeline State Management
**File:** `backend/app/services/generation/state_manager.py`

- [ ] 5.3.1 Create `PipelineStateManager` class:
  - Track step status, timing, and results
  - Save state to database after each step
  - Support resume from last successful step
  - Handle cleanup on failure/cancellation

---

## 6. Backend - Subtitle System

### 6.1 Create Subtitle Service
**File:** `backend/app/services/subtitle_service.py`

- [ ] 6.1.1 Create `SubtitleService` class:
  ```python
  class SubtitleService:
      STYLES = {
          "classic": {
              "font": "Arial",
              "size": 24,
              "color": "#FFFFFF",
              "outline_color": "#000000",
              "outline_width": 2,
              "position": "bottom",
              "background": None,
          },
          "modern": {
              "font": "Helvetica Neue",
              "size": 28,
              "color": "#FFFFFF",
              "outline_color": "#000000",
              "outline_width": 1,
              "position": "bottom",
              "background": "rgba(0,0,0,0.5)",
          },
          "bold": {
              "font": "Impact",
              "size": 32,
              "color": "#FFFF00",
              "outline_color": "#000000",
              "outline_width": 3,
              "position": "center",
              "background": None,
          },
          "minimal": {
              "font": "Roboto",
              "size": 22,
              "color": "#FFFFFF",
              "outline_color": None,
              "outline_width": 0,
              "position": "bottom",
              "background": "rgba(0,0,0,0.7)",
          },
      }
      
      def generate_srt(self, timing_data: List[TimingSegment]) -> str:
          """Generate SRT subtitle file content"""
          
      def generate_ass(self, timing_data: List[TimingSegment], style: str) -> str:
          """Generate ASS subtitle file with styling"""
  ```

- [ ] 6.1.2 Create `TimingSegment` dataclass:
  ```python
  @dataclass
  class TimingSegment:
      text: str
      start_ms: int
      end_ms: int
  ```

### 6.2 Update FFmpeg Assembly
**File:** `backend/app/integrations/providers/assembly/ffmpeg_provider.py`

- [ ] 6.2.1 Add subtitle burning to FFmpeg command:
  ```python
  def build_ffmpeg_command(self, ...):
      # Use ASS subtitles filter for styled subtitles
      # ffmpeg -i video.mp4 -vf "ass=subtitles.ass" output.mp4
  ```

- [ ] 6.2.2 Handle subtitle file upload to temp storage
- [ ] 6.2.3 Clean up subtitle file after assembly

---

## 7. Backend - Logging System

### 7.1 Create API Log Model
**File:** `backend/app/models/api_request_log.py`

- [ ] 7.1.1 Create `APIRequestLog` model:
  ```python
  class APIRequestLog(Base, UUIDMixin):
      __tablename__ = "api_request_logs"
      
      user_id = Column(UUID, ForeignKey("users.id"), nullable=True)
      video_id = Column(UUID, ForeignKey("videos.id"), nullable=True)
      
      provider = Column(String(50), nullable=False)
      endpoint = Column(String(500), nullable=False)
      method = Column(String(10), nullable=False)
      
      status_code = Column(Integer, nullable=True)
      response_body = Column(JSONB, nullable=True)
      duration_ms = Column(Integer, nullable=True)
      
      error_message = Column(Text, nullable=True)
      error_details = Column(JSONB, nullable=True)
      
      generation_step = Column(String(50), nullable=True)
      created_at = Column(DateTime, default=datetime.utcnow)
  ```

### 7.2 Create Logging Service
**File:** `backend/app/services/api_logging_service.py`

- [ ] 7.2.1 Create `APILoggingService` class:
  ```python
  class APILoggingService:
      def log_request(
          self,
          provider: str,
          endpoint: str,
          method: str,
          status_code: int,
          response_body: Dict,
          duration_ms: int,
          user_id: Optional[UUID] = None,
          video_id: Optional[UUID] = None,
          generation_step: Optional[str] = None,
          error_message: Optional[str] = None,
          error_details: Optional[Dict] = None,
      ) -> APIRequestLog:
          """Log API request to database and application logs"""
          
      def mask_sensitive_data(self, data: Dict) -> Dict:
          """Mask API keys (show last 4 chars only)"""
  ```

- [ ] 7.2.2 Integrate logging into all provider implementations

### 7.3 Create Logging Decorator
**File:** `backend/app/utils/logging_decorator.py`

- [ ] 7.3.1 Create `@log_api_request` decorator for provider methods:
  ```python
  def log_api_request(provider_name: str, step: str):
      def decorator(func):
          @wraps(func)
          async def wrapper(*args, **kwargs):
              start_time = time.time()
              try:
                  result = await func(*args, **kwargs)
                  # Log success
                  return result
              except Exception as e:
                  # Log failure
                  raise
          return wrapper
      return decorator
  ```

---

## 8. Backend - API Endpoints

### 8.1 User Generation Settings Endpoints
**File:** `backend/app/api/v1/endpoints/user_settings.py`

- [ ] 8.1.1 `GET /api/v1/settings/generation` - Get user's generation settings
- [ ] 8.1.2 `PUT /api/v1/settings/generation` - Update generation settings
- [ ] 8.1.3 `GET /api/v1/settings/generation/cost-estimate` - Get cost estimate
- [ ] 8.1.4 `GET /api/v1/settings/generation/available-providers` - Get available providers per category

### 8.2 Update Videos Endpoints
**File:** `backend/app/api/v1/endpoints/videos.py`

- [ ] 8.2.1 `POST /api/v1/videos/{id}/generate-now` - Trigger immediate generation for scheduled video
- [ ] 8.2.2 `POST /api/v1/videos/{id}/cancel` - Cancel processing video
- [ ] 8.2.3 `POST /api/v1/videos/{id}/retry` - Retry failed video
- [ ] 8.2.4 `PUT /api/v1/videos/{id}/reschedule` - Reschedule planned video
- [ ] 8.2.5 `PUT /api/v1/videos/{id}/edit` - Edit planned video details
- [ ] 8.2.6 `GET /api/v1/videos/scheduled` - List scheduled/planned videos
- [ ] 8.2.7 Update `DELETE /api/v1/videos/{id}` - Handle deletion of scheduled videos gracefully

### 8.3 Update Integration Endpoints
**File:** `backend/app/api/v1/endpoints/integrations.py`

- [ ] 8.3.1 Update `GET /api/v1/integrations/available` to return new provider list with pricing info

### 8.4 Admin Logs Endpoints
**File:** `backend/app/api/v1/endpoints/admin.py`

- [ ] 8.4.1 `GET /api/v1/admin/logs` - Search API request logs (admin only)
- [ ] 8.4.2 `GET /api/v1/admin/logs/{id}` - Get log details (admin only)

---

## 9. Backend - Scheduler & Workers

### 9.1 Update Video Scheduler
**File:** `backend/app/workers/video_scheduler.py`

- [ ] 9.1.1 Add existence check before processing scheduled video:
  ```python
  def check_and_trigger_scheduled_videos():
      for video in videos_to_generate:
          # Refresh from DB to check if still exists
          video = db.query(Video).get(video.id)
          if not video:
              logger.info(f"Video {video_id} deleted, skipping")
              continue
  ```

- [ ] 9.1.2 Update to use new provider selection from user settings

### 9.2 Create Stuck Job Monitor
**File:** `backend/app/workers/stuck_job_monitor.py`

- [ ] 9.2.1 Create `check_stuck_jobs` function:
  ```python
  def check_stuck_jobs():
      """
      Runs every 5 minutes.
      Finds videos where:
      - status = 'processing'
      - last_step_updated_at < 30 minutes ago
      Auto-cancels them and notifies user.
      """
      thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
      
      stuck_videos = db.query(Video).filter(
          Video.status == "processing",
          Video.last_step_updated_at < thirty_minutes_ago,
      ).all()
      
      for video in stuck_videos:
          video.status = "cancelled"
          video.error_message = "Generation timed out after 30 minutes"
          # Send notification
          # Clean up partial files
  ```

- [ ] 9.2.2 Schedule job to run every 5 minutes

### 9.3 Update Video Worker
**File:** `backend/app/workers/video_worker.py`

- [ ] 9.3.1 Add concurrency check before starting generation
- [ ] 9.3.2 Update `last_step_updated_at` after each step
- [ ] 9.3.3 Handle cancellation gracefully (check cancelled flag between steps)

---

## 10. Frontend - User Settings Page

### 10.1 Update Settings Page
**File:** `frontend/src/pages/dashboard/SettingsPage.tsx`

- [ ] 10.1.1 Add "Video Generation" section/tab

### 10.2 Create Video Generation Settings Component
**File:** `frontend/src/components/settings/VideoGenerationSettings.tsx`

- [ ] 10.2.1 Create component with sections:
  - **Default Providers** - Dropdowns for each category
  - **Subtitle Style** - Radio/select for 4 presets with preview
  - **Cost Summary** - Display estimated cost per video

- [ ] 10.2.2 Provider dropdown shows only enabled integrations for that category
- [ ] 10.2.3 Show "Not configured" state if no integration for category
- [ ] 10.2.4 Save button with loading state

### 10.3 Create Cost Summary Component
**File:** `frontend/src/components/settings/CostSummary.tsx`

- [ ] 10.3.1 Display breakdown:
  ```
  Estimated Cost Per Video
  ─────────────────────────
  Script (OpenAI GPT):     $0.05
  Voice (ElevenLabs):      $0.15
  Media (Pexels):          $0.00
  Video AI (Sora):         $0.40
  Assembly (FFmpeg):       $0.00
  ─────────────────────────
  Total:                   $0.60
  ```

### 10.4 Create Subtitle Style Preview
**File:** `frontend/src/components/settings/SubtitleStylePreview.tsx`

- [ ] 10.4.1 Show visual preview of each subtitle style
- [ ] 10.4.2 Radio button selection for Classic, Modern, Bold, Minimal

### 10.5 Frontend Hooks & Services
**File:** `frontend/src/hooks/useGenerationSettings.ts`

- [ ] 10.5.1 Create `useGenerationSettings` hook
- [ ] 10.5.2 Create `useUpdateGenerationSettings` mutation
- [ ] 10.5.3 Create `useCostEstimate` hook

**File:** `frontend/src/services/generationSettings.ts`

- [ ] 10.5.4 Create API service functions

---

## 11. Frontend - Videos Page

### 11.1 Refactor Videos Page with Tabs
**File:** `frontend/src/pages/dashboard/VideosPage.tsx`

- [ ] 11.1.1 Add tab navigation: "My Videos" | "Scheduled"
- [ ] 11.1.2 "My Videos" tab shows completed/failed/processing videos
- [ ] 11.1.3 "Scheduled" tab shows planned videos

### 11.2 Create Scheduled Video Card Component
**File:** `frontend/src/components/videos/ScheduledVideoCard.tsx`

- [ ] 11.2.1 Display:
  - Video title/prompt
  - Scheduled time
  - Target platforms
  - Status badge (Planned, Generating, Ready)

- [ ] 11.2.2 Action buttons:
  - "Generate Now" button
  - "Edit" button
  - "Reschedule" button
  - "Delete" button

### 11.3 Create Video Action Dialogs
**File:** `frontend/src/components/videos/VideoActionDialogs.tsx`

- [ ] 11.3.1 `GenerateNowDialog` - Confirm immediate generation
- [ ] 11.3.2 `RescheduleDialog` - Date/time picker for new schedule
- [ ] 11.3.3 `EditVideoDialog` - Edit prompt, template, platforms
- [ ] 11.3.4 `CancelVideoDialog` - Confirm cancellation of processing video
- [ ] 11.3.5 `RetryVideoDialog` - Confirm retry, show last error

### 11.4 Update Video Card for Processing Videos
**File:** `frontend/src/components/videos/VideoCard.tsx`

- [ ] 11.4.1 Add "Cancel" action for processing videos
- [ ] 11.4.2 Add "Retry" action for failed videos
- [ ] 11.4.3 Show current step and progress for processing videos
- [ ] 11.4.4 Show error message for failed videos

### 11.5 Frontend Hooks for Video Actions
**File:** `frontend/src/hooks/useVideos.ts`

- [ ] 11.5.1 Add `useGenerateNow` mutation
- [ ] 11.5.2 Add `useCancelVideo` mutation
- [ ] 11.5.3 Add `useRetryVideo` mutation
- [ ] 11.5.4 Add `useRescheduleVideo` mutation
- [ ] 11.5.5 Add `useEditVideo` mutation
- [ ] 11.5.6 Add `useScheduledVideos` query

---

## 12. Cost Estimation System

### 12.1 Provider Pricing Data
**File:** `backend/app/data/provider_pricing.py`

- [ ] 12.1.1 Create pricing constants:
  ```python
  PROVIDER_PRICING = {
      # Script providers
      "openai_gpt": {
          "name": "OpenAI GPT-4o",
          "unit": "per 1K tokens",
          "input_cost": 0.0025,
          "output_cost": 0.01,
          "estimated_per_video": 0.05,
      },
      "anthropic": {
          "name": "Anthropic Claude",
          "unit": "per 1K tokens", 
          "input_cost": 0.003,
          "output_cost": 0.015,
          "estimated_per_video": 0.06,
      },
      
      # Voice providers
      "openai_tts": {
          "name": "OpenAI TTS",
          "unit": "per 1K characters",
          "cost": 0.015,
          "estimated_per_video": 0.08,
      },
      "elevenlabs": {
          "name": "ElevenLabs",
          "unit": "per 1K characters",
          "cost": 0.30,
          "estimated_per_video": 0.15,
      },
      "playht": {
          "name": "PlayHT",
          "unit": "per 1K characters",
          "cost": 0.10,
          "estimated_per_video": 0.05,
      },
      
      # Media providers (typically free)
      "pexels": {"name": "Pexels", "estimated_per_video": 0.00},
      "unsplash": {"name": "Unsplash", "estimated_per_video": 0.00},
      "pixabay": {"name": "Pixabay", "estimated_per_video": 0.00},
      
      # Video AI providers
      "openai_sora": {
          "name": "OpenAI Sora",
          "unit": "per second",
          "cost": 0.02,
          "estimated_per_video": 0.40,
      },
      "runway": {
          "name": "Runway Gen-4",
          "unit": "per second",
          "cost": 0.05,
          "estimated_per_video": 1.00,
      },
      "veo": {
          "name": "Google Veo 3",
          "unit": "per second",
          "cost": 0.03,
          "estimated_per_video": 0.60,
      },
      "luma": {
          "name": "Luma Dream Machine",
          "unit": "per generation",
          "cost": 0.30,
          "estimated_per_video": 0.90,
      },
      "kling": {
          "name": "Kling AI",
          "unit": "per second",
          "cost": 0.02,
          "estimated_per_video": 0.40,
      },
      "minimax": {
          "name": "Minimax",
          "unit": "per second",
          "cost": 0.015,
          "estimated_per_video": 0.30,
      },
      "pixverse": {
          "name": "PixVerse",
          "unit": "per generation",
          "cost": 0.20,
          "estimated_per_video": 0.60,
      },
      "hailuo": {
          "name": "Hailuo AI",
          "unit": "per second",
          "cost": 0.01,
          "estimated_per_video": 0.20,
      },
      
      # Assembly providers
      "ffmpeg": {"name": "FFmpeg (Local)", "estimated_per_video": 0.00},
      "creatomate": {
          "name": "Creatomate",
          "unit": "per render",
          "cost": 0.10,
          "estimated_per_video": 0.10,
      },
      "shotstack": {
          "name": "Shotstack",
          "unit": "per render",
          "cost": 0.08,
          "estimated_per_video": 0.08,
      },
  }
  ```

### 12.2 Cost Calculation Service
**File:** `backend/app/services/cost_estimation.py`

- [ ] 12.2.1 Create `CostEstimationService`:
  ```python
  class CostEstimationService:
      def get_estimated_cost(self, provider: str) -> float:
          """Get estimated cost per video for a provider"""
          
      def calculate_total_cost(
          self,
          script_provider: str,
          voice_provider: str,
          media_provider: str,
          video_ai_provider: Optional[str],
          assembly_provider: str,
      ) -> CostBreakdown:
          """Calculate total estimated cost based on selected providers"""
  ```

---

## 13. Error Handling & Fallbacks

### 13.1 Video Deletion Handling
**File:** `backend/app/services/video.py`

- [ ] 13.1.1 Update `delete_video` to handle all states gracefully
- [ ] 13.1.2 Cancel any pending jobs when video is deleted
- [ ] 13.1.3 Clean up any partial files in storage

### 13.2 Scheduler Resilience
**File:** `backend/app/workers/video_scheduler.py`

- [ ] 13.2.1 Always refresh video from DB before processing
- [ ] 13.2.2 Wrap each video processing in try/except
- [ ] 13.2.3 Continue processing other videos if one fails

### 13.3 Pipeline Error Handling
**File:** `backend/app/services/generation/pipeline.py`

- [ ] 13.3.1 On any step failure:
  - Mark video as failed immediately
  - Save full error details to video record
  - Send notification to user
  - Clean up any partial files

- [ ] 13.3.2 Before each step:
  - Check if video still exists
  - Check if video is cancelled
  - Update `last_step_updated_at`

### 13.4 Notification Service Updates
**File:** `backend/app/services/notification.py`

- [ ] 13.4.1 Add notification types:
  - `video_generation_failed`
  - `video_generation_timeout`
  - `video_generation_cancelled`
  - `video_ready_to_post`

---

## 14. Testing

### 14.1 Unit Tests - Backend

- [ ] 14.1.1 Test `IntegrationProvider` enum and categories
- [ ] 14.1.2 Test `UserGenerationSettingsService`
- [ ] 14.1.3 Test `CostEstimationService`
- [ ] 14.1.4 Test `SubtitleService` SRT/ASS generation
- [ ] 14.1.5 Test `APILoggingService` with masking
- [ ] 14.1.6 Test pipeline state transitions
- [ ] 14.1.7 Test concurrency check
- [ ] 14.1.8 Test stuck job detection

### 14.2 Integration Tests - Backend

- [ ] 14.2.1 Test video generation endpoints
- [ ] 14.2.2 Test scheduled video management endpoints
- [ ] 14.2.3 Test user settings endpoints
- [ ] 14.2.4 Test admin logs endpoints

### 14.3 Unit Tests - Frontend

- [ ] 14.3.1 Test `VideoGenerationSettings` component
- [ ] 14.3.2 Test `ScheduledVideoCard` component
- [ ] 14.3.3 Test video action dialogs
- [ ] 14.3.4 Test tab switching on Videos page

---

## 15. Documentation

### 15.1 Update AI Overview
**File:** `ai-planning/ai-overview.md`

- [ ] 15.1.1 Update integration providers section
- [ ] 15.1.2 Add video generation pipeline documentation
- [ ] 15.1.3 Document user settings structure
- [ ] 15.1.4 Document cost estimation approach

### 15.2 API Documentation

- [ ] 15.2.1 Document new endpoints in OpenAPI schema
- [ ] 15.2.2 Add request/response examples

### 15.3 Provider Integration Guide
**File:** `docs/PROVIDER_INTEGRATION.md`

- [ ] 15.3.1 Document how to add new providers
- [ ] 15.3.2 Document provider interface requirements
- [ ] 15.3.3 Document pricing update process

---

## Implementation Order

### Phase 1: Database & Models (Foundation)
1. Database migrations (2.1 - 2.4)
2. Integration model updates (3.1)
3. User generation settings model (4.1)
4. API request log model (7.1)

### Phase 2: Backend Services (Core Logic)
5. Provider base classes (3.2)
6. Provider factory (3.8)
7. User generation settings service (4.3)
8. Subtitle service (6.1)
9. API logging service (7.2)
10. Cost estimation service (12.2)

### Phase 3: Provider Implementations
11. Script providers (3.3)
12. Voice providers (3.4)
13. Media providers (3.5)
14. Video AI providers (3.6)
15. Assembly providers with subtitles (3.7)

### Phase 4: Pipeline Refactor
16. Pipeline state machine (5.1)
17. Step executors (5.2)
18. State manager (5.3)
19. Scheduler updates (9.1)
20. Stuck job monitor (9.2)

### Phase 5: API Endpoints
21. User settings endpoints (8.1)
22. Video action endpoints (8.2)
23. Admin logs endpoints (8.4)

### Phase 6: Frontend
24. Settings page updates (10.1 - 10.5)
25. Videos page refactor (11.1 - 11.5)

### Phase 7: Testing & Documentation
26. Unit tests (14.1)
27. Integration tests (14.2)
28. Frontend tests (14.3)
29. Documentation updates (15.1 - 15.3)

---

## Notes

- All provider implementations should be stubbed initially, with real API calls added incrementally
- FFmpeg is the default assembly provider (no API key required)
- Pricing data should be reviewed and updated quarterly
- Log retention policy: Keep logs for 30 days, then archive/delete
