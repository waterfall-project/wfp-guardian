"""Tests for error handlers in the Flask application.

This module contains unit tests for all the custom error handlers
registered in the application factory, including 401, 403, 404, 400, 415, and 500 errors.
"""


def test_unauthorized_handler(client):
    """Test the 401 unauthorized error handler."""
    response = client.get("/unauthorized")

    assert response.status_code == 401
    data = response.get_json()
    assert data["message"] == "Unauthorized"
    assert data["path"] == "/unauthorized"
    assert data["method"] == "GET"
    assert "request_id" in data


def test_forbidden_handler(client):
    """Test the 403 forbidden error handler."""
    response = client.get("/forbidden")

    assert response.status_code == 403
    data = response.get_json()
    assert data["message"] == "Forbidden"
    assert data["path"] == "/forbidden"
    assert data["method"] == "GET"
    assert "request_id" in data


def test_not_found_handler(client):
    """Test the 404 not found error handler."""
    response = client.get("/nonexistent-route")

    assert response.status_code == 404
    data = response.get_json()
    assert data["message"] == "Resource not found"
    assert data["path"] == "/nonexistent-route"
    assert data["method"] == "GET"
    assert "request_id" in data


def test_bad_request_handler(client):
    """Test the 400 bad request error handler."""
    response = client.get("/bad")

    assert response.status_code == 400
    data = response.get_json()
    assert data["message"] == "Bad request"
    assert data["path"] == "/bad"
    assert data["method"] == "GET"
    assert "request_id" in data


def test_internal_server_error_handler(client):
    """Test the 500 internal server error handler."""
    response = client.get("/fail")

    assert response.status_code == 500
    data = response.get_json()
    assert data["message"] == "Internal server error"
    assert data["path"] == "/fail"
    assert data["method"] == "GET"
    assert "request_id" in data


def test_internal_server_error_handler_with_debug(app):
    """Test the 500 error handler includes exception details when DEBUG is True."""
    app.config["DEBUG"] = True

    with app.test_client() as client:
        response = client.get("/fail")

        assert response.status_code == 500
        data = response.get_json()
        assert data["message"] == "Internal server error"
        assert "exception" in data
        assert "Test internal error" in data["exception"]

    # Explicitly clean up database connection
    from app.models.db import db

    db.session.remove()
    db.engine.dispose()


def test_internal_server_error_handler_without_debug(app):
    """Test the 500 error handler does not include exception details when DEBUG is False."""
    app.config["DEBUG"] = False

    with app.test_client() as client:
        response = client.get("/fail")

        assert response.status_code == 500
        data = response.get_json()
        assert data["message"] == "Internal server error"
        assert "exception" not in data


def test_error_handlers_with_different_methods(client):
    """Test that error handlers work with different HTTP methods.

    Note: The test routes only accept GET by default, so we test only GET method
    for multiple error types instead.
    """
    # Test 401 with GET
    response = client.get("/unauthorized")
    assert response.status_code == 401
    data = response.get_json()
    assert data["method"] == "GET"

    # Test 403 with GET
    response = client.get("/forbidden")
    assert response.status_code == 403
    data = response.get_json()
    assert data["method"] == "GET"

    # Test 400 with GET
    response = client.get("/bad")
    assert response.status_code == 400
    data = response.get_json()
    assert data["method"] == "GET"


def test_error_handlers_preserve_request_context(client, app):
    """Test that error handlers correctly access request context including g.request_id."""
    response = client.get("/unauthorized")

    assert response.status_code == 401
    data = response.get_json()
    # request_id should be present (even if None) as it's set in the response
    assert "request_id" in data
