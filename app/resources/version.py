# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Version resource module.

This module defines the VersionResource for exposing the current API version
through a REST endpoint.
"""

import subprocess  # nosec B404
import sys
from pathlib import Path

from flask import current_app
from flask_restful import Resource

from app.service import SERVICE_NAME
from app.utils import Operation, access_required, require_jwt_auth
from app.utils.limiter import limiter


def _read_version():
    """Read version from VERSION file."""
    version_file_path = Path(__file__).parent.parent.parent / "VERSION"
    try:
        with version_file_path.open(encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"
    except (OSError, UnicodeDecodeError):
        return "unknown"


def _read_commit():
    """Read commit hash from COMMIT file or git command."""
    commit_file_path = Path(__file__).parent.parent.parent / ".meta" / "COMMIT"
    try:
        with commit_file_path.open(encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to git command in development
        try:
            result = subprocess.run(  # nosec B603 B607
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            return result.stdout.strip()
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            return "unknown"
    except (OSError, UnicodeDecodeError):
        return "unknown"


def _read_build_date():
    """Read build date from BUILD_DATE file or git command."""
    build_date_file_path = Path(__file__).parent.parent.parent / ".meta" / "BUILD_DATE"
    try:
        with build_date_file_path.open(encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to git commit date in development
        try:
            result = subprocess.run(  # nosec B603 B607
                ["git", "log", "-1", "--format=%cd", "--date=iso-strict"],
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
            )
            return result.stdout.strip()
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            return "unknown"
    except (OSError, UnicodeDecodeError):
        return "unknown"


def _get_python_version():
    """Get Python version."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


API_VERSION = _read_version()
API_COMMIT = _read_commit()
API_BUILD_DATE = _read_build_date()
PYTHON_VERSION = _get_python_version()


class VersionResource(Resource):
    """Resource for providing the API version.

    Methods:
        get():
            Retrieve the current API version.
    """

    @require_jwt_auth
    @access_required(Operation.READ)
    @limiter.limit(lambda: current_app.config["RATE_LIMIT_CONFIGURATION"])
    def get(self):
        """Retrieve the current API version.

        Returns:
            dict: A dictionary containing the API version, commit hash,
            build date, Python version and HTTP status code 200.
        """
        return {
            "service": SERVICE_NAME,
            "version": API_VERSION,
            "commit": API_COMMIT,
            "build_date": API_BUILD_DATE,
            "python_version": PYTHON_VERSION,
        }, 200
