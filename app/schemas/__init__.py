# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Marshmallow schemas module exports.

This module provides convenient access to all Marshmallow schemas
used for data serialization and validation throughout the application.
"""

from app.schemas.dummy_schema import DummyCreateSchema, DummySchema, DummyUpdateSchema

__all__ = [
    "DummyCreateSchema",
    "DummySchema",
    "DummyUpdateSchema",
]
