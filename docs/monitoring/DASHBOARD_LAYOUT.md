<div align="center">
  <img src="../assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Grafana Dashboard - Visual Layout

## Dashboard: WFP Flask Template - Application Metrics

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Time Range: Last 1 hour | Refresh: 5s | Variables: [Prometheus] [Job]      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Request Rate │  │ Latency p95  │  │  Error Rate  │  │Memory Usage  │  │
│  │              │  │              │  │              │  │              │  │
│  │   12.5 rps   │  │   0.25s      │  │    0.5%      │  │   450 MB     │  │
│  │              │  │              │  │              │  │              │  │
│  │    [GRAPH]   │  │   [GRAPH]    │  │   [GRAPH]    │  │   [GRAPH]    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │   Requests by Method             │  │   Requests by Status Code        ││
│  │                                  │  │                                  ││
│  │   Legend:                        │  │   Legend:                        ││
│  │   ■ GET   - 150 rps              │  │   ■ 200 - 145 rps (green)        ││
│  │   ■ POST  - 30 rps               │  │   ■ 404 - 3 rps   (yellow)       ││
│  │   ■ PUT   - 10 rps               │  │   ■ 500 - 2 rps   (red)          ││
│  │                                  │  │                                  ││
│  │   [TIME SERIES GRAPH]            │  │   [TIME SERIES GRAPH]            ││
│  │                                  │  │                                  ││
│  └──────────────────────────────────┘  └──────────────────────────────────┘│
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │   Request Latency Percentiles    │  │   Memory Usage                   ││
│  │                                  │  │                                  ││
│  │   Legend:        Mean    Max     │  │   Legend:        Mean    Max     ││
│  │   ■ p50 - 0.1s   0.12s   0.15s   │  │   ■ Resident - 450MB  500MB      ││
│  │   ■ p95 - 0.25s  0.28s   0.35s   │  │   ■ Virtual  - 2.5GB  2.7GB      ││
│  │   ■ p99 - 0.5s   0.55s   0.8s    │  │                                  ││
│  │                                  │  │                                  ││
│  │   [TIME SERIES GRAPH]            │  │   [TIME SERIES GRAPH]            ││
│  │                                  │  │                                  ││
│  └──────────────────────────────────┘  └──────────────────────────────────┘│
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │   CPU Usage                      │  │   Python GC Collections          ││
│  │                                  │  │                                  ││
│  │   Legend:        Mean    Max     │  │   Legend:        Mean    Last    ││
│  │   ■ CPU - 15%    18%     25%     │  │   ■ Gen 0 - 5/s   6/s    8/s     ││
│  │                                  │  │   ■ Gen 1 - 0.5/s 0.6/s  1/s     ││
│  │                                  │  │   ■ Gen 2 - 0.1/s 0.1/s  0.2/s   ││
│  │                                  │  │                                  ││
│  │   [TIME SERIES GRAPH]            │  │   [TIME SERIES GRAPH]            ││
│  │                                  │  │                                  ││
│  └──────────────────────────────────┘  └──────────────────────────────────┘│
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │   File Descriptors               │  │   Exception Rate                 ││
│  │                                  │  │                                  ││
│  │   Legend:        Mean    Last    │  │   Legend:        Mean    Last    ││
│  │   ■ Open - 16    25      16      │  │   ■ GET  - 0.01/s 0.02/s 0.01/s  ││
│  │   ■ Max  - 1024k 1024k   1024k   │  │   ■ POST - 0.05/s 0.06/s 0.04/s  ││
│  │                                  │  │                                  ││
│  │                                  │  │                                  ││
│  │   [TIME SERIES GRAPH]            │  │   [TIME SERIES GRAPH]            ││
│  │                                  │  │                                  ││
│  └──────────────────────────────────┘  └──────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Panel Details

### Row 1 - Key Performance Indicators (Stat Panels)

1. **Request Rate**
   - Type: Stat with sparkline
   - Color: Green (good) → Red (high load)
   - Threshold: Red > 80 req/s
   - Metric: `sum(rate(flask_http_request_total[5m]))`

2. **Request Latency (p95)**
   - Type: Stat with sparkline
   - Color: Green < 0.5s, Yellow < 1s, Red > 1s
   - Metric: `histogram_quantile(0.95, rate(...))`

3. **Error Rate (5xx)**
   - Type: Stat with sparkline
   - Color: Green < 1%, Yellow < 5%, Red > 5%
   - Metric: Error ratio calculation

4. **Memory Usage**
   - Type: Stat with sparkline
   - Color: Green < 500MB, Yellow < 1GB, Red > 1GB
   - Metric: `process_resident_memory_bytes`

### Row 2 - Traffic Analysis (Time Series)

5. **Requests by Method**
   - Shows: GET, POST, PUT, DELETE, etc.
   - Y-axis: Requests/second
   - Stacking: None (overlapping lines)

6. **Requests by Status Code**
   - Shows: 2xx (green), 4xx (yellow), 5xx (red)
   - Y-axis: Requests/second
   - Colors: Automatic based on status code range

### Row 3 - Performance Metrics (Time Series)

7. **Request Latency Percentiles**
   - Shows: p50, p95, p99
   - Y-axis: Seconds
   - Legend: Table with Mean and Max values

8. **Memory Usage Over Time**
   - Shows: Resident and Virtual memory
   - Y-axis: Bytes
   - Legend: Table with Mean and Max values

### Row 4 - System Resources (Time Series)

9. **CPU Usage**
   - Shows: CPU utilization percentage
   - Y-axis: Percent (0-100%)
   - Legend: Table with Mean and Max values

10. **Python GC Collections**
    - Shows: GC collections by generation (0, 1, 2)
    - Y-axis: Collections/second
    - Legend: Table with Mean and Last values

### Row 5 - System Health (Time Series)

11. **File Descriptors**
    - Shows: Open FDs vs Max FDs
    - Y-axis: Count
    - Helps detect FD leaks

12. **Exception Rate**
    - Shows: Exceptions by HTTP method
    - Y-axis: Exceptions/second
    - Helps identify problematic endpoints

## Color Coding

- **Green**: Healthy/Good state
- **Yellow**: Warning/Elevated state
- **Red**: Critical/Bad state
- **Blue**: Info/Neutral metric

## Legend Position

- Top 4 panels: No legend (single value)
- All time series: Bottom legend with statistics

## Refresh Rate

- Auto-refresh: Every 5 seconds
- Can be adjusted via top-right dropdown

## Time Range Selector

- Default: Last 1 hour
- Quick ranges: 5m, 15m, 30m, 1h, 3h, 6h, 12h, 24h, 7d
- Custom range available

## Dashboard Variables

- **DS_PROMETHEUS**: Datasource selector (top-left)
- **job**: Application job filter (top-left)
  - Auto-populated from Prometheus jobs
  - Default: wfp-flask-template
