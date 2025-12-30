# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit test configuration and fixtures.

This module provides pytest fixtures for unit testing the Flask application.
It configures the test environment, sets up the database, and provides
common utilities like test clients and API URL builders.

The environment is configured to prevent loading .env.development by setting
APP_MODE=testing before importing application modules.

Fixtures:
    app: Flask application instance with test database.
    client: Test client for HTTP requests.
    session: Database session for direct data manipulation.
    authenticated_client: Pre-authenticated test client.
    api_version: API version prefix (e.g., 'v0').
    api_url: Function to build versioned API URLs.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pytest import fixture

# Import app modules at top but use lazy loading in fixtures
# Set APP_MODE BEFORE any app imports to prevent loading .env.development
os.environ["APP_MODE"] = "testing"
os.environ["FLASK_ENV"] = "testing"
os.environ["USE_IDENTITY_SERVICE"] = "false"
os.environ["USE_GUARDIAN_SERVICE"] = "false"
os.environ["RATELIMIT_ENABLED"] = "false"
os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["PAGE_LIMIT"] = "20"
os.environ["MAX_PAGE_LIMIT"] = "100"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["INTERNAL_SERVICE_TOKEN"] = "test-internal-token-for-bootstrap-endpoints"  # nosec B105

# Now load .env.testing which will override any remaining defaults
dotenv_path = Path(__file__).parent.parent.parent / ".env.testing"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)

# Import app modules AFTER environment is configured  # noqa: E402
from app import create_app  # noqa: E402
from app.models.db import db  # noqa: E402


@fixture
def app():
    """Create and configure a Flask application for testing.

    Sets up the application context, initializes the database, and ensures
    that the database is created before tests run and dropped after tests complete.

    Yields:
        Flask: The configured Flask application instance.
    """
    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
        # Close database connection explicitly to avoid ResourceWarning
        db.session.remove()
        db.engine.dispose()


@fixture
def client(app):
    """Create a test client for the Flask application.

    Args:
        app: The Flask application fixture.

    Returns:
        FlaskClient: Test client for simulating HTTP requests.
    """
    return app.test_client()


@fixture
def session(app):
    """Provide a database session for tests.

    This session is scoped to the application context and can be used
    to interact with the database during tests.

    Args:
        app: The Flask application fixture.

    Yields:
        Session: SQLAlchemy database session.
    """
    with app.app_context():
        yield db.session


@fixture
def authenticated_client(client):
    """Create an authenticated test client.

    Since USE_IDENTITY_SERVICE is False in tests, no actual JWT is needed.
    The decorators will be bypassed.

    Args:
        client: The test client fixture.

    Returns:
        FlaskClient: Authenticated test client.
    """
    return client


@fixture
def api_version():
    """Get the API version prefix from VERSION file.

    Returns the major version in format 'vX' (e.g., 'v0', 'v1').
    This ensures tests stay in sync with the actual API version.

    Returns:
        str: API version prefix (e.g., 'v0').
    """
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    try:
        version = version_file.read_text().strip()
        major_version = version.split(".")[0]
        return f"v{major_version}"
    except (FileNotFoundError, IndexError):
        return "v0"


@fixture
def api_url(api_version):
    """Construct API URLs with the correct version prefix.

    Args:
        api_version: The API version fixture.

    Returns:
        callable: Function that builds versioned API URLs.

    Example:
        api_url('health') returns '/v0/health'
    """

    def _build_url(path: str) -> str:
        """Build a versioned API URL.

        Args:
            path: API path (with or without leading slash).

        Returns:
            str: Complete versioned API path.
        """
        if path.startswith("/"):
            path = path[1:]
        return f"/{api_version}/{path}"

    return _build_url


@fixture
def sample_company_id():
    """Provide a sample company UUID for testing.

    Returns the same UUID as MOCK_COMPANY_ID from environment to ensure consistency
    between test data and authenticated requests.

    Returns:
        UUID: The company_id used by @require_jwt_auth decorator in test mode.
    """
    from uuid import UUID

    mock_company_id = os.environ.get(
        "MOCK_COMPANY_ID", "00000000-0000-0000-0000-000000000001"
    )
    return UUID(mock_company_id)


@fixture
def sample_user_id():
    """Provide a sample user UUID for testing.

    Returns the same UUID as MOCK_USER_ID from environment to ensure consistency
    between test data and authenticated requests.

    Returns:
        UUID: The user_id used by @require_jwt_auth decorator in test mode.
    """
    from uuid import UUID

    mock_user_id = os.environ.get(
        "MOCK_USER_ID", "00000000-0000-0000-0000-000000000001"
    )
    return UUID(mock_user_id)
