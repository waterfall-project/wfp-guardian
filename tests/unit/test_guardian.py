# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Tests for Guardian access control utilities."""

from typing import TYPE_CHECKING, cast
from unittest.mock import patch
from uuid import UUID

import pytest
from flask import Flask, g

if TYPE_CHECKING:
    from flask.wrappers import Response

from app.utils.guardian import (
    Operation,
    _get_resource_name,
    _get_user_id,
    access_required,
    camel_to_snake,
)


class TestCamelToSnake:
    """Tests for camel_to_snake function."""

    def test_simple_camel_case(self):
        """Test simple CamelCase conversion."""
        assert camel_to_snake("ProjectResource") == "project_resource"

    def test_single_word(self):
        """Test single word conversion."""
        assert camel_to_snake("Project") == "project"

    def test_multiple_capitals(self):
        """Test multiple consecutive capitals."""
        assert camel_to_snake("HTTPResponse") == "http_response"

    def test_with_numbers(self):
        """Test conversion with numbers."""
        assert camel_to_snake("Project2Resource") == "project2_resource"

    def test_already_snake_case(self):
        """Test already snake_case string."""
        assert camel_to_snake("project_resource") == "project_resource"

    def test_milestone_list(self):
        """Test MilestoneList conversion."""
        assert camel_to_snake("MilestoneList") == "milestone_list"


class TestGetResourceName:
    """Tests for _get_resource_name function."""

    @pytest.fixture
    def app(self):
        """Create Flask application for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    def test_resource_name_from_kwargs(self, app):
        """Test resource name extraction from kwargs."""
        kwargs = {"resource_name": "projects"}
        with app.test_request_context():
            resource_name = _get_resource_name(kwargs, ())
            assert resource_name == "projects"

    def test_resource_name_from_class(self, app):
        """Test resource name extraction from class name."""

        class ProjectResource:
            pass

        instance = ProjectResource()
        with app.test_request_context():
            resource_name = _get_resource_name({}, (instance,))
            assert resource_name == "project"

    def test_resource_name_from_milestone_resource(self, app):
        """Test resource name extraction from MilestoneResource."""

        class MilestoneResource:
            pass

        instance = MilestoneResource()
        with app.test_request_context():
            resource_name = _get_resource_name({}, (instance,))
            assert resource_name == "milestone"

    def test_resource_name_removes_list_suffix(self, app):
        """Test that _list suffix is removed."""
        kwargs = {"resource_name": "projects_list"}
        with app.test_request_context():
            resource_name = _get_resource_name(kwargs, ())
            assert resource_name == "projects"

    def test_resource_name_from_list_class(self, app):
        """Test resource name from class ending with List but no Resource suffix."""

        class ProjectList:
            pass

        instance = ProjectList()
        with app.test_request_context():
            resource_name = _get_resource_name({}, (instance,))
            # Classes without "Resource" suffix return None
            assert resource_name is None

    def test_resource_name_no_resource_suffix(self, app):
        """Test class without Resource suffix."""

        class Project:
            pass

        instance = Project()
        with app.test_request_context():
            resource_name = _get_resource_name({}, (instance,))
            assert resource_name is None

    def test_resource_name_empty_args(self, app):
        """Test with empty args and kwargs."""
        with app.test_request_context():
            resource_name = _get_resource_name({}, ())
            assert resource_name is None

    def test_resource_name_from_view_args(self, app):
        """Test resource name from request.view_args."""
        with app.test_request_context("/", data={"resource_name": "milestones"}):
            # Manually set view_args since it's not set automatically
            from flask import request

            request.view_args = {"resource_name": "milestones"}
            resource_name = _get_resource_name({}, ())
            assert resource_name == "milestones"


class TestGetUserId:
    """Tests for _get_user_id function."""

    @pytest.fixture
    def app(self):
        """Create Flask application for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    def test_get_user_id_success(self, app):
        """Test successful user_id extraction."""
        user_id = "12345678-1234-5678-1234-567812345678"

        with app.app_context():
            g.user_context = {"user_id": user_id}

            result = _get_user_id()
            assert result == user_id

    def test_get_user_id_no_user_context(self, app):
        """Test when user_context is not in g."""
        with app.app_context():
            # Clear g - g is empty by default in new context
            result = _get_user_id()
            assert result is None

    def test_get_user_id_no_user_id_in_context(self, app):
        """Test when user_id is not in user_context."""
        with app.app_context():
            g.user_context = {"other_field": "value"}

            result = _get_user_id()
            assert result is None

    def test_get_user_id_converts_to_string(self, app):
        """Test that user_id is converted to string."""
        user_id = UUID("12345678-1234-5678-1234-567812345678")

        with app.app_context():
            g.user_context = {"user_id": user_id}

            result = _get_user_id()
            assert result == str(user_id)
            assert isinstance(result, str)


class TestAccessRequired:
    """Tests for access_required decorator."""

    @pytest.fixture
    def app(self):
        """Create Flask application for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def user_id(self):
        """Sample user UUID."""
        return "12345678-1234-5678-1234-567812345678"

    def test_access_granted(self, app, user_id):
        """Test successful access check."""

        class ProjectResource:
            @access_required(Operation.READ)
            def get(self):
                return {"status": "success"}, 200

        resource = ProjectResource()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with (
                patch("app.utils.guardian.check_access") as mock_check,
                app.test_request_context(),
            ):
                mock_check.return_value = {
                    "access_granted": True,
                    "reason": "permission_granted",
                    "message": "Access granted",
                }

                result = resource.get()

                assert result[0] == {"status": "success"}
                assert result[1] == 200

                # Verify check_access was called correctly
                mock_check.assert_called_once()
                call_kwargs = mock_check.call_args.kwargs
                assert str(call_kwargs["user_id"]) == user_id
                assert call_kwargs["operation"] == "READ"
                assert call_kwargs["resource"] == "project"

    def test_access_denied(self, app, user_id):
        """Test access denied."""

        class ProjectResource:
            @access_required(Operation.DELETE)
            def delete(self):
                return {"status": "deleted"}, 200

        resource = ProjectResource()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with (
                patch("app.utils.guardian.check_access") as mock_check,
                app.test_request_context(),
            ):
                mock_check.return_value = {
                    "access_granted": False,
                    "reason": "insufficient_permissions",
                    "message": "User lacks required permissions",
                }

                response_obj, status_code = resource.delete()

                assert status_code == 403
                # Cast to Response for type checking
                response = cast("Response", response_obj)
                json_data = response.get_json()
                assert json_data["error"] == "Access denied"
                assert json_data["reason"] == "insufficient_permissions"
                assert "lacks required permissions" in json_data["message"]

    def test_no_user_context(self, app):
        """Test when user_context is missing."""

        class ProjectResource:
            @access_required(Operation.LIST)
            def get(self):
                return {"projects": []}, 200

        resource = ProjectResource()

        with app.app_context(), app.test_request_context():
            # Don't set g.user_context
            response_obj, status_code = resource.get()

            assert status_code == 400
            # Cast to Response for type checking
            response = cast("Response", response_obj)
            json_data = response.get_json()
            assert json_data["error"] == "Access check failed"
            assert "User ID could not be determined" in json_data["message"]

    def test_no_user_id_in_context(self, app):
        """Test when user_id is missing from user_context."""

        class ProjectResource:
            @access_required(Operation.CREATE)
            def post(self):
                return {"id": "123"}, 201

        resource = ProjectResource()

        with app.app_context():
            g.user_context = {"other_field": "value"}

            with app.test_request_context():
                response_obj, status_code = resource.post()

                assert status_code == 400
                # Cast to Response for type checking
                response = cast("Response", response_obj)
                json_data = response.get_json()
                assert json_data["error"] == "Access check failed"
                assert "User ID could not be determined" in json_data["message"]

    def test_no_resource_name(self, app, user_id):
        """Test when resource name cannot be determined."""

        # Class without Resource suffix
        class SomeClass:
            @access_required(Operation.READ)
            def get(self):
                return {"data": []}, 200

        instance = SomeClass()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with app.test_request_context():
                response_obj, status_code = instance.get()

                assert status_code == 400
                # Cast to Response for type checking
                response = cast("Response", response_obj)
                json_data = response.get_json()
                assert json_data["error"] == "Access check failed"
                assert "Resource name could not be determined" in json_data["message"]

    def test_multiple_operations(self, app, user_id):
        """Test different operations on the same resource."""

        class MilestoneResource:
            @access_required(Operation.READ)
            def get(self):
                return {"milestone": {}}, 200

            @access_required(Operation.UPDATE)
            def put(self):
                return {"updated": True}, 200

            @access_required(Operation.DELETE)
            def delete(self):
                return {"deleted": True}, 200

        resource = MilestoneResource()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with (
                patch("app.utils.guardian.check_access") as mock_check,
                app.test_request_context(),
            ):
                mock_check.return_value = {
                    "access_granted": True,
                    "reason": "permission_granted",
                    "message": "Access granted",
                }

                # Test GET (READ)
                result = resource.get()
                assert result[1] == 200
                assert mock_check.call_args.kwargs["operation"] == "READ"

                # Test PUT (UPDATE)
                result = resource.put()
                assert result[1] == 200
                assert mock_check.call_args.kwargs["operation"] == "UPDATE"

                # Test DELETE
                result = resource.delete()
                assert result[1] == 200
                assert mock_check.call_args.kwargs["operation"] == "DELETE"

    def test_list_operation(self, app, user_id):
        """Test LIST operation."""

        class ProjectResource:
            @access_required(Operation.LIST)
            def get(self):
                return {"projects": []}, 200

        resource = ProjectResource()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with (
                patch("app.utils.guardian.check_access") as mock_check,
                app.test_request_context(),
            ):
                mock_check.return_value = {
                    "access_granted": True,
                    "reason": "permission_granted",
                    "message": "Access granted",
                }

                result = resource.get()
                assert result[1] == 200
                assert mock_check.call_args.kwargs["operation"] == "LIST"

    def test_create_operation(self, app, user_id):
        """Test CREATE operation."""

        class TaskResource:
            @access_required(Operation.CREATE)
            def post(self):
                return {"id": "new-task-id"}, 201

        resource = TaskResource()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with (
                patch("app.utils.guardian.check_access") as mock_check,
                app.test_request_context(),
            ):
                mock_check.return_value = {
                    "access_granted": True,
                    "reason": "permission_granted",
                    "message": "Access granted",
                }

                result = resource.post()
                assert result[1] == 201
                assert mock_check.call_args.kwargs["operation"] == "CREATE"
                assert mock_check.call_args.kwargs["resource"] == "task"

    @patch("app.utils.guardian.SERVICE_NAME", "test_service")
    def test_service_name_used(self, app, user_id):
        """Test that SERVICE_NAME is correctly used."""

        class ProjectResource:
            @access_required(Operation.READ)
            def get(self):
                return {"status": "ok"}, 200

        resource = ProjectResource()

        with app.app_context():
            g.user_context = {"user_id": user_id}

            with (
                patch("app.utils.guardian.check_access") as mock_check,
                app.test_request_context(),
            ):
                mock_check.return_value = {
                    "access_granted": True,
                    "reason": "permission_granted",
                    "message": "Access granted",
                }

                resource.get()

                # Verify SERVICE_NAME was used
                call_kwargs = mock_check.call_args.kwargs
                assert call_kwargs["service"] == "test_service"

    def test_decorator_preserves_function_metadata(self, app, user_id):
        """Test that decorator preserves function name and docstring."""

        class ProjectResource:
            @access_required(Operation.READ)
            def get(self):
                """Get project details."""
                return {"project": {}}, 200

        resource = ProjectResource()

        # Check that function metadata is preserved
        assert resource.get.__name__ == "get"
        assert resource.get.__doc__ == "Get project details."


class TestOperation:
    """Tests for Operation enum."""

    def test_operation_values(self):
        """Test that all operations have correct values."""
        assert Operation.LIST.value == "LIST"
        assert Operation.CREATE.value == "CREATE"
        assert Operation.READ.value == "READ"
        assert Operation.UPDATE.value == "UPDATE"
        assert Operation.DELETE.value == "DELETE"

    def test_operation_is_string(self):
        """Test that operations are strings."""
        assert isinstance(Operation.READ.value, str)
        assert isinstance(Operation.CREATE, str)
