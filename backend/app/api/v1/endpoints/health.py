"""
Health Check API Endpoints

Provides health check endpoints for monitoring and load balancers.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db, check_database_connection, get_database_info
from app.core.config import get_settings
from app.services.firebase import is_firebase_initialized
from app.schemas.common import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns a simple status indicating the API is running.
    This endpoint is typically used by load balancers and
    container orchestrators.
    
    **No authentication required.**
    """
    return HealthResponse(
        status="healthy",
        service="synthora-api",
    )


@router.get("/health/detailed", response_model=HealthResponse)
async def detailed_health_check(
    db: Session = Depends(get_db),
):
    """
    Detailed health check with dependency status.
    
    Checks the status of:
    - Database connection
    - Firebase initialization
    - Redis connection (if configured)
    
    **No authentication required.**
    
    **Note:** This endpoint may be slower due to health checks.
    """
    settings = get_settings()
    checks = {}
    overall_healthy = True
    
    # Check database
    try:
        db_info = get_database_info()
        checks["database"] = {
            "status": "healthy" if db_info.get("connected") else "unhealthy",
            "connected": db_info.get("connected", False),
            "pool_size": db_info.get("pool_size"),
            "checked_out": db_info.get("checked_out"),
        }
        if not db_info.get("connected"):
            overall_healthy = False
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_healthy = False
    
    # Check Firebase
    firebase_ready = is_firebase_initialized()
    checks["firebase"] = {
        "status": "healthy" if firebase_ready else "not_initialized",
        "initialized": firebase_ready,
    }
    # Firebase not being initialized is a warning, not a failure
    # (it might be intentionally disabled in some environments)
    
    # Check Redis (if configured)
    if settings.REDIS_URL:
        try:
            import redis
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            checks["redis"] = {
                "status": "healthy",
                "connected": True,
            }
        except Exception as e:
            checks["redis"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            overall_healthy = False
    else:
        checks["redis"] = {
            "status": "not_configured",
            "message": "Redis URL not set",
        }
    
    # Add timestamp
    checks["timestamp"] = datetime.utcnow().isoformat()
    
    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        service="synthora-api",
        checks=checks,
    )


@router.get("/health/ready")
async def readiness_check(
    db: Session = Depends(get_db),
):
    """
    Readiness probe endpoint.
    
    Returns 200 if the service is ready to accept traffic.
    Used by Kubernetes/Railway for readiness probes.
    
    **No authentication required.**
    """
    # Check database is accessible
    if not check_database_connection():
        return {"ready": False, "reason": "Database not connected"}
    
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """
    Liveness probe endpoint.
    
    Returns 200 if the service is alive.
    Used by Kubernetes/Railway for liveness probes.
    
    **No authentication required.**
    """
    return {"alive": True}


@router.get("/")
async def root():
    """
    API root endpoint.
    
    Returns basic API information.
    """
    settings = get_settings()
    
    return {
        "name": "Synthora API",
        "version": "1.0.0",
        "description": "AI Video Generator Platform",
        "docs_url": "/docs" if settings.DEBUG else None,
        "health_url": "/api/v1/health",
    }
