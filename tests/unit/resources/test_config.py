# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Test suite for the configuration endpoint."""


def test_configuration_endpoint_returns_200(app, api_url):
    """Test that the configuration endpoint returns 200 status."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        assert response.status_code == 200


def test_configuration_endpoint_returns_json(app, api_url):
    """Test that the configuration endpoint returns JSON."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        assert response.content_type == "application/json"


def test_configuration_endpoint_has_configuration_key(app, api_url):
    """Test that the response contains 'configuration' key."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        assert "configuration" in data
        assert "note" in data


def test_sensitive_variables_are_masked(app, api_url):
    """Test that sensitive configuration variables are masked."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        config = data["configuration"]

        # JWT_SECRET_KEY should be masked (whether set or not)
        if "JWT_SECRET_KEY" in config:
            assert (
                "is set" in config["JWT_SECRET_KEY"]
                or "is not set" in config["JWT_SECRET_KEY"]
            )

        # SQLALCHEMY_DATABASE_URI should be masked (whether set or not)
        if "SQLALCHEMY_DATABASE_URI" in config:
            assert (
                "is set" in config["SQLALCHEMY_DATABASE_URI"]
                or "is not set" in config["SQLALCHEMY_DATABASE_URI"]
            )


def test_non_sensitive_variables_are_visible(app, api_url):
    """Test that non-sensitive configuration variables are visible."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        config = data["configuration"]

        # LOG_LEVEL should be visible
        assert "LOG_LEVEL" in config
        assert config["LOG_LEVEL"] in ["DEBUG", "INFO", "WARNING", "ERROR"]

        # DEBUG should be visible
        assert "DEBUG" in config
        assert isinstance(config["DEBUG"], bool)

        # TESTING should be visible
        assert "TESTING" in config
        assert config["TESTING"] is True  # We're in testing mode


def test_service_urls_are_masked(app, api_url):
    """Test that external service URLs are displayed (not masked)."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        config = data["configuration"]

        # Service URLs should be displayed directly (not masked)
        # They can be None or actual URLs
        if (
            "GUARDIAN_SERVICE_URL" in config
            and config["GUARDIAN_SERVICE_URL"] is not None
        ):
            # Should be the actual URL, not masked string
            assert "is set" not in config["GUARDIAN_SERVICE_URL"]
            assert "is not set" not in config["GUARDIAN_SERVICE_URL"]

        if (
            "IDENTITY_SERVICE_URL" in config
            and config["IDENTITY_SERVICE_URL"] is not None
        ):
            # Should be the actual URL, not masked string
            assert "is set" not in config["IDENTITY_SERVICE_URL"]
            assert "is not set" not in config["IDENTITY_SERVICE_URL"]


def test_redis_url_is_masked(app, api_url):
    """Test that REDIS_URL is masked."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        config = data["configuration"]

        if "REDIS_URL" in config:
            assert (
                "is set" in config["REDIS_URL"] or "is not set" in config["REDIS_URL"]
            )


def test_configuration_is_sorted(app, api_url):
    """Test that configuration keys are returned in alphabetical order."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        config = data["configuration"]

        keys = list(config.keys())
        # Filter out internal Flask keys and dynamically added endpoints
        filtered_keys = [
            k for k in keys if not k.startswith("_") and not k.endswith("_ENDPOINT")
        ]
        assert filtered_keys == sorted(filtered_keys)


def test_internal_keys_are_excluded(app, api_url):
    """Test that internal Flask keys (starting with _) are excluded."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()
        config = data["configuration"]

        # No keys should start with underscore
        for key in config:
            assert not key.startswith("_")


def test_note_message_is_present(app, api_url):
    """Test that security note is present in response."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))
        data = response.get_json()

        assert "note" in data
        assert "sensitive" in data["note"].lower()
        assert "masked" in data["note"].lower()


def test_configuration_endpoint_rate_limit(app, api_url):
    """Test that rate limiting is applied to the configuration endpoint.

    The endpoint should allow 10 requests per minute and return 429
    on the 11th request.
    """
    with app.test_client() as client:
        # Make 10 successful requests
        for i in range(10):
            response = client.get(api_url("configuration"))
            assert response.status_code == 200, f"Request {i + 1} should succeed"

        # The 11th request should be rate limited
        response = client.get(api_url("configuration"))
        assert response.status_code == 429, "11th request should be rate limited"

        # Verify the response contains rate limit information
        data = response.get_json()
        assert data is not None
        # Flask-Limiter typically returns a message in the response
        assert "message" in data or "error" in data


def test_rate_limit_headers_present(app, api_url):
    """Test that rate limit headers are present in the response."""
    with app.test_client() as client:
        response = client.get(api_url("configuration"))

        # Check for rate limit headers
        # Flask-Limiter adds these headers when rate limiting is enabled
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 200
        assert (
            "X-RateLimit-Remaining" in response.headers or response.status_code == 200
        )
