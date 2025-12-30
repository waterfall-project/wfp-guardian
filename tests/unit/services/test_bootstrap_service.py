# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for BootstrapService.

Tests RBAC initialization for companies, including role creation,
policy creation, permission assignment, and user role assignment.
"""

from uuid import uuid4

import pytest

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy
from app.models.role import Role
from app.models.user_role import UserRole
from app.services.bootstrap_service import BootstrapService


class TestBootstrapService:
    """Test suite for BootstrapService."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()

            # Seed some permissions for testing
            permissions = [
                Permission(
                    name="test:config:READ",
                    service="test",
                    resource_name="config",
                    operation="READ",
                ),
                Permission(
                    name="test:files:CREATE",
                    service="test",
                    resource_name="files",
                    operation="CREATE",
                ),
                Permission(
                    name="test:files:READ",
                    service="test",
                    resource_name="files",
                    operation="READ",
                ),
                Permission(
                    name="test:files:UPDATE",
                    service="test",
                    resource_name="files",
                    operation="UPDATE",
                ),
                Permission(
                    name="test:files:DELETE",
                    service="test",
                    resource_name="files",
                    operation="DELETE",
                ),
                Permission(
                    name="test:files:LIST",
                    service="test",
                    resource_name="files",
                    operation="LIST",
                ),
            ]
            db.session.add_all(permissions)
            db.session.commit()

            yield

            db.session.remove()
            db.drop_all()

    def test_bootstrap_system_creates_roles_and_policies(self, app):
        """Test that bootstrap_system creates 4 standard roles and policies."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            result = service.bootstrap_system(company_id, user_id)

            # Check result structure
            assert result["success"] is True
            assert result["company_id"] == str(company_id)
            assert result["user_id"] == str(user_id)
            assert result["roles_created"] == 4
            assert result["policies_created"] == 4
            assert result["permissions_assigned"] > 0
            assert "Guardian RBAC initialized" in result["message"]

            # Verify roles in database
            roles = Role.query.filter_by(company_id=company_id).all()
            assert len(roles) == 4
            role_names = {r.name for r in roles}
            assert role_names == {
                "company_admin",
                "project_manager",
                "member",
                "viewer",
            }

            # Verify policies in database
            policies = Policy.query.filter_by(company_id=company_id).all()
            assert len(policies) == 4
            policy_names = {p.name for p in policies}
            assert policy_names == {
                "company_admin_policy",
                "project_manager_policy",
                "member_policy",
                "viewer_policy",
            }

    def test_bootstrap_system_assigns_company_admin_to_user(self, app):
        """Test that bootstrap_system assigns company_admin role to the user."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            service.bootstrap_system(company_id, user_id)

            # Verify user role assignment
            user_roles = UserRole.query.filter_by(
                user_id=str(user_id), company_id=str(company_id)
            ).all()
            assert len(user_roles) == 1

            user_role = user_roles[0]
            assert user_role.role.name == "company_admin"
            assert user_role.scope_type == "direct"
            assert str(user_role.granted_by) == str(user_id)  # Self-granted
            assert user_role.is_active is True

    def test_bootstrap_system_fails_if_company_already_initialized(self, app):
        """Test that bootstrap_system fails if company already has roles."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            # First bootstrap
            service.bootstrap_system(company_id, user_id)

            # Try to bootstrap again
            with pytest.raises(ValueError, match="already has .* roles"):
                service.bootstrap_system(company_id, uuid4())

    def test_bootstrap_system_roles_have_correct_attributes(self, app):
        """Test that created roles have correct attributes."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            service.bootstrap_system(company_id, user_id)

            # Check company_admin role
            admin_role = Role.query.filter_by(
                company_id=company_id, name="company_admin"
            ).first()
            assert admin_role is not None
            assert admin_role.display_name == "Company Administrator"
            assert "Full access" in admin_role.description
            assert admin_role.is_active is True

            # Check viewer role
            viewer_role = Role.query.filter_by(
                company_id=company_id, name="viewer"
            ).first()
            assert viewer_role is not None
            assert viewer_role.display_name == "Viewer"
            assert "Read-only" in viewer_role.description
            assert viewer_role.is_active is True

    def test_bootstrap_system_policies_have_permissions(self, app):
        """Test that policies are assigned appropriate permissions."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            service.bootstrap_system(company_id, user_id)

            # Company admin should have all permissions
            admin_policy = Policy.query.filter_by(
                company_id=company_id, name="company_admin_policy"
            ).first()
            assert len(admin_policy.permissions) == 6  # All seeded permissions

            # Viewer should only have READ and LIST permissions
            viewer_policy = Policy.query.filter_by(
                company_id=company_id, name="viewer_policy"
            ).first()
            viewer_operations = {p.operation for p in viewer_policy.permissions}
            assert viewer_operations == {"READ", "LIST"}

    def test_bootstrap_system_roles_linked_to_policies(self, app):
        """Test that roles are correctly linked to their policies."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            service.bootstrap_system(company_id, user_id)

            # Check company_admin role has company_admin_policy
            admin_role = Role.query.filter_by(
                company_id=company_id, name="company_admin"
            ).first()
            assert len(admin_role.policies) == 1
            assert admin_role.policies[0].name == "company_admin_policy"

            # Check project_manager role has project_manager_policy
            pm_role = Role.query.filter_by(
                company_id=company_id, name="project_manager"
            ).first()
            assert len(pm_role.policies) == 1
            assert pm_role.policies[0].name == "project_manager_policy"

    def test_init_company_roles_creates_roles_without_user_assignment(self, app):
        """Test that init_company_roles creates roles but doesn't assign users."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()

            result = service.init_company_roles(company_id)

            # Check result structure
            assert result["success"] is True
            assert result["company_id"] == str(company_id)
            assert result["roles_created"] == 4
            assert result["policies_created"] == 4
            assert len(result["roles"]) == 4
            assert "company_admin" in result["roles"]

            # Verify no user roles were created
            user_roles = UserRole.query.filter_by(company_id=str(company_id)).all()
            assert len(user_roles) == 0

    def test_init_company_roles_fails_if_company_already_has_roles(self, app):
        """Test that init_company_roles fails if company already has roles."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()

            # First initialization
            service.init_company_roles(company_id)

            # Try to initialize again
            with pytest.raises(ValueError, match="already has .* roles"):
                service.init_company_roles(company_id)

    def test_create_roles_and_policies_returns_correct_structure(self, app):
        """Test internal _create_roles_and_policies method."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()

            result = service._create_roles_and_policies(company_id)

            # Check return structure
            assert "roles" in result
            assert "roles_created" in result
            assert "policies_created" in result
            assert "permissions_assigned" in result

            assert len(result["roles"]) == 4
            assert result["roles_created"] == 4
            assert result["policies_created"] == 4
            assert result["permissions_assigned"] > 0

            # Check role keys
            assert "company_admin" in result["roles"]
            assert "project_manager" in result["roles"]
            assert "member" in result["roles"]
            assert "viewer" in result["roles"]

    def test_permission_filter_company_admin_gets_all_permissions(self, app):
        """Test that company_admin_policy gets all permissions."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()

            service._create_roles_and_policies(company_id)

            admin_policy = Policy.query.filter_by(
                company_id=company_id, name="company_admin_policy"
            ).first()

            # Should have all 6 seeded permissions
            assert len(admin_policy.permissions) == 6
            operations = {p.operation for p in admin_policy.permissions}
            assert operations == {"READ", "CREATE", "UPDATE", "DELETE", "LIST"}

    def test_permission_filter_member_excludes_config_and_dummy(self, app):
        """Test that member_policy excludes config and dummy resources."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()

            service._create_roles_and_policies(company_id)

            member_policy = Policy.query.filter_by(
                company_id=company_id, name="member_policy"
            ).first()

            # Should exclude config resource
            resource_names = {p.resource_name for p in member_policy.permissions}
            assert "config" not in resource_names

            # Should only have READ, UPDATE, LIST operations
            operations = {p.operation for p in member_policy.permissions}
            assert operations.issubset({"READ", "UPDATE", "LIST"})
            assert "CREATE" not in operations
            assert "DELETE" not in operations

    def test_multiple_companies_can_be_initialized(self, app):
        """Test that multiple companies can each have their own RBAC setup."""
        with app.app_context():
            service = BootstrapService()
            company1_id = uuid4()
            company2_id = uuid4()
            user1_id = uuid4()
            user2_id = uuid4()

            # Initialize two companies
            service.bootstrap_system(company1_id, user1_id)
            service.bootstrap_system(company2_id, user2_id)

            # Verify both companies have separate roles
            company1_roles = Role.query.filter_by(company_id=company1_id).all()
            company2_roles = Role.query.filter_by(company_id=company2_id).all()

            assert len(company1_roles) == 4
            assert len(company2_roles) == 4

            # Verify role IDs are different (separate entities)
            company1_role_ids = {r.id for r in company1_roles}
            company2_role_ids = {r.id for r in company2_roles}
            assert company1_role_ids.isdisjoint(company2_role_ids)

    def test_bootstrap_rollback_on_error(self, app):
        """Test that database changes are rolled back on error."""
        with app.app_context():
            service = BootstrapService()
            company_id = uuid4()
            user_id = uuid4()

            # First successful bootstrap
            service.bootstrap_system(company_id, user_id)

            initial_role_count = Role.query.filter_by(company_id=company_id).count()

            # Try to bootstrap again (should fail and rollback)
            with pytest.raises(ValueError):
                service.bootstrap_system(company_id, uuid4())

            # Verify no additional roles were created
            final_role_count = Role.query.filter_by(company_id=company_id).count()
            assert final_role_count == initial_role_count
