# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Role REST API endpoints."""

import uuid

import pytest

from app.models.db import db
from app.models.policy import Policy
from app.models.role import Role


class TestRoleListEndpoint:
    """Test cases for GET/POST /roles endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_sample_roles(self, app, sample_company_id):
        """Helper to create sample roles."""
        with app.app_context():
            roles = [
                Role(
                    company_id=sample_company_id,
                    name="admin",
                    display_name="Administrator",
                    description="Full administrative access",
                    is_active=True,
                ),
                Role(
                    company_id=sample_company_id,
                    name="user",
                    display_name="Regular User",
                    description="Standard user access",
                    is_active=True,
                ),
                Role(
                    company_id=sample_company_id,
                    name="guest",
                    display_name="Guest",
                    description="Limited guest access",
                    is_active=False,
                ),
            ]
            for role in roles:
                db.session.add(role)
            db.session.commit()

    def test_list_roles_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing all roles."""
        self.create_sample_roles(app, sample_company_id)

        response = authenticated_client.get(api_url("roles"))

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total_items"] == 3
        assert len(data["data"]) == 3

        # Check structure of first role
        role = data["data"][0]
        assert "id" in role
        assert "name" in role
        assert "display_name" in role
        assert "description" in role
        assert "company_id" in role
        assert "is_active" in role
        assert "policies_count" in role
        assert "created_at" in role
        assert "updated_at" in role

    def test_list_roles_empty(self, authenticated_client, api_url):
        """Test listing roles when database is empty."""
        response = authenticated_client.get(api_url("roles"))

        assert response.status_code == 200
        data = response.get_json()

        assert data["pagination"]["total_items"] == 0
        assert len(data["data"]) == 0

    def test_list_roles_with_page_size(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing roles with page_size parameter."""
        self.create_sample_roles(app, sample_company_id)

        response = authenticated_client.get(api_url("roles") + "?page_size=2")

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 2
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 3
        assert data["pagination"]["total_pages"] == 2

    def test_list_roles_with_pagination(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing roles with page parameter."""
        self.create_sample_roles(app, sample_company_id)

        # Get page 1
        response1 = authenticated_client.get(api_url("roles") + "?page_size=2&page=1")
        data1 = response1.get_json()
        first_names = [r["name"] for r in data1["data"]]
        assert data1["pagination"]["page"] == 1

        # Get page 2
        response2 = authenticated_client.get(api_url("roles") + "?page_size=2&page=2")
        data2 = response2.get_json()
        second_names = [r["name"] for r in data2["data"]]
        assert data2["pagination"]["page"] == 2

        # Should be different
        assert first_names != second_names
        assert len(second_names) == 1  # Only 1 item on page 2

    def test_create_role_success(
        self, authenticated_client, api_url, sample_company_id
    ):
        """Test creating a new role."""
        data = {
            "name": "new_role",
            "display_name": "New Role",
            "description": "A brand new role",
        }

        response = authenticated_client.post(api_url("roles"), json=data)

        assert response.status_code == 201
        result = response.get_json()

        assert result["name"] == "new_role"
        assert result["display_name"] == "New Role"
        assert result["description"] == "A brand new role"
        assert result["company_id"] == str(sample_company_id)
        assert result["is_active"] is True
        assert "id" in result
        assert "created_at" in result

    def test_create_role_minimal_fields(
        self, authenticated_client, api_url, sample_company_id
    ):
        """Test creating role with only required fields."""
        data = {
            "name": "minimal_role",
            "display_name": "Minimal Role",
        }

        response = authenticated_client.post(api_url("roles"), json=data)

        assert response.status_code == 201
        result = response.get_json()

        assert result["name"] == "minimal_role"
        assert result["display_name"] == "Minimal Role"

    def test_create_role_duplicate_name(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test creating role with duplicate name returns conflict."""
        self.create_sample_roles(app, sample_company_id)

        data = {
            "name": "admin",  # Already exists
            "display_name": "Duplicate Role",
        }

        response = authenticated_client.post(api_url("roles"), json=data)

        assert response.status_code == 409
        result = response.get_json()

        assert result["error"] == "conflict"
        assert "already exists" in result["message"]

    def test_create_role_invalid_name_format(self, authenticated_client, api_url):
        """Test creating role with invalid name format."""
        data = {
            "name": "Invalid-Name",  # Should be lowercase_underscore
            "display_name": "Invalid Role",
        }

        response = authenticated_client.post(api_url("roles"), json=data)

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"

    def test_create_role_missing_required_field(self, authenticated_client, api_url):
        """Test creating role without required fields."""
        data = {
            "name": "incomplete_role",
            # Missing display_name
        }

        response = authenticated_client.post(api_url("roles"), json=data)

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"


class TestRoleDetailEndpoint:
    """Test cases for GET/PATCH/DELETE /roles/<id> endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_sample_role(self, app, sample_company_id):
        """Helper to create a sample role."""
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
                description="A test role",
            )
            db.session.add(role)
            db.session.commit()
            return str(role.id)

    def test_get_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test getting a role by ID."""
        role_id = self.create_sample_role(app, sample_company_id)

        response = authenticated_client.get(api_url(f"roles/{role_id}"))

        assert response.status_code == 200
        result = response.get_json()

        assert result["id"] == role_id
        assert result["name"] == "test_role"
        assert result["display_name"] == "Test Role"

    def test_get_role_not_found(self, authenticated_client, api_url):
        """Test getting non-existent role."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(api_url(f"roles/{fake_id}"))

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"
        assert "not found" in result["message"]

    def test_update_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test updating a role."""
        role_id = self.create_sample_role(app, sample_company_id)

        update_data = {
            "display_name": "Updated Role",
            "description": "Updated description",
        }

        response = authenticated_client.patch(
            api_url(f"roles/{role_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["display_name"] == "Updated Role"
        assert result["description"] == "Updated description"
        assert result["name"] == "test_role"  # Unchanged

    def test_update_role_partial(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test partial update of role."""
        role_id = self.create_sample_role(app, sample_company_id)

        update_data = {"is_active": False}

        response = authenticated_client.patch(
            api_url(f"roles/{role_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["is_active"] is False
        assert result["name"] == "test_role"  # Unchanged

    def test_update_role_not_found(self, authenticated_client, api_url):
        """Test updating non-existent role."""
        fake_id = uuid.uuid4()
        update_data = {"display_name": "Updated"}

        response = authenticated_client.patch(
            api_url(f"roles/{fake_id}"), json=update_data
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_update_role_invalid_data(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test updating role with invalid data."""
        role_id = self.create_sample_role(app, sample_company_id)

        update_data = {"name": "Invalid-Name"}  # Invalid format

        response = authenticated_client.patch(
            api_url(f"roles/{role_id}"), json=update_data
        )

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"

    def test_delete_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test deleting a role."""
        role_id = self.create_sample_role(app, sample_company_id)

        response = authenticated_client.delete(api_url(f"roles/{role_id}"))

        assert response.status_code == 204

        # Verify it's deleted
        get_response = authenticated_client.get(api_url(f"roles/{role_id}"))
        assert get_response.status_code == 404

    def test_delete_role_not_found(self, authenticated_client, api_url):
        """Test deleting non-existent role."""
        fake_id = uuid.uuid4()
        response = authenticated_client.delete(api_url(f"roles/{fake_id}"))

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"


class TestRolePoliciesEndpoint:
    """Test cases for GET/POST /roles/<id>/policies endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_role_with_policies(self, app, sample_company_id):
        """Helper to create role and policies."""
        with app.app_context():
            # Create policies
            policy1 = Policy(
                company_id=sample_company_id,
                name="policy_one",
                display_name="Policy One",
            )
            policy2 = Policy(
                company_id=sample_company_id,
                name="policy_two",
                display_name="Policy Two",
            )
            db.session.add(policy1)
            db.session.add(policy2)
            db.session.flush()

            # Create role
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            role.policies.append(policy1)
            db.session.add(role)
            db.session.commit()

            return str(role.id), str(policy1.id), str(policy2.id)

    def test_list_role_policies_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing policies for a role."""
        role_id, policy1_id, _ = self.create_role_with_policies(app, sample_company_id)

        response = authenticated_client.get(api_url(f"roles/{role_id}/policies"))

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == policy1_id

    def test_list_role_policies_empty(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing policies for role with no policies."""
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="empty_role",
                display_name="Empty Role",
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

        response = authenticated_client.get(api_url(f"roles/{role_id}/policies"))

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 0

    def test_attach_policy_to_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test attaching a policy to a role."""
        role_id, _, policy2_id = self.create_role_with_policies(app, sample_company_id)

        data = {"policy_id": policy2_id}

        response = authenticated_client.post(
            api_url(f"roles/{role_id}/policies"), json=data
        )

        assert response.status_code == 201

        # Verify it was attached
        get_response = authenticated_client.get(api_url(f"roles/{role_id}/policies"))
        policies = get_response.get_json()["data"]
        assert len(policies) == 2

    def test_attach_policy_duplicate(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test attaching policy that's already attached."""
        role_id, policy1_id, _ = self.create_role_with_policies(app, sample_company_id)

        data = {"policy_id": policy1_id}

        response = authenticated_client.post(
            api_url(f"roles/{role_id}/policies"), json=data
        )

        assert response.status_code == 409
        result = response.get_json()

        assert result["error"] == "conflict"
        assert "already attached" in result["message"]

    def test_attach_policy_not_found(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test attaching non-existent policy."""
        role_id, _, _ = self.create_role_with_policies(app, sample_company_id)

        data = {"policy_id": str(uuid.uuid4())}

        response = authenticated_client.post(
            api_url(f"roles/{role_id}/policies"), json=data
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"


class TestRolePolicyDetailEndpoint:
    """Test cases for DELETE /roles/<id>/policies/<policy_id> endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_role_with_policy(self, app, sample_company_id):
        """Helper to create role with one policy."""
        with app.app_context():
            policy = Policy(
                company_id=sample_company_id,
                name="test_policy",
                display_name="Test Policy",
            )
            db.session.add(policy)
            db.session.flush()

            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            role.policies.append(policy)
            db.session.add(role)
            db.session.commit()

            return str(role.id), str(policy.id)

    def test_detach_policy_from_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test detaching a policy from a role."""
        role_id, policy_id = self.create_role_with_policy(app, sample_company_id)

        response = authenticated_client.delete(
            api_url(f"roles/{role_id}/policies/{policy_id}")
        )

        assert response.status_code == 204

        # Verify it was detached
        get_response = authenticated_client.get(api_url(f"roles/{role_id}/policies"))
        policies = get_response.get_json()["data"]
        assert len(policies) == 0

    def test_detach_policy_not_attached(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test detaching policy that's not attached."""
        role_id, _ = self.create_role_with_policy(app, sample_company_id)

        # Create another policy not attached to role
        with app.app_context():
            other_policy = Policy(
                company_id=sample_company_id,
                name="other_policy",
                display_name="Other Policy",
            )
            db.session.add(other_policy)
            db.session.commit()
            other_policy_id = str(other_policy.id)

        response = authenticated_client.delete(
            api_url(f"roles/{role_id}/policies/{other_policy_id}")
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_detach_policy_not_found(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test detaching non-existent policy."""
        role_id, _ = self.create_role_with_policy(app, sample_company_id)

        fake_policy_id = uuid.uuid4()
        response = authenticated_client.delete(
            api_url(f"roles/{role_id}/policies/{fake_policy_id}")
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"
