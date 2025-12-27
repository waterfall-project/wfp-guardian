# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Policy REST API endpoints."""

import uuid

import pytest

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy


class TestPolicyListEndpoint:
    """Test cases for GET/POST/HEAD /policies endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_sample_policies(self, app, sample_company_id):
        """Helper to create sample policies."""
        with app.app_context():
            policies = [
                Policy(
                    company_id=sample_company_id,
                    name="file_management",
                    display_name="File Management",
                    description="Full permissions for file operations",
                    priority=10,
                    is_active=True,
                ),
                Policy(
                    company_id=sample_company_id,
                    name="user_management",
                    display_name="User Management",
                    description="Permissions for managing users",
                    priority=20,
                    is_active=True,
                ),
                Policy(
                    company_id=sample_company_id,
                    name="read_only",
                    display_name="Read Only",
                    description="Read-only permissions",
                    priority=5,
                    is_active=False,
                ),
            ]
            for policy in policies:
                db.session.add(policy)
            db.session.commit()

    def test_list_policies_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing all policies."""
        self.create_sample_policies(app, sample_company_id)

        response = authenticated_client.get(api_url("policies"))

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total_items"] == 3
        assert len(data["data"]) == 3

        # Check structure of first policy
        policy = data["data"][0]
        assert "id" in policy
        assert "name" in policy
        assert "display_name" in policy
        assert "description" in policy
        assert "company_id" in policy
        assert "priority" in policy
        assert "is_active" in policy
        assert "permissions_count" in policy
        assert "created_at" in policy
        assert "updated_at" in policy

    def test_list_policies_empty(self, authenticated_client, api_url):
        """Test listing policies when database is empty."""
        response = authenticated_client.get(api_url("policies"))

        assert response.status_code == 200
        data = response.get_json()

        assert data["pagination"]["total_items"] == 0
        assert len(data["data"]) == 0

    def test_list_policies_with_page_size(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing policies with page_size parameter."""
        self.create_sample_policies(app, sample_company_id)

        response = authenticated_client.get(api_url("policies") + "?page_size=2")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 2
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 3
        assert data["pagination"]["total_pages"] == 2

    def test_list_policies_with_pagination(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing policies with page parameter."""
        self.create_sample_policies(app, sample_company_id)

        # Get page 1
        response1 = authenticated_client.get(
            api_url("policies") + "?page_size=2&page=1"
        )
        data1 = response1.get_json()
        first_names = [p["name"] for p in data1["data"]]
        assert data1["pagination"]["page"] == 1

        # Get page 2
        response2 = authenticated_client.get(
            api_url("policies") + "?page_size=2&page=2"
        )
        data2 = response2.get_json()
        second_names = [p["name"] for p in data2["data"]]
        assert data2["pagination"]["page"] == 2

        # Should be different
        assert first_names != second_names
        assert len(second_names) == 1  # Only 1 item on page 2

    def test_list_policies_filter_by_is_active_true(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test filtering policies by is_active=true."""
        self.create_sample_policies(app, sample_company_id)

        response = authenticated_client.get(api_url("policies") + "?is_active=true")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 2  # 2 active policies
        assert data["pagination"]["total_items"] == 2

        # All should be active
        for policy in data["data"]:
            assert policy["is_active"] is True

    def test_list_policies_filter_by_is_active_false(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test filtering policies by is_active=false."""
        self.create_sample_policies(app, sample_company_id)

        response = authenticated_client.get(api_url("policies") + "?is_active=false")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 1  # 1 inactive policy
        assert data["pagination"]["total_items"] == 1
        assert data["data"][0]["is_active"] is False

    def test_list_policies_invalid_page_size(self, authenticated_client, api_url):
        """Test that invalid page_size returns error."""
        response = authenticated_client.get(api_url("policies") + "?page_size=1000")

        assert response.status_code == 400
        data = response.get_json()

        assert "error" in data
        assert data["error"] == "invalid_parameter"

    def test_list_policies_invalid_page(self, authenticated_client, api_url):
        """Test that invalid page returns error."""
        response = authenticated_client.get(api_url("policies") + "?page=0")

        assert response.status_code == 400
        data = response.get_json()

        assert "error" in data
        assert data["error"] == "invalid_parameter"

    def test_create_policy_success(
        self, authenticated_client, api_url, sample_company_id
    ):
        """Test creating a new policy."""
        data = {
            "name": "new_policy",
            "display_name": "New Policy",
            "description": "A brand new policy",
            "priority": 15,
        }

        response = authenticated_client.post(api_url("policies"), json=data)

        assert response.status_code == 201
        result = response.get_json()

        assert result["name"] == "new_policy"
        assert result["display_name"] == "New Policy"
        assert result["description"] == "A brand new policy"
        assert result["priority"] == 15
        assert result["company_id"] == str(sample_company_id)
        assert result["is_active"] is True
        assert "id" in result
        assert "created_at" in result

    def test_create_policy_minimal_fields(
        self, authenticated_client, api_url, sample_company_id
    ):
        """Test creating policy with only required fields."""
        data = {
            "name": "minimal_policy",
            "display_name": "Minimal Policy",
        }

        response = authenticated_client.post(api_url("policies"), json=data)

        assert response.status_code == 201
        result = response.get_json()

        assert result["name"] == "minimal_policy"
        assert result["display_name"] == "Minimal Policy"
        assert result["priority"] == 0  # Default value

    def test_create_policy_duplicate_name(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test creating policy with duplicate name returns conflict."""
        self.create_sample_policies(app, sample_company_id)

        data = {
            "name": "file_management",  # Already exists
            "display_name": "Duplicate Policy",
        }

        response = authenticated_client.post(api_url("policies"), json=data)

        assert response.status_code == 409
        result = response.get_json()

        assert result["error"] == "conflict"
        assert "already exists" in result["message"]

    def test_create_policy_invalid_name_format(self, authenticated_client, api_url):
        """Test creating policy with invalid name format."""
        data = {
            "name": "Invalid-Name",  # Should be lowercase_underscore
            "display_name": "Invalid Policy",
        }

        response = authenticated_client.post(api_url("policies"), json=data)

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"

    def test_create_policy_missing_required_field(self, authenticated_client, api_url):
        """Test creating policy without required fields."""
        data = {
            "name": "incomplete_policy",
            # Missing display_name
        }

        response = authenticated_client.post(api_url("policies"), json=data)

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"

    def test_head_policies_count(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test HEAD request returns total count."""
        self.create_sample_policies(app, sample_company_id)

        response = authenticated_client.head(api_url("policies"))

        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "3"

    def test_head_policies_count_with_filter(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test HEAD request with is_active filter."""
        self.create_sample_policies(app, sample_company_id)

        response = authenticated_client.head(api_url("policies") + "?is_active=true")

        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "2"


class TestPolicyDetailEndpoint:
    """Test cases for GET/PATCH/DELETE /policies/<id> endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_sample_policy(self, app, sample_company_id):
        """Helper to create a sample policy."""
        with app.app_context():
            policy = Policy(
                company_id=sample_company_id,
                name="test_policy",
                display_name="Test Policy",
                description="A test policy",
                priority=10,
            )
            db.session.add(policy)
            db.session.commit()
            return str(policy.id)

    def test_get_policy_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test getting a policy by ID."""
        policy_id = self.create_sample_policy(app, sample_company_id)

        response = authenticated_client.get(api_url(f"policies/{policy_id}"))

        assert response.status_code == 200
        result = response.get_json()

        assert result["id"] == policy_id
        assert result["name"] == "test_policy"
        assert result["display_name"] == "Test Policy"

    def test_get_policy_not_found(self, authenticated_client, api_url):
        """Test getting non-existent policy."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(api_url(f"policies/{fake_id}"))

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"
        assert "not found" in result["message"]

    def test_update_policy_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test updating a policy."""
        policy_id = self.create_sample_policy(app, sample_company_id)

        update_data = {
            "display_name": "Updated Policy",
            "description": "Updated description",
            "priority": 20,
        }

        response = authenticated_client.patch(
            api_url(f"policies/{policy_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["display_name"] == "Updated Policy"
        assert result["description"] == "Updated description"
        assert result["priority"] == 20
        assert result["name"] == "test_policy"  # Unchanged

    def test_update_policy_partial(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test partial update of policy."""
        policy_id = self.create_sample_policy(app, sample_company_id)

        update_data = {"is_active": False}

        response = authenticated_client.patch(
            api_url(f"policies/{policy_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["is_active"] is False
        assert result["name"] == "test_policy"  # Unchanged

    def test_update_policy_not_found(self, authenticated_client, api_url):
        """Test updating non-existent policy."""
        fake_id = uuid.uuid4()
        update_data = {"display_name": "Updated"}

        response = authenticated_client.patch(
            api_url(f"policies/{fake_id}"), json=update_data
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_update_policy_invalid_data(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test updating policy with invalid data."""
        policy_id = self.create_sample_policy(app, sample_company_id)

        update_data = {"name": "Invalid-Name"}  # Invalid format

        response = authenticated_client.patch(
            api_url(f"policies/{policy_id}"), json=update_data
        )

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"

    def test_delete_policy_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test deleting a policy."""
        policy_id = self.create_sample_policy(app, sample_company_id)

        response = authenticated_client.delete(api_url(f"policies/{policy_id}"))

        assert response.status_code == 204

        # Verify it's deleted
        get_response = authenticated_client.get(api_url(f"policies/{policy_id}"))
        assert get_response.status_code == 404

    def test_delete_policy_not_found(self, authenticated_client, api_url):
        """Test deleting non-existent policy."""
        fake_id = uuid.uuid4()
        response = authenticated_client.delete(api_url(f"policies/{fake_id}"))

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"


class TestPolicyPermissionsEndpoint:
    """Test cases for GET/POST /policies/<id>/permissions endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_policy_with_permissions(self, app, sample_company_id):
        """Helper to create policy and permissions."""
        with app.app_context():
            # Create permissions
            perm1 = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            perm2 = Permission(
                name="storage:files:CREATE",
                service="storage",
                resource_name="files",
                operation="CREATE",
            )
            db.session.add(perm1)
            db.session.add(perm2)
            db.session.flush()

            # Create policy
            policy = Policy(
                company_id=sample_company_id,
                name="test_policy",
                display_name="Test Policy",
            )
            policy.permissions.append(perm1)
            db.session.add(policy)
            db.session.commit()

            return str(policy.id), str(perm1.id), str(perm2.id)

    def test_list_policy_permissions_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing permissions for a policy."""
        policy_id, perm1_id, _ = self.create_policy_with_permissions(
            app, sample_company_id
        )

        response = authenticated_client.get(
            api_url(f"policies/{policy_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == perm1_id

    def test_list_policy_permissions_empty(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing permissions for policy with no permissions."""
        with app.app_context():
            policy = Policy(
                company_id=sample_company_id,
                name="empty_policy",
                display_name="Empty Policy",
            )
            db.session.add(policy)
            db.session.commit()
            policy_id = str(policy.id)

        response = authenticated_client.get(
            api_url(f"policies/{policy_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 0

    def test_add_permission_to_policy_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test adding a permission to a policy."""
        policy_id, _, perm2_id = self.create_policy_with_permissions(
            app, sample_company_id
        )

        data = {"permission_id": perm2_id}

        response = authenticated_client.post(
            api_url(f"policies/{policy_id}/permissions"), json=data
        )

        assert response.status_code == 201

        # Verify it was added
        get_response = authenticated_client.get(
            api_url(f"policies/{policy_id}/permissions")
        )
        permissions = get_response.get_json()["data"]
        assert len(permissions) == 2

    def test_add_permission_duplicate(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test adding permission that's already attached."""
        policy_id, perm1_id, _ = self.create_policy_with_permissions(
            app, sample_company_id
        )

        data = {"permission_id": perm1_id}

        response = authenticated_client.post(
            api_url(f"policies/{policy_id}/permissions"), json=data
        )

        assert response.status_code == 409
        result = response.get_json()

        assert result["error"] == "conflict"
        assert "already attached" in result["message"]

    def test_add_permission_not_found(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test adding non-existent permission."""
        policy_id, _, _ = self.create_policy_with_permissions(app, sample_company_id)

        data = {"permission_id": str(uuid.uuid4())}

        response = authenticated_client.post(
            api_url(f"policies/{policy_id}/permissions"), json=data
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"


class TestPolicyPermissionDetailEndpoint:
    """Test cases for DELETE /policies/<id>/permissions/<perm_id> endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_policy_with_permission(self, app, sample_company_id):
        """Helper to create policy with one permission."""
        with app.app_context():
            perm = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(perm)
            db.session.flush()

            policy = Policy(
                company_id=sample_company_id,
                name="test_policy",
                display_name="Test Policy",
            )
            policy.permissions.append(perm)
            db.session.add(policy)
            db.session.commit()

            return str(policy.id), str(perm.id)

    def test_remove_permission_from_policy_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test removing a permission from a policy."""
        policy_id, perm_id = self.create_policy_with_permission(app, sample_company_id)

        response = authenticated_client.delete(
            api_url(f"policies/{policy_id}/permissions/{perm_id}")
        )

        assert response.status_code == 204

        # Verify it was removed
        get_response = authenticated_client.get(
            api_url(f"policies/{policy_id}/permissions")
        )
        permissions = get_response.get_json()["data"]
        assert len(permissions) == 0

    def test_remove_permission_not_attached(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test removing permission that's not attached."""
        policy_id, _ = self.create_policy_with_permission(app, sample_company_id)

        # Create another permission not attached to policy
        with app.app_context():
            other_perm = Permission(
                name="storage:files:DELETE",
                service="storage",
                resource_name="files",
                operation="DELETE",
            )
            db.session.add(other_perm)
            db.session.commit()
            other_perm_id = str(other_perm.id)

        response = authenticated_client.delete(
            api_url(f"policies/{policy_id}/permissions/{other_perm_id}")
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_remove_permission_not_found(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test removing non-existent permission."""
        policy_id, _ = self.create_policy_with_permission(app, sample_company_id)

        fake_perm_id = uuid.uuid4()
        response = authenticated_client.delete(
            api_url(f"policies/{policy_id}/permissions/{fake_perm_id}")
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"
