"""Seed default templates

Revision ID: 002_seed_templates
Revises: 001_initial
Create Date: 2026-01-21

This migration seeds the default system templates.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002_seed_templates'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Seed default templates."""
    templates_table = sa.table(
        'templates',
        sa.column('id', postgresql.UUID),
        sa.column('user_id', postgresql.UUID),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('category', sa.String),
        sa.column('is_public', sa.Boolean),
        sa.column('is_premium', sa.Boolean),
        sa.column('is_featured', sa.Boolean),
        sa.column('thumbnail_url', sa.String),
        sa.column('preview_url', sa.String),
        sa.column('config', postgresql.JSONB),
        sa.column('tags', postgresql.ARRAY(sa.String)),
        sa.column('use_count', sa.Integer),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    
    now = datetime.utcnow()
    
    templates = [
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Viral Hook',
            'description': 'Short, punchy videos designed to grab attention in the first 3 seconds. Perfect for TikTok and Instagram Reels. Uses bold statements and surprising facts to stop the scroll.',
            'category': 'entertainment',
            'is_public': True,
            'is_premium': False,
            'is_featured': True,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'bold_statement',
                'narrative_structure': 'hook_story_payoff',
                'num_scenes': 4,
                'duration_min': 15,
                'duration_max': 30,
                'pacing': 'fast',
                'aspect_ratio': '9:16',
                'voice_tone': 'energetic',
                'music_mood': 'trendy',
            },
            'tags': ['viral', 'short-form', 'hook', 'trending', 'tiktok'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Educational Explainer',
            'description': 'Clear, informative videos that teach concepts or skills. Uses a problem-solution structure with step-by-step explanations. Great for building authority.',
            'category': 'educational',
            'is_public': True,
            'is_premium': False,
            'is_featured': True,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'question',
                'narrative_structure': 'problem_solution',
                'num_scenes': 6,
                'duration_min': 30,
                'duration_max': 90,
                'pacing': 'medium',
                'aspect_ratio': '9:16',
                'voice_tone': 'professional',
                'music_mood': 'calm',
            },
            'tags': ['educational', 'tutorial', 'how-to', 'learn', 'tips'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Product Showcase',
            'description': 'Compelling product demonstrations that highlight features and benefits. Uses visual storytelling to show the product in action. Perfect for e-commerce.',
            'category': 'product',
            'is_public': True,
            'is_premium': False,
            'is_featured': True,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'visual_shock',
                'narrative_structure': 'demo_cta',
                'num_scenes': 5,
                'duration_min': 20,
                'duration_max': 60,
                'pacing': 'medium',
                'aspect_ratio': '9:16',
                'voice_tone': 'casual',
                'music_mood': 'upbeat',
            },
            'tags': ['product', 'showcase', 'demo', 'review', 'ecommerce'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Storytelling',
            'description': 'Emotionally engaging narrative videos that connect with viewers through story. Uses classic storytelling structure to build connection.',
            'category': 'entertainment',
            'is_public': True,
            'is_premium': False,
            'is_featured': False,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'story_opener',
                'narrative_structure': 'hook_story_payoff',
                'num_scenes': 7,
                'duration_min': 45,
                'duration_max': 120,
                'pacing': 'medium',
                'aspect_ratio': '9:16',
                'voice_tone': 'dramatic',
                'music_mood': 'dramatic',
            },
            'tags': ['story', 'narrative', 'emotional', 'journey', 'personal'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Trending Challenge',
            'description': 'Videos designed to participate in or start viral trends. Optimized for discoverability and shareability. Uses trending sounds and formats.',
            'category': 'entertainment',
            'is_public': True,
            'is_premium': False,
            'is_featured': False,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'surprising_fact',
                'narrative_structure': 'hook_list_cta',
                'num_scenes': 3,
                'duration_min': 10,
                'duration_max': 30,
                'pacing': 'fast',
                'aspect_ratio': '9:16',
                'voice_tone': 'energetic',
                'music_mood': 'trendy',
            },
            'tags': ['trend', 'challenge', 'viral', 'fun', 'creative'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Listicle',
            'description': 'Engaging list-format videos like "Top 5" or "3 Things You Didn\'t Know". Easy to follow and highly shareable content format.',
            'category': 'educational',
            'is_public': True,
            'is_premium': False,
            'is_featured': True,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'bold_statement',
                'narrative_structure': 'hook_list_cta',
                'num_scenes': 5,
                'duration_min': 30,
                'duration_max': 60,
                'pacing': 'medium',
                'aspect_ratio': '9:16',
                'voice_tone': 'professional',
                'music_mood': 'upbeat',
            },
            'tags': ['list', 'top', 'tips', 'facts', 'countdown'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': str(uuid.uuid4()),
            'user_id': None,
            'name': 'Behind The Scenes',
            'description': 'Authentic behind-the-scenes content that builds connection and trust with your audience. Shows the real you or your brand.',
            'category': 'lifestyle',
            'is_public': True,
            'is_premium': True,
            'is_featured': False,
            'thumbnail_url': None,
            'preview_url': None,
            'config': {
                'hook_style': 'story_opener',
                'narrative_structure': 'hook_story_payoff',
                'num_scenes': 5,
                'duration_min': 30,
                'duration_max': 90,
                'pacing': 'slow',
                'aspect_ratio': '9:16',
                'voice_tone': 'casual',
                'music_mood': 'calm',
            },
            'tags': ['bts', 'authentic', 'personal', 'brand', 'day-in-life'],
            'use_count': 0,
            'created_at': now,
            'updated_at': now,
        },
    ]
    
    op.bulk_insert(templates_table, templates)


def downgrade() -> None:
    """Remove seeded templates."""
    op.execute("DELETE FROM templates WHERE user_id IS NULL")
