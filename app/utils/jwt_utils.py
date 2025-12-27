# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""JWT authentication utilities.

This module provides JWT token validation and authentication decorators
for protecting API endpoints. It supports both real JWT validation (when
USE_IDENTITY_SERVICE is enabled) and mock mode (when disabled).
"""

import uuid
from functools import wraps
from typing import Any

import jwt
from flask import current_app, g, jsonify, request


def _validate_user_company_access_if_needed(
    user_id: uuid.UUID, company_id: uuid.UUID
) -> tuple[Any, int] | None:
    """Validate user access to company if Identity service is enabled.

    Args:
        user_id: UUID of the user from JWT token.
        company_id: UUID of the company from JWT token.

    Returns:
        None if validation passes or Identity service is disabled.
        A tuple of (response, status_code) if validation fails.
    """
    # Skip validation if Identity service is disabled
    if not current_app.config.get("USE_IDENTITY_SERVICE", True):
        return None

    # Import here to avoid circular dependency
    from app.services.identity_client import validate_user_company_access

    # Validate user has access to the company
    is_authorized, error_message = validate_user_company_access(user_id, company_id)

    if not is_authorized:
        current_app.logger.warning(
            f"User {user_id} denied access to company {company_id}: {error_message}"
        )
        return (
            jsonify(
                {
                    "error": "Access denied",
                    "message": error_message,
                }
            ),
            403,
        )

    return None


def _extract_token() -> tuple[str | None, tuple[Any, int] | None]:
    """Extract JWT token from access_token httpOnly cookie.

    Returns:
        A tuple of (token, error_tuple). If successful, token is the JWT string
        and error_tuple is None. If failed, token is None and error_tuple is a
        (response, status_code) tuple that Flask will understand.
    """
    token = request.cookies.get("access_token")

    if not token:
        return None, (
            jsonify(
                {
                    "error": "Missing authentication token",
                    "message": "access_token cookie required",
                }
            ),
            401,
        )

    return token, None


def _decode_jwt_token(token: str) -> tuple[dict | None, tuple[Any, int] | None]:
    """Decode and validate JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        A tuple of (payload, error_tuple). If successful, payload contains
        the decoded claims and error_tuple is None. If failed, payload is None
        and error_tuple is a (response, status_code) tuple that Flask will understand.
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config.get("JWT_ALGORITHM", "HS256")],
        )
        return payload, None

    except jwt.ExpiredSignatureError:
        return None, (
            jsonify({"error": "Token expired", "message": "JWT token has expired"}),
            401,
        )

    except jwt.InvalidTokenError as e:
        current_app.logger.warning(f"Invalid JWT token: {e}")
        return None, (
            jsonify({"error": "Invalid token", "message": "JWT token is invalid"}),
            401,
        )


def _validate_token_claims(payload: dict) -> tuple[bool, tuple[Any, int] | None]:
    """Validate required claims in JWT payload.

    Args:
        payload: The decoded JWT payload dictionary.

    Returns:
        A tuple of (success, error_tuple). If successful, success is True
        and error_tuple is None. If failed, success is False and error_tuple is a
        (response, status_code) tuple that Flask will understand.
    """
    user_id = payload.get("user_id")
    company_id = payload.get("company_id")

    # Validate user_id is present
    if not user_id:
        return False, (
            jsonify(
                {
                    "error": "Invalid token payload",
                    "message": "user_id missing in token",
                }
            ),
            401,
        )

    # Validate company_id is present (multi-tenancy requirement)
    if not company_id:
        return False, (
            jsonify(
                {
                    "error": "Invalid token payload",
                    "message": "company_id missing in token (multi-tenancy required)",
                }
            ),
            403,
        )

    return True, None


def _build_user_context(payload: dict) -> dict:
    """Build user context dictionary from JWT payload.

    Args:
        payload: The decoded JWT payload dictionary.

    Returns:
        A dictionary containing user context with validated claims.
    """
    return {
        "user_id": uuid.UUID(payload["user_id"]),
        "company_id": uuid.UUID(payload["company_id"]),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
        "token_issued_at": payload.get("iat"),
        "token_expires_at": payload.get("exp"),
    }


def require_jwt_auth(f):
    """Decorator to require JWT authentication on Flask routes.

    This decorator validates JWT tokens from the access_token httpOnly cookie and
    extracts user context (user_id, company_id, roles, etc.). If USE_IDENTITY_SERVICE
    is disabled, it uses mock values from MOCK_USER_ID and MOCK_COMPANY_ID.

    The decorator extracts and validates:
    - access_token cookie presence
    - JWT signature and expiration
    - Required claims: user_id, company_id
    - Optional claims: email, roles, iat, exp

    The validated context is stored in Flask's g.user_context dictionary with:
    - user_id: UUID of the authenticated user
    - company_id: UUID of the user's company (multi-tenancy)
    - email: User's email address (optional)
    - roles: List of user roles (optional)
    - token_issued_at: Token issuance timestamp (optional)
    - token_expires_at: Token expiration timestamp (optional)

    Args:
        f: The Flask route function to decorate.

    Returns:
        The decorated function with JWT authentication.

    Raises:
        401: If access_token cookie is missing or token is invalid/expired.
        403: If required claims (company_id) are missing.

    Example:
        @app.route('/protected')
        @require_jwt_auth
        def protected_route():
            user_id = g.user_context['user_id']
            return jsonify({'user_id': str(user_id)})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Mock mode: skip JWT validation if identity service is disabled
        if current_app.config.get("USE_IDENTITY_SERVICE", True) is False:
            mock_user_id = current_app.config.get(
                "MOCK_USER_ID", "00000000-0000-0000-0000-000000000001"
            )
            mock_company_id = current_app.config.get(
                "MOCK_COMPANY_ID", "00000000-0000-0000-0000-000000000001"
            )
            g.user_context = {
                "user_id": uuid.UUID(mock_user_id),
                "company_id": uuid.UUID(mock_company_id),
            }
            return f(*args, **kwargs)

        # 1. Extract token from access_token cookie
        token, error = _extract_token()
        if error:
            return error

        # At this point, token is guaranteed to be a string (not None)
        assert token is not None

        # 2. Decode and validate JWT token
        payload, error = _decode_jwt_token(token)
        if error:
            return error

        # At this point, payload is guaranteed to be a dict (not None)
        assert payload is not None

        # 3. Validate required claims
        valid, error = _validate_token_claims(payload)
        if not valid:
            return error

        # 4. Build and store user context
        g.user_context = _build_user_context(payload)

        # 5. Validate user access to company (hierarchical permissions)
        error = _validate_user_company_access_if_needed(
            g.user_context["user_id"], g.user_context["company_id"]
        )
        if error:
            return error

        # 6. Optional JWT validation logging
        if current_app.config.get("LOG_JWT_VALIDATION", False):
            current_app.logger.debug(
                f"JWT validated: user={payload['user_id']}, "
                f"company={payload['company_id']}, endpoint={request.endpoint}"
            )

        # 7. Call the protected function
        return f(*args, **kwargs)

    return decorated_function


def get_company_id_from_jwt() -> str:
    """Extract company_id from the current request's JWT token.

    This function retrieves the company_id from Flask's g.user_context,
    which is populated by the @require_jwt_auth decorator.

    Returns:
        str: The company_id from the JWT token as a string.

    Raises:
        RuntimeError: If called outside a request context or before @require_jwt_auth.

    Example:
        @app.route('/my-resource')
        @require_jwt_auth
        def get_my_resource():
            company_id = get_company_id_from_jwt()
            # Use company_id to filter resources...
    """
    if not hasattr(g, "user_context") or "company_id" not in g.user_context:
        raise RuntimeError(
            "get_company_id_from_jwt() called before JWT authentication. "
            "Ensure @require_jwt_auth decorator is applied to the route."
        )

    return str(g.user_context["company_id"])
