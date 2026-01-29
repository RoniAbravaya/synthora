"""
Video Generation Pipeline Orchestrator

Main orchestrator that coordinates all steps of video generation.
Handles step-by-step execution, state management, and error recovery.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.video import Video, VideoStatus, GenerationStep
from app.models.template import Template
from app.models.integration import Integration, IntegrationCategory, PROVIDER_CATEGORIES
from app.services.video import VideoService
from app.services.integration import IntegrationService

logger = logging.getLogger(__name__)

# Backwards compatibility mapping for old provider names -> new modular names
LEGACY_PROVIDER_MAPPING = {
    "openai": "openai_gpt",      # Old generic OpenAI -> new script-specific
    "sora": "openai_sora",        # Old Sora -> new OpenAI Sora
}


@dataclass
class PipelineConfig:
    """Configuration for the generation pipeline."""
    
    # Template configuration
    template_config: Dict[str, Any] = field(default_factory=dict)
    
    # User's prompt
    prompt: str = ""
    
    # Target duration in seconds
    target_duration: int = 30
    
    # Aspect ratio
    aspect_ratio: str = "9:16"
    
    # Integration preferences
    preferred_script_provider: Optional[str] = None
    preferred_voice_provider: Optional[str] = None
    preferred_media_provider: Optional[str] = None
    preferred_video_ai_provider: Optional[str] = None
    preferred_assembly_provider: Optional[str] = None


@dataclass
class StepResult:
    """Result of a pipeline step."""
    
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    duration_seconds: float = 0.0
    provider_used: Optional[str] = None


class GenerationPipeline:
    """
    Main video generation pipeline orchestrator.
    
    Coordinates all steps of video generation:
    1. Script Generation - Generate video script from prompt
    2. Voice Generation - Generate voice-over audio
    3. Media Fetching - Fetch stock media (images/videos)
    4. Video AI Generation - Generate AI video clips (optional)
    5. Video Assembly - Assemble final video
    
    Features:
    - Step-by-step execution with progress tracking
    - State persistence for resume capability
    - Error handling with full payload capture
    - Integration swapping on failure
    """
    
    # Step order for execution
    STEPS = [
        GenerationStep.SCRIPT,
        GenerationStep.VOICE,
        GenerationStep.MEDIA,
        GenerationStep.VIDEO_AI,
        GenerationStep.ASSEMBLY,
    ]
    
    # Progress percentages for each step
    STEP_PROGRESS = {
        GenerationStep.SCRIPT: (0, 15),
        GenerationStep.VOICE: (15, 35),
        GenerationStep.MEDIA: (35, 55),
        GenerationStep.VIDEO_AI: (55, 80),
        GenerationStep.ASSEMBLY: (80, 100),
    }
    
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
            video: Video being generated
            config: Pipeline configuration
        """
        self.db = db
        self.video = video
        self.config = config
        
        self.video_service = VideoService(db)
        self.integration_service = IntegrationService(db)
        
        # Generation state
        self.state: Dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.current_step: Optional[GenerationStep] = None
        
        # Load user's integrations
        self.integrations = self._load_integrations()
    
    def _load_integrations(self) -> Dict[IntegrationCategory, List[Integration]]:
        """Load user's active integrations grouped by category."""
        integrations = self.integration_service.get_active_integrations(self.video.user_id)
        
        logger.info(f"Found {len(integrations)} active integrations for user {self.video.user_id}")
        
        result: Dict[IntegrationCategory, List[Integration]] = {}
        for integration in integrations:
            # Try both string and enum lookup for provider category
            provider_value = integration.provider
            if hasattr(provider_value, 'value'):
                provider_value = provider_value.value
            
            # Apply legacy provider mapping for backwards compatibility
            # This handles old database records with 'openai' -> 'openai_gpt', 'sora' -> 'openai_sora'
            mapped_provider = LEGACY_PROVIDER_MAPPING.get(provider_value, provider_value)
            if mapped_provider != provider_value:
                logger.info(f"Mapped legacy provider '{provider_value}' -> '{mapped_provider}'")
            
            # Look up category by trying enum first, then string
            category = None
            for prov, cat in PROVIDER_CATEGORIES.items():
                if prov.value == mapped_provider or prov == mapped_provider:
                    category = cat
                    break
            
            if category:
                if category not in result:
                    result[category] = []
                result[category].append(integration)
                logger.info(f"Loaded integration: {provider_value} -> category {category.value}")
            else:
                logger.warning(f"Unknown provider category for: {provider_value} (mapped: {mapped_provider})")
        
        logger.info(f"Integrations by category: {[c.value for c in result.keys()]}")
        return result
    
    def _get_integration(
        self,
        category: IntegrationCategory,
        preferred_provider: Optional[str] = None,
    ) -> Optional[Integration]:
        """
        Get an integration for a category.
        
        Args:
            category: Integration category needed
            preferred_provider: Preferred provider (optional)
            
        Returns:
            Integration instance, or None if not available
        """
        available = self.integrations.get(category, [])
        
        if not available:
            return None
        
        # Try preferred provider first
        if preferred_provider:
            for integration in available:
                if integration.provider == preferred_provider:
                    return integration
        
        # Return first available
        return available[0]
    
    async def run(self) -> bool:
        """
        Run the complete generation pipeline.
        
        Returns:
            True if generation completed successfully
        """
        self.start_time = time.time()
        
        logger.info(f"Starting generation pipeline for video {self.video.id}")
        
        # Update video status
        self.video_service.update_status(
            self.video,
            "processing",
            progress=0,
        )
        
        try:
            # Determine starting step (for resume capability)
            start_step_index = 0
            last_successful = self.video.get_last_successful_step()
            
            if last_successful:
                # Resume from next step
                try:
                    start_step_index = self.STEPS.index(last_successful) + 1
                    # Load previous state
                    self._load_previous_state()
                except ValueError:
                    start_step_index = 0
            
            # Execute each step
            for i, step in enumerate(self.STEPS[start_step_index:], start=start_step_index):
                self.current_step = step
                
                # Update progress
                progress_start, _ = self.STEP_PROGRESS[step]
                self.video_service.update_status(
                    self.video,
                    "processing",
                    current_step=step,
                    progress=progress_start,
                )
                
                # Execute step
                result = await self._execute_step(step)
                
                if not result.success:
                    # Step failed
                    self._handle_step_failure(step, result)
                    return False
                
                # Update step status
                _, progress_end = self.STEP_PROGRESS[step]
                self.video_service.update_step(
                    self.video,
                    step,
                    "completed",
                    progress=100,
                    result=result.data,
                )
                
                # Update overall progress
                self.video_service.update_status(
                    self.video,
                    "processing",
                    progress=progress_end,
                )
            
            # Complete the video
            await self._complete_video()
            return True
            
        except Exception as e:
            logger.exception(f"Pipeline error for video {self.video.id}")
            self.video_service.fail_video(
                self.video,
                str(e),
                {"exception_type": type(e).__name__},
            )
            return False
    
    async def _execute_step(self, step: GenerationStep) -> StepResult:
        """
        Execute a single pipeline step.
        
        Args:
            step: Step to execute
            
        Returns:
            StepResult with outcome
        """
        step_start = time.time()
        
        logger.info(f"Executing step {step.value} for video {self.video.id}")
        
        # Mark step as processing
        self.video_service.update_step(self.video, step, "processing")
        
        try:
            if step == GenerationStep.SCRIPT:
                result = await self._generate_script()
            elif step == GenerationStep.VOICE:
                result = await self._generate_voice()
            elif step == GenerationStep.MEDIA:
                result = await self._fetch_media()
            elif step == GenerationStep.VIDEO_AI:
                result = await self._generate_video_ai()
            elif step == GenerationStep.ASSEMBLY:
                result = await self._assemble_video()
            else:
                result = StepResult(success=False, error=f"Unknown step: {step}")
            
            result.duration_seconds = time.time() - step_start
            return result
            
        except Exception as e:
            logger.exception(f"Step {step.value} failed")
            return StepResult(
                success=False,
                error=str(e),
                error_details={
                    "exception_type": type(e).__name__,
                    "step": step.value,
                },
                duration_seconds=time.time() - step_start,
            )
    
    async def _generate_script(self) -> StepResult:
        """Generate video script using AI."""
        from app.services.generation.script import ScriptGenerator
        
        integration = self._get_integration(
            IntegrationCategory.SCRIPT,
            self.config.preferred_script_provider,
        )
        
        if not integration:
            return StepResult(
                success=False,
                error="No script generation integration configured",
            )
        
        api_key = self.integration_service.get_decrypted_api_key(integration)
        
        generator = ScriptGenerator(api_key, integration.provider)
        result = await generator.generate(
            prompt=self.config.prompt,
            template_config=self.config.template_config,
            target_duration=self.config.target_duration,
        )
        
        if result.success:
            self.state["script"] = result.data
            self.integration_service.mark_used(integration)
        
        result.provider_used = integration.provider
        return result
    
    async def _generate_voice(self) -> StepResult:
        """Generate voice-over audio."""
        from app.services.generation.voice import VoiceGenerator
        
        integration = self._get_integration(
            IntegrationCategory.VOICE,
            self.config.preferred_voice_provider,
        )
        
        if not integration:
            return StepResult(
                success=False,
                error="No voice generation integration configured",
            )
        
        script = self.state.get("script", {})
        if not script:
            return StepResult(
                success=False,
                error="No script available for voice generation",
            )
        
        api_key = self.integration_service.get_decrypted_api_key(integration)
        
        generator = VoiceGenerator(api_key, integration.provider)
        result = await generator.generate(
            script=script,
            template_config=self.config.template_config,
        )
        
        if result.success:
            self.state["voice"] = result.data
            self.integration_service.mark_used(integration)
        
        result.provider_used = integration.provider
        return result
    
    async def _fetch_media(self) -> StepResult:
        """Fetch stock media for the video."""
        from app.services.generation.media import MediaFetcher
        
        integration = self._get_integration(
            IntegrationCategory.MEDIA,
            self.config.preferred_media_provider,
        )
        
        if not integration:
            return StepResult(
                success=False,
                error="No stock media integration configured",
            )
        
        script = self.state.get("script", {})
        if not script:
            return StepResult(
                success=False,
                error="No script available for media fetching",
            )
        
        api_key = self.integration_service.get_decrypted_api_key(integration)
        
        fetcher = MediaFetcher(api_key, integration.provider)
        result = await fetcher.fetch(
            script=script,
            template_config=self.config.template_config,
            aspect_ratio=self.config.aspect_ratio,
        )
        
        if result.success:
            self.state["media"] = result.data
            self.integration_service.mark_used(integration)
        
        result.provider_used = integration.provider
        return result
    
    async def _generate_video_ai(self) -> StepResult:
        """Generate AI video clips (optional step)."""
        from app.services.generation.video_ai import VideoAIGenerator
        
        integration = self._get_integration(
            IntegrationCategory.VIDEO_AI,
            self.config.preferred_video_ai_provider,
        )
        
        # Video AI is optional
        if not integration:
            logger.info("No video AI integration, skipping step")
            self.state["video_ai"] = {"skipped": True}
            return StepResult(
                success=True,
                data={"skipped": True, "reason": "No video AI integration configured"},
            )
        
        script = self.state.get("script", {})
        
        api_key = self.integration_service.get_decrypted_api_key(integration)
        
        generator = VideoAIGenerator(api_key, integration.provider)
        result = await generator.generate(
            script=script,
            template_config=self.config.template_config,
        )
        
        if result.success:
            self.state["video_ai"] = result.data
            self.integration_service.mark_used(integration)
        
        result.provider_used = integration.provider
        return result
    
    async def _assemble_video(self) -> StepResult:
        """Assemble the final video."""
        from app.services.generation.assembly import VideoAssembler
        
        integration = self._get_integration(
            IntegrationCategory.ASSEMBLY,
            self.config.preferred_assembly_provider,
        )
        
        if not integration:
            return StepResult(
                success=False,
                error="No video assembly integration configured",
            )
        
        api_key = self.integration_service.get_decrypted_api_key(integration)
        
        # Generate subtitle file if voice data is available
        subtitle_file = None
        try:
            subtitle_file = self._generate_subtitle_file()
            if subtitle_file:
                logger.info(f"Generated subtitle file: {subtitle_file}")
        except Exception as e:
            logger.warning(f"Failed to generate subtitles: {e}")
        
        assembler = VideoAssembler(api_key, integration.provider)
        result = await assembler.assemble(
            script=self.state.get("script", {}),
            voice=self.state.get("voice", {}),
            media=self.state.get("media", {}),
            video_ai=self.state.get("video_ai", {}),
            template_config=self.config.template_config,
            aspect_ratio=self.config.aspect_ratio,
            user_id=str(self.video.user_id),
            video_id=str(self.video.id),
            subtitle_file=subtitle_file,
        )
        
        if result.success:
            self.state["assembly"] = result.data
            self.integration_service.mark_used(integration)
        
        result.provider_used = integration.provider
        return result
    
    def _generate_subtitle_file(self) -> Optional[str]:
        """
        Generate a subtitle file from voice data.
        
        Uses timing data if available from the voice provider,
        otherwise estimates timing from the narration text.
        
        Returns:
            Path to the generated ASS subtitle file, or None if generation fails
        """
        import tempfile
        import os
        from app.services.subtitle_service import SubtitleService, TimingSegment
        
        voice_data = self.state.get("voice", {})
        if not voice_data:
            logger.info("No voice data available for subtitle generation")
            return None
        
        # Get narration text
        narration_text = voice_data.get("narration_text", "")
        if not narration_text:
            logger.info("No narration text available for subtitle generation")
            return None
        
        # Get or estimate duration
        estimated_duration_seconds = voice_data.get("estimated_duration", 30)
        duration_ms = int(estimated_duration_seconds * 1000)
        
        # Try to get timing segments from voice data if provider supports it
        timing_segments = SubtitleService.segments_from_voice_response(
            voice_data, 
            voice_data.get("provider", "")
        )
        
        # If no timing data from provider, estimate from text
        if not timing_segments:
            logger.info("Estimating subtitle timing from text")
            timing_segments = SubtitleService._estimate_timing_from_text(
                narration_text,
                duration_ms
            )
        
        if not timing_segments:
            logger.info("No timing segments could be generated")
            return None
        
        # Generate ASS subtitle content
        subtitle_service = SubtitleService(style="modern")
        ass_content = subtitle_service.generate_ass(timing_segments)
        
        if not ass_content:
            logger.info("Failed to generate ASS content")
            return None
        
        # Write to temp file
        temp_dir = tempfile.gettempdir()
        subtitle_path = os.path.join(temp_dir, f"subtitles_{self.video.id}.ass")
        
        try:
            with open(subtitle_path, "w", encoding="utf-8") as f:
                f.write(ass_content)
            logger.info(f"Subtitle file written to: {subtitle_path}")
            return subtitle_path
        except Exception as e:
            logger.error(f"Failed to write subtitle file: {e}")
            return None
    
    def _handle_step_failure(self, step: GenerationStep, result: StepResult) -> None:
        """Handle a step failure."""
        logger.error(f"Step {step.value} failed: {result.error}")
        
        # Update step status
        self.video_service.update_step(
            self.video,
            step,
            "failed",
            error=result.error,
        )
        
        # Update video status
        self.video_service.fail_video(
            self.video,
            f"Generation failed at step: {step.value}",
            {
                "step": step.value,
                "error": result.error,
                "error_details": result.error_details,
                "provider_used": result.provider_used,
                "state": self.state,
            },
        )
    
    async def _complete_video(self) -> None:
        """Complete the video generation."""
        assembly_result = self.state.get("assembly", {})
        
        total_time = time.time() - self.start_time if self.start_time else 0
        
        # Collect all providers used
        integrations_used = []
        for step_data in [
            self.state.get("script", {}),
            self.state.get("voice", {}),
            self.state.get("media", {}),
            self.state.get("video_ai", {}),
            self.state.get("assembly", {}),
        ]:
            if step_data.get("provider"):
                integrations_used.append(step_data["provider"])
        
        self.video_service.complete_video(
            self.video,
            video_url=assembly_result.get("video_url", ""),
            thumbnail_url=assembly_result.get("thumbnail_url"),
            duration=assembly_result.get("duration"),
            file_size=assembly_result.get("file_size"),
            resolution=assembly_result.get("resolution"),
            integrations_used=integrations_used,
            generation_time=total_time,
        )
        
        logger.info(f"Video {self.video.id} completed in {total_time:.2f}s")
    
    def _load_previous_state(self) -> None:
        """Load state from previous steps (for resume)."""
        generation_state = self.video.generation_state or {}
        
        for step in GenerationStep:
            step_data = generation_state.get(step.value, {})
            if step_data.get("status") == "completed" and step_data.get("result"):
                # Map step to state key
                state_key = step.value.lower()
                self.state[state_key] = step_data["result"]


async def run_generation_pipeline(
    db: Session,
    video_id: UUID,
    config: PipelineConfig,
) -> bool:
    """
    Convenience function to run the generation pipeline.
    
    Args:
        db: Database session
        video_id: Video ID to generate
        config: Pipeline configuration
        
    Returns:
        True if generation succeeded
    """
    video_service = VideoService(db)
    video = video_service.get_by_id(video_id)
    
    if not video:
        logger.error(f"Video not found: {video_id}")
        return False
    
    pipeline = GenerationPipeline(db, video, config)
    return await pipeline.run()

