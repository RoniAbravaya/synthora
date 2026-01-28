"""Update videos table for modular generation

Revision ID: 011_update_videos_table
Revises: 010_api_request_logs
Create Date: 2026-01-28

This migration adds new columns to the videos table:
- subtitle_file_url: URL to generated subtitle file
- generation_started_at: When generation actually started
- last_step_updated_at: Last time a step was updated (for stuck detection)
- selected_providers: Providers selected for this specific video
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_update_videos_table'
down_revision = '010_api_request_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Add new columns to videos table
    # ==========================================================================
    
    # Subtitle file URL
    op.add_column(
        'videos',
        sa.Column(
            'subtitle_file_url', 
            sa.Text(), 
            nullable=True,
            comment='URL to generated subtitle file (SRT/ASS) in cloud storage'
        )
    )
    
    # Generation timing columns for tracking and stuck detection
    op.add_column(
        'videos',
        sa.Column(
            'generation_started_at', 
            sa.DateTime(timezone=True), 
            nullable=True,
            comment='Timestamp when video generation actually started processing'
        )
    )
    
    op.add_column(
        'videos',
        sa.Column(
            'last_step_updated_at', 
            sa.DateTime(timezone=True), 
            nullable=True,
            comment='Last time a generation step was updated (for stuck job detection)'
        )
    )
    
    # Selected providers for this video (overrides user defaults)
    op.add_column(
        'videos',
        sa.Column(
            'selected_providers', 
            postgresql.JSONB(), 
            nullable=True,
            comment='Providers selected for this video: {script, voice, media, video_ai, assembly}'
        )
    )
    
    # Add index on last_step_updated_at for stuck job detection queries
    op.create_index(
        'ix_videos_last_step_updated_at', 
        'videos', 
        ['last_step_updated_at']
    )
    
    # Add index on generation_started_at for analytics
    op.create_index(
        'ix_videos_generation_started_at', 
        'videos', 
        ['generation_started_at']
    )
    
    # Add composite index for stuck job detection
    # (status = 'processing' AND last_step_updated_at < X)
    op.create_index(
        'ix_videos_stuck_detection',
        'videos',
        ['status', 'last_step_updated_at'],
        postgresql_where=sa.text("status = 'processing'")
    )


def downgrade() -> None:
    op.drop_index('ix_videos_stuck_detection', table_name='videos')
    op.drop_index('ix_videos_generation_started_at', table_name='videos')
    op.drop_index('ix_videos_last_step_updated_at', table_name='videos')
    
    op.drop_column('videos', 'selected_providers')
    op.drop_column('videos', 'last_step_updated_at')
    op.drop_column('videos', 'generation_started_at')
    op.drop_column('videos', 'subtitle_file_url')
