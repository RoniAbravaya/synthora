"""
Modular Video Generation Pipeline

Orchestrates video generation using the modular provider system.
Features:
- State machine for generation states
- Concurrency control (1 active per user)
- Timeout detection (30 minutes)
- Resume from failed step
- Subtitle generation
"""

import logging
import time
import os
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from dataclasses import dataclass, field

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.video import Video, VideoStatus, GenerationStep
from app.models.integration import Integration, IntegrationCategory
from app.services.generation.state_manager import PipelineStateManager
from app.services.user_generation_settings import UserGenerationSettingsService
from app.services.subtitle_service import SubtitleService, TimingSegment
from app.services.integration import IntegrationService
from app.services.notification import NotificationService
from app.integrations.providers.factory import ProviderFactory, get_provider
from app.integrations.providers.base import ProviderConfig, ProviderResult

logger = logging.getLogger(__name__)


class ConcurrencyError(Exception):
    """Raised when user already has an active generation."""
    pass


class VideoNotFoundError(Exception):
    """Raised when video is deleted during generation."""
    pass


class VideoCancelledError(Exception):
    """Raised when video generation is cancelled."""
    pass


@dataclass
class PipelineConfig:
    """Configuration for the generation pipeline."""
    
    # User's prompt
    prompt: str = ""
    
    # Template configuration
    template_config: Dict[str, Any] = field(default_factory=dict)
    
    # Target settings
    target_duration: int = 30
    aspect_ratio: str = "9:16"
    num_scenes: int = 5
    
    # Voice settings
    voice_gender: str = "female"
    voice_tone: str = "friendly"
    voice_speed: float = 1.0
    
    # Subtitle settings
    subtitle_style: str = "modern"
    include_subtitles: bool = True
    
    # Provider preferences (overrides user defaults)
    preferred_script_provider: Optional[str] = None
    preferred_voice_provider: Optional[str] = None
    preferred_media_provider: Optional[str] = None
    preferred_video_ai_provider: Optional[str] = None
    preferred_assembly_provider: Optional[str] = None


class ModularGenerationPipeline:
    """
    Modular video generation pipeline.
    
    Coordinates all steps of video generation using the provider system:
    1. Script Generation - Generate video script from prompt
    2. Voice Generation - Generate voice-over audio with timing
    3. Media Fetching - Fetch stock media for scenes
    4. Video AI Generation - Generate AI video clips (optional)
    5. Video Assembly - Assemble final video with subtitles
    
    Features:
    - Modular provider system
    - User-configurable defaults
    - Subtitle generation and burning
    - Concurrency control
    - State persistence for resume
    - 30-minute timeout detection
    """
    
    def __init__(
        self,
        db: Session,
        video: Video,
        config: PipelineConfig,
    ):
        """
        Initialize the pipeline.
        
        Args:
            db: Database session
            video: Video to generate
            config: Pipeline configuration
        """
        self.db = db
        self.video = video
        self.config = config
        
        # Services
        self.state_manager = PipelineStateManager(db, video)
        self.settings_service = UserGenerationSettingsService(db)
        self.integration_service = IntegrationService(db)
        self.provider_factory = ProviderFactory(db)
        
        # Provider configuration
        self.provider_config = ProviderConfig(
            user_id=video.user_id,
            video_id=video.id,
            template_config=config.template_config,
            target_duration=config.target_duration,
            aspect_ratio=config.aspect_ratio,
            num_scenes=config.num_scenes,
            voice_gender=config.voice_gender,
            voice_tone=config.voice_tone,
            voice_speed=config.voice_speed,
            subtitle_style=config.subtitle_style,
            include_subtitles=config.include_subtitles,
        )
        
        # Runtime state
        self._providers: Dict[str, str] = {}
        self._temp_dir: Optional[str] = None
        self._subtitle_file: Optional[str] = None
    
    async def run(self, resume: bool = False) -> bool:
        """
        Run the generation pipeline.
        
        Args:
            resume: If True, resume from last successful step
            
        Returns:
            True if generation completed successfully
        """
        try:
            # Check concurrency
            if not resume:
                self._check_concurrency()
            
            # Load providers
            self._load_providers()
            
            # Save selected providers to video
            self.video.selected_providers = self._providers
            self.db.commit()
            
            # Initialize or load state
            if resume:
                self.state_manager.load_previous_state()
                start_step_index = self._get_resume_index()
            else:
                self.state_manager.initialize()
                start_step_index = 0
            
            logger.info(f"Starting pipeline for video {self.video.id} from step {start_step_index}")
            
            # Create temp directory
            self._temp_dir = tempfile.mkdtemp(prefix="synthora_gen_")
            
            # Execute steps
            steps = [
                (GenerationStep.SCRIPT, self._execute_script),
                (GenerationStep.VOICE, self._execute_voice),
                (GenerationStep.MEDIA, self._execute_media),
                (GenerationStep.VIDEO_AI, self._execute_video_ai),
                (GenerationStep.ASSEMBLY, self._execute_assembly),
            ]
            
            for i, (step, executor) in enumerate(steps):
                if i < start_step_index:
                    continue
                
                # Check if cancelled or deleted
                if self.state_manager.is_cancelled():
                    raise VideoCancelledError("Video generation was cancelled")
                
                if self.state_manager.is_video_deleted():
                    raise VideoNotFoundError("Video was deleted during generation")
                
                # Execute step
                self.state_manager.start_step(step)
                
                result = await executor()
                
                if not result.success:
                    self.state_manager.fail_step(
                        step,
                        result.error,
                        result.error_details,
                    )
                    self._send_failure_notification(step, result.error)
                    return False
                
                self.state_manager.complete_step(step, result.data)
            
            # Complete pipeline
            assembly_result = self.state_manager.get_step_result(GenerationStep.ASSEMBLY)
            
            self.state_manager.complete_pipeline(
                video_url=assembly_result.get("video_url", ""),
                thumbnail_url=assembly_result.get("thumbnail_url"),
                duration=assembly_result.get("duration_seconds"),
                file_size=assembly_result.get("file_size"),
                resolution=assembly_result.get("resolution"),
                subtitle_url=self._subtitle_file,
            )
            
            logger.info(f"Pipeline completed successfully for video {self.video.id}")
            return True
            
        except ConcurrencyError as e:
            logger.warning(f"Concurrency error for video {self.video.id}: {e}")
            self.state_manager.fail_step(
                GenerationStep.SCRIPT,
                str(e),
                {"error_type": "concurrency"},
            )
            return False
            
        except VideoCancelledError:
            logger.info(f"Video {self.video.id} was cancelled")
            return False
            
        except VideoNotFoundError:
            logger.info(f"Video {self.video.id} was deleted")
            return False
            
        except Exception as e:
            logger.exception(f"Pipeline error for video {self.video.id}: {e}")
            
            # Try to update state
            try:
                current_step = self.video.current_step
                if current_step:
                    step = GenerationStep(current_step)
                    self.state_manager.fail_step(step, str(e))
                else:
                    self.video.status = VideoStatus.FAILED.value
                    self.video.error_message = str(e)
                    self.db.commit()
            except Exception:
                pass
            
            return False
            
        finally:
            # Cleanup temp files
            self._cleanup()
    
    def _check_concurrency(self) -> None:
        """Check that user doesn't have another active generation."""
        active_count = self.db.query(Video).filter(
            and_(
                Video.user_id == self.video.user_id,
                Video.status == VideoStatus.PROCESSING.value,
                Video.id != self.video.id,
            )
        ).count()
        
        if active_count > 0:
            raise ConcurrencyError(
                "You already have a video generation in progress. "
                "Please wait for it to complete."
            )
    
    def _load_providers(self) -> None:
        """Load providers based on user settings and config preferences."""
        # Get user's effective providers
        user_providers = self.settings_service.get_effective_providers(self.video.user_id)
        
        # Apply any overrides from config
        self._providers = {
            "script": self.config.preferred_script_provider or user_providers.get("script"),
            "voice": self.config.preferred_voice_provider or user_providers.get("voice"),
            "media": self.config.preferred_media_provider or user_providers.get("media"),
            "video_ai": self.config.preferred_video_ai_provider or user_providers.get("video_ai"),
            "assembly": self.config.preferred_assembly_provider or user_providers.get("assembly") or "ffmpeg",
        }
        
        # Validate required providers are available
        required = ["script", "voice", "media", "assembly"]
        for category in required:
            if not self._providers.get(category):
                raise ValueError(f"No {category} provider configured")
    
    def _get_provider_api_key(self, provider: str) -> str:
        """Get decrypted API key for a provider."""
        integration = self.db.query(Integration).filter(
            and_(
                Integration.user_id == self.video.user_id,
                Integration.provider == provider,
                Integration.is_active == True,
            )
        ).first()
        
        if not integration:
            # FFmpeg doesn't need API key
            if provider == "ffmpeg":
                return ""
            raise ValueError(f"Integration not found for provider: {provider}")
        
        return self.integration_service.get_decrypted_api_key(integration)
    
    def _get_resume_index(self) -> int:
        """Get the step index to resume from."""
        resume_step = self.state_manager.get_resume_step()
        
        if resume_step is None:
            return 0
        
        steps = [
            GenerationStep.SCRIPT,
            GenerationStep.VOICE,
            GenerationStep.MEDIA,
            GenerationStep.VIDEO_AI,
            GenerationStep.ASSEMBLY,
        ]
        
        try:
            return steps.index(resume_step)
        except ValueError:
            return 0
    
    async def _execute_script(self) -> ProviderResult:
        """Execute script generation step."""
        provider_name = self._providers["script"]
        api_key = self._get_provider_api_key(provider_name)
        
        provider = get_provider(provider_name, api_key, self.db, self.provider_config)
        
        if not provider:
            return ProviderResult.failure_result(
                error=f"Script provider not available: {provider_name}",
                provider_name=provider_name,
            )
        
        async with provider:
            result = await provider.execute({
                "prompt": self.config.prompt,
                "num_scenes": self.config.num_scenes,
                "target_duration": self.config.target_duration,
            })
        
        return result
    
    async def _execute_voice(self) -> ProviderResult:
        """Execute voice generation step."""
        provider_name = self._providers["voice"]
        api_key = self._get_provider_api_key(provider_name)
        
        provider = get_provider(provider_name, api_key, self.db, self.provider_config)
        
        if not provider:
            return ProviderResult.failure_result(
                error=f"Voice provider not available: {provider_name}",
                provider_name=provider_name,
            )
        
        # Get script from previous step
        script_result = self.state_manager.get_step_result(GenerationStep.SCRIPT)
        if not script_result:
            return ProviderResult.failure_result(
                error="Script result not found",
                provider_name=provider_name,
            )
        
        # Build full narration text
        narration_parts = []
        
        # Add hook
        hook = script_result.get("hook", "")
        if hook:
            narration_parts.append(hook)
        
        # Add scene narrations
        scenes = script_result.get("scenes", [])
        for scene in scenes:
            narration = scene.get("narration", "")
            if narration:
                narration_parts.append(narration)
        
        # Add CTA
        cta = script_result.get("cta", "")
        if cta:
            narration_parts.append(cta)
        
        full_text = " ".join(narration_parts)
        
        async with provider:
            result = await provider.execute({
                "text": full_text,
            })
        
        # Generate subtitle file if timing available
        if result.success and self.config.include_subtitles:
            timing_segments = result.timing_segments
            
            if timing_segments:
                self._generate_subtitle_file(timing_segments)
            elif result.data.get("duration_seconds"):
                # Estimate timing if not available
                estimated_segments = SubtitleService._estimate_timing_from_text(
                    full_text,
                    int(result.data["duration_seconds"] * 1000),
                )
                if estimated_segments:
                    self._generate_subtitle_file([
                        TimingSegment(s.text, s.start_ms, s.end_ms)
                        for s in estimated_segments
                    ])
        
        return result
    
    async def _execute_media(self) -> ProviderResult:
        """Execute media fetching step."""
        provider_name = self._providers["media"]
        api_key = self._get_provider_api_key(provider_name)
        
        provider = get_provider(provider_name, api_key, self.db, self.provider_config)
        
        if not provider:
            return ProviderResult.failure_result(
                error=f"Media provider not available: {provider_name}",
                provider_name=provider_name,
            )
        
        # Get script for search queries
        script_result = self.state_manager.get_step_result(GenerationStep.SCRIPT)
        if not script_result:
            return ProviderResult.failure_result(
                error="Script result not found",
                provider_name=provider_name,
            )
        
        scenes = script_result.get("scenes", [])
        all_media = []
        
        async with provider:
            for scene in scenes:
                # Use visual prompt as search query
                query = scene.get("visual_prompt", scene.get("narration", ""))
                if not query:
                    continue
                
                result = await provider.execute({
                    "query": query,
                    "media_type": "video",
                    "count": 1,
                })
                
                if result.success and result.data.get("items"):
                    media_item = result.data["items"][0]
                    all_media.append({
                        "scene_number": scene.get("scene_number"),
                        "query": query,
                        "media_url": media_item.get("url"),
                        "media_type": media_item.get("type", "video"),
                        "duration_seconds": scene.get("duration_seconds", 5),
                        "thumbnail_url": media_item.get("thumbnail_url"),
                    })
        
        if not all_media:
            return ProviderResult.failure_result(
                error="No media found for any scene",
                provider_name=provider_name,
            )
        
        return ProviderResult.success_result(
            data={
                "media": all_media,
                "total_scenes": len(all_media),
                "provider": provider_name,
            },
            provider_name=provider_name,
        )
    
    async def _execute_video_ai(self) -> ProviderResult:
        """Execute video AI generation step (optional)."""
        provider_name = self._providers.get("video_ai")
        
        # Video AI is optional
        if not provider_name:
            self.state_manager.skip_step(
                GenerationStep.VIDEO_AI,
                "No video AI provider configured",
            )
            return ProviderResult.success_result(
                data={"skipped": True, "reason": "No video AI provider configured"},
                provider_name="none",
            )
        
        try:
            api_key = self._get_provider_api_key(provider_name)
        except ValueError:
            self.state_manager.skip_step(
                GenerationStep.VIDEO_AI,
                "Video AI integration not found",
            )
            return ProviderResult.success_result(
                data={"skipped": True, "reason": "Video AI integration not found"},
                provider_name="none",
            )
        
        provider = get_provider(provider_name, api_key, self.db, self.provider_config)
        
        if not provider:
            self.state_manager.skip_step(
                GenerationStep.VIDEO_AI,
                f"Video AI provider not available: {provider_name}",
            )
            return ProviderResult.success_result(
                data={"skipped": True, "reason": "Provider not available"},
                provider_name=provider_name,
            )
        
        # Get script for prompts
        script_result = self.state_manager.get_step_result(GenerationStep.SCRIPT)
        if not script_result:
            return ProviderResult.failure_result(
                error="Script result not found",
                provider_name=provider_name,
            )
        
        scenes = script_result.get("scenes", [])
        generated_clips = []
        
        async with provider:
            for scene in scenes:
                prompt = scene.get("visual_prompt", "")
                duration = scene.get("duration_seconds", 5)
                
                result = await provider.execute({
                    "prompt": prompt,
                    "duration": duration,
                    "aspect_ratio": self.config.aspect_ratio,
                })
                
                if result.success:
                    generated_clips.append({
                        "scene_number": scene.get("scene_number"),
                        "video_url": result.data.get("video_url"),
                        "duration_seconds": result.data.get("duration_seconds", duration),
                    })
        
        return ProviderResult.success_result(
            data={
                "generated_clips": generated_clips,
                "total_clips": len(generated_clips),
                "provider": provider_name,
            },
            provider_name=provider_name,
        )
    
    async def _execute_assembly(self) -> ProviderResult:
        """Execute video assembly step."""
        provider_name = self._providers["assembly"]
        api_key = self._get_provider_api_key(provider_name)
        
        provider = get_provider(provider_name, api_key, self.db, self.provider_config)
        
        if not provider:
            return ProviderResult.failure_result(
                error=f"Assembly provider not available: {provider_name}",
                provider_name=provider_name,
            )
        
        # Get previous step results
        script_result = self.state_manager.get_step_result(GenerationStep.SCRIPT)
        voice_result = self.state_manager.get_step_result(GenerationStep.VOICE)
        media_result = self.state_manager.get_step_result(GenerationStep.MEDIA)
        video_ai_result = self.state_manager.get_step_result(GenerationStep.VIDEO_AI)
        
        # Build scenes for assembly
        scenes = []
        script_scenes = script_result.get("scenes", []) if script_result else []
        media_items = media_result.get("media", []) if media_result else []
        ai_clips = video_ai_result.get("generated_clips", []) if video_ai_result else []
        
        for i, script_scene in enumerate(script_scenes):
            scene_data = {
                "scene_number": script_scene.get("scene_number", i + 1),
                "duration_seconds": script_scene.get("duration_seconds", 5),
                "text_overlay": script_scene.get("text_overlay"),
            }
            
            # Prefer AI-generated clips, fall back to stock media
            ai_clip = next(
                (c for c in ai_clips if c.get("scene_number") == scene_data["scene_number"]),
                None
            )
            
            if ai_clip and ai_clip.get("video_url"):
                scene_data["media_url"] = ai_clip["video_url"]
                scene_data["media_type"] = "video"
            else:
                media_item = next(
                    (m for m in media_items if m.get("scene_number") == scene_data["scene_number"]),
                    None
                )
                if media_item:
                    scene_data["media_url"] = media_item.get("media_url")
                    scene_data["media_type"] = media_item.get("media_type", "video")
            
            scenes.append(scene_data)
        
        # Get audio URL
        # In production, this would be a URL to cloud storage
        # For now, we'll handle base64 audio in the provider
        audio_data = voice_result.get("audio_base64", "") if voice_result else ""
        
        async with provider:
            result = await provider.execute({
                "scenes": scenes,
                "audio_url": audio_data,  # Provider will handle base64 or URL
                "subtitle_file": self._subtitle_file,
            })
        
        return result
    
    def _generate_subtitle_file(self, timing_segments: List[TimingSegment]) -> None:
        """Generate and save subtitle file."""
        if not self._temp_dir:
            return
        
        # Get user's subtitle style
        subtitle_config = self.settings_service.get_subtitle_config(self.video.user_id)
        style = self.config.subtitle_style
        
        # Generate ASS file for FFmpeg
        subtitle_service = SubtitleService(style=style)
        ass_content = subtitle_service.generate_ass(timing_segments)
        
        # Save to temp file
        subtitle_path = os.path.join(self._temp_dir, "subtitles.ass")
        with open(subtitle_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        
        self._subtitle_file = subtitle_path
        logger.info(f"Generated subtitle file: {subtitle_path}")
    
    def _send_failure_notification(self, step: GenerationStep, error: str) -> None:
        """Send notification about generation failure."""
        try:
            notification_service = NotificationService(self.db)
            notification_service.create_notification(
                user_id=self.video.user_id,
                notification_type="video_generation_failed",
                title="Video Generation Failed",
                message=f"Your video failed at {step.value}: {error}",
                priority="high",
                metadata={
                    "video_id": str(self.video.id),
                    "failed_step": step.value,
                },
            )
        except Exception as e:
            logger.error(f"Failed to send failure notification: {e}")
    
    def _cleanup(self) -> None:
        """Clean up temporary files."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                import shutil
                # Keep subtitle file if generation succeeded
                # In production, upload to cloud storage first
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Failed to cleanup temp dir: {e}")


async def run_modular_pipeline(
    db: Session,
    video_id: UUID,
    config: PipelineConfig,
    resume: bool = False,
) -> bool:
    """
    Convenience function to run the modular pipeline.
    
    Args:
        db: Database session
        video_id: Video ID to generate
        config: Pipeline configuration
        resume: Whether to resume from last successful step
        
    Returns:
        True if generation succeeded
    """
    from app.services.video import VideoService
    
    video_service = VideoService(db)
    video = video_service.get_by_id(video_id)
    
    if not video:
        logger.error(f"Video not found: {video_id}")
        return False
    
    pipeline = ModularGenerationPipeline(db, video, config)
    return await pipeline.run(resume=resume)
