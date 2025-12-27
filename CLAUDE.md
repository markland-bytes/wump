# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**wump** (Who's Using My Package) is a dependency sponsorship discovery API that helps open-source maintainers find organizations using their packages for potential sponsorship opportunities.

- **Stack**: Python 3.14, FastAPI 0.115+, PostgreSQL 18, Valkey 8.x (Redis-compatible)
- **Architecture**: Layered architecture with repository pattern, async/await throughout
- **Phase**: Phase 1 (Foundation) - Database models, migrations, testing infrastructure complete

## Common Development Commands

### Running the Application

```bash
# Start all services (from repo root)
docker compose up -d

# View API logs
docker compose logs -f api

# Stop all services
docker compose down

# Local development (from api/ directory)
cd api
uv sync
uv run uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests (from api/ directory)
uv run pytest

# Run specific test file
uv run pytest src/tests/test_main.py

# Run specific test function
uv run pytest src/tests/test_main.py::test_health_check

# Run with coverage (80% minimum required)
uv run pytest --cov=src/app --cov-report=term-missing

# Run tests in Docker (mirrors CI environment)
docker compose run --rm test
```

### Code Quality

```bash
# Type checking (from api/ directory)
uv run mypy src/app/

# Linting
uv run ruff check src/app/

# Auto-fix linting issues
uv run ruff check --fix src/app/

# Format code
uv run ruff format src/app/
```

### Database Migrations

```bash
# View migration history (from api/ directory)
uv run alembic history

# Check current migration
uv run alembic current

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Create new migration (manual creation recommended)
uv run alembic revision -m "describe your changes"

# In Docker
docker compose exec api python -m alembic upgrade head
```

### Cache Operations

```bash
# Connect to Valkey CLI
docker compose exec valkey valkey-cli

# Inside valkey-cli
PING                 # Test connection
SET test-key value   # Set value
GET test-key         # Get value
FLUSHALL            # Clear all cache data
QUIT
```

## Architecture & Code Organization

### Layered Architecture

The API follows a strict layered architecture (see ARCHITECTURE.md for full details):

1. **HTTP Layer** (`app/main.py`): FastAPI application factory, route definitions, lifespan management
2. **API Layer** (`app/api/`): Route handlers, request/response models (TBD - Phase 2)
3. **Service Layer** (`app/services/`): Business logic, service composition (TBD - Phase 2)
4. **Repository Layer** (`app/repositories/`): Data access abstraction using repository pattern
5. **Model Layer** (`app/models/`): SQLAlchemy models with relationships
6. **Core Layer** (`app/core/`): Configuration, database, cache, logging, tracing, middleware

### Repository Pattern (Composition-Based)

The codebase uses a **composition-based repository pattern** (not inheritance):

```python
# app/repositories/organization.py
class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        # Inject BaseRepository as a dependency (composition)
        self._base_repo = BaseRepository(session, Organization)

    async def get(self, org_id: uuid.UUID) -> Optional[Organization]:
        return await self._base_repo.get(org_id)

    async def find_by_name(self, name: str) -> Optional[Organization]:
        # Custom queries go in the specific repository
        query = select(Organization).where(Organization.name == name)
        result = await self._base_repo._session.execute(query)
        return result.scalar_one_or_none()
```

**Key Points:**
- `BaseRepository[ModelType]` provides generic CRUD operations (create, get, update, delete, list, count)
- Entity-specific repositories compose `BaseRepository` and add custom queries
- All repositories use async/await with `AsyncSession`
- Soft delete is automatic via `deleted_at` column (models with `SoftDeleteMixin`)
- Pagination is built-in via `PaginationParams` and `PaginatedResult`

### Database Models

All models inherit from `TimestampMixin` and optionally `SoftDeleteMixin`:

```python
# app/models/base.py
class TimestampMixin:
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]]

# app/models/organization.py
class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID]
    name: Mapped[str]
    # ... relationships defined here
```

**Relationships:**
- Organizations have many Repositories (one-to-many)
- Repositories have many Dependencies (one-to-many)
- Dependencies link Packages to Repositories (many-to-many junction table)

### Configuration Management

All configuration is centralized in `app/core/config.py` using Pydantic settings:

```python
from app.core.config import settings

# Access configuration
settings.database_url
settings.valkey_url
settings.is_production
settings.log_level
```

Environment variables are loaded from `.env` (see `api/.env.example` for all options).

### Logging & Tracing

- **Logging**: `structlog` with JSON output (production) or console (development)
- **Tracing**: OpenTelemetry with automatic FastAPI, SQLAlchemy, and Redis instrumentation
- **Convention**: Use `get_logger(__name__)` in every module

```python
from app.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing request", user_id=user_id, action="update")
```

All database and cache operations are automatically traced via `@trace_database()` and `@trace_cache()` decorators.

### Testing Infrastructure

Tests use:
- **Database**: SQLite in-memory (via `conftest.py`, no PostgreSQL dependency in CI)
- **Cache**: FakeRedis in-memory (no Valkey dependency in CI)
- **Fixtures**: Shared fixtures in `conftest.py` (db_session, cache, async_client)
- **Factories**: Model factories in `factories.py` for test data creation

**Testing patterns:**

```python
# Use async test functions
@pytest.mark.asyncio
async def test_something(db_session: AsyncSession):
    # Use factories for test data
    org = await create_organization(db_session=db_session, name="test-org")

    # Test repository operations
    repo = OrganizationRepository(db_session)
    result = await repo.get(org.id)

    assert result is not None
    assert result.name == "test-org"
```

**Important**: Tests run in isolated transactions that are rolled back after each test. No need to manually clean up test data.

## Development Workflow

### Git Workflow

- **Main branch**: `main` (protected, always deployable)
- **Branch naming**: `<type>/<issue-number>-<description>` (e.g., `feature/8-testing-infrastructure`)
- **Commit format**: `<type>: <subject>` (e.g., `feat: add health check endpoint`)
- **Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`

See DEVELOPMENT.md for detailed Git workflow, commit conventions, and PR process.

### Creating a New Feature

1. Create feature branch: `git checkout -b feature/<issue>-<name>`
2. Make changes, run tests locally: `uv run pytest`
3. Check types and linting: `uv run mypy src/app/` and `uv run ruff check src/app/`
4. Commit with issue reference: `git commit -m "feat: description (#issue)"`
5. Push and create PR: `gh pr create --title "[Phase X] Title" --body "Closes #issue"`
6. Wait for CI to pass (tests, type checking, linting must all pass)
7. Merge PR: `gh pr merge --squash`

### Adding a New Database Model

1. Create model in `app/models/` inheriting from `Base, TimestampMixin, SoftDeleteMixin`
2. Define relationships using SQLAlchemy's `relationship()` and `back_populates`
3. Create manual migration: `uv run alembic revision -m "add model_name table"`
4. Edit migration file in `alembic/versions/` to add table and indexes
5. Test migration: `uv run alembic upgrade head`
6. Create repository in `app/repositories/` using composition pattern
7. Add model factory in `src/tests/factories.py`
8. Write tests in `src/tests/repositories/`

**Note**: Auto-generate (`--autogenerate`) is disabled for migrations. Always create migrations manually and review carefully.

### Adding a New Repository

Repositories use composition, not inheritance:

```python
# app/repositories/my_entity.py
from app.repositories.base import BaseRepository

class MyEntityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._base_repo = BaseRepository(session, MyEntity)

    # Expose base CRUD operations
    async def create(self, **kwargs: Any) -> MyEntity:
        return await self._base_repo.create(**kwargs)

    async def get(self, entity_id: uuid.UUID) -> Optional[MyEntity]:
        return await self._base_repo.get(entity_id)

    # Add custom queries
    async def find_by_slug(self, slug: str) -> Optional[MyEntity]:
        query = select(MyEntity).where(MyEntity.slug == slug)
        result = await self._base_repo._session.execute(query)
        return result.scalar_one_or_none()
```

### Testing Best Practices

- Always use async test functions with `@pytest.mark.asyncio`
- Use factories from `factories.py` instead of creating models manually
- Use descriptive test names: `test_create_organization_with_valid_data_succeeds`
- Add docstrings to tests explaining what they verify
- Coverage must be ≥80% (enforced in CI)
- Tests should be independent and not rely on execution order

## Project-Specific Patterns

### Error Handling

Use repository custom exceptions:

```python
from app.repositories.base import NotFoundError, ConflictError, RepositoryError

try:
    org = await repo.get_or_404(org_id)
except NotFoundError:
    raise HTTPException(status_code=404, detail="Organization not found")
except ConflictError:
    raise HTTPException(status_code=409, detail="Organization already exists")
except RepositoryError:
    raise HTTPException(status_code=500, detail="Database error")
```

### Async/Await Everywhere

All I/O operations are async:

```python
# Database
async with get_db() as session:
    repo = OrganizationRepository(session)
    org = await repo.get(org_id)

# Cache
cache = await get_cache()
value = await cache.get("key")
await cache.set("key", "value", ex=3600)

# HTTP requests (future)
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.github.com/...")
```

### Dependency Injection

Use FastAPI's dependency injection system:

```python
from fastapi import Depends
from app.core.database import get_db

@router.get("/organizations/{org_id}")
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    org = await repo.get_or_404(org_id)
    return org
```

### Soft Delete Convention

Models with `SoftDeleteMixin` are automatically filtered by `deleted_at IS NULL`:

```python
# Excludes soft-deleted entities (default)
org = await repo.get(org_id)

# Includes soft-deleted entities
org = await repo.get(org_id, include_deleted=True)

# Soft delete (sets deleted_at to current UTC timestamp)
deleted = await repo.delete(org_id, soft=True)

# Hard delete (permanently removes from database)
deleted = await repo.delete(org_id, soft=False)
```

## Important Configuration Files

- **pyproject.toml**: Python dependencies, tool configuration (ruff, mypy, pytest)
- **docker-compose.yml**: Service orchestration (api, db, valkey, jaeger, test)
- **.env.example**: Environment variable template with documentation
- **alembic.ini**: Alembic migration configuration
- **run_tests.py**: Test runner script (used in CI and Docker)

## Common Gotchas

1. **Migration Auto-generate is Disabled**: Always create migrations manually with `alembic revision -m "..."` and edit the generated file. Do not use `--autogenerate`.

2. **Tests Use In-Memory Databases**: CI tests run with SQLite in-memory and FakeRedis. No PostgreSQL or Valkey services are required for testing.

3. **Environment Variables**: Tests default to in-memory databases when `DATABASE_URL` and `VALKEY_URL` are not set. Check `conftest.py` for the fallback logic.

4. **Soft Delete Filter**: Repository operations automatically exclude soft-deleted entities unless `include_deleted=True` is specified.

5. **Async Context Managers**: Always use `async with get_db() as session:` or FastAPI's `Depends(get_db)` for database sessions.

6. **Type Hints Required**: All functions must have type hints. Mypy runs in strict mode in CI.

7. **OpenTelemetry**: Tracing is enabled by default in development. Set `OTEL_ENABLED=false` to disable. Jaeger UI is at http://localhost:16686.

8. **Health Check**: The `/health` endpoint always returns 200 OK. Check the `status` field in the response body for `"healthy"` or `"degraded"`.

## External APIs (Future Phases)

The architecture supports extensible data providers via a registry pattern:

- **Phase 2+**: GitHubProvider, LibrariesIoProvider
- **Provider Pattern**: All providers implement `DataProvider` interface (see ARCHITECTURE.md section 3.5)
- **Credentials**: Store in environment variables, never in code

## Deployment

- **Development**: Docker Compose (this repo)
- **Production** (future): AWS ECS with Fargate, OpenTofu for IaC
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`)

See ARCHITECTURE.md for detailed deployment architecture and infrastructure design.

## Documentation References

- **ARCHITECTURE.md**: System design, database schema, technology decisions
- **DEVELOPMENT.md**: Git workflow, commit conventions, PR process, testing guidelines
- **QUICKSTART.md**: 5-minute setup guide
- **api/README.md**: API service-specific documentation, database migrations, health checks

## Phase Roadmap

- **Phase 1 (Current)**: Foundation - Database models, migrations, basic API, testing infrastructure ✅
- **Phase 2**: Core API - CRUD endpoints, search, pagination (TBD)
- **Phase 3**: Background Jobs - Data ingestion from GitHub/Libraries.io (TBD)
- **Phase 4**: Infrastructure - OpenTofu, Railway/AWS deployment (TBD)
- **Phase 5**: Open Source Launch - Documentation, public release (TBD)
