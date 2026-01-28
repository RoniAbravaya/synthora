"""
FFmpeg Assembly Provider

Assembles final video using FFmpeg.
Supports subtitle burning with styled ASS subtitles.

This is a local provider that doesn't require an API key.
"""

import logging
import time
import os
import subprocess
import tempfile
import shutil
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pathlib import Path

from app.integrations.providers.base import (
    AssemblyProvider,
    ProviderResult,
    ProviderCapability,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.integrations.providers.base import ProviderConfig

logger = logging.getLogger(__name__)


class FFmpegProvider(AssemblyProvider):
    """
    FFmpeg provider for video assembly.
    
    Features:
    - Local video processing (no API costs)
    - Subtitle burning with ASS styling
    - Audio/video merging
    - Multiple output formats
    
    Requirements:
    - FFmpeg must be installed and available in PATH
    """
    
    provider_name = "ffmpeg"
    category = "assembly"
    capabilities = [
        ProviderCapability.VIDEO_ASSEMBLY,
        ProviderCapability.SUBTITLE_BURNING,
    ]
    timeout = 600  # 10 minutes for video processing
    
    # Output settings
    DEFAULT_VIDEO_CODEC = "libx264"
    DEFAULT_AUDIO_CODEC = "aac"
    DEFAULT_CRF = 23  # Quality (lower = better, 18-28 is good range)
    DEFAULT_PRESET = "medium"  # Encoding speed preset
    
    def __init__(
        self,
        api_key: str = "",  # Not needed for FFmpeg
        db: Optional["Session"] = None,
        config: Optional["ProviderConfig"] = None,
    ):
        """Initialize the FFmpeg provider."""
        super().__init__(api_key, db, config)
        self._temp_dir: Optional[str] = None
    
    async def assemble_video(
        self,
        scenes: List[Dict[str, Any]],
        audio_url: str,
        subtitle_file: Optional[str] = None,
    ) -> ProviderResult:
        """
        Assemble final video from components.
        
        Args:
            scenes: List of scene data with media URLs
            audio_url: URL to voiceover audio
            subtitle_file: Optional path to ASS subtitle file
            
        Returns:
            ProviderResult with final video info
        """
        self._start_time = time.time()
        
        # Check FFmpeg is available
        if not self._check_ffmpeg():
            return self._failure(
                error="FFmpeg is not installed or not in PATH",
                error_details={"command": "ffmpeg -version"},
            )
        
        try:
            # Create temp directory for processing
            self._temp_dir = tempfile.mkdtemp(prefix="synthora_ffmpeg_")
            
            # Download all media files
            media_files = await self._download_media(scenes)
            if not media_files:
                return self._failure(
                    error="No media files could be downloaded",
                )
            
            # Download audio
            audio_file = await self._download_file(audio_url, "audio.mp3")
            if not audio_file:
                return self._failure(
                    error="Failed to download audio file",
                )
            
            # Get audio duration
            audio_duration = self._get_duration(audio_file)
            
            # Create video from scenes
            video_file = await self._create_video_from_scenes(
                media_files,
                scenes,
                audio_duration,
            )
            
            if not video_file:
                return self._failure(
                    error="Failed to create video from scenes",
                )
            
            # Merge audio with video
            merged_file = await self._merge_audio_video(
                video_file,
                audio_file,
            )
            
            if not merged_file:
                return self._failure(
                    error="Failed to merge audio and video",
                )
            
            # Burn subtitles if provided
            if subtitle_file and os.path.exists(subtitle_file):
                final_file = await self._burn_subtitles(
                    merged_file,
                    subtitle_file,
                )
                if not final_file:
                    # Continue without subtitles if burning fails
                    logger.warning("Subtitle burning failed, continuing without subtitles")
                    final_file = merged_file
            else:
                final_file = merged_file
            
            # Get final video info
            duration = self._get_duration(final_file)
            file_size = os.path.getsize(final_file)
            resolution = self._get_resolution(final_file)
            
            # In production, upload to cloud storage here
            # For now, return local path
            video_url = final_file
            
            return self._success(
                data={
                    "video_url": video_url,
                    "video_path": final_file,
                    "thumbnail_url": None,  # Could generate thumbnail
                    "duration_seconds": duration,
                    "file_size": file_size,
                    "resolution": resolution,
                    "provider": self.provider_name,
                    "codec": self.DEFAULT_VIDEO_CODEC,
                },
            )
            
        except Exception as e:
            logger.exception(f"Video assembly failed: {e}")
            return self._failure(
                error=str(e),
                error_details={"exception": type(e).__name__},
            )
        finally:
            # Cleanup temp files (but keep final output)
            pass  # Don't cleanup yet - caller needs the file
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def _download_media(
        self,
        scenes: List[Dict[str, Any]],
    ) -> List[str]:
        """Download media files for all scenes."""
        import httpx
        
        files = []
        
        async with httpx.AsyncClient(timeout=60) as client:
            for i, scene in enumerate(scenes):
                media_url = scene.get("media_url") or scene.get("video_url") or scene.get("image_url")
                
                if not media_url:
                    continue
                
                # Determine file extension
                ext = ".mp4" if "video" in scene.get("media_type", "video") else ".jpg"
                filename = f"scene_{i:03d}{ext}"
                filepath = os.path.join(self._temp_dir, filename)
                
                try:
                    response = await client.get(media_url)
                    if response.status_code == 200:
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                        files.append(filepath)
                except Exception as e:
                    logger.error(f"Failed to download media for scene {i}: {e}")
        
        return files
    
    async def _download_file(
        self,
        url: str,
        filename: str,
    ) -> Optional[str]:
        """Download a single file."""
        import httpx
        
        filepath = os.path.join(self._temp_dir, filename)
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        f.write(response.content)
                    return filepath
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
        
        return None
    
    async def _create_video_from_scenes(
        self,
        media_files: List[str],
        scenes: List[Dict[str, Any]],
        target_duration: float,
    ) -> Optional[str]:
        """
        Create a video by concatenating scene media.
        
        Handles both video and image files.
        """
        output_file = os.path.join(self._temp_dir, "scenes.mp4")
        
        # Get aspect ratio
        aspect_ratio = "9:16"
        if self.config:
            aspect_ratio = self.config.aspect_ratio
        
        width, height = self._parse_aspect_ratio(aspect_ratio)
        
        # Create file list for concat
        list_file = os.path.join(self._temp_dir, "files.txt")
        
        # Calculate duration per scene
        scene_duration = target_duration / max(len(media_files), 1)
        
        processed_files = []
        
        for i, media_file in enumerate(media_files):
            scene_data = scenes[i] if i < len(scenes) else {}
            duration = scene_data.get("duration_seconds", scene_duration)
            
            # Process each file to same format/resolution
            processed = await self._process_media_file(
                media_file,
                width,
                height,
                duration,
                i,
            )
            if processed:
                processed_files.append(processed)
        
        if not processed_files:
            return None
        
        # Write concat file list
        with open(list_file, "w") as f:
            for pf in processed_files:
                f.write(f"file '{pf}'\n")
        
        # Concatenate all processed files
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_file,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                return output_file
            
            logger.error(f"FFmpeg concat failed: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"FFmpeg concat error: {e}")
        
        return None
    
    async def _process_media_file(
        self,
        input_file: str,
        width: int,
        height: int,
        duration: float,
        index: int,
    ) -> Optional[str]:
        """Process a single media file to standard format."""
        output_file = os.path.join(self._temp_dir, f"processed_{index:03d}.mp4")
        
        # Check if it's an image or video
        is_image = input_file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
        
        if is_image:
            # Convert image to video
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", input_file,
                "-t", str(duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", self.DEFAULT_VIDEO_CODEC,
                "-pix_fmt", "yuv420p",
                "-r", "30",
                output_file,
            ]
        else:
            # Process video
            cmd = [
                "ffmpeg", "-y",
                "-i", input_file,
                "-t", str(duration),
                "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", self.DEFAULT_VIDEO_CODEC,
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                output_file,
            ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                return output_file
            
            logger.error(f"FFmpeg process failed: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"FFmpeg process error: {e}")
        
        return None
    
    async def _merge_audio_video(
        self,
        video_file: str,
        audio_file: str,
    ) -> Optional[str]:
        """Merge audio track with video."""
        output_file = os.path.join(self._temp_dir, "merged.mp4")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", "copy",
            "-c:a", self.DEFAULT_AUDIO_CODEC,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_file,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                return output_file
            
            logger.error(f"FFmpeg merge failed: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"FFmpeg merge error: {e}")
        
        return None
    
    async def _burn_subtitles(
        self,
        video_file: str,
        subtitle_file: str,
    ) -> Optional[str]:
        """
        Burn subtitles into video.
        
        Uses the ASS subtitle format for styled subtitles.
        """
        output_file = os.path.join(self._temp_dir, "final.mp4")
        
        # Escape special characters in path for FFmpeg filter
        subtitle_path = subtitle_file.replace("\\", "/").replace(":", "\\:")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_file,
            "-vf", f"ass={subtitle_path}",
            "-c:v", self.DEFAULT_VIDEO_CODEC,
            "-c:a", "copy",
            "-crf", str(self.DEFAULT_CRF),
            "-preset", self.DEFAULT_PRESET,
            output_file,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                return output_file
            
            logger.error(f"FFmpeg subtitle burn failed: {result.stderr.decode()}")
        except Exception as e:
            logger.error(f"FFmpeg subtitle error: {e}")
        
        return None
    
    def _get_duration(self, file_path: str) -> float:
        """Get duration of a media file."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return float(result.stdout.decode().strip())
        except Exception as e:
            logger.error(f"Failed to get duration: {e}")
        
        return 0.0
    
    def _get_resolution(self, file_path: str) -> str:
        """Get resolution of a video file."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            file_path,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                output = result.stdout.decode().strip()
                if "," in output:
                    w, h = output.split(",")
                    return f"{w}x{h}"
        except Exception as e:
            logger.error(f"Failed to get resolution: {e}")
        
        return "unknown"
    
    def _parse_aspect_ratio(self, aspect_ratio: str) -> tuple:
        """Parse aspect ratio string to width/height."""
        ratios = {
            "9:16": (1080, 1920),  # Portrait (TikTok, Reels)
            "16:9": (1920, 1080),  # Landscape (YouTube)
            "1:1": (1080, 1080),   # Square (Instagram)
            "4:5": (1080, 1350),   # Portrait (Instagram)
        }
        return ratios.get(aspect_ratio, (1080, 1920))
    
    async def validate_api_key(self) -> bool:
        """Check if FFmpeg is available (no API key needed)."""
        return self._check_ffmpeg()
    
    def cleanup(self):
        """Clean up temporary files."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except Exception as e:
                logger.error(f"Failed to cleanup temp dir: {e}")
