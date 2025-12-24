# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Integration tests for error handlers.

These tests verify that error handlers work correctly in a real environment
with all services configured.
"""

import pytest


class TestErrorHandlers:
    """Integration tests for HTTP error handlers."""

    @pytest.mark.skip(reason="Dummy endpoints are disabled in routes.py")
    def test_unsupported_media_type_handler(self, authenticated_client, api_url):
        """Test the 415 unsupported media type error handler.

        This test sends a POST request to /v0/dummies with an unsupported
        Content-Type to trigger the 415 handler.
        """
        response = authenticated_client.post(
            api_url("dummies"),
            data='{"name": "test"}',
            content_type="text/plain",  # Invalid content type for this endpoint
        )

        assert response.status_code == 415
        data = response.get_json()
        assert "message" in data
        # Flask returns a specific message about Content-Type
        assert (
            "content-type" in data["message"].lower()
            or "unsupported media type" in data["message"].lower()
        )

    def test_method_not_allowed_handler(self, authenticated_client, api_url):
        """Test the 405 method not allowed error handler.

        This test sends a PUT request to /v0/health which only accepts GET,
        triggering the 405 handler.
        """
        response = authenticated_client.put(api_url("health"))

        assert response.status_code == 405
        data = response.get_json()
        assert "message" in data
        assert (
            "method" in data["message"].lower() or "allowed" in data["message"].lower()
        )

    def test_not_found_handler(self, authenticated_client, api_url):
        """Test the 404 not found error handler.

        This test requests a non-existent endpoint to trigger the 404 handler.
        """
        response = authenticated_client.get(api_url("nonexistent-endpoint"))

        assert response.status_code == 404
        data = response.get_json()
        assert "message" in data
        assert "not found" in data["message"].lower()

    @pytest.mark.skip(reason="Dummy endpoints are disabled in routes.py")
    def test_conflict_handler(self, authenticated_client, api_url, session):
        """Test the 409 conflict error handler.

        This test creates a dummy and then tries to create another with the same name,
        triggering an IntegrityError which should return 409.
        """
        from app.models.dummy_model import Dummy

        # Create first dummy
        Dummy.create("Conflict Test", "First")
        session.commit()

        # Try to create another with the same name (will trigger integrity error)
        payload = {"name": "Conflict Test", "description": "Second"}
        response = authenticated_client.post(
            api_url("dummies"),
            json=payload,
            content_type="application/json",
        )

        # Should get 422 from validation (uniqueness check in schema)
        # or 409 if it gets to the database
        assert response.status_code in [409, 422]
        data = response.get_json()
        assert "message" in data or "errors" in data

    @pytest.mark.skip(reason="Dummy endpoints are disabled in routes.py")
    def test_unprocessable_entity_handler(self, authenticated_client, api_url):
        """Test the 422 unprocessable entity error handler.

        This test sends invalid data to trigger validation errors which return 422.
        """
        # Send a request with an empty name (validation error)
        payload = {"name": ""}
        response = authenticated_client.post(
            api_url("dummies"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data
        assert "name" in data["errors"]
