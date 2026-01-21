"""
Seed Templates

Contains default system templates for Synthora.
Note: System templates are typically seeded via database migrations (002_seed_templates.py).
This module provides utilities for working with template definitions.
"""

import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.template import Template

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
        "category": "entertainment",
        "tags": ["viral", "short-form", "hook", "attention-grabbing", "trending"],
        "config": {
            "hook_style": "bold_statement",
            "narrative_structure": "hook_story_payoff",
            "num_scenes": 4,
            "duration_min": 15,
            "duration_max": 30,
            "pacing": "fast",
            "aspect_ratio": "9:16",
            "voice_tone": "energetic",
            "music_mood": "trendy",
        },
    },
    
    # -------------------------------------------------------------------------
    # 2. Educational Explainer - Tutorial/how-to format
    # -------------------------------------------------------------------------
    {
        "name": "Educational Explainer",
        "description": "Clear, informative videos that teach concepts or skills. Uses a problem-solution structure with step-by-step explanations. Great for building authority and providing value.",
        "category": "educational",
        "tags": ["educational", "tutorial", "how-to", "learn", "explainer"],
        "config": {
            "hook_style": "question",
            "narrative_structure": "problem_solution",
            "num_scenes": 6,
            "duration_min": 30,
            "duration_max": 90,
            "pacing": "medium",
            "aspect_ratio": "9:16",
            "voice_tone": "professional",
            "music_mood": "calm",
        },
    },
    
    # -------------------------------------------------------------------------
    # 3. Product Showcase - Product demo format
    # -------------------------------------------------------------------------
    {
        "name": "Product Showcase",
        "description": "Compelling product demonstrations that highlight features and benefits. Uses visual storytelling to show the product in action. Perfect for e-commerce and brand content.",
        "category": "product",
        "tags": ["product", "showcase", "demo", "review", "unboxing"],
        "config": {
            "hook_style": "visual_shock",
            "narrative_structure": "demo_cta",
            "num_scenes": 5,
            "duration_min": 20,
            "duration_max": 60,
            "pacing": "medium",
            "aspect_ratio": "9:16",
            "voice_tone": "casual",
            "music_mood": "upbeat",
        },
    },
    
    # -------------------------------------------------------------------------
    # 4. Storytelling - Narrative-driven format
    # -------------------------------------------------------------------------
    {
        "name": "Storytelling",
        "description": "Emotionally engaging narrative videos that connect with viewers through story. Uses classic storytelling structure to build connection and drive engagement.",
        "category": "entertainment",
        "tags": ["story", "narrative", "emotional", "journey", "personal"],
        "config": {
            "hook_style": "story_opener",
            "narrative_structure": "hook_story_payoff",
            "num_scenes": 7,
            "duration_min": 45,
            "duration_max": 120,
            "pacing": "medium",
            "aspect_ratio": "9:16",
            "voice_tone": "dramatic",
            "music_mood": "dramatic",
        },
    },
    
    # -------------------------------------------------------------------------
    # 5. Trending Challenge - Social media trend format
    # -------------------------------------------------------------------------
    {
        "name": "Trending Challenge",
        "description": "Videos designed to participate in or start viral trends. Optimized for discoverability and shareability. Uses trending sounds and formats.",
        "category": "entertainment",
        "tags": ["trend", "challenge", "viral", "fun", "creative"],
        "config": {
            "hook_style": "surprising_fact",
            "narrative_structure": "hook_list_cta",
            "num_scenes": 3,
            "duration_min": 10,
            "duration_max": 30,
            "pacing": "fast",
            "aspect_ratio": "9:16",
            "voice_tone": "energetic",
            "music_mood": "trendy",
        },
    },
]


# =============================================================================
# Seed Functions
# =============================================================================

def seed_system_templates(db: Session) -> List[Template]:
    """
    Create all system templates in the database.
    
    This function is idempotent - it will skip templates that already exist.
    Note: System templates are typically seeded via migrations, not this function.
    
    Args:
        db: Database session
        
    Returns:
        List of created Template instances
    """
    created_templates = []
    
    for template_data in SYSTEM_TEMPLATES:
        # Check if template already exists (system templates have user_id = NULL)
        existing = db.query(Template).filter(
            Template.name == template_data["name"],
            Template.user_id == None,
        ).first()
        
        if existing:
            logger.info(f"System template '{template_data['name']}' already exists, skipping")
            continue
        
        # Create the template
        template = Template(
            user_id=None,  # System templates have no owner
            name=template_data["name"],
            description=template_data["description"],
            category=template_data["category"],
            tags=template_data.get("tags", []),
            config=template_data.get("config", {}),
            is_public=True,  # System templates are always public
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
