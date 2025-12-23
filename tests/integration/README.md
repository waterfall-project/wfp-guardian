<div align="center">
  <img src="../../docs/assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Integration Tests

This document describes the integration testing environment, configuration, fixtures, Docker services, and best practices.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Docker Services](#docker-services)
- [Fixtures](#fixtures)
- [Running Integration Tests](#running-integration-tests)
- [Writing Integration Tests](#writing-integration-tests)
- [Best Practices](#best-practices)
- [Development Workflow](#development-workflow)

## Overview

Integration tests validate **real-world behavior** by testing against actual services running in Docker containers:

- **PostgreSQL** - Real database with migrations
- **Redis** - Real cache and session storage
- **Identity Service** - User authentication microservice
- **Guardian Service** - Authorization/permissions microservice

**Current Status:**
- **8 tests** (service connectivity + application health endpoints)
- **Execution time:** ~0.1 seconds (after services startup)
- **Coverage contribution:** ~3% (incremental to unit tests)

## Quick Start

For developers who want to get started quickly:

### 1. Start External Services

```bash
# Start all external services
docker-compose -f docker-compose.test.yml up -d

# Wait for all services to be healthy (30-60 seconds)
docker-compose -f docker-compose.test.yml ps

# View logs if needed
docker-compose -f docker-compose.test.yml logs -f
```

### 2. Run Integration Tests

```bash
# Run integration tests (reads .env.integration automatically)
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ --cov=app --cov-report=term-missing -v

# Run specific test file
pytest tests/integration/test_health.py -v
```

### 3. Stop Services

```bash
# Stop all services
docker-compose -f docker-compose.test.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.test.yml down -v
```

## Architecture

Understanding where each component runs:

- **Application Under Test**: Runs locally on your machine (port 5000)
  - Uses pytest fixtures and test client
  - Connects to external services in Docker

- **External Services**: Run in Docker containers
  - **PostgreSQL**: `localhost:5433` - Real database with test data
  - **Redis**: `localhost:6380` - Real cache and session storage
  - **Identity Service**: `localhost:5001` - User authentication microservice
  - **Guardian Service**: `localhost:5002` - Authorization/permissions microservice

**Key Differences from Unit Tests:**
- Unit tests mock external services → Integration tests use real services
- Unit tests use SQLite in-memory → Integration tests use PostgreSQL
- Unit tests skip Redis → Integration tests use Redis
- Unit tests are isolated → Integration tests test real service interactions

## Prerequisites

### Required Software

1. **Docker** (v20.10+)
   ```bash
   docker --version
   ```

2. **Docker Compose** (v2.0+)
   ```bash
   docker compose version
   ```

2. Services `wfp-identity` and `wfp-guardian` cloned in sibling directories:
   ```
   parent/
   ├── wfp-flask-template/  (this repo)
   ├── wfp-identity/
   └── wfp-guardian/
   ```

3. **Available Ports**
   - 5433 (PostgreSQL)
   - 6380 (Redis)
   - 5001 (Identity Service)
   - 5002 (Guardian Service)

### Verify Ports

```bash
# Check if ports are available
lsof -i :5433
lsof -i :6380
lsof -i :5001
lsof -i :5002

# If ports are in use, stop conflicting services or change ports in docker-compose.test.yml
```

## Configuration

### Environment File: `.env.integration`

Located at project root, this file configures the integration test environment.

**Key Differences from Unit Tests:**
- `USE_IDENTITY_SERVICE=true` (vs `false` in unit tests)
- `USE_GUARDIAN_SERVICE=true` (vs `false` in unit tests)
- `USE_REDIS_CACHE=true` (vs `false` in unit tests)
- Real PostgreSQL database (vs SQLite in-memory)
- Real Redis cache (vs disabled in unit tests)

**Service URLs:**
When services are running, you can access them at:

- **PostgreSQL**: `postgresql://testuser:testpassword@localhost:5433/testdb`
- **Redis**: `redis://localhost:6380/0`
- **Identity Service**: `http://localhost:5001`
  - Health: `http://localhost:5001/v0/health`
- **Guardian Service**: `http://localhost:5002`
  - Health: `http://localhost:5002/v0/health`

**Complete Configuration:**

```dotenv
# Integration Testing Environment Configuration
# Services started with: docker-compose -f docker-compose.test.yml up -d

# Flask Configuration
FLASK_ENV=testing
SERVICE_PORT=5000
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Database Configuration - PostgreSQL in Docker
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_NAME=testdb
DATABASE_USER=testuser
DATABASE_PASSWORD=testpassword

# Redis Configuration - Redis in Docker
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=0
REDIS_URL=redis://localhost:6380/0
USE_REDIS_CACHE=true

# External Services - Running in Docker
USE_IDENTITY_SERVICE=true
USE_GUARDIAN_SERVICE=true
IDENTITY_SERVICE_URL=http://localhost:5001
GUARDIAN_SERVICE_URL=http://localhost:5002
EXTERNAL_SERVICES_TIMEOUT=5.0

# JWT Configuration - Shared key with all services
JWT_SECRET_KEY=test-secret-key-shared
JWT_ALGORITHM=HS256

# Pagination
PAGE_LIMIT=20
MAX_PAGE_LIMIT=100

# CORS
CORS_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ALLOW_CREDENTIALS=true
CORS_MAX_AGE=3600

# Rate Limiting - Disabled for testing
RATE_LIMIT_ENABLED=false
RATE_LIMIT_STORAGE=redis
RATE_LIMIT_STRATEGY=fixed-window
RATE_LIMIT_CONFIGURATION=10 per minute

```

### Configuration Loading

The `tests/integration/conftest.py` loads configuration with override:

```python
# Load .env.integration with override=True
dotenv_path = Path(__file__).parent.parent.parent / ".env.integration"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)

# Ensure testing mode
os.environ["FLASK_ENV"] = "testing"
```

The `override=True` ensures integration-specific settings take precedence.

## Docker Services

### Service Definitions

All services are defined in `docker-compose.test.yml`:

#### PostgreSQL
```yaml
postgres-test:
  image: postgres:15-alpine
  container_name: wfp-postgres-test
  environment:
    POSTGRES_USER: testuser
    POSTGRES_PASSWORD: testpassword
    POSTGRES_DB: testdb
  ports:
    - "5433:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U testuser"]
    interval: 5s
    timeout: 5s
    retries: 5
```

#### Redis
```yaml
redis-test:
  image: redis:7-alpine
  container_name: wfp-redis-test
  ports:
    - "6380:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
```

#### Identity Service
```yaml
identity-test:
  build:
    context: ../wfp-identity
    dockerfile: Dockerfile
    target: test
  container_name: wfp-identity-test
  environment:
    FLASK_ENV: testing
    SERVICE_PORT: 5001
    USE_GUARDIAN_SERVICE: "false"
    USE_IDENTITY_SERVICE: "false"
    JWT_SECRET_KEY: test-secret-key-shared
    RUN_MIGRATIONS: "true"
  ports:
    - "5001:5001"
  depends_on:
    postgres-test:
      condition: service_healthy
    redis-test:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5001/v0/health"]
    interval: 10s
    timeout: 5s
    retries: 5
```

#### Guardian Service
```yaml
guardian-test:
  build:
    context: ../wfp-guardian
    dockerfile: Dockerfile
    target: test
  container_name: wfp-guardian-test
  environment:
    FLASK_ENV: testing
    SERVICE_PORT: 5002
    USE_GUARDIAN_SERVICE: "false"
    USE_IDENTITY_SERVICE: "false"
    JWT_SECRET_KEY: test-secret-key-shared
    RUN_MIGRATIONS: "true"
  ports:
    - "5002:5002"
  depends_on:
    identity-test:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5002/v0/health"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Managing Services

```bash
# Start all services and wait for healthy status
make test-integration-services-up

# Check services status
make test-integration-services-status

# View service logs
docker-compose -f docker-compose.test.yml logs -f

# Stop all services
make test-integration-services-down

# Restart services
make test-integration-services-down
make test-integration-services-up
```

### Service Health Checks

The Makefile automatically waits for all services to be healthy:

```bash
# Checks every 5 seconds, up to 12 times (60 seconds timeout)
# Verifies 4/4 services are healthy before proceeding
```

You can manually check:
```bash
docker-compose -f docker-compose.test.yml ps
```

Expected output when all healthy:
```
NAME                STATUS              PORTS
wfp-postgres-test   Up (healthy)        0.0.0.0:5433->5432/tcp
wfp-redis-test      Up (healthy)        0.0.0.0:6380->6379/tcp
wfp-identity-test   Up (healthy)        0.0.0.0:5001->5001/tcp
wfp-guardian-test   Up (healthy)        0.0.0.0:5002->5002/tcp
```

## Fixtures

### Core Fixtures

#### `app` Fixture
**Scope:** `session` (shared across all tests)
**Purpose:** Creates a Flask application that connects to real Docker services

```python
@fixture(scope="session")
def app():
    """Create Flask application for integration testing.

    - Uses TestingConfig
    - Connects to real PostgreSQL database
    - Connects to real Redis cache
    - Can communicate with Identity/Guardian services
    - Database is created once and reused
    """
    app = create_app("app.config.TestingConfig")

    with app.app_context():
        # Create all database tables
        db.create_all()
        yield app

        # Clean up
        db.drop_all()
        db.session.remove()
        db.engine.dispose()
```

**Why session scope?**
- Faster: App created once, reused for all tests
- Real services: Database and Redis persist between tests
- Isolation: Each test uses transactions (see `session` fixture)

#### `client` Fixture
**Scope:** `function` (new for each test)
**Purpose:** Provides test client for making HTTP requests

```python
@fixture(scope="function")
def client(app):
    """Create test client for making HTTP requests."""
    return app.test_client()
```

**Usage:**
```python
def test_health_endpoint(client, api_url):
    response = client.get(api_url("health"))
    assert response.status_code == 200
```

#### `session` Fixture
**Scope:** `function`
**Purpose:** Provides database session with transaction rollback

```python
@fixture(scope="function")
def session(app):
    """Provide database session for tests.

    Uses nested transactions to ensure test isolation:
    - Starts a nested transaction before each test
    - Rolls back after each test
    - Keeps database clean between tests
    """
    with app.app_context():
        # Start a nested transaction
        db.session.begin_nested()
        yield db.session

        # Rollback after each test to keep database clean
        db.session.rollback()
```

**Why rollback?**
- Each test starts with a clean database state
- No data pollution between tests
- Faster than dropping and recreating tables

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

### Future Fixtures (Planned)

As integration tests expand, the following fixtures will be added:

#### Authentication Fixtures
```python
@fixture
def auth_token():
    """Generate valid JWT token for testing."""
    # Will integrate with Identity service
    pass

@fixture
def authenticated_client(client, auth_token):
    """Client with authentication header."""
    # Will add Authorization header
    pass

@fixture
def admin_token():
    """Generate JWT token with admin permissions."""
    pass
```

#### Service Initialization Fixtures
```python
@fixture(scope="session")
def identity_service_ready():
    """Ensure Identity service is initialized with test data."""
    # Create test users, roles, etc.
    pass

@fixture(scope="session")
def guardian_service_ready():
    """Ensure Guardian service is initialized with permissions."""
    # Create test permissions, policies, etc.
    pass
```

#### Data Fixtures
```python
@fixture
def sample_users(session):
    """Create sample users in database."""
    pass

@fixture
def sample_permissions(session):
    """Create sample permissions in database."""
    pass
```

#### Request Context Fixtures
```python
@fixture
def request_headers():
    """Standard request headers for testing."""
    return {
        "Content-Type": "application/json",
        "X-Request-ID": str(uuid.uuid4()),
    }

@fixture
def mock_service_response():
    """Mock response from Identity/Guardian service."""
    pass
```

## Running Integration Tests

### Prerequisites Check

```bash
# Verify services are running
make test-integration-services-status

# If not running, start them
make test-integration-services-up
```

### Basic Execution

```bash
# All integration tests
make test-integration

# Specific test file
pytest tests/integration/test_health.py -v

# Specific test function
pytest tests/integration/test_health.py::TestServiceConnectivity::test_postgres_connection -v

# Tests matching pattern
pytest tests/integration/ -k "health" -v

# With coverage
pytest tests/integration/ --cov=app --cov-report=term
```

### Complete Test Suite

```bash
# Start services, run all tests with coverage, stop services
make test-all

# Or with coverage only (assumes services running)
make test-cov
```

### Useful Flags

```bash
# Stop on first failure
pytest tests/integration/ -x

# Show print statements
pytest tests/integration/ -s

# Verbose output
pytest tests/integration/ -v

# Very verbose with full diff
pytest tests/integration/ -vv
```

## Writing Integration Tests

### Test Structure

```python
"""
Module docstring explaining what is being tested.
"""
import pytest

class TestFeatureName:
    """Group related integration tests."""

    def test_specific_scenario(self, client, api_url, session):
        """Test docstring explaining the scenario."""
        # Arrange - Set up test data in real database
        from app.models.dummy_model import Dummy
        dummy = Dummy(name="test")
        session.add(dummy)
        session.commit()

        # Act - Make real HTTP request
        response = client.get(api_url(f"dummies/{dummy.id}"))

        # Assert - Verify real service behavior
        assert response.status_code == 200
        assert response.json["name"] == "test"
```

### Current Test Organization

```
tests/integration/
├── conftest.py                # Integration fixtures
└── test_health.py            # Service connectivity and health checks
    ├── TestServiceConnectivity
    │   ├── test_postgres_connection
    │   ├── test_redis_connection
    │   ├── test_identity_service_health
    │   └── test_guardian_service_health
    └── TestApplicationHealth
        ├── test_health_endpoint
        ├── test_ready_endpoint
        ├── test_version_endpoint
        └── test_configuration_endpoint
```

### Testing Patterns

#### Testing Service Connectivity

```python
def test_postgres_connection(session):
    """Test PostgreSQL connection."""
    # Execute a simple query
    result = session.execute("SELECT 1").scalar()
    assert result == 1

def test_redis_connection(app):
    """Test Redis connection."""
    import redis
    client = redis.Redis(host='localhost', port=6380, db=0)
    assert client.ping() is True
```

#### Testing External Services

```python
def test_identity_service_health():
    """Test Identity service is responding."""
    import requests
    response = requests.get("http://localhost:5001/v0/health", timeout=5)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

#### Testing Application Endpoints

```python
def test_endpoint_with_database(client, api_url, session):
    """Test endpoint that uses real database."""
    # Create test data
    from app.models.dummy_model import Dummy
    dummy = Dummy(name="integration_test")
    session.add(dummy)
    session.commit()

    # Test endpoint
    response = client.get(api_url(f"dummies/{dummy.id}"))
    assert response.status_code == 200
    assert response.json["id"] == str(dummy.id)
```

#### Testing with Authentication (Future)

```python
def test_protected_endpoint(authenticated_client, api_url):
    """Test endpoint requiring authentication."""
    response = authenticated_client.get(api_url("protected-resource"))
    assert response.status_code == 200

def test_admin_only_endpoint(admin_client, api_url):
    """Test endpoint requiring admin permissions."""
    response = admin_client.post(api_url("admin/action"))
    assert response.status_code == 200
```

## Best Practices

### 1. Service Dependencies
- Always check services are running before tests
- Use healthchecks to ensure services are ready
- Handle service failures gracefully

### 2. Test Isolation
- Use transaction rollback to isolate tests
- Clean up test data after each test
- Don't rely on execution order

### 3. Real-World Scenarios
- Test actual API flows (create → read → update → delete)
- Test service-to-service communication
- Test with realistic data volumes

### 4. Performance
- Use `scope="session"` for fixtures that don't need isolation
- Minimize database operations
- Reuse connections when possible

### 5. Error Handling
```python
def test_service_unavailable():
    """Test behavior when service is down."""
    # Stop service temporarily or mock connection failure
    response = client.get(api_url("endpoint"))
    assert response.status_code in [503, 500]
```

### 6. Timeouts
```python
def test_service_timeout():
    """Test timeout handling."""
    # Configure short timeout
    app.config["EXTERNAL_SERVICES_TIMEOUT"] = 0.1
    response = client.get(api_url("slow-endpoint"))
    assert response.status_code in [504, 500]
```

### 7. Documentation
- Document service dependencies
- Explain test setup and expectations
- Note any manual steps required

## Debugging Integration Tests

### View Service Logs

```bash
# All services
docker-compose -f docker-compose.test.yml logs -f

# Specific service
docker logs wfp-postgres-test -f
docker logs wfp-redis-test -f
docker logs wfp-identity-test -f
docker logs wfp-guardian-test -f
```

### Access Services Directly

```bash
# PostgreSQL
docker exec -it wfp-postgres-test psql -U testuser -d testdb

# Redis
docker exec -it wfp-redis-test redis-cli

# Check service health
curl http://localhost:5001/v0/health
curl http://localhost:5002/v0/health
```

### Debug Test Execution

```bash
# Run specific test with full output
pytest tests/integration/test_health.py::test_specific -vvs

# Drop into debugger on failure
pytest tests/integration/ --pdb

# Show local variables in traceback
pytest tests/integration/ -l
```

### Common Issues

**Services not healthy:**
```bash
# Check logs
docker-compose -f docker-compose.test.yml logs

# Restart services
make test-integration-services-down
make test-integration-services-up
```

**Database connection errors:**
```bash
# Verify PostgreSQL is running
docker exec -it wfp-postgres-test psql -U testuser -c "SELECT 1"

# Check connection from host
psql -h localhost -p 5433 -U testuser -d testdb
```

**Redis connection errors:**
```bash
# Verify Redis is running
docker exec -it wfp-redis-test redis-cli ping

# Check from host
redis-cli -h localhost -p 6380 ping
```

## Development Workflow

For iterative development with integration tests:

```bash
# 1. Start services once
docker-compose -f docker-compose.test.yml up -d

# 2. Develop and run tests iteratively
pytest tests/integration/ -v

# Make changes to code...

# Run tests again (services still running)
pytest tests/integration/ -v

# 3. When done, stop services
docker-compose -f docker-compose.test.yml down
```

**Benefits:**
- Services persist between test runs
- Only need to start services once per development session
- Faster feedback loop (no startup delay)
- Realistic testing against real services

**Coverage Goals:**
Integration tests help achieve the 95% coverage target by testing:
- Real database transactions and constraints
- Redis caching behavior and persistence
- Identity service authentication flows
- Guardian service authorization checks
- End-to-end API workflows with all services

## See Also

- [tests/README.md](../README.md) - Testing overview
- [tests/unit/README.md](../unit/README.md) - Unit tests
- [docker-compose.test.yml](../../docker-compose.test.yml) - Service definitions
- [.env.integration](../../.env.integration) - Integration test configuration
