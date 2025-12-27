# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for UserRole REST API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.db import db
from app.models.role import Role
from app.models.user_role import UserRole


class TestUserRoleListEndpoint:
    """Test cases for GET/POST/HEAD /users/<user_id>/roles endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_sample_user_roles(self, app, sample_company_id, user_id):
        """Helper to create sample user roles."""
        with app.app_context():
            # Create roles
            role1 = Role(
                company_id=sample_company_id,
                name="admin",
                display_name="Administrator",
            )
            role2 = Role(
                company_id=sample_company_id,
                name="user",
                display_name="Regular User",
            )
            role3 = Role(
                company_id=sample_company_id,
                name="guest",
                display_name="Guest",
            )
            db.session.add_all([role1, role2, role3])
            db.session.flush()

            # Create user roles
            user_roles = [
                UserRole(
                    user_id=user_id,
                    role_id=role1.id,
                    company_id=sample_company_id,
                    scope_type="direct",
                    granted_by=str(uuid.uuid4()),
                    granted_at=datetime.now(UTC),
                    is_active=True,
                ),
                UserRole(
                    user_id=user_id,
                    role_id=role2.id,
                    company_id=sample_company_id,
                    scope_type="hierarchical",
                    granted_by=str(uuid.uuid4()),
                    granted_at=datetime.now(UTC),
                    is_active=True,
                ),
                UserRole(
                    user_id=user_id,
                    role_id=role3.id,
                    company_id=sample_company_id,
                    scope_type="direct",
                    granted_by=str(uuid.uuid4()),
                    granted_at=datetime.now(UTC),
                    is_active=False,
                ),
            ]
            for user_role in user_roles:
                db.session.add(user_role)
            db.session.commit()

            return str(role1.id), str(role2.id), str(role3.id)

    def test_list_user_roles_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing all user roles for a user."""
        user_id = uuid.uuid4()
        self.create_sample_user_roles(app, sample_company_id, user_id)

        response = authenticated_client.get(api_url(f"users/{user_id}/roles"))

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total_items"] == 3
        assert len(data["data"]) == 3

        # Check structure of first user role
        user_role = data["data"][0]
        assert "id" in user_role
        assert "user_id" in user_role
        assert "role_id" in user_role
        assert "company_id" in user_role
        assert "scope_type" in user_role
        assert "is_active" in user_role
        assert "granted_by" in user_role
        assert "granted_at" in user_role
        assert "created_at" in user_role

    def test_list_user_roles_empty(self, authenticated_client, api_url):
        """Test listing user roles when none exist."""
        user_id = uuid.uuid4()
        response = authenticated_client.get(api_url(f"users/{user_id}/roles"))

        assert response.status_code == 200
        data = response.get_json()

        assert data["pagination"]["total_items"] == 0
        assert len(data["data"]) == 0

    def test_list_user_roles_with_page_size(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing user roles with page_size parameter."""
        user_id = uuid.uuid4()
        self.create_sample_user_roles(app, sample_company_id, user_id)

        response = authenticated_client.get(
            api_url(f"users/{user_id}/roles") + "?page_size=2"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 2
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 3

    def test_list_user_roles_filter_by_is_active_true(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test filtering user roles by is_active=true."""
        user_id = uuid.uuid4()
        self.create_sample_user_roles(app, sample_company_id, user_id)

        response = authenticated_client.get(
            api_url(f"users/{user_id}/roles") + "?is_active=true"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 2  # 2 active user roles
        assert data["pagination"]["total_items"] == 2

        # All should be active
        for user_role in data["data"]:
            assert user_role["is_active"] is True

    def test_list_user_roles_filter_by_is_active_false(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test filtering user roles by is_active=false."""
        user_id = uuid.uuid4()
        self.create_sample_user_roles(app, sample_company_id, user_id)

        response = authenticated_client.get(
            api_url(f"users/{user_id}/roles") + "?is_active=false"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 1  # 1 inactive user role
        assert data["pagination"]["total_items"] == 1
        assert data["data"][0]["is_active"] is False

    def test_assign_role_to_user_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test assigning a role to a user."""
        user_id = uuid.uuid4()

        # Create a role
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

        data = {
            "role_id": role_id,
            "scope_type": "direct",
        }

        response = authenticated_client.post(
            api_url(f"users/{user_id}/roles"), json=data
        )

        assert response.status_code == 201
        result = response.get_json()

        assert result["user_id"] == str(user_id)
        assert result["role_id"] == role_id
        assert result["company_id"] == str(sample_company_id)
        assert result["scope_type"] == "direct"
        assert result["is_active"] is True
        assert "id" in result
        assert "granted_at" in result

    def test_assign_role_with_project_id(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test assigning a role with project scope."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()

        # Create a role
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

        data = {
            "role_id": role_id,
            "project_id": str(project_id),
            "scope_type": "direct",
        }

        response = authenticated_client.post(
            api_url(f"users/{user_id}/roles"), json=data
        )

        assert response.status_code == 201
        result = response.get_json()

        assert result["project_id"] == str(project_id)

    def test_assign_role_with_expires_at(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test assigning a role with expiration."""
        user_id = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        # Create a role
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

        data = {
            "role_id": role_id,
            "scope_type": "direct",
            "expires_at": expires_at.isoformat(),
        }

        response = authenticated_client.post(
            api_url(f"users/{user_id}/roles"), json=data
        )

        assert response.status_code == 201
        result = response.get_json()

        assert "expires_at" in result

    def test_assign_role_duplicate(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test assigning role that's already assigned returns conflict."""
        user_id = uuid.uuid4()
        role_id, _, _ = self.create_sample_user_roles(app, sample_company_id, user_id)

        data = {
            "role_id": role_id,
            "scope_type": "direct",
        }

        response = authenticated_client.post(
            api_url(f"users/{user_id}/roles"), json=data
        )

        assert response.status_code == 409
        result = response.get_json()

        assert result["error"] == "conflict"
        assert "already assigned" in result["message"]

    def test_assign_role_not_found(self, authenticated_client, api_url):
        """Test assigning non-existent role."""
        user_id = uuid.uuid4()
        fake_role_id = uuid.uuid4()

        data = {
            "role_id": str(fake_role_id),
            "scope_type": "direct",
        }

        response = authenticated_client.post(
            api_url(f"users/{user_id}/roles"), json=data
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_assign_role_invalid_scope_type(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test assigning role with invalid scope_type."""
        user_id = uuid.uuid4()

        # Create a role
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

        data = {
            "role_id": role_id,
            "scope_type": "invalid_scope",
        }

        response = authenticated_client.post(
            api_url(f"users/{user_id}/roles"), json=data
        )

        assert response.status_code == 422
        result = response.get_json()

        assert result["error"] == "validation_error"

    def test_head_user_roles_count(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test HEAD request returns total count."""
        user_id = uuid.uuid4()
        self.create_sample_user_roles(app, sample_company_id, user_id)

        response = authenticated_client.head(api_url(f"users/{user_id}/roles"))

        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "3"

    def test_head_user_roles_count_with_filter(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test HEAD request with is_active filter."""
        user_id = uuid.uuid4()
        self.create_sample_user_roles(app, sample_company_id, user_id)

        response = authenticated_client.head(
            api_url(f"users/{user_id}/roles") + "?is_active=true"
        )

        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "2"


class TestUserRoleDetailEndpoint:
    """Test cases for GET/PATCH/DELETE /users/<user_id>/roles/<id> endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_user_role(self, app, sample_company_id, user_id):
        """Helper to create a user role."""
        with app.app_context():
            # Create role
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            db.session.add(role)
            db.session.flush()

            # Create user role
            user_role = UserRole(
                user_id=user_id,
                role_id=role.id,
                company_id=sample_company_id,
                scope_type="direct",
                granted_by=str(uuid.uuid4()),
                granted_at=datetime.now(UTC),
            )
            db.session.add(user_role)
            db.session.commit()

            return str(user_role.id)

    def test_get_user_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test getting a user role by ID."""
        user_id = uuid.uuid4()
        user_role_id = self.create_user_role(app, sample_company_id, user_id)

        response = authenticated_client.get(
            api_url(f"users/{user_id}/roles/{user_role_id}")
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["id"] == user_role_id
        assert result["user_id"] == str(user_id)

    def test_get_user_role_not_found(self, authenticated_client, api_url):
        """Test getting non-existent user role."""
        user_id = uuid.uuid4()
        fake_id = uuid.uuid4()
        response = authenticated_client.get(api_url(f"users/{user_id}/roles/{fake_id}"))

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_update_user_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test updating a user role."""
        user_id = uuid.uuid4()
        user_role_id = self.create_user_role(app, sample_company_id, user_id)

        update_data = {
            "scope_type": "hierarchical",
            "is_active": False,
        }

        response = authenticated_client.patch(
            api_url(f"users/{user_id}/roles/{user_role_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["scope_type"] == "hierarchical"
        assert result["is_active"] is False

    def test_update_user_role_partial(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test partial update of user role."""
        user_id = uuid.uuid4()
        user_role_id = self.create_user_role(app, sample_company_id, user_id)

        update_data = {"is_active": False}

        response = authenticated_client.patch(
            api_url(f"users/{user_id}/roles/{user_role_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert result["is_active"] is False
        assert result["scope_type"] == "direct"  # Unchanged

    def test_update_user_role_expires_at(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test updating expires_at."""
        user_id = uuid.uuid4()
        user_role_id = self.create_user_role(app, sample_company_id, user_id)

        expires_at = datetime.now(UTC) + timedelta(days=60)
        update_data = {"expires_at": expires_at.isoformat()}

        response = authenticated_client.patch(
            api_url(f"users/{user_id}/roles/{user_role_id}"), json=update_data
        )

        assert response.status_code == 200
        result = response.get_json()

        assert "expires_at" in result

    def test_update_user_role_not_found(self, authenticated_client, api_url):
        """Test updating non-existent user role."""
        user_id = uuid.uuid4()
        fake_id = uuid.uuid4()
        update_data = {"is_active": False}

        response = authenticated_client.patch(
            api_url(f"users/{user_id}/roles/{fake_id}"), json=update_data
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"

    def test_delete_user_role_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test deleting a user role."""
        user_id = uuid.uuid4()
        user_role_id = self.create_user_role(app, sample_company_id, user_id)

        response = authenticated_client.delete(
            api_url(f"users/{user_id}/roles/{user_role_id}")
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = authenticated_client.get(
            api_url(f"users/{user_id}/roles/{user_role_id}")
        )
        assert get_response.status_code == 404

    def test_delete_user_role_not_found(self, authenticated_client, api_url):
        """Test deleting non-existent user role."""
        user_id = uuid.uuid4()
        fake_id = uuid.uuid4()
        response = authenticated_client.delete(
            api_url(f"users/{user_id}/roles/{fake_id}")
        )

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"


class TestRoleUsersEndpoint:
    """Test cases for GET /roles/<role_id>/users endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_role_with_users(self, app, sample_company_id):
        """Helper to create role with user assignments."""
        with app.app_context():
            # Create role
            role = Role(
                company_id=sample_company_id,
                name="test_role",
                display_name="Test Role",
            )
            db.session.add(role)
            db.session.flush()

            # Create user roles
            user1_id = uuid.uuid4()
            user2_id = uuid.uuid4()
            user_roles = [
                UserRole(
                    user_id=str(user1_id),
                    role_id=role.id,
                    company_id=sample_company_id,
                    scope_type="direct",
                    granted_by=str(uuid.uuid4()),
                    granted_at=datetime.now(UTC),
                    is_active=True,
                ),
                UserRole(
                    user_id=str(user2_id),
                    role_id=role.id,
                    company_id=sample_company_id,
                    scope_type="hierarchical",
                    granted_by=str(uuid.uuid4()),
                    granted_at=datetime.now(UTC),
                    is_active=True,
                ),
            ]
            for user_role in user_roles:
                db.session.add(user_role)
            db.session.commit()

            return str(role.id), str(user1_id), str(user2_id)

    def test_list_role_users_success(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing users with a specific role."""
        role_id, user1_id, user2_id = self.create_role_with_users(
            app, sample_company_id
        )

        response = authenticated_client.get(api_url(f"roles/{role_id}/users"))

        assert response.status_code == 200
        data = response.get_json()

        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["total_items"] == 2
        assert len(data["data"]) == 2

        # Check that both users are present
        user_ids = [ur["user_id"] for ur in data["data"]]
        assert user1_id in user_ids
        assert user2_id in user_ids

    def test_list_role_users_empty(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing users for role with no assignments."""
        with app.app_context():
            role = Role(
                company_id=sample_company_id,
                name="empty_role",
                display_name="Empty Role",
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

        response = authenticated_client.get(api_url(f"roles/{role_id}/users"))

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 0
        assert data["pagination"]["total_items"] == 0

    def test_list_role_users_with_pagination(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test listing role users with pagination."""
        role_id, _, _ = self.create_role_with_users(app, sample_company_id)

        response = authenticated_client.get(
            api_url(f"roles/{role_id}/users") + "?page_size=1"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 1
        assert data["pagination"]["page_size"] == 1
        assert data["pagination"]["total_items"] == 2

    def test_list_role_users_filter_by_is_active(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test filtering role users by is_active."""
        role_id, _, _ = self.create_role_with_users(app, sample_company_id)

        response = authenticated_client.get(
            api_url(f"roles/{role_id}/users") + "?is_active=true"
        )

        assert response.status_code == 200
        data = response.get_json()

        assert len(data["data"]) == 2  # Both are active
        for user_role in data["data"]:
            assert user_role["is_active"] is True

    def test_list_role_users_role_not_found(self, authenticated_client, api_url):
        """Test listing users for non-existent role."""
        fake_role_id = uuid.uuid4()
        response = authenticated_client.get(api_url(f"roles/{fake_role_id}/users"))

        assert response.status_code == 404
        result = response.get_json()

        assert result["error"] == "not_found"
