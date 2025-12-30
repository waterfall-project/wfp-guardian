# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Flask application factory and initialization.

This module is the main entry point for initializing the Flask application.
It is responsible for configuring Flask extensions, registering custom error
handlers, registering REST API routes, and creating the Flask application
via the create_app factory.

Functions:
    register_extensions: Initialize and register Flask extensions.
    register_error_handlers: Register custom error handlers for the app.
    create_app: Application factory that creates and configures the Flask app.
"""

import os
import sys
from pathlib import Path
from typing import Any

from flask import Flask, abort, g, request
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import inspect
from werkzeug.exceptions import InternalServerError

from app.models.db import db
from app.routes import register_routes
from app.utils.limiter import limiter
from app.utils.logger import logger

# Initialisation des extensions Flask
migrate = Migrate()
ma = Marshmallow()
metrics = PrometheusMetrics(app=None)

# Export create_app
__all__ = ["create_app"]


def register_test_routes(app):
    """Register test-only routes that trigger error handlers directly.

    Args:
        app (Flask): The Flask application instance.
    """

    @app.route("/unauthorized")
    def trigger_unauthorized():
        abort(401)

    @app.route("/forbidden")
    def trigger_forbidden():
        abort(403)

    @app.route("/bad")
    def trigger_bad():
        abort(400)

    @app.route("/fail")
    def trigger_fail():
        raise InternalServerError("Test internal error")


def register_extensions(app):
    """Initialize and register Flask extensions on the application.

    Args:
        app (Flask): The Flask application instance.
    """
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)

    # Get API version from VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        version = version_file.read_text().strip()
        major_version = version.split(".")[0]
        api_version = f"v{major_version}"
    except (FileNotFoundError, IndexError) as e:
        logger.warning(f"Failed to read VERSION file: {e}. Using default 'v0'.")
        api_version = "v0"

    # Initialize Prometheus metrics with dynamic version path
    # This will automatically create /{api_version}/metrics endpoint
    metrics.path = f"/{api_version}/metrics"
    metrics.init_app(app)
    logger.info(f"Prometheus metrics initialized at /{api_version}/metrics endpoint.")

    # Configure rate limiter settings in app.config
    # Flask-Limiter reads from app.config for configuration
    rate_limit_storage = app.config.get("RATE_LIMIT_STORAGE", "memory")
    redis_url = app.config.get("REDIS_URL")

    # Configure storage URI based on storage type
    if rate_limit_storage == "redis" and redis_url:
        app.config["RATELIMIT_STORAGE_URI"] = redis_url
    else:
        app.config["RATELIMIT_STORAGE_URI"] = "memory://"

    # Set strategy
    app.config["RATELIMIT_STRATEGY"] = app.config.get(
        "RATE_LIMIT_STRATEGY", "fixed-window"
    )

    # Initialize rate limiter with app
    limiter.init_app(app)

    if app.config.get("RATE_LIMIT_ENABLED", False):
        logger.info(
            f"Rate limiter enabled with storage: {rate_limit_storage}, "
            f"strategy: {app.config['RATELIMIT_STRATEGY']}"
        )
    else:
        logger.info(
            "Rate limiter initialized but disabled (no limits will be enforced)."
        )

    logger.info("Extensions registered successfully.")


def register_error_handlers(app):
    """Register custom error handlers for the Flask application.

    Args:
        app (Flask): The Flask application instance.
    """

    @app.errorhandler(401)
    def unauthorized(err):
        """Handler for 401 (unauthorized) errors."""
        logger.warning(
            "Unauthorized access attempt detected.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "invalid_token",
            "message": "Unauthorized",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }
        return response, 401

    @app.errorhandler(403)
    def forbidden(err):
        """Handler for 403 (forbidden) errors."""
        logger.warning(
            "Forbidden access attempt detected.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "forbidden",
            "message": "Forbidden",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }
        return response, 403

    @app.errorhandler(404)
    def not_found(err):
        """Handler for 404 (resource not found) errors."""
        logger.warning(
            "Resource not found.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "not_found",
            "message": "Resource not found",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }
        return response, 404

    @app.errorhandler(400)
    def bad_request(err):
        """Handler for 400 (bad request) errors."""
        logger.warning(
            "Bad request received.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "bad_request",
            "message": "Bad request",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }
        return response, 400

    @app.errorhandler(415)
    def unsupported_media_type(err):
        """Handler for 415 (unsupported media type) errors."""
        logger.warning(
            "Unsupported media type.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "unsupported_media_type",
            "message": "Unsupported media type",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
                "exception": str(err),
            },
        }
        return response, 415

    @app.errorhandler(409)
    def conflict(err):
        """Handler for 409 (conflict) errors."""
        logger.warning(
            "Conflict detected.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "conflict",
            "message": "Conflict",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }
        return response, 409

    @app.errorhandler(422)
    def unprocessable_entity(err):
        """Handler for 422 (unprocessable entity) errors."""
        logger.warning(
            "Unprocessable entity.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "validation_error",
            "message": "Unprocessable entity",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }
        return response, 422

    @app.errorhandler(429)
    def ratelimit_handler(err):
        """Handler for 429 (too many requests) errors."""
        logger.warning(
            "Rate limit exceeded.",
            str(err),
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response = {
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded. Please try again later.",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
                "description": (
                    str(err.description) if hasattr(err, "description") else str(err)
                ),
            },
        }
        return response, 429

    @app.errorhandler(500)
    def internal_error(err):
        logger.error(
            "Internal server error",
            str(err),
            exc_info=True,
            path=request.path,
            method=request.method,
            request_id=getattr(g, "request_id", None),
        )
        response: dict[str, Any] = {
            "error": "internal_error",
            "message": "Internal server error",
            "details": {
                "path": request.path,
                "method": request.method,
                "request_id": getattr(g, "request_id", None),
            },
        }

        if app.config.get("DEBUG"):
            response["details"]["exception"] = str(err)
        return response, 500

    logger.info("Error handlers registered successfully.")


def _get_endpoint_string(host, port):
    """Format endpoint as HOST:PORT if both exist, otherwise just host.

    Args:
        host: The host value
        port: The port value

    Returns:
        str: Formatted endpoint string or None
    """
    if host and port:
        return f"{host}:{port}"
    if host:
        return host
    return None


def _format_config_value(key, value, sensitive_keys):
    """Format a config value for logging, masking if sensitive.

    Args:
        key: The configuration key
        value: The configuration value
        sensitive_keys: Set of sensitive key patterns

    Returns:
        str: Formatted key=value string
    """
    if any(sensitive in key.upper() for sensitive in sensitive_keys):
        masked_value = "<MASKED>" if value else "<NOT SET>"
        return f"  {key}={masked_value}"

    # Convert non-serializable types to strings
    if isinstance(value, (str, int, bool, float)) or value is None:
        return f"  {key}={value}"
    return f"  {key}={type(value).__name__}"


def _log_environment_variables(app):
    """Log environment variables at application startup with sensitive values masked.

    Args:
        app (Flask): The Flask application instance.
    """
    sensitive_keys = {
        "JWT_SECRET_KEY",
        "SECRET_KEY",
        "SQLALCHEMY_DATABASE_URI",
        "DATABASE_PASSWORD",
        "REDIS_PASSWORD",
        "REDIS_URL",
        "PASSWORD",
        "TOKEN",
        "API_KEY",
    }

    config = app.config
    env_vars = []

    # Add formatted endpoints for Database and Redis
    db_endpoint = _get_endpoint_string(
        config.get("DATABASE_HOST"), config.get("DATABASE_PORT")
    )
    if db_endpoint:
        env_vars.append(f"  DATABASE_ENDPOINT={db_endpoint}")

    redis_endpoint = _get_endpoint_string(
        config.get("REDIS_HOST"), config.get("REDIS_PORT")
    )
    if redis_endpoint:
        env_vars.append(f"  REDIS_ENDPOINT={redis_endpoint}")

    # Process all configuration keys
    for key in sorted(config.keys()):
        if not key.startswith("_"):
            env_vars.append(_format_config_value(key, config.get(key), sensitive_keys))

    # Log with proper formatting
    config_str = "\n".join(sorted(set(env_vars)))
    logger.info(f"Application configuration:\n{config_str}")


def create_app(config_class):
    """Factory to create and configure the Flask application.

    Args:
        config_class: The configuration class or import path to use for Flask.

    Returns:
        Flask: The configured and ready-to-use Flask application instance.
    """
    app = Flask(__name__)

    app.config.from_object(config_class)

    # Validate configuration consistency
    from werkzeug.utils import import_string

    if isinstance(config_class, str):
        config_cls = import_string(config_class)
    else:
        config_cls = config_class

    if hasattr(config_cls, "validate"):
        config_cls.validate()

    env = os.getenv("FLASK_ENV")
    logger.info("Creating app in environment.", environment=env)

    # Configure CORS if enabled
    if app.config.get("CORS_ENABLED", True):
        cors_origins = app.config.get("CORS_ORIGINS", "*")
        # Convert comma-separated string to list
        if isinstance(cors_origins, str):
            origins_list = [origin.strip() for origin in cors_origins.split(",")]
        else:
            origins_list = cors_origins

        cors_allow_credentials = app.config.get("CORS_ALLOW_CREDENTIALS", True)
        cors_max_age = app.config.get("CORS_MAX_AGE", 3600)

        CORS(
            app,
            supports_credentials=cors_allow_credentials,
            origins=origins_list,
            max_age=cors_max_age,
        )
        logger.info(
            f"CORS enabled with origins: {origins_list}, "
            f"credentials: {cors_allow_credentials}, max_age: {cors_max_age}"
        )
    else:
        logger.info("CORS disabled.")

    register_extensions(app)
    register_error_handlers(app)
    register_routes(app)
    if app.config.get("TESTING"):
        register_test_routes(app)

    # Validate critical configuration at startup
    _validate_startup_config(app)

    # Seed permissions at startup (only after extensions are registered)
    with app.app_context():
        _seed_permissions_at_startup()

    # Log environment variables (with sensitive values masked)
    _log_environment_variables(app)

    logger.info("App created successfully.")
    return app


def _seed_permissions_at_startup() -> None:
    """Seed permissions from permissions.json at application startup.

    Must be called within an active app_context.
    Uses local import to avoid circular dependencies.
    """
    try:
        from app.services.permission_seeder import seed_permissions_on_startup

        seed_permissions_on_startup()
    except Exception as e:
        logger.error(f"Failed to seed permissions: {e}")
        # Don't fail app startup if permission seeding fails


def _validate_startup_config(app: Flask) -> None:
    """Validate critical configuration values at application startup.

    Args:
        app: Flask application instance.

    Raises:
        ValueError: If critical configuration is missing or invalid.
    """
    # Validate INTERNAL_SERVICE_TOKEN is configured
    internal_token = app.config.get("INTERNAL_SERVICE_TOKEN")
    if not internal_token:
        logger.error(
            "INTERNAL_SERVICE_TOKEN is not configured. "
            "Bootstrap endpoints will not function."
        )
        raise ValueError(
            "INTERNAL_SERVICE_TOKEN must be configured for service-to-service authentication"
        )

    if len(internal_token) < 32:
        logger.warning(
            f"INTERNAL_SERVICE_TOKEN is too short ({len(internal_token)} chars). "
            "Minimum 32 characters recommended for security."
        )

    logger.info("Startup configuration validated successfully.")
