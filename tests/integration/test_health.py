# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Integration tests for application health checks and service connectivity."""

import pytest
import requests


class TestServiceConnectivity:
    """Test connectivity to external services (Identity, Guardian, Redis, PostgreSQL)."""

    def test_postgres_connection(self, app):
        """Test PostgreSQL database connection."""
        from sqlalchemy import text

        with app.app_context():
            from app.models.db import db

            result = db.session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_redis_connection(self, app):
        """Test Redis connection."""
        if not app.config.get("USE_REDIS_CACHE"):
            pytest.skip("Redis not enabled")

        try:
            import redis

            redis_url = app.config["REDIS_URL"]
            client = redis.from_url(redis_url, socket_connect_timeout=2)
            assert client.ping() is True
        except Exception as e:
            pytest.fail(f"Redis connection failed: {e}")

    def test_identity_service_health(self):
        """Test Identity service health endpoint at /v0/health."""
        try:
            response = requests.get("http://localhost:5001/v0/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "timestamp" in data
        except requests.RequestException as e:
            pytest.fail(f"Identity service not reachable: {e}")

    def test_guardian_service_health(self):
        """Test Guardian service health endpoint at /v0/health."""
        try:
            response = requests.get("http://localhost:5002/v0/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "timestamp" in data
        except requests.RequestException as e:
            pytest.fail(f"Guardian service not reachable: {e}")


class TestApplicationHealth:
    """Test application health endpoints."""

    def test_health_endpoint(self, client, api_url):
        """Test /v0/health endpoint returns healthy status."""
        response = client.get(api_url("health"))

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_ready_endpoint(self, client, api_url):
        """Test /v0/ready endpoint with all services enabled."""
        response = client.get(api_url("ready"))

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ready"

        # Check that services are reported as available
        assert "checks" in data
        assert "database" in data["checks"]
        assert data["checks"]["database"]["status"] == "ok"

    def test_ready_endpoint_includes_latency(self, client, api_url):
        """Test that ready endpoint includes latency measurements."""
        response = client.get(api_url("ready"))

        assert response.status_code == 200
        data = response.get_json()

        # Database should have latency info
        if "database" in data["checks"]:
            assert "latency_ms" in data["checks"]["database"]
            assert isinstance(data["checks"]["database"]["latency_ms"], (int, float))

        # Redis should have latency info (if enabled)
        if "redis" in data["checks"]:
            assert "latency_ms" in data["checks"]["redis"]

    def test_ready_endpoint_redis_status(self, client, api_url, app):
        """Test Redis status in ready endpoint."""
        response = client.get(api_url("ready"))

        assert response.status_code == 200
        data = response.get_json()

        # If Redis is enabled, it should be in checks
        if app.config.get("USE_REDIS_CACHE"):
            assert "redis" in data["checks"]
            redis_check = data["checks"]["redis"]
            assert "status" in redis_check
            assert "latency_ms" in redis_check

    def test_version_endpoint(self, client, api_url):
        """Test /version endpoint returns version information."""
        response = client.get(api_url("version"))

        assert response.status_code == 200
        data = response.get_json()
        assert "version" in data
        assert "commit" in data
        assert "build_date" in data
        assert "python_version" in data

    def test_configuration_endpoint(self, client, api_url):
        """Test /v0/configuration endpoint returns config."""
        response = client.get(api_url("configuration"))

        assert response.status_code == 200
        result = response.get_json()
        assert "configuration" in result
        data = result["configuration"]

        # Verify key configurations
        assert "DATABASE_ENDPOINT" in data
        assert "IDENTITY_SERVICE_URL" in data
        assert "GUARDIAN_SERVICE_URL" in data

        # Verify sensitive values are masked (either <MASKED> or "is set")
        if "DATABASE_PASSWORD" in data:
            password_value = data["DATABASE_PASSWORD"]
            assert password_value in ["<MASKED>", "DATABASE_PASSWORD is set"]
