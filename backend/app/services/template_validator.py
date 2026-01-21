"""
Template Validator

Validates template configuration data before saving.
Ensures all required fields are present and values are within acceptable ranges.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from app.models.template import TemplateCategory

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """Result of template validation."""
    valid: bool
    errors: List[ValidationError]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": [
                {"field": e.field, "message": e.message, "value": e.value}
                for e in self.errors
            ],
        }


class TemplateValidator:
    """
    Validates template configuration data.
    
    Checks:
    - Required fields are present
    - Enum values are valid
    - Numeric ranges are acceptable
    - String lengths are within limits
    """
    
    # Constraints
    MIN_NAME_LENGTH = 1
    MAX_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_TAGS = 20
    MAX_TAG_LENGTH = 50
    MAX_HASHTAGS = 30
    MAX_PROMPT_LENGTH = 5000
    
    # Valid values for string fields
    VALID_CATEGORIES = ["educational", "entertainment", "product", "motivational", "news", "howto", "lifestyle", "general"]
    VALID_PLATFORMS = ["youtube", "tiktok", "instagram", "facebook"]
    VALID_HOOK_STYLES = ["question", "bold_statement", "surprising_fact", "visual_shock", "story_opener"]
    VALID_PACING = ["fast", "medium", "slow"]
    VALID_VOICE_TONES = ["professional", "casual", "energetic", "calm", "dramatic"]
    VALID_MUSIC_MOODS = ["upbeat", "calm", "dramatic", "inspirational", "trendy", "none"]
    
    def __init__(self):
        """Initialize the validator."""
        self.errors: List[ValidationError] = []
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate template data.
        
        Args:
            data: Template data dictionary
            
        Returns:
            ValidationResult with validation status and errors
        """
        self.errors = []
        
        # Required fields
        self._validate_required("name", data.get("name"))
        
        # Basic info
        self._validate_name(data.get("name"))
        self._validate_description(data.get("description"))
        self._validate_category(data.get("category"))
        self._validate_tags(data.get("tags"))
        
        # Config validation (if present)
        config = data.get("config", {})
        if config:
            self._validate_config(config)
        
        return ValidationResult(
            valid=len(self.errors) == 0,
            errors=self.errors,
        )
    
    def _add_error(self, field: str, message: str, value: Any = None) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(field, message, value))
    
    def _validate_required(self, field: str, value: Any) -> bool:
        """Check if a required field is present."""
        if value is None or (isinstance(value, str) and not value.strip()):
            self._add_error(field, f"{field} is required")
            return False
        return True
    
    def _validate_name(self, name: Optional[str]) -> None:
        """Validate template name."""
        if name is None:
            return
        
        if len(name) < self.MIN_NAME_LENGTH:
            self._add_error("name", "Name is too short", name)
        elif len(name) > self.MAX_NAME_LENGTH:
            self._add_error("name", f"Name must be at most {self.MAX_NAME_LENGTH} characters", name)
    
    def _validate_description(self, description: Optional[str]) -> None:
        """Validate template description."""
        if description is None:
            return
        
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            self._add_error(
                "description",
                f"Description must be at most {self.MAX_DESCRIPTION_LENGTH} characters",
            )
    
    def _validate_category(self, category: Optional[str]) -> None:
        """Validate template category."""
        if category is None:
            return
        
        if category not in self.VALID_CATEGORIES:
            self._add_error("category", f"Invalid category. Must be one of: {self.VALID_CATEGORIES}", category)
    
    def _validate_tags(self, tags: Optional[List[str]]) -> None:
        """Validate template tags."""
        if tags is None:
            return
        
        if not isinstance(tags, list):
            self._add_error("tags", "Tags must be a list")
            return
        
        if len(tags) > self.MAX_TAGS:
            self._add_error("tags", f"Maximum {self.MAX_TAGS} tags allowed")
        
        for i, tag in enumerate(tags):
            if not isinstance(tag, str):
                self._add_error(f"tags[{i}]", "Tag must be a string")
            elif len(tag) > self.MAX_TAG_LENGTH:
                self._add_error(f"tags[{i}]", f"Tag must be at most {self.MAX_TAG_LENGTH} characters")
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate template config JSONB."""
        # Validate hook_style
        if "hook_style" in config and config["hook_style"] not in self.VALID_HOOK_STYLES:
            self._add_error("config.hook_style", f"Invalid hook_style. Must be one of: {self.VALID_HOOK_STYLES}")
        
        # Validate pacing
        if "pacing" in config and config["pacing"] not in self.VALID_PACING:
            self._add_error("config.pacing", f"Invalid pacing. Must be one of: {self.VALID_PACING}")
        
        # Validate voice_tone
        if "voice_tone" in config and config["voice_tone"] not in self.VALID_VOICE_TONES:
            self._add_error("config.voice_tone", f"Invalid voice_tone. Must be one of: {self.VALID_VOICE_TONES}")
        
        # Validate music_mood
        if "music_mood" in config and config["music_mood"] not in self.VALID_MUSIC_MOODS:
            self._add_error("config.music_mood", f"Invalid music_mood. Must be one of: {self.VALID_MUSIC_MOODS}")
        
        # Validate duration
        if "duration_min" in config:
            if not isinstance(config["duration_min"], int) or config["duration_min"] < 5:
                self._add_error("config.duration_min", "duration_min must be at least 5 seconds")
        
        if "duration_max" in config:
            if not isinstance(config["duration_max"], int) or config["duration_max"] > 600:
                self._add_error("config.duration_max", "duration_max must be at most 600 seconds")


def validate_template_config(data: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate template configuration.
    
    Args:
        data: Template data dictionary
        
    Returns:
        ValidationResult with validation status and errors
    """
    validator = TemplateValidator()
    return validator.validate(data)
