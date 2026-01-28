"""
OpenAI GPT Script Provider

Generates video scripts using OpenAI's GPT models.
Recommended model: gpt-4o
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, TYPE_CHECKING

import httpx

from app.integrations.providers.base import (
    ScriptProvider,
    ProviderResult,
    ProviderCapability,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.integrations.providers.base import ProviderConfig

logger = logging.getLogger(__name__)


class OpenAIGPTProvider(ScriptProvider):
    """
    OpenAI GPT provider for script generation.
    
    Uses GPT-4o by default for high-quality video script generation.
    Generates structured scripts with scenes, narration, and visual prompts.
    """
    
    provider_name = "openai_gpt"
    category = "script"
    capabilities = [ProviderCapability.SCRIPT_GENERATION]
    timeout = 60
    
    # API Configuration
    BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o"
    
    # Script generation system prompt
    SYSTEM_PROMPT = """You are an expert video script writer for short-form viral content.
Your task is to create engaging, attention-grabbing video scripts optimized for platforms like TikTok, YouTube Shorts, and Instagram Reels.

When given a topic, you will generate a complete video script with:
1. A hook that captures attention in the first 2 seconds
2. Multiple scenes with narration and visual descriptions
3. A strong call-to-action at the end

Output your response as valid JSON with this exact structure:
{
    "title": "Video title",
    "hook": "Opening hook text (spoken in first 2 seconds)",
    "scenes": [
        {
            "scene_number": 1,
            "narration": "What the narrator says",
            "visual_prompt": "Description for AI video/image generation",
            "duration_seconds": 5,
            "text_overlay": "Optional text to show on screen"
        }
    ],
    "cta": "Call-to-action text",
    "hashtags": ["relevant", "hashtags"],
    "estimated_duration_seconds": 30
}

Guidelines:
- Keep narration conversational and engaging
- Visual prompts should be specific and descriptive
- Each scene should be 3-7 seconds
- Total duration should match the requested length
- Include trending hooks and patterns
- Make content shareable and memorable"""

    def __init__(
        self,
        api_key: str,
        db: Optional["Session"] = None,
        config: Optional["ProviderConfig"] = None,
    ):
        """
        Initialize the OpenAI GPT provider.
        
        Args:
            api_key: OpenAI API key
            db: Optional database session for logging
            config: Optional provider configuration
        """
        super().__init__(api_key, db, config)
        self.model = self.DEFAULT_MODEL
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get headers for OpenAI API requests."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
    
    async def generate_script(
        self,
        prompt: str,
        num_scenes: int = 5,
        target_duration: int = 30,
    ) -> ProviderResult:
        """
        Generate a video script from a prompt.
        
        Args:
            prompt: User's topic/prompt for the video
            num_scenes: Number of scenes to generate
            target_duration: Target video duration in seconds
            
        Returns:
            ProviderResult with script data
        """
        self._start_time = time.time()
        
        # Build the user prompt
        user_prompt = self._build_user_prompt(prompt, num_scenes, target_duration)
        
        # Prepare API request
        endpoint = f"{self.BASE_URL}/chat/completions"
        
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
        }
        
        try:
            response = await self.client.post(
                endpoint,
                json=request_body,
                headers=self._get_default_headers(),
            )
            
            # Log the request
            await self._log_request(
                endpoint=endpoint,
                method="POST",
                request_body=request_body,
                status_code=response.status_code,
                response_body=response.json() if response.status_code == 200 else None,
                duration_ms=self._get_elapsed_ms(),
            )
            
            if response.status_code != 200:
                return self._handle_http_error(response.status_code, response.text)
            
            # Parse response
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            
            # Parse the JSON script
            script = json.loads(content)
            
            # Validate and enhance script
            script = self._validate_script(script, num_scenes, target_duration)
            
            return self._success(
                data={
                    "title": script.get("title", "Untitled"),
                    "hook": script.get("hook", ""),
                    "scenes": script.get("scenes", []),
                    "cta": script.get("cta", ""),
                    "hashtags": script.get("hashtags", []),
                    "estimated_duration_seconds": script.get("estimated_duration_seconds", target_duration),
                    "provider": self.provider_name,
                    "model": self.model,
                },
                raw_response=response_data,
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse script JSON: {e}")
            return self._failure(
                error="Failed to parse generated script",
                error_details={"parse_error": str(e)},
            )
        except httpx.RequestError as e:
            logger.error(f"OpenAI API request failed: {e}")
            return self._failure(
                error=f"API request failed: {str(e)}",
                error_details={"exception": type(e).__name__},
            )
        except Exception as e:
            logger.exception(f"Script generation failed: {e}")
            return self._failure(
                error=str(e),
                error_details={"exception": type(e).__name__},
            )
    
    def _build_user_prompt(
        self,
        topic: str,
        num_scenes: int,
        target_duration: int,
    ) -> str:
        """Build the user prompt for script generation."""
        
        # Get template config if available
        template_config = self.config.template_config if self.config else {}
        
        tone = template_config.get("script_structure", {}).get("tone_instructions", "engaging and conversational")
        hook_style = template_config.get("video_structure", {}).get("hook_style", "question or surprising fact")
        cta_type = template_config.get("script_structure", {}).get("cta_type", "follow for more")
        
        return f"""Create a viral video script about: {topic}

Requirements:
- Number of scenes: {num_scenes}
- Target duration: {target_duration} seconds
- Tone: {tone}
- Hook style: {hook_style}
- Call-to-action type: {cta_type}

Remember to:
1. Start with an attention-grabbing hook
2. Make each scene visually interesting
3. Keep narration punchy and engaging
4. End with a clear call-to-action

Generate the script in the JSON format specified."""
    
    def _validate_script(
        self,
        script: Dict[str, Any],
        expected_scenes: int,
        target_duration: int,
    ) -> Dict[str, Any]:
        """Validate and fix script structure."""
        
        # Ensure required fields exist
        if "title" not in script:
            script["title"] = "Untitled Video"
        
        if "hook" not in script:
            script["hook"] = ""
        
        if "scenes" not in script:
            script["scenes"] = []
        
        if "cta" not in script:
            script["cta"] = "Follow for more!"
        
        if "hashtags" not in script:
            script["hashtags"] = []
        
        # Validate scenes
        for i, scene in enumerate(script["scenes"]):
            if "scene_number" not in scene:
                scene["scene_number"] = i + 1
            if "narration" not in scene:
                scene["narration"] = ""
            if "visual_prompt" not in scene:
                scene["visual_prompt"] = scene.get("narration", "")
            if "duration_seconds" not in scene:
                scene["duration_seconds"] = target_duration // max(len(script["scenes"]), 1)
            if "text_overlay" not in scene:
                scene["text_overlay"] = None
        
        # Calculate total duration
        total_duration = sum(s.get("duration_seconds", 5) for s in script["scenes"])
        script["estimated_duration_seconds"] = total_duration
        
        return script
    
    async def validate_api_key(self) -> bool:
        """Validate the OpenAI API key."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/models",
                headers=self._get_default_headers(),
            )
            return response.status_code == 200
        except Exception:
            return False
