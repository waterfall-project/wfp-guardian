# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for JWT authentication utilities."""

import uuid
from datetime import datetime, timedelta

import jwt
import pytest
from flask import Flask, g, jsonify

from app.utils.jwt_utils import (
    _build_user_context,
    _decode_jwt_token,
    _extract_token,
    _validate_token_claims,
    _validate_user_company_access_if_needed,
    require_jwt_auth,
)


@pytest.fixture
def jwt_app():
    """Create Flask application for JWT testing."""
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test-secret-key"  # nosec B105
    app.config["JWT_ALGORITHM"] = "HS256"
    app.config["USE_IDENTITY_SERVICE"] = True
    app.config["MOCK_USER_ID"] = "00000000-0000-0000-0000-000000000001"
    app.config["MOCK_COMPANY_ID"] = "00000000-0000-0000-0000-000000000002"
    return app


@pytest.fixture
def valid_token_payload():
    """Create a valid JWT payload."""
    now = datetime.now()
    return {
        "user_id": "12345678-1234-5678-1234-567812345678",
        "company_id": "87654321-4321-8765-4321-876543218765",
        "email": "test@example.com",
        "roles": ["admin", "user"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }


@pytest.fixture
def valid_token(jwt_app, valid_token_payload):
    """Create a valid JWT token."""
    with jwt_app.app_context():
        return jwt.encode(
            valid_token_payload,
            jwt_app.config["JWT_SECRET_KEY"],
            algorithm=jwt_app.config["JWT_ALGORITHM"],
        )


class TestExtractToken:
    """Tests for _extract_token function."""

    def test_extract_token_success(self, jwt_app):
        """Test successful token extraction from cookie."""
        with jwt_app.test_request_context(
            "/", headers={"Cookie": "access_token=test_token_value"}
        ):
            token, error = _extract_token()

            assert token == "test_token_value"  # nosec B105
            assert error is None

    def test_extract_token_missing_cookie(self, jwt_app):
        """Test error when access_token cookie is missing."""
        with jwt_app.test_request_context("/"):
            token, error_tuple = _extract_token()

            assert token is None
            assert error_tuple is not None
            response, status_code = error_tuple
            assert status_code == 401
            json_data = response.get_json()
            assert json_data["error"] == "Missing authentication token"
            assert "access_token" in json_data["message"]


class TestDecodeJwtToken:
    """Tests for _decode_jwt_token function."""

    def test_decode_valid_token(self, jwt_app, valid_token, valid_token_payload):
        """Test decoding a valid JWT token."""
        with jwt_app.app_context():
            payload, error = _decode_jwt_token(valid_token)

            assert error is None
            assert payload is not None
            assert payload["user_id"] == valid_token_payload["user_id"]
            assert payload["company_id"] == valid_token_payload["company_id"]
            assert payload["email"] == valid_token_payload["email"]

    def test_decode_expired_token(self, jwt_app):
        """Test error when token is expired."""
        # Create an expired token
        now = datetime.now()
        expired_payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
            "company_id": "87654321-4321-8765-4321-876543218765",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }

        with jwt_app.app_context():
            expired_token = jwt.encode(
                expired_payload,
                jwt_app.config["JWT_SECRET_KEY"],
                algorithm=jwt_app.config["JWT_ALGORITHM"],
            )

            payload, error_tuple = _decode_jwt_token(expired_token)

            assert payload is None
            assert error_tuple is not None
            response, status_code = error_tuple
            assert status_code == 401
            json_data = response.get_json()
            assert json_data["error"] == "Token expired"

    def test_decode_invalid_token(self, jwt_app):
        """Test error when token is invalid."""
        with jwt_app.app_context():
            payload, error_tuple = _decode_jwt_token("invalid.jwt.token")

            assert payload is None
            assert error_tuple is not None
            response, status_code = error_tuple
            assert status_code == 401
            json_data = response.get_json()
            assert json_data["error"] == "Invalid token"

    def test_decode_token_wrong_secret(self, jwt_app, valid_token_payload):
        """Test error when token is signed with wrong secret."""
        # Create token with different secret
        wrong_token = jwt.encode(
            valid_token_payload,
            "wrong-secret-key",
            algorithm="HS256",
        )

        with jwt_app.app_context():
            payload, error_tuple = _decode_jwt_token(wrong_token)

            assert payload is None
            assert error_tuple is not None
            _, status_code = error_tuple
            assert status_code == 401


class TestValidateTokenClaims:
    """Tests for _validate_token_claims function."""

    def test_validate_claims_success(self):
        """Test successful validation with all required claims."""
        payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
            "company_id": "87654321-4321-8765-4321-876543218765",
        }

        success, error = _validate_token_claims(payload)

        assert success is True
        assert error is None

    def test_validate_claims_missing_user_id(self, jwt_app):
        """Test error when user_id is missing."""
        payload = {
            "company_id": "87654321-4321-8765-4321-876543218765",
        }

        with jwt_app.test_request_context("/"):
            success, error_tuple = _validate_token_claims(payload)

            assert success is False
            assert error_tuple is not None
            response, status_code = error_tuple
            assert status_code == 401
            json_data = response.get_json()
            assert "user_id missing" in json_data["message"]

    def test_validate_claims_missing_company_id(self, jwt_app):
        """Test error when company_id is missing."""
        payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
        }

        with jwt_app.test_request_context("/"):
            success, error_tuple = _validate_token_claims(payload)

            assert success is False
            assert error_tuple is not None
            response, status_code = error_tuple
            assert status_code == 403
            json_data = response.get_json()
            assert "company_id missing" in json_data["message"]


class TestBuildUserContext:
    """Tests for _build_user_context function."""

    def test_build_user_context_full_payload(self):
        """Test building user context with all claims."""
        payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
            "company_id": "87654321-4321-8765-4321-876543218765",
            "email": "test@example.com",
            "roles": ["admin", "user"],
            "iat": 1234567890,
            "exp": 1234567990,
        }

        context = _build_user_context(payload)

        assert context["user_id"] == uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert context["company_id"] == uuid.UUID(
            "87654321-4321-8765-4321-876543218765"
        )
        assert context["email"] == "test@example.com"
        assert context["roles"] == ["admin", "user"]
        assert context["token_issued_at"] == 1234567890
        assert context["token_expires_at"] == 1234567990

    def test_build_user_context_minimal_payload(self):
        """Test building user context with only required claims."""
        payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
            "company_id": "87654321-4321-8765-4321-876543218765",
        }

        context = _build_user_context(payload)

        assert context["user_id"] == uuid.UUID("12345678-1234-5678-1234-567812345678")
        assert context["company_id"] == uuid.UUID(
            "87654321-4321-8765-4321-876543218765"
        )
        assert context["email"] is None
        assert context["roles"] == []
        assert context["token_issued_at"] is None
        assert context["token_expires_at"] is None


class TestRequireJwtAuthDecorator:
    """Tests for require_jwt_auth decorator."""

    def test_decorator_mock_mode(self, jwt_app):
        """Test decorator in mock mode (USE_IDENTITY_SERVICE=False)."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = False

        @require_jwt_auth
        def protected_route():
            return jsonify({"user_id": str(g.user_context["user_id"])})

        with jwt_app.test_request_context("/"):
            response = protected_route()
            json_data = response.get_json()

            assert json_data["user_id"] == "00000000-0000-0000-0000-000000000001"
            assert g.user_context["company_id"] == uuid.UUID(
                "00000000-0000-0000-0000-000000000002"
            )

    def test_decorator_success_with_valid_token(self, jwt_app, valid_token):
        """Test decorator with valid JWT token in cookie."""
        # Disable identity service validation for this test
        jwt_app.config["USE_IDENTITY_SERVICE"] = False

        @require_jwt_auth
        def protected_route():
            return jsonify(
                {
                    "user_id": str(g.user_context["user_id"]),
                    "company_id": str(g.user_context["company_id"]),
                }
            )

        with jwt_app.test_request_context(
            "/", headers={"Cookie": f"access_token={valid_token}"}
        ):
            response = protected_route()
            json_data = response.get_json()

            assert "user_id" in json_data
            assert "company_id" in json_data

    def test_decorator_missing_cookie(self, jwt_app):
        """Test decorator returns 401 when cookie is missing."""

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context("/"):
            result = protected_route()
            # Decorator returns (response, status_code) tuple on error
            response, status_code = result  # type: ignore[misc]

            assert status_code == 401
            json_data = response.get_json()
            assert json_data["error"] == "Missing authentication token"

    def test_decorator_expired_token(self, jwt_app):
        """Test decorator returns 401 when token is expired."""
        now = datetime.now()
        expired_payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
            "company_id": "87654321-4321-8765-4321-876543218765",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }

        with jwt_app.app_context():
            expired_token = jwt.encode(
                expired_payload,
                jwt_app.config["JWT_SECRET_KEY"],
                algorithm=jwt_app.config["JWT_ALGORITHM"],
            )

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context(
            "/", headers={"Cookie": f"access_token={expired_token}"}
        ):
            result = protected_route()
            # Decorator returns (response, status_code) tuple on error
            response, status_code = result  # type: ignore[misc]

            assert status_code == 401
            json_data = response.get_json()
            assert json_data["error"] == "Token expired"

    def test_decorator_invalid_token(self, jwt_app):
        """Test decorator returns 401 when token is invalid."""

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context(
            "/", headers={"Cookie": "access_token=invalid.jwt.token"}
        ):
            result = protected_route()
            # Decorator returns (response, status_code) tuple on error
            response, status_code = result  # type: ignore[misc]

            assert status_code == 401
            json_data = response.get_json()
            assert json_data["error"] == "Invalid token"

    def test_decorator_missing_user_id_claim(self, jwt_app):
        """Test decorator returns 401 when user_id claim is missing."""
        now = datetime.now()
        payload = {
            "company_id": "87654321-4321-8765-4321-876543218765",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }

        with jwt_app.app_context():
            token = jwt.encode(
                payload,
                jwt_app.config["JWT_SECRET_KEY"],
                algorithm=jwt_app.config["JWT_ALGORITHM"],
            )

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context(
            "/", headers={"Cookie": f"access_token={token}"}
        ):
            result = protected_route()
            # Decorator returns (response, status_code) tuple on error
            response, status_code = result  # type: ignore[misc]

            assert status_code == 401
            json_data = response.get_json()
            assert "user_id missing" in json_data["message"]

    def test_decorator_missing_company_id_claim(self, jwt_app):
        """Test decorator returns 403 when company_id claim is missing."""
        now = datetime.now()
        payload = {
            "user_id": "12345678-1234-5678-1234-567812345678",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }

        with jwt_app.app_context():
            token = jwt.encode(
                payload,
                jwt_app.config["JWT_SECRET_KEY"],
                algorithm=jwt_app.config["JWT_ALGORITHM"],
            )

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context(
            "/", headers={"Cookie": f"access_token={token}"}
        ):
            result = protected_route()
            # Decorator returns (response, status_code) tuple on error
            response, status_code = result  # type: ignore[misc]

            assert status_code == 403
            json_data = response.get_json()
            assert "company_id missing" in json_data["message"]

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves original function metadata."""

        @require_jwt_auth
        def protected_route():
            """Test route docstring."""
            return jsonify({"message": "success"})

        assert protected_route.__name__ == "protected_route"
        assert protected_route.__doc__ == "Test route docstring."


class TestValidateUserCompanyAccess:
    """Tests for _validate_user_company_access_if_needed function."""

    def test_validate_user_company_access_disabled(self, jwt_app):
        """Test validation is skipped when USE_IDENTITY_SERVICE is disabled."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = False

        with jwt_app.app_context():
            user_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
            company_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

            result = _validate_user_company_access_if_needed(user_id, company_id)

            assert result is None

    def test_validate_user_company_access_authorized(self, jwt_app, monkeypatch):
        """Test validation succeeds when user has access to company."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = True

        # Mock the validate_user_company_access function to return success
        def mock_validate(user_id, company_id):
            return True, None

        import app.services.identity_client

        monkeypatch.setattr(
            app.services.identity_client,
            "validate_user_company_access",
            mock_validate,
        )

        with jwt_app.app_context():
            user_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
            company_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

            result = _validate_user_company_access_if_needed(user_id, company_id)

            assert result is None

    def test_validate_user_company_access_denied(self, jwt_app, monkeypatch):
        """Test validation fails when user doesn't have access to company."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = True

        # Mock the validate_user_company_access function to return failure
        def mock_validate(user_id, company_id):
            return False, "User does not have access to this company"

        import app.services.identity_client

        monkeypatch.setattr(
            app.services.identity_client,
            "validate_user_company_access",
            mock_validate,
        )

        with jwt_app.app_context():
            user_id = uuid.UUID("12345678-1234-5678-1234-567812345678")
            company_id = uuid.UUID("87654321-4321-8765-4321-876543218765")

            result = _validate_user_company_access_if_needed(user_id, company_id)

            assert result is not None
            response, status_code = result
            assert status_code == 403
            json_data = response.get_json()
            assert json_data["error"] == "Access denied"
            assert "does not have access" in json_data["message"]


class TestRequireJwtAuthWithIdentityService:
    """Tests for require_jwt_auth decorator with Identity service validation."""

    def test_decorator_with_identity_service_success(
        self, jwt_app, valid_token, monkeypatch
    ):
        """Test decorator with Identity service validation succeeds."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = True

        # Mock the validate_user_company_access function to return success
        def mock_validate(user_id, company_id):
            return True, None

        import app.services.identity_client

        monkeypatch.setattr(
            app.services.identity_client,
            "validate_user_company_access",
            mock_validate,
        )

        @require_jwt_auth
        def protected_route():
            return jsonify(
                {
                    "user_id": str(g.user_context["user_id"]),
                    "company_id": str(g.user_context["company_id"]),
                }
            )

        with jwt_app.test_request_context(
            "/", headers={"Cookie": f"access_token={valid_token}"}
        ):
            response = protected_route()
            json_data = response.get_json()

            assert "user_id" in json_data
            assert "company_id" in json_data

    def test_decorator_with_identity_service_denied(
        self, jwt_app, valid_token, monkeypatch
    ):
        """Test decorator with Identity service validation fails."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = True

        # Mock the validate_user_company_access function to return failure
        def mock_validate(user_id, company_id):
            return False, "User does not have access to this company"

        import app.services.identity_client

        monkeypatch.setattr(
            app.services.identity_client,
            "validate_user_company_access",
            mock_validate,
        )

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context(
            "/", headers={"Cookie": f"access_token={valid_token}"}
        ):
            result = protected_route()
            response, status_code = result  # type: ignore[misc]

            assert status_code == 403
            json_data = response.get_json()
            assert json_data["error"] == "Access denied"

    def test_decorator_with_jwt_logging_enabled(
        self, jwt_app, valid_token, monkeypatch
    ):
        """Test decorator logs JWT validation when LOG_JWT_VALIDATION is True."""
        jwt_app.config["USE_IDENTITY_SERVICE"] = True
        jwt_app.config["LOG_JWT_VALIDATION"] = True

        # Mock the validate_user_company_access function
        def mock_validate(user_id, company_id):
            return True, None

        import app.services.identity_client

        monkeypatch.setattr(
            app.services.identity_client,
            "validate_user_company_access",
            mock_validate,
        )

        # Track if logger.debug was called
        debug_called = []

        def mock_debug(message):
            debug_called.append(message)

        @require_jwt_auth
        def protected_route():
            return jsonify({"message": "success"})

        with jwt_app.test_request_context(
            "/protected", headers={"Cookie": f"access_token={valid_token}"}
        ):
            # Monkeypatch the logger
            monkeypatch.setattr(jwt_app.logger, "debug", mock_debug)

            response = protected_route()
            json_data = response.get_json()

            assert json_data["message"] == "success"
            assert len(debug_called) == 1
            assert "JWT validated" in debug_called[0]
            assert "user=" in debug_called[0]
            assert "company=" in debug_called[0]
