# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Application logger configuration.

This module configures the application logger using structlog and colorlog.
In development and testing environments, it sets up a colored log formatter
for improved readability in the console. In staging and production environments,
it switches to JSON logging for better integration with log aggregation tools.

Usage:
    from app.logger import logger
    logger.info("Your log message", extra_field="value")
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog
import structlog

# Detect environment
env = os.environ.get("FLASK_ENV", "development").lower()

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Configure handlers
handlers: list[logging.Handler] = []

# Console handler with color
console_handler = colorlog.StreamHandler()
console_handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(log_color)s[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d "
        "%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)
handlers.append(console_handler)

# File handler for JSON logs (always enabled for Loki/Promtail)
file_handler = RotatingFileHandler(
    log_dir / "guardian.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
# Simple format for file - structlog will handle JSON rendering
file_handler.setFormatter(logging.Formatter("%(message)s"))
handlers.append(file_handler)

# Set log level from LOG_LEVEL env var, default to INFO
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    log_level = "INFO"
logging.basicConfig(level=getattr(logging, log_level), handlers=handlers)

# Choose renderer based on environment
# For file logs, always use JSON for Loki/ELK
# For console, use colored output in dev/test
renderer: structlog.types.Processor
if env in ("development", "testing"):
    renderer = structlog.dev.ConsoleRenderer(colors=True)
else:
    renderer = structlog.processors.JSONRenderer()

# Configure structlog with dual processors for file (JSON) and console (colored)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Use JSONRenderer for all environments to ensure file logs are JSON
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
