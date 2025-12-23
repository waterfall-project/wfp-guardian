# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for health endpoint."""

from datetime import datetime
from unittest.mock import patch


class TestHealthEndpoint:
    """Test cases for the /health endpoint."""

    def test_health_endpoint_returns_ok_status(self, client, api_url):
        """Test that health endpoint returns ok status."""
        response = client.get(api_url("health"))

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_health_endpoint_timestamp_format(self, client, api_url):
        """Test that health endpoint returns proper ISO timestamp."""
        response = client.get(api_url("health"))
        data = response.get_json()

        # Verify timestamp is in ISO format with Z suffix
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        # Should be parseable as ISO format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_health_endpoint_no_authentication_required(self, client, api_url):
        """Test that health endpoint is publicly accessible."""
        # No JWT token should be required
        response = client.get(api_url("health"))
        assert response.status_code == 200

    @patch("app.resources.health.limiter.limit")
    def test_health_endpoint_has_rate_limiting(self, mock_limit, client):
        """Test that health endpoint has rate limiting configured."""
        # The decorator should be applied
        from app.resources.health import HealthResource

        # Check that the get method has the limiter decorator
        assert hasattr(HealthResource.get, "__wrapped__")

    def test_health_endpoint_response_structure(self, client, api_url):
        """Test that health endpoint returns correct response structure."""
        response = client.get(api_url("health"))
        data = response.get_json()

        # Should only have status and timestamp
        assert set(data.keys()) == {"status", "timestamp"}
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
