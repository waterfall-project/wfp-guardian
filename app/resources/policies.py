# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Policy REST API resources.

This module defines the Flask-RESTful resources for managing Policy entities.
Policies are company-scoped collections of permissions that can be attached to roles.
"""

from flask import current_app, request
from flask_restful import Resource
from marshmallow import ValidationError as MarshmallowValidationError

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy
from app.schemas.policy_schema import (
    PolicyCreateSchema,
    PolicySchema,
    PolicyUpdateSchema,
)
from app.utils.guardian import Operation, access_required
from app.utils.jwt_utils import get_company_id_from_jwt, require_jwt_auth
from app.utils.limiter import limiter
from app.utils.logger import logger

# Error message constants
ERROR_POLICY_NOT_FOUND = "Policy not found"
ERROR_INVALID_UUID_FORMAT = "Invalid UUID format"


class PolicyListResource(Resource):
    """Resource for listing and creating Policy entities.

    Provides endpoints for:
    - Listing all policies for a company with optional filtering (GET)
    - Creating a new policy (POST)

    All operations are scoped to the company_id from the JWT token.
    """

    @require_jwt_auth
    @access_required(Operation.LIST)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """Retrieve policies with optional filtering and pagination.

        Query Parameters:
            is_active (bool, optional): Filter by active status
            page (int, optional): Page number (1-indexed). Default: 1
            page_size (int, optional): Items per page. Default from config (PAGE_LIMIT),
                Max from config (MAX_PAGE_LIMIT)

        Returns:
            tuple: (dict, int). JSON response body with:
                - data (list): List of Policy entities for this page.
                - pagination (dict): Pagination metadata (page, page_size, total_items, total_pages)

        Example response:
            {
                "data": [
                    {
                        "id": "uuid",
                        "name": "file_management",
                        "display_name": "File Management",
                        "description": "Full permissions on files",
                        "company_id": "uuid",
                        "priority": 10,
                        "is_active": true,
                        "permissions_count": 5,
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
        logger.info("Retrieving policies")

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

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

            # Parse filter parameter
            is_active = request.args.get(
                "is_active", type=lambda v: v.lower() == "true"
            )

            # Get total count and paginated results
            total_items = Policy.count_by_company(company_id, is_active=is_active)
            policies = Policy.get_all(
                company_id=company_id,
                limit=page_size,
                offset=offset,
                is_active=is_active,
            )

        except ValueError as e:
            logger.warning(f"Invalid query parameters: {e}")
            return {
                "error": "invalid_parameter",
                "message": "Invalid query parameters",
            }, 400

        # Serialize policies
        schema = PolicySchema()
        data = [schema.dump(policy) for policy in policies]

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
            f"Retrieved {len(data)} policies (page {page}/{total_pages}, total: {total_items})"
        )
        return response, 200

    @require_jwt_auth
    @access_required(Operation.CREATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def post(self):
        """Create a new policy.

        Request Body (JSON):
            name (str, required): Technical name (lowercase, underscores).
            display_name (str, required): Human-readable display name.
            description (str, optional): Detailed description.
            priority (int, optional): Evaluation priority (default 0).

        Returns:
            tuple: JSON response with created Policy data and HTTP 201, or error.

        Errors:
            400: Invalid request data
            409: Policy with same name already exists
            422: Validation error
        """
        logger.info("Creating new policy")

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Validate and deserialize request
        schema = PolicyCreateSchema()
        try:
            data = schema.load(request.get_json())
        except MarshmallowValidationError as e:
            logger.warning(f"Policy validation failed: {e.messages}")
            return {"error": "validation_error", "message": e.messages}, 422

        # Check if policy name already exists for this company
        existing = Policy.get_by_name(data["name"], company_id)
        if existing:
            logger.warning(
                f"Policy name conflict: {data['name']} already exists for company {company_id}"
            )
            return {
                "error": "conflict",
                "message": f"Policy with name '{data['name']}' already exists",
            }, 409

        # Create policy
        policy = Policy(company_id=company_id, **data)
        db.session.add(policy)
        db.session.commit()

        logger.info(f"Policy created: {policy.name} (ID: {policy.id})")

        # Serialize and return
        result_schema = PolicySchema()
        return result_schema.dump(policy), 201

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def head(self):
        """Get total count of policies for pagination (HEAD request).

        Query Parameters:
            is_active (bool, optional): Filter by active status

        Returns:
            tuple: Empty response body with X-Total-Count header and HTTP 200.

        Headers:
            X-Total-Count: Total number of policies matching the filters.
        """
        logger.info("Retrieving policy count (HEAD)")

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Parse filter parameter
        is_active = request.args.get("is_active", type=lambda v: v.lower() == "true")

        # Get count
        total = Policy.count_by_company(company_id, is_active=is_active)

        logger.info(f"Policy count: {total}")
        return "", 200, {"X-Total-Count": str(total)}


class PolicyResource(Resource):
    """Resource for accessing individual Policy entities.

    Provides endpoints for:
    - Retrieving a single Policy by ID (GET)
    - Updating a Policy (PATCH)
    - Deleting a Policy (DELETE)

    All operations are scoped to the company_id from the JWT token.
    """

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self, policy_id: str):
        """Retrieve a single Policy by its ID.

        Args:
            policy_id: UUID of the policy to retrieve

        Returns:
            tuple: JSON response with Policy data and HTTP 200, or error and HTTP 404.
        """
        logger.info(f"Retrieving policy with ID: {policy_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(policy_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {policy_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Get policy (scoped to company)
        policy = Policy.get_by_id(policy_id, company_id)

        if not policy:
            logger.warning(f"Policy not found: {policy_id}")
            return {
                "error": "not_found",
                "message": ERROR_POLICY_NOT_FOUND,
            }, 404

        logger.info(f"Policy retrieved: {policy.name}")

        # Serialize and return
        schema = PolicySchema()
        return schema.dump(policy), 200

    @require_jwt_auth
    @access_required(Operation.UPDATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def patch(self, policy_id: str):
        """Update a policy (partial update).

        Args:
            policy_id: UUID of the policy to update

        Request Body (JSON):
            display_name (str, optional): Updated display name.
            description (str, optional): Updated description.
            priority (int, optional): Updated priority.
            is_active (bool, optional): Updated active status.

        Returns:
            tuple: JSON response with updated Policy data and HTTP 200, or error.

        Errors:
            404: Policy not found
            422: Validation error
        """
        logger.info(f"Updating policy with ID: {policy_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(policy_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {policy_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Get policy (scoped to company)
        policy = Policy.get_by_id(policy_id, company_id)

        if not policy:
            logger.warning(f"Policy not found: {policy_id}")
            return {
                "error": "not_found",
                "message": ERROR_POLICY_NOT_FOUND,
            }, 404

        # Validate and deserialize request
        schema = PolicyUpdateSchema()
        try:
            data = schema.load(request.get_json())
        except MarshmallowValidationError as e:
            logger.warning(f"Policy update validation failed: {e.messages}")
            return {"error": "validation_error", "message": e.messages}, 422

        # Update policy fields
        for key, value in data.items():
            setattr(policy, key, value)

        db.session.commit()

        logger.info(f"Policy updated: {policy.name}")

        # Serialize and return
        result_schema = PolicySchema()
        return result_schema.dump(policy), 200

    @require_jwt_auth
    @access_required(Operation.DELETE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def delete(self, policy_id: str):
        """Delete a policy.

        Args:
            policy_id: UUID of the policy to delete

        Returns:
            tuple: Empty response and HTTP 204, or error.

        Errors:
            404: Policy not found
            400: Cannot delete (policy still referenced by roles)

        Note:
            Recommendation is to disable (is_active=false) instead of deleting.
        """
        logger.info(f"Deleting policy with ID: {policy_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(policy_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {policy_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Get policy (scoped to company)
        policy = Policy.get_by_id(policy_id, company_id)

        if not policy:
            logger.warning(f"Policy not found: {policy_id}")
            return {
                "error": "not_found",
                "message": ERROR_POLICY_NOT_FOUND,
            }, 404

        # Check if policy is referenced by any roles before deletion
        if policy.roles:
            role_names = [role.name for role in policy.roles]
            logger.warning(
                f"Cannot delete policy {policy_id}: referenced by roles {role_names}"
            )
            return {
                "error": "conflict",
                "message": f"Cannot delete policy: attached to roles {', '.join(role_names)}",
            }, 409

        db.session.delete(policy)
        db.session.commit()

        logger.info(f"Policy deleted: {policy.name}")
        return "", 204


class PolicyPermissionListResource(Resource):
    """Resource for managing permissions attached to a policy.

    Provides endpoints for:
    - Listing all permissions attached to a policy (GET)
    - Attaching a permission to a policy (POST)
    """

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self, policy_id: str):
        """List all permissions attached to a policy.

        Args:
            policy_id: UUID of the policy

        Query Parameters:
            page (int, optional): Page number (1-indexed). Default: 1
            page_size (int, optional): Items per page. Default from config.

        Returns:
            tuple: JSON response with paginated permissions list and HTTP 200.
        """
        logger.info(f"Retrieving permissions for policy {policy_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(policy_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {policy_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Get policy (scoped to company)
        policy = Policy.get_by_id(policy_id, company_id)

        if not policy:
            logger.warning(f"Policy not found: {policy_id}")
            return {
                "error": "not_found",
                "message": ERROR_POLICY_NOT_FOUND,
            }, 404

        # Parse pagination parameters
        try:
            page = int(request.args.get("page", default=1))
            page_size = int(
                request.args.get("page_size", default=current_app.config["PAGE_LIMIT"])
            )
            max_page_size = current_app.config["MAX_PAGE_LIMIT"]

            if page < 1:
                return {
                    "error": "invalid_parameter",
                    "message": "Page must be >= 1",
                }, 400

            if page_size < 1 or page_size > max_page_size:
                return {
                    "error": "invalid_parameter",
                    "message": f"Page size must be between 1 and {max_page_size}",
                }, 400

            offset = (page - 1) * page_size

        except ValueError as e:
            logger.warning(f"Invalid pagination parameters: {e}")
            return {
                "error": "invalid_parameter",
                "message": "Invalid query parameters",
            }, 400

        # Get paginated permissions
        permissions = policy.permissions[offset : offset + page_size]
        total_items = len(policy.permissions)
        total_pages = (
            (total_items + page_size - 1) // page_size if total_items > 0 else 0
        )

        # Serialize permissions
        data = [perm.to_dict() for perm in permissions]

        response = {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
            },
        }

        logger.info(f"Retrieved {len(data)} permissions for policy {policy.name}")
        return response, 200

    @require_jwt_auth
    @access_required(Operation.UPDATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def post(self, policy_id: str):
        """Attach a permission to a policy.

        Args:
            policy_id: UUID of the policy

        Request Body (JSON):
            permission_id (str, required): UUID of the permission to attach

        Returns:
            tuple: Success message and HTTP 201, or error.

        Note:
            This operation is idempotent - attaching an already attached
            permission succeeds without error.
        """
        logger.info(f"Attaching permission to policy {policy_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(policy_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {policy_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Get policy (scoped to company)
        policy = Policy.get_by_id(policy_id, company_id)

        if not policy:
            logger.warning(f"Policy not found: {policy_id}")
            return {
                "error": "not_found",
                "message": ERROR_POLICY_NOT_FOUND,
            }, 404

        # Get permission_id from request
        data = request.get_json()
        if not data or "permission_id" not in data:
            return {
                "error": "bad_request",
                "message": "permission_id is required",
            }, 400

        permission_id = data["permission_id"]

        # Verify permission exists
        permission = db.session.get(Permission, permission_id)
        if not permission:
            logger.warning(f"Permission not found: {permission_id}")
            return {
                "error": "not_found",
                "message": "Permission not found",
            }, 404

        # Check if already attached
        if permission in policy.permissions:
            logger.warning(
                f"Permission {permission.name} already attached to policy {policy.name}"
            )
            return {
                "error": "conflict",
                "message": "Permission already attached to this policy",
            }, 409

        # Attach permission
        policy.attach_permission(permission_id)
        db.session.commit()

        logger.info(f"Permission {permission.name} attached to policy {policy.name}")
        return {"message": "Permission attached to policy successfully"}, 201


class PolicyPermissionResource(Resource):
    """Resource for removing a permission from a policy."""

    @require_jwt_auth
    @access_required(Operation.UPDATE)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def delete(self, policy_id: str, permission_id: str):
        """Remove a permission from a policy.

        Args:
            policy_id: UUID of the policy
            permission_id: UUID of the permission to remove

        Returns:
            tuple: Empty response and HTTP 204, or error.
        """
        logger.info(f"Removing permission {permission_id} from policy {policy_id}")

        # Validate UUID format
        try:
            from uuid import UUID

            UUID(policy_id)
            UUID(permission_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {policy_id} or {permission_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        # Extract company_id from JWT
        company_id = get_company_id_from_jwt()

        # Get policy (scoped to company)
        policy = Policy.get_by_id(policy_id, company_id)

        if not policy:
            logger.warning(f"Policy not found: {policy_id}")
            return {
                "error": "not_found",
                "message": ERROR_POLICY_NOT_FOUND,
            }, 404

        # Detach permission
        if not policy.detach_permission(permission_id):
            logger.warning(
                f"Permission {permission_id} not attached to policy {policy_id}"
            )
            return {
                "error": "not_found",
                "message": "Permission not attached to this policy",
            }, 404

        db.session.commit()

        logger.info(f"Permission {permission_id} removed from policy {policy.name}")
        return "", 204
