# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Utility modules for the application.

This package contains utility functions and classes used throughout the application:
- constants: Application-wide constants and error messages
- jwt_utils: JWT authentication utilities and decorators
- limiter: Flask-Limiter instance for rate limiting
- logger: Structured logging configuration
"""

from app.utils.guardian import Operation, access_required
from app.utils.jwt_utils import require_jwt_auth
from app.utils.limiter import limiter
from app.utils.logger import logger

__all__ = [
    # JWT utilities
    "require_jwt_auth",
    # Guardian
    "access_required",
    "Operation",
    # Rate limiting
    "limiter",
    # Logging
    "logger",
]
