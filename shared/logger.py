"""
Shared Logging Configuration for MediaGrab.
"""

import logging
import sys
from pathlib import Path


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Configures and returns a standardized logger.
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Standard Format: [2024-04-08 16:30:00] [INFO] [backend.main]: Message
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional: File Handler for critical errors in the user's home dir
    try:
        log_dir = Path.home() / ".mediagrab" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / f"{name.split('.')[0]}.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Silently fail if we can't write to home dir
        pass

    return logger
