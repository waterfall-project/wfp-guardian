<div align="center">
  <img src="../assets/waterfall_logo.svg" alt="Waterfall Logo" width="200"/>
</div>

# OpenAPI Specification

OpenAPI 3.0 specification for this Guardian service.

## Structure

```
openapi/
├── openapi.yaml           # Main specification file (complete spec)
├── .redocly.yaml          # Redocly CLI configuration
├── components/            # Reusable components (schemas, responses)
│   ├── schemas/          # Data models
│   └── responses/        # Reusable HTTP responses
├── paths/                 # Endpoint definitions
│   ├── system.yaml       # System endpoints (health, ready, version, config, metrics)
│   └── dummies.yaml      # CRUD endpoints (example - replace with your domain)
├── examples/              # Request/response examples
└── bundle/                # Generated bundled files
```

## Bundle Generation

**With Redocly CLI** (recommended):

```bash
# Install Redocly CLI
npm install -g @redocly/cli

# Generate bundle
redocly bundle openapi.yaml -o openapi-bundle.yaml
```

**With Swagger CLI** (alternative):

```bash
# Install Swagger CLI
npm install -g @apidevtools/swagger-cli

# Generate bundle
swagger-cli bundle openapi.yaml -o openapi-bundle.yaml -t yaml
```

## HTML Documentation Generation

**With Redocly CLI**:

```bash
# Generate interactive HTML (Redoc)
redocly build-docs openapi.yaml -o api-docs.html

# Or from bundle
redocly build-docs openapi-bundle.yaml -o api-docs.html
```

**With Docker** (without npm installation):

```bash
# Bundle
docker run --rm -v ${PWD}:/spec redocly/cli bundle openapi.yaml -o openapi-bundle.yaml

# HTML
docker run --rm -v ${PWD}:/spec redocly/cli build-docs openapi.yaml -o api-docs.html
```

## Validation

```bash
# Validate specification
redocly lint openapi.yaml

# With detailed report
redocly lint openapi.yaml --format stylish
```

## Preview

```bash
# Development server with hot-reload
redocly preview-docs openapi.yaml

# Open in browser: http://localhost:8080
```

## TypeScript Client Generation

**With OpenAPI Generator CLI**:

```bash
# Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate TypeScript client with Axios
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g typescript-axios \
  -o ../../frontend/src/api/client \
  --additional-properties=supportsES6=true,npmName=@yourorg/api-client,withSeparateModelsAndApi=true
```

**With openapi-typescript** (lightweight, types only):

```bash
# Install openapi-typescript
npm install -D openapi-typescript

# Generate TypeScript types
npx openapi-typescript openapi.yaml -o ../../frontend/src/api/types.ts
```

## API Endpoints

### System Endpoints (5)

Standard system endpoints for health, monitoring, and configuration:

- `GET /health` - Liveness probe (checks process is running)
- `GET /ready` - Readiness probe (checks dependencies: database, Redis, external services)
- `GET /version` - Service version information
- `GET /configuration` - Active configuration (without secrets)
- `GET /metrics` - Prometheus metrics

### Business Endpoints

Replace the example `/dummies` CRUD endpoints with your domain-specific resources:

- `GET /dummies` - List entities (example)
- `POST /dummies` - Create entity (example)
- `GET /dummies/{id}` - Get single entity (example)
- `PUT /dummies/{id}` - Update entity (full replacement) (example)
- `PATCH /dummies/{id}` - Partial update (example)
- `DELETE /dummies/{id}` - Delete entity (example)

## Authentication

This service uses JWT-based authentication with HTTP-only cookies.

### Public Endpoints

Endpoints that don't require authentication:
- `GET /health` - Health check
- `GET /ready` - Readiness check

### Protected Endpoints

All other endpoints require JWT authentication:
- Token passed via `access_token` HTTP-only cookie
- Or via `Authorization: Bearer <token>` header for non-browser clients

### JWT Token Structure

Tokens contain standard claims:
- `user_id` (UUID): Unique user identifier
- `company_id` (UUID): Company identifier (multi-tenant)
- `email` (string): User email
- `exp` (timestamp): Expiration date
- `iat` (timestamp): Issued at date

### Authorization with Guardian

RBAC authorization is delegated to the Guardian service:
1. Service validates JWT locally
2. Guardian checks permissions for each operation
3. Operations: LIST, CREATE, READ, UPDATE, DELETE

## Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `201` - Created
- `204` - No Content (successful deletion)
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `409` - Conflict (integrity constraint violation)
- `422` - Unprocessable Entity (validation error)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
- `503` - Service Unavailable (dependencies not ready)

All errors follow a consistent format with `message`, `path`, `method`, and `request_id` fields.

## Rate Limiting

Rate limiting is configurable per endpoint:
- Configurable via `ENABLE_RATE_LIMIT`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`
- Returns `429` status code when exceeded
- Response includes `X-RateLimit-*` headers

## Metrics

The service exposes Prometheus metrics via `/metrics`:

### Standard Flask Metrics
- `flask_http_request_duration_seconds` - Request duration histogram
- `flask_http_request_total` - Total HTTP requests counter
- `flask_http_request_exceptions_total` - Total exceptions counter

### Python Runtime Metrics
- `python_info` - Python version information
- `process_*` - CPU, memory, and file descriptor metrics

Add custom business metrics specific to your service as needed.

## Customization Guide

To adapt this template for your service:

1. **Update `openapi.yaml`**:
   - Change service title, description, and version
   - Update contact and license information
   - Modify server URLs

2. **Replace example endpoints**:
   - Remove or rename `paths/dummies.yaml`
   - Create your domain-specific path files
   - Update references in `openapi.yaml`

3. **Update schemas**:
   - Remove or modify `components/schemas/Dummy*.yaml`
   - Create schemas for your data models
   - Match schema fields with your SQLAlchemy models

4. **Update examples**:
   - Modify `examples/dummy_responses.json` for your domain
   - Update `examples/error_responses.json` if you have custom errors

5. **Update tags**:
   - Replace "Dummies" tag with your domain tags
   - Add descriptions for each tag

## Resources

- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.0)
- [Redocly CLI Documentation](https://redocly.com/docs/cli/)
- [OpenAPI Generator Documentation](https://openapi-generator.tech/)
- [JWT RFC 7519](https://tools.ietf.org/html/rfc7519)

## Related Documentation

For complete service documentation, see:
- [Main README](../../README.md) - Service overview
- [Architecture Documentation](../ARCHITECTURE.md) - System design and patterns
- [Configuration Guide](../CONFIGURATION.md) - Environment variables and settings
- [Operations Guide](../OPERATIONS.md) - Deployment and monitoring
