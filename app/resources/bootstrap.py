# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Bootstrap REST API resources.

This module defines the Flask-RESTful resources for RBAC initialization
during system bootstrap and new company creation.
"""

from typing import Any

from flask import current_app, request
from flask_restful import Resource
from marshmallow import ValidationError

from app.schemas.bootstrap_schema import (
    BootstrapRequestSchema,
    BootstrapResponseSchema,
    InitRolesResponseSchema,
)
from app.services.bootstrap_service import BootstrapService
from app.utils.limiter import limiter
from app.utils.logger import logger

BAD_REQUEST_ERROR = "Bad request"


class BootstrapResource(Resource):
    """Resource for system RBAC initialization.

    Service-to-service endpoint called by Identity during the first
    company creation to initialize Guardian RBAC.

    Security:
        - Requires X-Internal-Token header
        - No JWT authentication (service-to-service)
    """

    @limiter.limit("10 per minute")
    def post(self):
        """Initialize RBAC for the first company.

        This endpoint:
        1. Validates X-Internal-Token header
        2. Creates 4 standard roles for the company
        3. Creates 4 standard policies with permissions
        4. Assigns company_admin role to the first user

        Request Headers:
            X-Internal-Token (str, required): Internal service authentication token

        Request Body:
            company_id (UUID, required): UUID of the first company
            user_id (UUID, required): UUID of the first user (admin)

        Returns:
            tuple: (dict, int). JSON response with:
                - success (bool): Initialization success
                - company_id (str): Company UUID
                - user_id (str): User UUID
                - roles_created (int): Number of roles created (4)
                - policies_created (int): Number of policies created (4)
                - permissions_assigned (int): Total permissions assigned
                - message (str): Success message

            Status codes:
                - 201: Created successfully
                - 400: Invalid request body
                - 401: Missing or invalid X-Internal-Token
                - 409: Company already initialized
                - 422: Validation error
                - 500: Internal server error

        Example request:
            POST /v0/bootstrap
            Headers:
                X-Internal-Token: your-internal-token
            Body:
                {
                    "company_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "user_id": "f1e2d3c4-b5a6-9807-dcba-fe0987654321"
                }

        Example response (201):
            {
                "success": true,
                "company_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "user_id": "f1e2d3c4-b5a6-9807-dcba-fe0987654321",
                "roles_created": 4,
                "policies_created": 4,
                "permissions_assigned": 47,
                "message": "Guardian RBAC initialized successfully for first company"
            }
        """
        logger.info("Received bootstrap request")

        # 1. Validate X-Internal-Token
        internal_token = request.headers.get("X-Internal-Token")
        expected_token = current_app.config.get("INTERNAL_SERVICE_TOKEN")

        if not expected_token:
            logger.error("INTERNAL_SERVICE_TOKEN not configured")
            return {"error": "Internal service authentication not configured"}, 500

        if not internal_token or internal_token != expected_token:
            logger.warning("Invalid or missing X-Internal-Token")
            return {
                "error": "Unauthorized",
                "message": "Invalid or missing X-Internal-Token header",
            }, 401

        # 2. Validate request body
        schema = BootstrapRequestSchema()
        try:
            json_data = request.get_json()
            if json_data is None:
                return {
                    "error": BAD_REQUEST_ERROR,
                    "message": "Request body must be JSON",
                }, 400
            if not isinstance(json_data, dict):
                return {
                    "error": BAD_REQUEST_ERROR,
                    "message": "Request body must be a JSON object",
                }, 400
            loaded_data = schema.load(json_data)
            if not isinstance(loaded_data, dict):
                return {
                    "error": BAD_REQUEST_ERROR,
                    "message": "Invalid request data",
                }, 400
            data: dict[str, Any] = loaded_data
        except ValidationError as err:
            logger.warning(f"Bootstrap request validation failed: {err.messages}")
            return {"error": "Validation error", "details": err.messages}, 422

        # 3. Execute bootstrap
        try:
            bootstrap_service = BootstrapService()
            result = bootstrap_service.bootstrap_system(
                company_id=data["company_id"], user_id=data["user_id"]
            )

            # 4. Serialize response
            response_schema = BootstrapResponseSchema()
            return response_schema.dump(result), 201

        except ValueError as e:
            logger.warning(f"Bootstrap validation error: {e}")
            return {"error": "Conflict", "message": str(e)}, 409
        except Exception as e:
            logger.error(f"Bootstrap failed: {e}", exc_info=True)
            return {
                "error": "Internal server error",
                "message": "Failed to initialize RBAC",
            }, 500


class InitCompanyRolesResource(Resource):
    """Resource for initializing roles for new companies.

    Service-to-service endpoint called by Identity when creating
    new companies (after the first one).

    Security:
        - Requires X-Internal-Token header
        - No JWT authentication (service-to-service)
    """

    @limiter.limit("10 per minute")
    def post(self, company_id: str):
        """Initialize standard roles for a new company.

        Creates 4 standard roles and policies without assigning users.

        Path Parameters:
            company_id (str): UUID of the newly created company

        Request Headers:
            X-Internal-Token (str, required): Internal service authentication token

        Returns:
            tuple: (dict, int). JSON response with:
                - success (bool): Initialization success
                - company_id (str): Company UUID
                - roles_created (int): Number of roles created (4)
                - policies_created (int): Number of policies created (4)
                - roles (list[str]): List of role names created

            Status codes:
                - 200: Created successfully
                - 400: Invalid company_id format
                - 401: Missing or invalid X-Internal-Token
                - 409: Company already has roles
                - 500: Internal server error

        Example request:
            POST /v0/companies/b2c3d4e5-f6a7-8901-bcde-f23456789012/init-roles
            Headers:
                X-Internal-Token: your-internal-token

        Example response (200):
            {
                "success": true,
                "company_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
                "roles_created": 4,
                "policies_created": 4,
                "roles": ["company_admin", "project_manager", "member", "viewer"]
            }
        """
        logger.info(f"Received init-roles request for company_id={company_id}")

        # 1. Validate X-Internal-Token
        internal_token = request.headers.get("X-Internal-Token")
        expected_token = current_app.config.get("INTERNAL_SERVICE_TOKEN")

        if not expected_token:
            logger.error("INTERNAL_SERVICE_TOKEN not configured")
            return {"error": "Internal service authentication not configured"}, 500

        if not internal_token or internal_token != expected_token:
            logger.warning("Invalid or missing X-Internal-Token")
            return {
                "error": "Unauthorized",
                "message": "Invalid or missing X-Internal-Token header",
            }, 401

        # 2. Validate company_id format
        try:
            from uuid import UUID

            company_uuid = UUID(company_id)
        except ValueError:
            logger.warning(f"Invalid company_id format: {company_id}")
            return {
                "error": BAD_REQUEST_ERROR,
                "message": "Invalid company_id format (must be UUID)",
            }, 400

        # 3. Execute role initialization
        try:
            bootstrap_service = BootstrapService()
            result = bootstrap_service.init_company_roles(company_id=company_uuid)

            # 4. Serialize response
            response_schema = InitRolesResponseSchema()
            return response_schema.dump(result), 200

        except ValueError as e:
            logger.warning(f"Init roles validation error: {e}")
            return {"error": "Conflict", "message": str(e)}, 409
        except Exception as e:
            logger.error(f"Init roles failed: {e}", exc_info=True)
            return {
                "error": "Internal server error",
                "message": "Failed to initialize roles",
            }, 500
