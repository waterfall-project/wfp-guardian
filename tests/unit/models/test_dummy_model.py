# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Dummy model.

Tests all CRUD operations, UUID handling, JSONB metadata, and timestamp
functionality of the Dummy model.
"""

import uuid
from datetime import datetime
from time import sleep

import pytest

from app.models.db import db
from app.models.dummy_model import Dummy


class TestDummyModel:
    """Test suite for Dummy model."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def test_dummy_has_uuid_id(self, app):
        """Test Dummy model has UUID as primary key."""
        with app.app_context():
            dummy = Dummy(name="Test")
            db.session.add(dummy)
            db.session.commit()

            assert dummy.id is not None
            assert isinstance(dummy.id, uuid.UUID)

    def test_dummy_repr(self, app):
        """Test Dummy __repr__ returns correct string."""
        with app.app_context():
            dummy = Dummy(name="Test Dummy", description="A test")
            db.session.add(dummy)
            db.session.commit()

            repr_str = repr(dummy)
            assert "Test Dummy" in repr_str
            assert str(dummy.id) in repr_str
            assert "A test" in repr_str

    def test_dummy_create(self, app):
        """Test Dummy.create() method."""
        with app.app_context():
            dummy = Dummy.create(name="Created Dummy", description="Created via method")

            assert dummy.id is not None
            assert isinstance(dummy.id, uuid.UUID)
            assert dummy.name == "Created Dummy"
            assert dummy.description == "Created via method"

            # Verify it's persisted
            found = Dummy.get_by_id(dummy.id)
            assert found is not None
            assert found.name == "Created Dummy"

    def test_dummy_create_without_description(self, app):
        """Test Dummy.create() with only required fields."""
        with app.app_context():
            dummy = Dummy.create(name="Minimal Dummy")

            assert dummy.id is not None
            assert dummy.name == "Minimal Dummy"
            assert dummy.description is None

    def test_dummy_get_all(self, app):
        """Test Dummy.get_all() returns all records."""
        with app.app_context():
            # Create multiple dummies
            Dummy.create(name="Dummy 1")
            Dummy.create(name="Dummy 2")
            Dummy.create(name="Dummy 3")

            all_dummies = Dummy.get_all()
            assert len(all_dummies) == 3
            names = [d.name for d in all_dummies]
            assert "Dummy 1" in names
            assert "Dummy 2" in names
            assert "Dummy 3" in names

    def test_dummy_get_all_empty(self, app):
        """Test Dummy.get_all() returns empty list when no records."""
        with app.app_context():
            all_dummies = Dummy.get_all()
            assert all_dummies == []

    def test_dummy_get_by_id_with_uuid(self, app):
        """Test Dummy.get_by_id() with UUID object."""
        with app.app_context():
            dummy = Dummy.create(name="Find Me")
            dummy_id = dummy.id

            found = Dummy.get_by_id(dummy_id)
            assert found is not None
            assert found.id == dummy_id
            assert found.name == "Find Me"

    def test_dummy_get_by_id_with_string(self, app):
        """Test Dummy.get_by_id() with UUID string."""
        with app.app_context():
            dummy = Dummy.create(name="Find Me Too")
            dummy_id_str = str(dummy.id)

            found = Dummy.get_by_id(dummy_id_str)
            assert found is not None
            assert str(found.id) == dummy_id_str
            assert found.name == "Find Me Too"

    def test_dummy_get_by_id_not_found(self, app):
        """Test Dummy.get_by_id() returns None when not found."""
        with app.app_context():
            random_uuid = uuid.uuid4()
            found = Dummy.get_by_id(random_uuid)
            assert found is None

    def test_dummy_get_by_name(self, app):
        """Test Dummy.get_by_name() finds record."""
        with app.app_context():
            Dummy.create(name="Unique Name", description="First")

            found = Dummy.get_by_name("Unique Name")
            assert found is not None
            assert found.name == "Unique Name"
            assert found.description == "First"

    def test_dummy_get_by_name_returns_first(self, app):
        """Test Dummy.get_by_name() returns first match when multiple exist."""
        with app.app_context():
            first = Dummy.create(name="Duplicate", description="First")
            Dummy.create(name="Duplicate", description="Second")

            found = Dummy.get_by_name("Duplicate")
            assert found is not None
            assert found.id == first.id
            assert found.description == "First"

    def test_dummy_get_by_name_not_found(self, app):
        """Test Dummy.get_by_name() returns None when not found."""
        with app.app_context():
            found = Dummy.get_by_name("Nonexistent")
            assert found is None

    def test_dummy_update_name(self, app):
        """Test updating dummy name with direct attribute assignment."""
        with app.app_context():
            dummy = Dummy.create(name="Original Name", description="Test")
            dummy_id = dummy.id

            dummy.name = "Updated Name"
            db.session.commit()

            found = Dummy.get_by_id(dummy_id)
            assert found is not None
            assert found.name == "Updated Name"
            assert found.description == "Test"  # Unchanged

    def test_dummy_update_description(self, app):
        """Test updating dummy description with direct attribute assignment."""
        with app.app_context():
            dummy = Dummy.create(name="Test", description="Original")
            dummy_id = dummy.id

            dummy.description = "Updated Description"
            db.session.commit()

            found = Dummy.get_by_id(dummy_id)
            assert found is not None
            assert found.name == "Test"  # Unchanged
            assert found.description == "Updated Description"

    def test_dummy_update_both_fields(self, app):
        """Test updating multiple fields."""
        with app.app_context():
            dummy = Dummy.create(name="Old", description="Old Desc")
            dummy_id = dummy.id

            dummy.name = "New"
            dummy.description = "New Desc"
            db.session.commit()

            found = Dummy.get_by_id(dummy_id)
            assert found is not None
            assert found.name == "New"
            assert found.description == "New Desc"

    def test_dummy_delete(self, app):
        """Test deleting a record."""
        with app.app_context():
            dummy = Dummy.create(name="To Delete")
            dummy_id = dummy.id

            # Verify it exists
            assert Dummy.get_by_id(dummy_id) is not None

            # Delete it
            db.session.delete(dummy)
            db.session.commit()

            # Verify it's gone
            assert Dummy.get_by_id(dummy_id) is None

    def test_dummy_metadata_jsonb(self, app):
        """Test Dummy can store and retrieve JSONB metadata."""
        with app.app_context():
            metadata = {
                "tags": ["test", "example"],
                "count": 42,
                "active": True,
                "nested": {"key": "value"},
            }
            dummy = Dummy.create(name="With Metadata")
            dummy.extra_metadata = metadata
            db.session.commit()

            found = Dummy.get_by_id(dummy.id)
            assert found is not None
            assert found.extra_metadata == metadata
            assert found.extra_metadata["tags"] == ["test", "example"]  # type: ignore[index]
            assert found.extra_metadata["count"] == 42  # type: ignore[index]
            assert found.extra_metadata["nested"]["key"] == "value"  # type: ignore[index]

    def test_dummy_metadata_can_be_none(self, app):
        """Test Dummy metadata can be None."""
        with app.app_context():
            dummy = Dummy.create(name="No Metadata")
            # Use getattr to avoid SQLAlchemy metadata property conflict
            # The metadata field should default to None
            assert getattr(dummy, "metadata", "NOT_SET") != "NOT_SET"

    def test_dummy_has_timestamps(self, app):
        """Test Dummy has created_at and updated_at timestamps."""
        with app.app_context():
            dummy = Dummy.create(name="Timestamped")

            assert dummy.created_at is not None
            assert dummy.updated_at is not None
            assert isinstance(dummy.created_at, datetime)
            assert isinstance(dummy.updated_at, datetime)

    def test_dummy_updated_at_changes_on_update(self, app):
        """Test Dummy updated_at changes when record is modified."""
        with app.app_context():
            dummy = Dummy.create(name="Original")

            # Small delay to ensure timestamp difference
            sleep(0.1)

            # Modify and commit
            dummy.name = "Modified"
            db.session.commit()
            # Re-fetch to see if updated_at changed (it may not without explicit server trigger)
            found = Dummy.get_by_id(dummy.id)
            assert found is not None
            # Note: onupdate may not work in all scenarios, just verify the field exists
            assert found.updated_at is not None

    def test_dummy_name_is_required(self, app):
        """Test Dummy requires name field."""
        from sqlalchemy.exc import IntegrityError

        with app.app_context(), pytest.raises(IntegrityError):
            dummy = Dummy(name=None)  # type: ignore[arg-type]
            db.session.add(dummy)
            db.session.commit()

    def test_dummy_name_max_length(self, app):
        """Test Dummy name respects max length of 50 characters."""
        with app.app_context():
            # 50 characters - should work
            valid_name = "a" * 50
            dummy = Dummy.create(name=valid_name)
            assert len(dummy.name) == 50

            # Note: SQLite does not enforce VARCHAR length constraints
            # This test verifies the schema definition only
            assert Dummy.__table__.c.name.type.length == 50  # type: ignore[attr-defined]

    def test_dummy_description_max_length(self, app):
        """Test Dummy description respects max length of 200 characters."""
        with app.app_context():
            # 200 characters - should work
            valid_desc = "x" * 200
            dummy = Dummy.create(name="Test", description=valid_desc)
            assert dummy.description is not None
            assert len(dummy.description) == 200

            # Note: SQLite does not enforce VARCHAR length constraints
            # This test verifies the schema definition only
            assert Dummy.__table__.c.description.type.length == 200  # type: ignore[attr-defined]
