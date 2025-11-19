"""Logging configuration helpers."""

from __future__ import annotations

import logging
import logging.config
from typing import Any

from fly_search.config import get_settings


def get_logging_config() -> dict[str, Any]:
    """
    Get logging configuration based on settings.

    Returns:
        Logging configuration dictionary
    """
    settings = get_settings()
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)s | %(name)s | pid=%(pid)s | %(message)s",
            },
        },
        "filters": {
            "pid": {
                "()": "fly_search.logging_config.ProcessIdFilter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["pid"],
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
    }


class ProcessIdFilter(logging.Filter):
    """Ensure `pid` key is always available in log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "pid"):
            record.pid = "-"
        return True


def configure_logging(config: dict[str, Any] | None = None) -> None:
    """
    Apply logging configuration once.

    Args:
        config: Optional logging configuration dict. If None, uses config from settings.
    """
    if config is None:
        config = get_logging_config()
    logging.config.dictConfig(config)
