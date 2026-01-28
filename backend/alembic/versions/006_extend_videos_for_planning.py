"""
Extend videos table for planning and scheduling

Adds columns for:
- Planned/scheduled video workflow
- Series management
- AI suggestion data storage
- Target platforms for posting

Revision ID: 006
Revises: 005_add_user_last_login
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


# revision identifiers, used by Alembic.
revision = '006_extend_videos_for_planning'
down_revision = '005_add_user_last_login'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scheduling columns
    op.add_column('videos', sa.Column(
        'scheduled_post_time',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='When the video should be posted'
    ))
    op.add_column('videos', sa.Column(
        'generation_triggered_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='When generation was triggered by scheduler'
    ))
    op.add_column('videos', sa.Column(
        'posted_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='When the video was actually posted'
    ))
    
    # Add series columns
    op.add_column('videos', sa.Column(
        'series_name',
        sa.String(255),
        nullable=True,
        comment='Name of the video series (if part of series)'
    ))
    op.add_column('videos', sa.Column(
        'series_order',
        sa.Integer,
        nullable=True,
        comment='Order in the series (1, 2, 3...)'
    ))
    
    # Add platform targeting
    op.add_column('videos', sa.Column(
        'target_platforms',
        ARRAY(sa.String(50)),
        nullable=True,
        comment='Platforms to post to (youtube, tiktok, instagram, facebook)'
    ))
    
    # Add AI suggestion data (stores complete suggestion details for generation)
    op.add_column('videos', sa.Column(
        'ai_suggestion_data',
        JSONB,
        nullable=True,
        comment='Complete AI-generated suggestion data for video generation'
    ))
    
    # Add planning status tracking
    # Values: none, planned, generating, ready, posting, posted, failed
    op.add_column('videos', sa.Column(
        'planning_status',
        sa.String(50),
        nullable=True,
        server_default='none',
        comment='Planning workflow status'
    ))
    
    # Add indexes for efficient querying
    op.create_index(
        'ix_videos_scheduled_post_time',
        'videos',
        ['scheduled_post_time'],
        unique=False
    )
    op.create_index(
        'ix_videos_planning_status',
        'videos',
        ['planning_status'],
        unique=False
    )
    op.create_index(
        'ix_videos_series_name',
        'videos',
        ['series_name'],
        unique=False
    )
    
    # Composite index for scheduler queries
    op.create_index(
        'ix_videos_planning_scheduled',
        'videos',
        ['planning_status', 'scheduled_post_time'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_videos_planning_scheduled', table_name='videos')
    op.drop_index('ix_videos_series_name', table_name='videos')
    op.drop_index('ix_videos_planning_status', table_name='videos')
    op.drop_index('ix_videos_scheduled_post_time', table_name='videos')
    
    # Drop columns
    op.drop_column('videos', 'planning_status')
    op.drop_column('videos', 'ai_suggestion_data')
    op.drop_column('videos', 'target_platforms')
    op.drop_column('videos', 'series_order')
    op.drop_column('videos', 'series_name')
    op.drop_column('videos', 'posted_at')
    op.drop_column('videos', 'generation_triggered_at')
    op.drop_column('videos', 'scheduled_post_time')
