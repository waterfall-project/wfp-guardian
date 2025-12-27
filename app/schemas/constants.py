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

from app.models.constants import (
    DUMMY_DESCRIPTION_MAX_LENGTH,
    DUMMY_NAME_MAX_LENGTH,
    POLICY_DESCRIPTION_MAX_LENGTH,
    POLICY_DISPLAY_NAME_MAX_LENGTH,
    POLICY_NAME_MAX_LENGTH,
    ROLE_DESCRIPTION_MAX_LENGTH,
    ROLE_DISPLAY_NAME_MAX_LENGTH,
    ROLE_NAME_MAX_LENGTH,
)

# Dummy model validation messages
DUMMY_NAME_EMPTY = "Name cannot be empty."
DUMMY_NAME_TOO_LONG = f"Name cannot exceed {DUMMY_NAME_MAX_LENGTH} characters."
DUMMY_NAME_NOT_UNIQUE = "Name must be unique."
DUMMY_DESCRIPTION_TOO_LONG = (
    f"Description cannot exceed {DUMMY_DESCRIPTION_MAX_LENGTH} characters."
)

# Policy model validation messages
POLICY_NAME_EMPTY = "Name cannot be empty."
POLICY_NAME_TOO_LONG = f"Name cannot exceed {POLICY_NAME_MAX_LENGTH} characters."
POLICY_NAME_INVALID_FORMAT = (
    "Name must contain only lowercase letters and underscores (a-z, _)."
)
POLICY_NAME_NOT_UNIQUE = "Policy name must be unique within the company."
POLICY_DISPLAY_NAME_EMPTY = "Display name cannot be empty."
POLICY_DISPLAY_NAME_TOO_LONG = (
    f"Display name cannot exceed {POLICY_DISPLAY_NAME_MAX_LENGTH} characters."
)
POLICY_DESCRIPTION_TOO_LONG = (
    f"Description cannot exceed {POLICY_DESCRIPTION_MAX_LENGTH} characters."
)

# Role model validation messages
ROLE_NAME_EMPTY = "Name cannot be empty."
ROLE_NAME_TOO_LONG = f"Name cannot exceed {ROLE_NAME_MAX_LENGTH} characters."
ROLE_NAME_INVALID_FORMAT = (
    "Name must contain only lowercase letters and underscores (a-z, _)."
)
ROLE_NAME_NOT_UNIQUE = "Role name must be unique within the company."
ROLE_DISPLAY_NAME_EMPTY = "Display name cannot be empty."
ROLE_DISPLAY_NAME_TOO_LONG = (
    f"Display name cannot exceed {ROLE_DISPLAY_NAME_MAX_LENGTH} characters."
)
ROLE_DESCRIPTION_TOO_LONG = (
    f"Description cannot exceed {ROLE_DESCRIPTION_MAX_LENGTH} characters."
)
