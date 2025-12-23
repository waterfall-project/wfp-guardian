# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Tests for Identity service client."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
import requests
from flask import Flask


@pytest.fixture
def app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config["IDENTITY_SERVICE_URL"] = "https://identity.example.com"
    app.config["EXTERNAL_SERVICES_TIMEOUT"] = 5
    return app


@pytest.fixture
def user_id():
    """Sample user UUID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def company_id():
    """Sample company UUID."""
    return UUID("87654321-4321-8765-4321-876543218765")


class TestGetUser:
    """Tests for get_user function."""

    def test_get_user_success(self, app, user_id):
        """Test successful user retrieval."""
        from app.services.identity_client import get_user

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": str(user_id),
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "company_id": "87654321-4321-8765-4321-876543218765",
            "is_active": True,
        }

        with (
            app.test_request_context(
                "/", headers={"Cookie": "access_token=test_token"}
            ),
            patch("requests.get", return_value=mock_response) as mock_get,
        ):
            result = get_user(user_id)

            assert result is not None
            assert result["email"] == "test@example.com"
            assert result["first_name"] == "John"
            assert result["is_active"] is True

            # Verify cookies were forwarded
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args.kwargs
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"]["access_token"] == "test_token"

    def test_get_user_with_company_id(self, app, user_id, company_id):
        """Test user retrieval with company_id parameter."""
        from app.services.identity_client import get_user

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": str(user_id),
            "email": "test@example.com",
            "company_id": str(company_id),
            "is_active": True,
        }

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response) as mock_get,
        ):
            result = get_user(user_id, company_id)

            assert result is not None
            # Verify company_id was passed as parameter
            call_kwargs = mock_get.call_args.kwargs
            assert "params" in call_kwargs
            assert call_kwargs["params"]["company_id"] == str(company_id)

    def test_get_user_not_found(self, app, user_id):
        """Test user not found (404)."""
        from app.services.identity_client import get_user

        mock_response = MagicMock()
        mock_response.status_code = 404

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            result = get_user(user_id)

            assert result is None

    def test_get_user_request_exception(self, app, user_id):
        """Test request exception handling."""
        from app.services.identity_client import get_user

        with (
            app.test_request_context("/"),
            patch("requests.get", side_effect=requests.RequestException("Error")),
        ):
            result = get_user(user_id)

            assert result is None


class TestGetCompanyHierarchy:
    """Tests for get_company_hierarchy function."""

    def test_get_company_hierarchy_success(self, app, company_id):
        """Test successful company hierarchy retrieval."""
        from app.services.identity_client import get_company_hierarchy

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "company_id": str(company_id),
            "parent_id": "00000000-0000-0000-0000-000000000001",
            "children_ids": ["11111111-1111-1111-1111-111111111111"],
            "depth": 2,
            "path": [
                "00000000-0000-0000-0000-000000000001",
                str(company_id),
            ],
        }

        with (
            app.test_request_context(
                "/", headers={"Cookie": "access_token=test_token"}
            ),
            patch("requests.get", return_value=mock_response) as mock_get,
        ):
            result = get_company_hierarchy(company_id)

            assert result is not None
            assert result["company_id"] == str(company_id)
            assert result["depth"] == 2
            assert len(result["path"]) == 2

            # Verify cookies were forwarded
            call_kwargs = mock_get.call_args.kwargs
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"]["access_token"] == "test_token"

    def test_get_company_hierarchy_not_found(self, app, company_id):
        """Test company hierarchy not found (404)."""
        from app.services.identity_client import get_company_hierarchy

        mock_response = MagicMock()
        mock_response.status_code = 404

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            result = get_company_hierarchy(company_id)

            assert result is None

    def test_get_company_hierarchy_request_exception(self, app, company_id):
        """Test request exception handling."""
        from app.services.identity_client import get_company_hierarchy

        with (
            app.test_request_context("/"),
            patch("requests.get", side_effect=requests.RequestException("Error")),
        ):
            result = get_company_hierarchy(company_id)

            assert result is None


class TestValidateUserCompanyAccess:
    """Tests for validate_user_company_access function."""

    def test_validate_access_same_company(self, app, user_id, company_id):
        """Test validation when user's company matches requested company."""
        from app.services.identity_client import validate_user_company_access

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": str(user_id),
            "company_id": str(company_id),
            "is_active": True,
        }

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_user_response),
        ):
            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is True
            assert error == ""

    def test_validate_access_parent_company(self, app, user_id, company_id):
        """Test validation when user is from parent company (should allow)."""
        from app.services.identity_client import validate_user_company_access

        parent_company_id = UUID("00000000-0000-0000-0000-000000000001")

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": str(user_id),
            "company_id": str(parent_company_id),
            "is_active": True,
        }

        mock_hierarchy_response = MagicMock()
        mock_hierarchy_response.status_code = 200
        mock_hierarchy_response.json.return_value = {
            "company_id": str(company_id),
            "parent_id": str(parent_company_id),
            "path": [str(parent_company_id), str(company_id)],
        }

        with app.test_request_context("/"), patch("requests.get") as mock_get:
            # First call returns user, second call returns hierarchy
            mock_get.side_effect = [mock_user_response, mock_hierarchy_response]

            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is True
            assert error == ""

    def test_validate_access_different_company_not_parent(
        self, app, user_id, company_id
    ):
        """Test validation when user is from different, non-parent company (should deny)."""
        from app.services.identity_client import validate_user_company_access

        other_company_id = UUID("11111111-1111-1111-1111-111111111111")

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": str(user_id),
            "company_id": str(other_company_id),
            "is_active": True,
        }

        mock_hierarchy_response = MagicMock()
        mock_hierarchy_response.status_code = 200
        mock_hierarchy_response.json.return_value = {
            "company_id": str(company_id),
            "parent_id": "00000000-0000-0000-0000-000000000001",
            "path": ["00000000-0000-0000-0000-000000000001", str(company_id)],
        }

        with app.test_request_context("/"), patch("requests.get") as mock_get:
            mock_get.side_effect = [mock_user_response, mock_hierarchy_response]

            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is False
            assert "Access denied" in error

    def test_validate_access_user_not_found(self, app, user_id, company_id):
        """Test validation when user is not found."""
        from app.services.identity_client import validate_user_company_access

        mock_response = MagicMock()
        mock_response.status_code = 404

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is False
            assert "not found" in error

    def test_validate_access_user_inactive(self, app, user_id, company_id):
        """Test validation when user is inactive."""
        from app.services.identity_client import validate_user_company_access

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": str(user_id),
            "company_id": str(company_id),
            "is_active": False,
        }

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is False
            assert "not active" in error

    def test_validate_access_user_no_company(self, app, user_id, company_id):
        """Test validation when user has no company assigned."""
        from app.services.identity_client import validate_user_company_access

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": str(user_id),
            "is_active": True,
        }

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is False
            assert "no company assigned" in error

    def test_validate_access_hierarchy_unavailable(self, app, user_id, company_id):
        """Test validation when hierarchy cannot be retrieved."""
        from app.services.identity_client import validate_user_company_access

        other_company_id = UUID("11111111-1111-1111-1111-111111111111")

        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "id": str(user_id),
            "company_id": str(other_company_id),
            "is_active": True,
        }

        mock_hierarchy_response = MagicMock()
        mock_hierarchy_response.status_code = 500

        with app.test_request_context("/"), patch("requests.get") as mock_get:
            mock_get.side_effect = [mock_user_response, mock_hierarchy_response]

            is_authorized, error = validate_user_company_access(user_id, company_id)

            assert is_authorized is False
            assert "hierarchy" in error
