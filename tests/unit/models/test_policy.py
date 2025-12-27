# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Policy model.

Tests all operations, UUID handling, uniqueness constraints, relationships,
and query methods of the Policy model.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.db import db
from app.models.permission import Permission
from app.models.policy import Policy


@pytest.fixture
def sample_company_id():
    """Return a sample company UUID."""
    return uuid.uuid4()


class TestPolicyModel:
    """Test suite for Policy model."""

    def test_policy_has_uuid_id(self, app, sample_company_id):
        """Test Policy model has UUID as primary key."""
        with app.app_context():
            policy = Policy(
                name="file_reader",
                display_name="File Reader",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            assert policy.id is not None
            assert isinstance(policy.id, uuid.UUID)

    def test_policy_repr(self, app, sample_company_id):
        """Test Policy __repr__ returns correct string."""
        with app.app_context():
            policy = Policy(
                name="admin_policy",
                display_name="Admin Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            repr_str = repr(policy)
            assert "admin_policy" in repr_str
            assert str(sample_company_id) in repr_str
            assert str(policy.id) in repr_str

    def test_policy_creation_with_all_fields(self, app, sample_company_id):
        """Test creating policy with all fields."""
        with app.app_context():
            policy = Policy(
                name="developer_access",
                display_name="Developer Access",
                description="Standard developer permissions",
                company_id=sample_company_id,
                priority=10,
                is_active=True,
            )
            db.session.add(policy)
            db.session.commit()

            assert policy.name == "developer_access"
            assert policy.display_name == "Developer Access"
            assert policy.description == "Standard developer permissions"
            assert policy.company_id == sample_company_id
            assert policy.priority == 10
            assert policy.is_active is True
            assert isinstance(policy.created_at, datetime)
            assert isinstance(policy.updated_at, datetime)

    def test_policy_creation_with_defaults(self, app, sample_company_id):
        """Test creating policy with default values."""
        with app.app_context():
            policy = Policy(
                name="basic_policy",
                display_name="Basic Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            assert policy.name == "basic_policy"
            assert policy.description is None
            assert policy.priority == 0
            assert policy.is_active is True

    def test_policy_name_uniqueness_per_company(self, app, sample_company_id):
        """Test that policy name must be unique per company."""
        with app.app_context():
            # Create first policy
            policy1 = Policy(
                name="shared_policy",
                display_name="Shared Policy 1",
                company_id=sample_company_id,
            )
            db.session.add(policy1)
            db.session.commit()

            # Try to create duplicate in same company
            policy2 = Policy(
                name="shared_policy",  # Same name
                display_name="Shared Policy 2",
                company_id=sample_company_id,  # Same company
            )
            db.session.add(policy2)

            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_policy_name_can_be_same_in_different_companies(self, app):
        """Test that policy name can be same across different companies."""
        with app.app_context():
            company_id_1 = uuid.uuid4()
            company_id_2 = uuid.uuid4()

            # Create policy in company 1
            policy1 = Policy(
                name="shared_policy",
                display_name="Shared Policy 1",
                company_id=company_id_1,
            )
            db.session.add(policy1)
            db.session.commit()

            # Create policy with same name in company 2
            policy2 = Policy(
                name="shared_policy",  # Same name
                display_name="Shared Policy 2",
                company_id=company_id_2,  # Different company
            )
            db.session.add(policy2)
            db.session.commit()

            # Both should exist
            assert policy1.id != policy2.id
            assert policy1.company_id != policy2.company_id

    def test_policy_get_all(self, app, sample_company_id):
        """Test Policy.get_all() returns all policies for a company."""
        with app.app_context():
            # Create multiple policies for same company
            policies = [
                Policy(
                    name="policy_1",
                    display_name="Policy 1",
                    company_id=sample_company_id,
                ),
                Policy(
                    name="policy_2",
                    display_name="Policy 2",
                    company_id=sample_company_id,
                ),
                Policy(
                    name="policy_3",
                    display_name="Policy 3",
                    company_id=sample_company_id,
                ),
            ]
            for policy in policies:
                db.session.add(policy)
            db.session.commit()

            # Get all
            result = Policy.get_all(company_id=sample_company_id)
            assert len(result) == 3

    def test_policy_get_all_empty(self, app, sample_company_id):
        """Test Policy.get_all() returns empty list when no policies."""
        with app.app_context():
            result = Policy.get_all(company_id=sample_company_id)
            assert result == []

    def test_policy_get_all_with_pagination(self, app, sample_company_id):
        """Test Policy.get_all() with limit and offset."""
        with app.app_context():
            # Create 5 policies
            for i in range(5):
                policy = Policy(
                    name=f"policy_{i}",
                    display_name=f"Policy {i}",
                    company_id=sample_company_id,
                )
                db.session.add(policy)
            db.session.commit()

            # Get first 2
            result = Policy.get_all(company_id=sample_company_id, limit=2, offset=0)
            assert len(result) == 2

            # Get next 2
            result = Policy.get_all(company_id=sample_company_id, limit=2, offset=2)
            assert len(result) == 2

    def test_policy_get_all_filters_by_is_active(self, app, sample_company_id):
        """Test Policy.get_all() filters by is_active."""
        with app.app_context():
            # Create active and inactive policies
            active_policy = Policy(
                name="active_policy",
                display_name="Active Policy",
                company_id=sample_company_id,
                is_active=True,
            )
            inactive_policy = Policy(
                name="inactive_policy",
                display_name="Inactive Policy",
                company_id=sample_company_id,
                is_active=False,
            )
            db.session.add(active_policy)
            db.session.add(inactive_policy)
            db.session.commit()

            # Get only active
            result = Policy.get_all(company_id=sample_company_id, is_active=True)
            assert len(result) == 1
            assert result[0].name == "active_policy"

            # Get only inactive
            result = Policy.get_all(company_id=sample_company_id, is_active=False)
            assert len(result) == 1
            assert result[0].name == "inactive_policy"

    def test_policy_get_by_id(self, app, sample_company_id):
        """Test Policy.get_by_id() retrieves policy by ID."""
        with app.app_context():
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()
            policy_id = str(policy.id)

            # Retrieve by ID
            result = Policy.get_by_id(policy_id, sample_company_id)
            assert result is not None
            assert result.name == "test_policy"

    def test_policy_get_by_id_not_found(self, app, sample_company_id):
        """Test Policy.get_by_id() returns None for non-existent ID."""
        with app.app_context():
            result = Policy.get_by_id(str(uuid.uuid4()), sample_company_id)
            assert result is None

    def test_policy_get_by_id_wrong_company(self, session):
        """Test Policy.get_by_id() returns None for wrong company."""
        company_id_1 = uuid.uuid4()
        company_id_2 = uuid.uuid4()

        # Create policy for company 1
        policy = Policy(
            name="test_policy",
            display_name="Test Policy",
            company_id=company_id_1,
        )
        session.add(policy)
        session.commit()
        policy_id = policy.id

        # Try to retrieve with company 2
        result = Policy.get_by_id(policy_id, company_id_2)
        assert result is None

    def test_policy_get_by_name(self, app, sample_company_id):
        """Test Policy.get_by_name() retrieves policy by name."""
        with app.app_context():
            policy = Policy(
                name="named_policy",
                display_name="Named Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            # Retrieve by name
            result = Policy.get_by_name("named_policy", sample_company_id)
            assert result is not None
            assert result.display_name == "Named Policy"

    def test_policy_get_by_name_not_found(self, app, sample_company_id):
        """Test Policy.get_by_name() returns None for non-existent name."""
        with app.app_context():
            result = Policy.get_by_name("nonexistent", sample_company_id)
            assert result is None

    def test_policy_count_by_company(self, app, sample_company_id):
        """Test Policy.count_by_company() returns correct count."""
        with app.app_context():
            # Create 3 policies
            for i in range(3):
                policy = Policy(
                    name=f"policy_{i}",
                    display_name=f"Policy {i}",
                    company_id=sample_company_id,
                )
                db.session.add(policy)
            db.session.commit()

            count = Policy.count_by_company(sample_company_id)
            assert count == 3

    def test_policy_count_by_company_filters_by_is_active(self, app, sample_company_id):
        """Test Policy.count_by_company() filters by is_active."""
        with app.app_context():
            # Create 2 active and 1 inactive
            for i in range(2):
                policy = Policy(
                    name=f"active_{i}",
                    display_name=f"Active {i}",
                    company_id=sample_company_id,
                    is_active=True,
                )
                db.session.add(policy)

            inactive = Policy(
                name="inactive",
                display_name="Inactive",
                company_id=sample_company_id,
                is_active=False,
            )
            db.session.add(inactive)
            db.session.commit()

            # Count active only
            count = Policy.count_by_company(sample_company_id, is_active=True)
            assert count == 2

            # Count inactive only
            count = Policy.count_by_company(sample_company_id, is_active=False)
            assert count == 1

    def test_policy_attach_permission(self, session, sample_company_id):
        """Test Policy.attach_permission() adds a permission."""
        # Create permission
        permission = Permission(
            name="storage:files:READ",
            service="storage",
            resource_name="files",
            operation="READ",
        )
        session.add(permission)
        session.commit()

        policy = Policy(
            name="test_policy",
            display_name="Test Policy",
            company_id=sample_company_id,
        )
        session.add(policy)
        session.commit()

        # Attach permission
        policy.attach_permission(str(permission.id))
        session.commit()

        # Refresh policy to reload permissions
        session.refresh(policy)

        # Verify attachment
        assert len(policy.permissions) == 1
        assert policy.permissions[0].id == permission.id

    def test_policy_attach_permission_idempotent(self, app, sample_company_id):
        """Test Policy.attach_permission() is idempotent."""
        with app.app_context():
            # Create permission
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.flush()

            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.flush()

            # Attach permission twice
            policy.attach_permission(str(permission.id))
            db.session.commit()
            policy.attach_permission(str(permission.id))
            db.session.commit()

            # Should only be attached once
            assert len(policy.permissions) == 1

    def test_policy_detach_permission(self, app, sample_company_id):
        """Test Policy.detach_permission() removes a permission."""
        with app.app_context():
            # Create permission
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.flush()

            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.flush()

            # Attach and then detach
            policy.attach_permission(str(permission.id))
            db.session.commit()
            assert len(policy.permissions) == 1

            result = policy.detach_permission(str(permission.id))
            db.session.commit()

            assert result is True
            assert len(policy.permissions) == 0

    def test_policy_detach_permission_not_attached(self, app, sample_company_id):
        """Test Policy.detach_permission() returns False when permission not attached."""
        with app.app_context():
            # Create permission
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.flush()

            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            # Try to detach a permission that's not attached
            result = policy.detach_permission(str(permission.id))
            assert result is False

    def test_policy_get_permissions_count(self, app, sample_company_id):
        """Test Policy.get_permissions_count() returns correct count."""
        with app.app_context():
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)

            # Create and attach 3 permissions
            for i in range(3):
                permission = Permission(
                    name=f"service:resource_{i}:READ",
                    service="service",
                    resource_name=f"resource_{i}",
                    operation="READ",
                )
                db.session.add(permission)
                db.session.flush()
                policy.attach_permission(str(permission.id))

            db.session.commit()

            assert policy.get_permissions_count() == 3

    def test_policy_to_dict(self, app, sample_company_id):
        """Test Policy.to_dict() returns correct dictionary."""
        with app.app_context():
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                description="Test description",
                company_id=sample_company_id,
                priority=5,
                is_active=True,
            )
            db.session.add(policy)
            db.session.commit()

            result = policy.to_dict()

            assert result["id"] == str(policy.id)
            assert result["name"] == "test_policy"
            assert result["display_name"] == "Test Policy"
            assert result["description"] == "Test description"
            assert result["company_id"] == str(sample_company_id)
            assert result["priority"] == 5
            assert result["is_active"] is True
            assert "created_at" in result
            assert "updated_at" in result
            assert "permissions_count" in result
            assert result["permissions_count"] == 0

    def test_policy_to_dict_without_permissions_count(self, app, sample_company_id):
        """Test Policy.to_dict() can exclude permissions_count."""
        with app.app_context():
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            result = policy.to_dict(include_permissions_count=False)

            assert "permissions_count" not in result

    def test_policy_timestamps(self, app, sample_company_id):
        """Test Policy has valid timestamps."""
        with app.app_context():
            policy = Policy(
                name="test_policy",
                display_name="Test Policy",
                company_id=sample_company_id,
            )
            db.session.add(policy)
            db.session.commit()

            assert isinstance(policy.created_at, datetime)
            assert isinstance(policy.updated_at, datetime)
            assert policy.created_at <= policy.updated_at
