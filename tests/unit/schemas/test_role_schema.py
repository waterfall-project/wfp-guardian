# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Role Marshmallow schemas."""

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from marshmallow import ValidationError

from app.models.constants import (
    ROLE_DESCRIPTION_MAX_LENGTH,
    ROLE_DISPLAY_NAME_MAX_LENGTH,
    ROLE_NAME_MAX_LENGTH,
)
from app.models.db import db
from app.models.role import Role
from app.schemas.constants import (
    ROLE_DESCRIPTION_TOO_LONG,
    ROLE_DISPLAY_NAME_EMPTY,
    ROLE_DISPLAY_NAME_TOO_LONG,
    ROLE_NAME_EMPTY,
    ROLE_NAME_IMMUTABLE,
    ROLE_NAME_INVALID_FORMAT,
    ROLE_NAME_TOO_LONG,
)
from app.schemas.role_schema import RoleCreateSchema, RoleSchema, RoleUpdateSchema


class TestRoleSchema:
    """Test cases for RoleSchema (read/serialization)."""

    def test_dump_role_instance(self, app, sample_company_id):
        """Test serializing a Role model instance."""
        with app.app_context():
            schema = RoleSchema()
            role = Role(
                name="test_role",
                display_name="Test Role",
                description="Test description",
                company_id=sample_company_id,
                is_active=True,
            )
            role.id = uuid.uuid4()
            role.created_at = datetime.now(UTC)
            role.updated_at = datetime.now(UTC)

            result = cast("dict", schema.dump(role))

            assert result["id"] == str(role.id)
            assert result["name"] == "test_role"
            assert result["display_name"] == "Test Role"
            assert result["description"] == "Test description"
            assert result["company_id"] == str(sample_company_id)
            assert result["is_active"] is True
            assert "created_at" in result
            assert "updated_at" in result

    def test_dump_with_policies_count(self, app, sample_company_id):
        """Test serializing role with policies_count."""
        with app.app_context():
            db.create_all()
            schema = RoleSchema()
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            result = cast("dict", schema.dump(role))

            assert "policies_count" in result
            assert result["policies_count"] == 0

            db.session.remove()
            db.drop_all()

    def test_dump_only_fields_included(self, app, sample_company_id):
        """Test that dump_only fields are included in output."""
        with app.app_context():
            schema = RoleSchema()
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            role.id = uuid.uuid4()
            role.created_at = datetime.now(UTC)
            role.updated_at = datetime.now(UTC)

            result = schema.dump(role)

            assert "id" in result
            assert "company_id" in result
            assert "created_at" in result
            assert "updated_at" in result
            assert "policies_count" in result


class TestRoleCreateSchema:
    """Test cases for RoleCreateSchema (creation/POST requests)."""

    def test_load_valid_data(self, app):
        """Test loading valid role creation data."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "admin_role",
                "display_name": "Administrator Role",
                "description": "Full admin permissions",
            }

            result = schema.load(data)

            assert result["name"] == "admin_role"
            assert result["display_name"] == "Administrator Role"
            assert result["description"] == "Full admin permissions"

    def test_excluded_fields_not_in_result(self, app):
        """Test that excluded fields are not processed."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "test_role",
                "display_name": "Test Role",
                "id": str(uuid.uuid4()),
                "company_id": str(uuid.uuid4()),
                "created_at": datetime.now(UTC).isoformat(),
            }

            result = schema.load(data)

            assert "id" not in result
            assert "company_id" not in result
            assert "created_at" not in result

    def test_name_required(self, app):
        """Test that name field is required."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "display_name": "Test Role",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "name" in exc_info.value.messages

    def test_name_cannot_be_empty(self, app):
        """Test that name cannot be empty string."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "",
                "display_name": "Test Role",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)

            assert "name" in exc_info.value.messages
            assert ROLE_NAME_EMPTY in messages["name"]

    def test_name_cannot_be_whitespace(self, app):
        """Test that name cannot be only whitespace."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "   ",
                "display_name": "Test Role",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "name" in exc_info.value.messages

    def test_name_invalid_format(self, app):
        """Test that name must be lowercase with underscores."""
        with app.app_context():
            schema = RoleCreateSchema()
            invalid_names = ["TestRole", "test-role", "test.role", "Test_Role"]

            for invalid_name in invalid_names:
                data = {
                    "name": invalid_name,
                    "display_name": "Test Role",
                }

                with pytest.raises(ValidationError) as exc_info:
                    schema.load(data)

                messages = cast("dict[str, list[str]]", exc_info.value.messages)
                assert "name" in exc_info.value.messages
                assert ROLE_NAME_INVALID_FORMAT in messages["name"]

    def test_name_max_length_validation(self, app):
        """Test name maximum length validation."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "a" * (ROLE_NAME_MAX_LENGTH + 1),
                "display_name": "Test Role",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)
            assert "name" in exc_info.value.messages
            assert ROLE_NAME_TOO_LONG in messages["name"]

    def test_name_exactly_max_length(self, app):
        """Test name at exactly max length is valid."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "a" * ROLE_NAME_MAX_LENGTH,
                "display_name": "Test Role",
            }

            result = schema.load(data)

            assert len(result["name"]) == ROLE_NAME_MAX_LENGTH

    def test_display_name_required(self, app):
        """Test that display_name field is required."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "test_role",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "display_name" in exc_info.value.messages

    def test_display_name_cannot_be_empty(self, app):
        """Test that display_name cannot be empty string."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "test_role",
                "display_name": "",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)
            assert "display_name" in messages
            assert ROLE_DISPLAY_NAME_EMPTY in messages["display_name"]

    def test_display_name_max_length_validation(self, app):
        """Test display_name maximum length validation."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "test_role",
                "display_name": "A" * (ROLE_DISPLAY_NAME_MAX_LENGTH + 1),
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)
            assert "display_name" in messages
            assert ROLE_DISPLAY_NAME_TOO_LONG in messages["display_name"]

    def test_description_optional(self, app):
        """Test that description is optional."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "test_role",
                "display_name": "Test Role",
            }

            result = schema.load(data)

            assert "description" not in result or result.get("description") is None

    def test_description_max_length_validation(self, app):
        """Test description maximum length validation."""
        with app.app_context():
            schema = RoleCreateSchema()
            data = {
                "name": "test_role",
                "display_name": "Test Role",
                "description": "x" * (ROLE_DESCRIPTION_MAX_LENGTH + 1),
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)
            assert "description" in messages
            assert ROLE_DESCRIPTION_TOO_LONG in messages["description"]


class TestRoleUpdateSchema:
    """Test cases for RoleUpdateSchema (update/PATCH requests)."""

    def test_load_valid_data(self, app):
        """Test loading valid role update data."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data = {
                "display_name": "Updated Role",
                "description": "Updated description",
                "is_active": False,
            }

            result = schema.load(data)

            assert result["display_name"] == "Updated Role"
            assert result["description"] == "Updated description"
            assert result["is_active"] is False

    def test_partial_update_support(self, app):
        """Test that partial updates are supported."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data = {
                "display_name": "Updated Role",
            }

            result = schema.load(data)

            assert result["display_name"] == "Updated Role"
            assert "description" not in result
            assert "is_active" not in result

    def test_all_fields_optional(self, app):
        """Test that all fields are optional for updates."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data: dict[str, str] = {}

            result = schema.load(data)

            assert result == {}

    def test_excluded_fields_not_in_result(self, app):
        """Test that excluded fields are not processed."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data = {
                "display_name": "Updated Role",
                "id": str(uuid.uuid4()),
                "company_id": str(uuid.uuid4()),
            }

            result = schema.load(data)

            assert "id" not in result
            assert "company_id" not in result
            assert "display_name" in result

    def test_immutable_name_field_raises_error(self, app):
        """Test that attempting to modify name field raises ValidationError."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data = {
                "display_name": "Updated Role",
                "name": "should_be_rejected",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)
            assert "name" in messages
            assert ROLE_NAME_IMMUTABLE in str(messages["name"])

    def test_display_name_validation(self, app):
        """Test display_name validation in updates."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data = {
                "display_name": "",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "display_name" in exc_info.value.messages

    def test_description_max_length_validation(self, app):
        """Test description maximum length validation."""
        with app.app_context():
            schema = RoleUpdateSchema()
            data = {
                "description": "x" * (ROLE_DESCRIPTION_MAX_LENGTH + 1),
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "description" in exc_info.value.messages
