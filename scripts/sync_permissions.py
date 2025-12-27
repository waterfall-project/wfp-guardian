#!/usr/bin/env python3

# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""
sync_permissions.py
-------------------

Script to automatically synchronize permissions.json with decorated resources
from all microservices in the waterfall project.

This script:
1. Scans ../*/app/resources/*.py files
2. Extracts resources decorated with @access_required
3. Updates app/data/permissions.json with discovered permissions

Usage:
    python sync_permissions.py [--dry-run] [--service SERVICE_NAME]

Options:
    --dry-run       Show changes without updating permissions.json
    --service NAME  Only scan specific service (e.g., guardian, identity)
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.utils.guardian import Operation


class PermissionExtractor:
    """Extract permissions from Python resource files."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.permissions: dict[str, dict] = {}

    def find_service_directories(self, service_filter: str | None = None) -> list[Path]:
        """Find all service directories matching pattern."""
        # The script lives in `scripts/` (base_dir); climb two levels:
        # scripts/ -> wfp-guardian/ -> waterfall-project/ (repo root with all services)
        services_dir = self.base_dir.parent.parent
        service_dirs = []

        for item in services_dir.iterdir():
            if not item.is_dir():
                continue

            # Filter by service name if specified
            if service_filter and service_filter not in item.name:
                continue

            resources_dir = item / "app" / "resources"
            if resources_dir.exists():
                service_dirs.append(item)
                print(f"📁 Found service: {item.name}")

        return service_dirs

    def extract_resource_name_from_class(self, class_name: str) -> str:
        """
        Convert class name to resource name.

        Examples:
            RoleResource -> role
            UserRoleListResource -> user_role
            PolicyPermissionsResource -> policy_permissions
        """
        # Remove 'Resource' suffix
        name = re.sub(r"Resource$", "", class_name)
        name = re.sub(r"List$", "", name)
        name = re.sub(r"Detail$", "", name)

        # Convert CamelCase to snake_case
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        return name

    def _is_collection_endpoint(self, class_name: str) -> bool:
        """
        Determine if a resource class represents a collection endpoint.

        This helper is intentionally conservative and currently only treats
        classes whose name contains "List" as collection endpoints
        (e.g., RoleListResource, UserRoleListResource).

        As a result, collection endpoints that do not follow this naming
        convention will be treated as single-resource endpoints by
        extract_operation_from_method, and their GET methods will be
        mapped to READ instead of LIST.

        The heuristic can be extended in the future (e.g., by inspecting
        pluralized names or route patterns) if needed.

        Args:
            class_name: The name of the resource class to check.

        Returns:
            True if the class is considered a collection endpoint.
        """
        return "List" in class_name

    def extract_operation_from_method(
        self, method_name: str, class_name: str | None = None
    ) -> str:
        """
        Map HTTP method names to CRUD operations.

        Mapping:
            get -> READ (single) or LIST (collection)
            post -> CREATE
            put/patch -> UPDATE
            delete -> DELETE
        """
        method_map = {
            "get": "READ",  # Will be refined based on context
            "post": "CREATE",
            "put": "UPDATE",
            "patch": "UPDATE",
            "delete": "DELETE",
        }
        operation = method_map.get(method_name.lower(), method_name.upper())

        # Refine GET to LIST for collection endpoints
        if (
            operation == "READ"
            and class_name
            and self._is_collection_endpoint(class_name)
        ):
            operation = "LIST"

        return operation

    def parse_access_decorator(self, decorator_node) -> str | None:
        """Extract operation from @access_required decorator.

        Handles both formats:
        - @access_required("READ")  # String literal
        - @access_required(Operation.READ)  # Enum attribute
        """
        if isinstance(decorator_node, ast.Call) and decorator_node.args:
            arg = decorator_node.args[0]
            # Handle string literal: @access_required("READ")
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
            # Handle enum attribute: @access_required(Operation.READ)
            if (
                isinstance(arg, ast.Attribute)
                and isinstance(arg.value, ast.Name)
                and arg.value.id == "Operation"
            ):
                return arg.attr  # Returns "READ", "CREATE", etc.
        return None

    def _is_resource_class(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from Resource or BaseResource."""
        return any(
            (isinstance(base, ast.Name) and base.id in ("Resource", "BaseResource"))
            for base in node.bases
        )

    def _extract_decorator_name(self, decorator) -> str | None:
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id
        return None

    def _process_method(self, method: ast.FunctionDef, class_name: str) -> str | None:
        """Process a method and extract operation if decorated with access_required."""
        for decorator in method.decorator_list:
            decorator_name = self._extract_decorator_name(decorator)

            if decorator_name == "access_required":
                operation = self.parse_access_decorator(decorator)

                if not operation:
                    # Extract operation from method name, passing class_name for context
                    operation = self.extract_operation_from_method(
                        method.name, class_name
                    )
                else:
                    # Normalize to uppercase
                    operation = operation.upper()

                # Validate operation against Operation enum
                valid_operations = {op.value for op in Operation}
                if operation not in valid_operations:
                    print(
                        f"⚠️  Invalid operation '{operation}' in {class_name}.{method.name}"
                    )
                    return None

                return operation
        return None

    def _extract_class_permissions(
        self, node: ast.ClassDef, service_name: str, file_path: Path
    ) -> dict | None:
        """Extract permissions from a resource class."""
        if not self._is_resource_class(node):
            return None

        resource_name = self.extract_resource_name_from_class(node.name)
        operations = set()

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                operation = self._process_method(item, node.name)
                if operation:
                    operations.add(operation)

        if operations:
            # Compute a source_file relative to the repository root (two
            # levels up from scripts/). Use os.path.relpath for robustness
            # and fall back to filename only if something goes wrong to
            # avoid leaking absolute paths.
            try:
                repo_root = self.base_dir.parent.parent
                rel = os.path.relpath(file_path, start=repo_root)
            except Exception as e:
                print(
                    f"⚠️  Failed to compute relative path for {file_path}: {e}. "
                    f"Using filename only as fallback."
                )
                rel = file_path.name

            return {
                "service": service_name,
                "resource_name": resource_name,
                "operations": sorted(operations),
                "source_file": rel,
            }
        return None

    def analyze_resource_file(self, file_path: Path, service_name: str) -> list[dict]:
        """Analyze a single resource file and extract permissions."""
        permissions = []

        try:
            with file_path.open(encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    permission = self._extract_class_permissions(
                        node, service_name, file_path
                    )
                    if permission:
                        permissions.append(permission)

        except Exception as e:
            print(f"⚠️  Error parsing {file_path}: {e}")

        return permissions

    def scan_service(self, service_dir: Path) -> list[dict]:
        """Scan all resource files in a service directory."""
        service_name = service_dir.name.replace("_service", "").replace("-service", "")
        resources_dir = service_dir / "app" / "resources"
        permissions: list[dict] = []

        if not resources_dir.exists():
            return permissions

        print(f"\n🔍 Scanning {service_name} service...")

        for py_file in resources_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            print(f"   📄 {py_file.name}")
            file_permissions = self.analyze_resource_file(py_file, service_name)
            permissions.extend(file_permissions)

        return permissions

    def load_existing_permissions(self, permissions_file: Path) -> dict:
        """Load existing permissions.json."""
        if not permissions_file.exists():
            return {}

        try:
            with permissions_file.open(encoding="utf-8") as f:
                data = json.load(f)

                # Handle new grouped format: [{service, resources: [{name, operations, description}]}]
                if isinstance(data, list) and data and "resources" in data[0]:
                    # New format: grouped by service
                    permissions_dict = {}
                    for service_entry in data:
                        service = service_entry["service"]
                        for resource in service_entry.get("resources", []):
                            key = f"{service}:{resource['name']}"
                            permissions_dict[key] = {
                                "service": service,
                                "resource_name": resource["name"],
                                "operations": resource["operations"],
                                "description": resource.get("description", ""),
                            }
                    return permissions_dict

                # Handle old flat format for backward compatibility
                elif isinstance(data, list):
                    return {f"{p['service']}:{p['resource_name']}": p for p in data}
                else:
                    print("⚠️  Unknown permissions.json format")
                    return {}
        except Exception as e:
            print(f"⚠️  Error loading permissions.json: {e}")
            return {}

    def merge_permissions(
        self, existing: dict, discovered: list[dict]
    ) -> tuple[list[dict], dict]:
        """Merge discovered permissions with existing ones."""
        # First, consolidate discovered permissions (merge duplicates from multiple classes)
        consolidated: dict[str, dict] = {}
        for perm in discovered:
            key = f"{perm['service']}:{perm['resource_name']}"

            if key in consolidated:
                # Merge operations from multiple classes with same resource_name
                existing_ops = set(consolidated[key].get("operations", []))
                new_ops = set(perm.get("operations", []))
                all_ops = sorted(existing_ops | new_ops)
                consolidated[key]["operations"] = all_ops
            else:
                consolidated[key] = perm.copy()

        # Then merge consolidated discovered with existing permissions
        merged = existing.copy()

        for key, perm in consolidated.items():
            if key in merged:
                # Normalize operation case to uppercase and update operations
                existing_ops = {op.upper() for op in merged[key].get("operations", [])}
                new_ops = {op.upper() for op in perm.get("operations", [])}
                all_ops = sorted(existing_ops | new_ops)

                merged[key]["operations"] = all_ops
                merged[key]["source_file"] = perm["source_file"]
            else:
                # Add description placeholder
                perm_ops = {op.upper() for op in perm.get("operations", [])}
                perm["operations"] = sorted(perm_ops)
                perm["description"] = (
                    f"{perm['service'].capitalize()} {perm['resource_name']} resource"
                )
                merged[key] = perm

        return list(merged.values()), consolidated

    def save_permissions(self, permissions: list[dict], output_file: Path):
        """Save permissions to JSON file in grouped format."""
        # Sort by service, then resource_name
        permissions.sort(key=lambda p: (p["service"], p["resource_name"]))

        # Group by service
        services_dict: dict[str, list[dict]] = {}
        for p in permissions:
            service = p["service"]
            if service not in services_dict:
                services_dict[service] = []

            services_dict[service].append(
                {
                    "name": p["resource_name"],
                    "operations": p["operations"],
                    "description": p.get("description", ""),
                }
            )

        # Create final structure
        output_data = []
        for service in sorted(services_dict.keys()):
            output_data.append(
                {"service": service, "resources": services_dict[service]}
            )

        # Save as grouped format
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent="\t", ensure_ascii=False)
            f.write("\n")  # Add trailing newline

        total_resources = sum(len(s["resources"]) for s in output_data)
        print(
            f"\n✅ Saved {total_resources} resources across {len(output_data)} services to {output_file}"
        )

    def print_summary(self, existing: dict, consolidated: dict, merged: list[dict]):
        """Print summary of changes."""
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)

        consolidated_keys = set(consolidated.keys())
        existing_keys = set(existing.keys())

        new_perms = consolidated_keys - existing_keys
        updated_perms = consolidated_keys & existing_keys
        removed_perms = existing_keys - consolidated_keys

        print(f"\n✨ New permissions: {len(new_perms)}")
        for key in sorted(new_perms):
            print(f"   + {key}")

        print(f"\n🔄 Updated permissions: {len(updated_perms)}")
        for key in sorted(updated_perms):
            # Normalize cases for display so it matches stored normalization
            old_ops = {op.upper() for op in existing[key].get("operations", [])}
            new_ops = {op.upper() for op in consolidated[key].get("operations", [])}
            if old_ops != new_ops:
                print(f"   ~ {key}: {sorted(old_ops)} -> {sorted(new_ops)}")

        if removed_perms:
            print(f"\n⚠️  Permissions not found in code: {len(removed_perms)}")
            for key in sorted(removed_perms):
                print(f"   - {key} (kept in permissions.json)")

        print(f"\n📦 Total permissions: {len(merged)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Synchronize permissions.json with resource files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without updating permissions.json",
    )
    parser.add_argument(
        "--service",
        type=str,
        help="Only scan specific service (e.g., guardian, identity)",
    )

    args = parser.parse_args()

    # Get script directory. Save permissions.json to the service's `app/data`
    # directory (one level up from `scripts/`). For example, when the
    # script lives in `.../guardian_service/scripts`, the target should be
    # `.../guardian_service/app/data/permissions.json`.
    script_dir = Path(__file__).parent
    service_root = script_dir.parent
    permissions_file = service_root / "app" / "data" / "permissions.json"

    print("🚀 Permission Synchronization Tool")
    print("=" * 60)

    # Initialize extractor
    extractor = PermissionExtractor(script_dir)

    # Find services
    service_dirs = extractor.find_service_directories(args.service)

    if not service_dirs:
        print("❌ No service directories found!")
        return 1

    # Scan all services
    all_discovered = []
    for service_dir in service_dirs:
        permissions = extractor.scan_service(service_dir)
        all_discovered.extend(permissions)

    print(
        f"\n✅ Discovered {len(all_discovered)} permissions across {len(service_dirs)} services"
    )

    # Load existing permissions
    existing = extractor.load_existing_permissions(permissions_file)
    print(f"📖 Loaded {len(existing)} existing permissions")

    # Merge permissions
    merged, consolidated = extractor.merge_permissions(existing, all_discovered)

    # Print summary
    extractor.print_summary(existing, consolidated, merged)

    # Save if not dry-run
    if args.dry_run:
        print("\n🔍 DRY RUN - No changes made to permissions.json")
    else:
        # Ensure output directory exists before saving
        try:
            permissions_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"⚠️  Could not create directory {permissions_file.parent}: {e}")
            return 1

        extractor.save_permissions(merged, permissions_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
