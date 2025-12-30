# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Access log model for audit trail.

This module defines the AccessLog model for tracking all access control
decisions in the Guardian system. Logs are stored for compliance,
security auditing, and debugging purposes.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text

from app.models.db import db
from app.models.types import GUID, JSONB


class AccessLog(db.Model):
    """Model for access control audit logs.

    Tracks all access control decisions (granted/denied) for compliance
    and security auditing. Conforms to OpenAPI specification for
    access logs endpoint.

    Retention: 7 days in PostgreSQL (hot data), then shipped to Loki.
    """

    __tablename__ = "access_logs"

    # Required fields per OpenAPI spec
    id = db.Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID, nullable=False, index=True)
    company_id = db.Column(GUID, nullable=False, index=True)
    service = db.Column(String(50), nullable=False)
    resource_name = db.Column(String(50), nullable=False)
    operation = db.Column(String(20), nullable=False)
    access_granted = db.Column(Boolean, nullable=False, index=True)
    created_at = db.Column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC), index=True
    )

    # Optional fields per OpenAPI spec
    project_id = db.Column(GUID, nullable=True, index=True)
    resource_id = db.Column(String(255), nullable=True)
    reason = db.Column(String(50), nullable=True)
    ip_address = db.Column(String(45), nullable=True)  # IPv4 (15) or IPv6 (45 chars)
    user_agent = db.Column(Text, nullable=True)
    context = db.Column(JSONB, nullable=True)

    def __repr__(self):
        """String representation of AccessLog."""
        return (
            f"<AccessLog {self.id} user={self.user_id} "
            f"service={self.service} operation={self.operation} "
            f"granted={self.access_granted}>"
        )

    def to_dict(self):
        """Convert AccessLog to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "company_id": str(self.company_id),
            "service": self.service,
            "resource_name": self.resource_name,
            "operation": self.operation,
            "access_granted": self.access_granted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "project_id": str(self.project_id) if self.project_id else None,
            "resource_id": self.resource_id,
            "reason": self.reason,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "context": self.context,
        }
