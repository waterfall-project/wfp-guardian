# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Permission seeder service.

This module provides functionality to seed permissions from the permissions.json
file into the database. It reads the grouped permission structure and creates
individual permission entries for each service:resource:operation combination.
"""

import json
from pathlib import Path

from flask import current_app

from app.models.db import db
from app.models.permission import Permission


class PermissionSeeder:
    """Service to seed permissions from JSON file to database."""

    def __init__(self, permissions_file: Path | None = None):
        """Initialize the PermissionSeeder.

        Args:
            permissions_file: Path to permissions.json. If None, uses default location.
        """
        if permissions_file is None:
            app_dir = Path(__file__).parent.parent
            permissions_file = app_dir / "data" / "permissions.json"

        self.permissions_file = permissions_file

    def load_permissions(self) -> list[dict]:
        """Load and expand permissions from JSON file.

        Reads the grouped format and expands each resource/operation
        into individual permission dictionaries.

        Returns:
            List of permission dictionaries with keys: name, service,
            resource_name, operation, description.

        Raises:
            FileNotFoundError: If permissions.json doesn't exist.
            ValueError: If JSON format is invalid.
        """
        if not self.permissions_file.exists():
            raise FileNotFoundError(
                f"Permissions file not found: {self.permissions_file}"
            )

        try:
            with self.permissions_file.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in permissions file: {e}") from e

        if not isinstance(data, list):
            raise ValueError(
                "Permissions file must contain an array of service objects"
            )

        # Expand grouped format into individual permissions
        permissions = []
        for service_entry in data:
            service = service_entry.get("service")
            if not service:
                current_app.logger.warning(
                    f"Skipping service entry without 'service' field: {service_entry}"
                )
                continue

            for resource in service_entry.get("resources", []):
                resource_name = resource.get("name")
                operations = resource.get("operations", [])
                description_template = resource.get("description", "")

                if not resource_name:
                    current_app.logger.warning(
                        f"Skipping resource without 'name' in service {service}"
                    )
                    continue

                # Create one permission per operation
                for operation in operations:
                    permission_name = f"{service}:{resource_name}:{operation}"
                    # Customize description with operation
                    description = f"{description_template} - {operation}"

                    permissions.append(
                        {
                            "name": permission_name,
                            "service": service,
                            "resource_name": resource_name,
                            "operation": operation,
                            "description": description,
                        }
                    )

        return permissions

    def _needs_update(self, existing: Permission, perm_data: dict) -> bool:
        """Check if an existing permission needs to be updated.

        Args:
            existing: Existing Permission object from database
            perm_data: New permission data dictionary

        Returns:
            True if any fields have changed, False otherwise
        """
        has_changes: bool = (
            existing.service != perm_data["service"]
            or existing.resource_name != perm_data["resource_name"]
            or existing.operation != perm_data["operation"]
            or existing.description != perm_data["description"]
        )
        return has_changes

    def _update_permission(
        self, existing: Permission, perm_data: dict, dry_run: bool
    ) -> None:
        """Update an existing permission with new data.

        Args:
            existing: Existing Permission object to update
            perm_data: New permission data dictionary
            dry_run: If True, skip actual update
        """
        if not dry_run:
            existing.service = perm_data["service"]
            existing.resource_name = perm_data["resource_name"]
            existing.operation = perm_data["operation"]
            existing.description = perm_data["description"]

        action = "[DRY RUN] Would update" if dry_run else "Updated"
        current_app.logger.info(f"{action} permission: {perm_data['name']}")

    def _create_permission(self, perm_data: dict, dry_run: bool) -> None:
        """Create a new permission.

        Args:
            perm_data: Permission data dictionary
            dry_run: If True, skip actual creation
        """
        if not dry_run:
            permission = Permission(**perm_data)
            db.session.add(permission)

        action = "[DRY RUN] Would create" if dry_run else "Created"
        current_app.logger.info(f"{action} permission: {perm_data['name']}")

    def seed_permissions(self, dry_run: bool = False) -> dict[str, int]:
        """Seed permissions into the database.

        Creates new permissions and updates existing ones. Does not delete
        permissions that exist in DB but not in the file.

        Args:
            dry_run: If True, only reports what would be done without making changes.

        Returns:
            Dictionary with counts: {"created": int, "updated": int, "unchanged": int}
        """
        permissions_data = self.load_permissions()

        created = 0
        updated = 0
        unchanged = 0

        for perm_data in permissions_data:
            existing = Permission.get_by_name(perm_data["name"])

            if existing:
                if self._needs_update(existing, perm_data):
                    self._update_permission(existing, perm_data, dry_run)
                    updated += 1
                else:
                    unchanged += 1
            else:
                self._create_permission(perm_data, dry_run)
                created += 1

        if not dry_run:
            db.session.commit()
            current_app.logger.info(
                f"Permission seeding completed: {created} created, {updated} updated, {unchanged} unchanged"
            )
        else:
            current_app.logger.info(
                f"[DRY RUN] Would have: {created} created, {updated} updated, {unchanged} unchanged"
            )

        return {"created": created, "updated": updated, "unchanged": unchanged}


def seed_permissions_on_startup() -> None:
    """Seed permissions at application startup.

    This function is called during Flask application initialization to ensure
    all permissions from permissions.json are available in the database.
    """
    try:
        seeder = PermissionSeeder()
        results = seeder.seed_permissions()
        current_app.logger.info(
            f"✅ Permissions seeded: {results['created']} created, "
            f"{results['updated']} updated, {results['unchanged']} unchanged"
        )
    except FileNotFoundError as e:
        current_app.logger.warning(f"⚠️  {e}")
        current_app.logger.warning("Skipping permission seeding - file not found")
    except Exception as e:
        current_app.logger.error(f"❌ Error seeding permissions: {e}")
        # Don't raise - allow app to start even if seeding fails
