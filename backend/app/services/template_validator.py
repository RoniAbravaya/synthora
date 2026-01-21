"""
Template Validator

Validates template configuration data before saving.
Ensures all required fields are present and values are within acceptable ranges.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from app.models.template import (
    TemplateCategory,
    AspectRatio,
    HookStyle,
    NarrativeStructure,
    Pacing,
    VisualAesthetic,
    VoiceTone,
    MusicMood,
    CTAType,
)

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
    MIN_SCENES = 1
    MAX_SCENES = 20
    MIN_DURATION = 5
    MAX_DURATION = 600  # 10 minutes
    MAX_TAGS = 20
    MAX_TAG_LENGTH = 50
    MAX_HASHTAGS = 30
    MAX_PROMPT_LENGTH = 5000
    
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
        self._validate_target_platforms(data.get("target_platforms"))
        
        # Video structure
        video_structure = data.get("video_structure", {})
        self._validate_video_structure(video_structure)
        
        # Visual style
        visual_style = data.get("visual_style", {})
        self._validate_visual_style(visual_style)
        
        # Text/Captions
        text_captions = data.get("text_captions", {})
        self._validate_text_captions(text_captions)
        
        # Audio
        audio = data.get("audio", {})
        self._validate_audio(audio)
        
        # Script/Prompt
        script_prompt = data.get("script_prompt", {})
        self._validate_script_prompt(script_prompt)
        
        # Platform optimization
        platform_opt = data.get("platform_optimization", {})
        self._validate_platform_optimization(platform_opt)
        
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
        
        try:
            TemplateCategory(category)
        except ValueError:
            valid_values = [c.value for c in TemplateCategory]
            self._add_error("category", f"Invalid category. Must be one of: {valid_values}", category)
    
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
    
    def _validate_target_platforms(self, platforms: Optional[List[str]]) -> None:
        """Validate target platforms."""
        if platforms is None:
            return
        
        valid_platforms = {"youtube", "tiktok", "instagram", "facebook"}
        
        if not isinstance(platforms, list):
            self._add_error("target_platforms", "Target platforms must be a list")
            return
        
        for platform in platforms:
            if platform.lower() not in valid_platforms:
                self._add_error(
                    "target_platforms",
                    f"Invalid platform: {platform}. Must be one of: {valid_platforms}",
                )
    
    def _validate_video_structure(self, config: Dict[str, Any]) -> None:
        """Validate video structure configuration."""
        if not config:
            return
        
        # Hook style
        if "hook_style" in config:
            self._validate_enum("hook_style", config["hook_style"], HookStyle)
        
        # Narrative structure
        if "narrative_structure" in config:
            self._validate_enum("narrative_structure", config["narrative_structure"], NarrativeStructure)
        
        # Number of scenes
        if "num_scenes" in config:
            num_scenes = config["num_scenes"]
            if not isinstance(num_scenes, int):
                self._add_error("num_scenes", "Number of scenes must be an integer")
            elif num_scenes < self.MIN_SCENES or num_scenes > self.MAX_SCENES:
                self._add_error(
                    "num_scenes",
                    f"Number of scenes must be between {self.MIN_SCENES} and {self.MAX_SCENES}",
                    num_scenes,
                )
        
        # Duration range
        if "duration_range" in config:
            duration = config["duration_range"]
            if isinstance(duration, dict):
                min_dur = duration.get("min", 0)
                max_dur = duration.get("max", 0)
                
                if min_dur < self.MIN_DURATION:
                    self._add_error("duration_range.min", f"Minimum duration is {self.MIN_DURATION} seconds")
                if max_dur > self.MAX_DURATION:
                    self._add_error("duration_range.max", f"Maximum duration is {self.MAX_DURATION} seconds")
                if min_dur > max_dur:
                    self._add_error("duration_range", "Minimum duration cannot exceed maximum")
        
        # Pacing
        if "pacing" in config:
            self._validate_enum("pacing", config["pacing"], Pacing)
    
    def _validate_visual_style(self, config: Dict[str, Any]) -> None:
        """Validate visual style configuration."""
        if not config:
            return
        
        # Aspect ratio
        if "aspect_ratio" in config:
            self._validate_enum("aspect_ratio", config["aspect_ratio"], AspectRatio)
        
        # Visual aesthetic
        if "visual_aesthetic" in config:
            self._validate_enum("visual_aesthetic", config["visual_aesthetic"], VisualAesthetic)
        
        # Color palette
        if "color_palette" in config:
            palette = config["color_palette"]
            if not isinstance(palette, dict):
                self._add_error("color_palette", "Color palette must be an object")
    
    def _validate_text_captions(self, config: Dict[str, Any]) -> None:
        """Validate text/captions configuration."""
        if not config:
            return
        
        # Caption style
        valid_caption_styles = ["bold_popup", "subtitle", "minimal", "animated"]
        if "caption_style" in config and config["caption_style"] not in valid_caption_styles:
            self._add_error(
                "caption_style",
                f"Invalid caption style. Must be one of: {valid_caption_styles}",
            )
        
        # Text position
        valid_positions = ["top", "center", "bottom"]
        if "text_position" in config and config["text_position"] not in valid_positions:
            self._add_error(
                "text_position",
                f"Invalid text position. Must be one of: {valid_positions}",
            )
    
    def _validate_audio(self, config: Dict[str, Any]) -> None:
        """Validate audio configuration."""
        if not config:
            return
        
        # Voice tone
        if "voice_tone" in config:
            self._validate_enum("voice_tone", config["voice_tone"], VoiceTone)
        
        # Music mood
        if "music_mood" in config:
            self._validate_enum("music_mood", config["music_mood"], MusicMood)
        
        # Voice gender
        valid_genders = ["male", "female", "neutral"]
        if "voice_gender" in config and config["voice_gender"] not in valid_genders:
            self._add_error(
                "voice_gender",
                f"Invalid voice gender. Must be one of: {valid_genders}",
            )
        
        # Voice speed
        valid_speeds = ["slow", "normal", "fast"]
        if "voice_speed" in config and config["voice_speed"] not in valid_speeds:
            self._add_error(
                "voice_speed",
                f"Invalid voice speed. Must be one of: {valid_speeds}",
            )
    
    def _validate_script_prompt(self, config: Dict[str, Any]) -> None:
        """Validate script/prompt configuration."""
        if not config:
            return
        
        # Structure prompt
        if "structure_prompt" in config:
            prompt = config["structure_prompt"]
            if prompt and len(prompt) > self.MAX_PROMPT_LENGTH:
                self._add_error(
                    "structure_prompt",
                    f"Prompt must be at most {self.MAX_PROMPT_LENGTH} characters",
                )
        
        # Tone instructions
        if "tone_instructions" in config:
            instructions = config["tone_instructions"]
            if instructions and len(instructions) > self.MAX_PROMPT_LENGTH:
                self._add_error(
                    "tone_instructions",
                    f"Tone instructions must be at most {self.MAX_PROMPT_LENGTH} characters",
                )
        
        # CTA type
        if "cta_type" in config:
            self._validate_enum("cta_type", config["cta_type"], CTAType)
        
        # CTA placement
        valid_placements = ["end", "mid_end", "throughout"]
        if "cta_placement" in config and config["cta_placement"] not in valid_placements:
            self._add_error(
                "cta_placement",
                f"Invalid CTA placement. Must be one of: {valid_placements}",
            )
    
    def _validate_platform_optimization(self, config: Dict[str, Any]) -> None:
        """Validate platform optimization configuration."""
        if not config:
            return
        
        # Suggested hashtags
        if "suggested_hashtags" in config:
            hashtags = config["suggested_hashtags"]
            if not isinstance(hashtags, list):
                self._add_error("suggested_hashtags", "Hashtags must be a list")
            elif len(hashtags) > self.MAX_HASHTAGS:
                self._add_error(
                    "suggested_hashtags",
                    f"Maximum {self.MAX_HASHTAGS} hashtags allowed",
                )
    
    def _validate_enum(self, field: str, value: Any, enum_class: type) -> None:
        """Validate an enum value."""
        if value is None:
            return
        
        try:
            enum_class(value)
        except ValueError:
            valid_values = [e.value for e in enum_class]
            self._add_error(field, f"Invalid value. Must be one of: {valid_values}", value)


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

