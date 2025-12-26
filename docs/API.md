<div align="center">
  <img src="assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# Waterfall Guardian API

> API endpoint documentation for the Guardian Authorization Service.

For the complete OpenAPI specification, see [openapi/openapi.yaml](openapi/openapi.yaml).

## Overview

The Guardian service is the **centralized authorization service** for the Waterfall Platform. It implements a comprehensive Role-Based Access Control (RBAC) system with fine-grained policies.

**Key Features:**

- **Access Control**: High-performance permission checks (`/check-access`) with caching
- **RBAC Management**: Full lifecycle management for Roles, Policies, and Permissions
- **User Assignments**: Manage user roles within companies and projects
- **Audit Trail**: Comprehensive access logs for security and compliance
- **System Bootstrap**: Automated initialization for new tenants

**Integrations:**

- **Identity Service**: Consumes user and company events
- **Redis**: Distributed caching for low-latency access checks
- **PostgreSQL**: Persistent storage for RBAC configuration and audit logs


## Authentication

| Method | Description | Usage |
|--------|-------------|-------|
| `JWTAuth` | JWT token via HTTP-only cookie containing `user_id`, `company_id`, `email` | Authenticated users |
| `InternalToken` | `X-Internal-Token` header | Inter-service communication (Identity, etc.) |

**JWT Claims:**

| Claim | Type | Description |
|-------|------|-------------|
| `user_id` | UUID | Unique user identifier |
| `company_id` | UUID | Company identifier (multi-tenant) |
| `email` | string | User email |
| `exp` | timestamp | Token expiration date |
| `iat` | timestamp | Token issued at date |

---

## Endpoints

### System

Monitoring and configuration endpoints (unauthenticated for health/ready/metrics).

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Liveness probe (Kubernetes) | None |
| `GET` | `/ready` | Readiness probe - checks PostgreSQL, Redis | None |
| `GET` | `/version` | Service version | JWT |
| `GET` | `/configuration` | Public service configuration | JWT |
| `GET` | `/metrics` | Prometheus metrics | None |

#### `GET /health`

Checks that the service is alive (process is running).

**Usage:** Kubernetes liveness probe

**Responses:**

| Code | Description |
|------|-------------|
| `200` | Service is alive |
| `429` | Too many requests |
| `500` | Internal server error |

**Example response:**
```json
{
  "status": "ok",
  "timestamp": "2025-12-22T10:30:00Z"
}
```

---

#### `GET /ready`

Checks that the service is ready to handle requests.

**Checks performed:**

1. PostgreSQL connection
2. Redis connection (if enabled)
3. Identity Service accessible (if enabled)

**Usage:** Kubernetes readiness probe

**Responses:**

| Code | Description |
|------|-------------|
| `200` | Service is ready |
| `429` | Too many requests |
| `500` | Internal server error |
| `503` | Service not ready (dependency failure) |

**Example response (success):**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "identity": "ok"
  },
  "timestamp": "2025-12-22T10:30:00Z"
}
```

**Example response (failure):**
```json
{
  "status": "not_ready",
  "checks": {
    "database": "error",
    "redis": "ok"
  },
  "timestamp": "2025-12-22T10:30:00Z"
}
```

---

#### `GET /version`

Returns the current version of the service.

**Responses:**

| Code | Description |
|------|-------------|
| `200` | Version information |
| `401` | Unauthorized |
| `403` | Forbidden |
| `500` | Internal server error |

**Example response:**
```json
{
  "service": "guardian-service",
  "version": "0.0.1",
  "build_date": "2025-12-22T10:30:00Z",
  "commit": "abc123d",
  "python_version": "3.11"
}
```

---

#### `GET /configuration`

Returns the active service configuration (without secrets).

**Security:** Never returns `JWT_SECRET_KEY`, `DATABASE_PASSWORD`, etc.

**Responses:**

| Code | Description |
|------|-------------|
| `200` | Active configuration |
| `401` | Unauthorized |
| `403` | Forbidden |
| `500` | Internal server error |

**Example response:**
```json
{
  "jwt_algorithm": "HS256",
  "jwt_access_token_expire_minutes": 30,
  "jwt_refresh_token_expire_days": 7,
  "enable_rate_limit": true,
  "rate_limit_requests": 100,
  "rate_limit_window": 60,
  "use_redis_service": true,
  "use_identity_service": true,
  "log_level": "INFO",
  "log_format": "json",
  "enable_access_logging": true,
  "access_log_retention_days": 365,
  "access_log_level": "info"
}
```

---

#### `GET /metrics`

Exposes metrics in Prometheus format.

**Standard Flask metrics** (via prometheus_flask_exporter):

- `flask_http_request_duration_seconds`: Request duration histogram
- `flask_http_request_total`: Total HTTP requests counter
- `flask_http_request_exceptions_total`: Total exceptions counter
- `flask_exporter_info`: Application info (version)

**Responses:**

| Code | Description |
|------|-------------|
| `200` | Prometheus metrics (text/plain) |
| `429` | Too many requests |
| `500` | Internal server error |

---

### Access Control

Permission checks and user permissions retrieval. These are the **most critical endpoints** of the system.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/check-access` | Check user access for a single operation |
| `POST` | `/batch-check-access` | Check multiple accesses in batch (max 50) |
| `GET` | `/users/{user_id}/permissions` | Get all user permissions |

#### `POST /check-access`

**Most critical endpoint** - called thousands of times per day. Checks if a user has permission to perform an operation on a resource.

**Performance:**
- Cache hit: < 5ms
- Cache miss: < 30ms
- TTL: 5 minutes (permissions), 1 hour (hierarchy)

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `service` | string | Yes | Service identifier (`storage`, `diagram`, `project`, etc.) |
| `resource_name` | string | Yes | Resource type identifier |
| `operation` | string | Yes | Operation (`LIST`, `CREATE`, `READ`, `UPDATE`, `DELETE`, `APPROVE`, `EXPORT`, `IMPORT`) |
| `context` | object | No | Additional context (`project_id`, `target_company_id`, `resource_id`) |

**Example request (simple):**
```json
{
  "service": "storage",
  "resource_name": "files",
  "operation": "LIST"
}
```

**Example request (with project context):**
```json
{
  "service": "diagram",
  "resource_name": "diagrams",
  "operation": "CREATE",
  "context": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Responses:**

| Code | Description |
|------|-------------|
| `200` | Verification result (granted or denied) |
| `400` | Invalid request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `500` | Internal server error |

**Example response (granted):**
```json
{
  "access_granted": true,
  "reason": "granted",
  "message": "User has permission storage:files:DELETE",
  "access_type": "direct",
  "matched_role": {
    "role_id": "850e8400-e29b-41d4-a716-446655440000",
    "role_name": "project_manager",
    "scope_type": "direct",
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "cache_hit": true
}
```

**Example response (denied):**
```json
{
  "access_granted": false,
  "reason": "no_permission",
  "message": "User does not have permission storage:files:DELETE",
  "cache_hit": false
}
```

**Denial reasons:**

| Reason | Description |
|--------|-------------|
| `no_permission` | User lacks the required permission |
| `no_matching_role` | No role matches the request context |
| `role_expired` | User's role has expired |
| `role_inactive` | User's role is deactivated |
| `project_mismatch` | Role doesn't apply to the requested project |
| `company_mismatch` | Role doesn't apply to the target company |

---

#### `POST /batch-check-access`

Checks up to **50 accesses** simultaneously. Typically used to show/hide action buttons in UI.

**Limit:** Maximum 50 checks per request. Returns 400 if exceeded.

**Example request:**
```json
{
  "checks": [
    {
      "service": "diagram",
      "resource_name": "diagrams",
      "operation": "CREATE",
      "context": { "project_id": "550e8400-e29b-41d4-a716-446655440000" }
    },
    {
      "service": "diagram",
      "resource_name": "diagrams",
      "operation": "DELETE",
      "context": { "project_id": "550e8400-e29b-41d4-a716-446655440000" }
    },
    {
      "service": "storage",
      "resource_name": "files",
      "operation": "CREATE"
    }
  ]
}
```

**Example response:**
```json
{
  "results": [
    {
      "access_granted": true,
      "reason": "granted",
      "message": "User has permission diagram:diagrams:CREATE",
      "cache_hit": true
    },
    {
      "access_granted": false,
      "reason": "no_permission",
      "message": "User does not have permission diagram:diagrams:DELETE",
      "cache_hit": true
    },
    {
      "access_granted": true,
      "reason": "granted",
      "message": "User has permission storage:files:CREATE",
      "cache_hit": true
    }
  ],
  "processing_time_ms": 12
}
```

---

#### `GET /users/{user_id}/permissions`

Lists all roles, policies, and permissions for a user. Useful for debugging or profile display.

**Parameters:**

| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `user_id` | path | UUID | Yes | User ID |
| `project_id` | query | UUID | No | Filter by project |

**Project Filtering:**
- Without `project_id`: company-wide permissions only
- With `project_id`: company-wide + specific project permissions

**Example response:**
```json
{
  "user_id": "12345678-90ab-cdef-1234-567890abcdef",
  "company_id": "98765432-10ab-cdef-1234-567890abcdef",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "roles": [
    {
      "role_id": "850e8400-e29b-41d4-a716-446655440000",
      "role_name": "project_manager",
      "display_name": "Project Manager",
      "scope_type": "direct",
      "project_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  ],
  "permissions": [
    "diagram:diagrams:CREATE",
    "diagram:diagrams:READ"
  ],
  "policies": [
    {
      "policy_id": "950e8400-e29b-41d4-a716-446655440000",
      "policy_name": "diagram_management",
      "permissions_count": 5
    }
  ]
}
```

---

### Roles

Role management (CRUD operations). Roles are isolated by company.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `HEAD` | `/roles` | Get roles count |
| `GET` | `/roles` | List all roles |
| `POST` | `/roles` | Create a new role |
| `GET` | `/roles/{role_id}` | Get a role by ID |
| `PATCH` | `/roles/{role_id}` | Update a role |
| `DELETE` | `/roles/{role_id}` | Delete a role |
| `GET` | `/roles/{role_id}/policies` | List role policies |
| `POST` | `/roles/{role_id}/policies` | Attach a policy to a role |
| `DELETE` | `/roles/{role_id}/policies/{policy_id}` | Detach a policy from a role |

#### `GET /roles`

List all roles for the company (automatically filtered by `company_id` from JWT).

**Query parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 50 | Items per page (max 100) |
| `is_active` | boolean | - | Filter by active status |

**Example response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "project_manager",
      "display_name": "Project Manager",
      "description": "Full project management",
      "company_id": "650e8400-e29b-41d4-a716-446655440000",
      "is_active": true,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-20T14:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 4,
    "total_pages": 1
  }
}
```

---

#### `POST /roles`

Creates a new role in the company. Reserved for admins.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Technical name (lowercase, underscores only: `^[a-z_]+$`) |
| `display_name` | string | Yes | Display name |
| `description` | string | No | Role description |

**Example request:**
```json
{
  "name": "senior_developer",
  "display_name": "Senior Developer",
  "description": "Experienced developer with extended permissions"
}
```

**Responses:**

| Code | Description |
|------|-------------|
| `201` | Role created |
| `400` | Invalid request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `409` | Conflict (name already exists) |
| `422` | Validation error |
| `500` | Internal server error |

---

#### `PATCH /roles/{role_id}`

Modifies role properties. The technical `name` cannot be modified.

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `display_name` | string | Display name |
| `description` | string | Role description |
| `is_active` | boolean | Enable/disable the role |

---

#### `DELETE /roles/{role_id}`

Deletes a role. **Fails if UserRoles still exist.**

> **Recommendation:** Disable (`is_active=false`) instead of deleting.

---

### Policies

Policy management and permission assignments. Policies group permissions together.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `HEAD` | `/policies` | Get policies count |
| `GET` | `/policies` | List all policies |
| `POST` | `/policies` | Create a new policy |
| `GET` | `/policies/{policy_id}` | Get a policy by ID |
| `PATCH` | `/policies/{policy_id}` | Update a policy |
| `DELETE` | `/policies/{policy_id}` | Delete a policy |
| `GET` | `/policies/{policy_id}/permissions` | List policy permissions |
| `POST` | `/policies/{policy_id}/permissions` | Attach a permission to a policy |
| `DELETE` | `/policies/{policy_id}/permissions/{permission_id}` | Remove a permission from a policy |

#### `POST /policies`

Creates a new policy in the company.

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Technical name (lowercase, underscores only) |
| `display_name` | string | Yes | Display name |
| `description` | string | No | Policy description |
| `priority` | integer | No | Priority for evaluation order (default: 0) |

**Example request:**
```json
{
  "name": "budget_approval",
  "display_name": "Budget Approval",
  "description": "Approve budgets < 10k€",
  "priority": 5
}
```

---

### Permissions

Permission definitions (read-only, seeded by system).

**Permission Format:** `service:resource:operation`
Example: `storage:files:DELETE`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/permissions` | List all permissions |
| `GET` | `/permissions/{permission_id}` | Get a permission by ID |
| `GET` | `/permissions/by-service` | List permissions grouped by service |

> **Note:** Permissions are read-only and seeded automatically at application startup.

#### `GET /permissions`

List all available permissions in the system.

**Query parameters:**

| Name | Type | Description |
|------|------|-------------|
| `service` | string | Filter by service (`storage`, `diagram`, etc.) |
| `resource_name` | string | Filter by resource type |
| `operation` | string | Filter by operation |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

**Available services:**

`identity`, `storage`, `project`, `diagram`, `requirement`, `system`, `work`, `budget`, `timesheet`, `analytics`, `basic-io`, `resources`

**Available operations:**

`LIST`, `CREATE`, `READ`, `UPDATE`, `DELETE`, `APPROVE`, `EXPORT`, `IMPORT`

---

#### `GET /permissions/by-service`

List all permissions grouped by service. Useful for building permission selection interfaces.

**Example response:**
```json
{
  "storage": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "storage:files:DELETE",
      "service": "storage",
      "resource_name": "files",
      "operation": "DELETE",
      "description": "Delete files"
    }
  ],
  "diagram": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "diagram:diagrams:CREATE",
      "service": "diagram",
      "resource_name": "diagrams",
      "operation": "CREATE",
      "description": "Create diagrams"
    }
  ]
}
```

---

### User Roles

User role assignments within companies and projects.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/{user_id}/roles` | List all roles for a user |
| `POST` | `/users/{user_id}/roles` | Assign a role to a user |
| `GET` | `/users/{user_id}/roles/{user_role_id}` | Get a UserRole by ID |
| `PATCH` | `/users/{user_id}/roles/{user_role_id}` | Update a UserRole |
| `DELETE` | `/users/{user_id}/roles/{user_role_id}` | Remove a role from a user |
| `GET` | `/roles/{role_id}/users` | List all users with a role |

#### `POST /users/{user_id}/roles`

Assigns a role to a user.

**Scopes:**
- `project_id=NULL`, `scope_type=direct`: Company-wide, exact company
- `project_id=NULL`, `scope_type=hierarchical`: Company + children
- `project_id=UUID`, `scope_type=direct`: Specific project only

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role_id` | UUID | Yes | Role to assign |
| `project_id` | UUID | No | Project scope (NULL = company-wide) |
| `scope_type` | string | Yes | `direct` or `hierarchical` |
| `expires_at` | datetime | No | Expiration date (for temporary roles) |

**Example request (company-wide):**
```json
{
  "role_id": "850e8400-e29b-41d4-a716-446655440000",
  "scope_type": "hierarchical"
}
```

**Example request (project-specific with expiration):**
```json
{
  "role_id": "850e8400-e29b-41d4-a716-446655440000",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "scope_type": "direct",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

---

### Audit

Access logs for security and compliance.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `HEAD` | `/access-logs` | Get access logs count |
| `GET` | `/access-logs` | Get access logs |
| `GET` | `/access-logs/{log_id}` | Get access log by ID |
| `DELETE` | `/access-logs` | Purge old access logs (GDPR) |
| `GET` | `/access-logs/statistics` | Aggregated audit statistics |

#### `GET /access-logs`

List access logs with advanced filtering. Retention: 90 days by default.

**Security:** Results are automatically filtered by user's `company_id` from JWT.

**Query parameters:**

| Name | Type | Description |
|------|------|-------------|
| `user_id` | UUID | Filter by user |
| `company_id` | UUID | Filter by company (super-admin only) |
| `project_id` | UUID | Filter by project |
| `service` | string | Filter by service |
| `resource_name` | string | Filter by resource type |
| `operation` | string | Filter by operation |
| `is_granted` | boolean | Filter by result (true=granted, false=denied) |
| `from_date` | datetime | Start date |
| `to_date` | datetime | End date |
| `page` | integer | Page number |
| `page_size` | integer | Items per page |

**Use Cases:**
- Security audit (denied access)
- Regulatory compliance
- Permission debugging
- Usage statistics

**Example response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "12345678-90ab-cdef-1234-567890abcdef",
      "company_id": "98765432-10ab-cdef-1234-567890abcdef",
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "service": "storage",
      "resource_name": "files",
      "resource_id": "file-12345678-90ab-cdef-1234-567890abcdef",
      "operation": "DELETE",
      "access_granted": true,
      "reason": "granted",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0",
      "context": { "file_size": 2048576 },
      "created_at": "2025-01-20T14:35:22Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 15234,
    "total_pages": 305
  }
}
```

---

#### `DELETE /access-logs`

Purge old access logs (GDPR compliance).

**Requirements:**
- `before` parameter is required
- Minimum retention: 30 days (cannot delete recent logs)
- Admin permission required

**Query parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `before` | datetime | Yes | Delete logs older than this date |
| `company_id` | UUID | No | Limit purge to specific company (admin only) |

**Example response:**
```json
{
  "deleted_count": 15234,
  "before_date": "2024-10-01T00:00:00Z"
}
```

---

#### `GET /access-logs/statistics`

Aggregated audit statistics for analysis and reporting.

**Metrics:**
- Total requests / success rate
- Distribution by service
- Distribution by operation
- Top 10 most active users

**Example response:**
```json
{
  "total_requests": 15234,
  "granted_requests": 14890,
  "denied_requests": 344,
  "success_rate": 97.74,
  "by_service": [
    { "service": "storage", "count": 8523, "granted": 8401, "denied": 122 },
    { "service": "diagram", "count": 4234, "granted": 4178, "denied": 56 }
  ],
  "by_operation": [
    { "operation": "READ", "count": 9234, "granted": 9190, "denied": 44 }
  ],
  "top_users": [
    { "user_id": "12345678-90ab-cdef-1234-567890abcdef", "count": 456, "granted": 450, "denied": 6 }
  ]
}
```

---

### Bootstrap

System initialization for new tenants.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/bootstrap` | System RBAC initialization |
| `POST` | `/companies/{company_id}/init-roles` | Initialize roles for a new company |

#### `POST /bootstrap`

**RBAC Initialization Endpoint** called by Identity during bootstrap.

**Service-to-Service Only** - Requires `X-Internal-Token` header.

**This endpoint:**
1. Validates `X-Internal-Token` against configured secret
2. Checks if Guardian is already initialized
3. Creates 4 standard Roles: `company_admin`, `project_manager`, `member`, `viewer`
4. Creates 4 standard Policies with appropriate permissions
5. Creates UserRole to assign `company_admin` to the first user
6. Marks Guardian as initialized

**Request body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_id` | UUID | Yes | First company created by Identity |
| `user_id` | UUID | Yes | First admin user created by Identity |

**Example response:**
```json
{
  "success": true,
  "company_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "f1e2d3c4-b5a6-9807-dcba-fe0987654321",
  "roles_created": 4,
  "policies_created": 4,
  "permissions_assigned": 47,
  "message": "Guardian RBAC initialized successfully for first company"
}
```

---

#### `POST /companies/{company_id}/init-roles`

**Automatic Endpoint** called by Identity during `POST /companies`.

**Difference from `/bootstrap`:**
- `/bootstrap`: 1st company + assign user admin
- `/companies/{id}/init-roles`: New companies + no automatic assignment

**Example response:**
```json
{
  "success": true,
  "company_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
  "roles_created": 4,
  "policies_created": 4,
  "roles": ["company_admin", "project_manager", "member", "viewer"]
}
```

---

## Error Responses

All endpoints follow a consistent error format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message"
}
```

**Standard HTTP Status Codes:**

| Code | Description |
|------|-------------|
| `400` | Bad Request - Invalid parameters |
| `401` | Unauthorized - Missing or invalid authentication |
| `403` | Forbidden - Insufficient permissions |
| `404` | Not Found - Resource doesn't exist |
| `409` | Conflict - Resource already exists |
| `422` | Unprocessable Entity - Validation error |
| `429` | Too Many Requests - Rate limit exceeded |
| `500` | Internal Server Error |
| `503` | Service Unavailable - Dependency failure |

**Validation Error Format (422):**
```json
{
  "message": "Validation error",
  "errors": {
    "name": ["This field is required"],
    "email": ["Invalid email format", "Email already exists"]
  }
}
```
