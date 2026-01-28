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

import os
import sys
import logging
import argparse

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def main():
    """Main entry point for the RQ worker."""
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
        logger.error("REDIS_URL environment variable is not set!")
        sys.exit(1)
    
    # Parse queues
    queues = [q.strip() for q in args.queues.split(",") if q.strip()]
    
    logger.info("=" * 60)
    logger.info("Starting Synthora Worker")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"Queues: {', '.join(queues)}")
    logger.info("=" * 60)
    
    try:
        from redis import Redis
        from rq import Worker, Queue
        
        # Connect to Redis
        redis_conn = Redis.from_url(redis_url)
        
        # Test connection
        redis_conn.ping()
        logger.info("Redis connection successful")
        
        # Create queues
        queue_objects = [Queue(name, connection=redis_conn) for name in queues]
        
        # Create and start worker
        worker = Worker(
            queues=queue_objects,
            connection=redis_conn,
            name=f"synthora-worker-{os.getpid()}",
        )
        
        logger.info(f"Worker {worker.name} starting...")
        
        # Run the worker
        worker.work(burst=args.burst, with_scheduler=True)
        
    except ImportError as e:
        logger.error(f"Missing required package: {e}")
        logger.error("Make sure redis and rq are installed: pip install redis rq")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Worker failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
