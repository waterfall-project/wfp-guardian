# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Flask application routes.

This module is responsible for registering the routes of the REST API
and linking them to the corresponding resources.
"""

from pathlib import Path

from flask_restful import Api

from app.resources.check_access import CheckAccessResource
from app.resources.config import ConfigResource
from app.resources.dummy_res import DummyListResource, DummyResource
from app.resources.health import HealthResource
from app.resources.ready import ReadyResource
from app.resources.version import VersionResource
from app.utils.logger import logger


def _get_api_version() -> str:
    """Read the VERSION file and extract the major version number.

    Returns:
        str: API version prefix in format 'vX' (e.g., 'v0', 'v1').
    """
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        version = version_file.read_text().strip()
        major_version = version.split(".")[0]
        return f"v{major_version}"
    except (FileNotFoundError, IndexError) as e:
        logger.warning(f"Failed to read VERSION file: {e}. Using default 'v0'.")
        return "v0"


def register_routes(app):
    """Register the REST API routes on the Flask application.

    Args:
        app (Flask): The Flask application instance.

    This function creates a Flask-RESTful Api instance, adds the resource
    endpoints for managing dummy items, and logs the successful registration
    of routes.
    """
    api = Api(app)
    api_version = _get_api_version()

    # Health endpoint (lightweight)
    api.add_resource(HealthResource, f"/{api_version}/health")

    # Ready endpoint (comprehensive dependency checks)
    api.add_resource(ReadyResource, f"/{api_version}/ready")

    # Version endpoint
    api.add_resource(VersionResource, f"/{api_version}/version")

    # Configuration endpoint with rate limiting
    api.add_resource(ConfigResource, f"/{api_version}/configuration")

    # Dummy CRUD endpoints
    api.add_resource(DummyListResource, f"/{api_version}/dummies")
    api.add_resource(DummyResource, f"/{api_version}/dummies/<string:dummy_id>")

    # Access Control endpoint
    api.add_resource(CheckAccessResource, f"/{api_version}/check-access")

    logger.info("Routes registered successfully.")
