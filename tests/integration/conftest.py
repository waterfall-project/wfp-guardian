# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Integration tests configuration.

This conftest.py is for integration tests that run against real services
(PostgreSQL, Redis, Identity, Guardian) running in Docker containers.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pytest import fixture

from app import create_app
from app.models.db import db

# Load integration testing environment
dotenv_path = Path(__file__).parent.parent.parent / ".env.integration"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)

# Ensure we're in testing mode
os.environ["FLASK_ENV"] = "testing"

# Disable rate limiting for tests
os.environ["RATELIMIT_ENABLED"] = "false"
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"


@fixture(scope="session")
def app():
    """Create Flask application for integration testing.

    This uses real external services (PostgreSQL, Redis, Identity, Guardian)
    running in Docker containers.
    """
    app = create_app("app.config.TestingConfig")

    with app.app_context():
        # Create all database tables
        db.create_all()
        yield app

        # Clean up
        db.drop_all()
        db.session.remove()
        db.engine.dispose()


@fixture(scope="function")
def client(app):
    """Create test client for making HTTP requests."""
    return app.test_client()


@fixture(scope="function")
def session(app):
    """Provide database session for tests."""
    with app.app_context():
        # Start a nested transaction
        db.session.begin_nested()
        yield db.session

        # Rollback after each test to keep database clean
        db.session.rollback()


@fixture
def api_version(app):
    """Get API version prefix from VERSION file."""
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    try:
        version = version_file.read_text().strip()
        major_version = version.split(".")[0]
        return f"v{major_version}"
    except (FileNotFoundError, IndexError):
        return "v0"


@fixture
def authenticated_client(client):
    """Create an authenticated test client.

    Since USE_IDENTITY_SERVICE and USE_GUARDIAN_SERVICE are disabled in tests,
    no actual JWT is needed. The decorators will be bypassed.
    """
    return client


@fixture
def api_url(api_version):
    """Build API URL with version prefix."""

    def _build_url(path: str) -> str:
        """Build full API URL for given path.

        Args:
            path: API path (e.g., 'dummies', 'dummies/123')

        Returns:
            Full URL with version prefix (e.g., '/v0/dummies')
        """
        # Remove leading slash if present
        path = path.lstrip("/")
        return f"/{api_version}/{path}"

    return _build_url
