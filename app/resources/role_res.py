# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""REST API resources for Role management.

This module provides RESTful endpoints for Role CRUD operations and
policy attachment/detachment.
"""

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.constants import MAX_PAGE_LIMIT
from app.models.db import db
from app.models.policy import Policy
from app.models.role import Role
from app.schemas.role_schema import RoleCreateSchema, RoleSchema, RoleUpdateSchema
from app.utils.jwt_utils import require_jwt_auth


class RoleListResource(Resource):
    """Resource for listing and creating roles."""

    @require_jwt_auth
    def head(self):
        """Get role count for pagination.

        Returns:
            Response with X-Total-Count header.
        """
        company_id = g.user_context.get("company_id")
        is_active = request.args.get("is_active", type=lambda v: v.lower() == "true")

        total_count = Role.count_by_company(company_id=company_id, is_active=is_active)

        return "", 200, {"X-Total-Count": str(total_count)}

    @require_jwt_auth
    def get(self):
        """List all roles for the company.

        Query Parameters:
            page (int): Page number (default: 1)
            page_size (int): Items per page (default: 50, max: 100)
            is_active (bool): Filter by active status

        Returns:
            JSON response with paginated role list.
        """
        company_id = g.user_context.get("company_id")
        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("page_size", 50, type=int), MAX_PAGE_LIMIT)
        is_active = request.args.get("is_active", type=lambda v: v.lower() == "true")

        offset = (page - 1) * page_size
        roles = Role.get_all(
            company_id=company_id,
            limit=page_size,
            offset=offset,
            is_active=is_active,
        )

        total_count = Role.count_by_company(company_id=company_id, is_active=is_active)

        schema = RoleSchema(many=True)
        return {
            "data": schema.dump(roles),
            "page": page,
            "page_size": page_size,
            "total": total_count,
        }, 200

    @require_jwt_auth
    def post(self):
        """Create a new role.

        Request Body:
            RoleCreateSchema: name, display_name, description

        Returns:
            JSON response with created role (201) or error.
        """
        company_id = g.user_context.get("company_id")
        schema = RoleCreateSchema()

        try:
            data = schema.load(request.json)
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 422

        # Check name uniqueness
        existing = Role.get_by_name(name=data["name"], company_id=company_id)
        if existing:
            return {
                "error": "Conflict",
                "message": f"Role with name '{data['name']}' already exists for this company",
            }, 409

        # Create role
        role = Role(
            name=data["name"],
            display_name=data["display_name"],
            description=data.get("description"),
            company_id=company_id,
            is_active=True,
        )

        try:
            db.session.add(role)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "Database error",
                "message": "Failed to create role",
            }, 500

        return RoleSchema().dump(role), 201


class RoleResource(Resource):
    """Resource for individual role operations."""

    @require_jwt_auth
    def get(self, role_id):
        """Get a role by ID.

        Args:
            role_id: UUID of the role.

        Returns:
            JSON response with role details or 404.
        """
        company_id = g.user_context.get("company_id")
        role = Role.get_by_id(role_id=role_id, company_id=company_id)

        if not role:
            return {"error": "Not found", "message": "Role not found"}, 404

        return RoleSchema().dump(role), 200

    @require_jwt_auth
    def patch(self, role_id):
        """Update a role.

        Args:
            role_id: UUID of the role.

        Request Body:
            RoleUpdateSchema: display_name, description, is_active

        Returns:
            JSON response with updated role or error.
        """
        company_id = g.user_context.get("company_id")
        role = Role.get_by_id(role_id=role_id, company_id=company_id)

        if not role:
            return {"error": "Not found", "message": "Role not found"}, 404

        schema = RoleUpdateSchema()
        try:
            data = schema.load(request.json)
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 422

        # Update fields if provided
        if "display_name" in data:
            role.display_name = data["display_name"]
        if "description" in data:
            role.description = data["description"]
        if "is_active" in data:
            role.is_active = data["is_active"]

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "Database error",
                "message": "Failed to update role",
            }, 500

        return RoleSchema().dump(role), 200

    @require_jwt_auth
    def delete(self, role_id):
        """Delete a role.

        Args:
            role_id: UUID of the role.

        Returns:
            204 on success, 404 if not found, 400 if has dependencies.
        """
        company_id = g.user_context.get("company_id")
        role = Role.get_by_id(role_id=role_id, company_id=company_id)

        if not role:
            return {"error": "Not found", "message": "Role not found"}, 404

        # In a real system, check for UserRole associations
        # For now, we'll just delete the role

        try:
            db.session.delete(role)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "Bad request",
                "message": "Cannot delete role with assigned users. Disable it instead.",
            }, 400

        return "", 204


class RolePoliciesResource(Resource):
    """Resource for managing role-policy relationships."""

    @require_jwt_auth
    def get(self, role_id):
        """List all policies attached to a role.

        Args:
            role_id: UUID of the role.

        Query Parameters:
            page (int): Page number (default: 1)
            page_size (int): Items per page (default: 50, max: 100)

        Returns:
            JSON response with paginated policy list.
        """
        company_id = g.user_context.get("company_id")
        role = Role.get_by_id(role_id=role_id, company_id=company_id)

        if not role:
            return {"error": "Not found", "message": "Role not found"}, 404

        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("page_size", 50, type=int), MAX_PAGE_LIMIT)

        # Get policies with pagination
        offset = (page - 1) * page_size
        policies = role.policies[offset : offset + page_size]
        total_count = len(role.policies)

        from app.schemas.policy_schema import PolicySchema

        schema = PolicySchema(many=True)
        return {
            "data": schema.dump(policies),
            "page": page,
            "page_size": page_size,
            "total": total_count,
        }, 200

    @require_jwt_auth
    def post(self, role_id):
        """Attach a policy to a role.

        Args:
            role_id: UUID of the role.

        Request Body:
            policy_id (str): UUID of policy to attach

        Returns:
            201 on success, 404 if not found.
        """
        company_id = g.user_context.get("company_id")
        role = Role.get_by_id(role_id=role_id, company_id=company_id)

        if not role:
            return {"error": "Not found", "message": "Role not found"}, 404

        data = request.json
        if not data or "policy_id" not in data:
            return {
                "error": "Bad request",
                "message": "policy_id is required",
            }, 400

        policy_id = data["policy_id"]
        policy = Policy.get_by_id(policy_id=policy_id, company_id=company_id)

        if not policy:
            return {"error": "Not found", "message": "Policy not found"}, 404

        # Attach policy (idempotent)
        role.attach_policy(policy_id)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "Database error",
                "message": "Failed to attach policy",
            }, 500

        return {"message": "Policy attached successfully"}, 201


class RolePolicyResource(Resource):
    """Resource for detaching a specific policy from a role."""

    @require_jwt_auth
    def delete(self, role_id, policy_id):
        """Detach a policy from a role.

        Args:
            role_id: UUID of the role.
            policy_id: UUID of the policy.

        Returns:
            204 on success, 404 if not found.
        """
        company_id = g.user_context.get("company_id")
        role = Role.get_by_id(role_id=role_id, company_id=company_id)

        if not role:
            return {"error": "Not found", "message": "Role not found"}, 404

        # Detach policy
        detached = role.detach_policy(policy_id)

        if not detached:
            return {
                "error": "Not found",
                "message": "Policy not attached to this role",
            }, 404

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "error": "Database error",
                "message": "Failed to detach policy",
            }, 500

        return "", 204
