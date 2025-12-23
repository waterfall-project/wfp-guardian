<div align="center">
  <img src="../docs/assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Testing Infrastructure

This document describes the complete testing infrastructure for the Guardian Service, including unit tests, integration tests, and their respective environments.

## Table of Contents

- [Overview](#overview)
- [Test Environments](#test-environments)
- [Makefile Commands](#makefile-commands)
- [Environment Isolation](#environment-isolation)
- [Directory Structure](#directory-structure)

## Overview

The project uses **pytest** for testing with two distinct testing environments:

1. **Unit Tests** (`tests/unit/`) - Fast, isolated tests with SQLite in-memory database
2. **Integration Tests** (`tests/integration/`) - Tests against real services running in Docker containers

**Current Status:**
- **384 unit tests** (1 skipped)
- **8 integration tests**
- **93% code coverage**

## Test Environments

### Unit Tests Environment

- **Configuration File:** `.env.testing`
- **Fixtures:** `tests/unit/conftest.py`
- **Database:** SQLite in-memory
- **External Services:** Disabled (mocked)
- **Redis Cache:** Disabled
- **Rate Limiting:** Disabled
- **Execution Time:** ~5 seconds

See [tests/unit/README.md](unit/README.md) for detailed configuration.

### Integration Tests Environment

- **Configuration File:** `.env.integration`
- **Fixtures:** `tests/integration/conftest.py`
- **Database:** PostgreSQL (Docker, port 5433)
- **Redis:** Docker, port 6380
- **Identity Service:** Docker, port 5001
- **Guardian Service:** Docker, port 5002
- **Rate Limiting:** Disabled (for testing)
- **Execution Time:** ~0.1 seconds (after services startup)

See [tests/integration/README.md](integration/README.md) for detailed configuration.

## Makefile Commands

### Running Tests

```bash
# Unit tests only (fast, no external dependencies)
make test-unit

# Integration tests only (requires services running)
make test-integration

# All tests (unit + integration, assumes services running)
make test

# All tests with coverage report (assumes services running)
make test-cov

# Complete test suite: start services, test with coverage, stop services
make test-all
```

### Managing Integration Test Services

```bash
# Start Docker services (PostgreSQL, Redis, Identity, Guardian)
make test-integration-services-up

# Stop Docker services
make test-integration-services-down

# Check services status
make test-integration-services-status
```

### Other Commands

```bash
# Generate coverage badge
make test-cov-badge

# Clean test artifacts
make clean
```

## Environment Isolation

The two test environments are **completely isolated** from each other:

### Isolation Mechanisms

1. **Separate Configuration Files**
   - Unit tests: `.env.testing`
   - Integration tests: `.env.integration`

2. **Separate conftest.py Files**
   - `tests/unit/conftest.py` - Loads `.env.testing` and sets unit-specific overrides
   - `tests/integration/conftest.py` - Loads `.env.integration` with `override=True`

3. **Different Fixture Scopes**
   - Unit: `scope="function"` - Fresh database for each test
   - Integration: `scope="session"` - Shared app across tests for speed

4. **Sequential Execution**
   - Unit tests run first (isolated, in-memory)
   - Redis is flushed between unit and integration tests
   - Integration tests run second (real services)

### Configuration Loading Order

**Unit Tests:**
```python
# 1. Set environment variables BEFORE loading .env
os.environ["FLASK_ENV"] = "testing"
os.environ["USE_IDENTITY_SERVICE"] = "false"
os.environ["USE_GUARDIAN_SERVICE"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
# ... other overrides

# 2. Load .env.testing (does not override existing vars)
load_dotenv(dotenv_path=".env.testing")
```

**Integration Tests:**
```python
# 1. Load .env.integration (with override=True)
load_dotenv(dotenv_path=".env.integration", override=True)

# 2. Set FLASK_ENV to ensure testing mode
os.environ["FLASK_ENV"] = "testing"
```

### Why This Matters

- **Unit tests** must be fast and isolated → SQLite in-memory, no external services
- **Integration tests** verify real-world behavior → PostgreSQL, Redis, microservices
- Running them together in pytest would cause **environment conflicts**
- The Makefile ensures proper sequencing and cleanup

## Directory Structure

```
tests/
├── README.md                    # This file - overview and commands
├── unit/
│   ├── README.md               # Unit test configuration and fixtures
│   ├── conftest.py             # Unit test fixtures
│   ├── test_*.py               # Unit test files
│   └── resources/              # Tests for API resources
│       └── test_*.py
├── integration/
│   ├── README.md               # Integration test configuration and fixtures
│   ├── conftest.py             # Integration test fixtures
│   └── test_*.py               # Integration test files
└── __init__.py
```

## Running Tests in CI/CD

For continuous integration pipelines:

```bash
# Option 1: Use test-all (manages services lifecycle)
make test-all

# Option 2: Manual control
make test-integration-services-up
make test-cov
make test-integration-services-down
```

The `test-all` command is recommended for CI/CD as it:
1. Starts all required Docker services
2. Waits for services to be healthy
3. Runs unit tests with coverage
4. Flushes Redis
5. Runs integration tests with coverage
6. Generates combined coverage report
7. Stops services

## Coverage Reports

After running `make test-cov` or `make test-all`, coverage reports are available:

- **Terminal:** Displayed after test execution
- **HTML:** `htmlcov/index.html` (open in browser)
- **Coverage Data:** `.coverage` (used for badges)

## Troubleshooting

### Integration Tests Fail

```bash
# Check if services are running
make test-integration-services-status

# Restart services
make test-integration-services-down
make test-integration-services-up
```

### Rate Limiting Issues

If tests fail with "429 TOO MANY REQUESTS":

```bash
# Flush Redis manually
docker exec wfp-redis-test redis-cli FLUSHDB

# Or restart services
make test-integration-services-down
make test-integration-services-up
```

### Services Won't Start

```bash
# Check Docker logs
docker-compose -f docker-compose.test.yml logs

# Check ports are available
lsof -i :5433  # PostgreSQL
lsof -i :6380  # Redis
lsof -i :5001  # Identity
lsof -i :5002  # Guardian
```

## Next Steps

- See [tests/unit/README.md](unit/README.md) for unit test details
- See [tests/integration/README.md](integration/README.md) for integration test details
- See [INTEGRATION_TESTING.md](../INTEGRATION_TESTING.md) for Docker services setup
