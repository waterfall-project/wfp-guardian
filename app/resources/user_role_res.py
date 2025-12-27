"""User Role REST API resources.

Implements CRUD operations for user role assignments in the RBAC system.

Endpoints:
    GET    /users/{user_id}/roles          - List roles for a user
    POST   /users/{user_id}/roles          - Assign a role to a user
    GET    /users/{user_id}/roles/{id}     - Get specific role assignment
    PATCH  /users/{user_id}/roles/{id}     - Update role assignment
    DELETE /users/{user_id}/roles/{id}     - Remove role assignment
    GET    /roles/{role_id}/users          - List users with a role
"""

from datetime import UTC, datetime
from uuid import UUID

from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.db import db
from app.models.role import Role
from app.models.user_role import UserRole
from app.schemas.user_role_schema import (
    UserRoleCreateSchema,
    UserRoleSchema,
    UserRoleUpdateSchema,
)
from app.utils.jwt_utils import (
    get_company_id_from_jwt,
    get_user_id_from_jwt,
    require_jwt_auth,
)
from app.utils.logger import logger

# Error message constants
ERROR_COMPANY_ID_NOT_FOUND = "company_id not found in JWT"
ERROR_INVALID_UUID_FORMAT = "Invalid UUID format"
ERROR_INTERNAL_SERVER = "Internal server error"
ERROR_INVALID_UUID_REQUEST = "Invalid UUID in GET request"
ERROR_USER_ROLE_NOT_FOUND = "User role not found"


class UserRoleListResource(Resource):
    """List and create user role assignments."""

    @require_jwt_auth
    def head(self, user_id: str) -> tuple:
        """HEAD request to count user roles.

        Args:
            user_id: User UUID

        Returns:
            tuple: Empty response with X-Total-Count header
        """
        try:
            user_uuid = UUID(user_id)
            company_id = get_company_id_from_jwt()
            if not company_id:
                return {
                    "error": "unauthorized",
                    "message": ERROR_COMPANY_ID_NOT_FOUND,
                }, 401

            # Parse optional filters
            project_id_str = request.args.get("project_id")
            project_id = UUID(project_id_str) if project_id_str else None
            is_active_str = request.args.get("is_active")
            is_active: bool | None = None
            if is_active_str is not None:
                is_active = is_active_str.lower() == "true"

            # Get count
            count = UserRole.count_by_user(
                user_id=str(user_uuid),
                company_id=str(company_id),
                project_id=str(project_id) if project_id else None,
                is_active=is_active,
            )

            return "", 200, {"X-Total-Count": str(count)}

        except (ValueError, AttributeError) as e:
            logger.error("Invalid UUID in HEAD request", error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            logger.exception("Error in HEAD user roles", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500

    @require_jwt_auth
    def get(self, user_id: str) -> tuple:
        """List all roles assigned to a user.

        Args:
            user_id: User UUID

        Returns:
            tuple: (data dict, status code)
        """
        try:
            user_uuid = UUID(user_id)
            company_id = get_company_id_from_jwt()
            if not company_id:
                return {
                    "error": "unauthorized",
                    "message": ERROR_COMPANY_ID_NOT_FOUND,
                }, 401

            # Parse pagination
            page = request.args.get("page", 1, type=int)
            page_size = request.args.get("page_size", 50, type=int)
            page_size = min(page_size, 100)  # Max 100 items per page

            # Parse optional filters
            project_id_str = request.args.get("project_id")
            project_id = UUID(project_id_str) if project_id_str else None
            is_active_str = request.args.get("is_active")
            is_active: bool | None = None
            if is_active_str is not None:
                is_active = is_active_str.lower() == "true"

            # Calculate offset
            offset = (page - 1) * page_size

            # Get user roles
            user_roles = UserRole.get_all(
                user_id=str(user_uuid),
                company_id=str(company_id),
                limit=page_size,
                offset=offset,
                project_id=str(project_id) if project_id else None,
                is_active=is_active,
            )

            # Get total count
            total = UserRole.count_by_user(
                user_id=str(user_uuid),
                company_id=str(company_id),
                project_id=str(project_id) if project_id else None,
                is_active=is_active,
            )

            # Serialize
            schema = UserRoleSchema(many=True)
            data = schema.dump(user_roles)

            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total,
                    "total_pages": (total + page_size - 1) // page_size,
                },
            }, 200

        except (ValueError, AttributeError) as e:
            logger.error(ERROR_INVALID_UUID_REQUEST, error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            logger.exception("Error listing user roles", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500

    @require_jwt_auth
    def post(self, user_id: str) -> tuple:
        """Assign a role to a user.

        Args:
            user_id: User UUID

        Returns:
            tuple: (created user role, status code)
        """
        try:
            user_uuid = UUID(user_id)
            company_id = get_company_id_from_jwt()
            granted_by = get_user_id_from_jwt()

            if not company_id or not granted_by:
                return {
                    "error": "unauthorized",
                    "message": "company_id or user_id not found in JWT",
                }, 401

            # Parse and validate request
            schema = UserRoleCreateSchema()
            data = schema.load(request.get_json())

            # Verify role exists and belongs to company
            role = Role.get_by_id(UUID(data["role_id"]), UUID(company_id))
            if not role:
                return {
                    "error": "not_found",
                    "message": "Role not found or not accessible",
                }, 404

            # Check if user already has this active role assignment
            existing = UserRole.query.filter_by(
                user_id=str(user_uuid),
                role_id=data["role_id"],
                company_id=company_id,
                project_id=data.get("project_id"),
                is_active=True,
            ).first()

            if existing:
                logger.warning(
                    "Role already assigned to user",
                    user_id=str(user_uuid),
                    role_id=data["role_id"],
                )
                return {
                    "error": "conflict",
                    "message": "Role already assigned to this user",
                }, 409

            # Create user role assignment
            user_role = UserRole(
                user_id=str(user_uuid),
                role_id=data["role_id"],
                company_id=company_id,
                project_id=data.get("project_id"),
                scope_type=data.get("scope_type", "direct"),
                granted_by=granted_by,
                granted_at=datetime.now(UTC),
                expires_at=data.get("expires_at"),
                is_active=True,
            )

            db.session.add(user_role)
            db.session.commit()

            logger.info(
                "Role assigned to user",
                user_id=str(user_uuid),
                role_id=str(data["role_id"]),
                company_id=str(company_id),
                project_id=(
                    str(data.get("project_id")) if data.get("project_id") else None
                ),
            )

            # Serialize and return
            response_schema = UserRoleSchema()
            return response_schema.dump(user_role), 201

        except ValidationError as e:
            logger.warning("Validation error creating user role", errors=e.messages)
            return {
                "error": "validation_error",
                "message": "Validation failed",
                "details": e.messages,
            }, 422
        except IntegrityError as e:
            db.session.rollback()
            logger.warning("Integrity error creating user role", error=str(e))
            return {
                "error": "conflict",
                "message": "Role already assigned to this user",
            }, 409
        except (ValueError, AttributeError) as e:
            logger.error("Invalid UUID in POST request", error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            db.session.rollback()
            logger.exception("Error creating user role", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500


class UserRoleResource(Resource):
    """Get, update, and delete user role assignments."""

    @require_jwt_auth
    def get(self, user_id: str, user_role_id: str) -> tuple:
        """Get a specific user role assignment.

        Args:
            user_id: User UUID
            user_role_id: UserRole UUID

        Returns:
            tuple: (user role data, status code)
        """
        # Validate UUID format
        try:
            from uuid import UUID

            UUID(user_id)
            UUID(user_role_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {user_id} or {user_role_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        try:
            user_uuid = UUID(user_id)
            user_role_uuid = UUID(user_role_id)
            company_id = get_company_id_from_jwt()

            if not company_id:
                return {
                    "error": "unauthorized",
                    "message": ERROR_COMPANY_ID_NOT_FOUND,
                }, 401

            # Get user role
            user_role = UserRole.get_by_id(
                str(user_role_uuid), str(user_uuid), str(company_id)
            )
            if not user_role:
                return {"error": "not_found", "message": ERROR_USER_ROLE_NOT_FOUND}, 404

            # Serialize and return
            schema = UserRoleSchema()
            return schema.dump(user_role), 200

        except (ValueError, AttributeError) as e:
            logger.error(ERROR_INVALID_UUID_REQUEST, error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            logger.exception("Error getting user role", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500

    @require_jwt_auth
    def patch(self, user_id: str, user_role_id: str) -> tuple:
        """Update a user role assignment.

        Can update: project_id, scope_type, expires_at, is_active
        Cannot update: user_id, role_id, company_id

        Args:
            user_id: User UUID
            user_role_id: UserRole UUID

        Returns:
            tuple: (updated user role, status code)
        """
        # Validate UUID format
        try:
            from uuid import UUID

            UUID(user_id)
            UUID(user_role_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {user_id} or {user_role_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        try:
            user_uuid = UUID(user_id)
            user_role_uuid = UUID(user_role_id)
            company_id = get_company_id_from_jwt()

            if not company_id:
                return {
                    "error": "unauthorized",
                    "message": ERROR_COMPANY_ID_NOT_FOUND,
                }, 401

            # Get user role
            user_role = UserRole.get_by_id(
                str(user_role_uuid), str(user_uuid), str(company_id)
            )
            if not user_role:
                return {"error": "not_found", "message": ERROR_USER_ROLE_NOT_FOUND}, 404

            # Parse and validate request
            schema = UserRoleUpdateSchema()
            data = schema.load(request.get_json())

            # Update fields
            if "project_id" in data:
                user_role.project_id = data["project_id"]
            if "scope_type" in data:
                user_role.scope_type = data["scope_type"]
            if "expires_at" in data:
                user_role.expires_at = data["expires_at"]
            if "is_active" in data:
                user_role.is_active = data["is_active"]

            user_role.updated_at = datetime.now(UTC)

            db.session.commit()

            logger.info(
                "User role updated",
                user_role_id=str(user_role_uuid),
                user_id=str(user_uuid),
                company_id=str(company_id),
            )

            # Serialize and return
            response_schema = UserRoleSchema()
            return response_schema.dump(user_role), 200

        except ValidationError as e:
            logger.warning("Validation error updating user role", errors=e.messages)
            return {
                "error": "validation_error",
                "message": "Validation failed",
                "details": e.messages,
            }, 422
        except IntegrityError as e:
            db.session.rollback()
            logger.warning("Integrity error updating user role", error=str(e))
            return {
                "error": "conflict",
                "message": "Update would violate unique constraint",
            }, 409
        except (ValueError, AttributeError) as e:
            logger.error("Invalid UUID in PATCH request", error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            db.session.rollback()
            logger.exception("Error updating user role", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500

    @require_jwt_auth
    def delete(self, user_id: str, user_role_id: str) -> tuple:
        """Delete a user role assignment.

        Recommendation: Use PATCH with is_active=false instead to preserve history.

        Args:
            user_id: User UUID
            user_role_id: UserRole UUID

        Returns:
            tuple: (empty dict, status code)
        """
        # Validate UUID format
        try:
            from uuid import UUID

            UUID(user_id)
            UUID(user_role_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {user_id} or {user_role_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        try:
            user_uuid = UUID(user_id)
            user_role_uuid = UUID(user_role_id)
            company_id = get_company_id_from_jwt()

            if not company_id:
                return {
                    "error": "unauthorized",
                    "message": ERROR_COMPANY_ID_NOT_FOUND,
                }, 401

            # Get user role
            user_role = UserRole.get_by_id(
                str(user_role_uuid), str(user_uuid), str(company_id)
            )
            if not user_role:
                return {"error": "not_found", "message": ERROR_USER_ROLE_NOT_FOUND}, 404

            # Delete
            db.session.delete(user_role)
            db.session.commit()

            logger.info(
                "User role deleted",
                user_role_id=str(user_role_uuid),
                user_id=str(user_uuid),
                company_id=str(company_id),
            )

            return "", 204

        except (ValueError, AttributeError) as e:
            logger.error("Invalid UUID in DELETE request", error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            db.session.rollback()
            logger.exception("Error deleting user role", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500


class RoleUsersResource(Resource):
    """List users with a specific role."""

    @require_jwt_auth
    def get(self, role_id: str) -> tuple:
        """List all users assigned to a role.

        Args:
            role_id: Role UUID

        Returns:
            tuple: (data dict, status code)
        """
        # Validate UUID format
        try:
            from uuid import UUID

            UUID(role_id)
        except (ValueError, AttributeError):
            logger.warning(f"Invalid UUID format: {role_id}")
            return {
                "error": "bad_request",
                "message": ERROR_INVALID_UUID_FORMAT,
            }, 400

        try:
            role_uuid = UUID(role_id)
            company_id = get_company_id_from_jwt()

            if not company_id:
                return {
                    "error": "unauthorized",
                    "message": ERROR_COMPANY_ID_NOT_FOUND,
                }, 401

            # Verify role exists
            role = Role.get_by_id(role_uuid, UUID(company_id))
            if not role:
                return {
                    "error": "not_found",
                    "message": "Role not found or not accessible",
                }, 404

            # Parse pagination
            page = request.args.get("page", 1, type=int)
            page_size = request.args.get("page_size", 50, type=int)
            page_size = min(page_size, 100)

            # Parse optional filters
            is_active_str = request.args.get("is_active")
            is_active: bool | None = None
            if is_active_str is not None:
                is_active = is_active_str.lower() == "true"

            # Calculate offset
            offset = (page - 1) * page_size

            # Get user roles
            user_roles = UserRole.get_users_by_role(
                role_id=str(role_uuid),
                company_id=str(company_id),
                limit=page_size,
                offset=offset,
                is_active=is_active,
            )

            # Get total count
            total = UserRole.count_users_by_role(
                role_id=str(role_uuid),
                company_id=str(company_id),
                is_active=is_active,
            )

            # Serialize
            schema = UserRoleSchema(many=True)
            data = schema.dump(user_roles)

            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_items": total,
                    "total_pages": (total + page_size - 1) // page_size,
                },
            }, 200

        except (ValueError, AttributeError) as e:
            logger.error(ERROR_INVALID_UUID_REQUEST, error=str(e))
            return {"error": "bad_request", "message": ERROR_INVALID_UUID_FORMAT}, 400
        except Exception as e:
            logger.exception("Error listing users with role", error=str(e))
            return {"error": "internal_error", "message": ERROR_INTERNAL_SERVER}, 500
