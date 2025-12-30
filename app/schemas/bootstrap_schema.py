# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for Bootstrap operations.

This module defines schemas for system RBAC initialization during
the first company creation and for initializing roles for new companies.
"""

from marshmallow import Schema, fields, validate


class BootstrapRequestSchema(Schema):
    """Schema for validating bootstrap initialization request.

    Used by Identity service to initialize RBAC for the first company
    and assign company_admin role to the first user.

    Attributes:
        company_id: UUID of the first company created by Identity.
        user_id: UUID of the first user (admin) created by Identity.
    """

    company_id = fields.UUID(
        required=True,
        error_messages={"required": "company_id is required"},
    )
    user_id = fields.UUID(
        required=True,
        error_messages={"required": "user_id is required"},
    )


class BootstrapResponseSchema(Schema):
    """Schema for bootstrap initialization response.

    Returns information about created roles, policies, and permissions.

    Attributes:
        success: Whether initialization was successful.
        company_id: UUID of the company.
        user_id: UUID of the user assigned company_admin.
        roles_created: Number of roles created (expected: 4).
        policies_created: Number of policies created (expected: 4).
        permissions_assigned: Total number of permissions assigned to policies.
        message: Success message.
    """

    success = fields.Boolean(required=True)
    company_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    roles_created = fields.Integer(
        required=True,
        validate=validate.Range(min=0),
    )
    policies_created = fields.Integer(
        required=True,
        validate=validate.Range(min=0),
    )
    permissions_assigned = fields.Integer(
        required=True,
        validate=validate.Range(min=0),
    )
    message = fields.String(required=True)


class InitRolesResponseSchema(Schema):
    """Schema for company role initialization response.

    Used when creating standard roles/policies for a new company
    (without user assignment).

    Attributes:
        success: Whether initialization was successful.
        company_id: UUID of the company.
        roles_created: Number of roles created.
        policies_created: Number of policies created.
        roles: List of role names created.
    """

    success = fields.Boolean(required=True)
    company_id = fields.UUID(required=True)
    roles_created = fields.Integer(
        required=True,
        validate=validate.Range(min=0),
    )
    policies_created = fields.Integer(
        required=True,
        validate=validate.Range(min=0),
    )
    roles = fields.List(
        fields.String(),
        required=True,
    )
