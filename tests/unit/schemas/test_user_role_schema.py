# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for UserRole Marshmallow schemas."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from marshmallow import ValidationError

from app.models.user_role import UserRole
from app.schemas.user_role_schema import (
    UserRoleCreateSchema,
    UserRoleSchema,
    UserRoleUpdateSchema,
)


class TestUserRoleSchema:
    """Test cases for UserRoleSchema (read/serialization)."""

    def test_dump_user_role_instance(self, app, sample_company_id):
        """Test serializing a UserRole model instance."""
        with app.app_context():
            schema = UserRoleSchema()
            user_id = uuid.uuid4()
            role_id = uuid.uuid4()
            granted_by = uuid.uuid4()

            user_role = UserRole(
                user_id=str(user_id),
                role_id=str(role_id),
                company_id=str(sample_company_id),
                scope_type="direct",
                granted_by=str(granted_by),
                granted_at=datetime.now(UTC),
            )
            user_role.id = uuid.uuid4()
            user_role.created_at = datetime.now(UTC)
            user_role.updated_at = datetime.now(UTC)

            result = cast("dict", schema.dump(user_role))

            assert result["id"] == str(user_role.id)
            assert result["user_id"] == str(user_id)
            assert result["role_id"] == str(role_id)
            assert result["company_id"] == str(sample_company_id)
            assert result["scope_type"] == "direct"
            assert result["granted_by"] == str(granted_by)
            assert result["is_active"] is True
            assert "created_at" in result
            assert "updated_at" in result
            assert "granted_at" in result

    def test_dump_with_project_id(self, app, sample_company_id):
        """Test serializing user role with project scope."""
        with app.app_context():
            schema = UserRoleSchema()
            project_id = uuid.uuid4()

            user_role = UserRole(
                user_id=str(uuid.uuid4()),
                role_id=str(uuid.uuid4()),
                company_id=str(sample_company_id),
                project_id=str(project_id),
                scope_type="direct",
                granted_by=str(uuid.uuid4()),
                granted_at=datetime.now(UTC),
            )
            user_role.id = uuid.uuid4()

            result = cast("dict", schema.dump(user_role))

            assert result["project_id"] == str(project_id)

    def test_dump_with_expires_at(self, app, sample_company_id):
        """Test serializing user role with expiration."""
        with app.app_context():
            schema = UserRoleSchema()
            expires_at = datetime.now(UTC) + timedelta(days=30)

            user_role = UserRole(
                user_id=str(uuid.uuid4()),
                role_id=str(uuid.uuid4()),
                company_id=str(sample_company_id),
                scope_type="direct",
                granted_by=str(uuid.uuid4()),
                granted_at=datetime.now(UTC),
                expires_at=expires_at,
            )
            user_role.id = uuid.uuid4()

            result = schema.dump(user_role)

            assert "expires_at" in result

    def test_dump_only_fields_included(self, app, sample_company_id):
        """Test that dump_only fields are included in output."""
        with app.app_context():
            schema = UserRoleSchema()
            user_role = UserRole(
                user_id=str(uuid.uuid4()),
                role_id=str(uuid.uuid4()),
                company_id=str(sample_company_id),
                scope_type="direct",
                granted_by=str(uuid.uuid4()),
                granted_at=datetime.now(UTC),
            )
            user_role.id = uuid.uuid4()
            user_role.created_at = datetime.now(UTC)
            user_role.updated_at = datetime.now(UTC)

            result = schema.dump(user_role)

            assert "id" in result
            assert "user_id" in result
            assert "role_id" in result
            assert "company_id" in result
            assert "created_at" in result
            assert "updated_at" in result


class TestUserRoleCreateSchema:
    """Test cases for UserRoleCreateSchema (creation/POST requests)."""

    def test_load_valid_data(self, app):
        """Test loading valid user role creation data."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            role_id = uuid.uuid4()
            data = {
                "role_id": str(role_id),
                "scope_type": "direct",
            }

            result = schema.load(data)

            assert result["role_id"] == str(role_id)
            assert result["scope_type"] == "direct"

    def test_load_with_project_id(self, app):
        """Test loading with project_id."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            role_id = uuid.uuid4()
            project_id = uuid.uuid4()
            data = {
                "role_id": str(role_id),
                "project_id": str(project_id),
                "scope_type": "direct",
            }

            result = schema.load(data)

            assert result["role_id"] == str(role_id)
            assert result["project_id"] == str(project_id)

    def test_load_with_expires_at(self, app):
        """Test loading with expires_at."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            role_id = uuid.uuid4()
            expires_at = datetime.now(UTC) + timedelta(days=30)
            data = {
                "role_id": str(role_id),
                "scope_type": "direct",
                "expires_at": expires_at.isoformat(),
            }

            result = schema.load(data)

            assert result["role_id"] == str(role_id)
            assert "expires_at" in result

    def test_excluded_fields_not_in_result(self, app):
        """Test that excluded fields are not processed."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            data = {
                "role_id": str(uuid.uuid4()),
                "id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "company_id": str(uuid.uuid4()),
                "created_at": datetime.now(UTC).isoformat(),
            }

            result = schema.load(data)

            assert "id" not in result
            assert "user_id" not in result
            assert "company_id" not in result
            assert "created_at" not in result

    def test_role_id_required(self, app):
        """Test that role_id field is required."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            data = {
                "scope_type": "direct",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "role_id" in exc_info.value.messages

    def test_role_id_must_be_valid_uuid(self, app):
        """Test that role_id must be a valid UUID."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            data = {
                "role_id": "invalid-uuid",
                "scope_type": "direct",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "role_id" in exc_info.value.messages

    def test_scope_type_direct(self, app):
        """Test that scope_type accepts 'direct' value."""
        with app.app_context():
            schema = UserRoleCreateSchema()
            data = {
                "role_id": str(uuid.uuid4()),
                "scope_type": "direct",
            }

            result = schema.load(data)
            assert result["scope_type"] == "direct"


class TestUserRoleUpdateSchema:
    """Test cases for UserRoleUpdateSchema (update/PATCH requests)."""

    def test_load_valid_data(self, app):
        """Test loading valid user role update data."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            data = {
                "scope_type": "hierarchical",
                "is_active": False,
            }

            result = schema.load(data)

            assert result["scope_type"] == "hierarchical"
            assert result["is_active"] is False

    def test_partial_update_support(self, app):
        """Test that partial updates are supported."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            data = {
                "is_active": False,
            }

            result = schema.load(data)

            assert result["is_active"] is False
            assert "scope_type" not in result
            assert "expires_at" not in result

    def test_all_fields_optional(self, app):
        """Test that all fields are optional for updates."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            data: dict = {}

            result = schema.load(data)

            assert result == {}

    def test_excluded_fields_not_in_result(self, app):
        """Test that excluded fields are not processed."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            data = {
                "is_active": False,
                "id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
                "role_id": str(uuid.uuid4()),
                "company_id": str(uuid.uuid4()),
            }

            result = schema.load(data)

            assert "id" not in result
            assert "user_id" not in result
            assert "role_id" not in result
            assert "company_id" not in result

    def test_update_project_id(self, app):
        """Test updating project_id."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            project_id = uuid.uuid4()
            data = {
                "project_id": str(project_id),
            }

            result = schema.load(data)

            assert result["project_id"] == str(project_id)

    def test_update_expires_at(self, app):
        """Test updating expires_at."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            expires_at = datetime.now(UTC) + timedelta(days=60)
            data = {
                "expires_at": expires_at.isoformat(),
            }

            result = schema.load(data)

            assert "expires_at" in result

    def test_update_scope_type(self, app):
        """Test updating scope_type."""
        with app.app_context():
            schema = UserRoleUpdateSchema()
            data = {
                "scope_type": "hierarchical",
            }

            result = schema.load(data)

            assert result["scope_type"] == "hierarchical"
