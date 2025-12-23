# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""
Tests for the WSGI entrypoint.

This module contains tests for the WSGI entrypoint to ensure the correct configuration
class is selected based on the FLASK_ENV environment variable.
"""

import importlib
import os
import sys

import pytest


@pytest.mark.parametrize(
    "flask_env,expected_config",
    [
        ("development", "app.config.DevelopmentConfig"),
        ("testing", "app.config.TestingConfig"),
        ("integration", "app.config.IntegrationConfig"),
        ("staging", "app.config.StagingConfig"),
        ("production", "app.config.ProductionConfig"),
    ],
)
def test_wsgi_respects_flask_env(flask_env, expected_config, monkeypatch):
    """
    Test that the WSGI entrypoint respects FLASK_ENV environment variable.

    This test verifies that wsgi.py uses the configuration class based on
    FLASK_ENV for all supported environments.
    """
    # Patch app.create_app BEFORE importing wsgi
    captured = {}

    def fake_create_app(config_class):
        captured["config_class"] = config_class

        class DummyApp:
            """Dummy Flask application for testing."""

            def run(self):
                """Mock run method to prevent actual server startup."""

        return DummyApp()

    monkeypatch.setattr("app.create_app", fake_create_app)

    # Clean up any existing wsgi module
    if "wsgi" in sys.modules:
        del sys.modules["wsgi"]

    # Set FLASK_ENV
    os.environ["FLASK_ENV"] = flask_env

    try:
        wsgi = importlib.import_module("wsgi")

        # Verify the wsgi module has the app attribute
        assert hasattr(wsgi, "app")

        # Verify create_app was called with expected config
        assert "config_class" in captured, "create_app was not called"
        assert captured["config_class"] == expected_config

        # Verify FLASK_ENV was respected
        assert os.environ["FLASK_ENV"] == flask_env

    finally:
        # Clean up
        if "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]
        # Clean up wsgi module
        if "wsgi" in sys.modules:
            del sys.modules["wsgi"]


def test_wsgi_defaults_to_production(monkeypatch):
    """
    Test that the WSGI entrypoint defaults to ProductionConfig when FLASK_ENV is not set
    and .env.development is not loaded (e.g., in Docker).
    """
    # Patch app.create_app BEFORE importing wsgi
    captured = {}

    def fake_create_app(config_class):
        captured["config_class"] = config_class

        class DummyApp:
            """Dummy Flask application for testing."""

            def run(self):
                """Mock run method to prevent actual server startup."""

        return DummyApp()

    monkeypatch.setattr("app.create_app", fake_create_app)

    # Clean up any existing wsgi module
    if "wsgi" in sys.modules:
        del sys.modules["wsgi"]

    # Remove FLASK_ENV to test default behavior
    # Also remove any conftest.py set environment variables
    env_vars_to_clean = [
        "FLASK_ENV",
        "USE_IDENTITY_SERVICE",
        "USE_GUARDIAN_SERVICE",
        "LOG_LEVEL",
        "USE_REDIS_CACHE",
        "DEBUG",
        "TESTING",
        "SERVICE_PORT",
        "JWT_SECRET_KEY",
    ]
    for key in env_vars_to_clean:
        monkeypatch.delenv(key, raising=False)

    # Simulate being in Docker so .env.development is NOT loaded
    monkeypatch.setenv("IN_DOCKER_CONTAINER", "true")

    try:
        wsgi = importlib.import_module("wsgi")

        # Verify the wsgi module has the app attribute
        assert hasattr(wsgi, "app")

        # Verify create_app was called with ProductionConfig (default when no FLASK_ENV)
        assert "config_class" in captured, "create_app was not called"
        assert captured["config_class"] == "app.config.ProductionConfig"

    finally:
        # Module cleanup
        if "wsgi" in sys.modules:
            del sys.modules["wsgi"]
