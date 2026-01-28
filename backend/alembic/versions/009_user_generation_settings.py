"""User generation settings table

Revision ID: 009_user_generation_settings
Revises: 008_modular_integrations
Create Date: 2026-01-28

This migration creates the user_generation_settings table for storing:
- Default provider selections for each video generation category
- Subtitle style preferences
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_user_generation_settings'
down_revision = '008_modular_integrations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # User Generation Settings Table
    # ==========================================================================
    op.create_table(
        'user_generation_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id', 
            postgresql.UUID(as_uuid=True), 
            sa.ForeignKey('users.id', ondelete='CASCADE'), 
            nullable=False, 
            unique=True
        ),
        
        # Default providers for each category
        sa.Column('default_script_provider', sa.String(50), nullable=True,
                  comment='Default provider for script generation (e.g., openai_gpt, anthropic)'),
        sa.Column('default_voice_provider', sa.String(50), nullable=True,
                  comment='Default provider for voice generation (e.g., elevenlabs, openai_tts)'),
        sa.Column('default_media_provider', sa.String(50), nullable=True,
                  comment='Default provider for stock media (e.g., pexels, unsplash)'),
        sa.Column('default_video_ai_provider', sa.String(50), nullable=True,
                  comment='Default provider for AI video generation (e.g., openai_sora, runway)'),
        sa.Column('default_assembly_provider', sa.String(50), nullable=True,
                  comment='Default provider for video assembly (e.g., ffmpeg, creatomate)'),
        
        # Subtitle settings
        sa.Column(
            'subtitle_style', 
            sa.String(20), 
            nullable=False,
            server_default='modern',
            comment='Subtitle style preset: classic, modern, bold, minimal'
        ),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index on user_id for fast lookups
    op.create_index(
        'ix_user_generation_settings_user_id', 
        'user_generation_settings', 
        ['user_id']
    )


def downgrade() -> None:
    op.drop_index('ix_user_generation_settings_user_id', table_name='user_generation_settings')
    op.drop_table('user_generation_settings')
