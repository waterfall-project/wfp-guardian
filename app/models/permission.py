# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Permission model for RBAC authorization.

This module defines the Permission model which represents atomic permissions
in the Guardian authorization system. Permissions follow the format:
service:resource_name:operation (e.g., "storage:files:DELETE").

Permissions are read-only and seeded at application startup from permissions.json.
"""

from app.models.constants import (
    PERMISSION_DESCRIPTION_MAX_LENGTH,
    PERMISSION_NAME_MAX_LENGTH,
    PERMISSION_OPERATION_MAX_LENGTH,
    PERMISSION_RESOURCE_NAME_MAX_LENGTH,
    PERMISSION_SERVICE_MAX_LENGTH,
)
from app.models.db import db
from app.models.types import TimestampMixin, UUIDMixin


class Permission(UUIDMixin, TimestampMixin, db.Model):
    """Permission entity for RBAC authorization.

    Represents atomic permissions in the Guardian authorization system.
    Permissions are read-only and seeded from permissions.json at startup.

    Format: service:resource_name:operation
    Example: "storage:files:DELETE", "identity:users:READ"

    Attributes:
        id: Unique UUID identifier (inherited from UUIDMixin).
        name: Full permission name in format "service:resource_name:operation".
        service: Service identifier (e.g., "storage", "identity").
        resource_name: Resource type identifier (e.g., "files", "users").
        operation: Operation type (LIST, CREATE, READ, UPDATE, DELETE, etc.).
        description: Optional human-readable description of the permission.
        created_at: Timestamp of creation (inherited from TimestampMixin).
        updated_at: Timestamp of last update (inherited from TimestampMixin).
    """

    __tablename__ = "permissions"

    name = db.Column(
        db.String(PERMISSION_NAME_MAX_LENGTH), nullable=False, unique=True, index=True
    )
    service = db.Column(db.String(PERMISSION_SERVICE_MAX_LENGTH), nullable=False)
    resource_name = db.Column(
        db.String(PERMISSION_RESOURCE_NAME_MAX_LENGTH), nullable=False
    )
    operation = db.Column(db.String(PERMISSION_OPERATION_MAX_LENGTH), nullable=False)
    description = db.Column(db.String(PERMISSION_DESCRIPTION_MAX_LENGTH), nullable=True)

    # Add composite index for querying by service and resource
    __table_args__ = (
        db.Index("ix_permissions_service_resource", "service", "resource_name"),
    )

    def __init__(
        self,
        name: str,
        service: str,
        resource_name: str,
        operation: str,
        description: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize a new Permission instance.

        Args:
            name: Full permission name (service:resource_name:operation).
            service: Service identifier.
            resource_name: Resource type identifier.
            operation: Operation type.
            description: Optional description of the permission.
            **kwargs: Additional keyword arguments passed to parent classes.
        """
        super().__init__(**kwargs)
        self.name = name
        self.service = service
        self.resource_name = resource_name
        self.operation = operation
        self.description = description

    def __repr__(self) -> str:
        """Return string representation of the Permission instance.

        Returns:
            String representation including name and ID.
        """
        return f"<Permission {self.name}> (ID: {self.id})"

    @classmethod
    def get_all(
        cls, limit: int | None = None, offset: int | None = None
    ) -> list["Permission"]:
        """Retrieve all Permission records from the database with optional pagination.

        Args:
            limit: Maximum number of records to return. If None, returns all records.
            offset: Number of records to skip. If None, starts from the beginning.

        Returns:
            List of Permission instances.
        """
        query = cls.query
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_by_name(cls, name: str) -> "Permission | None":
        """Retrieve a Permission by its unique name.

        Args:
            name: The permission name (service:resource_name:operation).

        Returns:
            Permission instance if found, None otherwise.
        """
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_by_service(cls, service: str) -> list["Permission"]:
        """Retrieve all Permissions for a specific service.

        Args:
            service: The service identifier to filter by.

        Returns:
            List of Permission instances for the service.
        """
        return cls.query.filter_by(service=service).all()

    @classmethod
    def get_by_service_and_resource(
        cls, service: str, resource_name: str
    ) -> list["Permission"]:
        """Retrieve all Permissions for a specific service and resource.

        Args:
            service: The service identifier to filter by.
            resource_name: The resource name to filter by.

        Returns:
            List of Permission instances for the service and resource.
        """
        return cls.query.filter_by(service=service, resource_name=resource_name).all()

    def to_dict(self) -> dict:
        """Convert Permission to dictionary representation.

        Returns:
            Dictionary with permission attributes.
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "service": self.service,
            "resource_name": self.resource_name,
            "operation": self.operation,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
