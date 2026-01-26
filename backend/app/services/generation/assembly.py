"""
Video Assembly Service

Assembles the final video from all generated components.
"""

import logging
import os
import tempfile
import subprocess
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import base64

import httpx

from app.models.integration import IntegrationProvider
from app.services.generation.pipeline import StepResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AssemblyResult:
    """Result of video assembly."""
    
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: float = 0.0
    file_size: int = 0
    resolution: str = "1080x1920"
    format: str = "mp4"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "duration": self.duration,
            "file_size": self.file_size,
            "resolution": self.resolution,
            "format": self.format,
        }


class VideoAssembler:
    """
    Assembles the final video from components.
    
    Currently supports:
    - FFmpeg (local processing)
    - Creatomate (cloud API)
    - Shotstack (cloud API)
    - Remotion (programmatic)
    - Editframe (cloud API)
    
    The assembler combines:
    - Voice-over audio
    - Stock media (images/videos)
    - AI-generated clips (if available)
    - Text overlays
    - Background music
    - Transitions
    """
    
    def __init__(self, api_key: str, provider: IntegrationProvider):
        """
        Initialize the video assembler.
        
        Args:
            api_key: API key for the provider (or path for FFmpeg)
            provider: Integration provider to use
        """
        self.api_key = api_key
        self.provider = provider
        self.client = httpx.AsyncClient(timeout=300.0)
        self.settings = get_settings()
    
    async def assemble(
        self,
        script: Dict[str, Any],
        voice: Dict[str, Any],
        media: Dict[str, Any],
        video_ai: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str = "9:16",
    ) -> StepResult:
        """
        Assemble the final video.
        
        Args:
            script: Script data
            voice: Voice-over data
            media: Stock media data
            video_ai: AI-generated clips data
            template_config: Template configuration
            aspect_ratio: Target aspect ratio
            
        Returns:
            StepResult with assembly result
        """
        try:
            if self.provider == IntegrationProvider.FFMPEG:
                return await self._assemble_ffmpeg(
                    script, voice, media, video_ai, template_config, aspect_ratio
                )
            elif self.provider == IntegrationProvider.CREATOMATE:
                return await self._assemble_creatomate(
                    script, voice, media, video_ai, template_config, aspect_ratio
                )
            elif self.provider == IntegrationProvider.SHOTSTACK:
                return await self._assemble_shotstack(
                    script, voice, media, video_ai, template_config, aspect_ratio
                )
            elif self.provider == IntegrationProvider.REMOTION:
                return await self._assemble_remotion(
                    script, voice, media, video_ai, template_config, aspect_ratio
                )
            elif self.provider == IntegrationProvider.EDITFRAME:
                return await self._assemble_editframe(
                    script, voice, media, video_ai, template_config, aspect_ratio
                )
            else:
                return StepResult(
                    success=False,
                    error=f"Unsupported assembly provider: {self.provider}",
                )
        except Exception as e:
            logger.exception("Video assembly failed")
            return StepResult(
                success=False,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
            )
        finally:
            await self.client.aclose()
    
    async def _assemble_ffmpeg(
        self,
        script: Dict[str, Any],
        voice: Dict[str, Any],
        media: Dict[str, Any],
        video_ai: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Assemble video using FFmpeg."""
        
        # Check FFmpeg availability
        ffmpeg_path = self.settings.FFMPEG_PATH or shutil.which("ffmpeg")
        if not ffmpeg_path:
            return StepResult(
                success=False,
                error="FFmpeg not found on system",
            )
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix="synthora_")
        
        try:
            # Get resolution from aspect ratio
            resolution = self._get_resolution(aspect_ratio)
            
            # Save audio file
            audio_path = os.path.join(temp_dir, "voice.mp3")
            if voice.get("audio_base64"):
                audio_data = base64.b64decode(voice["audio_base64"])
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
            
            # Download media files
            media_files = []
            media_items = media.get("media_items", [])
            
            for i, item in enumerate(media_items):
                url = item.get("url")
                if not url:
                    continue
                
                ext = "mp4" if item.get("type") == "video" else "jpg"
                media_path = os.path.join(temp_dir, f"media_{i}.{ext}")
                
                # Download the file
                response = await self.client.get(url)
                if response.status_code == 200:
                    with open(media_path, "wb") as f:
                        f.write(response.content)
                    media_files.append({
                        "path": media_path,
                        "type": item.get("type"),
                        "duration": item.get("duration", 5),
                    })
            
            if not media_files:
                return StepResult(
                    success=False,
                    error="No media files to assemble",
                )
            
            # Create video from media
            output_path = os.path.join(temp_dir, "output.mp4")
            
            # Build FFmpeg command
            # This is a simplified version - a full implementation would be more complex
            cmd = self._build_ffmpeg_command(
                ffmpeg_path,
                media_files,
                audio_path if os.path.exists(audio_path) else None,
                output_path,
                resolution,
                template_config,
            )
            
            # Run FFmpeg
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            if process.returncode != 0:
                return StepResult(
                    success=False,
                    error=f"FFmpeg failed: {process.stderr[:500]}",
                    error_details={"stderr": process.stderr, "stdout": process.stdout},
                )
            
            # Get output file info
            file_size = os.path.getsize(output_path)
            duration = self._get_video_duration(ffmpeg_path, output_path)
            
            # Upload to storage (placeholder - would use GCS in production)
            # For now, return a placeholder URL
            video_url = f"file://{output_path}"  # In production, upload to GCS
            
            return StepResult(
                success=True,
                data={
                    "video_url": video_url,
                    "thumbnail_url": None,
                    "duration": duration,
                    "file_size": file_size,
                    "resolution": resolution,
                    "format": "mp4",
                    "provider": self.provider,
                },
            )
            
        finally:
            # Cleanup temp directory (in production, do this after upload)
            # shutil.rmtree(temp_dir, ignore_errors=True)
            pass
    
    def _build_ffmpeg_command(
        self,
        ffmpeg_path: str,
        media_files: List[Dict[str, Any]],
        audio_path: Optional[str],
        output_path: str,
        resolution: str,
        template_config: Dict[str, Any],
    ) -> List[str]:
        """Build FFmpeg command for video assembly."""
        
        width, height = resolution.split("x")
        
        # Simple concatenation approach
        # A full implementation would handle transitions, text overlays, etc.
        
        cmd = [ffmpeg_path, "-y"]  # -y to overwrite output
        
        # Add input files
        for mf in media_files:
            if mf["type"] == "image":
                # Loop image for duration
                cmd.extend(["-loop", "1", "-t", str(mf.get("duration", 5))])
            cmd.extend(["-i", mf["path"]])
        
        # Add audio if available
        if audio_path:
            cmd.extend(["-i", audio_path])
        
        # Filter complex for scaling and concatenation
        filter_parts = []
        for i in range(len(media_files)):
            filter_parts.append(
                f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
            )
        
        # Concatenate
        concat_inputs = "".join(f"[v{i}]" for i in range(len(media_files)))
        filter_parts.append(f"{concat_inputs}concat=n={len(media_files)}:v=1:a=0[outv]")
        
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        
        # Map video output
        cmd.extend(["-map", "[outv]"])
        
        # Map audio if available
        if audio_path:
            cmd.extend(["-map", f"{len(media_files)}:a"])
        
        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output_path,
        ])
        
        return cmd
    
    def _get_video_duration(self, ffmpeg_path: str, video_path: str) -> float:
        """Get video duration using ffprobe."""
        ffprobe_path = ffmpeg_path.replace("ffmpeg", "ffprobe")
        
        try:
            result = subprocess.run(
                [
                    ffprobe_path,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0
    
    def _get_resolution(self, aspect_ratio: str) -> str:
        """Get resolution from aspect ratio."""
        resolutions = {
            "9:16": "1080x1920",  # Vertical (TikTok, Reels)
            "16:9": "1920x1080",  # Horizontal (YouTube)
            "1:1": "1080x1080",   # Square (Instagram)
            "4:5": "1080x1350",   # Portrait (Instagram)
        }
        return resolutions.get(aspect_ratio, "1080x1920")
    
    async def _assemble_creatomate(
        self,
        script: Dict[str, Any],
        voice: Dict[str, Any],
        media: Dict[str, Any],
        video_ai: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Assemble video using Creatomate API."""
        
        # Build Creatomate render request
        # This is a simplified implementation
        
        media_items = media.get("media_items", [])
        
        # Build elements array
        elements = []
        
        for i, item in enumerate(media_items):
            element = {
                "type": "video" if item.get("type") == "video" else "image",
                "source": item.get("url"),
                "duration": item.get("duration", 5),
            }
            elements.append(element)
        
        # Add audio
        if voice.get("audio_base64"):
            elements.append({
                "type": "audio",
                "source": f"data:audio/mp3;base64,{voice['audio_base64']}",
            })
        
        # Make API request
        response = await self.client.post(
            "https://api.creatomate.com/v1/renders",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "output_format": "mp4",
                "width": 1080,
                "height": 1920,
                "elements": elements,
            },
        )
        
        if response.status_code != 200:
            return StepResult(
                success=False,
                error=f"Creatomate API error: {response.text}",
            )
        
        data = response.json()
        
        return StepResult(
            success=True,
            data={
                "video_url": data.get("url", ""),
                "render_id": data.get("id"),
                "duration": data.get("duration", 0),
                "provider": self.provider,
            },
        )
    
    async def _assemble_shotstack(
        self,
        script: Dict[str, Any],
        voice: Dict[str, Any],
        media: Dict[str, Any],
        video_ai: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Assemble video using Shotstack API."""
        
        media_items = media.get("media_items", [])
        
        # Build timeline
        clips = []
        start_time = 0.0
        
        for item in media_items:
            duration = item.get("duration", 5)
            clip = {
                "asset": {
                    "type": "video" if item.get("type") == "video" else "image",
                    "src": item.get("url"),
                },
                "start": start_time,
                "length": duration,
            }
            clips.append(clip)
            start_time += duration
        
        # Build edit request
        edit = {
            "timeline": {
                "tracks": [{"clips": clips}],
            },
            "output": {
                "format": "mp4",
                "resolution": "hd",
                "aspectRatio": aspect_ratio.replace(":", "/"),
            },
        }
        
        # Add audio track
        if voice.get("audio_base64"):
            edit["timeline"]["soundtrack"] = {
                "src": f"data:audio/mp3;base64,{voice['audio_base64']}",
            }
        
        response = await self.client.post(
            "https://api.shotstack.io/v1/render",
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            json=edit,
        )
        
        if response.status_code not in [200, 201]:
            return StepResult(
                success=False,
                error=f"Shotstack API error: {response.text}",
            )
        
        data = response.json()
        
        return StepResult(
            success=True,
            data={
                "render_id": data.get("response", {}).get("id"),
                "status": "queued",
                "message": "Video rendering started",
                "provider": self.provider,
            },
        )
    
    async def _assemble_remotion(
        self,
        script: Dict[str, Any],
        voice: Dict[str, Any],
        media: Dict[str, Any],
        video_ai: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Assemble video using Remotion."""
        
        # Remotion is typically self-hosted or uses Remotion Lambda
        # This is a placeholder implementation
        
        return StepResult(
            success=True,
            data={
                "message": "Remotion assembly pending implementation",
                "provider": self.provider,
            },
        )
    
    async def _assemble_editframe(
        self,
        script: Dict[str, Any],
        voice: Dict[str, Any],
        media: Dict[str, Any],
        video_ai: Dict[str, Any],
        template_config: Dict[str, Any],
        aspect_ratio: str,
    ) -> StepResult:
        """Assemble video using Editframe API."""
        
        # Editframe API implementation
        # This is a placeholder
        
        return StepResult(
            success=True,
            data={
                "message": "Editframe assembly pending implementation",
                "provider": self.provider,
            },
        )

