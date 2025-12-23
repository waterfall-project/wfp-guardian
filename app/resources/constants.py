# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Resource constants.

This module defines constant values used throughout the application resources.
These constants help avoid code duplication and make the codebase easier to maintain.
"""

# Error messages for resources
ERROR_VALIDATION = "Validation error"
ERROR_VALIDATION_LOG = "Validation error: %s"
ERROR_INTEGRITY = "Integrity error"
ERROR_INTEGRITY_LOG = "Integrity error: %s"
ERROR_DATABASE = "Database error"
ERROR_DATABASE_LOG = "Database error: %s"

# Dummy resource messages
MSG_DUMMY_NOT_FOUND = "Dummy not found"
MSG_DUMMY_ITEM_NOT_FOUND = "Dummy item not found"
MSG_DUMMY_DELETED = "Dummy deleted successfully"
MSG_DUMMY_CREATED = "Dummy created successfully"
MSG_DUMMY_UPDATED = "Dummy updated successfully"
MSG_NO_INPUT_DATA = "No input data provided"
LOG_DUMMY_NOT_FOUND = "Dummy not found: %s"
LOG_DUMMY_ITEM_NOT_FOUND = "Dummy item with ID %s not found"
LOG_RETRIEVING_ALL_DUMMIES = "Retrieving all Dummy entities"
LOG_RETRIEVING_DUMMY = "Retrieving Dummy with ID: %s"
LOG_CREATING_DUMMY = "Creating new Dummy entity"
LOG_DUMMY_CREATED = "Dummy created successfully: %s"
LOG_UPDATING_DUMMY = "Updating Dummy with ID: %s"
LOG_DUMMY_UPDATED = "Dummy updated successfully: %s"
LOG_PARTIAL_UPDATING_DUMMY = "Partially updating Dummy with ID: %s"
LOG_DUMMY_PARTIAL_UPDATED = "Dummy partially updated: %s"
LOG_DELETING_DUMMY = "Deleting Dummy with ID: %s"
LOG_DUMMY_DELETED = "Dummy deleted successfully: %s"
