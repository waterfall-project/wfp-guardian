# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Configuration endpoint resource."""

from datetime import datetime, timedelta

from flask import current_app
from flask_restful import Resource

from app.utils.guardian import Operation, access_required
from app.utils.jwt_utils import require_jwt_auth
from app.utils.limiter import limiter


class ConfigResource(Resource):
    """API resource for retrieving application configuration.

    This endpoint returns all configuration variables with sensitive values
    masked for security purposes.

    Rate limiting is applied to prevent abuse:
    - 10 requests per minute per IP address
    """

    # List of sensitive configuration keys that should be masked
    SENSITIVE_KEYS = {
        "JWT_SECRET_KEY",
        "SECRET_KEY",
        "SQLALCHEMY_DATABASE_URI",
        "DATABASE_PASSWORD",
        "REDIS_PASSWORD",
        "REDIS_URL",
    }

    # Keys that should be displayed as HOST:PORT format
    HOST_PORT_DISPLAY = {
        "DATABASE": ("DATABASE_HOST", "DATABASE_PORT"),
        "REDIS": ("REDIS_HOST", "REDIS_PORT"),
    }

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """Retrieve application configuration.

        Returns a dictionary of all configuration variables where sensitive
        values are replaced with '<VARIABLE> is set' to prevent exposure.

        Rate limit: 10 requests per minute per IP address.

        Returns:
            dict: Configuration dictionary with masked sensitive values.
                - For sensitive keys: '<KEY_NAME> is set' if value exists
                - For non-sensitive keys: actual value
                - Service URLs displayed directly
                - Database and Redis shown as HOST:PORT
                - All keys are returned in alphabetical order

        Raises:
            429: Too Many Requests if rate limit is exceeded
        """
        config = current_app.config
        result = {}

        # Add formatted HOST:PORT entries
        for service, (host_key, port_key) in self.HOST_PORT_DISPLAY.items():
            host = config.get(host_key)
            port = config.get(port_key)
            if host and port:
                result[f"{service}_ENDPOINT"] = f"{host}:{port}"
            elif host:
                result[f"{service}_ENDPOINT"] = host

        # Get all configuration keys
        for key in sorted(config.keys()):
            # Skip internal Flask keys that start with underscore
            if key.startswith("_"):
                continue

            value = config.get(key)

            # Mask sensitive configuration values
            if key in self.SENSITIVE_KEYS:
                if value:
                    result[key] = f"{key} is set"
                else:
                    result[key] = f"{key} is not set"
            else:
                # Convert non-JSON-serializable types to strings
                result[key] = self._serialize_value(value)

        return {
            "configuration": result,
            "note": "Sensitive values are masked for security",
        }

    @staticmethod
    def _serialize_value(value):
        """Convert a value to a JSON-serializable format.

        Args:
            value: The value to serialize.

        Returns:
            A JSON-serializable representation of the value.
        """
        # Handle timedelta objects
        if isinstance(value, timedelta):
            return str(value)
        # Handle datetime objects
        if isinstance(value, datetime):
            return value.isoformat()
        # Handle lists
        if isinstance(value, list):
            return [ConfigResource._serialize_value(item) for item in value]
        # Handle dictionaries
        if isinstance(value, dict):
            return {k: ConfigResource._serialize_value(v) for k, v in value.items()}
        # Return other types as-is (str, int, bool, None, etc.)
        return value
