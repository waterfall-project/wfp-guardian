# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Tests for Guardian service client."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
import requests
from flask import Flask


@pytest.fixture
def app():
    """Create Flask application for testing."""
    app = Flask(__name__)
    app.config["GUARDIAN_SERVICE_URL"] = "https://guardian.example.com"
    app.config["EXTERNAL_SERVICES_TIMEOUT"] = 5
    app.config["USE_GUARDIAN_SERVICE"] = True
    return app


@pytest.fixture
def user_id():
    """Sample user UUID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def company_id():
    """Sample company UUID."""
    return UUID("87654321-4321-8765-4321-876543218765")


@pytest.fixture
def project_id():
    """Sample project UUID."""
    return UUID("11111111-1111-1111-1111-111111111111")


class TestCheckAccess:
    """Tests for check_access function."""

    def test_check_access_granted(self, app, user_id):
        """Test successful access check with access granted."""
        from app.services.guardian_client import check_access

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_granted": True,
            "reason": "permission_granted",
            "message": "User has required permissions",
        }

        with (
            app.test_request_context(
                "/", headers={"Cookie": "access_token=test_token"}
            ),
            patch("requests.post", return_value=mock_response) as mock_post,
        ):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="projects",
                operation="READ",
            )

            assert result is not None
            assert result["access_granted"] is True
            assert result["reason"] == "permission_granted"
            assert result["message"] == "User has required permissions"

            # Verify the correct URL was called
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://guardian.example.com/check-access"

            # Verify payload
            call_kwargs = call_args.kwargs
            assert "json" in call_kwargs
            payload = call_kwargs["json"]
            assert payload["service"] == "project"
            assert payload["resource"] == "projects"
            assert payload["operation"] == "READ"
            assert payload["context"] == {}

            # Verify cookies were forwarded
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"]["access_token"] == "test_token"

    def test_check_access_denied(self, app, user_id):
        """Test access check with access denied."""
        from app.services.guardian_client import check_access

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_granted": False,
            "reason": "insufficient_permissions",
            "message": "User lacks required permissions",
        }

        with (
            app.test_request_context("/"),
            patch("requests.post", return_value=mock_response),
        ):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="projects",
                operation="DELETE",
            )

            assert result is not None
            assert result["access_granted"] is False
            assert result["reason"] == "insufficient_permissions"

    def test_check_access_with_context(self, app, user_id, project_id):
        """Test access check with context parameters."""
        from app.services.guardian_client import check_access

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_granted": True,
            "reason": "permission_granted",
            "message": "Access granted",
        }

        context = {"project_id": str(project_id)}

        with (
            app.test_request_context("/"),
            patch("requests.post", return_value=mock_response) as mock_post,
        ):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="milestones",
                operation="UPDATE",
                context=context,
            )

            assert result is not None
            assert result["access_granted"] is True

            # Verify context was passed
            call_kwargs = mock_post.call_args.kwargs
            payload = call_kwargs["json"]
            assert payload["context"] == context

    def test_check_access_guardian_disabled(self, app, user_id):
        """Test access check when Guardian service is disabled."""
        from app.services.guardian_client import check_access

        app.config["USE_GUARDIAN_SERVICE"] = False

        with app.test_request_context("/"):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="projects",
                operation="READ",
            )

            assert result is not None
            assert result["access_granted"] is True
            assert result["reason"] == "guardian_disabled"
            assert "Guardian service disabled" in result["message"]

    def test_check_access_timeout(self, app, user_id):
        """Test access check with timeout."""
        from app.services.guardian_client import check_access

        with (
            app.test_request_context("/"),
            patch("requests.post", side_effect=requests.Timeout),
        ):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="projects",
                operation="READ",
            )

            assert result is not None
            assert result["access_granted"] is False
            assert result["reason"] == "guardian_timeout"
            assert "unavailable" in result["message"].lower()

    def test_check_access_http_error(self, app, user_id):
        """Test access check with HTTP error."""
        from app.services.guardian_client import check_access

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "Internal Server Error"
        )

        with (
            app.test_request_context("/"),
            patch("requests.post", return_value=mock_response),
        ):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="projects",
                operation="READ",
            )

            assert result is not None
            assert result["access_granted"] is False
            assert result["reason"] == "guardian_error"

    def test_check_access_no_cookies(self, app, user_id):
        """Test access check without cookies in request."""
        from app.services.guardian_client import check_access

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_granted": True,
            "reason": "permission_granted",
            "message": "Access granted",
        }

        with (
            app.test_request_context("/"),
            patch("requests.post", return_value=mock_response) as mock_post,
        ):
            result = check_access(
                user_id=user_id,
                service="project",
                resource="projects",
                operation="READ",
            )

            assert result is not None
            assert result["access_granted"] is True

            # Verify empty cookies were passed
            call_kwargs = mock_post.call_args.kwargs
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"] == {}


class TestGetUserPermissions:
    """Tests for get_user_permissions function."""

    def test_get_user_permissions_success(self, app, user_id, company_id):
        """Test successful retrieval of user permissions."""
        from app.services.guardian_client import get_user_permissions

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "permissions": [
                {
                    "permission": "project:projects:READ",
                    "project_id": None,
                    "scope_type": "direct",
                    "role_name": "Company Admin",
                },
                {
                    "permission": "project:projects:UPDATE",
                    "project_id": "11111111-1111-1111-1111-111111111111",
                    "scope_type": "hierarchical",
                    "role_name": "Project Manager",
                },
            ]
        }

        with (
            app.test_request_context(
                "/", headers={"Cookie": "access_token=test_token"}
            ),
            patch("requests.get", return_value=mock_response) as mock_get,
        ):
            result = get_user_permissions(user_id, company_id)

            assert result is not None
            assert "permissions" in result
            assert len(result["permissions"]) == 2

            # Verify first permission (company-wide)
            perm1 = result["permissions"][0]
            assert perm1["permission"] == "project:projects:READ"
            assert perm1["project_id"] is None
            assert perm1["scope_type"] == "direct"
            assert perm1["role_name"] == "Company Admin"

            # Verify second permission (project-scoped)
            perm2 = result["permissions"][1]
            assert perm2["permission"] == "project:projects:UPDATE"
            assert perm2["project_id"] == "11111111-1111-1111-1111-111111111111"
            assert perm2["scope_type"] == "hierarchical"

            # Verify the correct URL was called
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            expected_url = f"https://guardian.example.com/users/{user_id}/permissions"
            assert call_args[0][0] == expected_url

            # Verify company_id was passed as parameter
            call_kwargs = call_args.kwargs
            assert "params" in call_kwargs
            assert call_kwargs["params"]["company_id"] == str(company_id)

            # Verify cookies were forwarded
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"]["access_token"] == "test_token"

    def test_get_user_permissions_empty(self, app, user_id, company_id):
        """Test retrieval with no permissions."""
        from app.services.guardian_client import get_user_permissions

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"permissions": []}

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            result = get_user_permissions(user_id, company_id)

            assert result is not None
            assert "permissions" in result
            assert len(result["permissions"]) == 0

    def test_get_user_permissions_guardian_disabled(self, app, user_id, company_id):
        """Test permissions retrieval when Guardian service is disabled."""
        from app.services.guardian_client import get_user_permissions

        app.config["USE_GUARDIAN_SERVICE"] = False

        with app.test_request_context("/"):
            result = get_user_permissions(user_id, company_id)

            assert result is not None
            assert "permissions" in result
            assert len(result["permissions"]) == 0

    def test_get_user_permissions_timeout(self, app, user_id, company_id):
        """Test permissions retrieval with timeout."""
        from app.services.guardian_client import get_user_permissions

        with (
            app.test_request_context("/"),
            patch("requests.get", side_effect=requests.Timeout),
        ):
            result = get_user_permissions(user_id, company_id)

            assert result is not None
            assert "permissions" in result
            assert len(result["permissions"]) == 0

    def test_get_user_permissions_http_error(self, app, user_id, company_id):
        """Test permissions retrieval with HTTP error."""
        from app.services.guardian_client import get_user_permissions

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "Internal Server Error"
        )

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response),
        ):
            result = get_user_permissions(user_id, company_id)

            assert result is not None
            assert "permissions" in result
            assert len(result["permissions"]) == 0

    def test_get_user_permissions_no_cookies(self, app, user_id, company_id):
        """Test permissions retrieval without cookies in request."""
        from app.services.guardian_client import get_user_permissions

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"permissions": []}

        with (
            app.test_request_context("/"),
            patch("requests.get", return_value=mock_response) as mock_get,
        ):
            result = get_user_permissions(user_id, company_id)

            assert result is not None

            # Verify empty cookies were passed
            call_kwargs = mock_get.call_args.kwargs
            assert "cookies" in call_kwargs
            assert call_kwargs["cookies"] == {}
