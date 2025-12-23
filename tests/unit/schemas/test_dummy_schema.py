# Copyright (c) 2024 World Food Programme
# This file is part of wfp-flask-template and is released under the MIT License.
# See LICENSE file for more information.

"""
Unit tests for Dummy model Marshmallow schemas.

This module tests the serialization, deserialization, and validation logic
for DummySchema, DummyCreateSchema, and DummyUpdateSchema.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from marshmallow import ValidationError

from app.models.constants import DUMMY_DESCRIPTION_MAX_LENGTH, DUMMY_NAME_MAX_LENGTH
from app.models.dummy_model import Dummy
from app.schemas.constants import (
    DUMMY_DESCRIPTION_TOO_LONG,
    DUMMY_NAME_EMPTY,
    DUMMY_NAME_NOT_UNIQUE,
    DUMMY_NAME_TOO_LONG,
)
from app.schemas.dummy_schema import DummyCreateSchema, DummySchema, DummyUpdateSchema


class TestDummySchema:
    """Test cases for DummySchema (read/serialization)."""

    def test_dump_dummy_instance(self, app):
        """Test serializing a Dummy model instance."""
        schema = DummySchema()
        dummy_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        # Create a mock Dummy instance
        dummy = Dummy(name="Test Dummy")
        dummy.id = dummy_id
        dummy.description = "Test description"
        dummy.extra_metadata = {"key": "value"}
        dummy.created_at = created_at
        dummy.updated_at = updated_at

        result = cast("dict[str, Any]", schema.dump(dummy))

        assert result["id"] == str(dummy_id)
        assert result["name"] == "Test Dummy"
        assert result["description"] == "Test description"
        assert result["extra_metadata"] == {"key": "value"}
        assert "created_at" in result
        assert "updated_at" in result

    def test_dump_only_fields_included(self, app):
        """Test that dump_only fields (id, created_at, updated_at) are included in output."""
        schema = DummySchema()
        dummy = Dummy(name="Test")
        dummy.id = uuid.uuid4()
        dummy.created_at = datetime.now(timezone.utc)
        dummy.updated_at = datetime.now(timezone.utc)

        result = cast("dict[str, Any]", schema.dump(dummy))

        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result

    def test_dump_with_null_description(self, app):
        """Test serializing a Dummy with null description."""
        schema = DummySchema()
        dummy = Dummy(name="Test")
        dummy.id = uuid.uuid4()
        dummy.description = None
        dummy.created_at = datetime.now(timezone.utc)
        dummy.updated_at = datetime.now(timezone.utc)

        result = cast("dict[str, Any]", schema.dump(dummy))

        assert result["description"] is None

    def test_dump_with_null_extra_metadata(self, app):
        """Test serializing a Dummy with null extra_metadata."""
        schema = DummySchema()
        dummy = Dummy(name="Test")
        dummy.id = uuid.uuid4()
        dummy.extra_metadata = None
        dummy.created_at = datetime.now(timezone.utc)
        dummy.updated_at = datetime.now(timezone.utc)

        result = cast("dict[str, Any]", schema.dump(dummy))

        assert result["extra_metadata"] is None


class TestDummyCreateSchema:
    """Test cases for DummyCreateSchema (creation/POST requests)."""

    def test_load_valid_data(self, app, session):
        """Test loading valid creation data."""
        schema = DummyCreateSchema()
        data = {
            "name": "New Dummy",
            "description": "New description",
            "extra_metadata": {"key": "value"},
        }

        result = schema.load(data, session=session)

        assert result["name"] == "New Dummy"
        assert result["description"] == "New description"
        assert result["extra_metadata"] == {"key": "value"}

    def test_excluded_fields_not_in_result(self, app, session):
        """Test that id, created_at, updated_at are excluded from load."""
        schema = DummyCreateSchema()
        data = {
            "name": "Test",
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = schema.load(data, session=session)

        assert "id" not in result
        assert "created_at" not in result
        assert "updated_at" not in result
        assert result["name"] == "Test"

    def test_name_required(self, app, session):
        """Test that name is required."""
        schema = DummyCreateSchema()
        data = {
            "description": "Test description",
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages

    def test_name_cannot_be_empty(self, app, session):
        """Test that name cannot be empty string."""
        schema = DummyCreateSchema()
        data = {"name": ""}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_EMPTY in exc_info.value.messages["name"]  # type: ignore[index]

    def test_name_cannot_be_whitespace(self, app, session):
        """Test that name cannot be only whitespace."""
        schema = DummyCreateSchema()
        data = {"name": "   "}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_EMPTY in exc_info.value.messages["name"]  # type: ignore[index]

    def test_name_max_length_validation(self, app, session):
        """Test name max length validation."""
        schema = DummyCreateSchema()
        data = {"name": "a" * (DUMMY_NAME_MAX_LENGTH + 1)}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_TOO_LONG in exc_info.value.messages["name"]  # type: ignore[index]

    def test_name_exactly_max_length(self, app, session):
        """Test that name at exactly max length is valid."""
        schema = DummyCreateSchema()
        data = {"name": "a" * DUMMY_NAME_MAX_LENGTH}

        result = schema.load(data, session=session)

        assert result["name"] == "a" * DUMMY_NAME_MAX_LENGTH

    def test_description_max_length_validation(self, app, session):
        """Test description max length validation."""
        schema = DummyCreateSchema()
        data = {
            "name": "Test",
            "description": "a" * (DUMMY_DESCRIPTION_MAX_LENGTH + 1),
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "description" in exc_info.value.messages
        assert DUMMY_DESCRIPTION_TOO_LONG in exc_info.value.messages["description"]  # type: ignore[index]

    def test_description_exactly_max_length(self, app, session):
        """Test that description at exactly max length is valid."""
        schema = DummyCreateSchema()
        data = {
            "name": "Test",
            "description": "a" * DUMMY_DESCRIPTION_MAX_LENGTH,
        }

        result = schema.load(data, session=session)

        assert result["description"] == "a" * DUMMY_DESCRIPTION_MAX_LENGTH

    def test_description_optional(self, app, session):
        """Test that description is optional."""
        schema = DummyCreateSchema()
        data = {"name": "Test"}

        result = schema.load(data, session=session)

        assert "description" not in result or result["description"] is None

    def test_extra_metadata_optional(self, app, session):
        """Test that extra_metadata is optional."""
        schema = DummyCreateSchema()
        data = {"name": "Test"}

        result = schema.load(data, session=session)

        assert "extra_metadata" not in result or result["extra_metadata"] is None

    def test_extra_metadata_accepts_json(self, app, session):
        """Test that extra_metadata accepts valid JSON."""
        schema = DummyCreateSchema()
        data = {
            "name": "Test",
            "extra_metadata": {
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "number": 42,
            },
        }

        result = schema.load(data, session=session)

        assert result["extra_metadata"] == {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
        }

    def test_validate_name_uniqueness_with_session(self, app, session):
        """Test name uniqueness validation when duplicate exists."""
        # Create an existing dummy
        Dummy.create(
            name="Existing Dummy",
            description="Test",
            extra_metadata={},
        )
        session.commit()

        schema = DummyCreateSchema()
        data = {"name": "Existing Dummy"}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_NOT_UNIQUE in exc_info.value.messages["name"]  # type: ignore[index]

    def test_validate_name_uniqueness_no_duplicate(self, app, session):
        """Test name uniqueness validation when no duplicate exists."""
        schema = DummyCreateSchema()
        data = {"name": "Unique Name"}

        result = schema.load(data, session=session)

        assert result["name"] == "Unique Name"


class TestDummyUpdateSchema:
    """Test cases for DummyUpdateSchema (update/PUT/PATCH requests)."""

    def test_load_valid_data(self, app, session):
        """Test loading valid update data."""
        schema = DummyUpdateSchema()
        data = {
            "name": "Updated Name",
            "description": "Updated description",
            "extra_metadata": {"updated": "value"},
        }

        result = schema.load(data, session=session)

        assert result["name"] == "Updated Name"
        assert result["description"] == "Updated description"
        assert result["extra_metadata"] == {"updated": "value"}

    def test_partial_update_support(self, app, session):
        """Test that partial=True allows updating only some fields."""
        schema = DummyUpdateSchema()
        data = {"name": "Updated Name"}

        result = schema.load(data, session=session)

        assert result["name"] == "Updated Name"
        assert "description" not in result
        assert "extra_metadata" not in result

    def test_all_fields_optional(self, app, session):
        """Test that all fields are optional due to partial=True."""
        schema = DummyUpdateSchema()
        data = {}

        result = schema.load(data, session=session)

        assert result == {}

    def test_excluded_fields_not_in_result(self, app, session):
        """Test that id, created_at, updated_at are excluded."""
        schema = DummyUpdateSchema()
        data = {
            "name": "Test",
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = schema.load(data, session=session)

        assert "id" not in result
        assert "created_at" not in result
        assert "updated_at" not in result
        assert result["name"] == "Test"

    def test_name_cannot_be_empty_if_provided(self, app, session):
        """Test that name cannot be empty if provided in update."""
        schema = DummyUpdateSchema()
        data = {"name": ""}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_EMPTY in exc_info.value.messages["name"]  # type: ignore[index]

    def test_name_cannot_be_whitespace_if_provided(self, app, session):
        """Test that name cannot be whitespace if provided in update."""
        schema = DummyUpdateSchema()
        data = {"name": "   "}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_EMPTY in exc_info.value.messages["name"]  # type: ignore[index]

    def test_name_max_length_validation(self, app, session):
        """Test name max length validation in update."""
        schema = DummyUpdateSchema()
        data = {"name": "a" * (DUMMY_NAME_MAX_LENGTH + 1)}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_TOO_LONG in exc_info.value.messages["name"]  # type: ignore[index]

    def test_name_exactly_max_length(self, app, session):
        """Test that name at exactly max length is valid in update."""
        schema = DummyUpdateSchema()
        data = {"name": "a" * DUMMY_NAME_MAX_LENGTH}

        result = schema.load(data, session=session)

        assert result["name"] == "a" * DUMMY_NAME_MAX_LENGTH

    def test_description_max_length_validation(self, app, session):
        """Test description max length validation in update."""
        schema = DummyUpdateSchema()
        data = {"description": "a" * (DUMMY_DESCRIPTION_MAX_LENGTH + 1)}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "description" in exc_info.value.messages
        assert DUMMY_DESCRIPTION_TOO_LONG in exc_info.value.messages["description"]  # type: ignore[index]

    def test_description_exactly_max_length(self, app, session):
        """Test that description at exactly max length is valid in update."""
        schema = DummyUpdateSchema()
        data = {"description": "a" * DUMMY_DESCRIPTION_MAX_LENGTH}

        result = schema.load(data, session=session)

        assert result["description"] == "a" * DUMMY_DESCRIPTION_MAX_LENGTH

    def test_update_only_description(self, app, session):
        """Test updating only description field."""
        schema = DummyUpdateSchema()
        data = {"description": "New description"}

        result = schema.load(data, session=session)

        assert result["description"] == "New description"
        assert "name" not in result

    def test_update_only_extra_metadata(self, app, session):
        """Test updating only extra_metadata field."""
        schema = DummyUpdateSchema()
        data = {"extra_metadata": {"new": "metadata"}}

        result = schema.load(data, session=session)

        assert result["extra_metadata"] == {"new": "metadata"}
        assert "name" not in result

    def test_extra_metadata_accepts_json(self, app, session):
        """Test that extra_metadata accepts valid JSON in update."""
        schema = DummyUpdateSchema()
        data = {
            "extra_metadata": {
                "nested": {"key": "value"},
                "list": [1, 2, 3],
            },
        }

        result = schema.load(data, session=session)

        assert result["extra_metadata"] == {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }

    def test_validate_name_uniqueness_with_session(self, app, session):
        """Test name uniqueness validation in update when duplicate exists."""
        # Create two existing dummies
        Dummy.create(name="Dummy 1", description="Test")
        Dummy.create(name="Dummy 2", description="Test")
        session.commit()

        schema = DummyUpdateSchema()
        # Try to update Dummy 2's name to match Dummy 1
        data = {"name": "Dummy 1"}

        with pytest.raises(ValidationError) as exc_info:
            schema.load(data, session=session)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_NOT_UNIQUE in exc_info.value.messages["name"]  # type: ignore[index]

    def test_validate_name_uniqueness_no_duplicate(self, app, session):
        """Test name uniqueness validation in update when no duplicate exists."""
        Dummy.create(name="Existing Dummy", description="Test")
        session.commit()

        schema = DummyUpdateSchema()
        data = {"name": "Unique Name"}

        result = schema.load(data, session=session)

        assert result["name"] == "Unique Name"


class TestSchemaEdgeCases:
    """Test edge cases and code paths for increased coverage."""

    def test_dummy_schema_validate_name_without_session(self, app, session):
        """Test DummySchema name validation without session parameter."""
        # Create an existing dummy
        Dummy.create(name="Existing Name", description="Test")
        session.commit()

        schema = DummySchema()
        data = {"name": "Existing Name"}

        # Validation should use Dummy.get_by_name() when no session provided
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert "name" in exc_info.value.messages
        assert DUMMY_NAME_NOT_UNIQUE in exc_info.value.messages["name"]  # type: ignore[index]

    def test_dummy_schema_validate_name_unique_without_session(self, app):
        """Test DummySchema name validation passes for unique name without session."""
        schema = DummySchema()
        data = {"name": "Completely Unique Name"}

        result = schema.load(data)

        assert result["name"] == "Completely Unique Name"

    def test_dummy_create_schema_validate_name_without_session(self, app, session):
        """Test DummyCreateSchema name validation without session parameter."""
        # Create an existing dummy
        Dummy.create(name="Taken Name", description="Test")
        session.commit()

        schema = DummyCreateSchema()
        data = {"name": "Taken Name"}

        # Should fail validation when name exists
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert "name" in exc_info.value.messages

    def test_dummy_create_schema_validate_name_unique_without_session(self, app):
        """Test DummyCreateSchema name validation passes without session."""
        schema = DummyCreateSchema()
        data = {"name": "Brand New Name"}

        result = schema.load(data)

        assert result["name"] == "Brand New Name"

    def test_dummy_update_schema_validate_name_without_session(self, app, session):
        """Test DummyUpdateSchema name validation without session parameter."""
        # Create an existing dummy
        Dummy.create(name="Occupied Name", description="Test")
        session.commit()

        schema = DummyUpdateSchema()
        data = {"name": "Occupied Name"}

        # Should fail validation
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)

        assert "name" in exc_info.value.messages

    def test_dummy_update_schema_validate_name_unique_without_session(self, app):
        """Test DummyUpdateSchema name validation passes without session."""
        schema = DummyUpdateSchema()
        data = {"name": "Fresh Name"}

        result = schema.load(data)

        assert result["name"] == "Fresh Name"

    def test_dummy_schema_pre_load_strips_description(self, app):
        """Test that pre_load strips whitespace from description field."""
        schema = DummySchema()
        data = {"name": "Test", "description": "  spaced description  "}

        result = schema.load(data)

        assert result["description"] == "spaced description"

    def test_dummy_schema_pre_load_description_not_string(self, app):
        """Test that pre_load handles non-string description."""
        schema = DummySchema()
        # If description is not a string, it shouldn't be stripped
        data = {"name": "Test", "description": None}

        result = schema.load(data)

        assert result["description"] is None

    def test_dummy_create_schema_pre_load_strips_description(self, app):
        """Test DummyCreateSchema pre_load strips description."""
        schema = DummyCreateSchema()
        data = {"name": "Test", "description": "  desc with spaces  "}

        result = schema.load(data)

        assert result["description"] == "desc with spaces"

    def test_dummy_update_schema_pre_load_strips_description(self, app):
        """Test DummyUpdateSchema pre_load strips description."""
        schema = DummyUpdateSchema()
        data = {"description": "  trimmed  "}

        result = schema.load(data)

        assert result["description"] == "trimmed"

    def test_dummy_update_schema_pre_load_description_not_string(self, app):
        """Test DummyUpdateSchema pre_load handles non-string description."""
        schema = DummyUpdateSchema()
        data = {"description": None}

        result = schema.load(data)

        assert result["description"] is None
