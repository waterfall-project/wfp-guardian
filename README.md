<div align="center">
  <img src="docs/assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>

  # wfp-guardian

  ![Test Coverage](docs/assets/coverage_badge.svg)
  ![Docstring Coverage](docs/assets/interrogate_badge.svg)
  ![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
  ![Flask](https://img.shields.io/badge/flask-%3E=2.0-green.svg)
  ![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)
  ![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

  Centralized Authorization Service for the Waterfall Platform - Role-Based Access Control (RBAC) system with fine-grained permissions, policies, and comprehensive audit trail.
</div>

---

## 📖 Overview

**wfp-guardian** is the single source of truth for permissions and access control within the Waterfall ecosystem. It provides a comprehensive RBAC implementation with:

- **High-Performance Access Control**: Sub-5ms permission checks with Redis caching
- **Full RBAC Lifecycle**: Manage roles, policies, and permissions
- **User Role Assignments**: Company and project-level role management
- **Audit Trail**: Comprehensive logging for security and compliance
- **System Bootstrap**: Automated tenant initialization
- **Multi-Service Integration**: Identity Service, Redis, PostgreSQL

## 🚀 Quick Start

```bash
# Clone and install
git clone <repo-url>
cd wfp-guardian
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Complete installation (dev + pre-commit hooks)
make install-dev
make pre-commit-install

# Start server
make run
```

## 📋 Code Standards

Preconfigured professional tools: **Black** (formatting), **isort** (imports), **Ruff** (linting), **MyPy** (types), **Bandit** (security), **Pre-commit** (Git hooks).

See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) for details and [CONTRIBUTING.md](CONTRIBUTING.md) to contribute.

## 🛠️ Make Commands

### Development
```bash
make install-dev        # Install development dependencies
make pre-commit-install # Install Git hooks
make run                # Start development server
make format             # Format code (Black + Isort)
make lint               # Lint code (Ruff)
make type-check         # Check types (MyPy)
make check              # Run all quality checks
```

### Testing
```bash
make test               # Run unit + integration tests
make test-unit          # Run unit tests only
make test-integration   # Run integration tests only
make test-cov           # Run tests with coverage report
make test-all           # Full test suite (services + coverage)
```

### Docker & Services
```bash
make compose-up         # Start integration services (DB, Redis...)
make compose-down       # Stop integration services
make docker-build-dev   # Build development image
make docker-build-prod  # Build production image
make docker-test        # Run tests inside Docker
```

### Monitoring
```bash
make monitoring-up      # Start monitoring stack
make monitoring-logs    # View monitoring logs
```

## 📊 Monitoring

Full observability stack with Prometheus and Grafana:

```bash
make monitoring-up      # Start Flask + Prometheus + Grafana
```

Access:
- **Flask App**: http://localhost:5000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

See [docs/monitoring/MONITORING.md](docs/monitoring/MONITORING.md) for complete guide.

## ⚙️ Configuration

### Environments

The project supports 5 environments via `.env.*` files:

| Environment  | DEBUG | External Services | Database         |
|-------------|-------|-------------------|------------------|
| development | ✅     | ❌                | SQLite           |
| testing     | ❌     | ❌                | SQLite (memory)  |
| integration | ❌     | ✅                | SQLite/PostgreSQL|
| staging     | ✅     | ✅                | PostgreSQL       |
| production  | ❌     | ✅                | PostgreSQL       |

### Main Variables

```bash
FLASK_ENV=development
SERVICE_PORT=5000
LOG_LEVEL=DEBUG
JWT_SECRET_KEY=your-secret-key
USE_REDIS_CACHE=false
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_ENABLED=true
CORS_ORIGINS=http://localhost:3000
```

See [.env.example](.env.example) for the complete list.

## 🔌 API Endpoints

### System Endpoints (Public)

- `GET /v0/health` - Lightweight health check for Kubernetes liveness probe
- `GET /v0/ready` - Comprehensive readiness check (database, redis, external services)
- `GET /v0/metrics` - Prometheus metrics for monitoring and observability

### Management Endpoints (Authenticated)

- `GET /v0/version` - API version with build metadata (commit, build date, python version)
- `GET /v0/configuration` - Configuration display with sensitive values masked

### Access Control (Core Features)

- `POST /v0/check-access` - Check if user has permission (< 5ms with cache)
- `POST /v0/batch-check-access` - Check up to 50 permissions simultaneously
- `GET /v0/users/{user_id}/permissions` - Get all user permissions

### RBAC Management

**Roles**:
- `GET /v0/roles` - List all roles (paginated)
- `POST /v0/roles` - Create a new role
- `GET /v0/roles/{role_id}` - Get role details
- `PUT /v0/roles/{role_id}` - Update role
- `DELETE /v0/roles/{role_id}` - Delete role

**Policies**:
- `GET /v0/policies` - List all policies (paginated)
- `POST /v0/policies` - Create a new policy
- `GET /v0/policies/{policy_id}` - Get policy details
- `PUT /v0/policies/{policy_id}` - Update policy
- `DELETE /v0/policies/{policy_id}` - Delete policy
- `POST /v0/policies/{policy_id}/permissions` - Attach permissions to policy
- `DELETE /v0/policies/{policy_id}/permissions/{permission_id}` - Detach permission

**Permissions**:
- `GET /v0/permissions` - List all system permissions (read-only, seeded by system)
- `GET /v0/permissions/{permission_id}` - Get permission details

**User Role Assignments**:
- `GET /v0/user-roles` - List all user role assignments
- `POST /v0/user-roles` - Assign role to user
- `GET /v0/user-roles/{user_role_id}` - Get assignment details
- `DELETE /v0/user-roles/{user_role_id}` - Remove role assignment

### Audit & Bootstrap

- `GET /v0/audit` - Query access audit logs
- `POST /v0/bootstrap` - Initialize RBAC for new tenant

Full API documentation available in [docs/openapi/openapi.yaml](docs/openapi/openapi.yaml).

See [docs/monitoring/METRICS.md](docs/monitoring/METRICS.md) for Prometheus metrics documentation.

## 🧪 Tests

```bash
pytest tests/unit/ -v         # Unit tests
pytest tests/integration/ -v  # Integration tests
make test-cov                 # With coverage (htmlcov/)
```

For detailed testing documentation:
- [tests/unit/README.md](tests/unit/README.md) - Unit testing guide
- [tests/integration/README.md](tests/integration/README.md) - Integration testing guide

## 📖 Documentation

- [docs/README.md](docs/README.md) - Complete documentation index
- [docs/openapi/openapi.yaml](docs/openapi/openapi.yaml) - Full OpenAPI 3.0 specification
- [docs/openapi/README.md](docs/openapi/README.md) - API documentation guide
- [docs/monitoring/MONITORING.md](docs/monitoring/MONITORING.md) - Monitoring setup
- [docs/monitoring/METRICS.md](docs/monitoring/METRICS.md) - Prometheus metrics reference
- [tests/unit/README.md](tests/unit/README.md) - Unit testing documentation
- [tests/integration/README.md](tests/integration/README.md) - Integration testing documentation
- [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) - Code standards and tools

## 🏗️ Structure

```
wfp-guardian/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration classes
│   ├── routes.py            # API routes registration
│   ├── service.py           # Business logic layer
│   ├── models/              # SQLAlchemy models (RBAC entities)
│   ├── resources/           # Flask-RESTful resources (API endpoints)
│   ├── schemas/             # Marshmallow schemas (validation)
│   ├── services/            # External service clients (Identity)
│   └── utils/               # Utilities (logger, JWT, rate limiter)
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests (with DB/Redis)
├── docs/
│   ├── openapi/             # OpenAPI 3.0 specification
│   └── monitoring/          # Monitoring and metrics docs
├── migrations/              # Alembic database migrations
├── scripts/                 # Utility scripts
├── .env.example             # Configuration template
├── pyproject.toml           # Python dependencies and tools config
├── Makefile                 # Development commands
├── run.py                   # Development entry point
└── wsgi.py                  # Production entry point (Gunicorn)
```

## 📄 License

Dual license:
- **AGPLv3** for open source usage ([LICENSE](LICENSE))
- **Commercial** for proprietary usage ([COMMERCIAL-LICENSE.txt](COMMERCIAL-LICENSE.txt))

Contact: contact@waterfall-project.pro

## 📚 Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guide
- [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) - Code standards
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Code of conduct
