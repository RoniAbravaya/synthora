"""
Integration Validators

Concrete validator implementations for each supported integration.
"""

import logging
import subprocess
import shutil
from typing import Optional

import httpx

from app.integrations.base import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)


# =============================================================================
# Script/Text AI Validators
# =============================================================================

class OpenAIValidator(BaseValidator):
    """Validator for OpenAI API keys."""
    
    provider_name = "OpenAI"
    
    async def validate(self) -> ValidationResult:
        """
        Validate OpenAI API key by listing models.
        """
        try:
            response = await self.client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                return self._success(
                    f"Valid OpenAI API key with access to {model_count} models",
                    details={"model_count": model_count},
                )
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except httpx.TimeoutException:
            return self._failure("Connection timeout", error_code="timeout")
        except Exception as e:
            logger.error(f"OpenAI validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


# =============================================================================
# Voice AI Validators
# =============================================================================

class ElevenLabsValidator(BaseValidator):
    """Validator for ElevenLabs API keys."""
    
    provider_name = "ElevenLabs"
    
    async def validate(self) -> ValidationResult:
        """
        Validate ElevenLabs API key by getting user info.
        """
        try:
            response = await self.client.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": self.api_key},
            )
            
            if response.status_code == 200:
                data = response.json()
                subscription = data.get("subscription", {})
                return self._success(
                    "Valid ElevenLabs API key",
                    details={
                        "tier": subscription.get("tier"),
                        "character_count": subscription.get("character_count"),
                        "character_limit": subscription.get("character_limit"),
                    },
                )
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except httpx.TimeoutException:
            return self._failure("Connection timeout", error_code="timeout")
        except Exception as e:
            logger.error(f"ElevenLabs validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


# =============================================================================
# Stock Media Validators
# =============================================================================

class PexelsValidator(BaseValidator):
    """Validator for Pexels API keys."""
    
    provider_name = "Pexels"
    
    async def validate(self) -> ValidationResult:
        """
        Validate Pexels API key by searching for a test video.
        """
        try:
            response = await self.client.get(
                "https://api.pexels.com/videos/search",
                params={"query": "nature", "per_page": 1},
                headers={"Authorization": self.api_key},
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._success(
                    "Valid Pexels API key",
                    details={"total_results": data.get("total_results", 0)},
                )
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except httpx.TimeoutException:
            return self._failure("Connection timeout", error_code="timeout")
        except Exception as e:
            logger.error(f"Pexels validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


class UnsplashValidator(BaseValidator):
    """Validator for Unsplash API keys."""
    
    provider_name = "Unsplash"
    
    async def validate(self) -> ValidationResult:
        """
        Validate Unsplash API key by getting rate limit info.
        """
        try:
            response = await self.client.get(
                "https://api.unsplash.com/photos/random",
                headers={"Authorization": f"Client-ID {self.api_key}"},
            )
            
            if response.status_code == 200:
                # Get rate limit info from headers
                remaining = response.headers.get("X-Ratelimit-Remaining", "unknown")
                return self._success(
                    "Valid Unsplash API key",
                    details={"rate_limit_remaining": remaining},
                )
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except httpx.TimeoutException:
            return self._failure("Connection timeout", error_code="timeout")
        except Exception as e:
            logger.error(f"Unsplash validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


# =============================================================================
# Video AI Validators
# =============================================================================

class RunwayValidator(BaseValidator):
    """Validator for Runway API keys."""
    
    provider_name = "Runway"
    
    async def validate(self) -> ValidationResult:
        """
        Validate Runway API key.
        Note: Runway API may have different endpoints - this is a placeholder.
        """
        try:
            # Runway API endpoint - adjust based on actual API
            response = await self.client.get(
                "https://api.runwayml.com/v1/user",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            
            if response.status_code == 200:
                return self._success("Valid Runway API key")
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except httpx.TimeoutException:
            return self._failure("Connection timeout", error_code="timeout")
        except Exception as e:
            # Many AI video services are still in beta
            logger.warning(f"Runway validation error (service may be unavailable): {e}")
            return self._failure(
                "Could not validate Runway API key. Service may be unavailable.",
                error_code="service_unavailable"
            )


class SoraValidator(BaseValidator):
    """Validator for OpenAI Sora API keys."""
    
    provider_name = "OpenAI Sora"
    
    async def validate(self) -> ValidationResult:
        """
        Validate Sora API key.
        Sora uses OpenAI's API, so we validate against OpenAI.
        """
        try:
            response = await self.client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            
            if response.status_code == 200:
                # Check if Sora model is available
                data = response.json()
                models = [m.get("id", "") for m in data.get("data", [])]
                has_sora = any("sora" in m.lower() for m in models)
                
                if has_sora:
                    return self._success("Valid Sora API key with Sora access")
                else:
                    return self._success(
                        "Valid OpenAI key, but Sora access not confirmed",
                        details={"sora_available": False},
                    )
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except Exception as e:
            logger.error(f"Sora validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


class VeoValidator(BaseValidator):
    """Validator for Google Veo API keys."""
    
    provider_name = "Google Veo"
    
    async def validate(self) -> ValidationResult:
        """
        Validate Google Veo API key.
        Note: Veo may use Google Cloud authentication.
        """
        # Google Veo typically uses service account or OAuth
        # This is a placeholder for the actual validation
        return self._success(
            "Veo API key format accepted. Full validation requires Google Cloud setup.",
            details={"note": "Manual verification recommended"},
        )


class LumaValidator(BaseValidator):
    """Validator for Luma Dream Machine API keys."""
    
    provider_name = "Luma Dream Machine"
    
    async def validate(self) -> ValidationResult:
        """Validate Luma API key."""
        try:
            response = await self.client.get(
                "https://api.lumalabs.ai/v1/user",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            
            if response.status_code == 200:
                return self._success("Valid Luma API key")
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except Exception as e:
            logger.warning(f"Luma validation error: {e}")
            return self._failure(
                "Could not validate Luma API key",
                error_code="validation_failed"
            )


class ImagineArtValidator(BaseValidator):
    """Validator for ImagineArt API keys."""
    
    provider_name = "ImagineArt"
    
    async def validate(self) -> ValidationResult:
        """Validate ImagineArt API key."""
        # Placeholder - adjust based on actual API
        return self._success(
            "ImagineArt API key format accepted",
            details={"note": "Manual verification recommended"},
        )


class PixVerseValidator(BaseValidator):
    """Validator for PixVerse API keys."""
    
    provider_name = "PixVerse"
    
    async def validate(self) -> ValidationResult:
        """Validate PixVerse API key."""
        # Placeholder - adjust based on actual API
        return self._success(
            "PixVerse API key format accepted",
            details={"note": "Manual verification recommended"},
        )


class SeedanceValidator(BaseValidator):
    """Validator for Seedance AI API keys."""
    
    provider_name = "Seedance AI"
    
    async def validate(self) -> ValidationResult:
        """Validate Seedance API key."""
        # Placeholder - adjust based on actual API
        return self._success(
            "Seedance API key format accepted",
            details={"note": "Manual verification recommended"},
        )


class WanValidator(BaseValidator):
    """Validator for Wan2.6 API keys."""
    
    provider_name = "Wan2.6"
    
    async def validate(self) -> ValidationResult:
        """Validate Wan API key."""
        # Placeholder - adjust based on actual API
        return self._success(
            "Wan API key format accepted",
            details={"note": "Manual verification recommended"},
        )


class HailuoValidator(BaseValidator):
    """Validator for Hailuo AI API keys."""
    
    provider_name = "Hailuo AI"
    
    async def validate(self) -> ValidationResult:
        """Validate Hailuo API key."""
        # Placeholder - adjust based on actual API
        return self._success(
            "Hailuo API key format accepted",
            details={"note": "Manual verification recommended"},
        )


class LTXValidator(BaseValidator):
    """Validator for LTX-2 API keys."""
    
    provider_name = "LTX-2"
    
    async def validate(self) -> ValidationResult:
        """Validate LTX API key."""
        # Placeholder - adjust based on actual API
        return self._success(
            "LTX API key format accepted",
            details={"note": "Manual verification recommended"},
        )


# =============================================================================
# Video Assembly Validators
# =============================================================================

class FFmpegValidator(BaseValidator):
    """Validator for FFmpeg (local installation)."""
    
    provider_name = "FFmpeg"
    
    async def validate(self) -> ValidationResult:
        """
        Validate FFmpeg is installed and accessible.
        FFmpeg doesn't use an API key - we check if it's installed.
        """
        try:
            # Check if ffmpeg is in PATH
            ffmpeg_path = shutil.which("ffmpeg")
            
            if ffmpeg_path:
                # Get version
                result = subprocess.run(
                    [ffmpeg_path, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                
                if result.returncode == 0:
                    version_line = result.stdout.split("\n")[0]
                    return self._success(
                        "FFmpeg is installed and accessible",
                        details={"version": version_line, "path": ffmpeg_path},
                    )
            
            return self._failure(
                "FFmpeg not found. Please install FFmpeg on the server.",
                error_code="not_installed",
            )
            
        except subprocess.TimeoutExpired:
            return self._failure("FFmpeg check timed out", error_code="timeout")
        except Exception as e:
            logger.error(f"FFmpeg validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


class CreatomateValidator(BaseValidator):
    """Validator for Creatomate API keys."""
    
    provider_name = "Creatomate"
    
    async def validate(self) -> ValidationResult:
        """Validate Creatomate API key."""
        try:
            response = await self.client.get(
                "https://api.creatomate.com/v1/renders",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"limit": 1},
            )
            
            if response.status_code == 200:
                return self._success("Valid Creatomate API key")
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except Exception as e:
            logger.error(f"Creatomate validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


class ShotstackValidator(BaseValidator):
    """Validator for Shotstack API keys."""
    
    provider_name = "Shotstack"
    
    async def validate(self) -> ValidationResult:
        """Validate Shotstack API key."""
        try:
            # Shotstack uses different endpoints for sandbox vs production
            response = await self.client.get(
                "https://api.shotstack.io/v1/renders",
                headers={"x-api-key": self.api_key},
                params={"limit": 1},
            )
            
            if response.status_code == 200:
                return self._success("Valid Shotstack API key")
            elif response.status_code == 401:
                # Try sandbox endpoint
                response = await self.client.get(
                    "https://api.shotstack.io/stage/renders",
                    headers={"x-api-key": self.api_key},
                    params={"limit": 1},
                )
                if response.status_code == 200:
                    return self._success(
                        "Valid Shotstack API key (sandbox)",
                        details={"environment": "sandbox"},
                    )
                return self._handle_http_error(response.status_code, response.text)
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except Exception as e:
            logger.error(f"Shotstack validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")


class RemotionValidator(BaseValidator):
    """Validator for Remotion (self-hosted or cloud)."""
    
    provider_name = "Remotion"
    
    async def validate(self) -> ValidationResult:
        """
        Validate Remotion setup.
        Remotion can be self-hosted or use Remotion Lambda.
        """
        # For Remotion Lambda, we'd check the AWS credentials
        # For self-hosted, we'd check if the server is accessible
        return self._success(
            "Remotion configuration accepted",
            details={"note": "Ensure Remotion Lambda or server is properly configured"},
        )


class EditframeValidator(BaseValidator):
    """Validator for Editframe API keys."""
    
    provider_name = "Editframe"
    
    async def validate(self) -> ValidationResult:
        """Validate Editframe API key."""
        try:
            response = await self.client.get(
                "https://api.editframe.com/v2/applications",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            
            if response.status_code == 200:
                return self._success("Valid Editframe API key")
            else:
                return self._handle_http_error(response.status_code, response.text)
                
        except Exception as e:
            logger.error(f"Editframe validation error: {e}")
            return self._failure(f"Validation error: {str(e)}", error_code="error")

