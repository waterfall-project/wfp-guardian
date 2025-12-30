# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""REST API resources for access log audit endpoints.

Implements the audit API endpoints per OpenAPI specification:
- HEAD /access-logs - Count only
- GET /access-logs - List with filters
- DELETE /access-logs - Purge old logs (GDPR)
- GET /access-logs/{log_id} - Get specific log
- GET /access-logs/statistics - Aggregated stats
"""

from datetime import datetime

from flask import g, request
from flask_restful import Resource
from marshmallow import ValidationError

from app.schemas.audit_schema import (
    AccessLogQuerySchema,
    AccessLogSchema,
    AccessLogStatisticsSchema,
    PurgeLogsSchema,
)
from app.services.audit_service import AuditService
from app.utils.jwt_utils import require_jwt_auth
from app.utils.limiter import limiter
from app.utils.logger import logger

BAD_REQUEST_ERROR = "Bad request"


class AccessLogsResource(Resource):
    """Resource for listing and querying access logs.

    Implements HEAD, GET, and DELETE methods per OpenAPI spec.
    """

    @require_jwt_auth
    @limiter.limit("100 per minute")
    def head(self):
        """Get total count of access logs (HEAD request).

        Returns only headers with X-Total-Count for efficient pagination.

        Returns:
            tuple: (None, 200, headers) with X-Total-Count header
        """
        user_context = g.user_context
        company_id = user_context.get("company_id")

        # Parse query parameters
        schema = AccessLogQuerySchema()
        try:
            filters = schema.load(request.args)
        except ValidationError as err:
            return {"error": "Validation error", "details": err.messages}, 422

        # Override company_id from JWT (unless super-admin)
        # For now, always use JWT company_id
        filters["company_id"] = company_id

        # Get count only
        service = AuditService()
        _, total_count = service.get_logs(
            **{k: v for k, v in filters.items() if k not in ["page", "page_size"]},
            page=1,
            page_size=1,
        )

        return None, 200, {"X-Total-Count": str(total_count)}

    @require_jwt_auth
    @limiter.limit("100 per minute")
    def get(self):
        """List access logs with filtering and pagination.

        Query parameters:
            - user_id, company_id, project_id (UUIDs)
            - service, resource_name, operation (strings)
            - is_granted (boolean)
            - from_date, to_date (ISO datetime)
            - page, page_size (pagination)

        Returns:
            tuple: (dict, int) JSON response with paginated logs
        """
        user_context = g.user_context
        company_id = user_context.get("company_id")

        # Parse and validate query parameters
        schema = AccessLogQuerySchema()
        try:
            filters = schema.load(request.args)
        except ValidationError as err:
            logger.warning(f"Access logs query validation failed: {err.messages}")
            return {"error": "Validation error", "details": err.messages}, 422

        # Override company_id from JWT (security: users can only see their company's logs)
        filters["company_id"] = company_id

        # Query logs
        service = AuditService()
        try:
            logs, total_count = service.get_logs(**filters)

            # Serialize response
            log_schema = AccessLogSchema(many=True)
            logs_data = log_schema.dump(logs)

            # Build paginated response
            page = filters.get("page", 1)
            page_size = filters.get("page_size", 50)
            total_pages = (total_count + page_size - 1) // page_size

            return {
                "data": logs_data,
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "total_pages": total_pages,
            }, 200

        except Exception as e:
            logger.error(f"Failed to query access logs: {e}", exc_info=True)
            return {
                "error": "Internal server error",
                "message": "Failed to retrieve access logs",
            }, 500

    @require_jwt_auth
    @limiter.limit("10 per hour")
    def delete(self):
        """Purge old access logs (GDPR compliance).

        Query parameters:
            - before (required): Delete logs older than this date
            - company_id (optional): Limit to specific company

        Returns:
            tuple: (dict, int) JSON response with deleted count
        """
        user_context = g.user_context
        company_id = user_context.get("company_id")

        # Parse and validate parameters
        schema = PurgeLogsSchema()
        try:
            data = schema.load(request.args)
        except ValidationError as err:
            logger.warning(f"Purge logs validation failed: {err.messages}")
            return {"error": "Validation error", "details": err.messages}, 422

        before_date = data["before"]
        target_company_id = data.get("company_id")

        # Security: override company_id from JWT (unless super-admin)
        # For now, always use JWT company_id
        if target_company_id and target_company_id != company_id:
            logger.warning(
                f"User {user_context.get('user_id')} attempted to purge logs for different company"
            )
            return {
                "error": "Forbidden",
                "message": "Cannot purge logs for other companies",
            }, 403

        # Purge logs
        service = AuditService()
        try:
            deleted_count = service.purge_old_logs(before_date, company_id)

            return {
                "deleted_count": deleted_count,
                "before_date": before_date.isoformat(),
            }, 200

        except ValueError as e:
            logger.warning(f"Invalid purge request: {e}")
            return {"error": BAD_REQUEST_ERROR, "message": str(e)}, 400
        except Exception as e:
            logger.error(f"Failed to purge access logs: {e}", exc_info=True)
            return {
                "error": "Internal server error",
                "message": "Failed to purge access logs",
            }, 500


class AccessLogResource(Resource):
    """Resource for getting a specific access log by ID."""

    @require_jwt_auth
    @limiter.limit("100 per minute")
    def get(self, log_id: str):
        """Get a specific access log by ID.

        Args:
            log_id: UUID of the log entry

        Returns:
            tuple: (dict, int) JSON response with log details
        """
        user_context = g.user_context
        company_id = user_context.get("company_id")

        # Validate UUID format
        try:
            from uuid import UUID

            log_uuid = UUID(log_id)
        except ValueError:
            return {
                "error": BAD_REQUEST_ERROR,
                "message": "Invalid log_id format (must be UUID)",
            }, 400

        # Get log
        service = AuditService()
        log = service.get_log_by_id(log_uuid)

        if not log:
            return {"error": "Not found", "message": "Access log not found"}, 404

        # Security: ensure log belongs to user's company
        if str(log.company_id) != company_id:
            logger.warning(
                f"User {user_context.get('user_id')} attempted to access log from different company"
            )
            return {"error": "Not found", "message": "Access log not found"}, 404

        # Serialize and return
        schema = AccessLogSchema()
        return schema.dump(log), 200


class AccessLogsStatisticsResource(Resource):
    """Resource for aggregated audit statistics."""

    @require_jwt_auth
    @limiter.limit("60 per minute")
    def get(self):
        """Get aggregated audit statistics.

        Query parameters:
            - from_date, to_date (ISO datetime)
            - company_id, project_id (UUIDs)

        Returns:
            tuple: (dict, int) JSON response with statistics
        """
        user_context = g.user_context
        company_id = user_context.get("company_id")

        # Parse query parameters
        from_date_str = request.args.get("from_date")
        to_date_str = request.args.get("to_date")
        project_id_str = request.args.get("project_id")

        # Parse dates
        try:
            from_date = (
                datetime.fromisoformat(from_date_str.replace("Z", "+00:00"))
                if from_date_str
                else None
            )
            to_date = (
                datetime.fromisoformat(to_date_str.replace("Z", "+00:00"))
                if to_date_str
                else None
            )
        except ValueError as e:
            return {
                "error": BAD_REQUEST_ERROR,
                "message": f"Invalid date format: {e}",
            }, 400

        # Parse project_id
        try:
            from uuid import UUID

            project_id = UUID(project_id_str) if project_id_str else None
        except ValueError:
            return {
                "error": BAD_REQUEST_ERROR,
                "message": "Invalid project_id format (must be UUID)",
            }, 400

        # Get statistics
        service = AuditService()
        try:
            from uuid import UUID

            stats = service.get_statistics(
                company_id=UUID(company_id),
                project_id=project_id,
                from_date=from_date,
                to_date=to_date,
            )

            # Serialize and return
            schema = AccessLogStatisticsSchema()
            return schema.dump(stats), 200

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            return {
                "error": "Internal server error",
                "message": "Failed to retrieve statistics",
            }, 500
