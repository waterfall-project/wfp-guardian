# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Readiness check resource module.

Readiness check resource for the Flask application.
This module provides a comprehensive readiness check endpoint to verify that all
external dependencies (database, redis, guardian, identity) are available.
"""

from datetime import datetime, timezone
from typing import Any

import requests
from flask import current_app
from flask_restful import Resource
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.models.db import db
from app.utils import logger
from app.utils.limiter import limiter


class ReadyResource(Resource):
    """Resource for readiness check endpoint.

    This resource provides comprehensive checks for all external dependencies
    including database, redis, guardian service, and identity service.
    """

    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """GET /ready.

        Returns comprehensive readiness information including all dependency checks.

        Returns:
            dict: Readiness status with individual check results

        Status Codes:
            - 200: Service is ready and all checks pass
            - 503: Service is not ready (one or more checks failed)
        """
        logger.debug("Readiness check requested")

        ready_data: dict[str, Any] = {
            "status": "ready",
            "checks": {},
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        all_checks_passed = True

        # Database check (always required)
        all_checks_passed &= self._add_check_result(
            ready_data, "database", self._check_database()
        )

        # Redis check (if enabled)
        all_checks_passed &= self._add_optional_check_result(
            ready_data, "redis", "USE_REDIS_CACHE", self._check_redis
        )

        # Guardian check (if enabled)
        all_checks_passed &= self._add_optional_check_result(
            ready_data, "guardian", "USE_GUARDIAN_SERVICE", self._check_guardian
        )

        # Identity check (if enabled)
        all_checks_passed &= self._add_optional_check_result(
            ready_data, "identity", "USE_IDENTITY_SERVICE", self._check_identity
        )

        # Determine overall status and HTTP code
        if not all_checks_passed:
            ready_data["status"] = "degraded"
            return ready_data, 503

        return ready_data, 200

    def _add_check_result(
        self, ready_data: dict[str, Any], check_name: str, check_result: dict[str, Any]
    ) -> bool:
        """Add a check result to ready_data and return if check passed.

        Args:
            ready_data: The readiness data dictionary
            check_name: Name of the check (e.g., 'database', 'redis')
            check_result: Result from check function with 'healthy' key

        Returns:
            bool: True if check passed, False otherwise
        """
        ready_data["checks"][check_name] = {
            "status": "ok" if check_result["healthy"] else "error",
            "latency_ms": check_result.get("latency_ms", 0),
        }
        return bool(check_result["healthy"])

    def _add_optional_check_result(
        self, ready_data: dict[str, Any], check_name: str, config_key: str, check_func
    ) -> bool:
        """Add an optional check result if the feature is enabled.

        Args:
            ready_data: The readiness data dictionary
            check_name: Name of the check
            config_key: Config key to check if feature is enabled
            check_func: Function to call for the check

        Returns:
            bool: True if check passed or disabled, False if enabled and failed
        """
        if current_app.config.get(config_key, False):
            check_result = check_func()
            return self._add_check_result(ready_data, check_name, check_result)

        # Feature disabled, mark as ok
        ready_data["checks"][check_name] = {"status": "ok", "latency_ms": 0}
        return True

    def _check_database(self):
        """Check database connectivity and measure latency.

        Returns:
            dict: Database health status with latency
        """
        try:
            start_time = datetime.now(timezone.utc)
            result = db.session.execute(text("SELECT 1"))
            end_time = datetime.now(timezone.utc)

            if result.scalar() == 1:
                latency_ms = (end_time - start_time).total_seconds() * 1000
                return {
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                }

            return {
                "healthy": False,
                "latency_ms": 0,
            }

        except (OSError, SQLAlchemyError) as e:
            logger.error(f"Database readiness check failed: {str(e)}")
            return {
                "healthy": False,
                "latency_ms": 0,
            }

    def _check_redis(self):
        """Check Redis connectivity and measure latency.

        Returns:
            dict: Redis health status with latency
        """
        try:
            import redis

            redis_url = current_app.config.get("REDIS_URL")
            if not redis_url:
                return {
                    "healthy": False,
                    "latency_ms": 0,
                }

            start_time = datetime.now(timezone.utc)
            client = redis.from_url(redis_url, socket_connect_timeout=2)
            client.ping()
            end_time = datetime.now(timezone.utc)

            latency_ms = (end_time - start_time).total_seconds() * 1000
            return {
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            logger.error(f"Redis readiness check failed: {str(e)}")
            return {
                "healthy": False,
                "latency_ms": 0,
            }

    def _check_guardian(self):
        """Check Guardian service connectivity and measure latency.

        Returns:
            dict: Guardian service health status with latency
        """
        try:
            guardian_url = current_app.config.get("GUARDIAN_SERVICE_URL")
            if not guardian_url:
                return {
                    "healthy": False,
                    "latency_ms": 0,
                }

            # Use health endpoint if available
            health_url = f"{guardian_url.rstrip('/')}/health"
            timeout = current_app.config.get("EXTERNAL_SERVICES_TIMEOUT", 5)

            start_time = datetime.now(timezone.utc)
            response = requests.get(health_url, timeout=timeout)
            end_time = datetime.now(timezone.utc)

            latency_ms = (end_time - start_time).total_seconds() * 1000

            if response.status_code == 200:
                return {
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                }

            return {
                "healthy": False,
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            logger.error(f"Guardian service readiness check failed: {str(e)}")
            return {
                "healthy": False,
                "latency_ms": 0,
            }

    def _check_identity(self):
        """Check Identity service connectivity and measure latency.

        Returns:
            dict: Identity service health status with latency
        """
        try:
            identity_url = current_app.config.get("IDENTITY_SERVICE_URL")
            if not identity_url:
                return {
                    "healthy": False,
                    "latency_ms": 0,
                }

            # Use health endpoint if available
            health_url = f"{identity_url.rstrip('/')}/health"
            timeout = current_app.config.get("EXTERNAL_SERVICES_TIMEOUT", 5)

            start_time = datetime.now(timezone.utc)
            response = requests.get(health_url, timeout=timeout)
            end_time = datetime.now(timezone.utc)

            latency_ms = (end_time - start_time).total_seconds() * 1000

            if response.status_code == 200:
                return {
                    "healthy": True,
                    "latency_ms": round(latency_ms, 2),
                }

            return {
                "healthy": False,
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            logger.error(f"Identity service readiness check failed: {str(e)}")
            return {
                "healthy": False,
                "latency_ms": 0,
            }
