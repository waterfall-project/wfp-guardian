# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Guardian service client.

This module provides functions to interact with the Guardian service
for permission checks and user authorization in a multi-tenant context.
"""

from typing import Any, Optional
from uuid import UUID

import requests
from flask import current_app, request

from app.utils.logger import logger


def check_access(
    user_id: UUID,
    service: str,
    resource: str,
    operation: str,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Check user access permission via Guardian service.

    Calls Guardian /check-access endpoint to verify if a user has permission
    to perform an operation on a specific resource.

    Args:
        user_id: UUID of the user making the request.
        service: Service identifier (e.g., "project", "storage").
        resource: Resource type (e.g., "projects", "milestones").
        operation: Operation type (LIST, CREATE, READ, UPDATE, DELETE).
        context: Optional context dictionary with project_id, target_company_id, etc.

    Returns:
        Dictionary containing access decision:
        {
            "access_granted": bool,
            "reason": str,
            "message": str
        }

    Examples:
        >>> result = check_access(
        ...     user_id,
        ...     "project",
        ...     "projects",
        ...     "READ",
        ...     {"project_id": str(project_id)}
        ... )
        >>> if result["access_granted"]:
        ...     # Allow access
    """
    # Skip Guardian check if service is disabled
    if not current_app.config.get("USE_GUARDIAN_SERVICE", True):
        logger.debug(
            "guardian_disabled_granting_access",
            user_id=str(user_id),
            service=service,
            resource=resource,
            operation=operation,
        )
        return {
            "access_granted": True,
            "reason": "guardian_disabled",
            "message": "Guardian service disabled - access granted by default",
        }

    url = f"{current_app.config['GUARDIAN_SERVICE_URL']}/check-access"

    payload = {
        "service": service,
        "resource": resource,
        "operation": operation,
        "context": context or {},
    }

    # Forward cookies from the current request to Guardian service
    cookies = request.cookies.to_dict() if request else {}

    try:
        response = requests.post(  # nosec B113
            url,
            json=payload,
            cookies=cookies,
            timeout=current_app.config.get("EXTERNAL_SERVICES_TIMEOUT", 5),
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    except requests.Timeout:
        logger.error("guardian_timeout", url=url, user_id=str(user_id))
        return {
            "access_granted": False,
            "reason": "guardian_timeout",
            "message": "Guardian service unavailable",
        }

    except requests.HTTPError as e:
        logger.error("guardian_http_error", error=str(e), user_id=str(user_id))
        return {"access_granted": False, "reason": "guardian_error", "message": str(e)}


def get_user_permissions(user_id: UUID, company_id: UUID) -> dict[str, Any]:
    """Retrieve all user permissions via Guardian service.

    Used for filtering project lists with project-scoped permissions.
    Returns permissions with different scope types (direct, hierarchical).

    Args:
        user_id: UUID of the user.
        company_id: UUID of the company context.

    Returns:
        Dictionary containing permissions list:
        {
            "permissions": [
                {
                    "permission": "project:projects:READ",
                    "project_id": null | "uuid",
                    "scope_type": "direct" | "hierarchical",
                    "role_name": "Project Manager"
                }
            ]
        }

    Examples:
        >>> result = get_user_permissions(user_id, company_id)
        >>> for perm in result['permissions']:
        ...     if perm['permission'].startswith('project:projects:'):
        ...         if perm['project_id'] is None:
        ...             # UserRole.project_id = NULL → company-wide access
        ...             has_company_wide_access = True
        ...         else:
        ...             # UserRole.project_id = UUID → project-scoped
        ...             accessible_project_ids.append(perm['project_id'])
    """
    # Skip Guardian check if service is disabled
    if not current_app.config.get("USE_GUARDIAN_SERVICE", True):
        logger.debug(
            "guardian_disabled_returning_empty_permissions",
            user_id=str(user_id),
            company_id=str(company_id),
        )
        return {"permissions": []}

    url = f"{current_app.config['GUARDIAN_SERVICE_URL']}/users/{user_id}/permissions"

    # Forward cookies from the current request to Guardian service
    cookies = request.cookies.to_dict() if request else {}

    try:
        response = requests.get(  # nosec B113
            url,
            params={"company_id": str(company_id)},
            cookies=cookies,
            timeout=current_app.config.get("EXTERNAL_SERVICES_TIMEOUT", 5),
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    except requests.Timeout:
        logger.error("guardian_timeout", url=url, user_id=str(user_id))
        return {"permissions": []}

    except requests.HTTPError as e:
        logger.error("guardian_http_error", error=str(e), user_id=str(user_id))
        return {"permissions": []}
