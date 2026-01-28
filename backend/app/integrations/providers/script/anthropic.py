"""
Anthropic Claude Script Provider

Generates video scripts using Anthropic's Claude models.
Recommended model: claude-3-5-sonnet-20241022
"""

import logging
import json
import time
from typing import Dict, Any, Optional, TYPE_CHECKING

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


class AnthropicProvider(ScriptProvider):
    """
    Anthropic Claude provider for script generation.
    
    Uses Claude 3.5 Sonnet for high-quality creative writing.
    """
    
    provider_name = "anthropic"
    category = "script"
    capabilities = [ProviderCapability.SCRIPT_GENERATION]
    timeout = 60
    
    # API Configuration
    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    API_VERSION = "2023-06-01"
    
    # Script generation system prompt (same as OpenAI for consistency)
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
        """Initialize the Anthropic provider."""
        super().__init__(api_key, db, config)
        self.model = self.DEFAULT_MODEL
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get headers for Anthropic API requests."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
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
        
        user_prompt = self._build_user_prompt(prompt, num_scenes, target_duration)
        endpoint = f"{self.BASE_URL}/messages"
        
        request_body = {
            "model": self.model,
            "max_tokens": 2000,
            "system": self.SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }
        
        try:
            response = await self.client.post(
                endpoint,
                json=request_body,
                headers=self._get_default_headers(),
            )
            
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
            
            response_data = response.json()
            content = response_data["content"][0]["text"]
            
            # Extract JSON from response (Claude may include markdown)
            script = self._extract_json(content)
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
            logger.error(f"Anthropic API request failed: {e}")
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
        template_config = self.config.template_config if self.config else {}
        
        tone = template_config.get("script_structure", {}).get("tone_instructions", "engaging and conversational")
        
        return f"""Create a viral video script about: {topic}

Requirements:
- Number of scenes: {num_scenes}
- Target duration: {target_duration} seconds
- Tone: {tone}

Generate the script as JSON only, no additional text."""
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from text that may include markdown."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find raw JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        raise json.JSONDecodeError("No JSON found in response", text, 0)
    
    def _validate_script(
        self,
        script: Dict[str, Any],
        expected_scenes: int,
        target_duration: int,
    ) -> Dict[str, Any]:
        """Validate and fix script structure."""
        # Same validation as OpenAI provider
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
        
        for i, scene in enumerate(script["scenes"]):
            if "scene_number" not in scene:
                scene["scene_number"] = i + 1
            if "narration" not in scene:
                scene["narration"] = ""
            if "visual_prompt" not in scene:
                scene["visual_prompt"] = scene.get("narration", "")
            if "duration_seconds" not in scene:
                scene["duration_seconds"] = target_duration // max(len(script["scenes"]), 1)
        
        total_duration = sum(s.get("duration_seconds", 5) for s in script["scenes"])
        script["estimated_duration_seconds"] = total_duration
        
        return script
    
    async def validate_api_key(self) -> bool:
        """Validate the Anthropic API key."""
        try:
            # Simple validation request
            response = await self.client.post(
                f"{self.BASE_URL}/messages",
                json={
                    "model": self.model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
                headers=self._get_default_headers(),
            )
            return response.status_code == 200
        except Exception:
            return False
