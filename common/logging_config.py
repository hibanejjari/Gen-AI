"""
Logging configuration for LLM Council.
Provides structured logging with clear formatting for demo visibility.
"""

import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record):
        # Add color based on level
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Build message
        prefix = f"{color}{self.BOLD}[{timestamp}] [{record.levelname:8}]{self.RESET}"
        
        # Add component name if available
        component = getattr(record, 'component', None)
        if component:
            prefix += f" {self.BOLD}[{component}]{self.RESET}"
        
        return f"{prefix} {record.getMessage()}"


def setup_logging(
    level: str = "INFO",
    component: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for a component.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        component: Name of the component (e.g., "orchestrator", "council-1")
        log_file: Optional file path for logging
    
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(component or "llm-council")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter to add component name to log records."""
    
    def process(self, msg, kwargs):
        kwargs.setdefault('extra', {})
        kwargs['extra']['component'] = self.extra.get('component', 'unknown')
        return msg, kwargs


def get_logger(component: str) -> LoggerAdapter:
    """Get a logger adapter for a specific component."""
    logger = logging.getLogger("llm-council")
    return LoggerAdapter(logger, {'component': component})
