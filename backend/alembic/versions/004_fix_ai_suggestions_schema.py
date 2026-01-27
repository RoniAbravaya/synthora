"""Fix ai_suggestions table schema

Revision ID: 004_fix_ai_suggestions
Revises: 003_increase_url_column_sizes
Create Date: 2026-01-27

This migration fixes the ai_suggestions table to match the SQLAlchemy model:
- Rename 'type' column to 'suggestion_type'
- Rename 'is_applied' to 'is_acted'
- Rename 'applied_at' to 'acted_at'
- Rename 'metadata' to 'extra_data'
- Add missing columns: action_type, action_data, read_at, dismissed_at,
  related_video_id, related_post_id, related_template_id, suggestion, confidence_score
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_fix_ai_suggestions'
down_revision = '003_increase_url_column_sizes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Rename existing columns to match model
    # ==========================================================================
    
    # Rename 'type' to 'suggestion_type'
    op.alter_column('ai_suggestions', 'type', new_column_name='suggestion_type')
    
    # Rename 'is_applied' to 'is_acted'
    op.alter_column('ai_suggestions', 'is_applied', new_column_name='is_acted')
    
    # Rename 'applied_at' to 'acted_at'
    op.alter_column('ai_suggestions', 'applied_at', new_column_name='acted_at')
    
    # Rename 'metadata' to 'extra_data'
    op.alter_column('ai_suggestions', 'metadata', new_column_name='extra_data')
    
    # ==========================================================================
    # Add missing columns
    # ==========================================================================
    
    # Action information
    op.add_column('ai_suggestions', sa.Column('action_type', sa.String(50), nullable=True))
    op.add_column('ai_suggestions', sa.Column('action_data', postgresql.JSONB(), nullable=True))
    
    # Status timestamps
    op.add_column('ai_suggestions', sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ai_suggestions', sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Related entities
    op.add_column('ai_suggestions', sa.Column(
        'related_video_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('videos.id', ondelete='SET NULL'),
        nullable=True
    ))
    op.add_column('ai_suggestions', sa.Column(
        'related_post_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('posts.id', ondelete='SET NULL'),
        nullable=True
    ))
    op.add_column('ai_suggestions', sa.Column(
        'related_template_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('templates.id', ondelete='SET NULL'),
        nullable=True
    ))
    
    # Legacy fields for backwards compatibility
    op.add_column('ai_suggestions', sa.Column('suggestion', postgresql.JSONB(), nullable=True))
    op.add_column('ai_suggestions', sa.Column('confidence_score', sa.Float(), nullable=True, server_default='0.5'))
    
    # ==========================================================================
    # Update indexes
    # ==========================================================================
    
    # Drop old index on 'type' column
    op.drop_index('ix_ai_suggestions_type', table_name='ai_suggestions')
    
    # Create new index on 'suggestion_type' column
    op.create_index('ix_ai_suggestions_suggestion_type', 'ai_suggestions', ['suggestion_type'])
    
    # Create index on priority for sorting
    op.create_index('ix_ai_suggestions_priority', 'ai_suggestions', ['priority'])


def downgrade() -> None:
    # Drop new indexes
    op.drop_index('ix_ai_suggestions_priority', table_name='ai_suggestions')
    op.drop_index('ix_ai_suggestions_suggestion_type', table_name='ai_suggestions')
    
    # Create old index
    op.create_index('ix_ai_suggestions_type', 'ai_suggestions', ['suggestion_type'])
    
    # Drop new columns
    op.drop_column('ai_suggestions', 'confidence_score')
    op.drop_column('ai_suggestions', 'suggestion')
    op.drop_column('ai_suggestions', 'related_template_id')
    op.drop_column('ai_suggestions', 'related_post_id')
    op.drop_column('ai_suggestions', 'related_video_id')
    op.drop_column('ai_suggestions', 'dismissed_at')
    op.drop_column('ai_suggestions', 'read_at')
    op.drop_column('ai_suggestions', 'action_data')
    op.drop_column('ai_suggestions', 'action_type')
    
    # Rename columns back
    op.alter_column('ai_suggestions', 'extra_data', new_column_name='metadata')
    op.alter_column('ai_suggestions', 'acted_at', new_column_name='applied_at')
    op.alter_column('ai_suggestions', 'is_acted', new_column_name='is_applied')
    op.alter_column('ai_suggestions', 'suggestion_type', new_column_name='type')
    
    # Drop old index and create new one after rename
    op.drop_index('ix_ai_suggestions_type', table_name='ai_suggestions')
    op.create_index('ix_ai_suggestions_type', 'ai_suggestions', ['type'])
