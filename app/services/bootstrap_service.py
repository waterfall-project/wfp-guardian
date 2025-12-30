# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Bootstrap service for RBAC initialization.

This module provides functionality to bootstrap the Guardian RBAC system
during the first company creation and for initializing standard roles
for new companies.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from collections.abc import Callable

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy
from app.models.role import Role
from app.models.user_role import UserRole
from app.utils.logger import logger


class BootstrapService:
    """Service for initializing RBAC structure for companies.

    This service creates standard roles, policies, and permission assignments
    for new companies in the Waterfall platform.
    """

    # Standard roles created for each company
    STANDARD_ROLES = [
        {
            "name": "company_admin",
            "display_name": "Company Administrator",
            "description": "Full access to all company resources and settings",
        },
        {
            "name": "project_manager",
            "display_name": "Project Manager",
            "description": "Can create and manage projects, assign team members",
        },
        {
            "name": "member",
            "display_name": "Member",
            "description": "Can participate in projects and access assigned resources",
        },
        {
            "name": "viewer",
            "display_name": "Viewer",
            "description": "Read-only access to company resources",
        },
    ]

    # Standard policies with their permission patterns
    STANDARD_POLICIES: list[dict[str, Any]] = [
        {
            "name": "company_admin_policy",
            "display_name": "Company Admin Policy",
            "description": "Full access to all resources",
            "permission_filter": lambda p: True,  # All permissions
        },
        {
            "name": "project_manager_policy",
            "display_name": "Project Manager Policy",
            "description": "Project management and team collaboration",
            "permission_filter": lambda p: p.operation
            in ["CREATE", "READ", "UPDATE", "LIST"]
            and p.resource_name not in ["config"],  # Cannot change system config
        },
        {
            "name": "member_policy",
            "display_name": "Member Policy",
            "description": "Basic participation and resource access",
            "permission_filter": lambda p: p.operation in ["READ", "UPDATE", "LIST"]
            and p.resource_name not in ["config", "dummy"],
        },
        {
            "name": "viewer_policy",
            "display_name": "Viewer Policy",
            "description": "Read-only access",
            "permission_filter": lambda p: p.operation in ["READ", "LIST"],
        },
    ]

    # Mapping of roles to their policies
    ROLE_POLICY_MAPPING = {
        "company_admin": ["company_admin_policy"],
        "project_manager": ["project_manager_policy"],
        "member": ["member_policy"],
        "viewer": ["viewer_policy"],
    }

    def __init__(self):
        """Initialize the bootstrap service."""
        pass

    def bootstrap_system(self, company_id: UUID, user_id: UUID) -> dict:
        """Initialize RBAC for the first company and assign admin role.

        This method is called during system bootstrap to:
        1. Create 4 standard roles for the company
        2. Create 4 standard policies with permissions
        3. Assign company_admin role to the first user

        Args:
            company_id: UUID of the first company.
            user_id: UUID of the first user (to be assigned company_admin).

        Returns:
            Dictionary with initialization results:
                - success: bool
                - company_id: str
                - user_id: str
                - roles_created: int
                - policies_created: int
                - permissions_assigned: int
                - message: str

        Raises:
            ValueError: If company or user already has roles initialized.
            IntegrityError: If database constraints are violated.
        """
        logger.info(
            f"Starting RBAC bootstrap for company_id={company_id}, user_id={user_id}"
        )

        try:
            # Check if company already has roles
            existing_roles = Role.query.filter_by(company_id=company_id).count()
            if existing_roles > 0:
                raise ValueError(
                    f"Company {company_id} already has {existing_roles} roles. Bootstrap can only run once."
                )

            # Create roles and policies
            roles_data = self._create_roles_and_policies(company_id)

            # Assign company_admin role to the first user
            company_admin_role = roles_data["roles"]["company_admin"]
            user_role = UserRole(
                user_id=str(user_id),
                role_id=str(company_admin_role.id),
                company_id=str(company_id),
                scope_type="direct",
                granted_by=str(user_id),  # Self-granted for first admin
            )
            db.session.add(user_role)
            db.session.commit()

            logger.info(
                f"RBAC bootstrap completed successfully for company_id={company_id}"
            )

            return {
                "success": True,
                "company_id": str(company_id),
                "user_id": str(user_id),
                "roles_created": roles_data["roles_created"],
                "policies_created": roles_data["policies_created"],
                "permissions_assigned": roles_data["permissions_assigned"],
                "message": "Guardian RBAC initialized successfully for first company",
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to bootstrap RBAC: {e}")
            raise

    def init_company_roles(self, company_id: UUID) -> dict:
        """Initialize standard roles and policies for a new company.

        This method creates the standard RBAC structure without assigning
        any user roles. It's called when a new company is created.

        Args:
            company_id: UUID of the newly created company.

        Returns:
            Dictionary with initialization results:
                - success: bool
                - company_id: str
                - roles_created: int
                - policies_created: int
                - roles: list[str]

        Raises:
            ValueError: If company already has roles.
            IntegrityError: If database constraints are violated.
        """
        logger.info(f"Initializing roles for new company_id={company_id}")

        try:
            # Check if company already has roles
            existing_roles = Role.query.filter_by(company_id=company_id).count()
            if existing_roles > 0:
                raise ValueError(
                    f"Company {company_id} already has {existing_roles} roles"
                )

            # Create roles and policies
            roles_data = self._create_roles_and_policies(company_id)

            logger.info(
                f"Company roles initialized successfully for company_id={company_id}"
            )

            return {
                "success": True,
                "company_id": str(company_id),
                "roles_created": roles_data["roles_created"],
                "policies_created": roles_data["policies_created"],
                "roles": [role["name"] for role in self.STANDARD_ROLES],
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to initialize company roles: {e}")
            raise

    def _create_roles_and_policies(self, company_id: UUID) -> dict:
        """Create standard roles, policies, and assign permissions.

        Internal method used by both bootstrap_system and init_company_roles.

        Args:
            company_id: UUID of the company.

        Returns:
            Dictionary with:
                - roles: dict[str, Role] (role_name -> Role instance)
                - roles_created: int
                - policies_created: int
                - permissions_assigned: int
        """
        created_roles = {}
        created_policies = {}
        total_permissions_assigned = 0

        # 1. Create roles
        for role_config in self.STANDARD_ROLES:
            role = Role(
                company_id=company_id,
                name=role_config["name"],
                display_name=role_config["display_name"],
                description=role_config["description"],
                is_active=True,
            )
            db.session.add(role)
            created_roles[role_config["name"]] = role

        db.session.flush()  # Get role IDs

        # 2. Create policies and assign permissions
        all_permissions = Permission.query.all()

        for policy_config in self.STANDARD_POLICIES:
            policy = Policy(
                company_id=company_id,
                name=str(policy_config["name"]),
                display_name=str(policy_config["display_name"]),
                description=str(policy_config["description"]),
                is_active=True,
            )

            # Filter and assign permissions based on policy rules
            permission_filter: Callable[[Any], bool] = policy_config[
                "permission_filter"
            ]
            for permission in all_permissions:
                if permission_filter(permission):
                    policy.permissions.append(permission)
                    total_permissions_assigned += 1

            db.session.add(policy)
            created_policies[policy_config["name"]] = policy

        db.session.flush()  # Get policy IDs

        # 3. Assign policies to roles
        for role_name, policy_names in self.ROLE_POLICY_MAPPING.items():
            role = created_roles[role_name]
            for policy_name in policy_names:
                policy = created_policies[policy_name]
                role.policies.append(policy)

        db.session.commit()

        return {
            "roles": created_roles,
            "roles_created": len(created_roles),
            "policies_created": len(created_policies),
            "permissions_assigned": total_permissions_assigned,
        }
