# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""
Test suite for configuration management.

This module tests all configuration classes and their validation logic,
including default values, environment-specific settings, and consistency checks.
"""

import os

import pytest

from app.config import (
    Config,
    DevelopmentConfig,
    IntegrationConfig,
    ProductionConfig,
    StagingConfig,
    TestingConfig,
)

# =============================================================================
# Test Default Values
# =============================================================================


class TestDefaultValues:
    """Test default values for all configuration variables."""

    def test_flask_defaults(self):
        """Test Flask default configuration values."""
        assert Config.SERVICE_PORT == 5000

    def test_jwt_defaults(self):
        """Test JWT default configuration values."""
        # In the test environment, these might be set by conftest.py or .env.testing
        # We verify they match the environment or are None if not set
        assert os.environ.get("JWT_ALGORITHM") == Config.JWT_ALGORITHM
        assert os.environ.get("JWT_SECRET_KEY") == Config.JWT_SECRET_KEY

    def test_logging_defaults(self):
        """Test logging default configuration values."""
        # Test that defaults are defined in constants
        from app.utils.constants import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL

        assert DEFAULT_LOG_LEVEL == "INFO"
        assert DEFAULT_LOG_FORMAT == "text"

        # LOG_FORMAT should have its default value
        assert Config.LOG_FORMAT == "text"

    def test_sqlalchemy_defaults(self):
        """Test SQLAlchemy default configuration values."""
        assert Config.SQLALCHEMY_POOL_SIZE == 5
        assert Config.SQLALCHEMY_POOL_RECYCLE == 3600
        assert Config.SQLALCHEMY_POOL_TIMEOUT == 30
        assert Config.SQLALCHEMY_MAX_OVERFLOW == 10
        assert Config.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_cors_defaults(self):
        """Test CORS default configuration values."""
        assert Config.CORS_ENABLED is True
        assert Config.CORS_ORIGINS == "http://localhost:3000,http://localhost:5173"
        assert Config.CORS_ALLOW_CREDENTIALS is True
        assert Config.CORS_MAX_AGE == 3600

    def test_rate_limiting_defaults(self):
        """Test Rate Limiting default configuration values."""
        # Note: RATE_LIMIT_ENABLED depends on environment, so we test TestingConfig
        assert TestingConfig.RATE_LIMIT_ENABLED is False
        assert Config.RATE_LIMIT_CONFIGURATION == "10 per minute"
        assert Config.RATE_LIMIT_STRATEGY == "fixed-window"
        assert Config.RATE_LIMIT_STORAGE == "redis"

    def test_external_services_defaults(self):
        """Test external services default configuration values."""
        assert abs(Config.EXTERNAL_SERVICES_TIMEOUT - 5.0) < 0.001
        assert Config.GUARDIAN_SERVICE_URL is None
        assert Config.IDENTITY_SERVICE_URL is None

    def test_mock_user_defaults(self):
        """Test mock user default configuration values."""
        assert Config.MOCK_USER_ID == "00000000-0000-0000-0000-000000000001"
        assert Config.MOCK_COMPANY_ID == "00000000-0000-0000-0000-000000000001"

    def test_redis_defaults(self):
        """Test Redis default configuration values."""
        assert Config.USE_REDIS_CACHE is False
        assert Config.REDIS_URL is None


# =============================================================================
# Test Environment-Specific Configurations
# =============================================================================


class TestDevelopmentConfig:
    """Test Development environment configuration."""

    def test_development_service_flags(self):
        """Test that external services are disabled in development."""
        assert DevelopmentConfig.USE_IDENTITY_SERVICE is False
        assert DevelopmentConfig.USE_GUARDIAN_SERVICE is False

    def test_development_debug_mode(self):
        """Test that debug mode is enabled in development."""
        assert DevelopmentConfig.DEBUG is True

    def test_development_log_level(self):
        """Test that log level is DEBUG in development."""
        assert DevelopmentConfig.LOG_LEVEL == "DEBUG"

    def test_development_database(self):
        """Test that development uses SQLite database."""
        db_uri = DevelopmentConfig.SQLALCHEMY_DATABASE_URI
        assert db_uri is not None
        assert "sqlite:///" in db_uri
        assert "dev.db" in db_uri

    def test_development_testing_flag(self):
        """Test that TESTING flag is not set in development."""
        testing_flag = getattr(DevelopmentConfig, "TESTING", False)
        assert not testing_flag


class TestTestingConfig:
    """Test Testing environment configuration."""

    def test_testing_service_flags(self):
        """Test that external services are disabled in testing."""
        assert TestingConfig.USE_IDENTITY_SERVICE is False
        assert TestingConfig.USE_GUARDIAN_SERVICE is False

    def test_testing_testing_flag(self):
        """Test that TESTING flag is enabled in testing."""
        assert TestingConfig.TESTING is True

    def test_testing_log_level(self):
        """Test that log level is DEBUG in testing."""
        assert TestingConfig.LOG_LEVEL == "DEBUG"

    def test_testing_database(self):
        """Test that testing uses in-memory SQLite database."""
        assert TestingConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"


class TestIntegrationConfig:
    """Test Integration environment configuration."""

    def test_integration_service_flags(self):
        """Test that external services are enabled in integration."""
        assert IntegrationConfig.USE_IDENTITY_SERVICE is True
        assert IntegrationConfig.USE_GUARDIAN_SERVICE is True

    def test_integration_testing_flag(self):
        """Test that TESTING flag is enabled in integration."""
        assert IntegrationConfig.TESTING is True

    def test_integration_log_level(self):
        """Test that log level is DEBUG in integration."""
        assert IntegrationConfig.LOG_LEVEL == "DEBUG"

    def test_integration_database(self):
        """Test that integration uses in-memory SQLite database."""
        assert IntegrationConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///:memory:"


class TestStagingConfig:
    """Test Staging environment configuration."""

    def test_staging_service_flags(self):
        """Test that external services are enabled in staging."""
        assert StagingConfig.USE_IDENTITY_SERVICE is True
        assert StagingConfig.USE_GUARDIAN_SERVICE is True

    def test_staging_debug_mode(self):
        """Test that debug mode is enabled in staging."""
        assert StagingConfig.DEBUG is True

    def test_staging_requires_database_url(self):
        """Test that staging requires DATABASE_URL."""
        assert StagingConfig.REQUIRES_DATABASE_URL is True


class TestProductionConfig:
    """Test Production environment configuration."""

    def test_production_service_flags(self):
        """Test that external services are enabled in production."""
        assert ProductionConfig.USE_IDENTITY_SERVICE is True
        assert ProductionConfig.USE_GUARDIAN_SERVICE is True

    def test_production_debug_mode(self):
        """Test that debug mode is disabled in production."""
        assert ProductionConfig.DEBUG is False

    def test_production_requires_database_url(self):
        """Test that production requires DATABASE_URL."""
        assert ProductionConfig.REQUIRES_DATABASE_URL is True


# =============================================================================
# Test Environment Variable Override
# =============================================================================


class TestEnvironmentVariableOverride:
    """Test that environment variables properly override default values."""

    def test_service_port_override(self, monkeypatch):
        """Test SERVICE_PORT can be overridden by environment variable."""
        monkeypatch.setenv("SERVICE_PORT", "8080")
        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.SERVICE_PORT == 8080

    def test_jwt_algorithm_override(self, monkeypatch):
        """Test JWT_ALGORITHM can be overridden by environment variable."""
        monkeypatch.setenv("JWT_ALGORITHM", "RS256")
        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.JWT_ALGORITHM == "RS256"

    def test_log_level_override(self, monkeypatch):
        """Test LOG_LEVEL can be overridden by environment variable."""
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.LOG_LEVEL == "ERROR"

    def test_log_format_override(self, monkeypatch):
        """Test LOG_FORMAT can be overridden by environment variable."""
        monkeypatch.setenv("LOG_FORMAT", "json")
        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.LOG_FORMAT == "json"

    def test_mock_user_id_override(self, monkeypatch):
        """Test MOCK_USER_ID can be overridden by environment variable."""
        monkeypatch.setenv("MOCK_USER_ID", "42")
        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.MOCK_USER_ID == "42"

    def test_mock_company_id_override(self, monkeypatch):
        """Test MOCK_COMPANY_ID can be overridden by environment variable."""
        monkeypatch.setenv("MOCK_COMPANY_ID", "99")
        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.MOCK_COMPANY_ID == "99"


# =============================================================================
# Test Configuration Validation - JWT and Identity Service
# =============================================================================


class TestJWTValidation:
    """Test JWT configuration validation."""

    def test_jwt_secret_required_when_identity_enabled(self, monkeypatch):
        """Test that JWT_SECRET_KEY is required when USE_IDENTITY_SERVICE is enabled."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "true")
        monkeypatch.setenv("IDENTITY_SERVICE_URL", "http://localhost:8002")
        if "JWT_SECRET_KEY" in os.environ:
            monkeypatch.delenv("JWT_SECRET_KEY")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        with pytest.raises(
            ValueError, match="JWT_SECRET_KEY environment variable is not set"
        ):
            ReloadedDev.validate()

    def test_jwt_secret_not_required_when_identity_disabled(self, monkeypatch):
        """Test that JWT_SECRET_KEY is not required when USE_IDENTITY_SERVICE is disabled."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "false")
        if "JWT_SECRET_KEY" in os.environ:
            monkeypatch.delenv("JWT_SECRET_KEY")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        # Should not raise any exception
        ReloadedDev.validate()


# =============================================================================
# Test Configuration Validation - Identity Service
# =============================================================================


class TestIdentityServiceValidation:
    """Test Identity Service configuration validation."""

    def test_identity_url_required_when_enabled(self, monkeypatch):
        """Test that IDENTITY_SERVICE_URL is required when USE_IDENTITY_SERVICE is enabled."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        if "IDENTITY_SERVICE_URL" in os.environ:
            monkeypatch.delenv("IDENTITY_SERVICE_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        with pytest.raises(ValueError, match="IDENTITY_SERVICE_URL is required"):
            ReloadedDev.validate()

    def test_identity_url_not_required_when_disabled(self, monkeypatch):
        """Test that IDENTITY_SERVICE_URL is not required when USE_IDENTITY_SERVICE is disabled."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "false")
        if "IDENTITY_SERVICE_URL" in os.environ:
            monkeypatch.delenv("IDENTITY_SERVICE_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        # Should not raise any exception
        ReloadedDev.validate()


# =============================================================================
# Test Configuration Validation - Guardian Service
# =============================================================================


class TestGuardianServiceValidation:
    """Test Guardian Service configuration validation."""

    def test_guardian_url_required_when_enabled(self, monkeypatch):
        """Test that GUARDIAN_SERVICE_URL is required when USE_GUARDIAN_SERVICE is enabled."""
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "true")
        if "GUARDIAN_SERVICE_URL" in os.environ:
            monkeypatch.delenv("GUARDIAN_SERVICE_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        with pytest.raises(ValueError, match="GUARDIAN_SERVICE_URL is required"):
            ReloadedDev.validate()

    def test_guardian_url_not_required_when_disabled(self, monkeypatch):
        """Test that GUARDIAN_SERVICE_URL is not required when USE_GUARDIAN_SERVICE is disabled."""
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "false")
        if "GUARDIAN_SERVICE_URL" in os.environ:
            monkeypatch.delenv("GUARDIAN_SERVICE_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        # Should not raise any exception
        ReloadedDev.validate()


# =============================================================================
# Test Configuration Validation - Redis Cache
# =============================================================================


class TestRedisCacheValidation:
    """Test Redis Cache configuration validation."""

    def test_redis_url_required_when_cache_enabled(self, monkeypatch):
        """Test that REDIS_URL or REDIS_HOST is required when USE_REDIS_CACHE is enabled."""
        monkeypatch.setenv("USE_REDIS_CACHE", "true")
        if "REDIS_URL" in os.environ:
            monkeypatch.delenv("REDIS_URL")
        if "REDIS_HOST" in os.environ:
            monkeypatch.delenv("REDIS_HOST")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        with pytest.raises(ValueError, match="REDIS_URL or REDIS_HOST is required"):
            ReloadedDev.validate()

    def test_redis_url_ignored_when_cache_disabled(self, monkeypatch):
        """Test that REDIS_URL is ignored when USE_REDIS_CACHE is disabled."""
        monkeypatch.setenv("USE_REDIS_CACHE", "false")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        # Should not raise any exception
        ReloadedDev.validate()

        # REDIS_URL should be set to None after validation
        assert ReloadedDev.REDIS_URL is None

    def test_redis_url_built_from_components_without_password(self, monkeypatch):
        """Test that REDIS_URL is built from components when no password."""
        monkeypatch.setenv("USE_REDIS_CACHE", "true")
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        if "REDIS_URL" in os.environ:
            monkeypatch.delenv("REDIS_URL")
        if "REDIS_PASSWORD" in os.environ:
            monkeypatch.delenv("REDIS_PASSWORD")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.REDIS_URL == "redis://localhost:6379/0"

    def test_redis_url_built_from_components_with_password(self, monkeypatch):
        """Test that REDIS_URL is built from components with password."""
        monkeypatch.setenv("USE_REDIS_CACHE", "true")
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "1")
        monkeypatch.setenv("REDIS_PASSWORD", "secret123")
        if "REDIS_URL" in os.environ:
            monkeypatch.delenv("REDIS_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        assert ReloadedConfig.REDIS_URL == "redis://:secret123@localhost:6379/1"


# =============================================================================
# Test Configuration Validation - LOG_FORMAT
# =============================================================================


class TestLogFormatValidation:
    """Test LOG_FORMAT configuration validation."""

    @pytest.mark.parametrize("format_value", ["json", "text"])
    def test_valid_log_formats(self, format_value, monkeypatch):
        """Test that valid LOG_FORMAT values are accepted."""
        monkeypatch.setenv("LOG_FORMAT", format_value)

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        ReloadedDev.validate()
        assert format_value == ReloadedDev.LOG_FORMAT

    def test_invalid_log_format_defaults_to_text(self, monkeypatch):
        """Test that invalid LOG_FORMAT defaults to 'text'."""
        monkeypatch.setenv("LOG_FORMAT", "invalid")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        ReloadedDev.validate()
        assert ReloadedDev.LOG_FORMAT == "text"


# =============================================================================
# Test Configuration Validation - Rate Limiting
# =============================================================================


class TestRateLimitingValidation:
    """Test Rate Limiting configuration validation."""

    @pytest.mark.parametrize(
        "strategy", ["fixed-window", "sliding-window", "token-bucket"]
    )
    def test_valid_rate_limit_strategies(self, strategy, monkeypatch):
        """Test that valid RATE_LIMIT_STRATEGY values are accepted."""
        monkeypatch.setenv("RATE_LIMIT_STRATEGY", strategy)

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        ReloadedDev.validate()
        assert strategy == ReloadedDev.RATE_LIMIT_STRATEGY

    def test_invalid_rate_limit_strategy_defaults(self, monkeypatch):
        """Test that invalid RATE_LIMIT_STRATEGY defaults to 'fixed-window'."""
        monkeypatch.setenv("RATE_LIMIT_STRATEGY", "invalid")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        ReloadedDev.validate()
        assert ReloadedDev.RATE_LIMIT_STRATEGY == "fixed-window"

    @pytest.mark.parametrize("storage", ["redis", "memory"])
    def test_valid_rate_limit_storage(self, storage, monkeypatch):
        """Test that valid RATE_LIMIT_STORAGE values are accepted."""
        monkeypatch.setenv("RATE_LIMIT_STORAGE", storage)

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        ReloadedDev.validate()
        assert storage == ReloadedDev.RATE_LIMIT_STORAGE

    def test_invalid_rate_limit_storage_defaults(self, monkeypatch):
        """Test that invalid RATE_LIMIT_STORAGE defaults to 'redis'."""
        monkeypatch.setenv("RATE_LIMIT_STORAGE", "invalid")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        ReloadedDev.validate()
        assert ReloadedDev.RATE_LIMIT_STORAGE == "redis"

    def test_rate_limit_redis_storage_without_cache_warning(self, monkeypatch, caplog):
        """Test warning when RATE_LIMIT_STORAGE is redis but USE_REDIS_CACHE is false."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")
        monkeypatch.setenv("USE_REDIS_CACHE", "false")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        with caplog.at_level("WARNING"):
            ReloadedDev.validate()

        assert any(
            "Rate limiting will use Redis independently" in record.message
            for record in caplog.records
        )

    def test_rate_limit_memory_storage_warning(self, monkeypatch, caplog):
        """Test warning when RATE_LIMIT_STORAGE is memory."""
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_STORAGE", "memory")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        with caplog.at_level("WARNING"):
            ReloadedDev.validate()

        assert any(
            "should only be used for testing" in record.message
            for record in caplog.records
        )


# =============================================================================
# Test Configuration Validation - Database URL
# =============================================================================


class TestDatabaseURLValidation:
    """Test DATABASE_URL configuration validation."""

    def test_database_url_required_for_staging(self, monkeypatch):
        """Test that DATABASE_URL is required for staging environment."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "true")
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("IDENTITY_SERVICE_URL", "http://localhost:8002")
        monkeypatch.setenv("GUARDIAN_SERVICE_URL", "http://localhost:8001")
        if "DATABASE_URL" in os.environ:
            monkeypatch.delenv("DATABASE_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import StagingConfig as ReloadedStaging

        with pytest.raises(ValueError, match="Database configuration incomplete"):
            ReloadedStaging.validate()

    def test_database_url_required_for_production(self, monkeypatch):
        """Test that DATABASE_URL is required for production environment."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "true")
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        monkeypatch.setenv("IDENTITY_SERVICE_URL", "http://localhost:8002")
        monkeypatch.setenv("GUARDIAN_SERVICE_URL", "http://localhost:8001")
        if "DATABASE_URL" in os.environ:
            monkeypatch.delenv("DATABASE_URL")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import ProductionConfig as ReloadedProd

        with pytest.raises(ValueError, match="Database configuration incomplete"):
            ReloadedProd.validate()


# =============================================================================
# Test CORS Configuration Parsing
# =============================================================================


class TestCORSConfiguration:
    """Test CORS configuration parsing and validation."""

    def test_cors_origins_string_parsing(self, monkeypatch):
        """Test that CORS_ORIGINS string is properly parsed."""
        monkeypatch.setenv(
            "CORS_ORIGINS", "http://app1.com,http://app2.com,http://app3.com"
        )

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        # Config stores as string, app parses it
        assert (
            ReloadedDev.CORS_ORIGINS
            == "http://app1.com,http://app2.com,http://app3.com"
        )

    def test_cors_credentials_boolean(self, monkeypatch):
        """Test that CORS_ALLOW_CREDENTIALS is properly parsed as boolean."""
        monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "false")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        assert ReloadedDev.CORS_ALLOW_CREDENTIALS is False

    def test_cors_max_age_integer(self, monkeypatch):
        """Test that CORS_MAX_AGE is properly parsed as integer."""
        monkeypatch.setenv("CORS_MAX_AGE", "7200")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        assert ReloadedDev.CORS_MAX_AGE == 7200


# =============================================================================
# Test Configuration Validation
# =============================================================================


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_validate_missing_jwt_algorithm(self, monkeypatch):
        """Test validation fails when JWT_ALGORITHM is missing."""
        # Prevent loading .env file which might contain JWT_ALGORITHM
        monkeypatch.setenv("APP_MODE", "test")
        monkeypatch.delenv("JWT_ALGORITHM", raising=False)

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        with pytest.raises(ValueError) as excinfo:
            ReloadedConfig.validate()

        assert "JWT_ALGORITHM environment variable is not set" in str(excinfo.value)

    def test_validate_success_with_jwt_algorithm(self, monkeypatch):
        """Test validation succeeds when JWT_ALGORITHM is set."""
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import Config as ReloadedConfig

        # Should not raise
        ReloadedConfig.validate()


# =============================================================================
# Test Complete Configuration Scenarios
# =============================================================================


class TestCompleteConfigurationScenarios:
    """Test complete configuration scenarios with multiple variables."""

    def test_development_with_all_services_disabled(self, monkeypatch):
        """Test development configuration with all external services disabled."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "false")
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "false")
        monkeypatch.setenv("USE_REDIS_CACHE", "false")
        monkeypatch.setenv("CORS_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import DevelopmentConfig as ReloadedDev

        # Should not raise any exception
        ReloadedDev.validate()

    def test_integration_with_all_services_enabled(self, monkeypatch):
        """Test integration configuration with all external services enabled."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "true")
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "true")
        monkeypatch.setenv("USE_REDIS_CACHE", "true")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")
        monkeypatch.setenv("IDENTITY_SERVICE_URL", "http://localhost:8002")
        monkeypatch.setenv("GUARDIAN_SERVICE_URL", "http://localhost:8001")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("CORS_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
        monkeypatch.setenv("RATE_LIMIT_STORAGE", "redis")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import IntegrationConfig as ReloadedInt

        # Should not raise any exception
        ReloadedInt.validate()

    def test_production_minimal_configuration(self, monkeypatch):
        """Test production configuration with minimal required settings."""
        monkeypatch.setenv("USE_IDENTITY_SERVICE", "true")
        monkeypatch.setenv("USE_GUARDIAN_SERVICE", "true")
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")
        monkeypatch.setenv("JWT_SECRET_KEY", "production-secret-key")
        monkeypatch.setenv("IDENTITY_SERVICE_URL", "https://identity.prod.com")
        monkeypatch.setenv("GUARDIAN_SERVICE_URL", "https://guardian.prod.com")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")

        from importlib import reload

        from app import config as config_module

        reload(config_module)
        from app.config import ProductionConfig as ReloadedProd

        # Should not raise any exception
        ReloadedProd.validate()
