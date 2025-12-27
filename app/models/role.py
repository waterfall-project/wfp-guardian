# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Role model for RBAC authorization.

This module defines the Role model which groups policies for user assignment.
Roles are company-scoped and can be assigned to users.
"""

from typing import Any

from sqlalchemy.orm import relationship

from app.models.constants import (
    ROLE_DESCRIPTION_MAX_LENGTH,
    ROLE_DISPLAY_NAME_MAX_LENGTH,
    ROLE_NAME_MAX_LENGTH,
)
from app.models.db import db
from app.models.types import GUID, TimestampMixin, UUIDMixin

# Association table for Role-Policy many-to-many relationship
role_policies = db.Table(
    "role_policies",
    db.Column(
        "role_id",
        GUID(),
        db.ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "policy_id",
        GUID(),
        db.ForeignKey("policies.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "created_at",
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False,
    ),
)


class Role(UUIDMixin, TimestampMixin, db.Model):
    """Role entity for RBAC authorization.

    Represents a collection of policies that can be assigned to users.
    Roles are scoped to a company for multi-tenant isolation.

    Attributes:
        id: Unique UUID identifier (inherited from UUIDMixin).
        name: Technical name (lowercase, underscores, immutable).
        display_name: Human-readable display name.
        description: Optional detailed description of the role.
        company_id: UUID of the owning company (multi-tenant isolation).
        priority: Evaluation priority (higher = evaluated first), default 0.
        is_active: Whether the role is active, default True.
        policies: Many-to-many relationship to Policy entities.
        created_at: Timestamp of creation (inherited from TimestampMixin).
        updated_at: Timestamp of last update (inherited from TimestampMixin).
    """

    __tablename__ = "roles"

    name = db.Column(db.String(ROLE_NAME_MAX_LENGTH), nullable=False, index=True)
    display_name = db.Column(db.String(ROLE_DISPLAY_NAME_MAX_LENGTH), nullable=False)
    description = db.Column(db.String(ROLE_DESCRIPTION_MAX_LENGTH), nullable=True)
    company_id = db.Column(db.Uuid, nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Many-to-many relationship with Policy
    policies = relationship(
        "Policy",
        secondary=role_policies,
        backref="roles",
        lazy="selectin",
    )

    # Unique constraint on name per company
    __table_args__ = (
        db.UniqueConstraint("name", "company_id", name="uq_role_name_company"),
        db.Index("ix_roles_company_active", "company_id", "is_active"),
    )

    def __init__(
        self,
        name: str,
        display_name: str,
        company_id: str,
        description: str | None = None,
        is_active: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize a new Role instance.

        Args:
            name: Technical name (lowercase, underscores).
            display_name: Human-readable display name.
            company_id: UUID of the owning company.
            description: Optional detailed description.
            is_active: Whether the role is active (default True).
            **kwargs: Additional keyword arguments passed to parent classes.
        """
        super().__init__(**kwargs)
        self.name = name
        self.display_name = display_name
        self.company_id = company_id
        self.description = description
        self.is_active = is_active

    def __repr__(self) -> str:
        """Return string representation of the Role instance.

        Returns:
            String representation including name, company_id, and ID.
        """
        return f"<Role {self.name} (company={self.company_id})> (ID: {self.id})"

    @classmethod
    def get_all(
        cls,
        company_id: str,
        limit: int = 50,
        offset: int = 0,
        is_active: bool | None = None,
    ) -> list["Role"]:
        """Retrieve all roles for a company with pagination.

        Args:
            company_id: UUID of the company.
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            is_active: Optional filter by active status.

        Returns:
            List of Role instances.
        """
        query = cls.query.filter_by(company_id=company_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        return query.offset(offset).limit(limit).all()

    @classmethod
    def get_by_id(cls, role_id: str, company_id: str) -> "Role | None":
        """Retrieve a role by ID within a company scope.

        Args:
            role_id: UUID of the role.
            company_id: UUID of the company (for tenant isolation).

        Returns:
            Role instance if found, None otherwise.
        """
        return cls.query.filter_by(id=role_id, company_id=company_id).first()

    @classmethod
    def get_by_name(cls, name: str, company_id: str) -> "Role | None":
        """Retrieve a role by name within a company scope.

        Args:
            name: Technical name of the role.
            company_id: UUID of the company.

        Returns:
            Role instance if found, None otherwise.
        """
        return cls.query.filter_by(name=name, company_id=company_id).first()

    @classmethod
    def count_by_company(cls, company_id: str, is_active: bool | None = None) -> int:
        """Count roles for a company.

        Args:
            company_id: UUID of the company.
            is_active: Optional filter by active status.

        Returns:
            Total count of roles.
        """
        query = cls.query.filter_by(company_id=company_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        return query.count()

    def attach_policy(self, policy_id: str) -> None:
        """Attach a policy to this role.

        Args:
            policy_id: UUID of the policy to attach.

        Note:
            This method is idempotent - attaching an already attached
            policy will be ignored.
        """
        from uuid import UUID

        from app.models.policy import Policy

        policy_uuid = UUID(policy_id)
        policy = db.session.get(Policy, policy_uuid)
        if policy:
            if policy in self.policies:
                return  # Already attached
            self.policies.append(policy)
            db.session.add(self)  # Ensure role is in session

    def detach_policy(self, policy_id: str) -> bool:
        """Detach a policy from this role.

        Args:
            policy_id: UUID of the policy to detach.

        Returns:
            True if policy was detached, False if not found.
        """
        from uuid import UUID

        from app.models.policy import Policy

        policy = db.session.get(Policy, UUID(policy_id))
        if policy and policy in self.policies:
            self.policies.remove(policy)
            return True
        return False

    def get_policies_count(self) -> int:
        """Get the count of policies attached to this role.

        Returns:
            Number of policies.
        """
        return len(self.policies)

    def to_dict(self, include_policies_count: bool = True) -> dict[str, Any]:
        """Convert role to dictionary representation.

        Args:
            include_policies_count: Whether to include policies count.

        Returns:
            Dictionary with role data.
        """
        data = {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "company_id": str(self.company_id),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_policies_count:
            data["policies_count"] = self.get_policies_count()

        return data
