"""Repository Pattern Implementation Guide

This document explains the composition-based repository pattern used in this project.

## Architecture Overview

The repository pattern provides a data access abstraction layer between business logic
and the database. We use **composition over inheritance** for flexibility and testability.

### Components

1. **BaseRepository[ModelType]**: Generic CRUD operations for any SQLAlchemy model
   - Located: `app/repositories/base.py`
   - Handles: create, get, update, delete, list, count
   - Provides: soft delete, pagination, transaction support

2. **Entity Repositories**: Custom repositories for specific entities
   - Located: `app/repositories/{entity_name}.py`
   - Inherit from: (nothing - pure composition!)
   - Extend: Add custom queries specific to the entity

## Creating a New Repository

### Step 1: Import Required Dependencies

```python
from typing import Any, Optional, Union
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.your_model import YourModel
from app.repositories.base import (
    BaseRepository,
    PaginationParams,
    PaginatedResult,
    RepositoryError,
)
```

### Step 2: Create the Repository Class

```python
class YourModelRepository:
    """Repository for YourModel entities using composition pattern."""
    
    def __init__(self, session: AsyncSession, use_cache: bool = False) -> None:
        self._session = session
        self._base_repo = BaseRepository(session, YourModel, use_cache=use_cache)
        self._logger = get_logger(f"{__name__}.YourModelRepository")
```

### Step 3: Delegate CRUD Methods

```python
    async def create(self, **kwargs: Any) -> YourModel:
        """Create a new YourModel."""
        return await self._base_repo.create(**kwargs)
    
    async def get(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> Optional[YourModel]:
        """Get YourModel by ID."""
        return await self._base_repo.get(entity_id, include_deleted=include_deleted)
    
    async def get_or_404(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> YourModel:
        """Get YourModel by ID or raise NotFoundError."""
        return await self._base_repo.get_or_404(entity_id, include_deleted=include_deleted)
    
    async def update(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        **kwargs: Any
    ) -> Optional[YourModel]:
        """Update YourModel by ID."""
        return await self._base_repo.update(entity_id, **kwargs)
    
    async def delete(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        soft: bool = True
    ) -> bool:
        """Delete YourModel by ID."""
        return await self._base_repo.delete(entity_id, soft=soft)
    
    async def list(
        self, 
        pagination: Optional[PaginationParams] = None,
        include_deleted: bool = False
    ) -> PaginatedResult[YourModel]:
        """List YourModels with pagination."""
        return await self._base_repo.list(
            pagination=pagination, 
            include_deleted=include_deleted
        )
    
    async def count(self, include_deleted: bool = False) -> int:
        """Count total YourModels."""
        return await self._base_repo.count(include_deleted=include_deleted)
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        return await self._base_repo.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        return await self._base_repo.rollback()
```

### Step 4: Add Custom Methods

```python
    async def get_by_custom_field(self, field_value: str) -> Optional[YourModel]:
        """Get YourModel by a custom field.
        
        This is a custom method that's specific to YourModel.
        """
        try:
            self._logger.debug(
                "Getting YourModel by custom field",
                field_value=field_value
            )
            
            query = select(YourModel).where(
                YourModel.custom_field == field_value,
                YourModel.deleted_at.is_(None)
            )
            
            result = await self._session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self._logger.error(
                "Failed to get YourModel by custom field",
                field_value=field_value,
                error=str(e)
            )
            raise RepositoryError(f"Failed to get YourModel: {e}") from e
```

## Using Repositories in FastAPI Endpoints

### With Dependency Injection

```python
from fastapi import Depends
from app.core.database import get_db

@app.get("/your-models/{id}")
async def get_your_model(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = YourModelRepository(db)
    model = await repo.get_or_404(id)
    return model


@app.post("/your-models/")
async def create_your_model(
    data: CreateYourModelSchema,
    db: AsyncSession = Depends(get_db)
):
    repo = YourModelRepository(db)
    
    try:
        async with db.begin():
            model = await repo.create(**data.dict())
            await repo.commit()
            return model
    except ConflictError:
        await repo.rollback()
        raise HTTPException(status_code=409, detail="Already exists")
    except RepositoryError as e:
        await repo.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/your-models/")
async def list_your_models(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    repo = YourModelRepository(db)
    pagination = PaginationParams(offset=offset, limit=limit)
    
    result = await repo.list(pagination=pagination)
    
    return {
        "items": result.items,
        "total": result.total,
        "offset": result.offset,
        "limit": result.limit,
        "has_next": result.has_next,
        "has_prev": result.has_prev
    }
```

## BaseRepository Features

### CRUD Operations

- `create(**kwargs)`: Create a new entity
- `get(id, include_deleted=False)`: Get entity by ID
- `get_or_404(id)`: Get entity or raise NotFoundError
- `update(id, **kwargs)`: Update entity
- `delete(id, soft=True)`: Delete entity (soft or hard)
- `list(pagination, include_deleted=False)`: List with pagination
- `count(include_deleted=False)`: Count total entities

### Transaction Management

- `commit()`: Commit current transaction
- `rollback()`: Rollback current transaction

### Soft Deletes

Models that include `SoftDeleteMixin` get automatic soft delete support:
- `deleted_at` timestamp is set on delete
- Queries automatically exclude soft-deleted entities unless `include_deleted=True`
- Can restore soft-deleted entities by clearing `deleted_at`

### Pagination

```python
from app.repositories.base import PaginationParams, PaginatedResult

pagination = PaginationParams(offset=0, limit=50)  # Default values
result = await repo.list(pagination=pagination)

# Result contains:
# - items: List of entities
# - total: Total count of entities
# - offset: Current offset
# - limit: Current limit
# - has_next: Boolean indicating if more results exist
# - has_prev: Boolean indicating if previous results exist
```

### Error Handling

```python
from app.repositories.base import (
    RepositoryError,      # Base exception
    NotFoundError,        # Entity not found
    ConflictError,        # Constraint violation
)

try:
    entity = await repo.create(**data)
except ConflictError as e:
    # Handle duplicate/constraint violations
    pass
except RepositoryError as e:
    # Handle other database errors
    pass
```

## Testing Repositories

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def repository(mock_session):
    return YourModelRepository(mock_session)

@pytest.mark.asyncio
async def test_create(repository, mock_session):
    # Mock the BaseRepository
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    
    result = await repository.create(name="Test")
    assert result is not None
```

## Best Practices

1. **Always inject BaseRepository via constructor** - Enables testing and flexibility
2. **Use explicit method delegation** - Makes dependencies clear
3. **Add custom methods for entity-specific queries** - Keep custom logic separate
4. **Handle exceptions properly** - Convert SQLAlchemy errors to custom exceptions
5. **Log all operations** - Use structured logging for debugging
6. **Type hint everything** - Enables mypy validation
7. **Test with mocked sessions** - Easier than integration tests
8. **Use transactions for multi-step operations** - Ensure data consistency

## Example: Complete Repository

See `app/repositories/organization.py` for a complete, working example.

## Future Enhancements

- Caching layer (via `use_cache` parameter)
- Advanced filtering and search
- Batch operations
- Custom query builders
- Performance monitoring
"""
