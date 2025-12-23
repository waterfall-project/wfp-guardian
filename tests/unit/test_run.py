# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""
Test suite for the run module of a Flask application.

This module tests the configuration mapping logic based on the
environment variable `FLASK_ENV` and the main application startup.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from run import main


@pytest.mark.parametrize(
    "env,expected_config,expected_debug",
    [
        ("production", "app.config.ProductionConfig", False),
        ("staging", "app.config.StagingConfig", True),
        ("integration", "app.config.IntegrationConfig", False),
        ("testing", "app.config.TestingConfig", False),
        ("development", "app.config.DevelopmentConfig", True),
        ("unknown", "app.config.DevelopmentConfig", False),
    ],
)
def test_run_config_mapping(env, expected_config, expected_debug):
    """
    Test that the run module correctly maps FLASK_ENV to config class.
    """
    # Set environment
    original_env = os.environ.get("FLASK_ENV")
    original_docker = os.environ.get("IN_DOCKER_CONTAINER")
    original_app_mode = os.environ.get("APP_MODE")

    os.environ["FLASK_ENV"] = env

    # Ensure we're not in Docker for this test
    if original_docker:
        del os.environ["IN_DOCKER_CONTAINER"]
    if original_app_mode:
        del os.environ["APP_MODE"]

    try:
        # Mock all external dependencies
        mock_create_app = MagicMock()
        mock_logger = MagicMock()
        mock_load_dotenv = MagicMock()
        mock_os_path_exists = MagicMock(return_value=True)

        # Mock the app instance to prevent actual server startup
        mock_app = MagicMock()
        # Mock app.config.get to return appropriate values
        mock_app.config.get.side_effect = lambda key, default=None: {
            "DEBUG": expected_debug,
            "SERVICE_PORT": 5000,
        }.get(key, default)
        mock_create_app.return_value = mock_app

        with (
            patch("run.create_app", mock_create_app),
            patch("run.logger", mock_logger),
            patch("run.load_dotenv", mock_load_dotenv),
            patch("run.os.path.exists", mock_os_path_exists),
        ):
            # Call main function
            main()

            # Verify create_app was called with correct config
            mock_create_app.assert_called_once_with(expected_config)

            # Verify app.run was called with debug from app config
            mock_app.run.assert_called_once_with(
                host="0.0.0.0",  # nosec B104
                port=5000,
                debug=expected_debug,  # nosec B104
            )

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]

        if original_docker is not None:
            os.environ["IN_DOCKER_CONTAINER"] = original_docker

        if original_app_mode is not None:
            os.environ["APP_MODE"] = original_app_mode


def test_main_with_custom_port():
    """
    Test that the main function uses custom SERVICE_PORT from configuration.
    """
    original_env = os.environ.get("FLASK_ENV")
    original_service_port = os.environ.get("SERVICE_PORT")
    original_docker = os.environ.get("IN_DOCKER_CONTAINER")
    original_app_mode = os.environ.get("APP_MODE")

    os.environ["FLASK_ENV"] = "development"
    os.environ["SERVICE_PORT"] = "8080"

    # Ensure we're not in Docker for this test
    if original_docker:
        del os.environ["IN_DOCKER_CONTAINER"]
    if original_app_mode:
        del os.environ["APP_MODE"]

    try:
        mock_create_app = MagicMock()
        mock_logger = MagicMock()
        mock_load_dotenv = MagicMock()
        mock_os_path_exists = MagicMock(return_value=True)
        mock_app = MagicMock()
        # Mock debug=True for development and SERVICE_PORT=8080
        mock_app.config.get.side_effect = lambda key, default=None: {
            "DEBUG": True,
            "SERVICE_PORT": 8080,
        }.get(key, default)
        mock_create_app.return_value = mock_app

        with (
            patch("run.create_app", mock_create_app),
            patch("run.logger", mock_logger),
            patch("run.load_dotenv", mock_load_dotenv),
            patch("run.os.path.exists", mock_os_path_exists),
        ):
            main()

            # Verify app.run was called with custom port and debug from config
            mock_app.run.assert_called_once_with(host="0.0.0.0", port=8080, debug=True)  # nosec B104
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]

        if original_service_port is not None:
            os.environ["SERVICE_PORT"] = original_service_port
        elif "SERVICE_PORT" in os.environ:
            del os.environ["SERVICE_PORT"]

        if original_docker is not None:
            os.environ["IN_DOCKER_CONTAINER"] = original_docker

        if original_app_mode is not None:
            os.environ["APP_MODE"] = original_app_mode


def test_main_debug_mode_from_app_config():
    """
    Test that debug mode is retrieved from app configuration.
    """
    test_cases = [
        ("production", False),
        ("staging", True),
        ("development", True),
        ("testing", False),
    ]

    for env, expected_debug in test_cases:
        original_env = os.environ.get("FLASK_ENV")
        original_docker = os.environ.get("IN_DOCKER_CONTAINER")
        original_app_mode = os.environ.get("APP_MODE")

        os.environ["FLASK_ENV"] = env

        # Ensure we're not in Docker for this test
        if original_docker:
            del os.environ["IN_DOCKER_CONTAINER"]
        if original_app_mode:
            del os.environ["APP_MODE"]

        try:
            mock_create_app = MagicMock()
            mock_logger = MagicMock()
            mock_load_dotenv = MagicMock()
            mock_os_path_exists = MagicMock(return_value=True)
            mock_app = MagicMock()
            # Mock app.config.get to return expected debug value and port
            # Use default argument to capture loop variable
            mock_app.config.get.side_effect = (
                lambda key, default=None, debug=expected_debug: {
                    "DEBUG": debug,
                    "SERVICE_PORT": 5000,
                }.get(key, default)
            )
            mock_create_app.return_value = mock_app

            with (
                patch("run.create_app", mock_create_app),
                patch("run.logger", mock_logger),
                patch("run.load_dotenv", mock_load_dotenv),
                patch("run.os.path.exists", mock_os_path_exists),
            ):
                main()

                # Verify app.run was called with correct debug value
                mock_app.run.assert_called_once_with(
                    host="0.0.0.0",  # nosec B104
                    port=5000,
                    debug=expected_debug,
                )

        finally:
            # Restore original environment
            if original_env is not None:
                os.environ["FLASK_ENV"] = original_env
            elif "FLASK_ENV" in os.environ:
                del os.environ["FLASK_ENV"]

            if original_docker is not None:
                os.environ["IN_DOCKER_CONTAINER"] = original_docker

            if original_app_mode is not None:
                os.environ["APP_MODE"] = original_app_mode


def test_docker_environment_skips_env_file():
    """
    Test that .env file loading is skipped when running in Docker.
    """
    original_env = os.environ.get("FLASK_ENV")
    original_docker = os.environ.get("IN_DOCKER_CONTAINER")

    os.environ["FLASK_ENV"] = "development"
    os.environ["IN_DOCKER_CONTAINER"] = "true"

    try:
        mock_create_app = MagicMock()
        mock_logger = MagicMock()
        mock_load_dotenv = MagicMock()
        mock_os_path_exists = MagicMock()
        mock_app = MagicMock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            "DEBUG": True,
            "SERVICE_PORT": 5000,
        }.get(key, default)
        mock_create_app.return_value = mock_app

        with (
            patch("run.create_app", mock_create_app),
            patch("run.logger", mock_logger),
            patch("run.load_dotenv", mock_load_dotenv),
            patch("run.os.path.exists", mock_os_path_exists),
        ):
            main()

            # Verify .env file loading was skipped
            mock_os_path_exists.assert_not_called()
            mock_load_dotenv.assert_not_called()
            mock_logger.info.assert_any_call(
                "Running in Docker container, skipping .env file loading"
            )

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]

        if original_docker is not None:
            os.environ["IN_DOCKER_CONTAINER"] = original_docker
        elif "IN_DOCKER_CONTAINER" in os.environ:
            del os.environ["IN_DOCKER_CONTAINER"]


def test_app_mode_skips_env_file():
    """
    Test that .env file loading is skipped when APP_MODE is set.
    """
    original_env = os.environ.get("FLASK_ENV")
    original_app_mode = os.environ.get("APP_MODE")

    os.environ["FLASK_ENV"] = "staging"
    os.environ["APP_MODE"] = "staging"

    try:
        mock_create_app = MagicMock()
        mock_logger = MagicMock()
        mock_load_dotenv = MagicMock()
        mock_os_path_exists = MagicMock()
        mock_app = MagicMock()
        mock_app.config.get.side_effect = lambda key, default=None: {
            "DEBUG": False,
            "SERVICE_PORT": 5000,
        }.get(key, default)
        mock_create_app.return_value = mock_app

        with (
            patch("run.create_app", mock_create_app),
            patch("run.logger", mock_logger),
            patch("run.load_dotenv", mock_load_dotenv),
            patch("run.os.path.exists", mock_os_path_exists),
        ):
            main()

            # Verify .env file loading was skipped
            mock_os_path_exists.assert_not_called()
            mock_load_dotenv.assert_not_called()
            mock_logger.info.assert_any_call(
                "Running in Docker container, skipping .env file loading"
            )

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["FLASK_ENV"] = original_env
        elif "FLASK_ENV" in os.environ:
            del os.environ["FLASK_ENV"]

        if original_app_mode is not None:
            os.environ["APP_MODE"] = original_app_mode
        elif "APP_MODE" in os.environ:
            del os.environ["APP_MODE"]
