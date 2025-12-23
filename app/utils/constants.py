# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Application constants.

This module defines constant values used throughout the application.
These constants help avoid code duplication and make the codebase easier
to maintain.
"""

# Configuration error messages
ERROR_JWT_SECRET_NOT_SET = "JWT_SECRET_KEY environment variable is not set."  # nosec B105
ERROR_JWT_ALGORITHM_NOT_SET = "JWT_ALGORITHM environment variable is not set."
ERROR_DATABASE_URL_NOT_SET = (
    "DATABASE_URL or database connection variables are not set."
)
ERROR_DATABASE_TYPE_INVALID = "DATABASE_TYPE must be one of: sqlite, postgresql, mysql."
ERROR_DATABASE_CONFIG_INCOMPLETE = "Database configuration incomplete. Provide either DATABASE_URL or all required connection variables (HOST, PORT, USER, PASSWORD, NAME for postgresql/mysql)."
ERROR_GUARDIAN_URL_REQUIRED = (
    "GUARDIAN_SERVICE_URL is required when USE_GUARDIAN_SERVICE is enabled."
)
ERROR_IDENTITY_URL_REQUIRED = (
    "IDENTITY_SERVICE_URL is required when USE_IDENTITY_SERVICE is enabled."
)
ERROR_REDIS_URL_REQUIRED = (
    "REDIS_URL or REDIS_HOST is required when USE_REDIS_CACHE is enabled."
)

# Default configuration values
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "text"
DEFAULT_SERVICE_PORT = "5000"

# Pagination defaults
DEFAULT_PAGE_LIMIT = 20
DEFAULT_MAX_PAGE_LIMIT = 100

# External Services Configuration
DEFAULT_EXTERNAL_SERVICES_TIMEOUT = "5"
DEFAULT_USE_GUARDIAN = "true"
DEFAULT_USE_IDENTITY = "true"
DEFAULT_USE_REDIS_CACHE = "false"

# Mock user configuration (used when USE_IDENTITY_SERVICE is false)
DEFAULT_MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_MOCK_COMPANY_ID = "00000000-0000-0000-0000-000000000001"

# Database default values
DEFAULT_DATABASE_TYPE = "sqlite"
DEFAULT_DATABASE_HOST = "localhost"
DEFAULT_DATABASE_PORT_POSTGRESQL = "5432"
DEFAULT_DATABASE_PORT_MYSQL = "3306"
DEFAULT_DATABASE_PATH = "dev.db"

# SQLAlchemy default values
DEFAULT_SQLALCHEMY_POOL_SIZE = "5"
DEFAULT_SQLALCHEMY_POOL_RECYCLE = "3600"
DEFAULT_SQLALCHEMY_POOL_TIMEOUT = "30"
DEFAULT_SQLALCHEMY_MAX_OVERFLOW = "10"

# CORS default values
DEFAULT_CORS_ENABLED = "true"
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:5173"
DEFAULT_CORS_ALLOW_CREDENTIALS = "true"
DEFAULT_CORS_MAX_AGE = "3600"

# Rate Limiting default values
DEFAULT_RATE_LIMIT_ENABLED = "true"
DEFAULT_RATE_LIMIT_CONFIGURATION = "10 per minute"
DEFAULT_RATE_LIMIT_STRATEGY = "fixed-window"
DEFAULT_RATE_LIMIT_STORAGE = "redis"

# Valid database types
VALID_DATABASE_TYPES = ("sqlite", "postgresql", "mysql")

# Valid rate limit strategies
VALID_RATE_LIMIT_STRATEGIES = ("fixed-window", "sliding-window", "token-bucket")
VALID_RATE_LIMIT_STORAGE = ("redis", "memory")

# Boolean value representations
BOOLEAN_TRUE_VALUES = ("true", "yes", "1")

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
LOG_DUMMY_NOT_FOUND = "Dummy with ID %s not found"
LOG_DUMMY_ITEM_NOT_FOUND = "Dummy item with ID %s not found"
