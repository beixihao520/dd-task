"""Logging configuration for DD Agent."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

# Global console instance for rich output
console = Console()


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Set up logging with Rich handler for console output.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional file path for logging

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("dd_agent")
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Add Rich console handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(level)
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Optional name for the logger (will be prefixed with 'dd_agent.')

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"dd_agent.{name}")
    return logging.getLogger("dd_agent")


# Default logger setup
def init_default_logging() -> None:
    """Initialize default logging configuration."""
    setup_logging(level=logging.INFO)
