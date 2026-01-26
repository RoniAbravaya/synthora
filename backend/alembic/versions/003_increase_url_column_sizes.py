"""Increase URL column sizes for GCS signed URLs

Revision ID: 003_url_columns
Revises: 002_seed_templates
Create Date: 2026-01-26

GCS signed URLs are typically 1000-1500 characters. The original String(500)
was too short, causing StringDataRightTruncation errors when saving video_url
and thumbnail_url after uploading to GCS.

This migration changes the columns to TEXT type to accommodate any URL length.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_url_columns'
down_revision = '002_seed_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Increase URL column sizes from String(500) to TEXT for GCS signed URLs.
    
    Affected tables and columns:
    - videos.video_url
    - videos.thumbnail_url
    - templates.thumbnail_url
    - templates.preview_url
    - users.photo_url
    - social_accounts.profile_url
    - social_accounts.avatar_url
    - posts.post_url
    - notifications.action_url
    """
    # Videos table - most critical for GCS signed URLs
    op.alter_column(
        'videos',
        'video_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    op.alter_column(
        'videos',
        'thumbnail_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    
    # Templates table
    op.alter_column(
        'templates',
        'thumbnail_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    op.alter_column(
        'templates',
        'preview_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    
    # Users table
    op.alter_column(
        'users',
        'photo_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    
    # Social accounts table
    op.alter_column(
        'social_accounts',
        'profile_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    op.alter_column(
        'social_accounts',
        'avatar_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    
    # Posts table
    op.alter_column(
        'posts',
        'post_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )
    
    # Notifications table
    op.alter_column(
        'notifications',
        'action_url',
        existing_type=sa.String(500),
        type_=sa.Text(),
        existing_nullable=True
    )


def downgrade() -> None:
    """Revert URL columns back to String(500)."""
    # Note: This may fail if existing data exceeds 500 characters
    
    op.alter_column(
        'videos',
        'video_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    op.alter_column(
        'videos',
        'thumbnail_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    
    op.alter_column(
        'templates',
        'thumbnail_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    op.alter_column(
        'templates',
        'preview_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    
    op.alter_column(
        'users',
        'photo_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    
    op.alter_column(
        'social_accounts',
        'profile_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    op.alter_column(
        'social_accounts',
        'avatar_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    
    op.alter_column(
        'posts',
        'post_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
    
    op.alter_column(
        'notifications',
        'action_url',
        existing_type=sa.Text(),
        type_=sa.String(500),
        existing_nullable=True
    )
