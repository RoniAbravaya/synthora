"""
Template Model

Represents a video generation template with all configuration parameters.
Templates can be system-wide (created by admins) or personal (created by users).
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.video import Video


class TemplateCategory(str, enum.Enum):
    """Template content categories."""
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    PRODUCT = "product"
    MOTIVATIONAL = "motivational"
    NEWS = "news"
    HOWTO = "howto"
    GENERAL = "general"


class AspectRatio(str, enum.Enum):
    """Video aspect ratios."""
    VERTICAL = "9:16"      # TikTok, Reels, Shorts
    HORIZONTAL = "16:9"    # YouTube, Facebook
    SQUARE = "1:1"         # Instagram Feed


class HookStyle(str, enum.Enum):
    """Video hook styles for grabbing attention."""
    QUESTION = "question"
    BOLD_STATEMENT = "bold_statement"
    SURPRISING_FACT = "surprising_fact"
    VISUAL_SHOCK = "visual_shock"
    STORY_OPENER = "story_opener"


class NarrativeStructure(str, enum.Enum):
    """Video narrative structures."""
    HOOK_PROBLEM_SOLUTION_CTA = "hook_problem_solution_cta"
    HOOK_STORY_PAYOFF = "hook_story_payoff"
    HOOK_LIST_CTA = "hook_list_cta"
    HOOK_DEMO_CTA = "hook_demo_cta"
    HOOK_TIPS_CTA = "hook_tips_cta"


class Pacing(str, enum.Enum):
    """Video pacing styles."""
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class VisualAesthetic(str, enum.Enum):
    """Visual aesthetic styles."""
    REALISTIC = "realistic"
    CINEMATIC = "cinematic"
    ANIMATED = "animated"
    MINIMALIST = "minimalist"
    BOLD_VIBRANT = "bold_vibrant"


class VoiceTone(str, enum.Enum):
    """Voice-over tone styles."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENERGETIC = "energetic"
    CALM = "calm"
    DRAMATIC = "dramatic"


class MusicMood(str, enum.Enum):
    """Background music mood."""
    UPBEAT = "upbeat"
    CALM = "calm"
    DRAMATIC = "dramatic"
    INSPIRATIONAL = "inspirational"
    TRENDY = "trendy"
    NONE = "none"


class CTAType(str, enum.Enum):
    """Call-to-action types."""
    SUBSCRIBE = "subscribe"
    FOLLOW = "follow"
    CLICK_LINK = "click_link"
    COMMENT = "comment"
    SHARE = "share"
    CUSTOM = "custom"


class Template(Base, UUIDMixin, TimestampMixin):
    """
    Template model for video generation configurations.
    
    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to user (null for system templates)
        name: Template name
        description: Template description
        category: Content category
        target_platforms: Target social media platforms
        tags: Searchable tags
        
        # Video Structure
        hook_style: How to grab attention
        narrative_structure: Story flow structure
        num_scenes: Number of scenes
        duration_min: Minimum duration in seconds
        duration_max: Maximum duration in seconds
        pacing: Video pacing style
        
        # Visual Style
        aspect_ratio: Video aspect ratio
        color_palette: Color scheme (JSON)
        visual_aesthetic: Visual style
        transitions: Transition type
        filter_mood: Color filter/mood
        
        # Text & Captions
        caption_style: Caption display style
        font_style: Font style
        text_position: Text overlay position
        hook_text_overlay: Show text hook at start
        
        # Audio
        voice_gender: Voice-over gender
        voice_tone: Voice-over tone
        voice_speed: Voice-over speed
        music_mood: Background music mood
        sound_effects: Enable sound effects
        
        # Script/Prompt
        script_structure_prompt: Prompt template with placeholders
        tone_instructions: Writing style instructions
        cta_type: Call-to-action type
        cta_placement: Where to place CTA
        
        # Platform Optimization
        thumbnail_style: Thumbnail generation style
        suggested_hashtags: Default hashtags
        
        # Ownership
        is_system: Whether this is a system template
        is_public: Whether other users can see this template
        version: Template version number
        
    Relationships:
        user: The user who created this template (null for system)
        videos: Videos created using this template
    """
    
    __tablename__ = "templates"
    
    # Foreign Key (nullable for system templates)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Foreign key to user (null for system templates)"
    )
    
    # Basic Info
    name = Column(
        String(255),
        nullable=False,
        doc="Template name"
    )
    description = Column(
        Text,
        nullable=True,
        doc="Template description"
    )
    category = Column(
        Enum(TemplateCategory),
        default=TemplateCategory.GENERAL,
        nullable=False,
        index=True,
        doc="Content category"
    )
    target_platforms = Column(
        ARRAY(String),
        default=list,
        nullable=False,
        doc="Target social media platforms"
    )
    tags = Column(
        ARRAY(String),
        default=list,
        nullable=False,
        doc="Searchable tags"
    )
    
    # Video Structure
    hook_style = Column(
        Enum(HookStyle),
        default=HookStyle.QUESTION,
        nullable=False,
        doc="How to grab attention"
    )
    narrative_structure = Column(
        Enum(NarrativeStructure),
        default=NarrativeStructure.HOOK_PROBLEM_SOLUTION_CTA,
        nullable=False,
        doc="Story flow structure"
    )
    num_scenes = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Number of scenes"
    )
    duration_min = Column(
        Integer,
        default=15,
        nullable=False,
        doc="Minimum duration in seconds"
    )
    duration_max = Column(
        Integer,
        default=60,
        nullable=False,
        doc="Maximum duration in seconds"
    )
    pacing = Column(
        Enum(Pacing),
        default=Pacing.MEDIUM,
        nullable=False,
        doc="Video pacing style"
    )
    
    # Visual Style
    aspect_ratio = Column(
        Enum(AspectRatio),
        default=AspectRatio.VERTICAL,
        nullable=False,
        doc="Video aspect ratio"
    )
    color_palette = Column(
        JSONB,
        default=dict,
        nullable=False,
        doc="Color scheme (primary, secondary, accent)"
    )
    visual_aesthetic = Column(
        Enum(VisualAesthetic),
        default=VisualAesthetic.CINEMATIC,
        nullable=False,
        doc="Visual style"
    )
    transitions = Column(
        String(50),
        default="cut",
        nullable=False,
        doc="Transition type (cut, fade, slide, zoom)"
    )
    filter_mood = Column(
        String(50),
        default="neutral",
        nullable=False,
        doc="Color filter/mood"
    )
    
    # Text & Captions
    caption_style = Column(
        String(50),
        default="bold_popup",
        nullable=False,
        doc="Caption display style"
    )
    font_style = Column(
        String(50),
        default="modern",
        nullable=False,
        doc="Font style"
    )
    text_position = Column(
        String(50),
        default="bottom",
        nullable=False,
        doc="Text overlay position"
    )
    hook_text_overlay = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Show text hook at start"
    )
    
    # Audio
    voice_gender = Column(
        String(20),
        default="neutral",
        nullable=False,
        doc="Voice-over gender (male, female, neutral)"
    )
    voice_tone = Column(
        Enum(VoiceTone),
        default=VoiceTone.PROFESSIONAL,
        nullable=False,
        doc="Voice-over tone"
    )
    voice_speed = Column(
        String(20),
        default="normal",
        nullable=False,
        doc="Voice-over speed (slow, normal, fast)"
    )
    music_mood = Column(
        Enum(MusicMood),
        default=MusicMood.UPBEAT,
        nullable=False,
        doc="Background music mood"
    )
    sound_effects = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Enable sound effects"
    )
    
    # Script/Prompt
    script_structure_prompt = Column(
        Text,
        nullable=True,
        doc="Prompt template with placeholders"
    )
    tone_instructions = Column(
        Text,
        nullable=True,
        doc="Writing style instructions for AI"
    )
    cta_type = Column(
        Enum(CTAType),
        default=CTAType.FOLLOW,
        nullable=False,
        doc="Call-to-action type"
    )
    cta_placement = Column(
        String(20),
        default="end",
        nullable=False,
        doc="CTA placement (end, mid_end, throughout)"
    )
    
    # Platform Optimization
    thumbnail_style = Column(
        String(50),
        default="title_overlay",
        nullable=False,
        doc="Thumbnail generation style"
    )
    suggested_hashtags = Column(
        ARRAY(String),
        default=list,
        nullable=False,
        doc="Default hashtags"
    )
    
    # Ownership
    is_system = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether this is a system template"
    )
    is_public = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether other users can see this template"
    )
    version = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Template version number"
    )
    
    # Relationships
    user = relationship("User", back_populates="templates", foreign_keys=[user_id])
    videos = relationship("Video", back_populates="template")
    
    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name={self.name}, is_system={self.is_system})>"
    
    def increment_version(self) -> None:
        """Increment the template version."""
        self.version += 1
    
    def to_config_dict(self) -> Dict[str, Any]:
        """
        Export template configuration as a dictionary.
        Useful for passing to video generation pipeline.
        """
        return {
            "name": self.name,
            "category": self.category.value if self.category else None,
            "target_platforms": self.target_platforms,
            "video_structure": {
                "hook_style": self.hook_style.value if self.hook_style else None,
                "narrative_structure": self.narrative_structure.value if self.narrative_structure else None,
                "num_scenes": self.num_scenes,
                "duration_range": {"min": self.duration_min, "max": self.duration_max},
                "pacing": self.pacing.value if self.pacing else None,
            },
            "visual_style": {
                "aspect_ratio": self.aspect_ratio.value if self.aspect_ratio else None,
                "color_palette": self.color_palette,
                "visual_aesthetic": self.visual_aesthetic.value if self.visual_aesthetic else None,
                "transitions": self.transitions,
                "filter_mood": self.filter_mood,
            },
            "text_captions": {
                "caption_style": self.caption_style,
                "font_style": self.font_style,
                "text_position": self.text_position,
                "hook_text_overlay": self.hook_text_overlay,
            },
            "audio": {
                "voice_gender": self.voice_gender,
                "voice_tone": self.voice_tone.value if self.voice_tone else None,
                "voice_speed": self.voice_speed,
                "music_mood": self.music_mood.value if self.music_mood else None,
                "sound_effects": self.sound_effects,
            },
            "script_prompt": {
                "structure_prompt": self.script_structure_prompt,
                "tone_instructions": self.tone_instructions,
                "cta_type": self.cta_type.value if self.cta_type else None,
                "cta_placement": self.cta_placement,
            },
            "platform_optimization": {
                "thumbnail_style": self.thumbnail_style,
                "suggested_hashtags": self.suggested_hashtags,
            },
        }

