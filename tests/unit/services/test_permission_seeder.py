# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for PermissionSeeder service.

Tests permission loading from JSON, seeding logic, dry-run mode,
and error handling.
"""

import json
from pathlib import Path

import pytest

from app.models.db import db
from app.models.permission import Permission
from app.services.permission_seeder import PermissionSeeder


class TestPermissionSeeder:
    """Test suite for PermissionSeeder service."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self, app, tmp_path):
        """Setup and teardown for each test."""
        self.tmp_path = tmp_path
        with app.app_context():
            db.create_all()
            yield
            db.session.remove()
            db.drop_all()

    def create_permissions_json(self, data: list[dict] | dict) -> Path:
        """Helper to create a temporary permissions.json file."""
        permissions_file: Path = self.tmp_path / "permissions.json"
        with permissions_file.open("w", encoding="utf-8") as f:
            json.dump(data, f)
        return permissions_file

    def test_load_permissions_valid_format(self, app):
        """Test loading permissions from valid grouped JSON format."""
        with app.app_context():
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ", "CREATE"],
                            "description": "Storage files resource",
                        }
                    ],
                },
                {
                    "service": "identity",
                    "resources": [
                        {
                            "name": "users",
                            "operations": ["LIST"],
                            "description": "Identity users resource",
                        }
                    ],
                },
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            permissions = seeder.load_permissions()

            assert len(permissions) == 3  # 2 operations for storage + 1 for identity

            # Check first permission
            assert permissions[0]["name"] == "storage:files:READ"
            assert permissions[0]["service"] == "storage"
            assert permissions[0]["resource_name"] == "files"
            assert permissions[0]["operation"] == "READ"
            assert "Storage files resource" in permissions[0]["description"]

            # Check second permission
            assert permissions[1]["name"] == "storage:files:CREATE"
            assert permissions[1]["operation"] == "CREATE"

            # Check third permission
            assert permissions[2]["name"] == "identity:users:LIST"
            assert permissions[2]["service"] == "identity"

    def test_load_permissions_multiple_operations(self, app):
        """Test that operations are expanded correctly."""
        with app.app_context():
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": [
                                "LIST",
                                "CREATE",
                                "READ",
                                "UPDATE",
                                "DELETE",
                            ],
                            "description": "Files resource",
                        }
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            permissions = seeder.load_permissions()

            assert len(permissions) == 5
            operations = [p["operation"] for p in permissions]
            assert operations == ["LIST", "CREATE", "READ", "UPDATE", "DELETE"]

            # All should have same service and resource
            assert all(p["service"] == "storage" for p in permissions)
            assert all(p["resource_name"] == "files" for p in permissions)

    def test_load_permissions_file_not_found(self, app):
        """Test loading permissions when file doesn't exist."""
        with app.app_context():
            nonexistent_file = self.tmp_path / "nonexistent.json"
            seeder = PermissionSeeder(nonexistent_file)

            with pytest.raises(FileNotFoundError):
                seeder.load_permissions()

    def test_load_permissions_invalid_json(self, app):
        """Test loading permissions from invalid JSON."""
        with app.app_context():
            invalid_file = self.tmp_path / "invalid.json"
            invalid_file.write_text("{ invalid json }", encoding="utf-8")

            seeder = PermissionSeeder(invalid_file)

            with pytest.raises(ValueError, match="Invalid JSON"):
                seeder.load_permissions()

    def test_load_permissions_invalid_format(self, app):
        """Test loading permissions from invalid structure."""
        with app.app_context():
            # Not a list
            invalid_data: dict[str, list[dict[str, str]]] = {"permissions": []}
            permissions_file = self.create_permissions_json(invalid_data)

            seeder = PermissionSeeder(permissions_file)

            with pytest.raises(ValueError, match="must contain an array"):
                seeder.load_permissions()

    def test_load_permissions_missing_service_field(self, app):
        """Test handling of entries without service field."""
        with app.app_context():
            data: list[dict] = [
                {
                    # Missing 'service' field
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ"],
                            "description": "Test",
                        }
                    ],
                },
                {
                    "service": "identity",
                    "resources": [
                        {
                            "name": "users",
                            "operations": ["LIST"],
                            "description": "Users",
                        }
                    ],
                },
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            permissions = seeder.load_permissions()

            # Should skip the invalid entry
            assert len(permissions) == 1
            assert permissions[0]["service"] == "identity"

    def test_load_permissions_missing_resource_name(self, app):
        """Test handling of resources without name field."""
        with app.app_context():
            data: list[dict] = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            # Missing 'name' field
                            "operations": ["READ"],
                            "description": "Test",
                        },
                        {
                            "name": "valid",
                            "operations": ["CREATE"],
                            "description": "Valid resource",
                        },
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            permissions = seeder.load_permissions()

            # Should skip the invalid resource
            assert len(permissions) == 1
            assert permissions[0]["resource_name"] == "valid"

    def test_seed_permissions_create_new(self, app):
        """Test seeding new permissions into empty database."""
        with app.app_context():
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ", "CREATE"],
                            "description": "Storage files",
                        }
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            results = seeder.seed_permissions()

            assert results["created"] == 2
            assert results["updated"] == 0
            assert results["unchanged"] == 0

            # Verify in database
            all_perms = Permission.get_all()
            assert len(all_perms) == 2

            names = [p.name for p in all_perms]
            assert "storage:files:READ" in names
            assert "storage:files:CREATE" in names

    def test_seed_permissions_update_existing(self, app):
        """Test updating existing permissions."""
        with app.app_context():
            # Create initial permission
            existing = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
                description="Old description",
            )
            db.session.add(existing)
            db.session.commit()

            # Seed with updated description
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ"],
                            "description": "New description",
                        }
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            results = seeder.seed_permissions()

            assert results["created"] == 0
            assert results["updated"] == 1
            assert results["unchanged"] == 0

            # Verify description was updated
            updated = Permission.get_by_name("storage:files:READ")
            assert updated is not None
            assert "New description - READ" in updated.description

    def test_seed_permissions_unchanged(self, app):
        """Test seeding when permission already exists with same data."""
        with app.app_context():
            # Create permission
            existing = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
                description="Storage files - READ",
            )
            db.session.add(existing)
            db.session.commit()

            # Seed with same data
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ"],
                            "description": "Storage files",
                        }
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            results = seeder.seed_permissions()

            assert results["created"] == 0
            assert results["updated"] == 0
            assert results["unchanged"] == 1

    def test_seed_permissions_mixed_operations(self, app):
        """Test seeding with create, update, and unchanged."""
        with app.app_context():
            # Create one existing permission
            existing = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
                description="Storage files - READ",
            )
            db.session.add(existing)
            db.session.commit()

            # Seed with: 1 unchanged, 1 to update, 1 new
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ", "CREATE"],
                            "description": "Storage files",  # READ will be unchanged, CREATE is new
                        },
                        {
                            "name": "buckets",
                            "operations": ["LIST"],
                            "description": "Storage buckets",  # New
                        },
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            results = seeder.seed_permissions()

            assert results["created"] == 2  # CREATE and LIST
            assert results["updated"] == 0
            assert results["unchanged"] == 1  # READ

            # Verify total
            assert len(Permission.get_all()) == 3

    def test_seed_permissions_dry_run(self, app):
        """Test seeding in dry-run mode doesn't persist changes."""
        with app.app_context():
            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ", "CREATE"],
                            "description": "Storage files",
                        }
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            results = seeder.seed_permissions(dry_run=True)

            # Should report what would happen
            assert results["created"] == 2
            assert results["updated"] == 0
            assert results["unchanged"] == 0

            # But database should be empty
            all_perms = Permission.get_all()
            assert len(all_perms) == 0

    def test_seed_permissions_dry_run_with_existing(self, app):
        """Test dry-run mode with existing permissions."""
        with app.app_context():
            # Create existing permission
            existing = Permission(
                name="storage:files:READ",
                service="storage",
                resource_name="files",
                operation="READ",
                description="Old description",
            )
            db.session.add(existing)
            db.session.commit()

            data = [
                {
                    "service": "storage",
                    "resources": [
                        {
                            "name": "files",
                            "operations": ["READ", "CREATE"],
                            "description": "New description",
                        }
                    ],
                }
            ]
            permissions_file = self.create_permissions_json(data)

            seeder = PermissionSeeder(permissions_file)
            results = seeder.seed_permissions(dry_run=True)

            assert results["created"] == 1  # CREATE
            assert results["updated"] == 1  # READ with new description
            assert results["unchanged"] == 0

            # Original should be unchanged
            unchanged = Permission.get_by_name("storage:files:READ")
            assert unchanged is not None
            assert unchanged.description == "Old description"

    def test_seed_permissions_default_file_location(self, app):
        """Test that seeder uses correct default file location."""
        seeder = PermissionSeeder()

        # Should point to app/data/permissions.json
        assert seeder.permissions_file.name == "permissions.json"
        assert seeder.permissions_file.parent.name == "data"
