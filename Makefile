# Makefile for Guardian Service

.PHONY: help install install-dev format lint type-check test test-cov test-cov-badge clean run compose-build compose-up compose-down docker-build-dev docker-build-test docker-build-prod docker-test monitoring-up monitoring-down monitoring-logs pre-commit-install pre-commit-run docstring-check docstring-coverage test-integration test-integration-services-up test-integration-services-down test-integration-services-status test-unit test-all

# Default target
help:
	@echo "Available commands:"
	@echo "  make install           - Install production dependencies"
	@echo "  make install-dev       - Install development dependencies"
	@echo "  make format            - Format code with black and isort"
	@echo "  make lint              - Run ruff linter"
	@echo "  make type-check        - Run mypy type checker"
	@echo "  make docstring-check   - Check docstring presence with interrogate"
	@echo "  make docstring-coverage- Generate docstring coverage report"
	@echo "  make test              - Run unit + integration (requires services running)"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests (requires services)"
	@echo "  make test-integration-services-up   - Start integration test services"
	@echo "  make test-integration-services-down - Stop integration test services"
	@echo "  make test-integration-services-status - Check services status"
	@echo "  make test-cov          - Run unit + integration with coverage (requires services)"
	@echo "  make test-all          - Complete test suite: start services, test with coverage, stop"
	@echo "  make test-cov-badge    - Generate test coverage badge"
	@echo "  make pre-commit-install - Install pre-commit hooks"
	@echo "  make pre-commit-run    - Run pre-commit on all files"
	@echo "  make clean             - Remove cache and build artifacts"
	@echo "  make run               - Run development server"
	@echo "  make compose-build     - Build Docker Compose services"
	@echo "  make compose-up        - Start Docker Compose services"
	@echo "  make compose-down      - Stop Docker Compose services"
	@echo "  make docker-build-dev  - Build development Docker image"
	@echo "  make docker-build-test - Build test Docker image"
	@echo "  make docker-build-prod - Build production Docker image"
	@echo "  make docker-test       - Run tests in Docker container"
	@echo "  make monitoring-up     - Start monitoring stack (Flask + Prometheus + Grafana)"
	@echo "  make monitoring-down   - Stop monitoring stack"
	@echo "  make monitoring-logs   - View monitoring stack logs"

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
install-dev:
	pip install -e ".[dev]"

# Format code
format:
	@echo "Running isort..."
	isort .
	@echo "Running ruff format..."
	ruff format .
	@echo "✓ Code formatted"

# Lint code
lint:
	@echo "Running ruff..."
	ruff check . --fix
	@echo "✓ Linting complete"

# Type checking
type-check:
	@echo "Running mypy..."
	mypy app/ --config-file=pyproject.toml
	@echo "✓ Type checking complete"

# Check docstring presence
docstring-check:
	@echo "Running interrogate..."
	interrogate app/ -c pyproject.toml
	@echo "✓ Docstring check complete"

# Generate docstring coverage report
docstring-coverage:
	@echo "Generating docstring coverage report..."
	interrogate app/ -c pyproject.toml --generate-badge docs/assets
	@echo "✓ Badge generated: docs/assets/interrogate_badge.svg"

# Run tests (assumes integration services are already running)
test:
	@echo "Running unit tests..."
	pytest tests/unit/ -v
	@echo ""
	@echo "Running integration tests..."
	@echo "⚠️  Make sure integration services are running: make test-integration-services-up"
	pytest tests/integration/ -v
	@echo ""
	@echo "✓ All tests completed"

# Run unit tests only
test-unit:
	pytest tests/unit/ -v

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	@echo "⚠️  Make sure integration services are running: make test-integration-services-up"
	pytest tests/integration/ -v

# Start integration test services (PostgreSQL, Redis, Identity)
test-integration-services-up:
	@echo "Starting integration test services..."
	docker compose -f docker-compose.test.yml up -d
	@echo "✓ Services started"
	@echo ""
	@echo "Waiting for services to be healthy..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12; do \
		HEALTHY=$$(docker compose -f docker-compose.test.yml ps | grep -c "(healthy)"); \
		if [ $$HEALTHY -eq 3 ]; then \
			echo "✓ All 3 services are healthy"; \
			break; \
		fi; \
		echo "  Waiting... ($$HEALTHY/3 services healthy)"; \
		sleep 5; \
		if [ $$i -eq 12 ]; then \
			echo "⚠️  Timeout: Not all services became healthy"; \
			docker compose -f docker-compose.test.yml ps; \
			exit 1; \
		fi; \
	done
	@echo ""
	docker compose -f docker-compose.test.yml ps
	@echo ""
	@echo "Services available at:"
	@echo "  PostgreSQL: localhost:5433"
	@echo "  Redis:      localhost:6380"
	@echo "  Identity:   http://localhost:5001"
	@echo ""
	@echo "Run tests with: make test-integration"

# Stop integration test services
test-integration-services-down:
	@echo "Stopping integration test services..."
	docker compose -f docker-compose.test.yml down
	@echo "✓ Services stopped"

# Check integration test services status
test-integration-services-status:
	@echo "Integration test services status:"
	docker compose -f docker-compose.test.yml ps

# Run all tests (unit + integration) with services
test-all:
	@echo "Running complete test suite..."
	@$(MAKE) test-integration-services-up
	@echo ""
	@echo "Running unit tests with coverage..."
	@rm -rf .coverage htmlcov/
	pytest tests/unit/ -v --cov=app --cov-report=
	@echo ""
	@echo "Flushing Redis to clear rate limiting counters..."
	@docker exec wfp-redis-test redis-cli FLUSHDB > /dev/null 2>&1 || true
	@echo ""
	@echo "Running integration tests with coverage (appending)..."
	pytest tests/integration/ -v --cov=app --cov-append --cov-report=
	@echo ""
	@echo "Generating combined coverage report..."
	coverage report
	coverage html
	@$(MAKE) test-integration-services-down
	@echo ""
	@echo "✓ All tests completed"
	@echo "✓ Coverage report generated in htmlcov/"

# Run tests with coverage (unit + integration combined)
test-cov:
	@echo "Running unit tests with coverage..."
	@rm -rf .coverage htmlcov/
	pytest tests/unit/ -v --cov=app --cov-report=
	@echo ""
	@echo "Flushing Redis to clear rate limiting counters..."
	@docker exec wfp-redis-test redis-cli FLUSHDB > /dev/null 2>&1 || true
	@echo ""
	@echo "Running integration tests with coverage (appending)..."
	pytest tests/integration/ -v --cov=app --cov-append --cov-report=
	@echo ""
	@echo "Generating combined coverage report..."
	coverage report
	coverage html
	@echo ""
	@echo "✓ Coverage report generated in htmlcov/"
	@echo "  Open htmlcov/index.html to view the report"

# Generate test coverage badge
test-cov-badge:
	@echo "Generating test coverage badge..."
	pytest tests/ --cov=app --cov-report=xml --cov-report=term -q
	genbadge coverage -i coverage.xml -o docs/coverage_badge.svg
	@echo "✅ Badge generated: docs/coverage_badge.svg"

# Install pre-commit hooks
pre-commit-install:
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

# Run pre-commit on all files
pre-commit-run:
	pre-commit run --all-files

# Clean cache and build artifacts
clean:
	@echo "Cleaning cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ htmlcov/ .coverage
	@echo "✓ Cleaned"

# Run development server
run:
	python run.py

# Docker Compose commands
compose-build:
	docker compose -f docker-compose.test.yml build

compose-up:
	docker compose -f docker-compose.test.yml up -d

compose-down:
	docker compose -f docker-compose.test.yml down

# Docker Image commands
docker-build-dev:
	docker build --target development -t wfp-guardian:dev .

docker-build-test:
	docker build --target test -t wfp-guardian:test .

docker-build-prod:
	docker build --target production -t wfp-guardian:prod .

docker-test: docker-build-test
	docker run --rm wfp-guardian:test

# Monitoring stack commands
monitoring-up:
	@echo "Starting monitoring stack (Flask + Prometheus + Grafana)..."
	docker compose -f docs/monitoring/docker-compose.monitoring.yml up -d
	@echo "✓ Monitoring stack started"
	@echo ""
	@echo "Access services at:"
	@echo "  Flask App:   http://localhost:5000"
	@echo "  Prometheus:  http://localhost:9090"
	@echo "  Grafana:     http://localhost:3000 (admin/admin)"
	@echo ""
	@echo "View logs with: make monitoring-logs"

monitoring-down:
	@echo "Stopping monitoring stack..."
	docker compose -f docs/monitoring/docker-compose.monitoring.yml down
	@echo "✓ Monitoring stack stopped"

monitoring-logs:
	docker compose -f docs/monitoring/docker-compose.monitoring.yml logs -f

# Quality check (all checks)
check: format lint type-check docstring-check test
	@echo "✓ All quality checks passed"
