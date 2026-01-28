#!/usr/bin/env python3
"""
Synthora RQ Worker Entry Point

This script starts the RQ worker with proper logging configuration.
It should be used instead of running `rq worker` directly.

Usage:
    python run_worker.py
    
Or with specific queues:
    python run_worker.py --queues video,default
"""

# Print immediately to catch early startup issues
print("=" * 60, flush=True)
print("SYNTHORA WORKER STARTING", flush=True)
print("=" * 60, flush=True)

import os
import sys

# Print Python info for debugging
print(f"Python: {sys.version}", flush=True)
print(f"Working directory: {os.getcwd()}", flush=True)
print(f"Script location: {os.path.abspath(__file__)}", flush=True)

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import logging
    import argparse
    
    # Import and setup logging BEFORE any other imports
    from app.core.config import get_settings
    from app.core.logging_config import setup_logging
    
    settings = get_settings()
    
    # Setup logging with worker-specific prefix
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        app_name="synthora-worker",
        reduce_sqlalchemy_noise=True,  # Always reduce in worker
    )
    
    logger = logging.getLogger(__name__)
    print("Logging configured successfully", flush=True)
    
except Exception as e:
    print(f"FATAL: Failed to initialize worker: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)


def main():
    """Main entry point for the RQ worker."""
    print("Entering main()", flush=True)
    
    parser = argparse.ArgumentParser(description="Synthora RQ Worker")
    parser.add_argument(
        "--queues",
        type=str,
        default="video,default,analytics,posts,cleanup",
        help="Comma-separated list of queues to process",
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Run in burst mode (exit when queue is empty)",
    )
    args = parser.parse_args()
    
    redis_url = settings.REDIS_URL
    if not redis_url:
        print("FATAL: REDIS_URL environment variable is not set!", flush=True)
        logger.error("REDIS_URL environment variable is not set!")
        sys.exit(1)
    
    # Mask Redis URL for logging (show host only)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(redis_url)
        masked_url = f"{parsed.scheme}://{parsed.hostname}:***"
    except Exception:
        masked_url = "***"
    
    print(f"Redis URL configured: {masked_url}", flush=True)
    
    # Parse queues
    queues = [q.strip() for q in args.queues.split(",") if q.strip()]
    
    print("=" * 60, flush=True)
    print("WORKER CONFIGURATION", flush=True)
    print(f"  Environment: {settings.APP_ENV}", flush=True)
    print(f"  Log Level: {settings.LOG_LEVEL}", flush=True)
    print(f"  Queues: {', '.join(queues)}", flush=True)
    print(f"  Redis: {masked_url}", flush=True)
    print("=" * 60, flush=True)
    
    logger.info("=" * 60)
    logger.info("Starting Synthora Worker")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"Queues: {', '.join(queues)}")
    logger.info("=" * 60)
    
    try:
        print("Importing redis and rq...", flush=True)
        from redis import Redis
        from rq import Worker, Queue
        print("Import successful", flush=True)
        
        # Connect to Redis
        print("Connecting to Redis...", flush=True)
        redis_conn = Redis.from_url(redis_url)
        
        # Test connection
        redis_conn.ping()
        print("Redis connection successful!", flush=True)
        logger.info("Redis connection successful")
        
        # Create queues
        print(f"Creating {len(queues)} queue(s)...", flush=True)
        queue_objects = [Queue(name, connection=redis_conn) for name in queues]
        
        # Create and start worker
        worker_name = f"synthora-worker-{os.getpid()}"
        print(f"Creating worker: {worker_name}", flush=True)
        worker = Worker(
            queues=queue_objects,
            connection=redis_conn,
            name=worker_name,
        )
        
        print(f"Worker {worker.name} starting - listening for jobs...", flush=True)
        logger.info(f"Worker {worker.name} starting...")
        
        # Run the worker
        worker.work(burst=args.burst, with_scheduler=True)
        
    except ImportError as e:
        print(f"FATAL: Missing required package: {e}", flush=True)
        logger.error(f"Missing required package: {e}")
        logger.error("Make sure redis and rq are installed: pip install redis rq")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: Worker failed to start: {e}", flush=True)
        import traceback
        traceback.print_exc()
        logger.exception(f"Worker failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
