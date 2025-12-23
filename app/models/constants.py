# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Database model constants for field sizes and constraints.

This module centralizes all database field size constraints used across
SQLAlchemy models to ensure consistency and easier maintenance.
"""

# Dummy model field lengths
DUMMY_NAME_MAX_LENGTH = 50
DUMMY_DESCRIPTION_MAX_LENGTH = 200

# Pagination constants
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
