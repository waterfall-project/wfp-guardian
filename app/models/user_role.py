# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""UserRole model for RBAC authorization.

This module defines the UserRole model which assigns roles to users.
UserRoles are company-scoped and can optionally be project-scoped.
They support hierarchical access and expiration dates.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import Index, or_
from sqlalchemy.orm import relationship

from app.models.db import db
from app.models.types import GUID, TimestampMixin, UUIDMixin


class UserRole(UUIDMixin, TimestampMixin, db.Model):
    """UserRole model for user-role assignments.

    Represents the assignment of a role to a user within a company.
    Supports:
    - Company-wide or project-specific scope
    - Direct or hierarchical access (via scope_type)
    - Temporary roles (via expires_at)
    - Audit trail (granted_by, granted_at)

    Attributes:
        id (UUID): Primary key.
        user_id (UUID): User receiving the role.
        role_id (UUID): Role being assigned.
        company_id (UUID): Company scope (always required).
        project_id (UUID, optional): Project scope (NULL = company-wide).
        scope_type (str): Access scope ('direct' or 'hierarchical').
        granted_by (UUID, optional): User who granted this role.
        granted_at (datetime): Timestamp of role assignment.
        expires_at (datetime, optional): Expiration date (NULL = permanent).
        is_active (bool): Active status (default True).
        created_at (datetime): Record creation timestamp.
        updated_at (datetime): Last modification timestamp.

    Relationships:
        role: Reference to the assigned Role.

    Indexes:
        - (user_id, company_id) for efficient user lookups
        - (role_id, company_id) for role-based queries
        - (project_id) for project filtering
        - (expires_at) for expiration checks
    """

    __tablename__ = "user_roles"

    # Foreign Keys
    user_id = db.Column(GUID(), nullable=False, index=True)
    role_id = db.Column(
        GUID(), db.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    company_id = db.Column(GUID(), nullable=False, index=True)

    # Scope
    project_id = db.Column(GUID(), nullable=True, index=True)
    scope_type = db.Column(
        db.String(20), nullable=False, default="direct", server_default="direct"
    )

    # Audit & Metadata
    granted_by = db.Column(GUID(), nullable=True)
    granted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=db.func.now(),
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Relationships
    role = relationship("Role", backref="user_roles", lazy="joined")

    # Indexes for query performance
    __table_args__ = (
        Index("ix_user_roles_user_company", "user_id", "company_id"),
        Index("ix_user_roles_role_company", "role_id", "company_id"),
        Index("ix_user_roles_expires_at", "expires_at"),
        # Unique constraint: one active role per user per company/project
        Index(
            "ix_user_roles_unique_active",
            "user_id",
            "role_id",
            "company_id",
            "project_id",
            "is_active",
            unique=True,
            postgresql_where=db.text("is_active = true"),
        ),
    )

    def __init__(
        self,
        user_id: str,
        role_id: str,
        company_id: str,
        project_id: str | None = None,
        scope_type: str = "direct",
        granted_by: str | None = None,
        granted_at: datetime | None = None,
        expires_at: datetime | None = None,
        is_active: bool = True,
    ):
        """Initialize a new UserRole.

        Args:
            user_id: User receiving the role
            role_id: Role being assigned
            company_id: Company scope
            project_id: Project scope (optional, NULL = company-wide)
            scope_type: Access scope ('direct' or 'hierarchical')
            granted_by: User who granted this role (optional)
            granted_at: Timestamp of grant (defaults to now)
            expires_at: Expiration date (optional, NULL = permanent)
            is_active: Active status (default True)
        """
        super().__init__()
        self.user_id = user_id
        self.role_id = role_id
        self.company_id = company_id
        self.project_id = project_id
        self.scope_type = scope_type
        self.granted_by = granted_by
        self.granted_at = granted_at or datetime.now(UTC)
        self.expires_at = expires_at
        self.is_active = is_active

    def __repr__(self) -> str:
        """String representation of UserRole."""
        scope = f"project:{self.project_id}" if self.project_id else "company-wide"
        return (
            f"<UserRole(id={self.id}, user={self.user_id}, "
            f"role={self.role_id}, {scope})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert UserRole to dictionary.

        Returns:
            Dictionary representation with all fields.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "company_id": self.company_id,
            "project_id": self.project_id,
            "scope_type": self.scope_type,
            "granted_by": self.granted_by,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_expired(self) -> bool:
        """Check if this role assignment has expired.

        Returns:
            True if expires_at is set and in the past, False otherwise.
        """
        if not self.expires_at:
            return False
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            # Make naive datetime aware
            expires = expires.replace(tzinfo=UTC)
        return now > expires

    @classmethod
    def get_all(
        cls,
        user_id: str,
        company_id: str,
        limit: int | None = None,
        offset: int | None = None,
        project_id: str | None = None,
        is_active: bool | None = None,
    ) -> list["UserRole"]:
        """Get all UserRoles for a user in a company.

        Args:
            user_id: User ID to filter by
            company_id: Company ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            project_id: Optional project filter (if set, returns company-wide + project-specific)
            is_active: Optional active status filter

        Returns:
            List of UserRole instances matching criteria.
        """
        query = cls.query.filter_by(user_id=user_id, company_id=company_id)

        # Project filtering
        if project_id is not None:
            # Include both company-wide (project_id=NULL) and specific project
            query = query.filter(
                or_(cls.project_id.is_(None), cls.project_id == project_id)
            )

        # Active status filtering
        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        # Order by granted_at descending (most recent first)
        query = query.order_by(cls.granted_at.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_by_id(
        cls, user_role_id: str, user_id: str, company_id: str
    ) -> Optional["UserRole"]:
        """Get a UserRole by ID, scoped to user and company.

        Args:
            user_role_id: UserRole ID
            user_id: User ID for scoping
            company_id: Company ID for scoping

        Returns:
            UserRole instance if found, None otherwise.
        """
        return cls.query.filter_by(
            id=user_role_id, user_id=user_id, company_id=company_id
        ).first()

    @classmethod
    def count_by_user(
        cls,
        user_id: str,
        company_id: str,
        project_id: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count UserRoles for a user.

        Args:
            user_id: User ID
            company_id: Company ID
            project_id: Optional project filter
            is_active: Optional active status filter

        Returns:
            Count of matching UserRoles.
        """
        query = cls.query.filter_by(user_id=user_id, company_id=company_id)

        if project_id is not None:
            query = query.filter(
                or_(cls.project_id.is_(None), cls.project_id == project_id)
            )

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        return query.count()

    @classmethod
    def get_users_by_role(
        cls,
        role_id: str,
        company_id: str,
        limit: int | None = None,
        offset: int | None = None,
        is_active: bool | None = None,
    ) -> list["UserRole"]:
        """Get all users assigned to a role.

        Args:
            role_id: Role ID
            company_id: Company ID for scoping
            limit: Maximum number of results
            offset: Number of results to skip
            is_active: Optional active status filter

        Returns:
            List of UserRole instances.
        """
        query = cls.query.filter_by(role_id=role_id, company_id=company_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        query = query.order_by(cls.granted_at.desc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def count_users_by_role(
        cls, role_id: str, company_id: str, is_active: bool | None = None
    ) -> int:
        """Count users assigned to a role.

        Args:
            role_id: Role ID
            company_id: Company ID
            is_active: Optional active status filter

        Returns:
            Count of users with this role.
        """
        query = cls.query.filter_by(role_id=role_id, company_id=company_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        return query.count()
