# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for UserRole model serialization and validation.

This module defines Marshmallow schemas for serializing and validating
UserRole entities, including creation and update schemas.
"""

from datetime import UTC, datetime

from marshmallow import EXCLUDE, ValidationError, fields, post_load, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from app.models.user_role import UserRole


class UserRoleSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for serializing UserRole model instances.

    This schema provides automatic serialization/deserialization of UserRole
    entities with read-only fields for id, timestamps, and identifiers.

    Attributes:
        id: Unique UUID identifier (dump only).
        user_id: User ID receiving the role (dump only).
        role_id: Role ID being assigned (dump only).
        company_id: Company scope (dump only).
        project_id: Optional project scope.
        scope_type: Access scope ('direct' or 'hierarchical').
        granted_by: User who granted this role.
        granted_at: Timestamp of grant.
        expires_at: Optional expiration timestamp.
        is_active: Whether the assignment is active.
        created_at: Record creation timestamp (dump only).
        updated_at: Last modification timestamp (dump only).
    """

    class Meta:
        """Marshmallow schema configuration options."""

        model = UserRole
        load_instance = False
        include_fk = True
        dump_only = (
            "id",
            "user_id",
            "company_id",
            "granted_at",
            "created_at",
            "updated_at",
        )
        unknown = EXCLUDE


class UserRoleCreateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for creating new UserRole instances.

    Validates input for role assignment, ensuring required fields are present.
    user_id and company_id are automatically extracted from path and JWT.

    Attributes:
        role_id: Role to assign (required).
        project_id: Optional project scope (NULL = company-wide).
        scope_type: Access scope ('direct' or 'hierarchical', default 'direct').
        expires_at: Optional expiration date.
    """

    role_id = fields.UUID(required=True)
    project_id = fields.UUID(required=False, allow_none=True)
    scope_type = fields.Str(
        required=False,
        load_default="direct",
        validate=lambda x: x in ("direct", "hierarchical"),
    )
    expires_at = fields.DateTime(required=False, allow_none=True)

    class Meta:
        """Marshmallow schema configuration options."""

        model = UserRole
        load_instance = False
        include_fk = False
        exclude = (
            "id",
            "user_id",
            "company_id",
            "granted_by",
            "granted_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        unknown = EXCLUDE

    @validates("scope_type")
    def validate_scope_type(self, value: str) -> None:
        """Validate scope_type is either 'direct' or 'hierarchical'.

        Args:
            value: Scope type to validate.

        Raises:
            ValidationError: If scope_type is invalid.
        """
        if value not in ("direct", "hierarchical"):
            raise ValidationError(
                "scope_type must be either 'direct' or 'hierarchical'"
            )

    @validates("expires_at")
    def validate_expires_at(self, value: datetime) -> None:
        """Validate expiration date is in the future.

        Args:
            value: Expiration datetime to validate.

        Raises:
            ValidationError: If expires_at is in the past.
        """
        if value and value <= datetime.now(UTC):
            raise ValidationError("expires_at must be in the future")

    @post_load
    def convert_uuids_to_strings(self, data: dict, **kwargs) -> dict:
        """Convert UUID objects to strings for database insertion.

        Args:
            data: Validated data dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            Data with UUIDs converted to strings.
        """
        if "role_id" in data:
            data["role_id"] = str(data["role_id"])
        if "project_id" in data and data["project_id"] is not None:
            data["project_id"] = str(data["project_id"])
        return data


class UserRoleUpdateSchema(SQLAlchemyAutoSchema):
    """Marshmallow schema for updating UserRole instances.

    Allows updating scope (project_id, scope_type), expiration, and active status.
    user_id and role_id cannot be modified.

    Attributes:
        project_id: Optional project scope.
        scope_type: Access scope ('direct' or 'hierarchical').
        expires_at: Optional expiration date.
        is_active: Whether the assignment is active.
    """

    project_id = fields.UUID(required=False, allow_none=True)
    scope_type = fields.Str(
        required=False,
        validate=lambda x: x in ("direct", "hierarchical"),
    )
    expires_at = fields.DateTime(required=False, allow_none=True)
    is_active = fields.Bool(required=False)

    class Meta:
        """Marshmallow schema configuration options."""

        model = UserRole
        load_instance = False
        include_fk = False
        exclude = (
            "id",
            "user_id",
            "role_id",
            "company_id",
            "granted_by",
            "granted_at",
            "created_at",
            "updated_at",
        )
        unknown = EXCLUDE

    @validates("scope_type")
    def validate_scope_type(self, value: str) -> None:
        """Validate scope_type is either 'direct' or 'hierarchical'.

        Args:
            value: Scope type to validate.

        Raises:
            ValidationError: If scope_type is invalid.
        """
        if value not in ("direct", "hierarchical"):
            raise ValidationError(
                "scope_type must be either 'direct' or 'hierarchical'"
            )

    @validates("expires_at")
    def validate_expires_at(self, value: datetime) -> None:
        """Validate expiration date is in the future if being set.

        Args:
            value: Expiration datetime to validate.

        Raises:
            ValidationError: If expires_at is in the past.
        """
        if value and value <= datetime.now(UTC):
            raise ValidationError("expires_at must be in the future")

    @post_load
    def convert_uuids_to_strings(self, data: dict, **kwargs) -> dict:
        """Convert UUID objects to strings for database updates.

        Args:
            data: Validated data dictionary.
            **kwargs: Additional keyword arguments.

        Returns:
            Data with UUIDs converted to strings.
        """
        if "project_id" in data and data["project_id"] is not None:
            data["project_id"] = str(data["project_id"])
        return data
