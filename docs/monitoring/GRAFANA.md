<div align="center">
  <img src="../assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Grafana Dashboard Setup Guide

## Overview

This guide explains how to import and configure the Grafana dashboard for monitoring your WFP Flask Template application.

## Dashboard Features

The dashboard includes 12 panels organized to provide comprehensive monitoring:

### Top Row - Key Metrics (4 Stat Panels)
1. **Request Rate** - Requests per second
2. **Request Latency (p95)** - 95th percentile response time
3. **Error Rate (5xx)** - Percentage of server errors
4. **Memory Usage** - Current memory consumption

### Time Series Panels
5. **Requests by Method** - HTTP methods (GET, POST, etc.)
6. **Requests by Status Code** - 2xx (green), 4xx (yellow), 5xx (red)
7. **Request Latency Percentiles** - p50, p95, p99 latency trends
8. **Memory Usage Over Time** - Resident and virtual memory
9. **CPU Usage** - CPU utilization percentage
10. **Python GC Collections** - Garbage collection by generation
11. **File Descriptors** - Open vs maximum file descriptors
12. **Exception Rate** - Application exceptions per second

## Prerequisites

1. **Prometheus** configured to scrape your Flask app (see `prometheus.yml.example`)
2. **Grafana** instance (v10.0+)
3. **Prometheus datasource** configured in Grafana

## Import Dashboard

### Method 1: Import JSON File

1. Open Grafana web interface
2. Navigate to **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select `docs/monitoring/grafana-dashboard.json`
5. Select your Prometheus datasource
6. Click **Import**

### Method 2: Import via Dashboard ID (if published)

1. Open Grafana web interface
2. Navigate to **Dashboards** → **Import**
3. Enter dashboard ID or JSON
4. Paste the contents of `grafana-dashboard.json`
5. Click **Load**
6. Select your Prometheus datasource
7. Click **Import**

### Method 3: Using Grafana API

```bash
# Set your Grafana credentials
GRAFANA_URL="http://localhost:3000"
GRAFANA_API_KEY="your-api-key"

# Import the dashboard
curl -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @docs/monitoring/grafana-dashboard.json
```

## Configuration

### Datasource Setup

The dashboard uses a template variable `${DS_PROMETHEUS}` for the datasource:

1. After import, select your Prometheus datasource from the dropdown
2. The dashboard will automatically query available jobs
3. Select your Flask app job from the **Job** dropdown

### Variables

The dashboard includes two template variables:

#### DS_PROMETHEUS
- **Type**: Datasource
- **Query**: prometheus
- **Description**: Prometheus datasource to use

#### job
- **Type**: Query
- **Query**: `label_values(flask_http_request_total, job)`
- **Description**: Select the Flask application job to monitor
- **Default**: `wfp-flask-template`

### Time Range

- **Default**: Last 1 hour
- **Refresh**: Every 5 seconds
- Adjust as needed via the time picker in the top-right corner

## Panel Queries

### Request Rate
```promql
sum(rate(flask_http_request_total{job="$job"}[5m]))
```

### Request Latency (p95)
```promql
histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket{job="$job"}[5m])) by (le))
```

### Error Rate
```promql
sum(rate(flask_http_request_total{job="$job",status=~"5.."}[5m])) / sum(rate(flask_http_request_total{job="$job"}[5m]))
```

### Memory Usage
```promql
process_resident_memory_bytes{job="$job"}
```

## Customization

### Modify Thresholds

Each stat panel has configurable thresholds:

1. Click panel title → **Edit**
2. Navigate to **Thresholds** in the right panel
3. Adjust values and colors:
   - **Request Latency**: Green < 0.5s, Yellow < 1s, Red > 1s
   - **Error Rate**: Green < 1%, Yellow < 5%, Red > 5%
   - **Memory**: Green < 500MB, Yellow < 1GB, Red > 1GB

### Add Custom Panels

Example custom panel for endpoint-specific latency:

```promql
histogram_quantile(0.95,
  sum(rate(flask_http_request_duration_seconds_bucket{
    job="$job",
    endpoint="/api/users"
  }[5m])) by (le)
)
```

### Alert Configuration

To add alerts:

1. Edit any panel
2. Go to **Alert** tab
3. Click **Create alert rule from this panel**
4. Configure conditions (e.g., latency > 1s for 5m)
5. Add notification channels

Example alert condition:
```
WHEN avg() OF query(A, 5m, now) IS ABOVE 1
```

## Kubernetes Deployment

For Kubernetes deployments with the dashboard:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  wfp-flask-template.json: |
    # Paste grafana-dashboard.json content here
```

Grafana sidecar will automatically detect and load the dashboard.

## Troubleshooting

### No Data Displayed

1. **Check Prometheus datasource**:
   ```bash
   # Test Prometheus connection
   curl http://prometheus:9090/api/v1/query?query=up
   ```

2. **Verify metrics endpoint**:
   ```bash
   # Check Flask app exposes metrics
   curl http://flask-app:5000/metrics
   ```

3. **Check Prometheus targets**:
   - Open Prometheus UI: `http://prometheus:9090/targets`
   - Ensure Flask app target is UP

4. **Verify job label**:
   - Metrics must have `job` label matching the dashboard variable
   - Check in Prometheus: `flask_http_request_total{job="wfp-flask-template"}`

### Dashboard Shows "No Data"

1. **Check time range**: Ensure there's data in the selected time window
2. **Refresh dashboard**: Click refresh icon or Ctrl+R
3. **Check query syntax**: View panel JSON for PromQL errors

### Variables Not Populated

1. Ensure Prometheus datasource is selected
2. Check that `flask_http_request_total` metric exists
3. Verify job label is present in metrics

## Performance Tips

### For Large Deployments

1. **Adjust scrape interval**: Reduce from 15s to 30s or 60s
2. **Use recording rules** in Prometheus:
   ```yaml
   groups:
     - name: flask_app
       interval: 30s
       rules:
         - record: job:flask_http_request_rate:5m
           expr: sum(rate(flask_http_request_total[5m])) by (job)
   ```

3. **Limit time range**: Use shorter time windows (e.g., 6h instead of 24h)
4. **Enable query caching** in Grafana

### Dashboard Export

To share or version control your customized dashboard:

```bash
# Export via API
curl -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  "${GRAFANA_URL}/api/dashboards/uid/wfp-flask-template" \
  | jq '.dashboard' > my-custom-dashboard.json
```

## Related Documentation

- [Prometheus Configuration](prometheus.yml.example)
- [Metrics Documentation](METRICS.md)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## Support

For issues or questions:
- Check Grafana logs: `docker logs grafana`
- Check Prometheus logs: `docker logs prometheus`
- Review Flask app logs for `/metrics` endpoint access
