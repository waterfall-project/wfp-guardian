# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for ready endpoint."""

from datetime import datetime
from unittest.mock import MagicMock, patch


class TestReadyEndpoint:
    """Test cases for the /ready endpoint."""

    def test_ready_endpoint_returns_ready_status(self, client, api_url):
        """Test that ready endpoint returns ready status when all checks pass."""
        with patch("app.resources.ready.db.session.execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ready"
            assert "checks" in data
            assert "timestamp" in data

    def test_ready_endpoint_checks_structure(self, client, api_url):
        """Test that ready endpoint returns all required checks."""
        with patch("app.resources.ready.db.session.execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            checks = data["checks"]
            assert "database" in checks
            assert "redis" in checks
            assert "guardian" in checks
            assert "identity" in checks

            # Each check should have status and latency_ms
            for _service_name, check in checks.items():
                assert "status" in check
                assert "latency_ms" in check
                assert check["status"] in ["ok", "error"]
                assert isinstance(check["latency_ms"], (int, float))

    def test_ready_endpoint_database_check_failure(self, client, api_url):
        """Test that ready endpoint returns degraded when database fails."""
        with patch("app.resources.ready.ReadyResource._check_database") as mock_check:
            mock_check.return_value = {"healthy": False, "latency_ms": 0}

            response = client.get(api_url("ready"))

            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "degraded"
            assert data["checks"]["database"]["status"] == "error"

    def test_ready_endpoint_timestamp_format(self, client, api_url):
        """Test that ready endpoint returns proper ISO timestamp."""
        with patch("app.resources.ready.db.session.execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            # Verify timestamp is in ISO format with Z suffix
            timestamp = data["timestamp"]
            assert timestamp.endswith("Z")
            # Should be parseable as ISO format
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_ready_endpoint_no_authentication_required(self, client, api_url):
        """Test that ready endpoint is publicly accessible."""
        with patch("app.resources.ready.db.session.execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            # No JWT token should be required
            response = client.get(api_url("ready"))
            assert response.status_code == 200

    def test_ready_endpoint_disabled_services_show_ok(self, client, api_url):
        """Test that disabled services show as ok with 0 latency."""
        with patch("app.resources.ready.db.session.execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            # Redis, Guardian, and Identity should be disabled in tests
            assert data["checks"]["redis"]["status"] == "ok"
            assert data["checks"]["redis"]["latency_ms"] == 0
            assert data["checks"]["guardian"]["status"] == "ok"
            assert data["checks"]["guardian"]["latency_ms"] == 0
            assert data["checks"]["identity"]["status"] == "ok"
            assert data["checks"]["identity"]["latency_ms"] == 0

    @patch("app.resources.ready.requests.get")
    def test_ready_endpoint_guardian_service_check(self, mock_get, app, api_url):
        """Test guardian service check when enabled."""
        # Enable guardian service temporarily
        app.config["USE_GUARDIAN_SERVICE"] = True
        app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8001"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with (
            app.test_client() as client,
            patch("app.resources.ready.db.session.execute") as mock_execute,
        ):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            assert data["checks"]["guardian"]["status"] == "ok"
            assert data["checks"]["guardian"]["latency_ms"] > 0
            mock_get.assert_called_once()

    @patch("app.resources.ready.requests.get")
    def test_ready_endpoint_identity_service_check(self, mock_get, app, api_url):
        """Test identity service check when enabled."""
        # Enable identity service temporarily
        app.config["USE_IDENTITY_SERVICE"] = True
        app.config["IDENTITY_SERVICE_URL"] = "http://identity:8002"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with (
            app.test_client() as client,
            patch("app.resources.ready.db.session.execute") as mock_execute,
        ):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            assert data["checks"]["identity"]["status"] == "ok"
            assert data["checks"]["identity"]["latency_ms"] > 0
            mock_get.assert_called_once()

    @patch("app.resources.ready.limiter.limit")
    def test_ready_endpoint_has_rate_limiting(self, mock_limit, client, api_url):
        """Test that ready endpoint has rate limiting configured."""
        from app.resources.ready import ReadyResource

        # Check that the get method has the limiter decorator
        assert hasattr(ReadyResource.get, "__wrapped__")


class TestReadyServiceChecks:
    """Test individual service check methods for increased coverage."""

    @patch("app.resources.ready.requests.get")
    def test_guardian_check_when_enabled_failure(self, mock_get, app, api_url):
        """Test Guardian check when service is enabled but fails."""
        app.config["USE_GUARDIAN_SERVICE"] = True
        app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8001"

        # Mock request failure
        mock_get.side_effect = Exception("Connection timeout")

        with (
            app.test_client() as client,
            patch("app.resources.ready.db.session.execute") as mock_execute,
        ):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            assert response.status_code == 503
            assert data["status"] == "degraded"
            assert data["checks"]["guardian"]["status"] == "error"

    @patch("app.resources.ready.requests.get")
    def test_guardian_check_http_error(self, mock_get, app, api_url):
        """Test Guardian check when service returns non-200 status."""
        app.config["USE_GUARDIAN_SERVICE"] = True
        app.config["GUARDIAN_SERVICE_URL"] = "http://guardian:8001"

        # Mock non-200 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal Server Error")
        mock_get.return_value = mock_response

        with (
            app.test_client() as client,
            patch("app.resources.ready.db.session.execute") as mock_execute,
        ):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            assert response.status_code == 503
            assert data["checks"]["guardian"]["status"] == "error"

    @patch("app.resources.ready.requests.get")
    def test_identity_check_when_enabled_failure(self, mock_get, app, api_url):
        """Test Identity check when service is enabled but fails."""
        app.config["USE_IDENTITY_SERVICE"] = True
        app.config["IDENTITY_SERVICE_URL"] = "http://identity:8002"

        # Mock request failure
        mock_get.side_effect = Exception("Service unavailable")

        with (
            app.test_client() as client,
            patch("app.resources.ready.db.session.execute") as mock_execute,
        ):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            assert response.status_code == 503
            assert data["status"] == "degraded"
            assert data["checks"]["identity"]["status"] == "error"

    @patch("app.resources.ready.requests.get")
    def test_identity_check_http_error(self, mock_get, app, api_url):
        """Test Identity check when service returns non-200 status."""
        app.config["USE_IDENTITY_SERVICE"] = True
        app.config["IDENTITY_SERVICE_URL"] = "http://identity:8002"

        # Mock non-200 response
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = Exception("Service Unavailable")
        mock_get.return_value = mock_response

        with (
            app.test_client() as client,
            patch("app.resources.ready.db.session.execute") as mock_execute,
        ):
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_execute.return_value = mock_result

            response = client.get(api_url("ready"))
            data = response.get_json()

            assert response.status_code == 503
            assert data["checks"]["identity"]["status"] == "error"
