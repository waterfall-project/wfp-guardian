#!/usr/bin/env python3
"""Quick script to display permissions from database."""

from app import create_app
from app.models.permission import Permission

app = create_app("app.config.DevelopmentConfig")

with app.app_context():
    all_perms = Permission.get_all()
    print(f"\n✅ Total permissions in database: {len(all_perms)}\n")

    print("First 10 permissions:")
    for p in Permission.get_all(limit=10):
        print(f"  - {p.name}")

    print("\n\nPermissions by service:")
    services = {p.service for p in all_perms}
    for service in sorted(services):
        count = len(Permission.get_by_service(service))
        print(f"  {service}: {count} permissions")
