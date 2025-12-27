# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for UserRole model.

Tests all operations, UUID handling, uniqueness constraints, relationships,
query methods, and expiration handling of the UserRole model.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.db import db
from app.models.role import Role
from app.models.user_role import UserRole


@pytest.fixture
def sample_company_id():
    """Return a sample company UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_user_id():
    """Return a sample user UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_role(app, sample_company_id):
    """Create a sample role for testing and return its ID."""
    with app.app_context():
        role = Role(
            name="test_role",
            display_name="Test Role",
            company_id=sample_company_id,
        )
        db.session.add(role)
        db.session.commit()
        role_id = role.id
    return role_id


class TestUserRoleModel:
    """Test suite for UserRole model."""

    def test_user_role_has_uuid_id(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test UserRole model has UUID as primary key."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()

            assert user_role.id is not None
            assert isinstance(user_role.id, uuid.UUID)

    def test_user_role_repr(self, app, sample_user_id, sample_company_id, sample_role):
        """Test UserRole __repr__ returns correct string."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()

            repr_str = repr(user_role)
            assert str(sample_user_id) in repr_str
            assert str(sample_role) in repr_str
            assert "company-wide" in repr_str

    def test_user_role_creation_with_all_fields(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test creating UserRole with all fields."""
        project_id = uuid.uuid4()
        granted_by = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=30)
        granted_at = datetime.now(UTC)

        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=str(project_id),
                scope_type="hierarchical",
                granted_by=str(granted_by),
                granted_at=granted_at,
                expires_at=expires_at,
                is_active=True,
            )
            db.session.add(user_role)
            db.session.commit()

            assert user_role.user_id == sample_user_id
            assert user_role.role_id == sample_role
            assert user_role.company_id == sample_company_id
            assert user_role.project_id == project_id
            assert user_role.scope_type == "hierarchical"
            assert user_role.granted_by == granted_by
            # SQLite removes timezone info, compare without microseconds
            assert (
                abs(
                    (
                        user_role.granted_at.replace(tzinfo=UTC) - granted_at
                    ).total_seconds()
                )
                < 1
            )
            assert user_role.expires_at is not None
            assert (
                abs(
                    (
                        user_role.expires_at.replace(tzinfo=UTC) - expires_at
                    ).total_seconds()
                )
                < 1
            )
            assert user_role.is_active is True

    def test_user_role_creation_with_defaults(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test creating UserRole with default values."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()

            assert user_role.project_id is None
            assert user_role.scope_type == "direct"
            assert user_role.granted_by is None
            assert user_role.expires_at is None
            assert user_role.is_active is True
            assert isinstance(user_role.granted_at, datetime)

    def test_user_role_unique_constraint_active(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test unique constraint for active user-role-company-project combinations."""
        project_id = uuid.uuid4()
        with app.app_context():
            # Create first assignment with specific project
            user_role1 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=str(project_id),
                is_active=True,
            )
            db.session.add(user_role1)
            db.session.commit()

            # Try to create duplicate active assignment - should fail
            user_role2 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=str(project_id),
                is_active=True,
            )
            db.session.add(user_role2)

            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_user_role_allows_inactive_duplicates(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test that inactive roles can have duplicates."""
        with app.app_context():
            # Create inactive assignment
            user_role1 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                is_active=False,
            )
            db.session.add(user_role1)
            db.session.commit()

            # Create another inactive - should succeed
            user_role2 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                is_active=False,
            )
            db.session.add(user_role2)
            db.session.commit()

            assert user_role1.id != user_role2.id

    def test_user_role_get_all(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test get_all method for user roles."""
        with app.app_context():
            # Create multiple assignments
            for i in range(3):
                user_role = UserRole(
                    user_id=sample_user_id,
                    role_id=sample_role,
                    company_id=sample_company_id,
                    is_active=(i < 2),  # First 2 active, last inactive
                )
                db.session.add(user_role)
            db.session.commit()

            # Get all active
            roles = UserRole.get_all(sample_user_id, sample_company_id, is_active=True)
            assert len(roles) == 2

            # Get all (active and inactive)
            roles_all = UserRole.get_all(sample_user_id, sample_company_id)
            assert len(roles_all) == 3

    def test_user_role_get_all_with_project_filter(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test get_all with project filtering."""
        project_id = uuid.uuid4()

        with app.app_context():
            # Company-wide role
            user_role1 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=None,
            )
            # Project-specific role
            user_role2 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=str(project_id),
            )
            # Different project
            user_role3 = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=str(uuid.uuid4()),
            )
            db.session.add_all([user_role1, user_role2, user_role3])
            db.session.commit()

            # Filter by project - should return company-wide + specific project
            roles = UserRole.get_all(
                sample_user_id, sample_company_id, project_id=str(project_id)
            )
            assert len(roles) == 2
            project_ids = [r.project_id for r in roles]
            assert None in project_ids  # Company-wide
            assert project_id in project_ids

    def test_user_role_get_all_pagination(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test get_all with pagination."""
        with app.app_context():
            # Create 5 assignments
            for _i in range(5):
                user_role = UserRole(
                    user_id=sample_user_id,
                    role_id=sample_role,
                    company_id=sample_company_id,
                )
                db.session.add(user_role)
            db.session.commit()

            # Get first 2
            roles = UserRole.get_all(
                sample_user_id, sample_company_id, limit=2, offset=0
            )
            assert len(roles) == 2

            # Get next 2
            roles_next = UserRole.get_all(
                sample_user_id, sample_company_id, limit=2, offset=2
            )
            assert len(roles_next) == 2
            assert roles[0].id != roles_next[0].id

    def test_user_role_get_by_id(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test get_by_id method."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()
            user_role_id = user_role.id

            # Get by ID
            found = UserRole.get_by_id(user_role_id, sample_user_id, sample_company_id)
            assert found is not None
            assert found.id == user_role_id

    def test_user_role_get_by_id_wrong_user(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test get_by_id with wrong user returns None."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()
            user_role_id = user_role.id

            # Try to get with different user_id
            found = UserRole.get_by_id(
                user_role_id, str(uuid.uuid4()), sample_company_id
            )
            assert found is None

    def test_user_role_count_by_user(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test count_by_user method."""
        with app.app_context():
            # Create 3 active, 2 inactive
            for i in range(5):
                user_role = UserRole(
                    user_id=sample_user_id,
                    role_id=sample_role,
                    company_id=sample_company_id,
                    is_active=(i < 3),
                )
                db.session.add(user_role)
            db.session.commit()

            # Count active
            count_active = UserRole.count_by_user(
                sample_user_id, sample_company_id, is_active=True
            )
            assert count_active == 3

            # Count all
            count_all = UserRole.count_by_user(sample_user_id, sample_company_id)
            assert count_all == 5

    def test_user_role_get_users_by_role(self, app, sample_company_id, sample_role):
        """Test get_users_by_role method."""
        with app.app_context():
            # Assign role to 3 different users
            for _i in range(3):
                user_role = UserRole(
                    user_id=str(uuid.uuid4()),
                    role_id=sample_role,
                    company_id=sample_company_id,
                )
                db.session.add(user_role)
            db.session.commit()

            # Get all users with this role
            user_roles = UserRole.get_users_by_role(sample_role, sample_company_id)
            assert len(user_roles) == 3

    def test_user_role_count_users_by_role(self, app, sample_company_id, sample_role):
        """Test count_users_by_role method."""
        with app.app_context():
            # Create 4 assignments (3 active, 1 inactive)
            for i in range(4):
                user_role = UserRole(
                    user_id=str(uuid.uuid4()),
                    role_id=sample_role,
                    company_id=sample_company_id,
                    is_active=(i < 3),
                )
                db.session.add(user_role)
            db.session.commit()

            # Count active users
            count_active = UserRole.count_users_by_role(
                sample_role, sample_company_id, is_active=True
            )
            assert count_active == 3

            # Count all users
            count_all = UserRole.count_users_by_role(sample_role, sample_company_id)
            assert count_all == 4

    def test_user_role_is_expired_no_expiration(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test is_expired returns False when no expiration is set."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()

            assert user_role.is_expired() is False

    def test_user_role_is_expired_future(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test is_expired returns False for future expiration."""
        future_date = datetime.now(UTC) + timedelta(days=30)

        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                expires_at=future_date,
            )
            db.session.add(user_role)
            db.session.commit()

            assert user_role.is_expired() is False

    def test_user_role_is_expired_past(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test is_expired returns True for past expiration."""
        past_date = datetime.now(UTC) - timedelta(days=1)

        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                expires_at=past_date,
            )
            db.session.add(user_role)
            db.session.commit()

            assert user_role.is_expired() is True

    def test_user_role_to_dict(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test to_dict method."""
        project_id = uuid.uuid4()
        granted_by = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=30)

        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
                project_id=str(project_id),
                scope_type="hierarchical",
                granted_by=str(granted_by),
                expires_at=expires_at,
            )
            db.session.add(user_role)
            db.session.commit()

            result = user_role.to_dict()

            assert result["id"] == user_role.id
            assert result["user_id"] == sample_user_id
            assert result["role_id"] == sample_role
            assert result["company_id"] == sample_company_id
            assert result["project_id"] == project_id
            assert result["scope_type"] == "hierarchical"
            assert result["granted_by"] == granted_by
            assert result["is_active"] is True
            assert "granted_at" in result
            assert "expires_at" in result
            assert "created_at" in result
            assert "updated_at" in result

    def test_user_role_timestamps(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test automatic timestamp creation and update."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()

            assert isinstance(user_role.created_at, datetime)
            assert isinstance(user_role.updated_at, datetime)
            assert user_role.created_at <= user_role.updated_at

    def test_user_role_relationship_to_role(
        self, app, sample_user_id, sample_company_id, sample_role
    ):
        """Test relationship to Role model."""
        with app.app_context():
            user_role = UserRole(
                user_id=sample_user_id,
                role_id=sample_role,
                company_id=sample_company_id,
            )
            db.session.add(user_role)
            db.session.commit()

            # Access role through relationship
            assert user_role.role is not None
            assert user_role.role.id == sample_role
            assert user_role.role.name == "test_role"
