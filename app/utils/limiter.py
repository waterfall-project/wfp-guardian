# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Flask-Limiter instance for rate limiting.

This module provides a centralized limiter instance that can be imported
throughout the application to apply rate limiting to routes and resources.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize the limiter with default configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # No default limits, we'll apply per-route limits
)

__all__ = ["limiter"]
