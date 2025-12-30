# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Flask application configuration classes.

This module defines configuration classes for the Flask application based on
the deployment environment. Each class defines parameters such as secret keys,
database URLs, debug mode, and SQLAlchemy settings.

Classes:
    Config: Base configuration common to all environments.
    DevelopmentConfig: Configuration for development.
    TestingConfig: Configuration for testing.
    IntegrationConfig: Configuration for integration testing.
    StagingConfig: Configuration for staging.
    ProductionConfig: Configuration for production.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from app.utils.constants import (
    BOOLEAN_TRUE_VALUES,
    DEFAULT_CORS_ALLOW_CREDENTIALS,
    DEFAULT_CORS_ENABLED,
    DEFAULT_CORS_MAX_AGE,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_DATABASE_HOST,
    DEFAULT_DATABASE_PATH,
    DEFAULT_DATABASE_PORT_MYSQL,
    DEFAULT_DATABASE_PORT_POSTGRESQL,
    DEFAULT_DATABASE_TYPE,
    DEFAULT_EXTERNAL_SERVICES_TIMEOUT,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_PAGE_LIMIT,
    DEFAULT_MOCK_COMPANY_ID,
    DEFAULT_MOCK_USER_ID,
    DEFAULT_PAGE_LIMIT,
    DEFAULT_RATE_LIMIT_CONFIGURATION,
    DEFAULT_RATE_LIMIT_ENABLED,
    DEFAULT_RATE_LIMIT_STORAGE,
    DEFAULT_RATE_LIMIT_STRATEGY,
    DEFAULT_SERVICE_PORT,
    DEFAULT_SQLALCHEMY_MAX_OVERFLOW,
    DEFAULT_SQLALCHEMY_POOL_RECYCLE,
    DEFAULT_SQLALCHEMY_POOL_SIZE,
    DEFAULT_SQLALCHEMY_POOL_TIMEOUT,
    DEFAULT_USE_REDIS_CACHE,
    ERROR_DATABASE_CONFIG_INCOMPLETE,
    ERROR_DATABASE_TYPE_INVALID,
    ERROR_DATABASE_URL_NOT_SET,
    ERROR_IDENTITY_URL_REQUIRED,
    ERROR_JWT_ALGORITHM_NOT_SET,
    ERROR_JWT_SECRET_NOT_SET,
    ERROR_REDIS_URL_REQUIRED,
    VALID_DATABASE_TYPES,
    VALID_RATE_LIMIT_STORAGE,
    VALID_RATE_LIMIT_STRATEGIES,
)
from app.utils.logger import logger

# Load .env file ONLY for local development (not in Docker)
# In Docker (staging/production), variables come from orchestration tools (docker-compose, k8s, helm)
if not os.environ.get("IN_DOCKER_CONTAINER") and not os.environ.get("APP_MODE"):
    ENV_FILE = ".env.development"
    if Path(ENV_FILE).exists():
        load_dotenv(ENV_FILE)
    else:
        logger.warning(
            f"{ENV_FILE} not found. Ensure environment variables are set manually."
        )


class Config:
    """Base configuration common to all environments."""

    # Flask Configuration
    SERVICE_PORT = int(os.environ.get("SERVICE_PORT", DEFAULT_SERVICE_PORT))

    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM")

    # External Services Configuration
    IDENTITY_SERVICE_URL = os.environ.get("IDENTITY_SERVICE_URL")
    EXTERNAL_SERVICES_TIMEOUT = float(
        os.environ.get("EXTERNAL_SERVICES_TIMEOUT", DEFAULT_EXTERNAL_SERVICES_TIMEOUT)
    )

    # Internal Service Authentication (for service-to-service calls)
    INTERNAL_SERVICE_TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN")

    # Mock User Configuration (used when USE_IDENTITY_SERVICE is false)
    MOCK_USER_ID = os.environ.get("MOCK_USER_ID", DEFAULT_MOCK_USER_ID)
    MOCK_COMPANY_ID = os.environ.get("MOCK_COMPANY_ID", DEFAULT_MOCK_COMPANY_ID)

    # Redis Cache Configuration
    USE_REDIS_CACHE = (
        os.environ.get("USE_REDIS_CACHE", DEFAULT_USE_REDIS_CACHE).lower()
        in BOOLEAN_TRUE_VALUES
    )

    # Redis connection components (for display and building URL)
    REDIS_HOST = os.environ.get("REDIS_HOST")
    REDIS_PORT = os.environ.get("REDIS_PORT")
    REDIS_DB = os.environ.get("REDIS_DB", "0")
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

    # Build REDIS_URL from components or use direct URL if provided
    REDIS_URL = os.environ.get("REDIS_URL")
    if not REDIS_URL and USE_REDIS_CACHE and REDIS_HOST and REDIS_PORT:
        # Build URL from components
        if REDIS_PASSWORD:
            REDIS_URL = (
                f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            )
        else:
            REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

    # SQLAlchemy Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = (
        os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS", "false").lower()
        in BOOLEAN_TRUE_VALUES
    )
    SQLALCHEMY_POOL_SIZE = int(
        os.environ.get("SQLALCHEMY_POOL_SIZE", DEFAULT_SQLALCHEMY_POOL_SIZE)
    )
    SQLALCHEMY_POOL_RECYCLE = int(
        os.environ.get("SQLALCHEMY_POOL_RECYCLE", DEFAULT_SQLALCHEMY_POOL_RECYCLE)
    )
    SQLALCHEMY_POOL_TIMEOUT = int(
        os.environ.get("SQLALCHEMY_POOL_TIMEOUT", DEFAULT_SQLALCHEMY_POOL_TIMEOUT)
    )
    SQLALCHEMY_MAX_OVERFLOW = int(
        os.environ.get("SQLALCHEMY_MAX_OVERFLOW", DEFAULT_SQLALCHEMY_MAX_OVERFLOW)
    )

    # Database Configuration
    # Priority 1: Use DATABASE_URL if provided (common in production/cloud environments)
    # Priority 2: Build URL from individual components
    DATABASE_TYPE = os.environ.get("DATABASE_TYPE", DEFAULT_DATABASE_TYPE).lower()
    DATABASE_HOST = os.environ.get("DATABASE_HOST", DEFAULT_DATABASE_HOST)
    DATABASE_PORT = os.environ.get(
        "DATABASE_PORT"
    )  # Will be set based on type if not provided
    DATABASE_USER = os.environ.get("DATABASE_USER")
    DATABASE_PASSWORD = os.environ.get("DATABASE_PASSWORD")
    DATABASE_NAME = os.environ.get("DATABASE_NAME")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH)

    SQLALCHEMY_DATABASE_URI: str | None = None

    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    LOG_FORMAT = os.environ.get("LOG_FORMAT", DEFAULT_LOG_FORMAT).lower()

    # CORS Configuration
    CORS_ENABLED = (
        os.environ.get("CORS_ENABLED", DEFAULT_CORS_ENABLED).lower()
        in BOOLEAN_TRUE_VALUES
    )
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    CORS_ALLOW_CREDENTIALS = (
        os.environ.get("CORS_ALLOW_CREDENTIALS", DEFAULT_CORS_ALLOW_CREDENTIALS).lower()
        in BOOLEAN_TRUE_VALUES
    )
    CORS_MAX_AGE = int(os.environ.get("CORS_MAX_AGE", DEFAULT_CORS_MAX_AGE))

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = (
        os.environ.get("RATE_LIMIT_ENABLED", DEFAULT_RATE_LIMIT_ENABLED).lower()
        in BOOLEAN_TRUE_VALUES
    )
    RATE_LIMIT_CONFIGURATION = os.environ.get(
        "RATE_LIMIT_CONFIGURATION", DEFAULT_RATE_LIMIT_CONFIGURATION
    )
    RATE_LIMIT_STRATEGY = os.environ.get(
        "RATE_LIMIT_STRATEGY", DEFAULT_RATE_LIMIT_STRATEGY
    ).lower()
    RATE_LIMIT_STORAGE = os.environ.get(
        "RATE_LIMIT_STORAGE", DEFAULT_RATE_LIMIT_STORAGE
    ).lower()

    # Pagination Configuration
    PAGE_LIMIT = int(os.environ.get("PAGE_LIMIT", DEFAULT_PAGE_LIMIT))
    MAX_PAGE_LIMIT = int(os.environ.get("MAX_PAGE_LIMIT", DEFAULT_MAX_PAGE_LIMIT))

    @classmethod
    def validate(cls):
        """Validate configuration consistency after loading.

        This method should be called after the configuration is loaded
        to ensure all required variables are present and consistent.
        """
        # Build SQLALCHEMY_DATABASE_URI if not already set
        cls._build_database_uri()

        # Override with environment variables if set
        cls._override_from_environment()

        # Validate all configuration parameters
        cls._validate_database_type()
        cls._validate_log_format()
        cls._validate_rate_limiting()
        cls._validate_jwt()
        cls._validate_services()
        cls._validate_redis()
        cls._validate_database_uri()

        cls._log_validation_status()

    @classmethod
    def _override_from_environment(cls):
        """Override configuration with environment variables if set."""
        env_use_identity = os.environ.get("USE_IDENTITY_SERVICE")
        if env_use_identity is not None:
            cls.USE_IDENTITY_SERVICE = env_use_identity.lower() in BOOLEAN_TRUE_VALUES  # type: ignore[attr-defined]

    @classmethod
    def _validate_database_type(cls):
        """Validate DATABASE_TYPE configuration."""
        if cls.DATABASE_TYPE not in VALID_DATABASE_TYPES:
            raise ValueError(ERROR_DATABASE_TYPE_INVALID)

    @classmethod
    def _validate_log_format(cls):
        """Validate LOG_FORMAT configuration."""
        if cls.LOG_FORMAT not in ["json", "text"]:
            logger.warning(
                f"Invalid LOG_FORMAT '{cls.LOG_FORMAT}'. Using default 'text'."
            )
            cls.LOG_FORMAT = "text"

    @classmethod
    def _validate_rate_limiting(cls):
        """Validate rate limiting configuration."""
        # Validate RATE_LIMIT_STRATEGY
        if cls.RATE_LIMIT_STRATEGY not in VALID_RATE_LIMIT_STRATEGIES:
            logger.warning(
                f"Invalid RATE_LIMIT_STRATEGY '{cls.RATE_LIMIT_STRATEGY}'. "
                f"Using default '{DEFAULT_RATE_LIMIT_STRATEGY}'."
            )
            cls.RATE_LIMIT_STRATEGY = DEFAULT_RATE_LIMIT_STRATEGY

        # Validate RATE_LIMIT_STORAGE
        if cls.RATE_LIMIT_STORAGE not in VALID_RATE_LIMIT_STORAGE:
            logger.warning(
                f"Invalid RATE_LIMIT_STORAGE '{cls.RATE_LIMIT_STORAGE}'. "
                f"Using default '{DEFAULT_RATE_LIMIT_STORAGE}'."
            )
            cls.RATE_LIMIT_STORAGE = DEFAULT_RATE_LIMIT_STORAGE

        # Warn if rate limiting uses Redis storage but Redis is not configured
        if (
            cls.RATE_LIMIT_ENABLED
            and cls.RATE_LIMIT_STORAGE == "redis"
            and not cls.USE_REDIS_CACHE
        ):
            logger.warning(
                "RATE_LIMIT_STORAGE is set to 'redis' but USE_REDIS_CACHE is disabled. "
                "Rate limiting will use Redis independently of cache."
            )

        # Warn if rate limiting storage is memory in production
        if cls.RATE_LIMIT_ENABLED and cls.RATE_LIMIT_STORAGE == "memory":
            logger.warning(
                "RATE_LIMIT_STORAGE is set to 'memory'. This should only be used for testing. "
                "Use 'redis' for production environments."
            )

    @classmethod
    def _validate_jwt(cls):
        """Validate JWT configuration."""
        if not cls.JWT_ALGORITHM:
            raise ValueError(ERROR_JWT_ALGORITHM_NOT_SET)

    @classmethod
    def _validate_services(cls):
        """Validate external services configuration."""
        # Validate JWT_SECRET_KEY if Identity Service is enabled
        if cls.USE_IDENTITY_SERVICE and not cls.JWT_SECRET_KEY:  # type: ignore[attr-defined]
            raise ValueError(ERROR_JWT_SECRET_NOT_SET)

        # Validate IDENTITY_SERVICE_URL if Identity Service is enabled
        if cls.USE_IDENTITY_SERVICE and not cls.IDENTITY_SERVICE_URL:  # type: ignore[attr-defined]
            raise ValueError(ERROR_IDENTITY_URL_REQUIRED)

    @classmethod
    def _validate_redis(cls):
        """Validate Redis configuration."""
        # Validate REDIS_URL or REDIS_HOST if Redis Cache is enabled
        if cls.USE_REDIS_CACHE and not cls.REDIS_URL:
            logger.error(ERROR_REDIS_URL_REQUIRED)
            raise ValueError(ERROR_REDIS_URL_REQUIRED)

        # Ignore REDIS_URL and components if USE_REDIS_CACHE is False
        if not cls.USE_REDIS_CACHE and cls.REDIS_URL:
            logger.info("USE_REDIS_CACHE is disabled. REDIS_URL will be ignored.")
            cls.REDIS_URL = None

    @classmethod
    def _validate_database_uri(cls):
        """Validate SQLALCHEMY_DATABASE_URI if required."""
        if (
            getattr(cls, "REQUIRES_DATABASE_URL", False)
            and not cls.SQLALCHEMY_DATABASE_URI
        ):  # pyright: ignore[reportAttributeAccessIssue]
            raise ValueError(ERROR_DATABASE_URL_NOT_SET)

    @classmethod
    def _log_validation_status(cls):
        """Log the validation status for debugging."""
        logger.debug(
            f"Validating {cls.__name__}: "
            f"USE_IDENTITY_SERVICE={cls.USE_IDENTITY_SERVICE}, "  # type: ignore[attr-defined]
            f"USE_REDIS_CACHE={cls.USE_REDIS_CACHE}, "
            f"CORS_ENABLED={cls.CORS_ENABLED}, "
            f"RATE_LIMIT_ENABLED={cls.RATE_LIMIT_ENABLED}, "
            f"JWT_SECRET_KEY={'SET' if cls.JWT_SECRET_KEY else 'NOT SET'}"
        )

    @classmethod
    def _build_database_uri(cls):
        """Build SQLALCHEMY_DATABASE_URI from environment variables.

        Priority:
        1. Use SQLALCHEMY_DATABASE_URI if already set in the class (e.g., TestingConfig)
        2. Use DATABASE_URL if provided (e.g., from cloud providers)
        3. Build from individual components (DATABASE_TYPE, DATABASE_HOST, etc.)
        4. Use class default (for development/testing)

        For staging/production: Requires either DATABASE_URL or complete
        connection parameters (not SQLite).
        """
        # Priority 1: Skip if SQLALCHEMY_DATABASE_URI is already set (e.g., in TestingConfig)
        if hasattr(cls, "SQLALCHEMY_DATABASE_URI") and cls.SQLALCHEMY_DATABASE_URI:
            # Don't override if explicitly set in the class
            return

        # Priority 2: Use DATABASE_URL if explicitly provided
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            cls.SQLALCHEMY_DATABASE_URI = database_url
            return

        # Validate production/staging requirements
        cls._validate_production_database_config()

        # Priority 3: Build from components if DATABASE_TYPE is specified
        if cls.DATABASE_TYPE == "sqlite":
            cls._build_sqlite_uri()
        elif cls.DATABASE_TYPE in ("postgresql", "mysql"):
            cls._build_sql_server_uri()

        # Priority 4: Use class default (set in subclasses like DevelopmentConfig)
        # SQLALCHEMY_DATABASE_URI should be set by the subclass

    @classmethod
    def _validate_production_database_config(cls):
        """Validate database configuration for production/staging environments."""
        if not getattr(cls, "REQUIRES_DATABASE_URL", False):
            return

        # In production/staging, SQLite is not allowed
        if cls.DATABASE_TYPE == "sqlite":
            raise ValueError(ERROR_DATABASE_CONFIG_INCOMPLETE)

        # Must have all connection parameters for postgresql/mysql
        if not all(
            [
                cls.DATABASE_HOST,
                cls.DATABASE_USER,
                cls.DATABASE_PASSWORD,
                cls.DATABASE_NAME,
            ]
        ):
            raise ValueError(ERROR_DATABASE_CONFIG_INCOMPLETE)

    @classmethod
    def _build_sqlite_uri(cls):
        """Build SQLite database URI."""
        db_path = Path(cls.DATABASE_PATH).resolve()
        cls.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    @classmethod
    def _build_sql_server_uri(cls):
        """Build PostgreSQL or MySQL database URI."""
        # Check if all required parameters are present
        if not all(
            [
                cls.DATABASE_HOST,
                cls.DATABASE_USER,
                cls.DATABASE_PASSWORD,
                cls.DATABASE_NAME,
            ]
        ):
            return

        # Set default port based on database type if not provided
        if not cls.DATABASE_PORT:
            if cls.DATABASE_TYPE == "postgresql":
                cls.DATABASE_PORT = DEFAULT_DATABASE_PORT_POSTGRESQL
            elif cls.DATABASE_TYPE == "mysql":
                cls.DATABASE_PORT = DEFAULT_DATABASE_PORT_MYSQL

        # Build connection string
        driver = "postgresql" if cls.DATABASE_TYPE == "postgresql" else "mysql+pymysql"
        cls.SQLALCHEMY_DATABASE_URI = (
            f"{driver}://{cls.DATABASE_USER}:{cls.DATABASE_PASSWORD}"
            f"@{cls.DATABASE_HOST}:{cls.DATABASE_PORT}/{cls.DATABASE_NAME}"
        )


class DevelopmentConfig(Config):
    """Configuration for the development environment."""

    # External services disabled by default in development
    USE_IDENTITY_SERVICE = False

    DEBUG = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{Path('dev.db').resolve()}"


class TestingConfig(Config):
    """Configuration for the testing environment."""

    # External services disabled by default in testing
    USE_IDENTITY_SERVICE = False

    # Rate limiting disabled in testing to avoid interference with tests
    RATE_LIMIT_ENABLED = False

    TESTING = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class IntegrationConfig(Config):
    """Configuration for the integration testing environment."""

    # External services enabled in integration testing
    USE_IDENTITY_SERVICE = True

    # Rate limiting disabled in integration tests
    RATE_LIMIT_ENABLED = False

    TESTING = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class StagingConfig(Config):
    """Configuration for the staging environment."""

    # External services enabled by default in staging
    USE_IDENTITY_SERVICE = True
    REQUIRES_DATABASE_URL = True

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


class ProductionConfig(Config):
    """Configuration for the production environment."""

    # External services enabled by default in production
    USE_IDENTITY_SERVICE = True
    REQUIRES_DATABASE_URL = True

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
