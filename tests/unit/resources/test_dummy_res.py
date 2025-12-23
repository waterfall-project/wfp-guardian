# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Dummy REST resources."""

from unittest.mock import patch

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.dummy_model import Dummy


class TestDummyListResource:
    """Test cases for DummyListResource (GET list, POST create)."""

    def test_get_list_empty(self, authenticated_client, api_url):
        """Test GET list when no dummies exist."""
        response = authenticated_client.get(api_url("dummies"))

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert data == []

    def test_get_list_with_dummies(self, authenticated_client, api_url, session):
        """Test GET list with existing dummies."""
        # Create test dummies
        Dummy.create("Test 1", "Description 1")
        Dummy.create("Test 2", "Description 2")
        session.commit()

        response = authenticated_client.get(api_url("dummies"))

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_list_pagination_limit(self, authenticated_client, api_url, session):
        """Test GET list with limit parameter."""
        # Create 5 dummies
        for i in range(5):
            Dummy.create(f"Test {i}", f"Description {i}")
        session.commit()

        response = authenticated_client.get(api_url("dummies") + "?limit=3")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_get_list_pagination_offset(self, authenticated_client, api_url, session):
        """Test GET list with offset parameter."""
        # Create 5 dummies
        for i in range(5):
            Dummy.create(f"Test {i}", f"Description {i}")
        session.commit()

        response = authenticated_client.get(api_url("dummies") + "?offset=2&limit=2")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_get_list_limit_exceeds_max(self, authenticated_client, api_url, session):
        """Test GET list when requested limit exceeds MAX_PAGE_LIMIT."""
        # Create many dummies
        for i in range(10):
            Dummy.create(f"Test {i}", f"Description {i}")
        session.commit()

        response = authenticated_client.get(api_url("dummies") + "?limit=1000")

        assert response.status_code == 200
        data = response.get_json()
        # Current implementation doesn't cap limit, just returns what exists
        assert isinstance(data, list)
        assert len(data) == 10

    def test_post_create_success(self, authenticated_client, api_url):
        """Test POST create with valid data."""
        payload = {"name": "New Dummy", "description": "Test description"}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "New Dummy"
        assert data["description"] == "Test description"
        assert "id" in data
        assert "created_at" in data

    def test_post_create_with_metadata(self, authenticated_client, api_url):
        """Test POST create with extra_metadata."""
        payload = {
            "name": "Dummy with metadata",
            "description": "Test",
            "extra_metadata": {"key": "value", "number": 42},
        }

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["extra_metadata"] == {"key": "value", "number": 42}

    def test_post_create_minimal(self, authenticated_client, api_url):
        """Test POST create with only required fields."""
        payload = {"name": "Minimal Dummy"}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "Minimal Dummy"
        assert data["description"] is None

    def test_post_create_missing_name(self, authenticated_client, api_url):
        """Test POST create without required name field."""
        payload = {"description": "Missing name"}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data
        assert "name" in data["errors"]

    def test_post_create_empty_name(self, authenticated_client, api_url):
        """Test POST create with empty name."""
        payload = {"name": ""}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data

    def test_post_create_whitespace_name(self, authenticated_client, api_url):
        """Test POST create with whitespace-only name."""
        payload = {"name": "   "}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data

    def test_post_create_name_too_long(self, authenticated_client, api_url):
        """Test POST create with name exceeding max length."""
        payload = {"name": "x" * 51}  # Max is 50

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data
        assert "name" in data["errors"]

    def test_post_create_duplicate_name(self, authenticated_client, api_url, session):
        """Test POST create with duplicate name."""
        Dummy.create("Duplicate", "First")
        session.commit()

        payload = {"name": "Duplicate", "description": "Second"}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data

    @patch("app.resources.dummy_res.db.session.add")
    def test_post_create_integrity_error(self, mock_add, authenticated_client, api_url):
        """Test POST create with IntegrityError."""
        mock_add.side_effect = IntegrityError("statement", "params", Exception("orig"))

        payload = {"name": "Test"}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 409
        data = response.get_json()
        assert "message" in data

    @patch("app.resources.dummy_res.db.session.add")
    def test_post_create_database_error(self, mock_add, authenticated_client, api_url):
        """Test POST create with SQLAlchemyError."""
        mock_add.side_effect = SQLAlchemyError("Database error")

        payload = {"name": "Test"}

        response = authenticated_client.post(
            api_url("dummies"), json=payload, content_type="application/json"
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "message" in data


class TestDummyResource:
    """Test cases for DummyResource (GET, PUT, PATCH, DELETE by ID)."""

    def test_get_by_id_success(self, authenticated_client, api_url, session):
        """Test GET by ID with existing dummy."""
        dummy = Dummy.create("Test Dummy", "Test description")
        session.commit()

        response = authenticated_client.get(api_url(f"dummies/{dummy.id}"))

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == str(dummy.id)
        assert data["name"] == "Test Dummy"
        assert data["description"] == "Test description"

    def test_get_by_id_not_found(self, authenticated_client, api_url):
        """Test GET by ID with non-existent dummy."""
        fake_id = "00000000-0000-0000-0000-000000000001"
        response = authenticated_client.get(api_url(f"dummies/{fake_id}"))

        assert response.status_code == 404
        data = response.get_json()
        assert "message" in data

    def test_put_update_success(self, authenticated_client, api_url, session):
        """Test PUT update with valid data."""
        dummy = Dummy.create("Original", "Original description")
        session.commit()

        payload = {"name": "Updated", "description": "Updated description"}

        response = authenticated_client.put(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated"
        assert data["description"] == "Updated description"

    def test_put_update_not_found(self, authenticated_client, api_url):
        """Test PUT update with non-existent dummy."""
        fake_id = "00000000-0000-0000-0000-000000000001"
        payload = {"name": "Updated"}

        response = authenticated_client.put(
            api_url(f"dummies/{fake_id}"), json=payload, content_type="application/json"
        )

        assert response.status_code == 404

    def test_put_update_no_data(self, authenticated_client, api_url, session):
        """Test PUT update with no JSON data."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        response = authenticated_client.put(api_url(f"dummies/{dummy.id}"))

        assert (
            response.status_code == 415
        )  # Unsupported Media Type without Content-Type

    def test_put_update_missing_name(self, authenticated_client, api_url, session):
        """Test PUT update without required name."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        payload = {"description": "Only description"}

        response = authenticated_client.put(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 422
        data = response.get_json()
        assert "errors" in data

    def test_put_update_invalid_data(self, authenticated_client, api_url, session):
        """Test PUT update with invalid data."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        payload = {"name": "x" * 51}  # Too long

        response = authenticated_client.put(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 422

    def test_patch_partial_update_name(self, authenticated_client, api_url, session):
        """Test PATCH partial update of name only."""
        dummy = Dummy.create("Original", "Original description")
        session.commit()

        payload = {"name": "Updated Name"}

        response = authenticated_client.patch(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Original description"

    def test_patch_partial_update_description(
        self, authenticated_client, api_url, session
    ):
        """Test PATCH partial update of description only."""
        dummy = Dummy.create("Test", "Original description")
        session.commit()

        payload = {"description": "Updated description"}

        response = authenticated_client.patch(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Test"
        assert data["description"] == "Updated description"

    def test_patch_partial_update_metadata(
        self, authenticated_client, api_url, session
    ):
        """Test PATCH partial update of extra_metadata only."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        payload = {"extra_metadata": {"new": "data"}}

        response = authenticated_client.patch(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["extra_metadata"] == {"new": "data"}

    def test_patch_update_not_found(self, authenticated_client, api_url):
        """Test PATCH update with non-existent dummy."""
        fake_id = "00000000-0000-0000-0000-000000000001"
        payload = {"name": "Updated"}

        response = authenticated_client.patch(
            api_url(f"dummies/{fake_id}"), json=payload, content_type="application/json"
        )

        assert response.status_code == 404

    def test_patch_update_no_data(self, authenticated_client, api_url, session):
        """Test PATCH update with no JSON data."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        response = authenticated_client.patch(api_url(f"dummies/{dummy.id}"))

        assert response.status_code == 415  # Unsupported Media Type

    def test_patch_update_invalid_data(self, authenticated_client, api_url, session):
        """Test PATCH update with invalid data."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        payload = {"name": ""}

        response = authenticated_client.patch(
            api_url(f"dummies/{dummy.id}"),
            json=payload,
            content_type="application/json",
        )

        assert response.status_code == 422

    def test_delete_success(self, authenticated_client, api_url, session):
        """Test DELETE with existing dummy."""
        dummy = Dummy.create("To Delete", "Description")
        session.commit()
        dummy_id = dummy.id

        response = authenticated_client.delete(api_url(f"dummies/{dummy_id}"))

        assert response.status_code == 204
        # 204 No Content has no body

        # Verify it's actually deleted
        assert Dummy.get_by_id(dummy_id) is None

    def test_delete_not_found(self, authenticated_client, api_url):
        """Test DELETE with non-existent dummy."""
        fake_id = "00000000-0000-0000-0000-000000000001"

        response = authenticated_client.delete(api_url(f"dummies/{fake_id}"))

        assert response.status_code == 404
        data = response.get_json()
        assert "message" in data

    @patch("app.resources.dummy_res.db.session.delete")
    def test_delete_database_error(
        self, mock_delete, authenticated_client, api_url, session
    ):
        """Test DELETE with database error."""
        dummy = Dummy.create("Test", "Description")
        session.commit()

        mock_delete.side_effect = SQLAlchemyError("Database error")

        response = authenticated_client.delete(api_url(f"dummies/{dummy.id}"))

        assert response.status_code == 500
        data = response.get_json()
        assert "message" in data


class TestDummyListPaginationErrors:
    """Test cases for pagination validation errors."""

    def test_get_list_negative_limit(self, authenticated_client, api_url):
        """Test GET list with negative limit parameter."""
        response = authenticated_client.get(api_url("dummies?limit=-1"))

        assert response.status_code == 400
        data = response.get_json()
        assert "Limit must be greater than 0" in data["message"]

    def test_get_list_negative_offset(self, authenticated_client, api_url):
        """Test GET list with negative offset parameter."""
        response = authenticated_client.get(api_url("dummies?offset=-1"))

        assert response.status_code == 400
        data = response.get_json()
        assert "Offset must be greater than or equal to 0" in data["message"]
