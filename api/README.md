# API Service

FastAPI-based REST API for the wump dependency sponsorship discovery platform.

**For project overview and setup instructions, see the [top-level README](../README.md)**

### Prerequisites

For local development (running commands on your machine):
- **Python 3.14+**
- **uv** package manager

For containerized development:
- **Docker** & **Docker Compose** - See parent [README.md](../README.md)

---

## 📋 Service Structure

```
api/
├── src/app/
│   ├── api/         # API route handlers (TBD)
│   ├── core/        # Configuration & logging
│   ├── models/      # SQLAlchemy database models
│   ├── schemas/     # Pydantic request/response models (TBD)
│   ├── services/    # Business logic layer (TBD)
│   ├── providers/   # External data provider clients (TBD)
│   └── main.py      # FastAPI entry point
├── src/tests/       # Test suite
├── Dockerfile       # Container definition
├── pyproject.toml   # Dependencies & config
├── uv.lock          # Locked dependency versions
├── .env.example     # Config template
└── README.md        # This file
```

---

## 🚀 Running the Service

### Quick Start (Docker Compose)

From the repository root:

```bash
docker compose up -d         # Start all services
docker compose logs -f api   # View logs
docker compose down          # Stop services
```

See [QUICKSTART.md](../QUICKSTART.md) for detailed setup.

### Local Development

```bash
cd api
uv sync                      # Install dependencies
cp .env.example .env         # Configure environment
uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

Note: You'll need PostgreSQL 18 and Valkey 8.x running separately (or use Docker Compose to start just those services).

---

## 🛠️ Tech Stack & Configuration

### Core Technologies

- **Runtime**: Python 3.14
- **Web Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 18 (async via SQLAlchemy 2.0 + asyncpg)
- **Cache**: Valkey 8.x (Redis-compatible)
- **Validation**: Pydantic v2
- **Package Manager**: uv

### Development Tools

- **Testing**: pytest + pytest-asyncio
- **Type Checking**: mypy (strict mode)
- **Linting**: ruff

### Environment Configuration

See `.env.example` for all available variables. Key settings:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/wump
DATABASE_POOL_SIZE=20              # Connection pool size
DATABASE_MAX_OVERFLOW=10           # Max overflow connections
VALKEY_URL=redis://valkey:6379/0
LOG_LEVEL=INFO
```

### Database Connection Pool

The API uses SQLAlchemy 2.0 async engine with configurable connection pooling:

- **Pool Size**: Number of persistent connections (default: 20)
- **Max Overflow**: Additional temporary connections when pool is exhausted (default: 10)
- **Pool Pre-Ping**: Tests connections before using to prevent stale connections
- **Pool Recycle**: Recycles connections after 1 hour to handle database timeout policies

Configure these in your `.env`:
```env
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Database Migrations

The project uses **Alembic** for version-controlled database schema management.

#### Automatic Migrations (Docker Compose)

When running with Docker Compose, migrations automatically execute on container startup:

```bash
docker compose up -d          # Migrations run automatically
docker compose logs -f api    # See migration logs
```

#### Manual Migration Commands

For local development or advanced scenarios, you can run migrations manually:

```bash
cd api

# View migration history
uv run alembic history

# See current migration state
uv run alembic current

# Upgrade to latest migration
uv run alembic upgrade head

# Downgrade to previous migration
uv run alembic downgrade -1

# Downgrade to base (drop all tables)
uv run alembic downgrade base
```

In Docker containers:

```bash
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m alembic history
```

#### Creating New Migrations

When you modify SQLAlchemy models, create a new migration:

1. Update your models in `src/app/models/`
2. Create migration file (manual creation recommended):
   ```bash
   cd api
   uv run alembic revision -m "Describe your changes"
   ```
3. Edit the generated file in `alembic/versions/`
4. Test: `uv run alembic upgrade head`
5. Commit both the models and migration files

**Note**: Auto-generate (`--autogenerate`) is disabled due to async driver limitations. Always review generated migrations carefully and test thoroughly before committing.

#### Migration Files

All migrations are in `alembic/versions/` with naming: `{revision_id}_{description}.py`

Current migrations:
- `001_initial_schema.py` - Creates all base tables (organizations, packages, repositories, dependencies, api_keys)

### Valkey/Redis Connection & Caching

The API connects to **Valkey** (Redis-compatible cache) for performance optimization, rate limiting, and session management.

#### Configuration

Valkey connection is configured via environment variable:

```env
VALKEY_URL=redis://valkey:6379/0
```

In Docker Compose environments, the service name is `valkey`. For local development with a Redis instance on `localhost`:

```env
VALKEY_URL=redis://localhost:6379/0
```

#### Connection Pool

The Valkey client uses an async connection pool for efficient resource management:

- **Max Connections**: Maximum connections in the pool (default: 20)
- **Socket Timeout**: 5 seconds (default connection timeout)
- **Socket Keepalive**: Enabled to detect stale connections
- **Health Check Interval**: 30 seconds (automatic health checks)

#### Using Cache in Route Handlers

Inject the cache client as a dependency in your route handlers:

```python
from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from app.core.cache import get_cache

app = FastAPI()

@app.get("/cached-data")
async def get_cached_data(cache: Redis = Depends(get_cache)):
    """Get data from cache or compute if missing."""
    # Get from cache
    cached = await cache.get("data_key")
    if cached:
        return json.loads(cached)

    # Compute and cache
    data = {"key": "value"}
    await cache.set("data_key", json.dumps(data), ex=3600)  # 1 hour TTL
    return data
```

#### Cache Health Check

The `/health` endpoint includes Valkey connectivity status. See the [Health Check](#health-check) section for detailed response format and examples.

#### Testing Cache Connectivity

From within a running container:

```bash
# Test Valkey connection
docker compose exec api python -c "
import asyncio
from app.core.cache import check_cache_connection

result = asyncio.run(check_cache_connection())
print(f'Cache connected: {result}')
"

# Connect to Valkey CLI
docker compose exec valkey valkey-cli

# Inside valkey-cli
PING                 # Should return PONG
SET test-key value
GET test-key
FLUSHALL             # Clear all cache data
QUIT
```

### Health Check

The `/health` endpoint provides comprehensive system diagnostics including detailed status of service dependencies with response timing information.

#### Healthy Response (200 OK)

All services are operational:

```bash
curl http://localhost:8000/health

{
  "status": "healthy",
  "service": "wump-api",
  "version": "0.1.0",
  "timestamp": "2025-12-22T23:30:45.123Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.25,
      "timestamp": "2025-12-22T23:30:45.100Z"
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 2.10,
      "timestamp": "2025-12-22T23:30:45.120Z"
    }
  }
}
```

#### Degraded Response (200 OK with degraded status)

One or more services are unavailable:

```json
{
  "status": "degraded",
  "service": "wump-api",
  "version": "0.1.0",
  "timestamp": "2025-12-22T23:30:45.123Z",
  "checks": {
    "database": {
      "status": "unhealthy",
      "response_time_ms": 5001.50,
      "timestamp": "2025-12-22T23:30:45.100Z"
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 2.10,
      "timestamp": "2025-12-22T23:30:45.120Z"
    }
  }
}
```

#### Response Format

- **status**: `"healthy"` (all services OK) or `"degraded"` (any service down)
- **service**: API service identifier
- **version**: API version
- **timestamp**: ISO 8601 UTC timestamp when health check was performed
- **checks**: Object containing status of each service dependency
  - **database**: PostgreSQL connectivity status
    - **status**: `"healthy"` or `"unhealthy"`
    - **response_time_ms**: Time in milliseconds to check database connection
    - **timestamp**: ISO 8601 UTC timestamp of database check
  - **cache**: Valkey/Redis connectivity status
    - **status**: `"healthy"` or `"unhealthy"`
    - **response_time_ms**: Time in milliseconds to check cache connection
    - **timestamp**: ISO 8601 UTC timestamp of cache check

#### HTTP Status Code

The `/health` endpoint always returns **200 OK**. The `status` field in the response body indicates whether the service is `"healthy"` or `"degraded"`.

#### Kubernetes Liveness & Readiness Probes

Configure Kubernetes probes to use the health check endpoint:

```yaml
# liveness: Restart pod if health check fails
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

# readiness: Remove from service if health check indicates degraded
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

Check the `status` field in your monitoring system:
- If `status == "healthy"`: All dependencies operational
- If `status == "degraded"`: One or more dependencies unavailable - investigate logs and service status

#### Monitoring & Alerting

Use the health check endpoint with your monitoring system:

```bash
# Every 30 seconds, check API health
while true; do
  curl -s http://localhost:8000/health | jq '.status'
  sleep 30
done
```

Example alert conditions:
- Alert if `status` changes from `"healthy"` to `"degraded"`
- Alert if response_time_ms exceeds threshold (e.g., > 100ms for database)
- Alert if endpoint returns non-200 status code (indicates API crash)

---

## 📚 Related Documentation

- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System design and database schema
- [../DEVELOPMENT.md](../DEVELOPMENT.md) - Git workflow and code standards
- [../QUICKSTART.md](../QUICKSTART.md) - Project-level setup instructions

