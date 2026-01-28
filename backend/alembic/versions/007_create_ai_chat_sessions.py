"""
Create AI chat sessions table

Stores chat conversation context for AI suggestions feature.
Sessions are used for conversational AI interaction where users
can refine suggestions, create series, and plan content.

Revision ID: 007
Revises: 006_extend_videos_for_planning
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '007_create_ai_chat_sessions'
down_revision = '006_extend_videos_for_planning'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ai_chat_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        ),
        sa.Column(
            'suggestion_context',
            JSONB,
            nullable=True,
            comment='Current suggestion being discussed'
        ),
        sa.Column(
            'messages',
            JSONB,
            nullable=False,
            server_default='[]',
            comment='Chat message history'
        ),
        sa.Column(
            'is_active',
            sa.Boolean,
            nullable=False,
            default=True,
            server_default='true',
            comment='Whether session is still active'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=True
        ),
    )
    
    # Index for finding active sessions
    op.create_index(
        'ix_ai_chat_sessions_user_active',
        'ai_chat_sessions',
        ['user_id', 'is_active'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_ai_chat_sessions_user_active', table_name='ai_chat_sessions')
    op.drop_table('ai_chat_sessions')
