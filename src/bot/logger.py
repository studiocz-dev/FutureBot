"""
Structured logging module for the Wyckoff-Elliott Discord bot.

Provides JSON-formatted logging with structured fields for better observability.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from logging import LogRecord

from .config import config


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "symbol"):
            log_data["symbol"] = record.symbol
        if hasattr(record, "timeframe"):
            log_data["timeframe"] = record.timeframe
        if hasattr(record, "signal_type"):
            log_data["signal_type"] = record.signal_type
        if hasattr(record, "confidence"):
            log_data["confidence"] = record.confidence
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""
    
    def __init__(self):
        """Initialize text formatter."""
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with the configured format and level.
    
    Args:
        name: Logger name (typically __name__)
        level: Optional log level override
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    log_level = level or config.log.level
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level))
    
    # Set formatter based on config
    if config.log.format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds contextual information to log records.
    
    Usage:
        logger = LoggerAdapter(get_logger(__name__), {"symbol": "BTCUSDT"})
        logger.info("Processing candle")  # Will include symbol in structured logs
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Add extra context to log records."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


# Module-level logger for this file
logger = get_logger(__name__)
