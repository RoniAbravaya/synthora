"""Modular integrations - migrate provider names

Revision ID: 008_modular_integrations
Revises: 007_create_ai_chat_sessions
Create Date: 2026-01-28

This migration:
1. Migrates existing 'openai' provider to 'openai_gpt'
2. Adds index for faster provider lookups
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_modular_integrations'
down_revision = '007_create_ai_chat_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Migrate existing provider names to new modular format
    # ==========================================================================
    
    # Migrate 'openai' -> 'openai_gpt' (Script/Text AI)
    op.execute("""
        UPDATE integrations 
        SET provider = 'openai_gpt', 
            updated_at = NOW()
        WHERE provider = 'openai'
    """)
    
    # Migrate 'sora' -> 'openai_sora' (Video AI via OpenAI)
    op.execute("""
        UPDATE integrations 
        SET provider = 'openai_sora', 
            updated_at = NOW()
        WHERE provider = 'sora'
    """)
    
    # Add index on provider column for faster category lookups
    op.create_index(
        'ix_integrations_provider', 
        'integrations', 
        ['provider']
    )
    
    # Add index on category column
    op.create_index(
        'ix_integrations_category', 
        'integrations', 
        ['category']
    )


def downgrade() -> None:
    # Remove indexes
    op.drop_index('ix_integrations_category', table_name='integrations')
    op.drop_index('ix_integrations_provider', table_name='integrations')
    
    # Revert provider names
    op.execute("""
        UPDATE integrations 
        SET provider = 'openai', 
            updated_at = NOW()
        WHERE provider = 'openai_gpt'
    """)
    
    op.execute("""
        UPDATE integrations 
        SET provider = 'sora', 
            updated_at = NOW()
        WHERE provider = 'openai_sora'
    """)
