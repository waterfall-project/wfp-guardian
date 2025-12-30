# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for access log audit endpoints."""

from marshmallow import Schema, ValidationError, fields, validates


class AccessLogSchema(Schema):
    """Schema for AccessLog model per OpenAPI specification."""

    # Required fields
    id = fields.UUID(dump_only=True)
    user_id = fields.UUID(required=True)
    company_id = fields.UUID(required=True)
    service = fields.Str(required=True)
    resource_name = fields.Str(required=True)
    operation = fields.Str(required=True)
    access_granted = fields.Boolean(required=True)
    created_at = fields.DateTime(dump_only=True)

    # Optional fields
    project_id = fields.UUID(allow_none=True)
    resource_id = fields.Str(allow_none=True)
    reason = fields.Str(allow_none=True)
    ip_address = fields.Str(allow_none=True)
    user_agent = fields.Str(allow_none=True)
    context = fields.Dict(allow_none=True)

    @validates("operation")
    def validate_operation(self, value):
        """Validate operation is one of the allowed values."""
        valid_operations = [
            "LIST",
            "CREATE",
            "READ",
            "UPDATE",
            "DELETE",
            "APPROVE",
            "EXPORT",
            "IMPORT",
        ]
        if value not in valid_operations:
            raise ValidationError(
                f"Operation must be one of: {', '.join(valid_operations)}"
            )

    @validates("reason")
    def validate_reason(self, value):
        """Validate reason is one of the allowed values."""
        if value is None:
            return

        valid_reasons = [
            "granted",
            "no_permission",
            "no_matching_role",
            "role_expired",
            "role_inactive",
            "project_mismatch",
            "company_mismatch",
        ]
        if value not in valid_reasons:
            raise ValidationError(f"Reason must be one of: {', '.join(valid_reasons)}")


class AccessLogQuerySchema(Schema):
    """Schema for query parameters when listing access logs."""

    user_id = fields.UUID()
    company_id = fields.UUID()
    project_id = fields.UUID()
    service = fields.Str()
    resource_name = fields.Str()
    operation = fields.Str()
    is_granted = fields.Boolean()
    from_date = fields.DateTime()
    to_date = fields.DateTime()
    page = fields.Int(load_default=1)
    page_size = fields.Int(load_default=50)


class AccessLogStatisticsSchema(Schema):
    """Schema for audit statistics response."""

    total_requests = fields.Int()
    granted_requests = fields.Int()
    denied_requests = fields.Int()
    success_rate = fields.Float()
    by_service = fields.List(fields.Dict())
    by_operation = fields.List(fields.Dict())
    top_users = fields.List(fields.Dict())


class PurgeLogsSchema(Schema):
    """Schema for purge logs request parameters."""

    before = fields.DateTime(required=True)
    company_id = fields.UUID()
