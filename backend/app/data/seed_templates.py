"""
Seed Templates

Contains the 5 default system templates for Synthora.
These templates are created during initial setup and provide
users with ready-to-use configurations for common video types.
"""

import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.template import (
    Template,
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


# =============================================================================
# System Template Definitions
# =============================================================================

SYSTEM_TEMPLATES: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. Viral Hook - Short attention-grabbing format
    # -------------------------------------------------------------------------
    {
        "name": "Viral Hook",
        "description": "Short, punchy videos designed to grab attention in the first 3 seconds. Perfect for TikTok and Instagram Reels. Uses bold statements and surprising facts to stop the scroll.",
        "category": TemplateCategory.ENTERTAINMENT,
        "target_platforms": ["tiktok", "instagram", "youtube"],
        "tags": ["viral", "short-form", "hook", "attention-grabbing", "trending"],
        
        # Video Structure
        "hook_style": HookStyle.BOLD_STATEMENT,
        "narrative_structure": NarrativeStructure.HOOK_STORY_PAYOFF,
        "num_scenes": 4,
        "duration_min": 15,
        "duration_max": 30,
        "pacing": Pacing.FAST,
        
        # Visual Style
        "aspect_ratio": AspectRatio.VERTICAL,
        "color_palette": {
            "primary": "#FF0050",
            "secondary": "#00F2EA",
            "accent": "#FFFFFF",
            "background": "#000000",
        },
        "visual_aesthetic": VisualAesthetic.BOLD_VIBRANT,
        "transitions": "zoom",
        "filter_mood": "high_contrast",
        
        # Text & Captions
        "caption_style": "bold_popup",
        "font_style": "impact",
        "text_position": "center",
        "hook_text_overlay": True,
        
        # Audio
        "voice_gender": "neutral",
        "voice_tone": VoiceTone.ENERGETIC,
        "voice_speed": "fast",
        "music_mood": MusicMood.TRENDY,
        "sound_effects": True,
        
        # Script/Prompt
        "script_structure_prompt": """Create a viral short-form video script about {topic}.

Structure:
1. HOOK (0-3 seconds): Start with a bold, surprising statement or question that stops the scroll
2. BUILD (3-15 seconds): Deliver the main content with quick cuts and visual interest
3. PAYOFF (15-25 seconds): Reveal the answer/conclusion with impact
4. CTA (last 5 seconds): Quick call to action

Style: Punchy, conversational, use power words. Each sentence should be quotable.""",
        "tone_instructions": "Be bold and confident. Use short, impactful sentences. Create FOMO. Make viewers want to share.",
        "cta_type": CTAType.FOLLOW,
        "cta_placement": "end",
        
        # Platform Optimization
        "thumbnail_style": "text_overlay",
        "suggested_hashtags": ["viral", "fyp", "trending", "mustwatch"],
    },
    
    # -------------------------------------------------------------------------
    # 2. Educational Explainer - Tutorial/how-to format
    # -------------------------------------------------------------------------
    {
        "name": "Educational Explainer",
        "description": "Clear, informative videos that teach concepts or skills. Uses a problem-solution structure with step-by-step explanations. Great for building authority and providing value.",
        "category": TemplateCategory.EDUCATIONAL,
        "target_platforms": ["youtube", "tiktok", "instagram"],
        "tags": ["educational", "tutorial", "how-to", "learn", "explainer"],
        
        # Video Structure
        "hook_style": HookStyle.QUESTION,
        "narrative_structure": NarrativeStructure.HOOK_PROBLEM_SOLUTION_CTA,
        "num_scenes": 6,
        "duration_min": 30,
        "duration_max": 90,
        "pacing": Pacing.MEDIUM,
        
        # Visual Style
        "aspect_ratio": AspectRatio.VERTICAL,
        "color_palette": {
            "primary": "#4A90D9",
            "secondary": "#50E3C2",
            "accent": "#F5A623",
            "background": "#1A1A2E",
        },
        "visual_aesthetic": VisualAesthetic.MINIMALIST,
        "transitions": "slide",
        "filter_mood": "clean",
        
        # Text & Captions
        "caption_style": "subtitle",
        "font_style": "modern",
        "text_position": "bottom",
        "hook_text_overlay": True,
        
        # Audio
        "voice_gender": "neutral",
        "voice_tone": VoiceTone.PROFESSIONAL,
        "voice_speed": "normal",
        "music_mood": MusicMood.CALM,
        "sound_effects": False,
        
        # Script/Prompt
        "script_structure_prompt": """Create an educational video script about {topic}.

Structure:
1. HOOK (0-5 seconds): Ask a relatable question or state a common problem
2. PROBLEM (5-15 seconds): Explain why this matters and what people struggle with
3. SOLUTION (15-60 seconds): Break down the solution into 3-5 clear steps
4. RECAP (60-80 seconds): Summarize the key takeaways
5. CTA (last 10 seconds): Encourage engagement and following for more tips

Style: Clear, helpful, authoritative but approachable. Use analogies to explain complex concepts.""",
        "tone_instructions": "Be helpful and encouraging. Explain like you're teaching a friend. Use 'you' language. Anticipate questions.",
        "cta_type": CTAType.SUBSCRIBE,
        "cta_placement": "end",
        
        # Platform Optimization
        "thumbnail_style": "title_overlay",
        "suggested_hashtags": ["learn", "education", "howto", "tips", "tutorial"],
    },
    
    # -------------------------------------------------------------------------
    # 3. Product Showcase - Product demo format
    # -------------------------------------------------------------------------
    {
        "name": "Product Showcase",
        "description": "Compelling product demonstrations that highlight features and benefits. Uses visual storytelling to show the product in action. Perfect for e-commerce and brand content.",
        "category": TemplateCategory.PRODUCT,
        "target_platforms": ["instagram", "tiktok", "facebook", "youtube"],
        "tags": ["product", "showcase", "demo", "review", "unboxing"],
        
        # Video Structure
        "hook_style": HookStyle.VISUAL_SHOCK,
        "narrative_structure": NarrativeStructure.HOOK_DEMO_CTA,
        "num_scenes": 5,
        "duration_min": 20,
        "duration_max": 60,
        "pacing": Pacing.MEDIUM,
        
        # Visual Style
        "aspect_ratio": AspectRatio.VERTICAL,
        "color_palette": {
            "primary": "#FFFFFF",
            "secondary": "#F0F0F0",
            "accent": "#FF6B6B",
            "background": "#FAFAFA",
        },
        "visual_aesthetic": VisualAesthetic.CINEMATIC,
        "transitions": "fade",
        "filter_mood": "warm",
        
        # Text & Captions
        "caption_style": "minimal",
        "font_style": "elegant",
        "text_position": "bottom",
        "hook_text_overlay": False,
        
        # Audio
        "voice_gender": "female",
        "voice_tone": VoiceTone.CASUAL,
        "voice_speed": "normal",
        "music_mood": MusicMood.UPBEAT,
        "sound_effects": True,
        
        # Script/Prompt
        "script_structure_prompt": """Create a product showcase video script for {topic}.

Structure:
1. HOOK (0-5 seconds): Show the product in its best light with a wow moment
2. PROBLEM (5-15 seconds): What problem does this product solve?
3. DEMO (15-45 seconds): Show the product in action, highlight 3 key features
4. SOCIAL PROOF (45-55 seconds): Include testimonial or results (if available)
5. CTA (last 5 seconds): Where to get it, special offer

Style: Aspirational but authentic. Show real use cases. Focus on benefits over features.""",
        "tone_instructions": "Be enthusiastic but genuine. Focus on how the product improves life. Use sensory language.",
        "cta_type": CTAType.CLICK_LINK,
        "cta_placement": "end",
        
        # Platform Optimization
        "thumbnail_style": "product_focus",
        "suggested_hashtags": ["newproduct", "musthave", "review", "unboxing"],
    },
    
    # -------------------------------------------------------------------------
    # 4. Storytelling - Narrative-driven format
    # -------------------------------------------------------------------------
    {
        "name": "Storytelling",
        "description": "Emotionally engaging narrative videos that connect with viewers through story. Uses classic storytelling structure to build connection and drive engagement.",
        "category": TemplateCategory.ENTERTAINMENT,
        "target_platforms": ["youtube", "tiktok", "instagram", "facebook"],
        "tags": ["story", "narrative", "emotional", "journey", "personal"],
        
        # Video Structure
        "hook_style": HookStyle.STORY_OPENER,
        "narrative_structure": NarrativeStructure.HOOK_STORY_PAYOFF,
        "num_scenes": 7,
        "duration_min": 45,
        "duration_max": 120,
        "pacing": Pacing.MEDIUM,
        
        # Visual Style
        "aspect_ratio": AspectRatio.VERTICAL,
        "color_palette": {
            "primary": "#2C3E50",
            "secondary": "#E74C3C",
            "accent": "#F39C12",
            "background": "#ECF0F1",
        },
        "visual_aesthetic": VisualAesthetic.CINEMATIC,
        "transitions": "cut",
        "filter_mood": "cinematic",
        
        # Text & Captions
        "caption_style": "subtitle",
        "font_style": "classic",
        "text_position": "bottom",
        "hook_text_overlay": True,
        
        # Audio
        "voice_gender": "neutral",
        "voice_tone": VoiceTone.DRAMATIC,
        "voice_speed": "normal",
        "music_mood": MusicMood.DRAMATIC,
        "sound_effects": True,
        
        # Script/Prompt
        "script_structure_prompt": """Create a storytelling video script about {topic}.

Structure:
1. HOOK (0-10 seconds): Start in the middle of the action or with an intriguing statement
2. SETUP (10-25 seconds): Introduce the character/situation and what's at stake
3. CONFLICT (25-60 seconds): Present the challenge or turning point
4. RESOLUTION (60-100 seconds): Show the transformation or outcome
5. LESSON (100-115 seconds): What can viewers learn from this?
6. CTA (last 5 seconds): Invite viewers to share their story

Style: Emotional, relatable, use vivid details. Create tension and release.""",
        "tone_instructions": "Be authentic and vulnerable. Use descriptive language. Build emotional connection. Make it personal.",
        "cta_type": CTAType.COMMENT,
        "cta_placement": "end",
        
        # Platform Optimization
        "thumbnail_style": "emotion_capture",
        "suggested_hashtags": ["story", "journey", "motivation", "inspiration"],
    },
    
    # -------------------------------------------------------------------------
    # 5. Trending Challenge - Social media trend format
    # -------------------------------------------------------------------------
    {
        "name": "Trending Challenge",
        "description": "Videos designed to participate in or start viral trends. Optimized for discoverability and shareability. Uses trending sounds and formats.",
        "category": TemplateCategory.ENTERTAINMENT,
        "target_platforms": ["tiktok", "instagram", "youtube"],
        "tags": ["trend", "challenge", "viral", "fun", "creative"],
        
        # Video Structure
        "hook_style": HookStyle.SURPRISING_FACT,
        "narrative_structure": NarrativeStructure.HOOK_LIST_CTA,
        "num_scenes": 3,
        "duration_min": 10,
        "duration_max": 30,
        "pacing": Pacing.FAST,
        
        # Visual Style
        "aspect_ratio": AspectRatio.VERTICAL,
        "color_palette": {
            "primary": "#FF00FF",
            "secondary": "#00FFFF",
            "accent": "#FFFF00",
            "background": "#000000",
        },
        "visual_aesthetic": VisualAesthetic.BOLD_VIBRANT,
        "transitions": "zoom",
        "filter_mood": "vibrant",
        
        # Text & Captions
        "caption_style": "animated",
        "font_style": "bold",
        "text_position": "center",
        "hook_text_overlay": True,
        
        # Audio
        "voice_gender": "neutral",
        "voice_tone": VoiceTone.ENERGETIC,
        "voice_speed": "fast",
        "music_mood": MusicMood.TRENDY,
        "sound_effects": True,
        
        # Script/Prompt
        "script_structure_prompt": """Create a trending challenge video script about {topic}.

Structure:
1. HOOK (0-3 seconds): Immediately grab attention with the trend format
2. CONTENT (3-20 seconds): Execute the challenge/trend with your unique spin
3. SURPRISE (20-25 seconds): Add an unexpected twist or result
4. CTA (last 5 seconds): Challenge viewers to try it

Style: Fun, energetic, shareable. Add your unique personality. Make it easy to replicate.""",
        "tone_instructions": "Be playful and fun. Don't take yourself too seriously. Encourage participation. Be relatable.",
        "cta_type": CTAType.SHARE,
        "cta_placement": "end",
        
        # Platform Optimization
        "thumbnail_style": "action_shot",
        "suggested_hashtags": ["challenge", "trend", "viral", "fyp", "foryou"],
    },
]


# =============================================================================
# Seed Functions
# =============================================================================

def seed_system_templates(db: Session) -> List[Template]:
    """
    Create all system templates in the database.
    
    This function is idempotent - it will skip templates that already exist.
    
    Args:
        db: Database session
        
    Returns:
        List of created Template instances
    """
    created_templates = []
    
    for template_data in SYSTEM_TEMPLATES:
        # Check if template already exists
        existing = db.query(Template).filter(
            Template.name == template_data["name"],
            Template.is_system == True,
        ).first()
        
        if existing:
            logger.info(f"System template '{template_data['name']}' already exists, skipping")
            continue
        
        # Create the template
        template = Template(
            user_id=None,  # System templates have no owner
            is_system=True,
            is_public=True,  # System templates are always public
            **template_data,
        )
        
        db.add(template)
        created_templates.append(template)
        logger.info(f"Created system template: {template_data['name']}")
    
    if created_templates:
        db.commit()
        for template in created_templates:
            db.refresh(template)
    
    logger.info(f"Seeded {len(created_templates)} system templates")
    return created_templates


def get_system_template_names() -> List[str]:
    """Get the names of all system templates."""
    return [t["name"] for t in SYSTEM_TEMPLATES]


def get_system_template_by_name(name: str) -> Dict[str, Any]:
    """
    Get a system template definition by name.
    
    Args:
        name: Template name
        
    Returns:
        Template definition dictionary
        
    Raises:
        ValueError: If template not found
    """
    for template in SYSTEM_TEMPLATES:
        if template["name"] == name:
            return template
    
    raise ValueError(f"System template '{name}' not found")

