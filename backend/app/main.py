"""
Synthora Backend Application

Main FastAPI application entry point. This module initializes the FastAPI app,
configures middleware, sets up exception handlers, and includes all API routers.

To run the application:
    uvicorn app.main:app --reload

For production:
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import get_settings
from app.core.database import check_database_connection, get_database_info
from app.api.v1.router import api_router

# Get settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if settings.LOG_FORMAT == "text"
    else '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the application.
    - Startup: Initialize database, check connections, warm up caches
    - Shutdown: Close connections, cleanup resources
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    
    # Check database connection
    if check_database_connection():
        logger.info("Database connection successful")
        db_info = get_database_info()
        logger.info(f"Database version: {db_info.get('version', 'unknown')}")
    else:
        logger.error("Database connection failed!")
    
    # Initialize Firebase
    from app.services.firebase import initialize_firebase
    if initialize_firebase():
        logger.info("Firebase initialized successfully")
    else:
        logger.warning("Firebase initialization failed or not configured")
    
    logger.info(f"{settings.APP_NAME} started successfully")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## Synthora API

AI-Powered Video Generator Platform - Generate viral videos using multiple AI integrations.

### Features
- 🎬 **Video Generation** - Create videos with AI-powered scripts, voiceovers, and visuals
- 📱 **Multi-Platform Posting** - Post to YouTube, TikTok, Instagram, and Facebook
- 📊 **Analytics** - Track performance across all platforms
- 🤖 **AI Suggestions** - Get recommendations to improve content (Premium)

### Authentication
All endpoints (except `/health` and `/auth/setup-status`) require Firebase Authentication.
Include the Firebase ID token in the `Authorization` header:
```
Authorization: Bearer <firebase-id-token>
```

### Rate Limiting
- Free users: 100 requests/minute
- Premium users: 500 requests/minute
- Admin users: Unlimited
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# =============================================================================
# Middleware Configuration
# =============================================================================

# CORS Middleware
# Configured for strict origin checking in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    Middleware to add a unique request ID to each request.
    Useful for tracing and debugging.
    """
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all incoming requests.
    """
    import time
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log request (skip health checks to reduce noise)
    if request.url.path != "/api/v1/health":
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s"
        )
    
    return response


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with a clean response format.
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions.
    In production, hide internal error details.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unexpected error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True
    )
    
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred",
                "request_id": request_id
            }
        )
    else:
        # In development, show full error details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "request_id": request_id
            }
        )


# =============================================================================
# API Routers
# =============================================================================

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")


# =============================================================================
# Root Endpoints
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - returns basic API information.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "AI-Powered Video Generator Platform",
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/api/v1/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Simple health check endpoint for load balancers.
    """
    return {"status": "healthy"}


# =============================================================================
# Development Helpers
# =============================================================================

if settings.is_development:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """
        Debug endpoint to view non-sensitive configuration.
        Only available in development mode.
        """
        return {
            "app_name": settings.APP_NAME,
            "app_env": settings.APP_ENV,
            "debug": settings.DEBUG,
            "cors_origins": settings.cors_origins_list,
            "features": {
                "ai_suggestions": settings.FEATURE_AI_SUGGESTIONS,
                "scheduling": settings.FEATURE_SCHEDULING,
                "analytics": settings.FEATURE_ANALYTICS,
            },
            "limits": {
                "rate_limit_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
                "max_video_duration": settings.MAX_VIDEO_DURATION,
                "free_user_retention_days": settings.FREE_USER_VIDEO_RETENTION_DAYS,
            }
        }
    
    @app.get("/debug/db", tags=["Debug"])
    async def debug_database():
        """
        Debug endpoint to view database connection info.
        Only available in development mode.
        """
        return get_database_info()

