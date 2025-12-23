<div align="center">
  <img src="../assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Monitoring Stack Setup

This directory contains configurations for running a complete monitoring stack with Prometheus and Grafana.

## Quick Start

```bash
# From the project root
cd docs
docker-compose -f docker-compose.monitoring.yml up -d
```

Access the services:
- **Flask App**: http://localhost:5000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## What's Included

### Services

1. **Flask App** (port 5000)
   - Your application with `/metrics` endpoint
   - Auto-reloads on code changes (development mode)
   - SQLite database

2. **Prometheus** (port 9090)
   - Scrapes metrics from Flask app every 15s
   - Stores time-series data
   - PromQL query interface

3. **Grafana** (port 3000)
   - Pre-configured Prometheus datasource
   - Auto-loaded dashboard
   - Default credentials: admin/admin

### Volumes

- `flask-data`: Application database
- `prometheus-data`: Metrics storage
- `grafana-data`: Grafana configuration and dashboards

## Configuration Files

```
docs/
├── docker-compose.monitoring.yml    # Docker Compose stack
├── prometheus.yml.example           # Prometheus scrape config
├── grafana-dashboard.json           # Pre-built dashboard
├── GRAFANA.md                       # Dashboard documentation
└── grafana-provisioning/
    ├── datasources/
    │   └── prometheus.yml          # Auto-configure Prometheus
    └── dashboards/
        └── dashboard-provider.yml  # Auto-load dashboards
```

## Usage

### Start Stack

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.monitoring.yml logs -f

# Specific service
docker-compose -f docker-compose.monitoring.yml logs -f flask-app
docker-compose -f docker-compose.monitoring.yml logs -f prometheus
docker-compose -f docker-compose.monitoring.yml logs -f grafana
```

### Stop Stack

```bash
docker-compose -f docker-compose.monitoring.yml down
```

### Clean Everything (including data)

```bash
docker-compose -f docker-compose.monitoring.yml down -v
```

## Accessing Services

### Flask Application

```bash
# Health check
curl http://localhost:5000/health

# Readiness check
curl http://localhost:5000/ready

# Metrics
curl http://localhost:5000/metrics

# Version info (requires auth)
curl http://localhost:5000/version
```

### Prometheus

1. Open http://localhost:9090
2. Go to **Status** → **Targets** to verify Flask app is scraped
3. Try queries:
   ```promql
   flask_http_request_total
   rate(flask_http_request_total[5m])
   histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))
   ```

### Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin`
3. Change password when prompted (optional for testing)
4. Dashboard is auto-loaded: **WFP Flask Template - Application Metrics**

## Import Custom Dashboard

If the dashboard doesn't auto-load:

1. Go to **Dashboards** → **Import**
2. Click **Upload JSON file**
3. Select `grafana-dashboard.json`
4. Click **Import**

## Generate Traffic

To populate metrics:

```bash
# Simple load test
for i in {1..100}; do
  curl http://localhost:5000/health
  curl http://localhost:5000/ready
  sleep 0.1
done

# Using Apache Bench
ab -n 1000 -c 10 http://localhost:5000/health

# Using hey
hey -n 1000 -c 10 http://localhost:5000/health
```

## Troubleshooting

### Flask App Not Starting

```bash
# Check logs
docker-compose -f docker-compose.monitoring.yml logs flask-app

# Common issues:
# - Port 5000 already in use: Stop other services using port 5000
# - Build errors: Rebuild with --no-cache
docker-compose -f docker-compose.monitoring.yml build --no-cache flask-app
```

### Prometheus Not Scraping

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Flask metrics endpoint from Prometheus container
docker-compose -f docker-compose.monitoring.yml exec prometheus \
  wget -O- http://flask-app:5000/metrics
```

### Grafana Dashboard Shows No Data

1. **Check Prometheus datasource**:
   - Grafana → Configuration → Data sources
   - Click "Prometheus"
   - Click "Save & test" - should show green checkmark

2. **Check metrics exist**:
   - Open Prometheus: http://localhost:9090
   - Run query: `flask_http_request_total`
   - Should show results

3. **Check time range**:
   - Grafana shows last 1 hour by default
   - Generate some traffic first
   - Adjust time range if needed

### Permission Issues

```bash
# Fix Grafana permissions
chmod -R 777 docs/monitoring/grafana-provisioning/

# Recreate volumes
docker-compose -f docker-compose.monitoring.yml down -v
docker-compose -f docker-compose.monitoring.yml up -d
```

## Production Considerations

This setup is for **development/testing only**. For production:

1. **Security**:
   - Change Grafana admin password
   - Use secrets management for credentials
   - Enable HTTPS/TLS
   - Restrict network access

2. **Storage**:
   - Configure Prometheus retention: `--storage.tsdb.retention.time=30d`
   - Use persistent volumes
   - Configure backup strategies

3. **Scaling**:
   - Use Prometheus federation for multiple instances
   - Consider Thanos or Cortex for long-term storage
   - Deploy Grafana with high availability

4. **Configuration**:
   - Use environment-specific configs
   - Externalize configuration via ConfigMaps (Kubernetes)
   - Use service discovery instead of static targets

## Next Steps

1. **Customize Dashboard**: Edit panels to match your needs
2. **Add Alerts**: Configure Grafana alerts for critical metrics
3. **Add More Metrics**: Instrument your application code
4. **Explore PromQL**: Learn advanced queries
5. **Scale Up**: Deploy to Kubernetes with proper monitoring

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)

## Support

For issues with the monitoring stack:
- Check Docker logs
- Verify network connectivity between containers
- Ensure volumes have correct permissions
- Review Prometheus and Grafana documentation
