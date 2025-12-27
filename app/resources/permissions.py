# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Permission REST API resources.

This module defines the Flask-RESTful resources for accessing Permission entities.
Permissions are read-only and seeded from permissions.json at application startup.
"""

from flask import current_app, request
from flask_restful import Resource

from app.models.db import db
from app.models.permission import Permission
from app.utils.guardian import Operation, access_required
from app.utils.jwt_utils import require_jwt_auth
from app.utils.limiter import limiter
from app.utils.logger import logger


class PermissionListResource(Resource):
    """Resource for listing Permission entities.

    Provides endpoint for:
    - Listing all Permission entities with optional filtering (GET)

    Permissions are read-only. Use sync_permissions.py script to update them.
    """

    @require_jwt_auth
    @access_required(Operation.LIST)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """Retrieve Permission entities with optional filtering and pagination.

        Query Parameters:
            service (str, optional): Filter by service name
            resource_name (str, optional): Filter by resource name
            operation (str, optional): Filter by operation (LIST, CREATE, READ, etc.)
            page (int, optional): Page number (1-indexed). Default: 1
            page_size (int, optional): Items per page. Default from config (PAGE_LIMIT),
                Max from config (MAX_PAGE_LIMIT)

        Returns:
            tuple: (dict, int). JSON response body with:
                - data (list): List of Permission entities for this page.
                - pagination (dict): Pagination metadata (page, page_size, total_items, total_pages)

        Example response:
            {
                "data": [
                    {
                        "id": "uuid",
                        "name": "storage:files:DELETE",
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "DELETE",
                        "description": "Storage files resource - DELETE",
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 50,
                    "total_items": 1,
                    "total_pages": 1
                }
            }
        """
        logger.info("Retrieving permissions")

        # Parse pagination and filter parameters
        try:
            page = int(request.args.get("page", default=1))
            page_size = int(
                request.args.get("page_size", default=current_app.config["PAGE_LIMIT"])
            )
            max_page_size = current_app.config["MAX_PAGE_LIMIT"]

            # Validate pagination parameters
            if page < 1:
                logger.warning(f"Invalid page parameter: {page}. Must be >= 1")
                return {
                    "error": "invalid_parameter",
                    "message": "Page must be >= 1",
                }, 400

            if page_size < 1 or page_size > max_page_size:
                logger.warning(
                    f"Invalid page_size parameter: {page_size}. Must be between 1 and {max_page_size}"
                )
                return {
                    "error": "invalid_parameter",
                    "message": f"Page size must be between 1 and {max_page_size}",
                }, 400

            # Calculate offset from page number
            offset = (page - 1) * page_size

            # Parse filter parameters
            service = request.args.get("service", type=str)
            resource_name = request.args.get("resource_name", type=str)
            operation = request.args.get("operation", type=str)

            # Build query based on filters
            query = Permission.query

            if service:
                query = query.filter_by(service=service)
            if resource_name:
                query = query.filter_by(resource_name=resource_name)
            if operation:
                query = query.filter_by(operation=operation)

            # Get total count and paginated results
            total_items = query.count()
            permissions = query.offset(offset).limit(page_size).all()

        except ValueError as e:
            logger.warning(f"Invalid query parameters: {e}")
            return {
                "error": "invalid_parameter",
                "message": "Invalid query parameters",
            }, 400

        # Serialize permissions
        data = [perm.to_dict() for perm in permissions]

        # Calculate total pages
        total_pages = (
            (total_items + page_size - 1) // page_size if total_items > 0 else 0
        )

        # Build response with pagination metadata
        response = {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
            },
        }

        logger.info(
            f"Retrieved {len(data)} permissions (page {page}/{total_pages}, total: {total_items})"
        )
        return response, 200


class PermissionResource(Resource):
    """Resource for accessing individual Permission entities.

    Provides endpoint for:
    - Retrieving a single Permission by ID (GET)

    Permissions are read-only.
    """

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self, permission_id: str):
        """Retrieve a single Permission by its ID.

        Args:
            permission_id: UUID of the permission to retrieve

        Returns:
            tuple: JSON response with Permission data and HTTP 200, or error and HTTP 404/400.

        Example response:
            {
                "id": "uuid",
                "name": "storage:files:DELETE",
                "service": "storage",
                "resource_name": "files",
                "operation": "DELETE",
                "description": "Storage files resource - DELETE",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        """
        logger.info(f"Retrieving permission with ID: {permission_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(permission_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {permission_id}")
            return {
                "error": "bad_request",
                "message": "Invalid UUID format",
            }, 400

        permission = db.session.get(Permission, permission_id)

        if not permission:
            logger.warning(f"Permission not found: {permission_id}")
            return {
                "error": "not_found",
                "message": "Permission not found",
            }, 404

        logger.info(f"Permission retrieved: {permission.name}")
        return permission.to_dict(), 200


class PermissionsByServiceResource(Resource):
    """Resource for listing permissions grouped by service.

    Provides endpoint for:
    - Listing all permissions grouped by service name (GET)

    This is useful for building permission selection UIs.
    """

    @require_jwt_auth
    @access_required(Operation.LIST)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """Retrieve all permissions grouped by service.

        Returns:
            tuple: (dict, int). JSON response body with permissions grouped by service:
                Key: service name (e.g., "storage", "diagram")
                Value: list of Permission entities for that service

        Example response:
            {
                "storage": [
                    {
                        "id": "uuid",
                        "name": "storage:files:LIST",
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "LIST",
                        "description": "List files",
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00"
                    },
                    {
                        "id": "uuid",
                        "name": "storage:files:CREATE",
                        "service": "storage",
                        "resource_name": "files",
                        "operation": "CREATE",
                        "description": "Create/upload files",
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00"
                    }
                ],
                "diagram": [
                    {
                        "id": "uuid",
                        "name": "diagram:diagrams:CREATE",
                        "service": "diagram",
                        "resource_name": "diagrams",
                        "operation": "CREATE",
                        "description": "Create diagrams",
                        "created_at": "2025-01-01T00:00:00",
                        "updated_at": "2025-01-01T00:00:00"
                    }
                ]
            }
        """
        logger.info("Retrieving permissions grouped by service")

        # Get all permissions
        permissions = Permission.query.order_by(
            Permission.service, Permission.resource_name, Permission.operation
        ).all()

        # Group by service
        grouped: dict[str, list] = {}
        for permission in permissions:
            service = permission.service
            if service not in grouped:
                grouped[service] = []
            grouped[service].append(permission.to_dict())

        logger.info(
            f"Retrieved {len(permissions)} permissions across {len(grouped)} services"
        )
        return grouped, 200
