# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Application logger configuration.

This module configures the application logger using structlog.
In development and testing environments, console output uses colored formatting
for improved readability. In staging and production environments, console output
switches to JSON logging. File logs always use JSON format for better integration
with log aggregation tools like Loki, Promtail, and ELK stack.

Usage:
    from app.utils.logger import logger
    logger.info("Your log message", extra_field="value")
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

# Detect environment
env = os.environ.get("FLASK_ENV", "development").lower()

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Choose console renderer based on environment
# For console, use colored output in dev/test, JSON in production
console_renderer: structlog.types.Processor
if env in ("development", "testing"):
    console_renderer = structlog.dev.ConsoleRenderer(colors=True)
else:
    console_renderer = structlog.processors.JSONRenderer()

# Common processors for both handlers
shared_processors = [
    structlog.stdlib.filter_by_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
]

# Configure handlers
handlers: list[logging.Handler] = []

# Console handler with environment-specific formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    structlog.stdlib.ProcessorFormatter(
        processor=console_renderer,
        foreign_pre_chain=shared_processors,
    )
)
handlers.append(console_handler)

# File handler for JSON logs (always enabled for Loki/Promtail)
file_handler = RotatingFileHandler(
    log_dir / "guardian.log",
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
)
file_handler.setFormatter(
    structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
)
handlers.append(file_handler)

# Set log level from LOG_LEVEL env var, default to INFO
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    log_level = "INFO"
logging.basicConfig(level=getattr(logging, log_level), handlers=handlers)

# Configure structlog with processors that prepare data for the formatters
structlog.configure(
    processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
