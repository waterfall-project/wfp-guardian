# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Role model.

Tests all operations, UUID handling, uniqueness constraints, relationships,
and query methods of the Role model.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.db import db
from app.models.policy import Policy
from app.models.role import Role


@pytest.fixture
def sample_company_id():
    """Return a sample company UUID."""
    return uuid.uuid4()


class TestRoleModel:
    """Test suite for Role model."""

    def test_role_has_uuid_id(self, app, sample_company_id):
        """Test Role model has UUID as primary key."""
        with app.app_context():
            role = Role(
                name="file_reader",
                display_name="File Reader",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            assert role.id is not None
            assert isinstance(role.id, uuid.UUID)

    def test_role_repr(self, app, sample_company_id):
        """Test Role __repr__ returns correct string."""
        with app.app_context():
            role = Role(
                name="admin_role",
                display_name="Admin Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            repr_str = repr(role)
            assert "admin_role" in repr_str
            assert str(sample_company_id) in repr_str
            assert str(role.id) in repr_str

    def test_role_creation_with_all_fields(self, app, sample_company_id):
        """Test creating role with all fields."""
        with app.app_context():
            role = Role(
                name="developer_access",
                display_name="Developer Access",
                description="Standard developer policies",
                company_id=sample_company_id,
                is_active=True,
            )
            db.session.add(role)
            db.session.commit()

            assert role.name == "developer_access"
            assert role.display_name == "Developer Access"
            assert role.description == "Standard developer policies"
            assert role.company_id == sample_company_id
            assert role.is_active is True
            assert isinstance(role.created_at, datetime)
            assert isinstance(role.updated_at, datetime)

    def test_role_creation_with_defaults(self, app, sample_company_id):
        """Test creating role with default values."""
        with app.app_context():
            role = Role(
                name="basic_role",
                display_name="Basic Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            assert role.name == "basic_role"
            assert role.description is None
            assert role.is_active is True

    def test_role_name_uniqueness_per_company(self, app, sample_company_id):
        """Test that role name must be unique per company."""
        with app.app_context():
            # Create first role
            role1 = Role(
                name="shared_role",
                display_name="Shared Role 1",
                company_id=sample_company_id,
            )
            db.session.add(role1)
            db.session.commit()

            # Try to create duplicate in same company
            role2 = Role(
                name="shared_role",  # Same name
                display_name="Shared Role 2",
                company_id=sample_company_id,  # Same company
            )
            db.session.add(role2)

            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_role_name_can_be_same_in_different_companies(self, app):
        """Test that role name can be same across different companies."""
        with app.app_context():
            company_id_1 = uuid.uuid4()
            company_id_2 = uuid.uuid4()

            # Create role in company 1
            role1 = Role(
                name="shared_role",
                display_name="Shared Role 1",
                company_id=company_id_1,
            )
            db.session.add(role1)
            db.session.commit()

            # Create role with same name in company 2
            role2 = Role(
                name="shared_role",  # Same name
                display_name="Shared Role 2",
                company_id=company_id_2,  # Different company
            )
            db.session.add(role2)
            db.session.commit()

            # Both should exist
            assert role1.id != role2.id
            assert role1.company_id != role2.company_id

    def test_role_get_all(self, app, sample_company_id):
        """Test Role.get_all() returns all policies for a company."""
        with app.app_context():
            # Create multiple policies for same company
            policies = [
                Role(
                    name="role_1",
                    display_name="Role 1",
                    company_id=sample_company_id,
                ),
                Role(
                    name="role_2",
                    display_name="Role 2",
                    company_id=sample_company_id,
                ),
                Role(
                    name="role_3",
                    display_name="Role 3",
                    company_id=sample_company_id,
                ),
            ]
            for role in policies:
                db.session.add(role)
            db.session.commit()

            # Get all
            result = Role.get_all(company_id=sample_company_id)
            assert len(result) == 3

    def test_role_get_all_empty(self, app, sample_company_id):
        """Test Role.get_all() returns empty list when no policies."""
        with app.app_context():
            result = Role.get_all(company_id=sample_company_id)
            assert result == []

    def test_role_get_all_with_pagination(self, app, sample_company_id):
        """Test Role.get_all() with limit and offset."""
        with app.app_context():
            # Create 5 policies
            for i in range(5):
                role = Role(
                    name=f"role_{i}",
                    display_name=f"Role {i}",
                    company_id=sample_company_id,
                )
                db.session.add(role)
            db.session.commit()

            # Get first 2
            result = Role.get_all(company_id=sample_company_id, limit=2, offset=0)
            assert len(result) == 2

            # Get next 2
            result = Role.get_all(company_id=sample_company_id, limit=2, offset=2)
            assert len(result) == 2

    def test_role_get_all_filters_by_is_active(self, app, sample_company_id):
        """Test Role.get_all() filters by is_active."""
        with app.app_context():
            # Create active and inactive policies
            active_role = Role(
                name="active_role",
                display_name="Active Role",
                company_id=sample_company_id,
                is_active=True,
            )
            inactive_role = Role(
                name="inactive_role",
                display_name="Inactive Role",
                company_id=sample_company_id,
                is_active=False,
            )
            db.session.add(active_role)
            db.session.add(inactive_role)
            db.session.commit()

            # Get only active
            result = Role.get_all(company_id=sample_company_id, is_active=True)
            assert len(result) == 1
            assert result[0].name == "active_role"

            # Get only inactive
            result = Role.get_all(company_id=sample_company_id, is_active=False)
            assert len(result) == 1
            assert result[0].name == "inactive_role"

    def test_role_get_by_id(self, app, sample_company_id):
        """Test Role.get_by_id() retrieves role by ID."""
        with app.app_context():
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()
            role_id = str(role.id)

            # Retrieve by ID
            result = Role.get_by_id(role_id, sample_company_id)
            assert result is not None
            assert result.name == "test_role"

    def test_role_get_by_id_not_found(self, app, sample_company_id):
        """Test Role.get_by_id() returns None for non-existent ID."""
        with app.app_context():
            result = Role.get_by_id(str(uuid.uuid4()), sample_company_id)
            assert result is None

    def test_role_get_by_id_wrong_company(self, session):
        """Test Role.get_by_id() returns None for wrong company."""
        company_id_1 = uuid.uuid4()
        company_id_2 = uuid.uuid4()

        # Create role for company 1
        role = Role(
            name="test_role",
            display_name="Test Role",
            company_id=company_id_1,
        )
        session.add(role)
        session.commit()
        role_id = role.id

        # Try to retrieve with company 2
        result = Role.get_by_id(role_id, company_id_2)
        assert result is None

    def test_role_get_by_name(self, app, sample_company_id):
        """Test Role.get_by_name() retrieves role by name."""
        with app.app_context():
            role = Role(
                name="named_role",
                display_name="Named Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            # Retrieve by name
            result = Role.get_by_name("named_role", sample_company_id)
            assert result is not None
            assert result.display_name == "Named Role"

    def test_role_get_by_name_not_found(self, app, sample_company_id):
        """Test Role.get_by_name() returns None for non-existent name."""
        with app.app_context():
            result = Role.get_by_name("nonexistent", sample_company_id)
            assert result is None

    def test_role_count_by_company(self, app, sample_company_id):
        """Test Role.count_by_company() returns correct count."""
        with app.app_context():
            # Create 3 policies
            for i in range(3):
                role = Role(
                    name=f"role_{i}",
                    display_name=f"Role {i}",
                    company_id=sample_company_id,
                )
                db.session.add(role)
            db.session.commit()

            count = Role.count_by_company(sample_company_id)
            assert count == 3

    def test_role_count_by_company_filters_by_is_active(self, app, sample_company_id):
        """Test Role.count_by_company() filters by is_active."""
        with app.app_context():
            # Create 2 active and 1 inactive
            for i in range(2):
                role = Role(
                    name=f"active_{i}",
                    display_name=f"Active {i}",
                    company_id=sample_company_id,
                    is_active=True,
                )
                db.session.add(role)

            inactive = Role(
                name="inactive",
                display_name="Inactive",
                company_id=sample_company_id,
                is_active=False,
            )
            db.session.add(inactive)
            db.session.commit()

            # Count active only
            count = Role.count_by_company(sample_company_id, is_active=True)
            assert count == 2

            # Count inactive only
            count = Role.count_by_company(sample_company_id, is_active=False)
            assert count == 1

    def test_role_attach_policy(self, session, sample_company_id):
        """Test Role.attach_policy() adds a policy."""
        # Create policy
        policy = Policy(
            name="test_policy",
            display_name="Test Policy",
            company_id=sample_company_id,
        )
        session.add(policy)
        session.commit()

        role = Role(
            name="test_role",
            display_name="Test Role",
            company_id=sample_company_id,
        )
        session.add(role)
        session.commit()

        # Attach policy
        role.attach_policy(str(policy.id))
        session.commit()

        # Refresh role to reload policies
        session.refresh(role)

        # Verify attachment
        assert len(role.policies) == 1
        assert role.policies[0].id == policy.id

    def test_role_attach_policy_idempotent(self, app, sample_company_id):
        """Test Role.attach_policy() is idempotent."""
        with app.app_context():
            # Create policy
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.flush()

            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.flush()

            # Attach policy twice
            role.attach_policy(str(policy.id))
            db.session.commit()
            role.attach_policy(str(policy.id))
            db.session.commit()

            # Should only be attached once
            assert len(role.policies) == 1

    def test_role_detach_policy(self, app, sample_company_id):
        """Test Role.detach_policy() removes a policy."""
        with app.app_context():
            # Create policy
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.flush()

            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.flush()

            # Attach and then detach
            role.attach_policy(str(policy.id))
            db.session.commit()
            assert len(role.policies) == 1

            result = role.detach_policy(str(policy.id))
            db.session.commit()

            assert result is True
            assert len(role.policies) == 0

    def test_role_detach_policy_not_attached(self, app, sample_company_id):
        """Test Role.detach_policy() returns False when policy not attached."""
        with app.app_context():
            # Create policy
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.flush()

            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            # Try to detach a policy that's not attached
            result = role.detach_policy(str(policy.id))
            assert result is False

    def test_role_get_policies_count(self, app, sample_company_id):
        """Test Role.get_policies_count() returns correct count."""
        with app.app_context():
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)

            # Create and attach 3 policies
            for i in range(3):
                policy = Policy(
                    name=f"policy_{i}",
                    display_name=f"Policy {i}",
                    company_id=sample_company_id,
                )
                db.session.add(policy)
                db.session.flush()
                role.attach_policy(str(policy.id))

            db.session.commit()

            assert role.get_policies_count() == 3

    def test_role_to_dict(self, app, sample_company_id):
        """Test Role.to_dict() returns correct dictionary."""
        with app.app_context():
            role = Role(
                name="test_role",
                display_name="Test Role",
                description="Test description",
                company_id=sample_company_id,
                is_active=True,
            )
            db.session.add(role)
            db.session.commit()

            result = role.to_dict()

            assert result["id"] == str(role.id)
            assert result["name"] == "test_role"
            assert result["display_name"] == "Test Role"
            assert result["description"] == "Test description"
            assert result["company_id"] == str(sample_company_id)
            assert result["is_active"] is True
            assert "created_at" in result
            assert "updated_at" in result
            assert "policies_count" in result
            assert result["policies_count"] == 0

    def test_role_to_dict_without_policies_count(self, app, sample_company_id):
        """Test Role.to_dict() can exclude policies_count."""
        with app.app_context():
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            result = role.to_dict(include_policies_count=False)

            assert "policies_count" not in result

    def test_role_timestamps(self, app, sample_company_id):
        """Test Role has valid timestamps."""
        with app.app_context():
            role = Role(
                name="test_role",
                display_name="Test Role",
                company_id=sample_company_id,
            )
            db.session.add(role)
            db.session.commit()

            assert isinstance(role.created_at, datetime)
            assert isinstance(role.updated_at, datetime)
            assert role.created_at <= role.updated_at
