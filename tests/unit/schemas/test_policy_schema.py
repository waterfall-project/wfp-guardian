# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Policy Marshmallow schemas."""

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from marshmallow import ValidationError

from app.models.constants import (
    POLICY_DESCRIPTION_MAX_LENGTH,
    POLICY_DISPLAY_NAME_MAX_LENGTH,
    POLICY_NAME_MAX_LENGTH,
)
from app.models.db import db
from app.models.policy import Policy
from app.schemas.constants import (
    POLICY_DESCRIPTION_TOO_LONG,
    POLICY_DISPLAY_NAME_EMPTY,
    POLICY_DISPLAY_NAME_TOO_LONG,
    POLICY_NAME_EMPTY,
    POLICY_NAME_IMMUTABLE,
    POLICY_NAME_INVALID_FORMAT,
    POLICY_NAME_TOO_LONG,
)
from app.schemas.policy_schema import (
    PolicyCreateSchema,
    PolicySchema,
    PolicyUpdateSchema,
)


class TestPolicySchema:
    """Test cases for PolicySchema (read/serialization)."""

    def test_dump_policy_instance(self, app, sample_company_id):
        """Test serializing a Policy model instance."""
        with app.app_context():
            schema = PolicySchema()
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                description="Test description",
                company_id=sample_company_id,
                priority=10,
            )
            policy.id = uuid.uuid4()
            policy.created_at = datetime.now(UTC)
            policy.updated_at = datetime.now(UTC)

            result = cast("dict", schema.dump(policy))

            assert result["id"] == str(policy.id)
            assert result["name"] == "test_policy"
            assert result["display_name"] == "Test Policy"
            assert result["description"] == "Test description"
            assert result["company_id"] == str(sample_company_id)
            assert result["priority"] == 10
            assert result["is_active"] is True
            assert "created_at" in result
            assert "updated_at" in result

    def test_dump_with_permissions_count(self, app, sample_company_id):
        """Test serializing policy with permissions_count."""
        with app.app_context():
            db.create_all()
            schema = PolicySchema()
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            result = cast("dict", schema.dump(policy))

            assert "permissions_count" in result
            assert result["permissions_count"] == 0

            db.session.remove()
            db.drop_all()

    def test_dump_only_fields_included(self, app, sample_company_id):
        """Test that dump_only fields are included in output."""
        with app.app_context():
            schema = PolicySchema()
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            policy.id = uuid.uuid4()
            policy.created_at = datetime.now(UTC)
            policy.updated_at = datetime.now(UTC)

            result = cast("dict", schema.dump(policy))

            assert "id" in result
            assert "company_id" in result
            assert "created_at" in result
            assert "updated_at" in result
            assert "permissions_count" in result


class TestPolicyCreateSchema:
    """Test cases for PolicyCreateSchema (creation/POST requests)."""

    def test_load_valid_data(self, app):
        """Test loading valid policy creation data."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "file_admin",
                "display_name": "File Administrator",
                "description": "Full file management permissions",
                "priority": 5,
            }

            result = cast("dict", schema.load(data))

            assert result["name"] == "file_admin"
            assert result["display_name"] == "File Administrator"
            assert result["description"] == "Full file management permissions"
            assert result["priority"] == 5

    def test_excluded_fields_not_in_result(self, app):
        """Test that excluded fields are not processed."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
                "display_name": "Test Policy",
                "id": str(uuid.uuid4()),
                "company_id": str(uuid.uuid4()),
                "created_at": datetime.now(UTC).isoformat(),
            }

            result = cast("dict", schema.load(data))

            assert "id" not in result
            assert "company_id" not in result
            assert "created_at" not in result

    def test_name_required(self, app):
        """Test that name field is required."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "display_name": "Test Policy",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "name" in exc_info.value.messages

    def test_name_cannot_be_empty(self, app):
        """Test that name cannot be empty string."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "",
                "display_name": "Test Policy",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "name" in messages
            assert POLICY_NAME_EMPTY in str(messages["name"])

    def test_name_cannot_be_whitespace(self, app):
        """Test that name cannot be only whitespace."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "   ",
                "display_name": "Test Policy",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "name" in exc_info.value.messages

    def test_name_invalid_format(self, app):
        """Test that name must be lowercase with underscores."""
        with app.app_context():
            schema = PolicyCreateSchema()
            invalid_names = ["TestPolicy", "test-policy", "test.policy", "Test_Policy"]

            for invalid_name in invalid_names:
                data = {
                    "name": invalid_name,
                    "display_name": "Test Policy",
                }

                with pytest.raises(ValidationError) as exc_info:
                    schema.load(data)

                messages = cast("dict", exc_info.value.messages)
                assert "name" in messages
                assert POLICY_NAME_INVALID_FORMAT in str(messages["name"])

    def test_name_max_length_validation(self, app):
        """Test name maximum length validation."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "a" * (POLICY_NAME_MAX_LENGTH + 1),
                "display_name": "Test Policy",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "name" in messages
            assert POLICY_NAME_TOO_LONG in str(messages["name"])

    def test_name_exactly_max_length(self, app):
        """Test name at exactly max length is valid."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "a" * POLICY_NAME_MAX_LENGTH,
                "display_name": "Test Policy",
            }

            result = cast("dict", schema.load(data))

            assert len(result["name"]) == POLICY_NAME_MAX_LENGTH

    def test_display_name_required(self, app):
        """Test that display_name field is required."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            assert "display_name" in exc_info.value.messages

    def test_display_name_cannot_be_empty(self, app):
        """Test that display_name cannot be empty string."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
                "display_name": "",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "display_name" in messages
            assert POLICY_DISPLAY_NAME_EMPTY in str(messages["display_name"])

    def test_display_name_max_length_validation(self, app):
        """Test display_name maximum length validation."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
                "display_name": "A" * (POLICY_DISPLAY_NAME_MAX_LENGTH + 1),
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "display_name" in messages
            assert POLICY_DISPLAY_NAME_TOO_LONG in str(messages["display_name"])

    def test_description_optional(self, app):
        """Test that description is optional."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
                "display_name": "Test Policy",
            }

            result = cast("dict", schema.load(data))

            assert "description" not in result or result.get("description") is None

    def test_description_max_length_validation(self, app):
        """Test description maximum length validation."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
                "display_name": "Test Policy",
                "description": "x" * (POLICY_DESCRIPTION_MAX_LENGTH + 1),
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "description" in messages
            assert POLICY_DESCRIPTION_TOO_LONG in str(messages["description"])

    def test_priority_optional(self, app):
        """Test that priority is optional with default."""
        with app.app_context():
            schema = PolicyCreateSchema()
            data = {
                "name": "test_policy",
                "display_name": "Test Policy",
            }

            result = cast("dict", schema.load(data))

            # Priority should either not be present or have default value
            assert "priority" not in result or result["priority"] == 0


class TestPolicyUpdateSchema:
    """Test cases for PolicyUpdateSchema (update/PATCH requests)."""

    def test_load_valid_data(self, app):
        """Test loading valid policy update data."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data = {
                "display_name": "Updated Policy",
                "description": "Updated description",
                "priority": 15,
                "is_active": False,
            }

            result = cast("dict", schema.load(data))

            assert result["display_name"] == "Updated Policy"
            assert result["description"] == "Updated description"
            assert result["priority"] == 15
            assert result["is_active"] is False

    def test_partial_update_support(self, app):
        """Test that partial updates are supported."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data = {
                "display_name": "Updated Policy",
            }

            result = cast("dict", schema.load(data))

            assert result["display_name"] == "Updated Policy"
            assert "description" not in result
            assert "priority" not in result

    def test_all_fields_optional(self, app):
        """Test that all fields are optional for updates."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data: dict[str, object] = {}

            result = cast("dict", schema.load(data))

            assert result == {}

    def test_excluded_fields_not_in_result(self, app):
        """Test that excluded fields are not processed."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data = {
                "display_name": "Updated Policy",
                "id": str(uuid.uuid4()),
                "company_id": str(uuid.uuid4()),
            }

            result = cast("dict", schema.load(data))

            assert "id" not in result
            assert "company_id" not in result
            assert "display_name" in result

    def test_immutable_name_field_raises_error(self, app):
        """Test that attempting to modify name field raises ValidationError."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data = {
                "display_name": "Updated Policy",
                "name": "should_be_rejected",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict[str, list[str]]", exc_info.value.messages)
            assert "name" in messages
            assert POLICY_NAME_IMMUTABLE in str(messages["name"])

    def test_display_name_validation(self, app):
        """Test display_name validation in updates."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data = {
                "display_name": "",
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "display_name" in messages

    def test_description_max_length_validation(self, app):
        """Test description maximum length validation."""
        with app.app_context():
            schema = PolicyUpdateSchema()
            data = {
                "description": "x" * (POLICY_DESCRIPTION_MAX_LENGTH + 1),
            }

            with pytest.raises(ValidationError) as exc_info:
                schema.load(data)

            messages = cast("dict", exc_info.value.messages)
            assert "description" in messages
