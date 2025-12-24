# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Integration tests for Dummy CRUD operations.

These tests verify the complete CRUD functionality for Dummy resources
in a real environment with all services configured.
"""

import pytest


@pytest.mark.skip(reason="Dummy endpoints are disabled in routes.py")
class TestDummyCRUD:
    """Integration tests for Dummy resource CRUD operations."""

    def test_create_dummy_success(self, authenticated_client, api_url, session):
        """Test successful dummy creation."""
        payload = {"name": "Integration Test Dummy", "description": "Test description"}

        response = authenticated_client.post(
            api_url("dummies"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Integration Test Dummy"
        assert data["description"] == "Test description"
        assert "id" in data

    def test_create_dummy_with_metadata(self, authenticated_client, api_url, session):
        """Test dummy creation with extra metadata."""
        payload = {
            "name": "Dummy with Metadata",
            "description": "Test",
            "extra_metadata": {"key1": "value1", "key2": 123},
        }

        response = authenticated_client.post(
            api_url("dummies"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["extra_metadata"]["key1"] == "value1"
        assert data["extra_metadata"]["key2"] == 123

    def test_get_dummy_list(self, authenticated_client, api_url, session):
        """Test retrieving list of dummies."""
        from app.models.dummy_model import Dummy

        # Create test data
        Dummy.create("Dummy 1", "Description 1")
        Dummy.create("Dummy 2", "Description 2")
        session.commit()

        response = authenticated_client.get(api_url("dummies"))

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_get_dummy_by_id(self, authenticated_client, api_url, session):
        """Test retrieving a specific dummy by ID."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("Get Test", "Description")
        session.commit()

        response = authenticated_client.get(api_url(f"dummies/{dummy.id}"))

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Get Test"
        assert data["id"] == str(dummy.id)

    def test_update_dummy_put(self, authenticated_client, api_url, session):
        """Test full update (PUT) of a dummy."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("Original Name", "Original Description")
        session.commit()

        payload = {"name": "Updated Name", "description": "Updated Description"}

        response = authenticated_client.put(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Description"

    def test_update_dummy_patch(self, authenticated_client, api_url, session):
        """Test partial update (PATCH) of a dummy."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("Original", "Original Description")
        session.commit()

        payload = {"description": "Patched Description"}

        response = authenticated_client.patch(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Original"  # Name unchanged
        assert data["description"] == "Patched Description"

    def test_update_dummy_keep_same_name(self, authenticated_client, api_url, session):
        """Test that updating a dummy with its own name works (no uniqueness error)."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("Same Name", "Description")
        session.commit()

        # Update with the same name should work
        payload = {"name": "Same Name", "description": "New Description"}

        response = authenticated_client.put(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Same Name"
        assert data["description"] == "New Description"

    def test_delete_dummy(self, authenticated_client, api_url, session):
        """Test deleting a dummy."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("To Delete", "Will be deleted")
        session.commit()
        dummy_id = dummy.id

        response = authenticated_client.delete(api_url(f"dummies/{dummy_id}"))

        assert response.status_code == 204

        # Verify deletion
        response = authenticated_client.get(api_url(f"dummies/{dummy_id}"))
        assert response.status_code == 404

    def test_pagination(self, authenticated_client, api_url, session):
        """Test pagination parameters."""
        from app.models.dummy_model import Dummy

        # Create multiple dummies
        for i in range(15):
            Dummy.create(f"Dummy {i}", f"Description {i}")
        session.commit()

        # Test with limit
        response = authenticated_client.get(api_url("dummies?limit=5"))
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 5

        # Test with offset
        response = authenticated_client.get(api_url("dummies?limit=5&offset=5"))
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 5

    def test_validation_errors(self, authenticated_client, api_url):
        """Test that validation errors are properly returned."""
        # Name too long
        payload = {"name": "x" * 51}

        response = authenticated_client.post(
            api_url("dummies"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data
        assert "name" in data["errors"]

    def test_create_without_data(self, authenticated_client, api_url):
        """Test POST without JSON data."""
        response = authenticated_client.post(
            api_url("dummies"),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "message" in data

    def test_put_without_data(self, authenticated_client, api_url, session):
        """Test PUT without JSON data."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("Test", "Description")
        session.commit()

        response = authenticated_client.put(
            api_url(f"dummies/{dummy.id}"),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "message" in data

    def test_patch_without_data(self, authenticated_client, api_url, session):
        """Test PATCH without JSON data."""
        from app.models.dummy_model import Dummy

        dummy = Dummy.create("Test", "Description")
        session.commit()

        response = authenticated_client.patch(
            api_url(f"dummies/{dummy.id}"),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "message" in data
