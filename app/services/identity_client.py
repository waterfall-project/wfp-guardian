# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Identity service client.

This module provides functions to interact with the Identity service
for validating companies, retrieving user information, and managing
company hierarchies in a multi-tenant context.
"""

from typing import Any, Optional
from uuid import UUID

import requests
from flask import current_app, request

from app.utils.logger import logger


def get_user(
    user_id: UUID, company_id: Optional[UUID] = None
) -> Optional[dict[str, Any]]:
    """Retrieve user details via Identity service.

    Used to display audit trail information (changed_by, created_by names).

    Args:
        user_id: UUID of the user to retrieve.
        company_id: Optional company context for multi-tenancy.

    Returns:
        User data dictionary if found, None otherwise:
        {
            "id": "uuid",
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "company_id": "uuid",
            "is_active": true
        }

    Examples:
        >>> user = get_user(user_id, company_id)
        >>> if user:
        >>>     display_name = f"{user['first_name']} {user['last_name']}"
    """
    url = f"{current_app.config['IDENTITY_SERVICE_URL']}/users/{user_id}"

    params = {}
    if company_id:
        params["company_id"] = str(company_id)

    # Forward cookies from the current request to Identity service
    cookies = request.cookies.to_dict() if request else {}

    try:
        response = requests.get(  # nosec B113
            url,
            params=params,
            cookies=cookies,
            timeout=current_app.config.get("EXTERNAL_SERVICES_TIMEOUT", 5),
        )

        if response.status_code == 200:
            result: dict[str, Any] = response.json()
            return result

        logger.warning(
            "user_not_found_in_identity",
            user_id=str(user_id),
            status_code=response.status_code,
        )
        return None

    except requests.RequestException as e:
        logger.error(
            "identity_service_error_fetching_user",
            user_id=str(user_id),
            error=str(e),
        )
        return None


def get_company_hierarchy(company_id: UUID) -> Optional[dict[str, Any]]:
    """Retrieve company hierarchy (parent/children).

    Used for filtering projects with hierarchical visibility.

    Args:
        company_id: UUID of the company.

    Returns:
        Hierarchy data dictionary if found, None otherwise:
        {
            "company_id": "uuid",
            "parent_id": "uuid" | null,
            "children_ids": ["uuid1", "uuid2"],
            "depth": 2,
            "path": ["root_id", "parent_id", "company_id"]
        }

    Examples:
        >>> hierarchy = get_company_hierarchy(company_id)
        >>> if hierarchy:
        >>>     # Filter visible projects (company + children)
        >>>     visible_company_ids = [company_id] + hierarchy['children_ids']
        >>>     query = query.filter(Project.company_id.in_(visible_company_ids))
    """
    url = (
        f"{current_app.config['IDENTITY_SERVICE_URL']}/companies/{company_id}/hierarchy"
    )

    # Forward cookies from the current request to Identity service
    cookies = request.cookies.to_dict() if request else {}

    try:
        response = requests.get(  # nosec B113
            url,
            cookies=cookies,
            timeout=current_app.config.get("EXTERNAL_SERVICES_TIMEOUT", 5),
        )

        if response.status_code == 200:
            result: dict[str, Any] = response.json()
            return result

        logger.warning(
            "company_hierarchy_not_found",
            company_id=str(company_id),
            status_code=response.status_code,
        )
        return None

    except requests.RequestException as e:
        logger.error(
            "identity_service_error_fetching_hierarchy",
            company_id=str(company_id),
            error=str(e),
        )
        return None


def validate_user_company_access(user_id: UUID, company_id: UUID) -> tuple[bool, str]:
    """Validate user access to company resources with hierarchical permissions.

    This function implements top-down hierarchical access control where users
    from parent companies can access child company resources, but not vice versa.

    The validation process:
    1. Retrieve user information from Identity service
    2. Check user exists and is active
    3. Get user's company_id (company of belonging)
    4. If user's company matches requested company_id, grant access
    5. If different, retrieve company hierarchy
    6. Check if user's company is in the parent path (top-down access)

    Args:
        user_id: UUID of the user making the request.
        company_id: UUID of the company resource being accessed.

    Returns:
        A tuple of (is_authorized, error_message):
        - (True, "") if user has access to the company
        - (False, "reason") if access is denied

    Examples:
        >>> # User from parent company accessing child company resource
        >>> is_authorized, error = validate_user_company_access(user_id, child_company_id)
        >>> if not is_authorized:
        >>>     return {"error": error}, 403

        >>> # User from child company trying to access parent resource (denied)
        >>> is_authorized, error = validate_user_company_access(user_id, parent_company_id)
        >>> # Returns (False, "Access denied: insufficient permissions")
    """
    # 1. Retrieve user information
    user = get_user(user_id)
    if not user:
        return False, f"User {user_id} not found"

    # 2. Check user is active
    if not user.get("is_active", False):
        return False, "User account is not active"

    # 3. Get user's company
    user_company_id_str = user.get("company_id")
    if not user_company_id_str:
        return False, "User has no company assigned"

    user_company_id = UUID(user_company_id_str)

    # 4. If user's company matches requested company, grant access
    if user_company_id == company_id:
        return True, ""

    # 5. Check hierarchical access (user from parent company accessing child)
    hierarchy = get_company_hierarchy(company_id)
    if not hierarchy:
        # If we can't get hierarchy, deny access (fail-closed)
        logger.warning(
            "company_hierarchy_unavailable_denying_access",
            user_id=str(user_id),
            company_id=str(company_id),
        )
        return False, "Unable to verify company hierarchy"

    # 6. Check if user's company is in the parent path
    path = hierarchy.get("path", [])
    if str(user_company_id) in path:
        # User's company is a parent in the hierarchy - grant access
        return True, ""

    # User's company is not in the path - deny access
    return False, "Access denied: insufficient permissions"
