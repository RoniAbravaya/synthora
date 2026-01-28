"""
Logging Configuration for Synthora Backend

This module provides centralized logging configuration for both the
FastAPI application and RQ workers. It ensures logs are properly
formatted and routed to stdout/stderr for production environments.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    app_name: str = "synthora",
    reduce_sqlalchemy_noise: bool = True,
) -> None:
    """
    Configure logging for the application.
    
    This should be called early in application startup for both
    the FastAPI app and RQ workers.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format (json or text)
        app_name: Application name prefix
        reduce_sqlalchemy_noise: If True, set SQLAlchemy to WARNING level
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Define format based on preference
    if log_format == "json":
        format_string = (
            '{"time": "%(asctime)s", "app": "' + app_name + '", '
            '"name": "%(name)s", "level": "%(levelname)s", '
            '"message": "%(message)s"}'
        )
    else:
        format_string = (
            f"%(asctime)s [{app_name}] %(name)s %(levelname)s: %(message)s"
        )
    
    # Create handlers that write to stdout (not stderr)
    # This ensures logs are captured properly in Railway/Docker
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter(format_string))
    stdout_handler.setLevel(level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(stdout_handler)
    
    # Reduce noise from verbose libraries
    if reduce_sqlalchemy_noise:
        # SQLAlchemy engine logs ALL SQL queries at INFO level
        # Set to WARNING to only see important messages
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    
    # Other noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Ensure our app loggers are at the right level
    logging.getLogger("app").setLevel(level)
    logging.getLogger("app.services").setLevel(level)
    logging.getLogger("app.workers").setLevel(level)
    logging.getLogger("app.api").setLevel(level)
    
    # Log that we've configured logging
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, format={log_format}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class VideoGenerationLogger:
    """
    Specialized logger for video generation with structured logging.
    
    Provides methods for logging each step of video generation
    with consistent formatting for easy debugging.
    """
    
    def __init__(self, video_id: str, user_id: Optional[str] = None):
        """
        Initialize the video generation logger.
        
        Args:
            video_id: Video UUID
            user_id: User UUID (optional)
        """
        self.video_id = video_id
        self.user_id = user_id
        self.logger = logging.getLogger(f"app.video.{video_id[:8]}")
    
    def _format_msg(self, message: str) -> str:
        """Format message with video context."""
        prefix = f"[Video:{self.video_id[:8]}]"
        if self.user_id:
            prefix = f"[User:{self.user_id[:8]}]{prefix}"
        return f"{prefix} {message}"
    
    def start(self, step: str) -> None:
        """Log the start of a generation step."""
        self.logger.info(self._format_msg(f"Starting step: {step}"))
    
    def progress(self, step: str, progress: int, message: str = "") -> None:
        """Log progress for a step."""
        msg = f"Step {step} progress: {progress}%"
        if message:
            msg += f" - {message}"
        self.logger.info(self._format_msg(msg))
    
    def complete(self, step: str, details: Optional[dict] = None) -> None:
        """Log successful completion of a step."""
        msg = f"Step {step} completed"
        if details:
            msg += f": {details}"
        self.logger.info(self._format_msg(msg))
    
    def skip(self, step: str, reason: str) -> None:
        """Log that a step was skipped."""
        self.logger.info(self._format_msg(f"Step {step} skipped: {reason}"))
    
    def error(self, step: str, error: str, details: Optional[dict] = None) -> None:
        """Log an error during a step."""
        msg = f"Step {step} failed: {error}"
        if details:
            msg += f" | Details: {details}"
        self.logger.error(self._format_msg(msg))
    
    def warning(self, message: str) -> None:
        """Log a warning."""
        self.logger.warning(self._format_msg(message))
    
    def debug(self, message: str) -> None:
        """Log a debug message."""
        self.logger.debug(self._format_msg(message))
    
    def api_call(
        self,
        provider: str,
        endpoint: str,
        duration_ms: Optional[int] = None,
        status_code: Optional[int] = None,
    ) -> None:
        """Log an external API call."""
        msg = f"API call to {provider}: {endpoint}"
        if duration_ms is not None:
            msg += f" ({duration_ms}ms)"
        if status_code is not None:
            msg += f" -> {status_code}"
        self.logger.info(self._format_msg(msg))
    
    def generation_complete(self, total_time_seconds: float) -> None:
        """Log successful video generation completion."""
        self.logger.info(
            self._format_msg(f"Generation complete! Total time: {total_time_seconds:.1f}s")
        )
    
    def generation_failed(self, error: str, step: Optional[str] = None) -> None:
        """Log video generation failure."""
        msg = f"Generation failed: {error}"
        if step:
            msg += f" (at step: {step})"
        self.logger.error(self._format_msg(msg))
