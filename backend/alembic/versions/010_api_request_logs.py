"""API request logs table

Revision ID: 010_api_request_logs
Revises: 009_user_generation_settings
Create Date: 2026-01-28

This migration creates the api_request_logs table for storing:
- All external API requests made during video generation
- Request/response data for debugging
- Duration and error information
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_api_request_logs'
down_revision = '009_user_generation_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # API Request Logs Table
    # ==========================================================================
    op.create_table(
        'api_request_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        
        # Foreign keys (nullable for flexibility)
        sa.Column(
            'user_id', 
            postgresql.UUID(as_uuid=True), 
            sa.ForeignKey('users.id', ondelete='SET NULL'), 
            nullable=True,
            comment='User who initiated the request'
        ),
        sa.Column(
            'video_id', 
            postgresql.UUID(as_uuid=True), 
            sa.ForeignKey('videos.id', ondelete='SET NULL'), 
            nullable=True,
            comment='Video being generated (if applicable)'
        ),
        
        # Request information
        sa.Column('provider', sa.String(50), nullable=False,
                  comment='Integration provider name (e.g., openai_gpt, elevenlabs)'),
        sa.Column('endpoint', sa.String(500), nullable=False,
                  comment='API endpoint URL'),
        sa.Column('method', sa.String(10), nullable=False,
                  comment='HTTP method (GET, POST, etc.)'),
        sa.Column('request_body', postgresql.JSONB(), nullable=True,
                  comment='Request payload (sensitive data masked)'),
        
        # Response information
        sa.Column('status_code', sa.Integer(), nullable=True,
                  comment='HTTP response status code'),
        sa.Column('response_body', postgresql.JSONB(), nullable=True,
                  comment='Response payload (may be truncated for large responses)'),
        sa.Column('duration_ms', sa.Integer(), nullable=True,
                  comment='Request duration in milliseconds'),
        
        # Error information
        sa.Column('error_message', sa.Text(), nullable=True,
                  comment='Error message if request failed'),
        sa.Column('error_details', postgresql.JSONB(), nullable=True,
                  comment='Additional error details (stack trace, etc.)'),
        
        # Context
        sa.Column('generation_step', sa.String(50), nullable=True,
                  comment='Video generation step (script, voice, media, video_ai, assembly)'),
        
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for common queries
    op.create_index('ix_api_request_logs_user_id', 'api_request_logs', ['user_id'])
    op.create_index('ix_api_request_logs_video_id', 'api_request_logs', ['video_id'])
    op.create_index('ix_api_request_logs_provider', 'api_request_logs', ['provider'])
    op.create_index('ix_api_request_logs_created_at', 'api_request_logs', ['created_at'])
    op.create_index('ix_api_request_logs_status_code', 'api_request_logs', ['status_code'])
    
    # Composite index for admin log search
    op.create_index(
        'ix_api_request_logs_provider_created', 
        'api_request_logs', 
        ['provider', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_api_request_logs_provider_created', table_name='api_request_logs')
    op.drop_index('ix_api_request_logs_status_code', table_name='api_request_logs')
    op.drop_index('ix_api_request_logs_created_at', table_name='api_request_logs')
    op.drop_index('ix_api_request_logs_provider', table_name='api_request_logs')
    op.drop_index('ix_api_request_logs_video_id', table_name='api_request_logs')
    op.drop_index('ix_api_request_logs_user_id', table_name='api_request_logs')
    op.drop_table('api_request_logs')
