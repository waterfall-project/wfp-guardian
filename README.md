<div align="center">
  <img src="docs/assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>

  # wfp-flask-template

  ![Test Coverage](docs/assets/coverage_badge.svg)
  ![Docstring Coverage](docs/assets/interrogate_badge.svg)
  ![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
  ![Flask](https://img.shields.io/badge/flask-%3E=2.0-green.svg)
  ![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)
  ![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

  Professional Flask template for Waterfall projects with complete configuration, code standards, and integrated quality tools (Black, Ruff, MyPy, Pre-commit).
</div>

## 🚀 Quick Start

```bash
# Clone and install
git clone <repo-url>
cd wfp-flask-template
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

### Operational Endpoints (Public)

- `GET /health` - Lightweight health check for Kubernetes liveness probe
- `GET /ready` - Comprehensive readiness check (database, redis, external services)
- `GET /metrics` - Prometheus metrics for monitoring and observability

### API Endpoints (Authenticated)

- `GET /version` - API version with build metadata (commit, build date, python version)
- `GET /configuration` - Configuration display with sensitive values masked

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
- [tests/unit/README.md](tests/unit/README.md) - Unit testing documentation
- [tests/integration/README.md](tests/integration/README.md) - Integration testing documentation

## 🏗️ Structure

```
wfp-flask-template/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration classes
│   ├── routes.py            # Routes and endpoints
│   ├── helpers/             # Utility functions
│   ├── models/              # SQLAlchemy models
│   ├── resources/           # Flask-RESTful resources
│   ├── schemas/             # Marshmallow schemas
│   └── utils/               # Logger, constants
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── docs/                    # Documentation
├── .env.example             # Configuration template
├── pyproject.toml           # Python configuration
├── Makefile                 # Automated commands
├── run.py                   # Dev entry point
└── wsgi.py                  # Production entry point
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
