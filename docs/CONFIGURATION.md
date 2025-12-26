<div align="center">
  <img src="assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Waterfall Guardian Configuration

This document describes all environment variables used to configure the Guardian Authorization Service.

## Table of Contents

- [Waterfall Guardian Configuration](#waterfall-guardian-configuration)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
  - [Configuration Priority](#configuration-priority)
  - [Flask Configuration](#flask-configuration)
  - [JWT Configuration](#jwt-configuration)
  - [External Services](#external-services)
    - [Identity Service](#identity-service)
    - [Mock Configuration (Development)](#mock-configuration-development)
  - [Database Configuration](#database-configuration)
    - [Option 1: Complete URL (Recommended for Production)](#option-1-complete-url-recommended-for-production)
    - [Option 2: Individual Components](#option-2-individual-components)
    - [SQLAlchemy Pool Settings](#sqlalchemy-pool-settings)
  - [Redis Configuration](#redis-configuration)
    - [Option 1: Complete URL](#option-1-complete-url)
    - [Option 2: Individual Components](#option-2-individual-components-1)
  - [Logging Configuration](#logging-configuration)
  - [CORS Configuration](#cors-configuration)
  - [Rate Limiting Configuration](#rate-limiting-configuration)
  - [Pagination Configuration](#pagination-configuration)
  - [Environment Examples](#environment-examples)
    - [Development (.env.development)](#development-envdevelopment)
    - [Testing (.env.testing)](#testing-envtesting)
    - [Integration (.env.integration)](#integration-envintegration)
    - [Staging (.env.staging)](#staging-envstaging)
    - [Production (.env.production)](#production-envproduction)
  - [Docker Compose Example](#docker-compose-example)
  - [Generating Secure Keys](#generating-secure-keys)
  - [Configuration Classes](#configuration-classes)
  - [See Also](#see-also)

---

## Quick Start

Minimal configuration for development:

```bash
# Required
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256

# Optional (defaults work for development)
DATABASE_TYPE=sqlite
USE_IDENTITY_SERVICE=false
USE_REDIS_CACHE=false
```

---

## Configuration Priority

The application loads configuration in the following order:

1. **Environment variables** (highest priority)
2. **`.env.*` files** based on `APP_MODE`:
   - `.env.development` (default for local development)
   - `.env.testing` (unit tests)
   - `.env.integration` (integration tests)
   - `.env.staging` / `.env.production` (deployment)
3. **Class defaults** in `app/config.py`

> **Note**: In Docker containers (`IN_DOCKER_CONTAINER=true`), `.env` files are not loaded. All configuration comes from environment variables set by docker-compose or orchestration tools.

---

## Flask Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SERVICE_PORT` | No | `5000` | Port on which the service listens |
| `APP_MODE` | No | - | Application mode: `development`, `testing`, `integration`, `staging`, `production` |
| `IN_DOCKER_CONTAINER` | No | `false` | Set to `true` when running in Docker (skips .env file loading) |
| `FLASK_ENV` | No | `development` | Flask environment mode |

---

## JWT Configuration

These variables configure JWT token validation for authentication.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes* | - | Secret key for JWT signature verification. Required when `USE_IDENTITY_SERVICE=true` |
| `JWT_ALGORITHM` | Yes | - | JWT signing algorithm: `HS256`, `HS512`, `RS256` |

> **Security Note**: Use a strong, randomly generated key of at least 32 characters for `JWT_SECRET_KEY`. Never commit this value to version control.

**JWT Claims Expected:**

| Claim | Type | Description |
|-------|------|-------------|
| `user_id` | UUID | Unique user identifier |
| `company_id` | UUID | Company identifier (multi-tenant) |
| `email` | string | User email |
| `exp` | timestamp | Token expiration date |
| `iat` | timestamp | Token issued at date |

---

## External Services

### Identity Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_IDENTITY_SERVICE` | No | `true`* | Enable Identity Service integration. *Default varies by environment |
| `IDENTITY_SERVICE_URL` | Yes* | - | URL of the Identity Service. Required when `USE_IDENTITY_SERVICE=true` |
| `EXTERNAL_SERVICES_TIMEOUT` | No | `5` | Timeout in seconds for external service calls |

**Default values by environment:**

| Environment | USE_IDENTITY_SERVICE |
|-------------|---------------------|
| Development | `false` |
| Testing | `false` |
| Integration | `true` |
| Staging | `true` |
| Production | `true` |

### Mock Configuration (Development)

When `USE_IDENTITY_SERVICE=false`, these mock values are used for local development:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MOCK_USER_ID` | No | `00000000-0000-0000-0000-000000000001` | Mock user ID |
| `MOCK_COMPANY_ID` | No | `00000000-0000-0000-0000-000000000001` | Mock company ID |

---

## Database Configuration

The database can be configured using either a complete URL or individual components.

### Option 1: Complete URL (Recommended for Production)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | - | Complete database connection URL. Takes precedence over individual components |

**URL Format Examples:**
```
postgresql://user:password@host:5432/dbname
mysql+pymysql://user:password@host:3306/dbname
sqlite:///path/to/database.db
```

### Option 2: Individual Components

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_TYPE` | No | `sqlite` | Database type: `sqlite`, `postgresql`, `mysql` |
| `DATABASE_HOST` | Yes* | `localhost` | Database host. Required for postgresql/mysql |
| `DATABASE_PORT` | No | `5432` (pg) / `3306` (mysql) | Database port (auto-detected if not set) |
| `DATABASE_USER` | Yes* | - | Database username. Required for postgresql/mysql |
| `DATABASE_PASSWORD` | Yes* | - | Database password. Required for postgresql/mysql |
| `DATABASE_NAME` | Yes* | - | Database name. Required for postgresql/mysql |
| `DATABASE_PATH` | No | `dev.db` | Path to SQLite database file (SQLite only) |

> **Note**: In staging/production environments, SQLite is not allowed. You must provide either `DATABASE_URL` or complete connection parameters for PostgreSQL/MySQL.

### SQLAlchemy Pool Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SQLALCHEMY_POOL_SIZE` | No | `5` | Number of connections in the pool |
| `SQLALCHEMY_POOL_RECYCLE` | No | `3600` | Seconds before recycling connections |
| `SQLALCHEMY_POOL_TIMEOUT` | No | `30` | Seconds to wait for available connection |
| `SQLALCHEMY_MAX_OVERFLOW` | No | `10` | Max connections above pool size |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | No | `false` | Track object modifications (disable for performance) |

---

## Redis Configuration

Redis is used for caching user permissions and rate limiting storage.

### Option 1: Complete URL

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | - | Complete Redis connection URL. Takes precedence over individual components |

**URL Format:**
```
redis://[:password@]host:port/db
redis://:mypassword@localhost:6379/0
```

### Option 2: Individual Components

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | Yes* | - | Redis host. Required when `USE_REDIS_CACHE=true` and no `REDIS_URL` |
| `REDIS_PORT` | Yes* | - | Redis port |
| `REDIS_DB` | No | `0` | Redis database number |
| `REDIS_PASSWORD` | No | - | Redis password (if authentication enabled) |

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_REDIS_CACHE` | No | `false` | Enable Redis caching for permissions |

> **Performance Note**: Enable Redis caching in production for sub-5ms access checks. Without Redis, each check requires database queries.

**Cache TTL (hardcoded):**
- User permissions: 5 minutes
- Company hierarchy: 1 hour
- All permissions: 1 hour

---

## Logging Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | No | `text` | Log format: `text` (human-readable) or `json` (structured) |

> **Tip**: Use `LOG_FORMAT=json` in production for better log aggregation with tools like ELK, Loki, or CloudWatch.

---

## CORS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ENABLED` | No | `true` | Enable CORS support |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | No | `true` | Allow credentials (cookies, authorization headers) |
| `CORS_MAX_AGE` | No | `3600` | Preflight request cache duration (seconds) |

---

## Rate Limiting Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting |
| `RATE_LIMIT_CONFIGURATION` | No | `10 per minute` | Default rate limit for endpoints |
| `RATE_LIMIT_STRATEGY` | No | `fixed-window` | Strategy: `fixed-window`, `sliding-window`, `token-bucket` |
| `RATE_LIMIT_STORAGE` | No | `redis` | Storage backend: `redis` (production) or `memory` (testing) |

**Endpoint-specific limits (from .env.example):**

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_LOGIN` | `100/minute` | Login endpoint limit |
| `RATE_LIMIT_REFRESH` | `200/minute` | Token refresh limit |
| `RATE_LIMIT_VERIFY` | `500/minute` | Token verification limit |

> **Warning**: Use `memory` storage only for testing. In production, always use `redis` for distributed rate limiting across multiple instances.

---

## Pagination Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PAGE_LIMIT` | No | `20` | Default number of items per page |
| `MAX_PAGE_LIMIT` | No | `100` | Maximum allowed items per page |

---

## Environment Examples

### Development (.env.development)

```bash
# Flask
FLASK_ENV=development
SERVICE_PORT=5000

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production-min-32-chars
JWT_ALGORITHM=HS256

# Database (SQLite for development)
DATABASE_TYPE=sqlite
DATABASE_PATH=dev.db

# External Services (disabled for local development)
USE_IDENTITY_SERVICE=false

# Mock User Configuration
MOCK_USER_ID=00000000-0000-0000-0000-000000000001
MOCK_COMPANY_ID=00000000-0000-0000-0000-000000000001

# Redis (disabled for development)
USE_REDIS_CACHE=false

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# CORS
CORS_ENABLED=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Rate Limiting (memory for development)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=memory

# Pagination
PAGE_LIMIT=20
MAX_PAGE_LIMIT=100
```

### Testing (.env.testing)

```bash
# Flask
FLASK_ENV=testing
APP_MODE=testing

# JWT
JWT_SECRET_KEY=test-secret-key-for-unit-tests-only
JWT_ALGORITHM=HS256

# Database (SQLite in-memory for fast tests)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///:memory:

# External Services (disabled for isolated tests)
USE_IDENTITY_SERVICE=false

# Redis (disabled for unit tests)
USE_REDIS_CACHE=false

# Rate Limiting (disabled for tests)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_STORAGE=memory

# Logging
LOG_LEVEL=DEBUG
```

### Integration (.env.integration)

```bash
# Flask
FLASK_ENV=testing
APP_MODE=integration

# JWT
JWT_SECRET_KEY=integration-test-secret-key-32chars
JWT_ALGORITHM=HS256

# Database (PostgreSQL in Docker, port 5433 to avoid conflicts)
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_USER=guardian
DATABASE_PASSWORD=guardian_test
DATABASE_NAME=guardian_test

# External Services (enabled, pointing to Docker containers)
USE_IDENTITY_SERVICE=true
IDENTITY_SERVICE_URL=http://localhost:5001

# Redis (enabled, port 6380 to avoid conflicts)
USE_REDIS_CACHE=true
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_DB=0

# Rate Limiting (disabled for tests)
RATE_LIMIT_ENABLED=false

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

### Staging (.env.staging)

```bash
# Flask
SERVICE_PORT=5000
APP_MODE=staging
IN_DOCKER_CONTAINER=true

# JWT
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS256

# Database (PostgreSQL)
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}
SQLALCHEMY_POOL_SIZE=5
SQLALCHEMY_MAX_OVERFLOW=10

# Redis
USE_REDIS_CACHE=true
REDIS_URL=redis://${REDIS_HOST}:6379/0

# External Services
USE_IDENTITY_SERVICE=true
IDENTITY_SERVICE_URL=http://identity-service:5000
EXTERNAL_SERVICES_TIMEOUT=5

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS
CORS_ENABLED=true
CORS_ORIGINS=https://staging.waterfall-project.pro

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=redis
```

### Production (.env.production)

```bash
# Flask
SERVICE_PORT=5000
APP_MODE=production
IN_DOCKER_CONTAINER=true

# JWT (from secrets manager)
JWT_SECRET_KEY=${JWT_SECRET_KEY}
JWT_ALGORITHM=HS512

# Database (PostgreSQL with connection pooling)
DATABASE_URL=${DATABASE_URL}
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_POOL_RECYCLE=3600
SQLALCHEMY_POOL_TIMEOUT=30
SQLALCHEMY_MAX_OVERFLOW=20

# Redis
USE_REDIS_CACHE=true
REDIS_URL=${REDIS_URL}

# External Services
USE_IDENTITY_SERVICE=true
IDENTITY_SERVICE_URL=http://identity-service:5000
EXTERNAL_SERVICES_TIMEOUT=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# CORS
CORS_ENABLED=true
CORS_ORIGINS=https://app.waterfall-project.pro
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CONFIGURATION=60 per minute
RATE_LIMIT_STRATEGY=sliding-window
RATE_LIMIT_STORAGE=redis

# Pagination
PAGE_LIMIT=50
MAX_PAGE_LIMIT=100
```

---

## Docker Compose Example

```yaml
version: '3.8'

services:
  guardian:
    image: waterfall/guardian:latest
    ports:
      - "5000:5000"
    environment:
      - IN_DOCKER_CONTAINER=true
      - APP_MODE=production
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - JWT_ALGORITHM=HS256
      - DATABASE_URL=postgresql://postgres:password@db:5432/guardian
      - USE_REDIS_CACHE=true
      - REDIS_URL=redis://redis:6379/0
      - USE_IDENTITY_SERVICE=true
      - IDENTITY_SERVICE_URL=http://identity:5000
      - LOG_FORMAT=json
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=https://app.waterfall-project.pro
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=guardian
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

---

## Generating Secure Keys

### JWT_SECRET_KEY

```bash
# Using OpenSSL (recommended)
openssl rand -hex 32

# Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Using /dev/urandom
head -c 32 /dev/urandom | base64
```

> **Security Requirements:**
> - Minimum 32 characters
> - Use different keys for each environment
> - Store in secrets manager (Vault, AWS Secrets Manager, etc.) for production
> - Never commit to version control

---

## Configuration Classes

The application uses different configuration classes based on the environment:

| Class | Environment | Key Characteristics |
|-------|-------------|---------------------|
| `DevelopmentConfig` | development | DEBUG=True, SQLite, services disabled |
| `TestingConfig` | testing | TESTING=True, SQLite in-memory, rate limiting disabled |
| `IntegrationConfig` | integration | TESTING=True, services enabled, rate limiting disabled |
| `StagingConfig` | staging | DEBUG=True, PostgreSQL required, services enabled |
| `ProductionConfig` | production | DEBUG=False, PostgreSQL required, all validations |

**Validation in Staging/Production:**
- `DATABASE_URL` or complete PostgreSQL/MySQL parameters required
- SQLite not allowed
- `JWT_SECRET_KEY` required when `USE_IDENTITY_SERVICE=true`
- `IDENTITY_SERVICE_URL` required when `USE_IDENTITY_SERVICE=true`
- `REDIS_URL` required when `USE_REDIS_CACHE=true`

---

## See Also

- [API Documentation](API.md) - REST API endpoints reference
- [Models Documentation](MODELS.md) - Data models and database schema
- [Workflows Documentation](WORKFLOWS.md) - Authorization operation workflows
- [Monitoring Documentation](MONITORING.md) - Metrics and observability
