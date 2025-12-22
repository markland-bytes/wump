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

### Health Check

The `/health` endpoint includes database connectivity status:

```bash
curl http://localhost:8000/health

{
  "status": "healthy",
  "service": "wump-api",
  "version": "0.1.0",
  "database": "healthy"
}
```

If the database is unavailable:
```json
{
  "status": "degraded",
  "service": "wump-api",
  "version": "0.1.0",
  "database": "unhealthy"
}
```

Use this endpoint for monitoring and alerting. If `database` is `"unhealthy"`, the API cannot fulfill requests requiring database access.

---

## 📚 Related Documentation

- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System design and database schema
- [../DEVELOPMENT.md](../DEVELOPMENT.md) - Git workflow and code standards
- [../QUICKSTART.md](../QUICKSTART.md) - Project-level setup instructions

