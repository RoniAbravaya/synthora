"""
Synthora API v1 Router

This module aggregates all API v1 routers into a single router
that is included in the main FastAPI application.

All endpoints are prefixed with /api/v1 when included in main.py
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    templates,
    integrations,
    videos,
    social_accounts,
    posts,
    analytics,
    suggestions,
    notifications,
    subscriptions,
    admin,
    health,
)

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
# Note: Each router already has its own prefix defined in the endpoint file

# Health endpoints (no prefix - health.router already has tags)
api_router.include_router(health.router)

# Authentication endpoints
api_router.include_router(auth.router)

# User management endpoints
api_router.include_router(users.router)

# Template endpoints
api_router.include_router(templates.router)

# Integration endpoints
api_router.include_router(integrations.router)

# Video endpoints
api_router.include_router(videos.router)

# Social account endpoints
api_router.include_router(social_accounts.router)

# Post endpoints
api_router.include_router(posts.router)

# Analytics endpoints
api_router.include_router(analytics.router)

# AI Suggestions endpoints
api_router.include_router(suggestions.router)

# Notification endpoints
api_router.include_router(notifications.router)

# Subscription endpoints
api_router.include_router(subscriptions.router)

# Admin endpoints
api_router.include_router(admin.router)
