# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for custom SQLAlchemy model types.

Tests the GUID, JSONB, UUIDMixin, and TimestampMixin types for compatibility
across SQLite and PostgreSQL databases.
"""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column, String

from app.models.db import db
from app.models.types import GUID, JSONB, TimestampMixin, UUIDMixin


class TestGUID:
    """Test suite for GUID custom type."""

    def test_guid_with_sqlite_dialect(self):
        """Test GUID behavior with SQLite dialect."""
        from sqlalchemy.dialects import sqlite

        guid = GUID()
        dialect = sqlite.dialect()

        # Test load_dialect_impl returns String(36) for SQLite
        impl = guid.load_dialect_impl(dialect)
        assert isinstance(impl, String)
        assert impl.length == 36

    def test_guid_bind_param_sqlite_converts_uuid_to_string(self):
        """Test GUID converts UUID to string for SQLite."""
        guid = GUID()
        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"
        test_uuid = uuid.uuid4()

        result = guid.process_bind_param(test_uuid, mock_dialect)
        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_guid_bind_param_sqlite_accepts_string(self):
        """Test GUID accepts string input for SQLite."""
        guid = GUID()
        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"
        test_uuid_str = str(uuid.uuid4())

        result = guid.process_bind_param(test_uuid_str, mock_dialect)
        assert result == test_uuid_str

    def test_guid_bind_param_none(self):
        """Test GUID handles None value."""
        guid = GUID()
        mock_dialect = MagicMock()

        result = guid.process_bind_param(None, mock_dialect)
        assert result is None

    def test_guid_result_value_converts_string_to_uuid(self):
        """Test GUID converts string from DB to UUID."""
        guid = GUID()
        mock_dialect = MagicMock()
        test_uuid_str = str(uuid.uuid4())

        result = guid.process_result_value(test_uuid_str, mock_dialect)
        assert isinstance(result, uuid.UUID)
        assert str(result) == test_uuid_str

    def test_guid_result_value_returns_uuid_as_is(self):
        """Test GUID returns UUID object unchanged."""
        guid = GUID()
        mock_dialect = MagicMock()
        test_uuid = uuid.uuid4()

        result = guid.process_result_value(test_uuid, mock_dialect)
        assert result == test_uuid

    def test_guid_result_value_none(self):
        """Test GUID handles None result value."""
        guid = GUID()
        mock_dialect = MagicMock()

        result = guid.process_result_value(None, mock_dialect)
        assert result is None


class TestJSONB:
    """Test suite for JSONB custom type."""

    def test_jsonb_with_sqlite_dialect(self):
        """Test JSONB uses Text for SQLite."""
        from sqlalchemy.dialects import sqlite

        jsonb = JSONB()
        dialect = sqlite.dialect()

        impl = jsonb.load_dialect_impl(dialect)
        assert impl.__class__.__name__ == "Text"

    def test_jsonb_bind_param_sqlite_serializes_dict(self):
        """Test JSONB serializes dict to JSON string for SQLite."""
        jsonb = JSONB()
        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"
        test_data = {"key": "value", "number": 42}

        result = jsonb.process_bind_param(test_data, mock_dialect)
        assert isinstance(result, str)
        assert json.loads(result) == test_data

    def test_jsonb_bind_param_sqlite_serializes_list(self):
        """Test JSONB serializes list to JSON string for SQLite."""
        jsonb = JSONB()
        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"
        test_data = [1, 2, 3, "test"]

        result = jsonb.process_bind_param(test_data, mock_dialect)
        assert isinstance(result, str)
        assert json.loads(result) == test_data

    def test_jsonb_bind_param_none(self):
        """Test JSONB handles None value."""
        jsonb = JSONB()
        mock_dialect = MagicMock()

        result = jsonb.process_bind_param(None, mock_dialect)
        assert result is None

    def test_jsonb_result_value_deserializes_json(self):
        """Test JSONB deserializes JSON string from SQLite."""
        jsonb = JSONB()
        mock_dialect = MagicMock()
        mock_dialect.name = "sqlite"
        test_data = {"key": "value", "nested": {"data": 123}}
        json_string = json.dumps(test_data)

        result = jsonb.process_result_value(json_string, mock_dialect)
        assert result == test_data

    def test_jsonb_result_value_none(self):
        """Test JSONB handles None result value."""
        jsonb = JSONB()
        mock_dialect = MagicMock()

        result = jsonb.process_result_value(None, mock_dialect)
        assert result is None


class TestUUIDMixin:
    """Test suite for UUIDMixin."""

    def test_uuid_mixin_has_id_column(self):
        """Test UUIDMixin provides id column."""
        assert hasattr(UUIDMixin, "id")
        assert UUIDMixin.id.type.__class__.__name__ == "GUID"

    def test_uuid_mixin_id_is_primary_key(self):
        """Test UUIDMixin id is configured as primary key."""
        assert UUIDMixin.id.primary_key is True

    def test_uuid_mixin_id_has_default(self):
        """Test UUIDMixin id has uuid4 default."""
        assert UUIDMixin.id.default.arg == uuid.uuid4 or callable(
            UUIDMixin.id.default.arg
        )


class TestTimestampMixin:
    """Test suite for TimestampMixin."""

    def test_timestamp_mixin_has_created_at(self):
        """Test TimestampMixin provides created_at column."""
        assert hasattr(TimestampMixin, "created_at")
        assert TimestampMixin.created_at.nullable is False

    def test_timestamp_mixin_has_updated_at(self):
        """Test TimestampMixin provides updated_at column."""
        assert hasattr(TimestampMixin, "updated_at")
        assert TimestampMixin.updated_at.nullable is False

    def test_timestamp_mixin_has_server_defaults(self):
        """Test TimestampMixin columns have server defaults."""
        assert TimestampMixin.created_at.server_default is not None
        assert TimestampMixin.updated_at.server_default is not None

    def test_timestamp_mixin_updated_at_has_onupdate(self):
        """Test TimestampMixin updated_at has onupdate trigger."""
        assert TimestampMixin.updated_at.onupdate is not None


class TestModelWithMixins:
    """Integration tests for models using custom types and mixins."""

    @pytest.fixture
    def test_model(self):
        """Create a test model using the mixins."""
        # Use a unique class name to avoid SQLAlchemy registry warnings
        import uuid as uuid_module

        class_name = f"TestModel_{uuid_module.uuid4().hex[:8]}"

        test_model_cls = type(
            class_name,
            (UUIDMixin, TimestampMixin, db.Model),
            {
                "__tablename__": "test_model",
                "__table_args__": {"extend_existing": True},
                "name": Column(String(50), nullable=False),
                "data": Column(JSONB(), nullable=True),
            },
        )

        return test_model_cls

    def test_model_creates_with_uuid(self, app, test_model):
        """Test model instance is created with UUID."""
        with app.app_context():
            db.create_all()
            instance = test_model(name="test")
            db.session.add(instance)
            db.session.commit()

            assert instance.id is not None
            assert isinstance(instance.id, uuid.UUID)
            assert instance.name == "test"

            db.session.delete(instance)
            db.session.commit()
            db.drop_all()

    def test_model_stores_jsonb_data(self, app, test_model):
        """Test model stores and retrieves JSONB data."""
        with app.app_context():
            db.create_all()
            test_data = {"key": "value", "count": 42, "active": True}
            instance = test_model(name="json_test", data=test_data)
            db.session.add(instance)
            db.session.commit()

            retrieved = db.session.get(test_model, instance.id)
            assert retrieved is not None
            assert retrieved.data == test_data
            assert retrieved.data["key"] == "value"
            assert retrieved.data["count"] == 42

            db.session.delete(instance)
            db.session.commit()
            db.drop_all()

    def test_model_timestamps_are_set(self, app, test_model):
        """Test model timestamps are automatically set."""
        with app.app_context():
            db.create_all()
            instance = test_model(name="timestamp_test")
            db.session.add(instance)
            db.session.commit()

            assert instance.created_at is not None
            assert instance.updated_at is not None
            assert isinstance(instance.created_at, datetime)
            assert isinstance(instance.updated_at, datetime)

            db.session.delete(instance)
            db.session.commit()
            db.drop_all()
