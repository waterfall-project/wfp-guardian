<div align="center">
  <img src="../../docs/assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Unit Tests

This document describes the unit testing environment, configuration, fixtures, and best practices.

## Table of Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [Fixtures](#fixtures)
- [Running Unit Tests](#running-unit-tests)
- [Writing Unit Tests](#writing-unit-tests)
- [Best Practices](#best-practices)

## Overview

Unit tests are **fast, isolated tests** that validate individual components without external dependencies. They use:

- **SQLite in-memory database** - Fast, no persistence
- **No external services** - Identity/Guardian disabled, mocked when needed
- **No Redis** - Caching disabled
- **No rate limiting** - All endpoints freely accessible

**Current Status:**
- **384 tests** (1 skipped)
- **Execution time:** ~5 seconds
- **Coverage contribution:** ~90% of total coverage

## Configuration

### Environment File: `.env.testing`

Located at project root, this file configures the unit test environment:

```dotenv
# Unit Testing Environment Configuration

# Flask Configuration
FLASK_ENV=testing
SERVICE_PORT=5000
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Database Configuration - SQLite in memory
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///memory

# JWT Configuration
JWT_ALGORITHM=HS256

# Redis Configuration - Disabled for unit tests
USE_REDIS_CACHE=false

# External Services - Disabled for unit tests
USE_IDENTITY_SERVICE=false
USE_GUARDIAN_SERVICE=false

# Pagination
PAGE_LIMIT=20
MAX_PAGE_LIMIT=100

# CORS
CORS_ENABLED=true

# Rate Limiting - Disabled for unit tests
RATE_LIMIT_ENABLED=false

# Mock Users (used when services are disabled)
MOCK_USER_ID=00000000-0000-0000-0000-000000000001
MOCK_COMPANY_ID=00000000-0000-0000-0000-000000000001
```

### Configuration Loading Order

The `tests/unit/conftest.py` loads configuration in a specific order to ensure proper isolation:

```python
# 1. Set environment variables FIRST (highest priority)
os.environ["FLASK_ENV"] = "testing"
os.environ["USE_IDENTITY_SERVICE"] = "false"
os.environ["USE_GUARDIAN_SERVICE"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["PAGE_LIMIT"] = "20"
os.environ["MAX_PAGE_LIMIT"] = "100"

# 2. Load .env.testing (does NOT override existing vars)
dotenv_path = Path(__file__).parent.parent.parent / ".env.testing"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
```

This ensures unit tests always run in the correct isolated mode, even if `.env.testing` has different values.

## Fixtures

### Core Fixtures

#### `app` Fixture
**Scope:** `function` (new app for each test)
**Purpose:** Creates a Flask application with TestingConfig

```python
@fixture
def app():
    """Create Flask application for testing.

    - Uses TestingConfig
    - Creates fresh in-memory SQLite database
    - Drops database after test completion
    """
    app = create_app("app.config.TestingConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
        db.session.remove()
        db.engine.dispose()
```

**Usage:**
```python
def test_app_configuration(app):
    assert app.config["TESTING"] is True
    assert app.config["USE_IDENTITY_SERVICE"] is False
```

#### `client` Fixture
**Scope:** `function`
**Purpose:** Provides test client for making HTTP requests

```python
@fixture
def client(app):
    """Create test client for HTTP requests."""
    return app.test_client()
```

**Usage:**
```python
def test_health_endpoint(client):
    response = client.get("/v0/health")
    assert response.status_code == 200
```

#### `session` Fixture
**Scope:** `function`
**Purpose:** Provides database session for direct DB operations

```python
@fixture
def session(app):
    """Provide database session for tests."""
    with app.app_context():
        yield db.session
```

**Usage:**
```python
def test_create_dummy(session):
    dummy = Dummy(name="test")
    session.add(dummy)
    session.commit()
    assert dummy.id is not None
```

### Helper Fixtures

#### `api_version` Fixture
**Purpose:** Returns API version prefix (e.g., "v0")

```python
@fixture
def api_version(app):
    """Get API version prefix from VERSION file."""
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    try:
        version = version_file.read_text().strip()
        major_version = version.split(".")[0]
        return f"v{major_version}"
    except (FileNotFoundError, IndexError):
        return "v0"
```

#### `api_url` Fixture
**Purpose:** Helper to build API URLs with version prefix

```python
@fixture
def api_url(api_version):
    """Build API URL with version prefix."""
    def _build_url(path: str) -> str:
        path = path.lstrip("/")
        return f"/{api_version}/{path}"
    return _build_url
```

**Usage:**
```python
def test_version_endpoint(client, api_url):
    response = client.get(api_url("version"))
    assert response.status_code == 200
```

### Future Fixtures (To Be Added)

As the project grows, additional fixtures will be added:

- **Authentication fixtures** - Mock JWT tokens, user contexts
- **Data fixtures** - Pre-populated test data
- **Mock service fixtures** - Mock responses from Identity/Guardian
- **Request context fixtures** - Custom headers, request IDs

## Running Unit Tests

### Basic Execution

```bash
# All unit tests
make test-unit

# Specific test file
pytest tests/unit/test_config.py -v

# Specific test function
pytest tests/unit/test_config.py::test_database_configuration -v

# Tests matching pattern
pytest tests/unit/ -k "test_health" -v

# With coverage
pytest tests/unit/ --cov=app --cov-report=term
```

### Useful Flags

```bash
# Stop on first failure
pytest tests/unit/ -x

# Show print statements
pytest tests/unit/ -s

# Run last failed tests
pytest tests/unit/ --lf

# Verbose output with test names
pytest tests/unit/ -v

# Very verbose with full diff
pytest tests/unit/ -vv

# Parallel execution (requires pytest-xdist)
pytest tests/unit/ -n auto
```

## Writing Unit Tests

### Test Structure

```python
"""
Module docstring explaining what is being tested.
"""

def test_function_name(client, session):
    """Test docstring explaining the specific behavior."""
    # Arrange - Set up test data
    data = {"name": "test"}

    # Act - Perform the action
    response = client.post("/v0/resource", json=data)

    # Assert - Verify the results
    assert response.status_code == 201
    assert response.json["name"] == "test"
```

### Test Organization

Tests are organized by the component they test:

```
tests/unit/
├── test_app_init.py           # Application initialization
├── test_config.py             # Configuration classes
├── test_error_handlers.py     # Error handling
├── test_jwt_utils.py          # JWT utilities
├── test_logger.py             # Logging
├── test_run.py                # Application entry point
├── test_wsgi.py               # WSGI configuration
├── models/
│   └── test_dummy_model.py    # Database models
├── resources/
│   ├── test_config.py         # /v0/configuration endpoint
│   ├── test_dummy_res.py      # /v0/dummies endpoints
│   ├── test_health.py         # /v0/health endpoint
│   ├── test_ready.py          # /v0/ready endpoint
│   └── test_version.py        # /v0/version endpoint
└── services/
    ├── test_guardian_client.py # Guardian service client
    └── test_identity_client.py # Identity service client
```

### Naming Conventions

- **Test files:** `test_<module_name>.py`
- **Test classes:** `Test<FeatureName>` (optional, for grouping)
- **Test functions:** `test_<what_is_being_tested>`

Examples:
```python
# Good naming
def test_health_endpoint_returns_200(client):
    """Test that /v0/health returns 200 OK."""

def test_create_dummy_with_valid_data(client):
    """Test creating a dummy with all required fields."""

def test_authentication_fails_with_invalid_token(client):
    """Test that invalid JWT token returns 401."""

# Class-based grouping
class TestDummyValidation:
    """Test input validation for Dummy resource."""

    def test_name_required(self, client):
        """Test that name field is required."""

    def test_name_too_long(self, client):
        """Test that name cannot exceed max length."""
```

### Testing Different Scenarios

```python
import pytest

# Parametrized tests for multiple inputs
@pytest.mark.parametrize("value,expected", [
    ("valid", True),
    ("", False),
    (None, False),
])
def test_validation(value, expected):
    result = validate(value)
    assert result == expected

# Testing exceptions
def test_invalid_config_raises_error():
    with pytest.raises(ValueError, match="Invalid configuration"):
        Config.validate_with_error()

# Testing with monkeypatch (environment variables)
def test_with_env_var(monkeypatch):
    monkeypatch.setenv("MY_VAR", "test_value")
    assert os.getenv("MY_VAR") == "test_value"

# Testing logs
def test_logs_warning(caplog):
    import logging
    caplog.set_level(logging.WARNING)

    my_function_that_logs()

    assert "Expected warning" in caplog.text
```

### Mocking External Services

Since external services are disabled, they return mock data:

```python
def test_ready_endpoint_with_services_disabled(client, api_url):
    """Test that /v0/ready shows services as OK when disabled."""
    # Services are disabled in unit tests, should return OK
    response = client.get(api_url("ready"))
    data = response.json

    assert data["checks"]["identity"]["status"] == "ok"
    assert data["checks"]["guardian"]["status"] == "ok"
```

## Best Practices

### 1. Isolation
- Each test should be **independent** and not rely on other tests
- Use fixtures to set up required state
- Clean up after tests (fixtures do this automatically)

### 2. Fast Execution
- Keep unit tests **fast** (< 100ms per test)
- Use in-memory database (already configured)
- Avoid sleep() or time delays
- Mock external calls instead of making real ones

### 3. Clear Assertions
```python
# Good
assert response.status_code == 200
assert response.json["name"] == "expected_name"

# Better - with helpful messages
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert "name" in response.json, "Response missing 'name' field"
```

### 4. Test Edge Cases
- Valid inputs (happy path)
- Invalid inputs (validation)
- Boundary conditions (min/max values)
- Missing required fields
- Duplicate data
- Database errors

### 5. DRY Principle
- Extract common setup to fixtures
- Use helper functions for repeated logic
- Create custom fixtures for complex scenarios

### 6. Documentation
- Write clear docstrings for each test
- Explain **what** is being tested and **why**
- Document any non-obvious setup or assertions

## Debugging Tests

```bash
# Run specific failing test with full output
pytest tests/unit/test_config.py::test_specific -vvs

# Drop into debugger on failure
pytest tests/unit/ --pdb

# Show local variables in traceback
pytest tests/unit/ -l

# Show print statements
pytest tests/unit/ -s

# Increase verbosity
pytest tests/unit/ -vv
```

## Common Patterns

### Testing API Endpoints

```python
def test_get_resource(client, api_url):
    """Test GET /v0/resource."""
    response = client.get(api_url("resource"))
    assert response.status_code == 200

def test_post_resource(client, api_url):
    """Test POST /v0/resource."""
    data = {"name": "test", "value": 42}
    response = client.post(api_url("resource"), json=data)
    assert response.status_code == 201
    assert response.json["name"] == "test"

def test_post_invalid_data(client, api_url):
    """Test POST with invalid data returns 400."""
    response = client.post(api_url("resource"), json={})
    assert response.status_code == 400
```

### Testing Database Operations

```python
def test_create_and_retrieve(session):
    """Test creating and retrieving a model."""
    # Create
    obj = MyModel(name="test")
    session.add(obj)
    session.commit()

    # Retrieve
    found = session.query(MyModel).filter_by(name="test").first()
    assert found is not None
    assert found.name == "test"
```

### Testing Configuration

```python
def test_config_value(app):
    """Test configuration value."""
    assert app.config["MY_SETTING"] == "expected_value"

def test_config_with_env(monkeypatch):
    """Test configuration with environment variable."""
    monkeypatch.setenv("MY_VAR", "test")
    # Reload config or create new app
    assert Config.MY_VAR == "test"
```

## See Also

- [tests/README.md](../README.md) - Testing overview
- [tests/integration/README.md](../integration/README.md) - Integration tests
- [pytest documentation](https://docs.pytest.org/)
