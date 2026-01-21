"""
Synthora Backend Configuration

This module handles all application configuration using Pydantic Settings.
Environment variables are loaded from .env file or system environment.
All sensitive values should be set via environment variables, never hardcoded.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Usage:
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.APP_NAME)
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # -------------------------------------------------------------------------
    # App Configuration
    # -------------------------------------------------------------------------
    APP_NAME: str = "Synthora"
    APP_ENV: str = Field(default="development", description="development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for encryption")
    
    # URLs
    BACKEND_URL: str = Field(default="http://localhost:8000", description="Backend API URL")
    FRONTEND_URL: str = Field(default="http://localhost:5173", description="Frontend URL")
    
    # -------------------------------------------------------------------------
    # Database (PostgreSQL)
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="sqlite:///./synthora.db",
        description="PostgreSQL connection URL (or SQLite for development)"
    )
    DB_ENCRYPTION_KEY: Optional[str] = Field(default=None, description="Database encryption key for pgcrypto")
    
    # -------------------------------------------------------------------------
    # Redis (Upstash) - Optional for initial deployment
    # -------------------------------------------------------------------------
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (optional - background jobs disabled without it)"
    )
    
    # -------------------------------------------------------------------------
    # Firebase Authentication - Required for auth but has defaults for startup
    # -------------------------------------------------------------------------
    FIREBASE_PROJECT_ID: str = Field(
        default="placeholder",
        description="Firebase project ID"
    )
    FIREBASE_WEB_API_KEY: str = Field(
        default="placeholder",
        description="Firebase Web API key"
    )
    FIREBASE_AUTH_DOMAIN: Optional[str] = Field(default=None, description="Firebase auth domain")
    FIREBASE_CREDENTIALS_PATH: Optional[str] = Field(default=None, description="Path to service account JSON file")
    FIREBASE_CREDENTIALS_JSON: Optional[str] = Field(default=None, description="Service account JSON as string (for Railway)")
    
    # -------------------------------------------------------------------------
    # Stripe - Optional for initial deployment
    # -------------------------------------------------------------------------
    STRIPE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Stripe secret key (optional - payments disabled without it)"
    )
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, description="Stripe publishable key")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Stripe webhook signing secret")
    STRIPE_MONTHLY_PRICE_ID: Optional[str] = Field(default=None, description="Stripe price ID for monthly plan")
    STRIPE_ANNUAL_PRICE_ID: Optional[str] = Field(default=None, description="Stripe price ID for annual plan")
    
    # -------------------------------------------------------------------------
    # Google Cloud Storage - Optional for initial deployment
    # -------------------------------------------------------------------------
    GCS_BUCKET_NAME: Optional[str] = Field(
        default=None,
        description="GCS bucket name (optional - local storage used without it)"
    )
    GCS_PROJECT_ID: Optional[str] = Field(default=None, description="GCP project ID")
    GCS_SERVICE_ACCOUNT_PATH: Optional[str] = Field(default=None, description="Path to GCS service account JSON")
    GCS_SERVICE_ACCOUNT_JSON: Optional[str] = Field(default=None, description="GCS service account JSON as string")
    
    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed origins"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, description="Max requests per minute per user")
    
    # -------------------------------------------------------------------------
    # Encryption
    # -------------------------------------------------------------------------
    # WARNING: This default key is for DEVELOPMENT ONLY!
    # Generate a real key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = Field(
        default="ZGV2ZWxvcG1lbnRfa2V5X29ubHlfY2hhbmdlX3RoaXM=",
        description="Fernet encryption key for API keys (MUST change in production!)"
    )
    
    # -------------------------------------------------------------------------
    # Worker Configuration
    # -------------------------------------------------------------------------
    RQ_QUEUE_NAME: str = Field(default="synthora", description="RQ queue name")
    RQ_WORKER_COUNT: int = Field(default=2, description="Number of RQ workers")
    
    # -------------------------------------------------------------------------
    # AI Services
    # -------------------------------------------------------------------------
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key for AI features")
    
    # -------------------------------------------------------------------------
    # Video Generation
    # -------------------------------------------------------------------------
    MAX_VIDEO_DURATION: int = Field(default=300, description="Maximum video duration in seconds")
    DEFAULT_VIDEO_RESOLUTION: str = Field(default="1080p", description="Default video resolution")
    DEFAULT_VIDEO_BITRATE: str = Field(default="5000k", description="Default video bitrate")
    FFMPEG_PATH: Optional[str] = Field(default=None, description="Path to FFmpeg binary")
    
    # -------------------------------------------------------------------------
    # Storage Settings
    # -------------------------------------------------------------------------
    FREE_USER_VIDEO_RETENTION_DAYS: int = Field(default=30, description="Video retention for free users")
    MAX_UPLOAD_SIZE: int = Field(default=524288000, description="Max upload size in bytes (500MB)")
    
    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    FEATURE_AI_SUGGESTIONS: bool = Field(default=True, description="Enable AI suggestions feature")
    FEATURE_SCHEDULING: bool = Field(default=True, description="Enable scheduling feature")
    FEATURE_ANALYTICS: bool = Field(default=True, description="Enable analytics feature")
    
    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    
    # -------------------------------------------------------------------------
    # Social Media OAuth
    # -------------------------------------------------------------------------
    # YouTube
    YOUTUBE_CLIENT_ID: Optional[str] = Field(default=None, description="YouTube OAuth client ID")
    YOUTUBE_CLIENT_SECRET: Optional[str] = Field(default=None, description="YouTube OAuth client secret")
    
    # TikTok
    TIKTOK_CLIENT_KEY: Optional[str] = Field(default=None, description="TikTok client key")
    TIKTOK_CLIENT_SECRET: Optional[str] = Field(default=None, description="TikTok client secret")
    
    # Meta (Instagram/Facebook)
    META_APP_ID: Optional[str] = Field(default=None, description="Meta app ID")
    META_APP_SECRET: Optional[str] = Field(default=None, description="Meta app secret")
    
    # -------------------------------------------------------------------------
    # Sentry (Optional)
    # -------------------------------------------------------------------------
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Validate APP_ENV is one of the allowed values."""
        allowed = {"development", "staging", "production", "test"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of: {allowed}")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate LOG_LEVEL is a valid Python logging level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {allowed}")
        return v_upper
    
    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"
    
    @property
    def database_url(self) -> str:
        """Get database URL (alias for DATABASE_URL for Alembic compatibility)."""
        return self.DATABASE_URL
    
    @property
    def youtube_redirect_uri(self) -> str:
        """Get YouTube OAuth redirect URI."""
        return f"{self.BACKEND_URL}/api/v1/social-accounts/callback/youtube"
    
    @property
    def tiktok_redirect_uri(self) -> str:
        """Get TikTok OAuth redirect URI."""
        return f"{self.BACKEND_URL}/api/v1/social-accounts/callback/tiktok"
    
    @property
    def instagram_redirect_uri(self) -> str:
        """Get Instagram OAuth redirect URI."""
        return f"{self.BACKEND_URL}/api/v1/social-accounts/callback/instagram"
    
    @property
    def facebook_redirect_uri(self) -> str:
        """Get Facebook OAuth redirect URI."""
        return f"{self.BACKEND_URL}/api/v1/social-accounts/callback/facebook"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    In tests, you can clear the cache with: get_settings.cache_clear()
    
    Returns:
        Settings: Application settings instance
    """
    return Settings()

