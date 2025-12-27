# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for Role model serialization and validation.

This module defines Marshmallow schemas for serializing and validating
Role entities, including creation and update schemas with custom validation.
"""

import re

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.models.constants import (
    ROLE_DESCRIPTION_MAX_LENGTH,
    ROLE_DISPLAY_NAME_MAX_LENGTH,
    ROLE_NAME_MAX_LENGTH,
)
from app.models.role import Role
from app.schemas.constants import (
    ROLE_DESCRIPTION_TOO_LONG,
    ROLE_DISPLAY_NAME_EMPTY,
    ROLE_DISPLAY_NAME_TOO_LONG,
    ROLE_NAME_EMPTY,
    ROLE_NAME_INVALID_FORMAT,
    ROLE_NAME_TOO_LONG,
)


class RoleSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for serializing Role model instances.

    This schema provides automatic serialization/deserialization of Role
    entities with read-only fields for id, timestamps, and company_id.

    Attributes:
        id: Unique UUID identifier (dump only).
        name: Technical name (lowercase, underscores).
        display_name: Human-readable display name.
        description: Optional detailed description.
        company_id: UUID of the owning company (dump only).
        priority: Evaluation priority (default 0).
        is_active: Whether the role is active (default True).
        policies_count: Count of attached policies (dump only).
        created_at: Timestamp of creation (dump only).
        updated_at: Timestamp of last update (dump only).
    """

    policies_count = fields.Int(dump_only=True)

    class Meta:
        """Marshmallow schema configuration options."""

        model = Role
        load_instance = False
        include_fk = True
        dump_only = (
            "id",
            "company_id",
            "created_at",
            "updated_at",
            "policies_count",
        )
        unknown = EXCLUDE


class RoleCreateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for creating new Role instances.

    Validates input for role creation, ensuring required fields are present
    and properly formatted. Company ID is automatically extracted from JWT.

    Attributes:
        name: Technical name (required, lowercase with underscores).
        display_name: Human-readable display name (required).
        description: Optional detailed description.
        priority: Evaluation priority (optional, default 0).
    """

    name = fields.Str(
        required=True,
        validate=validate.Length(max=ROLE_NAME_MAX_LENGTH, error=ROLE_NAME_TOO_LONG),
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(
            max=ROLE_DISPLAY_NAME_MAX_LENGTH, error=ROLE_DISPLAY_NAME_TOO_LONG
        ),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=ROLE_DESCRIPTION_MAX_LENGTH, error=ROLE_DESCRIPTION_TOO_LONG
        ),
    )
    priority = fields.Int(required=False, load_default=0)

    class Meta:
        """Marshmallow schema configuration options."""

        model = Role
        load_instance = False
        include_fk = False
        exclude = ("id", "company_id", "created_at", "updated_at", "is_active")
        unknown = EXCLUDE

    @pre_load
    def preprocess_fields(self, data: dict, **kwargs) -> dict:
        """Preprocess data before validation.

        - Strips whitespace from name and display_name
        - Strips whitespace from description if present and is a string

        Args:
            data: Input data dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            Preprocessed data dictionary.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()

        if "display_name" in data and isinstance(data["display_name"], str):
            data["display_name"] = data["display_name"].strip()

        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()

        return data

    @validates("name")
    def validate_name(self, value: str) -> None:
        """Validate role name format and uniqueness.

        Rules:
        - Cannot be empty or whitespace
        - Must be lowercase with underscores only
        - Must be unique per company (checked via database)

        Args:
            value: Role name to validate.

        Raises:
            ValidationError: If name format is invalid or already exists.
        """
        if not value or not value.strip():
            raise ValidationError(ROLE_NAME_EMPTY)

        # Validate format: lowercase letters, numbers, underscores
        if not re.match(r"^[a-z0-9_]+$", value):
            raise ValidationError(ROLE_NAME_INVALID_FORMAT)

        # Check uniqueness will be done at the resource level with company_id

    @validates("display_name")
    def validate_display_name(self, value: str) -> None:
        """Validate role display name.

        Rules:
        - Cannot be empty or whitespace

        Args:
            value: Display name to validate.

        Raises:
            ValidationError: If display name is empty or whitespace.
        """
        if not value or not value.strip():
            raise ValidationError(ROLE_DISPLAY_NAME_EMPTY)


class RoleUpdateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for updating existing Role instances.

    All fields are optional for partial updates. Validates format when provided.

    Attributes:
        name: Technical name (optional, lowercase with underscores).
        display_name: Human-readable display name (optional).
        description: Optional detailed description.
        priority: Evaluation priority (optional).
        is_active: Whether the role is active (optional).
    """

    name = fields.Str(
        required=False,
        validate=validate.Length(max=ROLE_NAME_MAX_LENGTH, error=ROLE_NAME_TOO_LONG),
    )
    display_name = fields.Str(
        required=False,
        validate=validate.Length(
            max=ROLE_DISPLAY_NAME_MAX_LENGTH, error=ROLE_DISPLAY_NAME_TOO_LONG
        ),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=ROLE_DESCRIPTION_MAX_LENGTH, error=ROLE_DESCRIPTION_TOO_LONG
        ),
    )
    priority = fields.Int(required=False)
    is_active = fields.Bool(required=False)

    class Meta:
        """Marshmallow schema configuration options."""

        model = Role
        load_instance = False
        include_fk = False
        exclude = ("id", "company_id", "created_at", "updated_at")
        unknown = EXCLUDE

    @pre_load
    def preprocess_fields(self, data: dict, **kwargs) -> dict:
        """Preprocess data before validation.

        - Strips whitespace from name and display_name if present
        - Strips whitespace from description if present and is a string

        Args:
            data: Input data dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            Preprocessed data dictionary.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()

        if "display_name" in data and isinstance(data["display_name"], str):
            data["display_name"] = data["display_name"].strip()

        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()

        return data

    @validates("name")
    def validate_name(self, value: str) -> None:
        """Validate role name format.

        Rules:
        - Cannot be empty or whitespace
        - Must be lowercase with underscores only

        Args:
            value: Role name to validate.

        Raises:
            ValidationError: If name format is invalid.
        """
        if not value or not value.strip():
            raise ValidationError(ROLE_NAME_EMPTY)

        # Validate format: lowercase letters, numbers, underscores
        if not re.match(r"^[a-z0-9_]+$", value):
            raise ValidationError(ROLE_NAME_INVALID_FORMAT)

    @validates("display_name")
    def validate_display_name(self, value: str) -> None:
        """Validate role display name.

        Rules:
        - Cannot be empty or whitespace

        Args:
            value: Display name to validate.

        Raises:
            ValidationError: If display name is empty or whitespace.
        """
        if not value or not value.strip():
            raise ValidationError(ROLE_DISPLAY_NAME_EMPTY)
