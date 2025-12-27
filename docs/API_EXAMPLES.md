# API Examples

This document provides practical examples for interacting with the wump API using `curl` and other HTTP clients.

## Table of Contents

- [Health Check](#health-check)
- [Interactive API Documentation](#interactive-api-documentation)
- [Future Endpoints](#future-endpoints)

---

## Health Check

The health check endpoint provides comprehensive system diagnostics.

### Endpoint

```
GET /health
```

### Example Request

```bash
curl -X GET http://localhost:8000/health
```

### Example Response (Healthy)

```json
{
  "status": "healthy",
  "service": "wump-api",
  "version": "0.1.0",
  "timestamp": "2025-12-26T22:30:45.123Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.25,
      "timestamp": "2025-12-26T22:30:45.100Z"
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 2.10,
      "timestamp": "2025-12-26T22:30:45.120Z"
    }
  }
}
```

### Example Response (Degraded)

When one or more services are unavailable:

```json
{
  "status": "degraded",
  "service": "wump-api",
  "version": "0.1.0",
  "timestamp": "2025-12-26T22:30:45.123Z",
  "checks": {
    "database": {
      "status": "unhealthy",
      "response_time_ms": 5001.50,
      "timestamp": "2025-12-26T22:30:45.100Z"
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 2.10,
      "timestamp": "2025-12-26T22:30:45.120Z"
    }
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall system status: `"healthy"` or `"degraded"` |
| `service` | string | API service identifier |
| `version` | string | API version |
| `timestamp` | string | ISO 8601 UTC timestamp of health check |
| `checks.database.status` | string | Database connection status |
| `checks.database.response_time_ms` | number | Database health check latency |
| `checks.cache.status` | string | Cache connection status |
| `checks.cache.response_time_ms` | number | Cache health check latency |

### Use Cases

**Kubernetes Liveness Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

**Monitoring Script:**
```bash
#!/bin/bash
while true; do
  STATUS=$(curl -s http://localhost:8000/health | jq -r '.status')
  if [ "$STATUS" != "healthy" ]; then
    echo "WARNING: API is $STATUS"
    # Send alert
  fi
  sleep 30
done
```

---

## Interactive API Documentation

wump provides interactive API documentation using Swagger UI and ReDoc.

### Swagger UI

**URL:** http://localhost:8000/docs

Features:
- Try out endpoints directly in the browser
- View request/response schemas
- See example values
- Test authentication

### ReDoc

**URL:** http://localhost:8000/redoc

Features:
- Clean, responsive documentation
- Search functionality
- Code samples in multiple languages
- Download OpenAPI spec

### OpenAPI Specification

**URL:** http://localhost:8000/openapi.json

Download the raw OpenAPI 3.0 specification for use with code generators, testing tools, or API clients.

```bash
# Download OpenAPI spec
curl -X GET http://localhost:8000/openapi.json > openapi.json

# Generate Python client (example)
openapi-generator-cli generate \
  -i openapi.json \
  -g python \
  -o ./client
```

---

## Future Endpoints

The following endpoints are planned for Phase 2. Examples are provided for reference.

### Package Endpoints

#### Get Package Dependents

**Coming in Phase 2**

```bash
GET /api/v1/packages/{ecosystem}/{name}/dependents
```

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/v1/packages/npm/react/dependents
```

**Example Response:**
```json
{
  "package": {
    "name": "react",
    "ecosystem": "npm",
    "description": "A JavaScript library for building user interfaces",
    "latest_version": "18.3.1"
  },
  "dependents": [
    {
      "organization": {
        "name": "vercel",
        "github_url": "https://github.com/vercel",
        "sponsorship_url": null
      },
      "repositories": [
        {
          "name": "next.js",
          "stars": 128000,
          "github_url": "https://github.com/vercel/next.js"
        }
      ],
      "total_repositories": 2
    },
    {
      "organization": {
        "name": "shopify",
        "github_url": "https://github.com/shopify",
        "sponsorship_url": "https://github.com/sponsors/shopify"
      },
      "repositories": [
        {
          "name": "polaris",
          "stars": 5700,
          "github_url": "https://github.com/Shopify/polaris"
        }
      ],
      "total_repositories": 2
    }
  ],
  "total_organizations": 2,
  "total_repositories": 4
}
```

#### List Packages

**Coming in Phase 2**

```bash
GET /api/v1/packages?ecosystem=npm&limit=10&offset=0
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/packages?ecosystem=npm&limit=10"
```

**Example Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "react",
      "ecosystem": "npm",
      "description": "A JavaScript library for building user interfaces",
      "latest_version": "18.3.1",
      "dependent_count": 4
    }
  ],
  "total": 8,
  "offset": 0,
  "limit": 10,
  "has_next": false,
  "has_prev": false
}
```

### Organization Endpoints

#### Get Organization Details

**Coming in Phase 2**

```bash
GET /api/v1/organizations/{org_name}
```

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/v1/organizations/vercel
```

**Example Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "vercel",
  "github_url": "https://github.com/vercel",
  "website_url": "https://vercel.com",
  "description": "Develop. Preview. Ship.",
  "sponsorship_url": null,
  "total_repositories": 2,
  "total_stars": 158500,
  "repositories": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "next.js",
      "github_url": "https://github.com/vercel/next.js",
      "stars": 128000,
      "primary_language": "TypeScript",
      "is_archived": false
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "name": "swr",
      "github_url": "https://github.com/vercel/swr",
      "stars": 30500,
      "primary_language": "TypeScript",
      "is_archived": false
    }
  ],
  "created_at": "2025-12-26T22:00:00.000Z",
  "updated_at": "2025-12-26T22:30:00.000Z"
}
```

#### List Organizations

**Coming in Phase 2**

```bash
GET /api/v1/organizations?limit=10&offset=0&sort=total_stars
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/organizations?sort=total_stars&limit=5"
```

### Search Endpoints

#### Search Packages

**Coming in Phase 2**

```bash
GET /api/v1/search/packages?q=react&ecosystem=npm
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/search/packages?q=react"
```

#### Search Organizations

**Coming in Phase 2**

```bash
GET /api/v1/search/organizations?q=vercel
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/search/organizations?q=vercel"
```

---

## Authentication

**Coming in Phase 2**

Future endpoints will require API key authentication:

```bash
curl -X GET \
  -H "X-API-Key: your_api_key_here" \
  http://localhost:8000/api/v1/packages/npm/react/dependents
```

---

## Error Responses

Standard error response format:

```json
{
  "detail": "Error message here"
}
```

### Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Database/cache unavailable |

---

## Rate Limiting

**Coming in Phase 2**

Rate limits will be enforced based on API key tier:

| Tier | Requests/Minute |
|------|-----------------|
| Free | 60 |
| Standard | 600 |
| Premium | 6000 |

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

---

## Monitoring with Jaeger

wump includes OpenTelemetry tracing with Jaeger UI for request monitoring.

**Jaeger UI:** http://localhost:16686

Features:
- View distributed traces for API requests
- Analyze database query performance
- Monitor cache hit/miss rates
- Debug slow requests

---

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Jaeger Tracing**: http://localhost:16686
- **Architecture**: [../docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Development Guide**: [../docs/DEVELOPMENT.md](DEVELOPMENT.md)
