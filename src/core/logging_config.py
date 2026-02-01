"""
Logging Configuration - Structured logging with JSON output

Provides centralized logging configuration for Jarvis with:
- JSON format for easy parsing
- Severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Automatic log rotation
- Integration with Event Bus
- Environment-based verbosity
"""

import logging
import json
import time
import os
from typing import Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "source": record.name,
            "message": record.getMessage(),
            "file": record.filename,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add correlation_id if present in extra
        if hasattr(record, 'correlation_id'):
            log_data["correlation_id"] = record.correlation_id
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(
    log_file: str = "service.log",
    level: str = "INFO",
    format_type: str = "json",
    max_file_size_mb: int = 10,
    backup_count: int = 3
) -> logging.Logger:
    """
    Setup structured logging for Jarvis
    
    Args:
        log_file: Path to log file
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" or "text"
        max_file_size_mb: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured root logger
    """
    # Map string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    log_level = level_map.get(level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    max_bytes = max_file_size_mb * 1024 * 1024
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # Set formatter
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (always text format for readability)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(TextFormatter())
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class EventBusLogHandler(logging.Handler):
    """
    Log handler that publishes log records to Event Bus
    
    Allows log events to be tracked in the event system for debugging.
    """
    
    def __init__(self, event_bus):
        """
        Initialize handler
        
        Args:
            event_bus: EventBus instance to publish to
        """
        super().__init__()
        self.event_bus = event_bus
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to the Event Bus"""
        try:
            # Only publish WARNING and above to avoid spam
            if record.levelno >= logging.WARNING:
                self.event_bus.publish_sync(
                    "log.event",
                    {
                        "level": record.levelname,
                        "source": record.name,
                        "message": record.getMessage(),
                        "file": record.filename,
                        "line": record.lineno
                    },
                    source="logging"
                )
        except Exception:
            # Don't let logging errors crash the application
            pass


def add_event_bus_handler(event_bus):
    """
    Add Event Bus handler to root logger
    
    Args:
        event_bus: EventBus instance
    """
    logger = logging.getLogger()
    handler = EventBusLogHandler(event_bus)
    logger.addHandler(handler)
