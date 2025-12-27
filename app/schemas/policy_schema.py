# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for Policy model serialization and validation.

This module defines Marshmallow schemas for serializing and validating
Policy entities, including creation and update schemas with custom validation.
"""

import re

from marshmallow import EXCLUDE, ValidationError, fields, pre_load, validate, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.models.constants import (
    POLICY_DESCRIPTION_MAX_LENGTH,
    POLICY_DISPLAY_NAME_MAX_LENGTH,
    POLICY_NAME_MAX_LENGTH,
)
from app.models.policy import Policy
from app.schemas.constants import (
    POLICY_DESCRIPTION_TOO_LONG,
    POLICY_DISPLAY_NAME_EMPTY,
    POLICY_DISPLAY_NAME_TOO_LONG,
    POLICY_NAME_EMPTY,
    POLICY_NAME_INVALID_FORMAT,
    POLICY_NAME_TOO_LONG,
)


class PolicySchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for serializing Policy model instances.

    This schema provides automatic serialization/deserialization of Policy
    entities with read-only fields for id, timestamps, and company_id.

    Attributes:
        id: Unique UUID identifier (dump only).
        name: Technical name (lowercase, underscores).
        display_name: Human-readable display name.
        description: Optional detailed description.
        company_id: UUID of the owning company (dump only).
        priority: Evaluation priority (default 0).
        is_active: Whether the policy is active (default True).
        permissions_count: Count of attached permissions (dump only).
        created_at: Timestamp of creation (dump only).
        updated_at: Timestamp of last update (dump only).
    """

    permissions_count = fields.Int(dump_only=True)

    class Meta:
        """Marshmallow schema configuration options."""

        model = Policy
        load_instance = False
        include_fk = True
        dump_only = (
            "id",
            "company_id",
            "created_at",
            "updated_at",
            "permissions_count",
        )
        unknown = EXCLUDE


class PolicyCreateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for creating new Policy instances.

    Validates input for policy creation, ensuring required fields are present
    and properly formatted. Company ID is automatically extracted from JWT.

    Attributes:
        name: Technical name (required, lowercase with underscores).
        display_name: Human-readable display name (required).
        description: Optional detailed description.
        priority: Evaluation priority (optional, default 0).
    """

    name = fields.Str(
        required=True,
        validate=validate.Length(
            max=POLICY_NAME_MAX_LENGTH, error=POLICY_NAME_TOO_LONG
        ),
    )
    display_name = fields.Str(
        required=True,
        validate=validate.Length(
            max=POLICY_DISPLAY_NAME_MAX_LENGTH, error=POLICY_DISPLAY_NAME_TOO_LONG
        ),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=POLICY_DESCRIPTION_MAX_LENGTH, error=POLICY_DESCRIPTION_TOO_LONG
        ),
    )
    priority = fields.Int(
        required=False,
        load_default=0,
        validate=validate.Range(min=0, error="Priority must be >= 0"),
    )

    class Meta:
        """Marshmallow schema configuration options."""

        model = Policy
        load_instance = False
        include_fk = False
        exclude = ("id", "company_id", "is_active", "created_at", "updated_at")
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Strip whitespace from string fields before validation.

        Args:
            data: The input data dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            The modified data dictionary with stripped strings.
        """
        if "name" in data and isinstance(data["name"], str):
            data["name"] = data["name"].strip()
        if "display_name" in data and isinstance(data["display_name"], str):
            data["display_name"] = data["display_name"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        return data

    @validates("name")
    def validate_name(self, value, **kwargs):
        """Validate policy name format and uniqueness.

        Args:
            value: The name value to validate.
            **kwargs: Additional keyword arguments.

        Raises:
            ValidationError: If name is empty, invalid format, or not unique.
        """
        if not value or not value.strip():
            raise ValidationError(POLICY_NAME_EMPTY)

        # Validate format: lowercase letters and underscores only
        if not re.match(r"^[a-z_]+$", value):
            raise ValidationError(POLICY_NAME_INVALID_FORMAT)

    @validates("display_name")
    def validate_display_name(self, value, **kwargs):
        """Validate display_name is not empty.

        Args:
            value: The display_name value to validate.
            **kwargs: Additional keyword arguments.

        Raises:
            ValidationError: If display_name is empty.
        """
        if not value or not value.strip():
            raise ValidationError(POLICY_DISPLAY_NAME_EMPTY)


class PolicyUpdateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for updating existing Policy instances.

    Validates input for policy updates. All fields are optional.
    The technical name cannot be modified after creation.

    Attributes:
        display_name: Human-readable display name (optional).
        description: Detailed description (optional).
        priority: Evaluation priority (optional).
        is_active: Whether the policy is active (optional).
    """

    display_name = fields.Str(
        required=False,
        validate=validate.Length(
            max=POLICY_DISPLAY_NAME_MAX_LENGTH, error=POLICY_DISPLAY_NAME_TOO_LONG
        ),
    )
    description = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(
            max=POLICY_DESCRIPTION_MAX_LENGTH, error=POLICY_DESCRIPTION_TOO_LONG
        ),
    )
    priority = fields.Int(
        required=False,
        validate=validate.Range(min=0, error="Priority must be >= 0"),
    )
    is_active = fields.Bool(required=False)

    class Meta:
        """Marshmallow schema configuration options."""

        model = Policy
        load_instance = False
        include_fk = False
        exclude = ("id", "name", "company_id", "created_at", "updated_at")
        unknown = EXCLUDE

    @pre_load
    def strip_strings(self, data, **kwargs):
        """Strip whitespace from string fields before validation.

        Args:
            data: The input data dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            The modified data dictionary with stripped strings.
        """
        if "display_name" in data and isinstance(data["display_name"], str):
            data["display_name"] = data["display_name"].strip()
        if "description" in data and isinstance(data["description"], str):
            data["description"] = data["description"].strip()
        return data

    @validates("display_name")
    def validate_display_name(self, value, **kwargs):
        """Validate display_name is not empty if provided.

        Args:
            value: The display_name value to validate.
            **kwargs: Additional keyword arguments.

        Raises:
            ValidationError: If display_name is empty.
        """
        if value is not None and (not value or not value.strip()):
            raise ValidationError(POLICY_DISPLAY_NAME_EMPTY)
