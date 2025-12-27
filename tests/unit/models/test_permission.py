# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for Permission model.

Tests all operations, UUID handling, uniqueness constraints, and query
methods of the Permission model.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.db import db
from app.models.permission import Permission


class TestPermissionModel:
    """Test suite for Permission model."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app):
        """Setup and teardown for each test."""
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def test_permission_has_uuid_id(self, app):
        """Test Permission model has UUID as primary key."""
        with app.app_context():
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.commit()

            assert permission.id is not None
            assert isinstance(permission.id, uuid.UUID)

    def test_permission_repr(self, app):
        """Test Permission __repr__ returns correct string."""
        with app.app_context():
            permission = Permission(
                name="storage:files:DELETE",
                service="storage",
                resource_name="files",
                operation="DELETE",
            )
            db.session.add(permission)
            db.session.commit()

            repr_str = repr(permission)
            assert "storage:files:DELETE" in repr_str
            assert str(permission.id) in repr_str

    def test_permission_creation_with_all_fields(self, app):
        """Test creating permission with all fields."""
        with app.app_context():
            permission = Permission(
                name="identity:users:CREATE",
                service="identity",
                resource_name="users",
                operation="CREATE",
                description="Create new users in identity service",
            )
            db.session.add(permission)
            db.session.commit()

            assert permission.name == "identity:users:CREATE"
            assert permission.service == "identity"
            assert permission.resource_name == "users"
            assert permission.operation == "CREATE"
            assert permission.description == "Create new users in identity service"
            assert isinstance(permission.created_at, datetime)
            assert isinstance(permission.updated_at, datetime)

    def test_permission_creation_without_description(self, app):
        """Test creating permission without description."""
        with app.app_context():
            permission = Permission(
                name="storage:files:LIST",
                service="storage",
                resource_name="files",
                operation="LIST",
            )
            db.session.add(permission)
            db.session.commit()

            assert permission.name == "storage:files:LIST"
            assert permission.description is None

    def test_permission_name_uniqueness(self, app):
        """Test that permission name must be unique."""
        with app.app_context():
            # Create first permission
            permission1 = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission1)
            db.session.commit()

            # Try to create duplicate
            permission2 = Permission(
                name="storage:files:READ",  # Same name
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission2)

            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_permission_get_all(self, app):
        """Test Permission.get_all() returns all records."""
        with app.app_context():
            # Create multiple permissions
            perms = [
                Permission(
                    name="storage:files:READ",
                    service="storage",
                    resource_name="files",
                    operation="READ",
                ),
                Permission(
                    name="storage:files:CREATE",
                    service="storage",
                    resource_name="files",
                    operation="CREATE",
                ),
                Permission(
                    name="identity:users:DELETE",
                    service="identity",
                    resource_name="users",
                    operation="DELETE",
                ),
            ]
            for perm in perms:
                db.session.add(perm)
            db.session.commit()

            all_permissions = Permission.get_all()
            assert len(all_permissions) == 3

            names = [p.name for p in all_permissions]
            assert "storage:files:READ" in names
            assert "storage:files:CREATE" in names
            assert "identity:users:DELETE" in names

    def test_permission_get_all_empty(self, app):
        """Test Permission.get_all() returns empty list when no records."""
        with app.app_context():
            all_permissions = Permission.get_all()
            assert len(all_permissions) == 0

    def test_permission_get_all_with_pagination(self, app):
        """Test Permission.get_all() with limit and offset."""
        with app.app_context():
            # Create 10 permissions
            for i in range(10):
                perm = Permission(
                    name=f"service{i}:resource:READ",
                    service=f"service{i}",
                    resource_name="resource",
                    operation="READ",
                )
                db.session.add(perm)
            db.session.commit()

            # Test limit
            limited = Permission.get_all(limit=3)
            assert len(limited) == 3

            # Test offset
            offset_results = Permission.get_all(limit=3, offset=5)
            assert len(offset_results) == 3

            # Verify different results
            assert limited[0].name != offset_results[0].name

    def test_permission_get_by_name(self, app):
        """Test Permission.get_by_name()."""
        with app.app_context():
            # Create permissions
            perm1 = Permission(
                name="storage:files:UPDATE",
                service="storage",
                resource_name="files",
                operation="UPDATE",
            )
            perm2 = Permission(
                name="identity:users:READ",
                service="identity",
                resource_name="users",
                operation="READ",
            )
            db.session.add_all([perm1, perm2])
            db.session.commit()

            # Find by name
            found = Permission.get_by_name("storage:files:UPDATE")
            assert found is not None
            assert found.name == "storage:files:UPDATE"
            assert found.service == "storage"
            assert found.operation == "UPDATE"

            # Non-existent name
            not_found = Permission.get_by_name("nonexistent:resource:OPERATION")
            assert not_found is None

    def test_permission_get_by_service(self, app):
        """Test Permission.get_by_service()."""
        with app.app_context():
            # Create permissions for different services
            storage_perms = [
                Permission(
                    name="storage:files:READ",
                    service="storage",
                    resource_name="files",
                    operation="READ",
                ),
                Permission(
                    name="storage:files:CREATE",
                    service="storage",
                    resource_name="files",
                    operation="CREATE",
                ),
                Permission(
                    name="storage:buckets:LIST",
                    service="storage",
                    resource_name="buckets",
                    operation="LIST",
                ),
            ]
            identity_perms = [
                Permission(
                    name="identity:users:READ",
                    service="identity",
                    resource_name="users",
                    operation="READ",
                ),
            ]
            for perm in storage_perms + identity_perms:
                db.session.add(perm)
            db.session.commit()

            # Get storage permissions
            storage_results = Permission.get_by_service("storage")
            assert len(storage_results) == 3
            assert all(p.service == "storage" for p in storage_results)

            # Get identity permissions
            identity_results = Permission.get_by_service("identity")
            assert len(identity_results) == 1
            assert identity_results[0].service == "identity"

            # Non-existent service
            empty_results = Permission.get_by_service("nonexistent")
            assert len(empty_results) == 0

    def test_permission_get_by_service_and_resource(self, app):
        """Test Permission.get_by_service_and_resource()."""
        with app.app_context():
            # Create permissions
            perms = [
                Permission(
                    name="storage:files:READ",
                    service="storage",
                    resource_name="files",
                    operation="READ",
                ),
                Permission(
                    name="storage:files:CREATE",
                    service="storage",
                    resource_name="files",
                    operation="CREATE",
                ),
                Permission(
                    name="storage:files:DELETE",
                    service="storage",
                    resource_name="files",
                    operation="DELETE",
                ),
                Permission(
                    name="storage:buckets:LIST",
                    service="storage",
                    resource_name="buckets",
                    operation="LIST",
                ),
                Permission(
                    name="identity:users:READ",
                    service="identity",
                    resource_name="users",
                    operation="READ",
                ),
            ]
            for perm in perms:
                db.session.add(perm)
            db.session.commit()

            # Get storage:files permissions
            files_perms = Permission.get_by_service_and_resource("storage", "files")
            assert len(files_perms) == 3
            assert all(
                p.service == "storage" and p.resource_name == "files"
                for p in files_perms
            )

            operations = [p.operation for p in files_perms]
            assert "READ" in operations
            assert "CREATE" in operations
            assert "DELETE" in operations

            # Get storage:buckets permissions
            bucket_perms = Permission.get_by_service_and_resource("storage", "buckets")
            assert len(bucket_perms) == 1
            assert bucket_perms[0].operation == "LIST"

            # Non-existent combination
            empty_results = Permission.get_by_service_and_resource(
                "storage", "nonexistent"
            )
            assert len(empty_results) == 0

    def test_permission_to_dict(self, app):
        """Test Permission.to_dict() method."""
        with app.app_context():
            permission = Permission(
                name="project:diagrams:UPDATE",
                service="project",
                resource_name="diagrams",
                operation="UPDATE",
                description="Update project diagrams",
            )
            db.session.add(permission)
            db.session.commit()

            result = permission.to_dict()

            assert isinstance(result, dict)
            assert result["name"] == "project:diagrams:UPDATE"
            assert result["service"] == "project"
            assert result["resource_name"] == "diagrams"
            assert result["operation"] == "UPDATE"
            assert result["description"] == "Update project diagrams"
            assert "id" in result
            assert "created_at" in result
            assert "updated_at" in result

            # Verify UUID is string
            assert isinstance(result["id"], str)
            uuid.UUID(result["id"])  # Should not raise

    def test_permission_to_dict_without_description(self, app):
        """Test Permission.to_dict() when description is None."""
        with app.app_context():
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.commit()

            result = permission.to_dict()
            assert result["description"] is None

    def test_permission_timestamps(self, app):
        """Test that created_at and updated_at are set correctly."""
        with app.app_context():
            permission = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
            )
            db.session.add(permission)
            db.session.commit()

            assert permission.created_at is not None
            assert permission.updated_at is not None
            assert isinstance(permission.created_at, datetime)
            assert isinstance(permission.updated_at, datetime)

            # They should be very close in time
            time_diff = (permission.updated_at - permission.created_at).total_seconds()
            assert abs(time_diff) < 1  # Less than 1 second difference
