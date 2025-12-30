# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Access Control Resource module.

This module provides endpoints for checking user access permissions
against the Guardian service policies using RBAC.
"""

import time
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from flask import request
from flask_restful import Resource
from marshmallow import ValidationError

from app.models.permission import Permission
from app.models.role import Role
from app.models.user_role import UserRole
from app.schemas.access_schema import (
    BatchCheckAccessRequestSchema,
    CheckAccessRequestSchema,
)
from app.utils.jwt_utils import (
    get_company_id_from_jwt,
    get_user_id_from_jwt,
    require_jwt_auth,
)
from app.utils.logger import logger


def _get_active_user_roles(
    user_id: UUID | str, company_id: UUID | str, project_id: str | None = None
) -> list[UserRole]:
    """Get active, non-expired user roles for a user.

    Args:
        user_id: User UUID or string.
        company_id: Company UUID or string.
        project_id: Optional project UUID filter.

    Returns:
        List of active UserRole objects.
    """
    query = UserRole.query.filter_by(
        user_id=user_id,
        company_id=company_id,
        is_active=True,
    )

    # Filter by project if provided
    if project_id:
        query = query.filter(
            (UserRole.project_id == project_id) | (UserRole.project_id.is_(None))
        )

    # Check expiration
    now = datetime.now(UTC)
    query = query.filter((UserRole.expires_at.is_(None)) | (UserRole.expires_at > now))

    return cast("list", query.all())


def _check_policies_for_permission(role, user_role, permission):
    """Check if a role's policies contain a permission.

    Args:
        role: Role object to check.
        user_role: UserRole association.
        permission: Permission to look for.

    Returns:
        Matched role dict if found, None otherwise.
    """
    for policy in role.policies:
        if not policy.is_active:
            continue

        if permission in policy.permissions:
            return {
                "role_id": str(role.id),
                "role_name": role.name,
                "scope_type": user_role.scope_type,
                "project_id": (
                    str(user_role.project_id) if user_role.project_id else None
                ),
            }
    return None


def _check_permission_in_roles(
    user_roles: list, permission: Permission, company_id: UUID | str
) -> tuple[bool, dict | None]:
    """Check if permission exists in any of the user's roles.

    Args:
        user_roles: List of UserRole objects.
        permission: Permission to check for.
        company_id: Company UUID or string.

    Returns:
        Tuple of (access_granted, matched_role_info).
    """
    # Collect all role IDs and fetch roles in a single query to avoid N+1
    role_ids = {user_role.role_id for user_role in user_roles}
    if not role_ids:
        return False, None

    roles = Role.query.filter(
        Role.id.in_(role_ids),
        Role.company_id == company_id,
        Role.is_active == True,  # noqa: E712
    ).all()

    roles_by_id = {role.id: role for role in roles}

    for user_role in user_roles:
        role = roles_by_id.get(user_role.role_id)
        if not role:
            continue

        matched_role = _check_policies_for_permission(role, user_role, permission)
        if matched_role:
            return True, matched_role

    return False, None


class CheckAccessResource(Resource):
    """Resource for checking access permissions.

    This resource handles the verification of user permissions for specific
    operations on resources, supporting RBAC with project and company scopes.
    """

    @require_jwt_auth
    def post(self):
        """Check if user has permission to perform an operation.

        Request Body:
            {
                "service": "storage",
                "resource_name": "files",
                "operation": "DELETE",
                "context": {
                    "project_id": "uuid",  # optional
                    "target_company_id": "uuid",  # optional
                    "resource_id": "uuid"  # optional
                }
            }

        Returns:
            tuple: JSON response with access_granted, reason, message, etc.
        """
        start_time = time.time()

        # Validate request
        schema = CheckAccessRequestSchema()
        try:
            data = cast("dict", schema.load(request.get_json()))
        except ValidationError as err:
            logger.warning(f"Access check validation failed: {err.messages}")
            return {"error": "validation_error", "message": err.messages}, 422

        # Extract user context from JWT
        try:
            user_id = get_user_id_from_jwt()
            company_id = get_company_id_from_jwt()
        except RuntimeError as e:
            logger.error(f"JWT context error: {e}")
            return {"error": "unauthorized", "message": str(e)}, 401

        service: str = data["service"]
        resource_name: str = data["resource_name"]
        operation: str = data["operation"]
        context = cast("dict", data.get("context", {}))
        project_id: str | None = context.get("project_id")

        # Build permission name
        permission_name = f"{service}:{resource_name}:{operation}"

        logger.info(
            f"Checking access for user {user_id}: {permission_name}",
            extra={
                "user_id": user_id,
                "company_id": company_id,
                "project_id": project_id,
            },
        )

        # Check if permission exists in the system
        permission = Permission.query.filter_by(name=permission_name).first()
        if not permission:
            logger.warning(f"Permission not found: {permission_name}")
            return {
                "access_granted": False,
                "reason": "no_permission",
                "message": f"Permission '{permission_name}' does not exist in the system",
                "cache_hit": False,
            }, 200

        # Get user's active roles
        user_roles = _get_active_user_roles(user_id, company_id, project_id)

        if not user_roles:
            logger.info(f"No active roles found for user {user_id}")
            return {
                "access_granted": False,
                "reason": "no_matching_role",
                "message": "User does not have any active roles",
                "cache_hit": False,
            }, 200

        # Check if permission exists in any role
        access_granted, matched_role = _check_permission_in_roles(
            user_roles, permission, company_id
        )

        processing_time = int((time.time() - start_time) * 1000)

        if access_granted and matched_role:
            logger.info(
                f"Access granted for {user_id}: {permission_name}",
                extra={"processing_time_ms": processing_time},
            )
            return {
                "access_granted": True,
                "reason": "granted",
                "message": f"User has permission {permission_name}",
                "access_type": matched_role["scope_type"],
                "matched_role": matched_role,
                "cache_hit": False,
            }, 200

        logger.info(
            f"Access denied for {user_id}: {permission_name}",
            extra={"processing_time_ms": processing_time},
        )
        return {
            "access_granted": False,
            "reason": "no_permission",
            "message": f"User does not have permission {permission_name}",
            "cache_hit": False,
        }, 200


def _check_single_permission(
    user_id: UUID | str,
    company_id: UUID | str,
    service: str,
    resource_name: str,
    operation: str,
    project_id: str | None = None,
) -> dict:
    """Check a single permission for a user.

    Args:
        user_id: User UUID or string.
        company_id: Company UUID or string.
        service: Service name.
        resource_name: Resource name.
        operation: Operation name.
        project_id: Optional project UUID.

    Returns:
        Dictionary with access check result.
    """
    permission_name = f"{service}:{resource_name}:{operation}"

    # Check if permission exists
    permission = Permission.query.filter_by(name=permission_name).first()
    if not permission:
        return {
            "access_granted": False,
            "reason": "no_permission",
            "message": f"Permission '{permission_name}' does not exist in the system",
            "cache_hit": False,
        }

    # Get user's active roles
    user_roles = _get_active_user_roles(user_id, company_id, project_id)

    if not user_roles:
        return {
            "access_granted": False,
            "reason": "no_matching_role",
            "message": "User does not have any active roles",
            "cache_hit": False,
        }

    # Check if permission exists in any role
    access_granted, matched_role = _check_permission_in_roles(
        user_roles, permission, company_id
    )

    if access_granted and matched_role:
        return {
            "access_granted": True,
            "reason": "granted",
            "message": f"User has permission {permission_name}",
            "access_type": matched_role["scope_type"],
            "matched_role": matched_role,
            "cache_hit": False,
        }

    return {
        "access_granted": False,
        "reason": "no_permission",
        "message": f"User does not have permission {permission_name}",
        "cache_hit": False,
    }


class BatchCheckAccessResource(Resource):
    """Resource for batch checking multiple access permissions.

    Allows checking up to 50 permissions in a single request.
    """

    @require_jwt_auth
    def post(self):
        """Check multiple permissions in batch.

        Request Body:
            {
                "checks": [
                    {"service": "storage", "resource_name": "files", "operation": "DELETE"},
                    {"service": "diagram", "resource_name": "diagrams", "operation": "CREATE"}
                ]
            }

        Returns:
            tuple: JSON response with array of results
        """
        start_time = time.time()

        # Validate request
        schema = BatchCheckAccessRequestSchema()
        try:
            data = cast("dict", schema.load(request.get_json()))
        except ValidationError as err:
            logger.warning(f"Batch access check validation failed: {err.messages}")
            return {"error": "validation_error", "message": err.messages}, 422

        checks = data["checks"]
        logger.info(f"Batch checking {len(checks)} permissions")

        # Extract user context from JWT once for all checks
        try:
            user_id = get_user_id_from_jwt()
            company_id = get_company_id_from_jwt()
        except RuntimeError as e:
            logger.error(f"JWT context error: {e}")
            return {"error": "unauthorized", "message": str(e)}, 401

        # Process each check
        results = [
            _check_single_permission(
                user_id,
                company_id,
                check["service"],
                check["resource_name"],
                check["operation"],
                check.get("context", {}).get("project_id"),
            )
            for check in checks
        ]

        processing_time = int((time.time() - start_time) * 1000)
        logger.info(
            f"Batch check completed: {len(checks)} checks in {processing_time}ms"
        )

        return {
            "results": results,
            "processing_time_ms": processing_time,
        }, 200


def _build_role_info(user_role, role) -> dict:
    """Build role information dictionary."""
    return {
        "role_id": str(role.id),
        "role_name": role.name,
        "role_display_name": role.display_name,
        "scope_type": user_role.scope_type,
        "project_id": str(user_role.project_id) if user_role.project_id else None,
        "expires_at": (
            user_role.expires_at.isoformat() if user_role.expires_at else None
        ),
    }


def _build_policy_info(policy) -> dict:
    """Build policy information dictionary."""
    return {
        "policy_id": str(policy.id),
        "policy_name": policy.name,
        "policy_display_name": policy.display_name,
        "priority": policy.priority,
    }


def _build_permission_info(permission) -> dict:
    """Build permission information dictionary."""
    return {
        "permission_id": str(permission.id),
        "permission_name": permission.name,
        "service": permission.service,
        "resource_name": permission.resource_name,
        "operation": permission.operation,
        "description": permission.description,
    }


def _process_role_policies(
    role, policies_data, policies_set, permissions_set, permissions_list
):
    """Process policies and permissions for a role.

    Args:
        role: Role object to process.
        policies_data: List to append policy info to.
        policies_set: Set to track processed policy IDs.
        permissions_set: Set to track processed permissions.
        permissions_list: List to append permission info to.
    """
    for policy in role.policies:
        if not policy.is_active:
            continue

        # Use set for O(1) lookup instead of list comparison
        if policy.id not in policies_set:
            policies_set.add(policy.id)
            policies_data.append(_build_policy_info(policy))

        # Process permissions
        for permission in policy.permissions:
            if permission.id not in permissions_set:
                permissions_set.add(permission.id)
                permissions_list.append(_build_permission_info(permission))


def _collect_user_permissions(
    user_roles: list, company_id: UUID | str
) -> tuple[list[dict], list[dict], list[dict]]:
    """Collect roles, policies, and permissions from user roles.

    Args:
        user_roles: List of UserRole objects.
        company_id: Company UUID or string.

    Returns:
        Tuple of (roles_data, policies_data, permissions_list).
    """
    roles_data: list[dict] = []
    policies_data: list[dict] = []
    policies_set: set = set()
    permissions_set: set = set()
    permissions_list: list[dict] = []

    # Collect all role IDs and fetch roles in a single query to avoid N+1
    role_ids = {user_role.role_id for user_role in user_roles}
    if not role_ids:
        return roles_data, policies_data, permissions_list

    roles = Role.query.filter(
        Role.id.in_(role_ids),
        Role.company_id == company_id,
        Role.is_active == True,  # noqa: E712
    ).all()

    roles_by_id = {role.id: role for role in roles}

    for user_role in user_roles:
        role = roles_by_id.get(user_role.role_id)
        if not role:
            continue

        # Add role info
        roles_data.append(_build_role_info(user_role, role))

        # Process policies and permissions
        _process_role_policies(
            role, policies_data, policies_set, permissions_set, permissions_list
        )

    return roles_data, policies_data, permissions_list


class UserPermissionsResource(Resource):
    """Resource for retrieving all permissions for a specific user.

    Provides a comprehensive view of a user's effective permissions
    by traversing their roles, policies, and permission assignments.
    """

    @require_jwt_auth
    def get(self, user_id: str):
        """Get all permissions for a user.

        Args:
            user_id: UUID of the user to query permissions for.

        Query Parameters:
            project_id (optional): Filter by specific project scope.

        Returns:
            tuple: JSON response with roles, policies, and permissions arrays.
        """
        start_time = time.time()

        # Extract company context from JWT
        try:
            company_id = get_company_id_from_jwt()
            authenticated_user_id = get_user_id_from_jwt()
        except RuntimeError as e:
            logger.error(f"JWT context error: {e}")
            return {"error": "unauthorized", "message": str(e)}, 401

        # Optional: Check if user can view this user's permissions
        # For now, users can only view their own permissions
        if str(authenticated_user_id) != user_id:
            return {
                "error": "forbidden",
                "message": "You can only view your own permissions",
            }, 403

        project_id = request.args.get("project_id")

        logger.info(
            f"Retrieving permissions for user {user_id}",
            extra={"company_id": company_id, "project_id": project_id},
        )

        # Get user's active roles
        user_roles = _get_active_user_roles(user_id, company_id, project_id)

        if not user_roles:
            return {
                "user_id": user_id,
                "company_id": str(company_id),
                "project_id": project_id,
                "roles": [],
                "policies": [],
                "permissions": [],
                "total_permissions": 0,
            }, 200

        # Collect all roles, policies, and permissions
        roles_data, policies_data, permissions_list = _collect_user_permissions(
            user_roles, company_id
        )

        processing_time = int((time.time() - start_time) * 1000)
        logger.info(
            f"Retrieved {len(permissions_list)} permissions for user {user_id}",
            extra={"processing_time_ms": processing_time},
        )

        return {
            "user_id": user_id,
            "company_id": str(company_id),
            "project_id": project_id,
            "roles": roles_data,
            "policies": policies_data,
            "permissions": permissions_list,
            "total_permissions": len(permissions_list),
            "processing_time_ms": processing_time,
        }, 200
