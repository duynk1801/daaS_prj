"""
Logging configuration.
Detailed logs for developers, generic messages exposed to users.
Sensitive data (passwords, tokens) MUST NOT appear in logs.
"""
import logging
import logging.config
import sys
from typing import Any, Dict


def configure_logging(debug: bool = False) -> None:
    """
    Configure application-wide logging.

    Args:
        debug: If True, sets root logger to DEBUG level.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
            "detailed": {
                "format": (
                    "%(asctime)s [%(levelname)s] %(name)s "
                    "(%(filename)s:%(lineno)d): %(message)s"
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "standard",
                "level": log_level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
        "loggers": {
            # Suppress noisy third-party loggers in production
            "uvicorn.access": {
                "handlers": ["console"],
                "level": logging.INFO,
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": logging.WARNING if not debug else logging.INFO,
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
    logging.getLogger(__name__).info("Logging configured (debug=%s)", debug)
