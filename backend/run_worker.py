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

from __future__ import print_function
import sys

# IMMEDIATELY print to both stdout and stderr to ensure we see something
print("=" * 60)
print("SYNTHORA WORKER SCRIPT STARTING")
print("=" * 60)
sys.stdout.flush()
sys.stderr.write("Worker script is running\n")
sys.stderr.flush()

import os

# Print environment info
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Script path: {os.path.abspath(__file__)}")
print(f"Files in current dir: {os.listdir('.')[:10]}...")  # First 10 files
sys.stdout.flush()

# Check if app directory exists
if os.path.exists('app'):
    print("app/ directory exists")
    print(f"  Contents: {os.listdir('app')[:10]}")
else:
    print("ERROR: app/ directory NOT FOUND!")
    print(f"  Available dirs: {[d for d in os.listdir('.') if os.path.isdir(d)]}")
sys.stdout.flush()

# Check critical environment variables
print("\nEnvironment variables check:")
critical_vars = ['REDIS_URL', 'DATABASE_URL', 'APP_ENV', 'SECRET_KEY']
for var in critical_vars:
    value = os.environ.get(var)
    if value:
        # Mask sensitive values
        if 'URL' in var or 'KEY' in var or 'SECRET' in var:
            print(f"  {var}: SET (masked)")
        else:
            print(f"  {var}: {value}")
    else:
        print(f"  {var}: NOT SET!")
sys.stdout.flush()

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\nImporting app modules...")
sys.stdout.flush()

try:
    print("  Importing app.core.config...", end=" ")
    sys.stdout.flush()
    from app.core.config import get_settings
    print("OK")
    sys.stdout.flush()
    
    print("  Importing app.core.logging_config...", end=" ")
    sys.stdout.flush()
    from app.core.logging_config import setup_logging
    print("OK")
    sys.stdout.flush()
    
    print("  Loading settings...", end=" ")
    sys.stdout.flush()
    settings = get_settings()
    print("OK")
    sys.stdout.flush()
    
    print("  Setting up logging...", end=" ")
    sys.stdout.flush()
    import logging
    import argparse
    
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
        app_name="synthora-worker",
        reduce_sqlalchemy_noise=True,
    )
    print("OK")
    sys.stdout.flush()
    
    logger = logging.getLogger(__name__)
    print("\nAll imports successful!")
    sys.stdout.flush()
    
except Exception as e:
    print(f"\nFATAL: Failed to initialize: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    sys.stderr.flush()
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
