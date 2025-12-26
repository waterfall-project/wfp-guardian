# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Health check resource module.

Health check resource for the Flask application.
This module provides a simple health check endpoint to verify that the service is running.
"""

from datetime import UTC, datetime

from flask import current_app
from flask_restful import Resource

from app.utils import logger
from app.utils.limiter import limiter


class HealthResource(Resource):
    """Resource for health check endpoint.

    This resource provides a simple way to check if the service is running
    and responding to requests. For comprehensive dependency checks, use /ready.
    """

    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """GET /health.

        Returns basic health status to confirm the service is running.

        Returns:
            dict: Health status with timestamp

        Status Codes:
            - 200: Service is healthy
        """
        logger.debug("Health check requested")

        return {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }, 200
