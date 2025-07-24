import logging
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "flock", log_level: str = "INFO") -> logging.Logger:
    """Set up a logger with file and console output"""
    logger = logging.getLogger(name)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.NullHandler()
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    # Console handler setup
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level.upper())
    console_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

    return logger


logger = setup_logger()
