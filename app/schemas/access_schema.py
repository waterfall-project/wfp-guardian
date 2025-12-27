# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas for Access Control endpoints."""

from marshmallow import EXCLUDE, Schema, ValidationError, fields, validates
from marshmallow.validate import Length

from app.utils.guardian import Operation


class CheckAccessRequestSchema(Schema):
    """Schema for check-access request."""

    service = fields.Str(required=True)
    resource_name = fields.Str(required=True)
    operation = fields.Str(required=True)
    context = fields.Dict(keys=fields.Str(), values=fields.Raw(), required=False)

    class Meta:
        """Schema configuration."""

        unknown = EXCLUDE

    @validates("operation")
    def validate_operation(self, value: str, **kwargs) -> None:
        """Validate operation is a valid CRUD operation.

        Args:
            value: Operation to validate.
            **kwargs: Additional keyword arguments from Marshmallow.

        Raises:
            ValidationError: If operation is not valid.
        """
        valid_operations = [op.value for op in Operation]
        if value not in valid_operations:
            raise ValidationError(
                f"Invalid operation. Must be one of: {', '.join(valid_operations)}"
            )


class BatchCheckAccessRequestSchema(Schema):
    """Schema for batch check-access request."""

    checks = fields.List(
        fields.Nested(CheckAccessRequestSchema),
        required=True,
        validate=Length(min=1, max=50, error="Must provide between 1 and 50 checks"),
    )

    class Meta:
        """Schema configuration."""

        unknown = EXCLUDE
