# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Access Control REST API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy
from app.models.role import Role
from app.models.user_role import UserRole


class TestCheckAccessEndpoint:
    """Test cases for POST /check-access endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_permission(self, app, name, service, resource_name, operation):
        """Helper to create a permission."""
        with app.app_context():
            permission = Permission(
                name=name,
                service=service,
                resource_name=resource_name,
                operation=operation,
                description=f"{operation} {resource_name} in {service}",
            )
            db.session.add(permission)
            db.session.commit()
            return permission.id

    def create_policy_with_permissions(
        self, app, company_id, policy_name, permission_ids
    ):
        """Helper to create a policy with permissions."""
        with app.app_context():
            policy = Policy(
                name=policy_name,
                display_name=policy_name.replace("_", " ").title(),
                company_id=company_id,
                description=f"Test policy {policy_name}",
            )
            db.session.add(policy)
            db.session.flush()

            # Add permissions to policy
            for perm_id in permission_ids:
                permission = db.session.get(Permission, perm_id)
                if permission:
                    policy.permissions.append(permission)

            db.session.commit()
            return policy.id

    def create_role_with_policies(self, app, company_id, role_name, policy_ids):
        """Helper to create a role with policies."""
        with app.app_context():
            role = Role(
                name=role_name,
                display_name=role_name,
                company_id=company_id,
                description=f"Test role {role_name}",
                is_active=True,
            )
            db.session.add(role)
            db.session.flush()

            # Add policies to role
            for policy_id in policy_ids:
                policy = db.session.get(Policy, policy_id)
                if policy:
                    role.policies.append(policy)

            db.session.commit()
            return role.id

    def assign_role_to_user(
        self,
        app,
        user_id,
        role_id,
        company_id,
        project_id=None,
        expires_at=None,
        is_active=True,
    ):
        """Helper to assign a role to a user."""
        with app.app_context():
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                company_id=company_id,
                project_id=project_id,
                granted_by=user_id,
                expires_at=expires_at,
                is_active=is_active,
            )
            db.session.add(user_role)
            db.session.commit()
            return user_role.id

    def test_check_access_granted(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access granted when user has the required permission."""
        # Create permission
        perm_id = self.create_permission(
            app, "storage:files:READ", "storage", "files", "READ"
        )

        # Create policy with permission
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "storage_reader", [perm_id]
        )

        # Create role with policy
        role_id = self.create_role_with_policies(
            app, sample_company_id, "Reader", [policy_id]
        )

        # Assign role to user
        self.assign_role_to_user(app, sample_user_id, role_id, sample_company_id)

        # Check access
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "files",
                "operation": "READ",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is True
        assert "matched_role" in data
        assert data["matched_role"]["role_name"] == "Reader"
        assert data["reason"] == "granted"

    def test_check_access_denied_no_permission(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access denied when permission doesn't exist."""
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "nonexistent",
                "resource_name": "resource",
                "operation": "READ",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is False
        assert data["reason"] == "no_permission"
        assert "does not exist" in data["message"]

    def test_check_access_denied_no_role(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access denied when user has no roles."""
        # Create permission but don't assign any role
        self.create_permission(
            app, "storage:files:DELETE", "storage", "files", "DELETE"
        )

        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "files",
                "operation": "DELETE",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is False
        assert data["reason"] == "no_matching_role"

    def test_check_access_denied_role_missing_permission(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access denied when user's role doesn't have the required permission."""
        # Create two permissions
        read_perm_id = self.create_permission(
            app, "storage:files:READ", "storage", "files", "READ"
        )
        self.create_permission(
            app, "storage:files:DELETE", "storage", "files", "DELETE"
        )

        # Create policy with only READ permission
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "storage_reader", [read_perm_id]
        )

        # Create role with policy
        role_id = self.create_role_with_policies(
            app, sample_company_id, "Reader", [policy_id]
        )

        # Assign role to user
        self.assign_role_to_user(app, sample_user_id, role_id, sample_company_id)

        # Try to check DELETE permission
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "files",
                "operation": "DELETE",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is False
        assert data["reason"] == "no_permission"

    def test_check_access_with_project_scope(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access check with project scope filtering."""
        project_id = uuid.uuid4()

        # Create permission
        perm_id = self.create_permission(
            app, "storage:files:CREATE", "storage", "files", "CREATE"
        )

        # Create policy and role
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "storage_writer", [perm_id]
        )
        role_id = self.create_role_with_policies(
            app, sample_company_id, "Writer", [policy_id]
        )

        # Assign role to user with project scope
        self.assign_role_to_user(
            app, sample_user_id, role_id, sample_company_id, project_id=project_id
        )

        # Check access with matching project_id
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "files",
                "operation": "CREATE",
                "context": {"project_id": str(project_id)},
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is True

    def test_check_access_denied_wrong_project(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access denied when checking different project."""
        project_id = uuid.uuid4()
        other_project_id = uuid.uuid4()

        # Create permission
        perm_id = self.create_permission(
            app, "storage:files:UPDATE", "storage", "files", "UPDATE"
        )

        # Create policy and role
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "storage_editor", [perm_id]
        )
        role_id = self.create_role_with_policies(
            app, sample_company_id, "Editor", [policy_id]
        )

        # Assign role to user for specific project
        self.assign_role_to_user(
            app, sample_user_id, role_id, sample_company_id, project_id=project_id
        )

        # Check access with different project_id
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "files",
                "operation": "UPDATE",
                "context": {"project_id": str(other_project_id)},
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is False
        assert data["reason"] == "no_matching_role"

    def test_check_access_company_wide_role_works_for_project(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test company-wide role (project_id=None) grants access to any project."""
        project_id = uuid.uuid4()

        # Create permission
        perm_id = self.create_permission(
            app, "storage:buckets:LIST", "storage", "buckets", "LIST"
        )

        # Create policy and role
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "storage_admin", [perm_id]
        )
        role_id = self.create_role_with_policies(
            app, sample_company_id, "Admin", [policy_id]
        )

        # Assign company-wide role (no project_id)
        self.assign_role_to_user(app, sample_user_id, role_id, sample_company_id)

        # Check access with project context
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "buckets",
                "operation": "LIST",
                "context": {"project_id": str(project_id)},
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is True

    def test_check_access_denied_expired_role(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access denied when user's role has expired."""
        # Create permission
        perm_id = self.create_permission(
            app, "identity:users:READ", "identity", "users", "READ"
        )

        # Create policy and role
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "identity_reader", [perm_id]
        )
        role_id = self.create_role_with_policies(
            app, sample_company_id, "User Reader", [policy_id]
        )

        # Assign expired role
        expired_time = datetime.now(UTC) - timedelta(days=1)
        self.assign_role_to_user(
            app, sample_user_id, role_id, sample_company_id, expires_at=expired_time
        )

        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "identity",
                "resource_name": "users",
                "operation": "READ",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is False
        assert data["reason"] == "no_matching_role"

    def test_check_access_denied_inactive_role(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test access denied when user's role is inactive."""
        # Create permission
        perm_id = self.create_permission(
            app, "identity:users:CREATE", "identity", "users", "CREATE"
        )

        # Create policy and role
        policy_id = self.create_policy_with_permissions(
            app, sample_company_id, "identity_admin", [perm_id]
        )
        role_id = self.create_role_with_policies(
            app, sample_company_id, "User Admin", [policy_id]
        )

        # Assign inactive role
        self.assign_role_to_user(
            app, sample_user_id, role_id, sample_company_id, is_active=False
        )

        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "identity",
                "resource_name": "users",
                "operation": "CREATE",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["access_granted"] is False
        assert data["reason"] == "no_matching_role"

    def test_check_access_validation_missing_field(self, authenticated_client, api_url):
        """Test validation error when required field is missing."""
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                # Missing resource_name and operation
            },
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data["error"] == "validation_error"

    def test_check_access_validation_invalid_operation(
        self, authenticated_client, api_url
    ):
        """Test validation error for invalid operation."""
        response = authenticated_client.post(
            api_url("check-access"),
            json={
                "service": "storage",
                "resource_name": "files",
                "operation": "INVALID_OP",
            },
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data["error"] == "validation_error"
        assert "operation" in str(data["message"])


class TestBatchCheckAccessEndpoint:
    """Test cases for POST /batch-check-access endpoint."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_permission(self, app, name, service, resource_name, operation):
        """Helper to create a permission."""
        with app.app_context():
            permission = Permission(
                name=name,
                service=service,
                resource_name=resource_name,
                operation=operation,
                description=f"{operation} {resource_name} in {service}",
            )
            db.session.add(permission)
            db.session.commit()
            return permission.id

    def create_full_rbac_setup(self, app, company_id, user_id, permission_names):
        """Helper to create complete RBAC setup."""
        with app.app_context():
            # Create permissions
            permission_ids = []
            for perm_name in permission_names:
                parts = perm_name.split(":")
                perm_id = self.create_permission(
                    app, perm_name, parts[0], parts[1], parts[2]
                )
                permission_ids.append(perm_id)

            # Create policy
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=company_id,
                description="Test policy",
            )
            db.session.add(policy)
            db.session.flush()

            for perm_id in permission_ids:
                permission = db.session.get(Permission, perm_id)
                if permission:
                    policy.permissions.append(permission)

            # Create role
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=company_id,
                description="Test role",
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

    def test_batch_check_access_success(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test batch check with multiple permissions."""
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

        response = authenticated_client.post(
            api_url("batch-check-access"),
            json={
                "checks": [
                    {
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "READ",
                    },
                    {
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "CREATE",
                    },
                    {
                        "service": "identity",
                        "resource_name": "users",
                        "operation": "READ",
                    },
                    {
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "DELETE",  # Not granted
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert len(data["results"]) == 4
        assert data["results"][0]["access_granted"] is True
        assert data["results"][1]["access_granted"] is True
        assert data["results"][2]["access_granted"] is True
        assert data["results"][3]["access_granted"] is False

    def test_batch_check_access_empty_list(self, authenticated_client, api_url):
        """Test batch check with empty checks list."""
        response = authenticated_client.post(
            api_url("batch-check-access"),
            json={"checks": []},
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data["error"] == "validation_error"

    def test_batch_check_access_too_many_items(self, authenticated_client, api_url):
        """Test batch check exceeding maximum limit."""
        checks = [
            {
                "service": "storage",
                "resource_name": "files",
                "operation": "READ",
            }
            for _ in range(51)  # Exceeds limit of 50
        ]

        response = authenticated_client.post(
            api_url("batch-check-access"),
            json={"checks": checks},
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data["error"] == "validation_error"
        assert "50" in str(data["message"])

    def test_batch_check_access_mixed_results(
        self, authenticated_client, api_url, app, sample_user_id, sample_company_id
    ):
        """Test batch check returns correct mix of granted/denied."""
        # Only grant READ permission
        self.create_full_rbac_setup(
            app,
            sample_company_id,
            sample_user_id,
            ["storage:files:READ"],
        )

        response = authenticated_client.post(
            api_url("batch-check-access"),
            json={
                "checks": [
                    {
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "READ",
                    },
                    {
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "DELETE",
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 2
        assert data["results"][0]["access_granted"] is True
        assert data["results"][1]["access_granted"] is False

    def test_batch_check_access_validation_error_in_item(
        self, authenticated_client, api_url
    ):
        """Test batch check with invalid item."""
        response = authenticated_client.post(
            api_url("batch-check-access"),
            json={
                "checks": [
                    {
                        "service": "storage",
                        # Missing resource_name
                        "operation": "READ",
                    }
                ]
            },
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data["error"] == "validation_error"
