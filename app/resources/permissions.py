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
            resource_name (str, optional): Filter by resource name (requires service)
            limit (int, optional): Maximum number of records to return.
                Default from config (PAGE_LIMIT), Max from config (MAX_PAGE_LIMIT)
            offset (int, optional): Number of records to skip. Default: 0

        Returns:
            tuple: (dict, int). JSON response body with:
                - permissions (list): List of Permission entities for this page.
                - count (int): Number of permissions returned in this page.
                - total (int): Total number of matching permissions.

        Example response:
            {
                "permissions": [
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
                "count": 1,
                "total": 1
            }
        """
        logger.info("Retrieving permissions")

        # Parse pagination and filter parameters
        try:
            limit = int(
                request.args.get("limit", default=current_app.config["PAGE_LIMIT"])
            )
            offset = int(request.args.get("offset", default=0))
            max_limit = current_app.config["MAX_PAGE_LIMIT"]

            # Validate pagination parameters
            if limit < 1 or limit > max_limit:
                logger.warning(
                    f"Invalid limit parameter: {limit}. Must be between 1 and {max_limit}"
                )
                return {
                    "error": "invalid_parameter",
                    "message": f"Limit must be between 1 and {max_limit}",
                }, 400

            if offset < 0:
                logger.warning(f"Invalid offset parameter: {offset}. Must be >= 0")
                return {
                    "error": "invalid_parameter",
                    "message": "Offset must be >= 0",
                }, 400

            # Parse filter parameters
            service = request.args.get("service", type=str)
            resource_name = request.args.get("resource_name", type=str)

            # Build query based on filters and paginate at DB level
            if service and resource_name:
                # Filter by both service and resource_name, paginate at DB level
                query = Permission.query.filter_by(
                    service=service, resource_name=resource_name
                )
                total = query.count()
                permissions = query.offset(offset).limit(limit).all()
            elif service:
                # Filter by service only, paginate at DB level
                query = Permission.query.filter_by(service=service)
                total = query.count()
                permissions = query.offset(offset).limit(limit).all()
            else:
                # No filters: paginate at DB level and include total count
                permissions = Permission.get_all(limit=limit, offset=offset)
                total = Permission.query.count()

        except ValueError as e:
            logger.warning(f"Invalid query parameters: {e}")
            return {
                "error": "invalid_parameter",
                "message": "Invalid query parameters",
            }, 400

        # Serialize permissions
        result = [perm.to_dict() for perm in permissions]

        # Build response with pagination metadata
        response = {
            "permissions": result,
            "count": len(result),
            "total": total,
        }

        logger.info(f"Retrieved {len(result)} permissions (total: {total})")
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
            tuple: JSON response with Permission data and HTTP 200, or error and HTTP 404.

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

        permission = db.session.get(Permission, permission_id)

        if not permission:
            logger.warning(f"Permission not found: {permission_id}")
            return {
                "error": "not_found",
                "message": "Permission not found",
            }, 404

        logger.info(f"Permission retrieved: {permission.name}")
        return permission.to_dict(), 200
