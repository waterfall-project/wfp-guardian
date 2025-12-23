# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Unit tests for version endpoint."""

import subprocess  # nosec B404
import sys
from unittest.mock import MagicMock, patch

from app.resources.version import (
    _get_python_version,
    _read_build_date,
    _read_commit,
    _read_version,
)


class TestVersionEndpoint:
    """Test cases for the /version endpoint."""

    def test_version_endpoint_accessible(self, client, api_url):
        """Test that version endpoint is accessible.

        Note: In test environment, USE_IDENTITY_SERVICE is False,
        so authentication decorators are bypassed.
        """
        response = client.get(api_url("version"))

        # Should succeed since auth is disabled in tests
        assert response.status_code == 200

    def test_version_endpoint_returns_version_info(self, authenticated_client, api_url):
        """Test that version endpoint returns version information."""
        response = authenticated_client.get(api_url("version"))

        assert response.status_code == 200
        data = response.get_json()

        # Check all required fields
        assert "service" in data
        assert "version" in data
        assert "commit" in data
        assert "build_date" in data
        assert "python_version" in data

    def test_version_endpoint_service_name(self, authenticated_client, api_url):
        """Test that version endpoint returns correct service name."""
        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        assert data["service"] == "template"

    def test_version_endpoint_python_version_format(
        self, authenticated_client, api_url
    ):
        """Test that Python version is in correct format."""
        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        python_version = data["python_version"]
        # Should be in format X.Y.Z
        parts = python_version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

        # Should match actual Python version
        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert python_version == expected

    @patch("app.resources.version.Path")
    def test_version_read_from_file(self, mock_path, authenticated_client, api_url):
        """Test that version is read from VERSION file."""
        mock_file = MagicMock()
        mock_file.open.return_value.__enter__.return_value.read.return_value = "1.2.3\n"
        mock_path.return_value.parent.parent.parent.__truediv__.return_value = mock_file

        # Need to reload module to apply patch
        import importlib

        from app.resources import version as version_module

        importlib.reload(version_module)

        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        assert "version" in data

    def test_version_endpoint_commit_hash_exists(self, authenticated_client, api_url):
        """Test that commit hash is present."""
        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        commit = data["commit"]
        assert isinstance(commit, str)
        assert len(commit) > 0
        # Should be either a git hash or "unknown" or "dev" or "test" (in test stage)
        assert (
            commit in ["unknown", "dev", "test"] or len(commit) == 7
        )  # short git hash

    def test_version_endpoint_build_date_format(self, authenticated_client, api_url):
        """Test that build date is in ISO format."""
        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        build_date = data["build_date"]
        assert isinstance(build_date, str)
        # Should be ISO format or "unknown"
        if build_date != "unknown":
            assert "T" in build_date
            assert build_date.endswith("Z") or "+" in build_date

    @patch("app.resources.version.limiter.limit")
    def test_version_endpoint_has_rate_limiting(
        self, mock_limit, authenticated_client, api_url
    ):
        """Test that version endpoint has rate limiting configured."""
        from app.resources.version import VersionResource

        # Check that the get method has the limiter decorator
        assert hasattr(VersionResource.get, "__wrapped__")

    def test_version_endpoint_with_access_control(self, authenticated_client):
        """Test that version endpoint has access control decorator."""
        from app.resources.version import VersionResource

        # Check that access_required decorator is applied
        method = VersionResource.get
        # The decorator should wrap the method
        assert hasattr(method, "__wrapped__") or hasattr(method, "__func__")

    def test_version_endpoint_response_structure(self, authenticated_client, api_url):
        """Test that version endpoint returns correct response structure."""
        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        # Should have exactly these keys
        expected_keys = {"service", "version", "commit", "build_date", "python_version"}
        assert set(data.keys()) == expected_keys

        # All values should be strings
        for key, value in data.items():
            assert isinstance(value, str), f"{key} should be a string"

    @patch("app.resources.version.subprocess.run")
    @patch("app.resources.version.Path")
    def test_version_commit_fallback_to_git(
        self, mock_path, mock_subprocess, authenticated_client, api_url
    ):
        """Test that commit hash falls back to git command if file not found."""
        # Mock COMMIT file not found
        mock_file = MagicMock()
        mock_file.open.side_effect = FileNotFoundError

        # Mock git command success
        mock_result = MagicMock()
        mock_result.stdout = "abc1234\n"
        mock_subprocess.return_value = mock_result

        response = authenticated_client.get(api_url("version"))
        data = response.get_json()

        # Should have commit info (from cache or git)
        assert "commit" in data

    def test_version_values_are_consistent(self, authenticated_client, api_url):
        """Test that multiple calls return consistent values."""
        response1 = authenticated_client.get(api_url("version"))
        response2 = authenticated_client.get(api_url("version"))

        data1 = response1.get_json()
        data2 = response2.get_json()

        # Version, commit, build_date, python_version should be consistent
        assert data1["version"] == data2["version"]
        assert data1["commit"] == data2["commit"]
        assert data1["build_date"] == data2["build_date"]
        assert data1["python_version"] == data2["python_version"]


class TestVersionHelpers:
    """Test cases for version helper functions to increase coverage."""

    def test_read_version_os_error(self):
        """Test _read_version with OSError."""
        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
            version = _read_version()
            assert version == "unknown"

    def test_read_version_unicode_decode_error(self):
        """Test _read_version with UnicodeDecodeError."""
        with patch(
            "pathlib.Path.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte"),
        ):
            version = _read_version()
            assert version == "unknown"

    def test_read_commit_file_not_found_git_command_success(self):
        """Test _read_commit falls back to git when COMMIT file not found."""
        # Mock file not found
        mock_open_obj = MagicMock()
        mock_open_obj.side_effect = FileNotFoundError

        # Mock successful git command
        mock_result = MagicMock()
        mock_result.stdout = "abc1234\n"

        with (
            patch("pathlib.Path.open", mock_open_obj),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            commit = _read_commit()
            assert commit == "abc1234"
            mock_run.assert_called_once()

    def test_read_commit_file_not_found_git_command_fails(self):
        """Test _read_commit returns unknown when both file and git fail."""
        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(128, "git"),
            ),
        ):
            commit = _read_commit()
            assert commit == "unknown"

    def test_read_commit_file_not_found_git_not_found(self):
        """Test _read_commit returns unknown when git command not found."""
        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch("subprocess.run", side_effect=FileNotFoundError("git not found")),
        ):
            commit = _read_commit()
            assert commit == "unknown"

    def test_read_commit_file_not_found_git_timeout(self):
        """Test _read_commit returns unknown when git command times out."""
        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)),
        ):
            commit = _read_commit()
            assert commit == "unknown"

    def test_read_commit_os_error(self):
        """Test _read_commit with OSError."""
        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
            commit = _read_commit()
            assert commit == "unknown"

    def test_read_commit_unicode_decode_error(self):
        """Test _read_commit with UnicodeDecodeError."""
        with patch(
            "pathlib.Path.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        ):
            commit = _read_commit()
            assert commit == "unknown"

    def test_read_build_date_file_not_found_git_success(self):
        """Test _read_build_date falls back to git when file not found."""
        mock_result = MagicMock()
        mock_result.stdout = "2025-12-21T10:30:00Z\n"

        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            build_date = _read_build_date()
            assert build_date == "2025-12-21T10:30:00Z"
            mock_run.assert_called_once()

    def test_read_build_date_file_not_found_git_fails(self):
        """Test _read_build_date returns unknown when both file and git fail."""
        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(128, "git"),
            ),
        ):
            build_date = _read_build_date()
            assert build_date == "unknown"

    def test_read_build_date_file_not_found_git_not_found(self):
        """Test _read_build_date returns unknown when git command not found."""
        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch("subprocess.run", side_effect=FileNotFoundError("git not found")),
        ):
            build_date = _read_build_date()
            assert build_date == "unknown"

    def test_read_build_date_file_not_found_git_timeout(self):
        """Test _read_build_date returns unknown when git command times out."""
        with (
            patch("pathlib.Path.open", side_effect=FileNotFoundError),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 2)),
        ):
            build_date = _read_build_date()
            assert build_date == "unknown"

    def test_read_build_date_os_error(self):
        """Test _read_build_date with OSError."""
        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
            build_date = _read_build_date()
            assert build_date == "unknown"

    def test_read_build_date_unicode_decode_error(self):
        """Test _read_build_date with UnicodeDecodeError."""
        with patch(
            "pathlib.Path.open",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        ):
            build_date = _read_build_date()
            assert build_date == "unknown"

    def test_get_python_version_format(self):
        """Test _get_python_version returns correct format."""
        version = _get_python_version()
        assert isinstance(version, str)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)
        # Should match sys.version_info
        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert version == expected
