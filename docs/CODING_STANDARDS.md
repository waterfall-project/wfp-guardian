<div align="center">
  <img src="assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Coding Standards

This project follows professional Python coding standards to ensure code quality, maintainability, and consistency.

## Applied Standards

### 1. PEP 8 - Style Guide for Python Code

Official standard from the Python community and reference base for all Python files.

**Naming conventions:**
- Modules and packages: `lowercase_with_underscores`
- Classes: `CapitalizedWords` (PascalCase)
- Functions and methods: `lowercase_with_underscores`
- Constants: `UPPERCASE_WITH_UNDERSCORES`
- Variables: `lowercase_with_underscores`

**Line length:** 88 characters (Black default)

**Whitespace:**
```python
# Good
spam(ham[1], {eggs: 2})
foo = (0,)

# Bad
spam( ham[ 1 ], { eggs: 2 } )
bar = (0, )
```

[Official PEP 8 Documentation](https://peps.python.org/pep-0008/)

### 2. Ruff Format - Code Formatter

Automatic and non-negotiable code formatting using Ruff's built-in formatter.

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

**Features:**
- Double quotes by default
- Trailing commas in multi-line
- Consistent and deterministic formatting
- Compatible with Black style

[Ruff Formatter Documentation](https://docs.astral.sh/ruff/formatter/)

### 3. isort - Import Sorting

Automatic import organization compatible with Ruff.

**Configuration** (`pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 88
```

**Import order:**
```python
# 1. Standard library
import os
import sys
from typing import Optional

# 2. Third-party packages
from flask import Flask, request
from sqlalchemy import Column

# 3. Local application imports
from app.models.db import db
from app.utils.logger import logger
```

[isort Documentation](https://pycqa.github.io/isort/)

### 4. Ruff - Fast Linter

Ultra-fast linter that replaces flake8, pylint, pyupgrade, etc.

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 88
target-version = "py39"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM", "TCH", "PTH"]
```

**Activated rules:**
- `E/W` : pycodestyle errors/warnings
- `F` : Pyflakes
- `I` : isort
- `N` : pep8-naming
- `UP` : pyupgrade
- `B` : flake8-bugbear
- `C4` : flake8-comprehensions
- `SIM` : flake8-simplify
- `TCH` : flake8-type-checking
- `PTH` : flake8-use-pathlib

[Ruff Documentation](https://docs.astral.sh/ruff/)

### 5. MyPy - Static Type Checker

Static type checking.

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

**Type Hints (PEP 484, 585):**
```python
from typing import Optional, List, Dict

def get_user(user_id: int) -> Optional[Dict[str, str]]:
    """Retrieve user by ID."""
    pass

def process_items(items: List[str]) -> None:
    """Process a list of items."""
    pass
```

[MyPy Documentation](https://mypy.readthedocs.io/)

### 6. Bandit - Security Linter

Security vulnerability detection.

**Configuration** (`pyproject.toml`):
```toml
[tool.bandit]
exclude_dirs = ["tests", "migrations"]
skips = ["B101"]  # Skip assert_used
```

[Bandit Documentation](https://bandit.readthedocs.io/)

## Docstrings (PEP 257 + Google Style)

Use Google format for docstrings:

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

    Example:
        >>> function_with_docstring("test", 42)
        True
    """
    pass
```

[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

## Pre-commit Hooks

Pre-commit hooks run automatically on each commit:

1. **isort** - Import organization
2. **Ruff** - Linting with auto-fix
3. **Ruff Format** - Automatic formatting
4. **MyPy** - Type checking
5. **Bandit** - Security analysis
6. **check-added-large-files** - Prevents files > 1MB
7. **check-merge-conflict** - Detects unresolved conflicts
8. **debug-statements** - Detects `import pdb`, `breakpoint()`
9. **check-yaml/json/toml** - Syntax validation
10. **end-of-file-fixer** - Adds final newline
11. **trailing-whitespace** - Removes trailing spaces
12. **detect-private-key** - Detects private keys

Configuration in `.pre-commit-config.yaml`.

## IDE Configuration

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit"
  },
  "editor.rulers": [88]
}
```

### PyCharm

1. Install plugins: Ruff, Mypy
2. Settings → Tools → Ruff → Enable
3. Settings → Editor → Code Style → Formatter → Ruff

## Rule Exceptions

Use exceptions sparingly and document why:

```python
# ruff: noqa: E501
# mypy: ignore-errors
```

## References

- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Formatter Documentation](https://docs.astral.sh/ruff/formatter/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)

  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "python.analysis.typeCheckingMode": "basic",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Installer les plugins : Ruff, Mypy
2. Settings → Tools → Ruff → Enable
3. Settings → Editor → Code Style → Formatter → Ruff

## Exceptions

Certaines règles peuvent être ignorées dans des cas spécifiques :

```python
# ruff: noqa: E501
# mypy: ignore-errors
```

Mais utilisez ces exceptions avec parcimonie et documentez pourquoi.

## Références

- [PEP 8 - Style Guide](https://peps.python.org/pep-0008/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Formatter Documentation](https://docs.astral.sh/ruff/formatter/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
