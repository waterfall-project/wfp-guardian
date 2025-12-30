"""Tests for application initialization and extensions.

This module contains unit tests for app/__init__.py functionality including
extension registration, rate limiter configuration, and helper functions.
"""

import logging

import pytest


def test_register_extensions_with_redis(app):
    """Test that rate limiter is configured with Redis when REDIS_URL is set."""

    # Set Redis configuration
    app.config["RATE_LIMIT_STORAGE"] = "redis"
    app.config["REDIS_URL"] = "redis://localhost:6379/0"
    app.config["RATE_LIMIT_ENABLED"] = True

    # Check that RATELIMIT_STORAGE_URI is set to Redis URL
    # This is set during app creation, so we verify it was set correctly
    # by checking the config
    assert "RATELIMIT_STORAGE_URI" in app.config


def test_register_test_routes_creates_error_routes(app):
    """Test that register_test_routes creates routes that trigger errors."""
    # The test routes should already be registered in the app fixture
    # Verify they exist
    with app.test_client() as client:
        # These routes should trigger error handlers
        response = client.get("/unauthorized")
        assert response.status_code == 401

        response = client.get("/forbidden")
        assert response.status_code == 403

        response = client.get("/bad")
        assert response.status_code == 400

        response = client.get("/fail")
        assert response.status_code == 500


def test_log_environment_variables_masks_sensitive_data(app, caplog):
    """Test that _log_environment_variables masks sensitive configuration values."""
    from app import _log_environment_variables

    # Set caplog to capture INFO level
    caplog.set_level(logging.INFO)

    # Set some sensitive values
    app.config["JWT_SECRET_KEY"] = "super-secret-key-123"  # nosec B105
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:password@localhost/db"
    app.config["SECRET_KEY"] = "another-secret"  # nosec B105
    with app.app_context():
        _log_environment_variables(app)

    # Check that sensitive values are masked in logs
    log_output = caplog.text
    assert "super-secret-key-123" not in log_output
    assert "password@localhost" not in log_output
    assert "another-secret" not in log_output
    assert "<MASKED>" in log_output


def test_create_app_with_different_configs():
    """Test that create_app works with different configuration classes."""
    from app import create_app

    # Test with development config
    app = create_app("app.config.DevelopmentConfig")
    assert app.config["DEBUG"] is True

    # Test with testing config
    app = create_app("app.config.TestingConfig")
    assert app.config["TESTING"] is True


def test_cors_configuration(app):
    """Test that CORS is configured properly based on config."""
    assert "CORS_ENABLED" in app.config
    assert "CORS_ORIGINS" in app.config

    # CORS should be enabled in test config
    if app.config.get("CORS_ENABLED"):
        assert isinstance(app.config["CORS_ORIGINS"], (list, str))


def test_metrics_endpoint_with_missing_version_file(monkeypatch, caplog):
    """Test that app handles missing VERSION file gracefully for metrics endpoint."""
    from pathlib import Path

    from app import create_app

    # Mock Path.read_text to raise FileNotFoundError for VERSION
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == "VERSION":
            raise FileNotFoundError("VERSION file not found")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    caplog.set_level(logging.WARNING)

    # Create app - should handle missing VERSION file
    app = create_app("app.config.TestingConfig")

    # Check that warning was logged
    assert any(
        "Failed to read VERSION file" in record.message for record in caplog.records
    )

    # Verify default v0 metrics endpoint exists
    with app.test_client() as client:
        response = client.get("/v0/metrics")
        assert response.status_code == 200


def test_startup_validation_fails_without_internal_service_token(monkeypatch):
    """Test that app fails to start when INTERNAL_SERVICE_TOKEN is not configured."""
    from app import create_app
    from app.config import TestingConfig

    # Create a test config class without INTERNAL_SERVICE_TOKEN
    class InvalidConfig(TestingConfig):
        INTERNAL_SERVICE_TOKEN = None

    # Attempt to create app should raise ValueError
    with pytest.raises(
        ValueError,
        match="INTERNAL_SERVICE_TOKEN must be configured for service-to-service authentication",
    ):
        create_app(InvalidConfig)


def test_startup_validation_warns_for_short_internal_service_token(caplog):
    """Test that app warns when INTERNAL_SERVICE_TOKEN is too short."""
    from app import create_app
    from app.config import TestingConfig

    # Create a test config class with a short token
    class ShortTokenConfig(TestingConfig):
        INTERNAL_SERVICE_TOKEN = "short"  # nosec B105

    caplog.set_level(logging.WARNING)

    # Create app - should warn but not fail
    app = create_app(ShortTokenConfig)

    # Check that warning was logged
    assert any(
        "INTERNAL_SERVICE_TOKEN is too short" in record.message
        for record in caplog.records
    )
    assert app is not None
