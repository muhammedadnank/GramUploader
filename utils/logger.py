import logging
from logging.handlers import RotatingFileHandler
import sys


def setup_logger(name: str = "gramuploader") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Rotating file (5MB x 3 backups)
    try:
        file_handler = RotatingFileHandler(
            "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except Exception:
        pass  # Skip file logging if not writable (Railway etc.)

    return logger


log = setup_logger()
