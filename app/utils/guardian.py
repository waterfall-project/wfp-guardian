# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Guardian access control decorator.

This module provides the @access_required decorator for protecting Flask-RESTful
resources with Guardian permission checks.
"""

import re
from enum import Enum
from functools import wraps
from typing import Any
from uuid import UUID

from flask import g, jsonify, request

from app.service import SERVICE_NAME
from app.utils.logger import logger


class Operation(str, Enum):
    """Guardian operation types for access control.

    These operations represent the standard CRUD operations plus LIST
    for collection endpoints.
    """

    LIST = "LIST"
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    Args:
        name: CamelCase string to convert.

    Returns:
        snake_case version of the string.

    Examples:
        >>> camel_to_snake("ProjectResource")
        'project_resource'
        >>> camel_to_snake("MilestoneList")
        'milestone_list'
    """
    # Insert underscore before uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _get_resource_name(kwargs: dict, args: tuple) -> str | None:
    """Extract resource name from kwargs, request, or class name.

    The resource name is extracted in the following priority order:
    1. From kwargs['resource_name']
    2. From request.view_args['resource_name']
    3. From the class name (converted from CamelCase to snake_case)

    For class names ending with "Resource", the suffix is removed.
    For resource names ending with "_list", the suffix is removed.

    Args:
        kwargs: View function keyword arguments.
        args: View function positional arguments (first arg is usually self).

    Returns:
        Resource name in snake_case, or None if not found.

    Examples:
        >>> # From class ProjectResource
        >>> _get_resource_name({}, [project_resource_instance])
        'project'
    """
    # Try to get from kwargs
    resource_name = kwargs.get("resource_name")

    # Try to get from request.view_args
    if not resource_name and request.view_args:
        resource_name = request.view_args.get("resource_name")

    # Try to deduce from class name
    if not resource_name:
        view_self = args[0] if args else None
        if view_self and hasattr(view_self, "__class__"):
            class_name = view_self.__class__.__name__
            # Remove "Resource" suffix if present
            if class_name.lower().endswith("resource"):
                base_name = class_name[:-8]  # Remove "Resource" (8 chars)
                resource_name = camel_to_snake(base_name)

    # Normalize: remove "_list" suffix if present
    if resource_name and resource_name.endswith("_list"):
        resource_name = resource_name[:-5]  # Remove "_list" (5 chars)

    return resource_name


def _get_user_id() -> str | None:
    """Extract user_id from Flask g.user_context.

    The user_context is set by the @require_jwt_auth decorator,
    which must be applied before @access_required.

    Returns:
        User ID as string, or None if not found.

    Examples:
        >>> # After @require_jwt_auth has run
        >>> _get_user_id()
        '12345678-1234-5678-1234-567812345678'
    """
    user_context = getattr(g, "user_context", None)
    if not user_context:
        logger.warning("user_context_not_found_in_g")
        return None

    user_id = user_context.get("user_id")
    if not user_id:
        logger.warning("user_id_not_found_in_user_context")
        return None

    return str(user_id)


def check_access(
    user_id: UUID,
    service: str,
    resource: str,
    operation: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check user access permission via Guardian service.

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
    """
    # Mock implementation: always grant access
    logger.debug(
        "guardian_check_access_mock",
        user_id=str(user_id),
        service=service,
        resource=resource,
        operation=operation,
    )
    return {
        "access_granted": True,
        "reason": "mock_access_granted",
        "message": "Access granted by mock implementation",
    }


def access_required(operation: Operation):
    """Decorator to check user access permission via Guardian service.

    This decorator must be applied AFTER @require_jwt_auth, as it relies
    on g.user_context being populated.

    The decorator:
    1. Extracts user_id from g.user_context
    2. Extracts resource name from the class name
    3. Gets service name from SERVICE_NAME constant
    4. Calls Guardian check_access endpoint
    5. Returns 403 if access is denied

    Args:
        operation: Operation type from Operation enum (LIST, CREATE, READ, UPDATE, DELETE).

    Returns:
        Decorated function that checks access before execution.

    Examples:
        >>> from app.utils.guardian import Operation
        >>> class ProjectResource(Resource):
        ...     @require_jwt_auth
        ...     @access_required(Operation.LIST)
        ...     def get(self):
        ...         return {"projects": []}

    Raises:
        400: If user_id or resource_name cannot be determined.
        403: If Guardian denies access.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            # Extract resource name from class
            resource_name = _get_resource_name(kwargs, args)
            if not resource_name:
                logger.warning("resource_name_not_found_for_access_check")
                return (
                    jsonify(
                        {
                            "error": "Access check failed",
                            "message": "Resource name could not be determined",
                        }
                    ),
                    400,
                )

            # Extract user_id from g.user_context
            user_id = _get_user_id()
            if not user_id:
                logger.warning("user_id_not_found_for_access_check")
                return (
                    jsonify(
                        {
                            "error": "Access check failed",
                            "message": "User ID could not be determined",
                        }
                    ),
                    400,
                )

            # Call Guardian check_access
            logger.debug(
                "checking_guardian_access",
                user_id=user_id,
                service=SERVICE_NAME,
                resource=resource_name,
                operation=operation.value,
            )

            result = check_access(
                user_id=UUID(user_id),
                service=SERVICE_NAME,
                resource=resource_name,
                operation=operation.value,
                context=None,
            )

            # Check if access is granted
            if result.get("access_granted", False):
                logger.debug(
                    "guardian_access_granted",
                    user_id=user_id,
                    resource=resource_name,
                    operation=operation.value,
                )
                return view_func(*args, **kwargs)

            # Access denied
            reason = result.get("reason", "Unknown")
            message = result.get("message", "Access denied")

            logger.warning(
                "guardian_access_denied",
                user_id=user_id,
                resource=resource_name,
                operation=operation.value,
                reason=reason,
            )

            return (
                jsonify(
                    {
                        "error": "Access denied",
                        "reason": reason,
                        "message": message,
                    }
                ),
                403,
            )

        return wrapped

    return decorator
