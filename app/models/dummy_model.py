# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Dummy model for demonstration purposes.

This module defines a simple SQLAlchemy model to demonstrate database
operations and testing patterns in the application.
"""

import uuid
from typing import Optional, Union

from app.models.constants import DUMMY_DESCRIPTION_MAX_LENGTH, DUMMY_NAME_MAX_LENGTH
from app.models.db import db
from app.models.types import JSONB, TimestampMixin, UUIDMixin


class Dummy(UUIDMixin, TimestampMixin, db.Model):
    """Dummy entity for demonstration and testing.

    This model represents a simple entity with a name and description,
    used primarily for testing database operations and demonstrating
    SQLAlchemy patterns. Includes UUID primary key and automatic timestamps.

    Attributes:
        id: Unique UUID identifier (inherited from UUIDMixin).
        name: Name of the Dummy entity (max {DUMMY_NAME_MAX_LENGTH} characters).
        description: Optional description of the Dummy entity (max {DUMMY_DESCRIPTION_MAX_LENGTH} characters).
        extra_metadata: Optional JSON metadata for flexible data storage.
        created_at: Timestamp of creation (inherited from TimestampMixin).
        updated_at: Timestamp of last update (inherited from TimestampMixin).
    """

    __tablename__ = "dummy"

    name = db.Column(db.String(DUMMY_NAME_MAX_LENGTH), nullable=False)
    description = db.Column(db.String(DUMMY_DESCRIPTION_MAX_LENGTH), nullable=True)
    extra_metadata = db.Column(JSONB(), nullable=True)

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        extra_metadata: Optional[dict] = None,
        **kwargs,
    ) -> None:
        """Initialize a new Dummy instance.

        Args:
            name: Name for the Dummy entity.
            description: Optional description for the Dummy entity.
            extra_metadata: Optional JSON metadata for flexible data storage.
            **kwargs: Additional keyword arguments passed to parent classes.
        """
        super().__init__(**kwargs)
        self.name = name
        self.description = description
        self.extra_metadata = extra_metadata

    def __repr__(self) -> str:
        """Return string representation of the Dummy instance.

        Returns:
            String representation including name, ID, and description.
        """
        return f"<Dummy {self.name}> (ID: {self.id}, Description: {self.description})"

    @classmethod
    def get_all(
        cls, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> list["Dummy"]:
        """Retrieve all Dummy records from the database with optional pagination.

        Args:
            limit: Maximum number of records to return. If None, returns all records.
            offset: Number of records to skip. Defaults to 0.

        Returns:
            List of Dummy objects from the database.

        Example:
            >>> dummies = Dummy.get_all()
            >>> len(dummies)
            5
            >>> dummies_page = Dummy.get_all(limit=10, offset=0)
            >>> len(dummies_page)
            10
        """
        query = cls.query

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        result: list[Dummy] = query.all()
        return result

    @classmethod
    def get_by_id(cls, dummy_id: Union[uuid.UUID, str]) -> Optional["Dummy"]:
        """Retrieve a Dummy record by its primary key ID.

        Args:
            dummy_id: The unique UUID identifier of the Dummy to retrieve.
                     Can be a UUID object or string representation.

        Returns:
            The Dummy object with the specified ID, or None if not found.

        Example:
            >>> dummy = Dummy.get_by_id("550e8400-e29b-41d4-a716-446655440000")
            >>> dummy.name if dummy else "Not found"
            'Example Dummy'
        """
        if isinstance(dummy_id, str):
            dummy_id = uuid.UUID(dummy_id)
        result: Optional[Dummy] = db.session.get(cls, dummy_id)
        return result

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Dummy"]:
        """Retrieve a Dummy record by its name.

        Args:
            name: The name of the Dummy to retrieve.

        Returns:
            The first Dummy object with the specified name, or None if not found.

        Example:
            >>> dummy = Dummy.get_by_name("test")
            >>> dummy.description if dummy else "Not found"
            'Test description'
        """
        result: Optional[Dummy] = cls.query.filter_by(name=name).first()
        return result

    @classmethod
    def create(
        cls,
        name: str,
        description: Optional[str] = None,
        extra_metadata: Optional[dict] = None,
    ) -> "Dummy":
        """Create and persist a new Dummy record.

        Args:
            name: Name for the new Dummy entity.
            description: Optional description for the Dummy entity.
            extra_metadata: Optional JSON metadata for flexible data storage.

        Returns:
            The newly created and committed Dummy object with auto-generated UUID.

        Example:
            >>> dummy = Dummy.create("New Dummy", "A test dummy")
            >>> isinstance(dummy.id, uuid.UUID)
            True
        """
        dummy = cls(name=name, description=description, extra_metadata=extra_metadata)
        db.session.add(dummy)
        db.session.commit()
        return dummy
