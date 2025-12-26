<div align="center">
  <img src="assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Waterfall Guardian Documentation

Technical documentation for the Waterfall Guardian Authorization Service.

## 🎯 Overview

The **Guardian Service** is the centralized authorization engine for the Waterfall Platform:

- **Role-Based Access Control (RBAC)** - Hierarchical roles, policies, and permissions management
- **Multi-tenant Isolation** - Company-scoped authorization with strict data segregation
- **High-Performance Access Checks** - Sub-5ms latency with Redis caching
- **Comprehensive Audit Logging** - Full traceability of all authorization decisions
- **Flexible Scope Resolution** - Direct and hierarchical permission inheritance

## 📚 Main Documentation

### Guardian Service
- [**Architecture**](ARCHITECTURE.md) - Key architecture decisions and rationale
- [**Configuration**](CONFIGURATION.md) - Environment variables and configuration
- [**API Reference**](API.md) - REST endpoints, requests/responses, authentication
- [**Data Models**](MODELS.md) - Entities, relationships, database schema
- [**Workflows**](WORKFLOWS.md) - Authorization process sequence diagrams
- [**Monitoring**](MONITORING.md) - Prometheus metrics, alerts and Grafana dashboards

### Development Standards
- [**Coding Standards**](CODING_STANDARDS.md) - Code style, conventions and best practices

### OpenAPI Specification
- [**OpenAPI Specifications**](openapi/) - REST documentation and JSON schemas

### Monitoring & Observability
- [**Monitoring Guide**](monitoring/MONITORING.md) - Monitoring stack configuration
- [**Metrics Documentation**](monitoring/METRICS.md) - Prometheus metrics reference
- [**Grafana Setup**](monitoring/GRAFANA.md) - Dashboard configuration

---

## 🔗 Relationships with Other Services

```mermaid
flowchart LR
    subgraph External
        CL[Client Applications]
        AD[Admin Dashboard]
    end

    subgraph Waterfall Platform
        OTHER[Other Services]
        GD[Guardian Service]
        ID[Identity Service]
    end

    CL -->|API calls| OTHER
    AD -->|RBAC management| GD

    OTHER -->|Check permissions| GD
    ID -->|JWT tokens| OTHER
    ID -->|JWT tokens| AD
    GD -->|Validate user & company hierarchy| ID
```

| Service | Interaction |
|---------|-------------|
| **Identity** | Provides JWT tokens with `user_id` and `company_id` to all services and dashboards. Guardian validates user existence and retrieves company hierarchy for hierarchical scope resolution. |
| **Other Services** | Receive client requests, extract JWT claims, then call Guardian's `/access/check` endpoint to verify user permissions before processing. |
| **Admin Dashboard** | Directly calls Guardian's management API to configure roles, policies, and permissions. |

---

## 🏗️ Core Concepts

### RBAC Hierarchy

```mermaid
flowchart TB
    U[User] -->|assigned to| R[Role]
    R -->|contains| P[Policy]
    P -->|grants| PERM[Permission]
    PERM -->|allows| A[Action on Resource]

    style U fill:#e3f2fd
    style R fill:#fff3e0
    style P fill:#e8f5e9
    style PERM fill:#fce4ec
    style A fill:#f3e5f5
```

### Permission Check Flow

```mermaid
sequenceDiagram
    participant S as Service
    participant G as Guardian
    participant C as Cache
    participant DB as Database

    S->>G: POST /access/check
    G->>C: Get cached permissions
    alt Cache Hit
        C-->>G: Permissions
    else Cache Miss
        G->>DB: Query permissions
        DB-->>G: Permissions
        G->>C: Cache permissions
    end
    G-->>S: {granted: true/false}
```

---

## 🧪 Tests

- [Unit Tests](../tests/unit/README.md)
- [Integration Tests](../tests/integration/README.md)

## 🚀 Quick Links

- [Main README](../README.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [License](../LICENSE.md)
