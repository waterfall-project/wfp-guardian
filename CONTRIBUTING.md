<div align="center">
  <img src="docs/assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Contributing to wfp-flask-template

Thank you for your interest in contributing to **wfp-flask-template**!

> **Note**: This template is part of the larger [Waterfall Development](https://github.com/bengeek06/waterfall-development) project. For overall project conventions, please refer to the main project's [CONTRIBUTING.md](https://github.com/bengeek06/waterfall-development/blob/develop/CONTRIBUTING.md).

## Table of Contents

- [Branch Strategy](#branch-strategy)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Contribution Workflow](#contribution-workflow)
- [Common Tasks](#common-tasks)

## Branch Strategy

We follow a **Git Flow** simplified strategy with three long-lived branches:

```
main (production) → staging (pre-production) → develop (development)
```

### Long-lived Branches

- **`main`**: Production-ready code
  - Protected branch
  - Only receives merges from `staging`
  - Tagged with version numbers (v1.0.0, v1.1.0, etc.)
  - Triggers production deployment

- **`staging`**: Pre-production/integration environment
  - Integration testing environment
  - Receives merges from `develop` or `release/*` branches
  - Bug fixes via `fix/*` branches
  - Triggers staging deployment

- **`develop`**: Active development
  - Latest development changes
  - Receives merges from `feature/*` branches
  - Base branch for new features

### Short-lived Branches

All feature and fix branches should be:
- Short-lived (delete after merge)
- Focused on a single feature/fix
- Named according to conventions

### Branch Naming Conventions

Follow these naming patterns for consistency:

```
feature/PROJ-123-short-description     # New features
fix/PROJ-456-bug-description           # Bug fixes for staging
hotfix/critical-issue-description      # Critical production fixes
release/v1.2.0                         # Release preparation
```

**Examples:**
- `feature/WFP-101-add-redis-caching`
- `feature/WFP-202-jwt-refresh-token`
- `fix/WFP-303-resolve-config-validation`
- `hotfix/critical-security-patch`
- `release/v2.0.0`

## Development Setup

### Prerequisites

- Python 3.9+
- pip and virtualenv

### Installation

```bash
# Clone the project
git clone <repo-url>
cd wfp-flask-template

# Virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Complete installation
make install-dev
make pre-commit-install
```

### Development Environment

```bash
# Copy the template
cp .env.example .env.development

# Main variables
FLASK_ENV=development
LOG_LEVEL=DEBUG
SERVICE_PORT=5000
```

### Start the Server

```bash
# Development mode
make run
# or
python run.py

# Production mode (test)
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## Code Standards

The project uses automated tools to ensure quality. See [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md) for complete details.

### Formatting and Linting

```bash
make format      # Black + isort
make lint        # Ruff with auto-fix
make type-check  # MyPy
make check       # All checks
```

### Pre-commit Hooks

Pre-commit hooks run automatically on each commit and check:
- Formatting (Black, isort)
- Linting (Ruff)
- Type checking (MyPy)
- Security (Bandit)
- Large files, private keys, merge conflicts
- YAML/JSON/TOML syntax

```bash
# Test manually
make pre-commit-run
```

### Naming Conventions (PEP 8)

```python
# Modules and packages
lowercase_with_underscores

# Classes
CapitalizedWords

# Functions and methods
lowercase_with_underscores

# Constants
UPPERCASE_WITH_UNDERSCORES
```

### General Conventions

- **File Names**:
  - Python: `snake_case.py`
  - Components: `PascalCase.py` (if applicable)
- **Constants**: `UPPER_CASE_WITH_UNDERSCORES`
- **Private Functions**: Prefix with underscore (`_private_function`)
- **API Routes**: Use kebab-case (`/api/auth/login`, `/api/users/create`)
- **Environment Variables**: `UPPER_CASE_WITH_UNDERSCORES`

### Type Hints

```python
from typing import Optional, List, Dict

def get_user(user_id: int) -> Optional[Dict[str, str]]:
    """Retrieve user by ID."""
    pass

def process_items(items: List[str]) -> None:
    """Process a list of items."""
    pass
```

### Docstrings (Google Style)

```python
def function_with_docstring(param1: str, param2: int) -> bool:
    """
    Short description of the function.

    Longer description if needed. Explain what the function does,
    any important behavior, and edge cases.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: Description of when this error is raised.
    """
    pass
```

## Testing

### Running Tests

```bash
# All tests
make test
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v -m integration

# With coverage
make test-cov
# Open htmlcov/index.html
```

### Writing Tests

```python
# tests/unit/test_example.py
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"
```

## Contribution Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-fix
```

Branch naming conventions:
- `feature/` : New features (merge to `develop`)
- `fix/` : Bug fixes (merge to `staging` or `develop`)
- `hotfix/` : Critical production fixes (merge to `main`)
- `release/` : Release preparation (merge to `staging`, then `main`)
- `docs/` : Documentation
- `refactor/` : Refactoring
- `test/` : Test additions/modifications

### 2. Develop

```bash
# Edit files
vim app/routes.py

# Check continuously
make format
make lint
make test
```

### 3. Commit

```bash
git add .
git commit -m "feat: feature description"
```

Commit message format (Conventional Commits):
- `feat:` : New feature
- `fix:` : Bug fix
- `docs:` : Documentation
- `style:` : Formatting (no code change)
- `refactor:` : Refactoring
- `test:` : Test additions/modifications
- `chore:` : Maintenance (deps, config)
- `perf:` : Performance improvement

**Examples:**
```
feat(auth): add JWT refresh token support

Implement automatic token refresh mechanism with
sliding window expiration.

Closes #123
```

```
fix(config): resolve environment variable validation

Add proper validation for required environment variables
and improve error messages.

Fixes #456
```

### 4. Push and Pull Request

```bash
git push origin feature/my-feature
```

Then, create a Pull Request on GitHub/GitLab with:
- Clear title
- Detailed description
- Reference to related issues
- Screenshots if relevant

### Workflow Examples

#### Creating a Feature

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/WFP-123-add-rate-limiting

# Work on your feature
# ... make changes, commit frequently ...

# Keep your branch up to date
git fetch origin
git rebase origin/develop

# Push your feature branch
git push origin feature/WFP-123-add-rate-limiting

# Create Pull Request to develop
```

#### Fixing a Bug in Staging

```bash
# Start from staging
git checkout staging
git pull origin staging

# Create fix branch
git checkout -b fix/WFP-456-resolve-config-error

# Fix the bug
# ... make changes, commit ...

# Push and create PR to staging
git push origin fix/WFP-456-resolve-config-error

# After merge to staging, cherry-pick to develop
git checkout develop
git cherry-pick <commit-hash>
```

#### Creating a Release

```bash
# Create release branch from develop
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# Bump version numbers, update CHANGELOG
# ... version bumps in pyproject.toml, __init__.py, etc. ...

# Commit changes
git commit -m "chore(release): prepare version 1.2.0"

# Push and create PR to staging
git push origin release/v1.2.0

# After testing in staging, merge to main
git checkout main
git merge staging --no-ff
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin main --tags

# Merge back to develop
git checkout develop
git merge release/v1.2.0
git push origin develop

# Delete release branch
git branch -d release/v1.2.0
git push origin --delete release/v1.2.0
```

#### Hotfix for Production

```bash
# Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-patch

# Fix the critical issue
# ... make changes, commit ...

# Merge to main and tag
git checkout main
git merge hotfix/critical-security-patch --no-ff
git tag -a v1.2.1 -m "Security hotfix 1.2.1"
git push origin main --tags

# Cherry-pick to staging and develop
git checkout staging
git cherry-pick <commit-hash>
git push origin staging

git checkout develop
git cherry-pick <commit-hash>
git push origin develop

# Delete hotfix branch
git branch -d hotfix/critical-security-patch
git push origin --delete hotfix/critical-security-patch
```

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Branch follows naming conventions
- [ ] Commits follow commit message guidelines
- [ ] All tests pass locally (`make test`)
- [ ] Code follows project coding conventions (`make check`)
- [ ] Documentation updated (if applicable)
- [ ] No merge conflicts with target branch
- [ ] PR description clearly explains changes
- [ ] Related issue(s) linked

### Review Process

1. **Create PR** with a clear title and description
2. **Automated checks** must pass (CI/CD, linting, tests)
3. **Code review** by at least one maintainer
4. **Address feedback** and push updates
5. **Approval** from maintainer(s)
6. **Merge** by maintainer (squash or merge commit based on context)

### Merge Strategies

- **Feature branches**: Squash and merge (clean history)
- **Release branches**: Merge commit (preserve release history)
- **Hotfix branches**: Merge commit (preserve fix details)

## Common Tasks

### Add a Route

```python
# app/routes.py
@app.route("/api/new-endpoint", methods=["GET"])
def new_endpoint():
    """New endpoint description."""
    return jsonify({"message": "success"}), 200
```

### Add a Flask-RESTful Resource

```python
# app/resources/my_resource.py
from flask_restful import Resource
from flask import request

class MyResource(Resource):
    """My resource description."""

    def get(self):
        """Get method."""
        return {"message": "success"}, 200

    def post(self):
        """Post method."""
        data = request.get_json()
        return {"message": "created"}, 201
```

```python
# app/__init__.py
from app.resources.my_resource import MyResource

api.add_resource(MyResource, "/api/my-resource")
```

### Add a Configuration Variable

```python
# app/config.py
class Config:
    """Base configuration."""
    NEW_SETTING = os.getenv("NEW_SETTING", "default_value")
```

```bash
# .env.development
NEW_SETTING=development_value
```

### Add a SQLAlchemy Model

```python
# app/models/my_model.py
from app.models.db import db

class MyModel(db.Model):
    """My model description."""

    __tablename__ = "my_models"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat()
        }
```

### Add a Dependency

Add the package to `pyproject.toml` in the `dependencies` or `dev` section.

```bash
# Reinstall
make install-dev
```

## Questions and Support

For any questions:
- **Documentation**: Check the [README.md](README.md)
- **Issues**: Search existing issues or create a new one on GitHub/GitLab
- **Main Project**: See [Waterfall Development CONTRIBUTING.md](https://github.com/bengeek06/waterfall-development/blob/develop/CONTRIBUTING.md)
- **Contact**: contact@waterfall-project.pro

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

This project is dual-licensed (AGPLv3 / Commercial). See [LICENSE](LICENSE) and [COMMERCIAL-LICENSE.txt](COMMERCIAL-LICENSE.txt).

---

**Remember**: Always refer to the [main CONTRIBUTING.md](https://github.com/bengeek06/waterfall-development/blob/develop/CONTRIBUTING.md) for branch strategy, commit conventions, and pull request process!
