"""Tests for configuration serialization in ConfigResource.

This module contains unit tests for the _serialize_value method
to ensure all data types are properly serialized to JSON.
"""

import math
from datetime import datetime, timedelta


def test_serialize_value_with_timedelta(client, app):
    """Test that timedelta values are serialized as strings."""
    from app.resources.config import ConfigResource

    # Test timedelta serialization
    td = timedelta(hours=3, minutes=30)
    result = ConfigResource._serialize_value(td)

    assert isinstance(result, str)
    assert "3:30:00" in result


def test_serialize_value_with_datetime(client, app):
    """Test that datetime values are serialized in ISO format."""
    from app.resources.config import ConfigResource

    # Test datetime serialization
    dt = datetime(2025, 1, 15, 12, 30, 45)
    result = ConfigResource._serialize_value(dt)

    assert isinstance(result, str)
    assert "2025-01-15" in result
    assert "12:30:45" in result


def test_serialize_value_with_list(client, app):
    """Test that lists are recursively serialized."""
    from app.resources.config import ConfigResource

    # Test list with mixed types including datetime
    test_list = ["string", 123, datetime(2025, 1, 1, 10, 0, 0), timedelta(hours=2)]
    result = ConfigResource._serialize_value(test_list)

    assert isinstance(result, list)
    assert len(result) == 4
    assert result[0] == "string"
    assert result[1] == 123
    assert "2025-01-01" in result[2]
    assert "2:00:00" in result[3]


def test_serialize_value_with_dict(client, app):
    """Test that dictionaries are recursively serialized."""
    from app.resources.config import ConfigResource

    # Test dict with mixed types including datetime
    test_dict = {
        "name": "test",
        "count": 42,
        "created_at": datetime(2025, 1, 1, 10, 0, 0),
        "duration": timedelta(hours=1, minutes=30),
    }
    result = ConfigResource._serialize_value(test_dict)

    assert isinstance(result, dict)
    assert result["name"] == "test"
    assert result["count"] == 42
    assert "2025-01-01" in result["created_at"]
    assert "1:30:00" in result["duration"]


def test_serialize_value_with_nested_structures(client, app):
    """Test that nested structures (lists of dicts, etc.) are properly serialized."""
    from app.resources.config import ConfigResource

    # Test nested structure
    test_data = {
        "users": [
            {
                "name": "Alice",
                "joined": datetime(2024, 6, 1, 0, 0, 0),
                "session_duration": timedelta(minutes=45),
            },
            {
                "name": "Bob",
                "joined": datetime(2024, 7, 1, 0, 0, 0),
                "session_duration": timedelta(hours=2),
            },
        ],
        "total": 2,
    }
    result = ConfigResource._serialize_value(test_data)

    assert isinstance(result, dict)
    assert len(result["users"]) == 2
    assert result["users"][0]["name"] == "Alice"
    assert "2024-06-01" in result["users"][0]["joined"]
    assert "0:45:00" in result["users"][0]["session_duration"]
    assert result["total"] == 2


def test_serialize_value_with_primitive_types(client, app):
    """Test that primitive types pass through unchanged."""
    from app.resources.config import ConfigResource

    # Test primitives
    assert ConfigResource._serialize_value("string") == "string"
    assert ConfigResource._serialize_value(123) == 123
    assert ConfigResource._serialize_value(True) is True
    assert ConfigResource._serialize_value(False) is False
    assert ConfigResource._serialize_value(None) is None
    # Float - just check type preservation
    result = ConfigResource._serialize_value(45.67)
    assert isinstance(result, float)
    assert math.isclose(result, 45.67)


def test_configuration_endpoint_with_datetime_config(client, app, api_url):
    """Test that configuration endpoint properly serializes datetime configs."""
    # Set a timedelta in app config (like PERMANENT_SESSION_LIFETIME)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    response = client.get(api_url("configuration"))

    assert response.status_code == 200
    data = response.get_json()

    # Check that timedelta was serialized
    assert "PERMANENT_SESSION_LIFETIME" in data["configuration"]
    # Should be serialized as a string
    psl_value = data["configuration"]["PERMANENT_SESSION_LIFETIME"]
    assert isinstance(psl_value, str)

    # Explicitly clean up database connection
    from app.models.db import db

    db.session.remove()
    db.engine.dispose()
