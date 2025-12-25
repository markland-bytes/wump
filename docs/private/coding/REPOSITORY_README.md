# Repository Pattern Implementation Guide

This guide explains the repository pattern implementation in the wump API, including design decisions, usage examples, and best practices.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Pattern: Composition](#architecture-pattern-composition)
3. [BaseRepository](#baserepository)
4. [Features](#features)
5. [Usage Examples](#usage-examples)
6. [Testing](#testing)
7. [Best Practices](#best-practices)

## Overview

The repository pattern provides a clean abstraction layer between the business logic and data access layers. Our implementation uses:

- **Generic type-safe CRUD operations** with Python generics (`TypeVar[ModelType]`)
- **Composition over inheritance** for better separation of concerns
- **Soft delete support** via `SoftDeleteMixin`
- **Pagination** with validation and metadata
- **Transaction management** (commit/rollback)
- **OpenTelemetry tracing** for observability
- **Comprehensive error handling** with custom exceptions

## Architecture Pattern: Composition

We use **composition** instead of inheritance for repository implementations.

### Why Composition?

```python
# ❌ Inheritance (traditional approach)
class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self, db: AsyncSession):
        super().__init__(Organization, db)
    
    # Custom methods...

# ✅ Composition (our approach)
class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self._base = BaseRepository(Organization, db)
    
    async def create(self, data: dict) -> Organization:
        return await self._base.create(data)
```

### Benefits of Composition:

1. **Explicit delegation**: No magic `__getattr__`, clear intent
2. **Better testability**: Easy to mock `_base` repository
3. **Separation of concerns**: Domain logic separate from CRUD
4. **Flexible composition**: Can compose multiple concerns (caching, logging)
5. **FastAPI alignment**: Works naturally with dependency injection

### Trade-offs:

- **More boilerplate**: Must explicitly delegate methods
- **No automatic inheritance**: Can't add methods to base and use immediately

## BaseRepository

The `BaseRepository` is a generic class that provides type-safe CRUD operations.

### Generic Type Safety

```python
from typing import TypeVar, Generic
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db
```

This provides full type safety:
- `await repo.create(...)` returns `ModelType`
- `await repo.get(...)` returns `ModelType | None`
- IDEs provide accurate autocomplete
- mypy validates all operations

### Core Methods

#### create(data: dict) -> ModelType
Creates a new record and returns the instance with database-generated fields.

```python
org = await repo.create({
    "name": "my-org",
    "github_url": "https://github.com/my-org"
})
# org.id and org.created_at are populated
```

#### get(id: UUID, include_deleted: bool = False) -> ModelType | None
Retrieves a record by ID. Filters soft-deleted records by default.

```python
org = await repo.get(org_id)
if org is None:
    raise HTTPException(404, "Not found")
```

#### update(id: UUID, data: dict) -> ModelType | None
Updates a record and returns the updated instance.

```python
org = await repo.update(org_id, {"name": "new-name"})
if org is None:
    raise HTTPException(404, "Not found")
```

#### delete(id: UUID) -> bool
Deletes a record. For models with `SoftDeleteMixin`, sets `deleted_at` timestamp. For other models, physically removes the record.

```python
deleted = await repo.delete(org_id)
if not deleted:
    raise HTTPException(404, "Not found")
```

#### list(pagination: PaginationParams | None, include_deleted: bool = False) -> PaginatedResult[ModelType]
Lists records with pagination support.

```python
result = await repo.list(PaginationParams(offset=0, limit=20))
for org in result.items:
    print(org.name)

print(f"Page {result.page} of {result.total_pages}")
```

#### commit() -> None
Commits the current transaction.

```python
org = await repo.create(data)
await repo.commit()
```

#### rollback() -> None
Rolls back the current transaction.

```python
try:
    org = await repo.create(data)
    await repo.commit()
except Exception:
    await repo.rollback()
    raise
```

## Features

### Soft Delete Support

Models with `SoftDeleteMixin` get automatic soft delete support:

```python
from app.models.base import Base, UUIDMixin
from app.repositories.base import SoftDeleteMixin

class Organization(Base, UUIDMixin, SoftDeleteMixin):
    __tablename__ = "organizations"
    
    name: Mapped[str] = mapped_column(String(255))
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

Behavior:
- `delete()` sets `deleted_at` timestamp instead of removing records
- `get()` and `list()` automatically filter out soft-deleted records
- Use `include_deleted=True` to retrieve soft-deleted records

### Pagination

Pagination is handled via `PaginationParams` and `PaginatedResult`:

```python
from app.repositories.base import PaginationParams

# Create pagination params
params = PaginationParams(offset=20, limit=10)  # Page 3, 10 items per page

# List with pagination
result = await repo.list(params)

# Access pagination metadata
print(f"Total: {result.total}")
print(f"Page {result.page} of {result.total_pages}")
print(f"Has next: {result.has_next}")
print(f"Has previous: {result.has_prev}")

# Access items
for item in result.items:
    print(item)
```

**Validation:**
- `offset` must be >= 0
- `limit` must be > 0 and <= 100

### Error Handling

Custom exceptions for better error handling:

```python
from app.repositories.base import (
    RepositoryError,           # Base exception
    RecordNotFoundError,       # Record not found
    RecordAlreadyExistsError,  # Unique constraint violation
    DatabaseOperationError,    # General database error
)

try:
    org = await repo.create(data)
except RecordAlreadyExistsError:
    raise HTTPException(409, "Organization already exists")
except DatabaseOperationError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(500, "Internal server error")
```

### OpenTelemetry Tracing

All repository operations are automatically traced:

```python
@trace_async("repository.create")
async def create(self, data: dict) -> ModelType:
    # Tracing is automatic
    pass
```

Traces include:
- Operation name (create, get, update, delete, list)
- Model name
- Timing information
- Error information (if any)

## Usage Examples

### Basic CRUD

```python
from app.repositories.organization import OrganizationRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

@app.post("/organizations")
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    
    try:
        org = await repo.create(org_data.dict())
        await repo.commit()
        return org
    except RecordAlreadyExistsError:
        await repo.rollback()
        raise HTTPException(409, "Organization already exists")
    except Exception:
        await repo.rollback()
        raise

@app.get("/organizations/{org_id}")
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    org = await repo.get(org_id)
    
    if org is None:
        raise HTTPException(404, "Organization not found")
    
    return org

@app.get("/organizations")
async def list_organizations(
    offset: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    result = await repo.list(PaginationParams(offset=offset, limit=limit))
    
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "total_pages": result.total_pages,
    }
```

### With Transaction Management

```python
@app.post("/organizations/{org_id}/repositories")
async def create_repository(
    org_id: str,
    repo_data: RepositoryCreate,
    db: AsyncSession = Depends(get_db)
):
    org_repo = OrganizationRepository(db)
    repo_repo = RepositoryRepository(db)
    
    try:
        # Verify organization exists
        org = await org_repo.get(org_id)
        if org is None:
            raise HTTPException(404, "Organization not found")
        
        # Create repository
        new_repo = await repo_repo.create({
            **repo_data.dict(),
            "organization_id": org_id
        })
        
        # Update organization stats
        await org_repo.update(org_id, {
            "total_repositories": org.total_repositories + 1
        })
        
        # Commit both operations
        await org_repo.commit()
        
        return new_repo
    except Exception:
        await org_repo.rollback()
        raise
```

### Custom Repository Methods

Add domain-specific methods to repositories:

```python
class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self._base = BaseRepository(Organization, db)
    
    # Delegate CRUD operations
    async def create(self, data: dict) -> Organization:
        return await self._base.create(data)
    
    # ... other delegated methods ...
    
    # Custom methods
    async def get_by_name(self, name: str) -> Organization | None:
        """Get organization by name."""
        stmt = select(Organization).where(Organization.name == name)
        result = await self._base.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_top_by_stars(self, limit: int = 10) -> list[Organization]:
        """Get top organizations by total stars."""
        stmt = (
            select(Organization)
            .order_by(Organization.total_stars.desc())
            .limit(limit)
        )
        result = await self._base.db.execute(stmt)
        return list(result.scalars().all())
```

## Testing

### Unit Tests

Mock the database session and test repository logic:

```python
from unittest.mock import AsyncMock, MagicMock
import pytest

@pytest.mark.asyncio
async def test_create_organization():
    mock_db = AsyncMock(spec=AsyncSession)
    repo = OrganizationRepository(mock_db)
    
    mock_org = MagicMock(spec=Organization)
    mock_org.id = uuid.uuid4()
    mock_org.name = "test-org"
    
    with patch.object(repo._base, "create", return_value=mock_org):
        result = await repo.create({"name": "test-org"})
        
        assert result == mock_org
        assert result.name == "test-org"
```

### Integration Tests

Test with real database (using test fixtures):

```python
@pytest.mark.asyncio
async def test_create_and_retrieve_organization(db_session):
    repo = OrganizationRepository(db_session)
    
    # Create
    org = await repo.create({
        "name": "test-org",
        "github_url": "https://github.com/test-org"
    })
    await repo.commit()
    
    # Retrieve
    retrieved = await repo.get(str(org.id))
    
    assert retrieved is not None
    assert retrieved.name == "test-org"
    assert retrieved.github_url == "https://github.com/test-org"
```

## Best Practices

### 1. Always Use Transaction Management

```python
# ✅ Good: Explicit commit
try:
    org = await repo.create(data)
    await repo.commit()
except Exception:
    await repo.rollback()
    raise

# ❌ Bad: No commit (changes not persisted)
org = await repo.create(data)
```

### 2. Handle Not Found Cases

```python
# ✅ Good: Check for None
org = await repo.get(org_id)
if org is None:
    raise HTTPException(404, "Not found")

# ❌ Bad: Assume record exists
org = await repo.get(org_id)
org.name = "new-name"  # AttributeError if org is None!
```

### 3. Use Pagination for List Operations

```python
# ✅ Good: Use pagination
result = await repo.list(PaginationParams(offset=0, limit=20))

# ❌ Bad: Load all records
result = await repo.list(PaginationParams(offset=0, limit=10000))
```

### 4. Leverage Type Safety

```python
# ✅ Good: Type annotations
async def get_organization(org_id: str) -> Organization | None:
    repo = OrganizationRepository(db)
    return await repo.get(org_id)

# ❌ Bad: No type annotations
async def get_organization(org_id):
    repo = OrganizationRepository(db)
    return await repo.get(org_id)
```

### 5. Use Custom Exceptions

```python
# ✅ Good: Catch specific exceptions
try:
    org = await repo.create(data)
except RecordAlreadyExistsError:
    raise HTTPException(409, "Already exists")
except DatabaseOperationError:
    raise HTTPException(500, "Database error")

# ❌ Bad: Catch all exceptions
try:
    org = await repo.create(data)
except Exception:
    raise HTTPException(500, "Error")
```

### 6. Don't Mix Repository and ORM Code

```python
# ✅ Good: Use repository methods
repo = OrganizationRepository(db)
org = await repo.get(org_id)

# ❌ Bad: Mix repository and ORM
repo = OrganizationRepository(db)
stmt = select(Organization).where(Organization.id == org_id)
org = await repo._base.db.execute(stmt)  # Don't access _base.db directly!
```

### 7. Add Custom Methods to Repositories

```python
# ✅ Good: Domain logic in repository
class OrganizationRepository:
    async def get_by_name(self, name: str) -> Organization | None:
        # Custom query logic
        pass

# ❌ Bad: Domain logic in service/controller
@app.get("/organizations")
async def get_org_by_name(name: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Organization).where(Organization.name == name)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

## Migration Path

If you have existing code using direct ORM access, migrate gradually:

1. **Create repository** for the model
2. **Update new code** to use repository
3. **Refactor existing code** incrementally
4. **Add tests** for repository operations
5. **Remove direct ORM access** once fully migrated

## Summary

The repository pattern provides a clean, type-safe abstraction for data access:

- ✅ Use composition for flexibility
- ✅ Leverage generic types for safety
- ✅ Handle transactions explicitly
- ✅ Use pagination for lists
- ✅ Add custom methods for domain logic
- ✅ Write comprehensive tests
- ✅ Benefit from automatic tracing

For questions or improvements, see the main documentation or open an issue.
