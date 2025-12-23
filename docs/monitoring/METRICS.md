<div align="center">
  <img src="../assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Metrics Endpoint Documentation

## Overview

The `/metrics` endpoint exposes Prometheus-compatible metrics for monitoring and observability.

## Endpoint Details

- **URL**: `/metrics`
- **Method**: `GET`
- **Authentication**: Not required (public endpoint)
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

## Available Metrics

### Flask HTTP Metrics

#### `flask_http_request_total`
- **Type**: Counter
- **Description**: Total number of HTTP requests
- **Labels**:
  - `method`: HTTP method (GET, POST, etc.)
  - `status`: HTTP status code
  - `endpoint`: Flask endpoint name

#### `flask_http_request_duration_seconds`
- **Type**: Histogram
- **Description**: HTTP request latency in seconds
- **Labels**:
  - `method`: HTTP method
  - `status`: HTTP status code
  - `endpoint`: Flask endpoint name

#### `flask_http_request_exceptions_total`
- **Type**: Counter
- **Description**: Total number of HTTP requests that resulted in an exception
- **Labels**:
  - `method`: HTTP method
  - `status`: HTTP status code
  - `endpoint`: Flask endpoint name

### Python Process Metrics

#### `python_info`
- **Type**: Gauge
- **Description**: Python platform information
- **Labels**:
  - `implementation`: Python implementation (CPython, PyPy, etc.)
  - `major`: Major version number
  - `minor`: Minor version number
  - `patchlevel`: Patch level
  - `version`: Full version string

#### `python_gc_objects_collected_total`
- **Type**: Counter
- **Description**: Objects collected during garbage collection
- **Labels**:
  - `generation`: GC generation (0, 1, 2)

#### `python_gc_objects_uncollectable_total`
- **Type**: Counter
- **Description**: Uncollectable objects found during GC
- **Labels**:
  - `generation`: GC generation

#### `python_gc_collections_total`
- **Type**: Counter
- **Description**: Number of times this generation was collected
- **Labels**:
  - `generation`: GC generation

### System Process Metrics

#### `process_virtual_memory_bytes`
- **Type**: Gauge
- **Description**: Virtual memory size in bytes

#### `process_resident_memory_bytes`
- **Type**: Gauge
- **Description**: Resident memory size in bytes

#### `process_start_time_seconds`
- **Type**: Gauge
- **Description**: Start time of the process since unix epoch in seconds

#### `process_cpu_seconds_total`
- **Type**: Counter
- **Description**: Total user and system CPU time spent in seconds

#### `process_open_fds`
- **Type**: Gauge
- **Description**: Number of open file descriptors

#### `process_max_fds`
- **Type**: Gauge
- **Description**: Maximum number of open file descriptors

### Flask Exporter Info

#### `flask_exporter_info`
- **Type**: Gauge
- **Description**: Information about the Prometheus Flask exporter
- **Labels**:
  - `version`: Version of prometheus-flask-exporter

## Usage Examples

### Curl

```bash
curl http://localhost:5000/metrics
```

### Python

```python
import requests

response = requests.get('http://localhost:5000/metrics')
print(response.text)
```

### Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'flask-app'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Grafana Dashboard

A pre-built Grafana dashboard is available in [grafana-dashboard.json](grafana-dashboard.json).

**Features:**
- Request rate, latency (p50/p95/p99), and error rate
- Memory and CPU usage monitoring
- HTTP status code distribution
- Python GC statistics
- File descriptor tracking
- Exception rate monitoring

**Quick Import:**
```bash
# Import via Grafana UI
1. Dashboards → Import
2. Upload grafana-dashboard.json
3. Select Prometheus datasource
```

See [GRAFANA.md](GRAFANA.md) for detailed setup instructions.

**Example Queries:**

### Request Rate
```promql
rate(flask_http_request_total[5m])
```

### Request Latency (p95)
```promql
histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))
```

### Error Rate
```promql
rate(flask_http_request_total{status=~"5.."}[5m])
```

### Memory Usage
```promql
process_resident_memory_bytes
```

## Kubernetes Integration

When deploying to Kubernetes, you can configure Prometheus to automatically discover and scrape your pods:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: flask-app
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "5000"
    prometheus.io/path: "/metrics"
spec:
  selector:
    app: flask-app
  ports:
    - port: 5000
      targetPort: 5000
```

## Security Considerations

- The `/metrics` endpoint is **publicly accessible** by design for Prometheus scraping
- Ensure your Prometheus server is properly secured
- Consider using network policies to restrict access to the metrics endpoint in production
- The endpoint does not expose sensitive data, only operational metrics

## Custom Metrics

To add custom metrics to your application, you can use the `metrics` object:

```python
from app import metrics

# Create a custom counter
my_counter = metrics.counter(
    'my_custom_counter',
    'Description of my counter',
    labels={'label_name': lambda: 'label_value'}
)

# Increment the counter
my_counter.inc()
```

See the [prometheus-flask-exporter documentation](https://github.com/rycus86/prometheus_flask_exporter) for more details.
