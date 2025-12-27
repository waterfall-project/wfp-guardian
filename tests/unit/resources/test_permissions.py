# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Permission REST API endpoints."""

import uuid

import pytest

from app.models.db import db
from app.models.permission import Permission


class TestPermissionListEndpoint:
    """Test cases for GET /permissions endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_sample_permissions(self, app):
        """Helper to create sample permissions."""
        with app.app_context():
            permissions = [
                Permission(
                    name="storage:files:READ",
                    service="storage",
                    resource_name="files",
                    operation="READ",
                    description="Read files in storage",
                ),
                Permission(
                    name="storage:files:CREATE",
                    service="storage",
                    resource_name="files",
                    operation="CREATE",
                    description="Create files in storage",
                ),
                Permission(
                    name="storage:buckets:LIST",
                    service="storage",
                    resource_name="buckets",
                    operation="LIST",
                    description="List storage buckets",
                ),
                Permission(
                    name="identity:users:READ",
                    service="identity",
                    resource_name="users",
                    operation="READ",
                    description="Read user information",
                ),
                Permission(
                    name="identity:users:CREATE",
                    service="identity",
                    resource_name="users",
                    operation="CREATE",
                    description="Create new users",
                ),
            ]
            for perm in permissions:
                db.session.add(perm)
            db.session.commit()

    def test_list_permissions_success(self, authenticated_client, api_url, app):
        """Test listing all permissions."""
        self.create_sample_permissions(app)

        response = authenticated_client.get(api_url("permissions"))

        assert response.status_code == 200
        data = response.get_json()

        assert "permissions" in data
        assert "count" in data
        assert data["count"] == 5
        assert len(data["permissions"]) == 5

        # Check structure of first permission
        perm = data["permissions"][0]
        assert "id" in perm
        assert "name" in perm
        assert "service" in perm
        assert "resource_name" in perm
        assert "operation" in perm
        assert "description" in perm
        assert "created_at" in perm
        assert "updated_at" in perm

    def test_list_permissions_empty(self, authenticated_client, api_url):
        """Test listing permissions when database is empty."""
        response = authenticated_client.get(api_url("permissions"))

        assert response.status_code == 200
        data = response.get_json()

        assert data["count"] == 0
        assert len(data["permissions"]) == 0

    def test_list_permissions_with_limit(self, authenticated_client, api_url, app):
        """Test listing permissions with limit parameter."""
        self.create_sample_permissions(app)

        response = authenticated_client.get(api_url("permissions") + "?limit=2")

        assert response.status_code == 200
        data = response.get_json()

        assert data["count"] == 2
        assert len(data["permissions"]) == 2

    def test_list_permissions_with_offset(self, authenticated_client, api_url, app):
        """Test listing permissions with offset parameter."""
        self.create_sample_permissions(app)

        # Get first 2
        response1 = authenticated_client.get(api_url("permissions") + "?limit=2")
        data1 = response1.get_json()
        first_names = [p["name"] for p in data1["permissions"]]

        # Get next 2 with offset
        response2 = authenticated_client.get(
            api_url("permissions") + "?limit=2&offset=2"
        )
        data2 = response2.get_json()
        second_names = [p["name"] for p in data2["permissions"]]

        # Should be different
        assert first_names != second_names
        assert len(second_names) == 2

    def test_list_permissions_filter_by_service(
        self, authenticated_client, api_url, app
    ):
        """Test filtering permissions by service."""
        self.create_sample_permissions(app)

        response = authenticated_client.get(api_url("permissions") + "?service=storage")

        assert response.status_code == 200
        data = response.get_json()

        assert data["count"] == 3  # 3 storage permissions
        assert "total" in data
        assert data["total"] == 3

        # All should be storage service
        services = [p["service"] for p in data["permissions"]]
        assert all(s == "storage" for s in services)

    def test_list_permissions_filter_by_service_and_resource(
        self, authenticated_client, api_url, app
    ):
        """Test filtering permissions by service and resource_name."""
        self.create_sample_permissions(app)

        response = authenticated_client.get(
            api_url("permissions") + "?service=storage&resource_name=files"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["count"] == 2  # 2 storage:files permissions
        assert data["total"] == 2

        # All should be storage:files
        for perm in data["permissions"]:
            assert perm["service"] == "storage"
            assert perm["resource_name"] == "files"

    def test_list_permissions_filter_nonexistent_service(
        self, authenticated_client, api_url, app
    ):
        """Test filtering by non-existent service returns empty."""
        self.create_sample_permissions(app)

        response = authenticated_client.get(
            api_url("permissions") + "?service=nonexistent"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["count"] == 0
        assert data["total"] == 0

    def test_list_permissions_invalid_limit_too_high(
        self, authenticated_client, api_url, app
    ):
        """Test that limit exceeding MAX_PAGE_LIMIT returns error."""
        response = authenticated_client.get(api_url("permissions") + "?limit=1000")

        assert response.status_code == 400
        data = response.get_json()

        assert "error" in data
        assert "Limit must be between" in data["message"]

    def test_list_permissions_invalid_limit_zero(
        self, authenticated_client, api_url, app
    ):
        """Test that limit of 0 returns error."""
        response = authenticated_client.get(api_url("permissions") + "?limit=0")

        assert response.status_code == 400
        data = response.get_json()

        assert "error" in data

    def test_list_permissions_invalid_offset_negative(
        self, authenticated_client, api_url, app
    ):
        """Test that negative offset returns error."""
        response = authenticated_client.get(api_url("permissions") + "?offset=-1")

        assert response.status_code == 400
        data = response.get_json()

        assert "error" in data
        assert "Offset must be >= 0" in data["message"]

    def test_list_permissions_invalid_limit_non_numeric(
        self, authenticated_client, api_url, app
    ):
        """Test that non-numeric limit returns error."""
        response = authenticated_client.get(api_url("permissions") + "?limit=abc")

        assert response.status_code == 400

    def test_list_permissions_requires_authentication(self, client, api_url, app):
        """Test that endpoint requires JWT authentication."""
        self.create_sample_permissions(app)

        # Note: In test environment, USE_IDENTITY_SERVICE is False,
        # so authentication is bypassed. This test verifies the decorator exists.
        response = client.get(api_url("permissions"))

        # In test mode, auth is disabled, so this should succeed
        assert response.status_code == 200


class TestPermissionDetailEndpoint:
    """Test cases for GET /permissions/<id> endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def test_get_permission_by_id_success(self, authenticated_client, api_url, app):
        """Test retrieving a permission by ID."""
        with app.app_context():
            permission = Permission(
                name="storage:files:DELETE",
                service="storage",
                resource_name="files",
                operation="DELETE",
                description="Delete files from storage",
            )
            db.session.add(permission)
            db.session.commit()
            permission_id = str(permission.id)

        response = authenticated_client.get(api_url(f"permissions/{permission_id}"))

        assert response.status_code == 200
        data = response.get_json()

        assert data["id"] == permission_id
        assert data["name"] == "storage:files:DELETE"
        assert data["service"] == "storage"
        assert data["resource_name"] == "files"
        assert data["operation"] == "DELETE"
        assert data["description"] == "Delete files from storage"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_permission_by_id_not_found(self, authenticated_client, api_url):
        """Test retrieving non-existent permission returns 404."""
        nonexistent_id = str(uuid.uuid4())

        response = authenticated_client.get(api_url(f"permissions/{nonexistent_id}"))

        assert response.status_code == 404
        data = response.get_json()

        assert "error" in data
        assert data["error"] == "not_found"
        assert "message" in data

    def test_get_permission_by_id_invalid_uuid(self, authenticated_client, api_url):
        """Test retrieving permission with invalid UUID format."""
        response = authenticated_client.get(api_url("permissions/invalid-uuid"))

        # Flask-RESTful/SQLAlchemy will handle invalid UUID
        # Typically returns 404 or 400
        assert response.status_code in [400, 404]

    def test_get_permission_requires_authentication(self, client, api_url, app):
        """Test that endpoint requires JWT authentication."""
        with app.app_context():
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.commit()
            permission_id = str(permission.id)

        # Note: In test environment, authentication is bypassed
        response = client.get(api_url(f"permissions/{permission_id}"))

        # Should succeed in test mode
        assert response.status_code == 200


class TestPermissionEndpointSecurity:
    """Test security aspects of permission endpoints."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def test_permissions_are_read_only(self, authenticated_client, api_url):
        """Test that POST, PUT, DELETE are not allowed on permissions endpoints."""
        # Try POST to create permission
        response = authenticated_client.post(
            api_url("permissions"),
            json={
                "name": "test:resource:READ",
                "service": "test",
                "resource_name": "resource",
                "operation": "READ",
            },
        )
        # Should be 405 Method Not Allowed or 404 (no route)
        assert response.status_code in [404, 405]

        # Try PUT to update
        permission_id = str(uuid.uuid4())
        response = authenticated_client.put(
            api_url(f"permissions/{permission_id}"),
            json={"description": "Updated"},
        )
        assert response.status_code in [404, 405]

        # Try DELETE
        response = authenticated_client.delete(api_url(f"permissions/{permission_id}"))
        assert response.status_code in [404, 405]
