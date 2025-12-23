# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Validation error messages for schema validation.

This module centralizes all validation error messages used across
Marshmallow schemas to ensure consistency and easier maintenance.
"""

from app.models.constants import DUMMY_DESCRIPTION_MAX_LENGTH, DUMMY_NAME_MAX_LENGTH

# Dummy model validation messages
DUMMY_NAME_EMPTY = "Name cannot be empty."
DUMMY_NAME_TOO_LONG = f"Name cannot exceed {DUMMY_NAME_MAX_LENGTH} characters."
DUMMY_NAME_NOT_UNIQUE = "Name must be unique."
DUMMY_DESCRIPTION_TOO_LONG = (
    f"Description cannot exceed {DUMMY_DESCRIPTION_MAX_LENGTH} characters."
)
