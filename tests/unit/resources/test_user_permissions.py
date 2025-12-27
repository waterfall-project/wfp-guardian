# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for User Permissions REST API endpoint."""

import uuid

import pytest

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy
from app.models.role import Role
from app.models.user_role import UserRole


class TestUserPermissionsEndpoint:
    """Test cases for GET /users/{user_id}/permissions endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_full_rbac_setup(
        self, app, company_id, user_id, permission_names, role_name="test_role"
    ):
        """Helper to create complete RBAC setup."""
        with app.app_context():
            # Create permissions (check if exists first to avoid duplicates)
            permission_ids = []
            for perm_name in permission_names:
                parts = perm_name.split(":")
                # Check if permission already exists
                permission = Permission.query.filter_by(name=perm_name).first()
                if not permission:
                    permission = Permission(
                        name=perm_name,
                        service=parts[0],
                        resource_name=parts[1],
                        operation=parts[2],
                        description=f"{parts[2]} {parts[1]} in {parts[0]}",
                    )
                    db.session.add(permission)
                    db.session.flush()
                permission_ids.append(permission.id)

            # Create policy
            policy = Policy(
                name=f"{role_name}_policy",
                display_name=f"{role_name.replace('_', ' ').title()} Policy",
                company_id=company_id,
                description=f"Test policy for {role_name}",
            )
            db.session.add(policy)
            db.session.flush()

            for perm_id in permission_ids:
                permission = db.session.get(Permission, perm_id)
                if permission:
                    policy.permissions.append(permission)

            # Create role
            role = Role(
                name=role_name,
                display_name=role_name.replace("_", " ").title(),
                company_id=company_id,
                description=f"Test role {role_name}",
                is_active=True,
            )
            db.session.add(role)
            db.session.flush()
            role.policies.append(policy)

            # Assign role to user
            user_role = UserRole(
                user_id=user_id,
                role_id=role.id,
                company_id=company_id,
                granted_by=user_id,
                is_active=True,
            )
            db.session.add(user_role)
            db.session.commit()

            return {
                "role_id": role.id,
                "policy_id": policy.id,
                "permission_ids": permission_ids,
            }

    def test_get_user_permissions_success(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test retrieving all permissions for a user."""
        # Setup RBAC with multiple permissions
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            [
                "storage:files:READ",
                "storage:files:CREATE",
                "identity:users:READ",
            ],
        )

        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == str(sample_user_id)
        assert data["company_id"] == str(sample_company_id)
        assert "roles" in data
        assert "policies" in data
        assert "permissions" in data
        assert data["total_permissions"] == 3
        assert len(data["permissions"]) == 3

        # Verify permission details
        permission_names = [p["permission_name"] for p in data["permissions"]]
        assert "storage:files:READ" in permission_names
        assert "storage:files:CREATE" in permission_names
        assert "identity:users:READ" in permission_names

    def test_get_user_permissions_no_roles(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test getting permissions for user with no roles."""
        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == str(sample_user_id)
        assert data["roles"] == []
        assert data["policies"] == []
        assert data["permissions"] == []
        assert data["total_permissions"] == 0

    def test_get_user_permissions_forbidden(
        self, authenticated_client, api_url, app, sample_company_id
    ):
        """Test that users cannot view other users' permissions."""
        other_user_id = uuid.uuid4()

        response = authenticated_client.get(
            api_url(f"users/{other_user_id}/permissions")
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "forbidden"

    def test_get_user_permissions_with_project_filter(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test filtering permissions by project."""
        project_id = uuid.uuid4()

        # Create permissions
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ"],
        )

        # Assign project-specific role
        with app.app_context():
            permission = Permission(
                name="project:tasks:CREATE",
                service="project",
                resource_name="tasks",
                operation="CREATE",
                description="Create tasks",
            )
            db.session.add(permission)
            db.session.flush()

            policy = Policy(
                name="project_policy",
                display_name="Project Policy",
                company_id=sample_company_id,
                description="Project-specific policy",
            )
            db.session.add(policy)
            db.session.flush()
            policy.permissions.append(permission)

            role = Role(
                name="project_manager",
                display_name="Project Manager",
                company_id=sample_company_id,
                description="Project manager role",
                is_active=True,
            )
            db.session.add(role)
            db.session.flush()
            role.policies.append(policy)

            user_role = UserRole(
                user_id=sample_user_id,
                role_id=role.id,
                company_id=sample_company_id,
                project_id=str(project_id),
                granted_by=sample_user_id,
                is_active=True,
            )
            db.session.add(user_role)
            db.session.commit()

        # Query with project filter
        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions"),
            query_string={"project_id": str(project_id)},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["project_id"] == str(project_id)
        # Should include both company-wide and project-specific permissions
        assert data["total_permissions"] >= 1

    def test_get_user_permissions_multiple_roles(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test user with multiple roles and deduplicated permissions."""
        # Create first role with permissions
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ", "storage:files:CREATE"],
            role_name="storage_admin",
        )

        # Create second role with overlapping permission
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ", "identity:users:READ"],  # READ overlaps
            role_name="viewer",
        )

        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["roles"]) == 2
        # Permissions should be deduplicated
        assert data["total_permissions"] == 3  # READ counted once
        permission_names = [p["permission_name"] for p in data["permissions"]]
        assert permission_names.count("storage:files:READ") == 1

    def test_get_user_permissions_includes_role_details(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test that response includes detailed role information."""
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ"],
        )

        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["roles"]) == 1
        role = data["roles"][0]
        assert "role_id" in role
        assert "role_name" in role
        assert "role_display_name" in role
        assert "scope_type" in role
        assert "project_id" in role
        assert "expires_at" in role

    def test_get_user_permissions_includes_policy_details(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test that response includes policy information."""
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ"],
        )

        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["policies"]) == 1
        policy = data["policies"][0]
        assert "policy_id" in policy
        assert "policy_name" in policy
        assert "policy_display_name" in policy
        assert "priority" in policy

    def test_get_user_permissions_includes_permission_details(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test that response includes detailed permission information."""
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ"],
        )

        response = authenticated_client.get(
            api_url(f"users/{sample_user_id}/permissions")
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["permissions"]) == 1
        permission = data["permissions"][0]
        assert "permission_id" in permission
        assert "permission_name" in permission
        assert permission["service"] == "storage"
        assert permission["resource_name"] == "files"
        assert permission["operation"] == "READ"
        assert "description" in permission
