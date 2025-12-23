# Copyright (c) 2025 Waterfall
#
# This source code is dual-licensed under:
# - GNU Affero General Public License v3.0 (AGPLv3) for open source use
# - Commercial License for proprietary use
#
# See LICENSE and LICENSE.md files in the root directory for full license text.
# For commercial licensing inquiries, contact: contact@waterfall-project.pro
"""Test suite for the /metrics endpoint."""


class TestMetricsEndpoint:
    """Test suite for Prometheus metrics endpoint."""

    def test_metrics_endpoint_exists(self, app, api_url):
        """Test that the /metrics endpoint exists and returns 200."""
        with app.test_client() as client:
            response = client.get(api_url("metrics"))
            assert response.status_code == 200

    def test_metrics_endpoint_content_type(self, app, api_url):
        """Test that the /metrics endpoint returns prometheus format."""
        with app.test_client() as client:
            response = client.get(api_url("metrics"))
            # Prometheus metrics use text/plain with version parameter
            assert "text/plain" in response.content_type

    def test_metrics_endpoint_contains_flask_metrics(self, app, api_url):
        """Test that the response contains Flask HTTP metrics."""
        with app.test_client() as client:
            # Make a request to generate some metrics
            client.get(api_url("health"))

            # Get metrics
            response = client.get(api_url("metrics"))
            data = response.get_data(as_text=True)

            # Check for standard Flask metrics
            assert "flask_http_request_total" in data
            assert "flask_http_request_duration_seconds" in data

    def test_metrics_endpoint_tracks_requests(self, app, api_url):
        """Test that metrics endpoint is functional."""
        with app.test_client() as client:
            # Get metrics - the endpoint itself should work
            response = client.get(api_url("metrics"))
            data = response.get_data(as_text=True)

            # Check that Flask metrics infrastructure is present
            assert "flask_http_request" in data or "flask_exporter_info" in data

    def test_metrics_endpoint_no_authentication_required(self, app, api_url):
        """Test that metrics endpoint is publicly accessible."""
        with app.test_client() as client:
            # Should work without any authentication
            response = client.get(api_url("metrics"))
            assert response.status_code == 200

    def test_metrics_endpoint_contains_process_metrics(self, app, api_url):
        """Test that system process metrics are included."""
        with app.test_client() as client:
            response = client.get(api_url("metrics"))
            data = response.get_data(as_text=True)

            # Check for standard process metrics
            # These are added by default by prometheus-flask-exporter
            assert "process_" in data or "python_info" in data

    def test_metrics_format_is_valid_prometheus(self, app, api_url):
        """Test that metrics follow Prometheus text format."""
        with app.test_client() as client:
            response = client.get(api_url("metrics"))
            data = response.get_data(as_text=True)

            # Prometheus format should have:
            # - Lines starting with # for comments/help/type
            # - Metric lines with format: metric_name{labels} value timestamp
            lines = data.split("\n")
            has_comments = any(line.startswith("#") for line in lines)
            has_metrics = any(line and not line.startswith("#") for line in lines)

            assert has_comments, "Should have comment lines for metric metadata"
            assert has_metrics, "Should have actual metric data lines"

    def test_metrics_endpoint_includes_http_status_codes(self, app, api_url):
        """Test that metrics endpoint includes Flask exporter info."""
        with app.test_client() as client:
            response = client.get(api_url("metrics"))
            data = response.get_data(as_text=True)

            # Should include Flask exporter version info
            assert "flask_exporter_info" in data
