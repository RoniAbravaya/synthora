"""
Script Generation Service

Generates video scripts using AI (OpenAI).
"""

import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import httpx

from app.models.integration import IntegrationProvider
from app.services.generation.pipeline import StepResult

logger = logging.getLogger(__name__)


@dataclass
class ScriptScene:
    """Represents a single scene in the script."""
    
    scene_number: int
    duration: float  # seconds
    narration: str
    visual_description: str
    text_overlay: Optional[str] = None
    sound_effects: Optional[List[str]] = None


@dataclass
class VideoScript:
    """Complete video script."""
    
    title: str
    hook: str
    scenes: List[ScriptScene]
    cta: str
    total_duration: float
    hashtags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "hook": self.hook,
            "scenes": [
                {
                    "scene_number": s.scene_number,
                    "duration": s.duration,
                    "narration": s.narration,
                    "visual_description": s.visual_description,
                    "text_overlay": s.text_overlay,
                    "sound_effects": s.sound_effects,
                }
                for s in self.scenes
            ],
            "cta": self.cta,
            "total_duration": self.total_duration,
            "hashtags": self.hashtags,
        }


class ScriptGenerator:
    """
    Generates video scripts using AI.
    
    Currently supports:
    - OpenAI (GPT-4, GPT-3.5)
    
    The generator uses template configuration to customize the script
    structure, tone, and style.
    """
    
    def __init__(self, api_key: str, provider: IntegrationProvider):
        """
        Initialize the script generator.
        
        Args:
            api_key: API key for the provider
            provider: Integration provider to use
        """
        self.api_key = api_key
        self.provider = provider
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate(
        self,
        prompt: str,
        template_config: Dict[str, Any],
        target_duration: int = 30,
    ) -> StepResult:
        """
        Generate a video script.
        
        Args:
            prompt: User's topic/prompt
            template_config: Template configuration
            target_duration: Target video duration in seconds
            
        Returns:
            StepResult with script data
        """
        try:
            if self.provider == IntegrationProvider.OPENAI_GPT:
                return await self._generate_openai(prompt, template_config, target_duration)
            else:
                return StepResult(
                    success=False,
                    error=f"Unsupported script provider: {self.provider}",
                )
        except Exception as e:
            logger.exception("Script generation failed")
            return StepResult(
                success=False,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
            )
        finally:
            await self.client.aclose()
    
    async def _generate_openai(
        self,
        prompt: str,
        template_config: Dict[str, Any],
        target_duration: int,
    ) -> StepResult:
        """Generate script using OpenAI."""
        
        # Build the system prompt
        system_prompt = self._build_system_prompt(template_config, target_duration)
        
        # Build the user prompt
        user_prompt = self._build_user_prompt(prompt, template_config)
        
        # Call OpenAI API
        response = await self.client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
            },
        )
        
        if response.status_code != 200:
            error_data = response.json()
            return StepResult(
                success=False,
                error=f"OpenAI API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                error_details=error_data,
            )
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse the JSON response
        try:
            script_data = json.loads(content)
        except json.JSONDecodeError as e:
            return StepResult(
                success=False,
                error=f"Failed to parse script JSON: {e}",
                error_details={"raw_content": content[:500]},
            )
        
        # Validate and structure the script
        script = self._parse_script(script_data, target_duration)
        
        return StepResult(
            success=True,
            data={
                "script": script.to_dict(),
                "provider": self.provider,
                "model": "gpt-4-turbo-preview",
                "raw_response": script_data,
            },
        )
    
    def _build_system_prompt(
        self,
        template_config: Dict[str, Any],
        target_duration: int,
    ) -> str:
        """Build the system prompt for script generation."""
        
        # Get template-specific instructions
        script_prompt = template_config.get("script_prompt", {})
        structure_prompt = script_prompt.get("structure_prompt", "")
        tone_instructions = script_prompt.get("tone_instructions", "")
        
        # Get video structure settings
        video_structure = template_config.get("video_structure", {})
        hook_style = video_structure.get("hook_style", "question")
        narrative_structure = video_structure.get("narrative_structure", "hook_problem_solution_cta")
        num_scenes = video_structure.get("num_scenes", 5)
        pacing = video_structure.get("pacing", "medium")
        
        # Get CTA settings
        cta_type = script_prompt.get("cta_type", "follow")
        
        system_prompt = f"""You are an expert viral video scriptwriter. Your task is to create engaging, 
attention-grabbing video scripts optimized for social media platforms.

TARGET DURATION: {target_duration} seconds
NUMBER OF SCENES: {num_scenes}
PACING: {pacing}
HOOK STYLE: {hook_style}
NARRATIVE STRUCTURE: {narrative_structure}
CTA TYPE: {cta_type}

{structure_prompt}

TONE AND STYLE:
{tone_instructions if tone_instructions else "Be engaging, concise, and optimized for social media attention spans."}

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
    "title": "Video title (catchy, clickable)",
    "hook": "Opening hook text (first 3 seconds)",
    "scenes": [
        {{
            "scene_number": 1,
            "duration": <seconds>,
            "narration": "What the narrator says",
            "visual_description": "What should be shown on screen",
            "text_overlay": "Text to display on screen (optional)",
            "sound_effects": ["effect1", "effect2"] (optional)
        }}
    ],
    "cta": "Call to action text",
    "hashtags": ["hashtag1", "hashtag2", ...]
}}

RULES:
1. The hook MUST grab attention in the first 3 seconds
2. Each scene should have clear visual descriptions for media selection
3. Narration should be natural and conversational
4. Total duration of all scenes must approximately equal target duration
5. Include relevant, trending hashtags
6. Make it shareable and engaging"""

        return system_prompt
    
    def _build_user_prompt(
        self,
        prompt: str,
        template_config: Dict[str, Any],
    ) -> str:
        """Build the user prompt."""
        
        # Get platform targets
        platforms = template_config.get("basic_info", {}).get("target_platforms", ["tiktok", "instagram"])
        
        user_prompt = f"""Create a viral video script about: {prompt}

Target platforms: {', '.join(platforms)}

Make it engaging, shareable, and optimized for these platforms. 
The script should feel authentic and not overly promotional."""

        return user_prompt
    
    def _parse_script(
        self,
        script_data: Dict[str, Any],
        target_duration: int,
    ) -> VideoScript:
        """Parse and validate the script data."""
        
        scenes = []
        total_duration = 0
        
        for scene_data in script_data.get("scenes", []):
            scene = ScriptScene(
                scene_number=scene_data.get("scene_number", len(scenes) + 1),
                duration=float(scene_data.get("duration", 5)),
                narration=scene_data.get("narration", ""),
                visual_description=scene_data.get("visual_description", ""),
                text_overlay=scene_data.get("text_overlay"),
                sound_effects=scene_data.get("sound_effects"),
            )
            scenes.append(scene)
            total_duration += scene.duration
        
        return VideoScript(
            title=script_data.get("title", "Untitled Video"),
            hook=script_data.get("hook", ""),
            scenes=scenes,
            cta=script_data.get("cta", ""),
            total_duration=total_duration,
            hashtags=script_data.get("hashtags", []),
        )

