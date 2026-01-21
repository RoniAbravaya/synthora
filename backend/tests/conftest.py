"""
Pytest Configuration and Fixtures

Shared fixtures for all backend tests.
"""

import os
import pytest
from typing import Generator, Dict, Any
from datetime import datetime
from uuid import uuid4

# Set test environment before any imports
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_WEB_API_KEY"] = "test-api-key"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_fake"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
os.environ["STRIPE_MONTHLY_PRICE_ID"] = "price_monthly"
os.environ["STRIPE_ANNUAL_PRICE_ID"] = "price_annual"
os.environ["GCS_BUCKET_NAME"] = "test-bucket"
os.environ["GCS_PROJECT_ID"] = "test-gcs-project"
os.environ["ENCRYPTION_KEY"] = "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1jaGFyYWN0ZXJz"


# =============================================================================
# Simple Test Fixtures (No App Dependencies)
# =============================================================================

@pytest.fixture
def sample_template_config() -> Dict[str, Any]:
    """Return a sample template configuration."""
    return {
        "video_structure": {
            "duration_seconds": 60,
            "aspect_ratio": "9:16",
            "segments": [
                {"type": "hook", "duration_seconds": 5, "description": "Attention grabber"},
                {"type": "content", "duration_seconds": 45, "description": "Main content"},
                {"type": "cta", "duration_seconds": 10, "description": "Call to action"},
            ],
        },
        "visual_style": {
            "color_scheme": "vibrant",
            "font_family": "Montserrat",
            "transition_style": "smooth",
            "overlay_style": "minimal",
        },
        "audio": {
            "voice_style": "energetic",
            "background_music_genre": "upbeat",
            "sound_effects": True,
        },
        "script_prompt": {
            "tone": "casual",
            "hook_style": "question",
            "call_to_action": "follow",
            "content_structure": ["problem", "solution", "benefit"],
        },
        "platform_optimization": {
            "primary_platform": "tiktok",
            "hashtag_strategy": "trending",
            "caption_style": "engaging",
        },
    }


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Return sample user data."""
    return {
        "id": str(uuid4()),
        "firebase_uid": "test_firebase_uid_123",
        "email": "testuser@example.com",
        "display_name": "Test User",
        "role": "free",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_video_data() -> Dict[str, Any]:
    """Return sample video data."""
    return {
        "id": str(uuid4()),
        "title": "Test Video",
        "status": "completed",
        "progress": 100,
        "video_url": "https://storage.example.com/videos/test.mp4",
        "duration_seconds": 60,
    }


# =============================================================================
# Auth Helpers
# =============================================================================

@pytest.fixture
def mock_auth_headers() -> Dict[str, str]:
    """Create mock auth headers for testing."""
    return {"Authorization": "Bearer mock_test_token"}

