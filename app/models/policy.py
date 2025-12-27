# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Policy model for RBAC authorization.

This module defines the Policy model which groups permissions into reusable sets.
Policies are company-scoped and can be attached to roles.
"""

import uuid
from typing import Any

from sqlalchemy.orm import relationship

from app.models.constants import (
    POLICY_DESCRIPTION_MAX_LENGTH,
    POLICY_DISPLAY_NAME_MAX_LENGTH,
    POLICY_NAME_MAX_LENGTH,
)
from app.models.db import db
from app.models.types import GUID, TimestampMixin, UUIDMixin

# Association table for Policy-Permission many-to-many relationship
policy_permissions = db.Table(
    "policy_permissions",
    db.Column(
        "policy_id",
        GUID(),
        db.ForeignKey("policies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "permission_id",
        GUID(),
        db.ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "created_at",
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False,
    ),
)


class Policy(UUIDMixin, TimestampMixin, db.Model):
    """Policy entity for RBAC authorization.

    Represents a collection of permissions that can be attached to roles.
    Policies are scoped to a company for multi-tenant isolation.

    Attributes:
        id: Unique UUID identifier (inherited from UUIDMixin).
        name: Technical name (lowercase, underscores, immutable).
        display_name: Human-readable display name.
        description: Optional detailed description of the policy.
        company_id: UUID of the owning company (multi-tenant isolation).
        priority: Evaluation priority (higher = evaluated first), default 0.
        is_active: Whether the policy is active, default True.
        permissions: Many-to-many relationship to Permission entities.
        created_at: Timestamp of creation (inherited from TimestampMixin).
        updated_at: Timestamp of last update (inherited from TimestampMixin).
    """

    __tablename__ = "policies"

    name = db.Column(db.String(POLICY_NAME_MAX_LENGTH), nullable=False, index=True)
    display_name = db.Column(db.String(POLICY_DISPLAY_NAME_MAX_LENGTH), nullable=False)
    description = db.Column(db.String(POLICY_DESCRIPTION_MAX_LENGTH), nullable=True)
    company_id = db.Column(GUID(), nullable=False, index=True)
    priority = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Many-to-many relationship with Permission
    permissions = relationship(
        "Permission",
        secondary=policy_permissions,
        backref="policies",
        lazy="selectin",
    )

    # Unique constraint on name per company
    __table_args__ = (
        db.UniqueConstraint("name", "company_id", name="uq_policy_name_company"),
        db.Index("ix_policies_company_active", "company_id", "is_active"),
    )

    def __init__(
        self,
        name: str,
        display_name: str,
        company_id: uuid.UUID | str,
        description: str | None = None,
        priority: int = 0,
        is_active: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize a new Policy instance.

        Args:
            name: Technical name (lowercase, underscores).
            display_name: Human-readable display name.
            company_id: UUID of the owning company.
            description: Optional detailed description.
            priority: Evaluation priority (default 0).
            is_active: Whether the policy is active (default True).
            **kwargs: Additional keyword arguments passed to parent classes.
        """
        super().__init__(**kwargs)
        self.name = name
        self.display_name = display_name
        self.company_id = company_id
        self.description = description
        self.priority = priority
        self.is_active = is_active

    def __repr__(self) -> str:
        """Return string representation of the Policy instance.

        Returns:
            String representation including name, company_id, and ID.
        """
        return f"<Policy {self.name} (company={self.company_id})> (ID: {self.id})"

    @classmethod
    def get_all(
        cls,
        company_id: uuid.UUID | str,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> list["Policy"]:
        """Retrieve all policies for a company with pagination.

        Args:
            company_id: UUID of the company.
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            is_active: Optional filter by active status.

        Returns:
            List of Policy instances.
        """
        query = cls.query.filter_by(company_id=company_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        return query.offset(offset).limit(limit).all()

    @classmethod
    def get_by_id(
        cls, policy_id: uuid.UUID | str, company_id: uuid.UUID | str
    ) -> "Policy | None":
        """Retrieve a policy by ID within a company scope.

        Args:
            policy_id: UUID of the policy.
            company_id: UUID of the company (for tenant isolation).

        Returns:
            Policy instance if found, None otherwise.
        """
        return cls.query.filter_by(id=policy_id, company_id=company_id).first()

    @classmethod
    def get_by_name(cls, name: str, company_id: uuid.UUID | str) -> "Policy | None":
        """Retrieve a policy by name within a company scope.

        Args:
            name: Technical name of the policy.
            company_id: UUID of the company.

        Returns:
            Policy instance if found, None otherwise.
        """
        return cls.query.filter_by(name=name, company_id=company_id).first()

    @classmethod
    def count_by_company(
        cls, company_id: uuid.UUID | str, is_active: bool | None = None
    ) -> int:
        """Count policies for a company.

        Args:
            company_id: UUID of the company.
            is_active: Optional filter by active status.

        Returns:
            Total count of policies.
        """
        query = cls.query.filter_by(company_id=company_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        return query.count()

    def attach_permission(self, permission_id: str) -> None:
        """Attach a permission to this policy.

        Args:
            permission_id: UUID of the permission to attach.

        Note:
            This method is idempotent - attaching an already attached
            permission will raise an IntegrityError on commit.
        """
        from uuid import UUID

        from app.models.permission import Permission

        perm_uuid = UUID(permission_id)
        permission = db.session.get(Permission, perm_uuid)
        if permission:
            # Debug: check if already in list
            if permission in self.permissions:
                return  # Already attached
            self.permissions.append(permission)
            db.session.add(self)  # Ensure policy is in session

    def detach_permission(self, permission_id: str) -> bool:
        """Detach a permission from this policy.

        Args:
            permission_id: UUID of the permission to detach.

        Returns:
            True if permission was detached, False if not found.
        """
        from uuid import UUID

        from app.models.permission import Permission

        permission = db.session.get(Permission, UUID(permission_id))
        if permission and permission in self.permissions:
            self.permissions.remove(permission)
            return True
        return False

    def get_permissions_count(self) -> int:
        """Get the count of permissions attached to this policy.

        Returns:
            Number of permissions.
        """
        return len(self.permissions)

    @property
    def permissions_count(self) -> int:
        """Property for permissions count (for schema serialization).

        Returns:
            Number of permissions.
        """
        return self.get_permissions_count()

    def to_dict(self, include_permissions_count: bool = True) -> dict[str, Any]:
        """Convert policy to dictionary representation.

        Args:
            include_permissions_count: Whether to include permissions count.

        Returns:
            Dictionary with policy data.
        """
        data = {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "company_id": str(self.company_id),
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_permissions_count:
            data["permissions_count"] = self.get_permissions_count()

        return data
