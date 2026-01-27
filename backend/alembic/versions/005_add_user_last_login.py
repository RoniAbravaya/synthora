"""Add last_login column to users table

Revision ID: 005
Revises: 004
Create Date: 2026-01-27

This migration adds a last_login timestamp column to the users table
to track when users last authenticated with the system.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_login column to users table."""
    op.add_column(
        'users',
        sa.Column(
            'last_login',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Last login timestamp'
        )
    )


def downgrade() -> None:
    """Remove last_login column from users table."""
    op.drop_column('users', 'last_login')
