"""Base repository pattern with generic CRUD operations.

This module implements a comprehensive base repository pattern with:
- Generic type-safe CRUD operations using Python generics (TypeVar)
- Soft delete support via SoftDeleteMixin
- Pagination with PaginationParams and PaginatedResult
- Transaction management (commit/rollback)
- OpenTelemetry tracing integration for observability
- Comprehensive error handling with custom exceptions

Architecture Pattern: Composition over Inheritance
---------------------------------------------------
This base repository is designed to be used via composition rather than inheritance.
Composition provides:
- Better separation of concerns and testability
- Explicit method delegation (no magic __getattr__)
- Aligns with FastAPI's dependency injection patterns
- Easier to extend with cross-cutting concerns (caching, logging)

Usage Example:
    class OrganizationRepository:
        def __init__(self, db: AsyncSession):
            self._base = BaseRepository(Organization, db)
        
        async def create(self, data: dict) -> Organization:
            return await self._base.create(data)

Type Safety with Generics:
    ModelType = TypeVar("ModelType", bound=Base)
    
    class BaseRepository(Generic[ModelType]):
        def __init__(self, model: type[ModelType], db: AsyncSession):
            self.model = model
            self.db = db

Soft Delete Implementation:
    Models with SoftDeleteMixin get automatic soft delete support:
    - delete() sets deleted_at timestamp instead of removing records
    - get() and list() automatically filter out soft-deleted records
    - Use include_deleted=True to retrieve soft-deleted records

Pagination Support:
    PaginationParams(offset=0, limit=10)
    result = await repo.list(pagination=params)
    # Returns PaginatedResult with items, total, offset, limit
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tracing import trace_async
from app.models.base import Base

logger = get_logger(__name__)

# Generic type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


class RepositoryError(Exception):
    """Base exception for repository errors."""

    pass


class RecordNotFoundError(RepositoryError):
    """Raised when a record is not found."""

    pass


class RecordAlreadyExistsError(RepositoryError):
    """Raised when attempting to create a duplicate record."""

    pass


class DatabaseOperationError(RepositoryError):
    """Raised when a database operation fails."""

    pass


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality to models.
    
    Models using this mixin should have a deleted_at column:
        deleted_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
    
    Soft-deleted records have deleted_at set to a timestamp instead of being
    physically removed from the database. This allows for data recovery and
    audit trails.
    """

    deleted_at: datetime | None


@dataclass
class PaginationParams:
    """Parameters for pagination.
    
    Attributes:
        offset: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 10)
    
    Validation:
        - offset must be >= 0
        - limit must be > 0 and <= 100
    """

    offset: int = 0
    limit: int = 10

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.offset < 0:
            raise ValueError("Offset must be non-negative")
        if self.limit <= 0:
            raise ValueError("Limit must be positive")
        if self.limit > 100:
            raise ValueError("Limit must not exceed 100")


@dataclass
class PaginatedResult(Generic[ModelType]):
    """Result container for paginated queries.
    
    Attributes:
        items: List of model instances for the current page
        total: Total number of records matching the query
        offset: Number of records skipped
        limit: Maximum number of records per page
    
    Properties:
        has_next: Whether there are more pages available
        has_prev: Whether there are previous pages available
        page: Current page number (1-indexed)
        total_pages: Total number of pages
    """

    items: list[ModelType]
    total: int
    offset: int
    limit: int

    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.offset + self.limit < self.total

    @property
    def has_prev(self) -> bool:
        """Check if there are previous pages."""
        return self.offset > 0

    @property
    def page(self) -> int:
        """Get current page number (1-indexed)."""
        return (self.offset // self.limit) + 1

    @property
    def total_pages(self) -> int:
        """Get total number of pages."""
        return (self.total + self.limit - 1) // self.limit


class BaseRepository(Generic[ModelType]):
    """Generic repository with type-safe CRUD operations.
    
    This repository provides:
    - Type-safe CRUD operations (create, read, update, delete)
    - Soft delete support for models with SoftDeleteMixin
    - Pagination with validation
    - Transaction management (commit/rollback)
    - OpenTelemetry tracing for all operations
    - Comprehensive error handling
    
    Type Parameters:
        ModelType: SQLAlchemy model class bound to Base
    
    Attributes:
        model: SQLAlchemy model class
        db: Async database session
    
    Example:
        repo = BaseRepository(Organization, db_session)
        org = await repo.create({"name": "my-org"})
        orgs = await repo.list(pagination=PaginationParams(offset=0, limit=10))
    """

    def __init__(self, model: type[ModelType], db: AsyncSession) -> None:
        """Initialize repository with model and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db

    @trace_async("repository.create")
    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create a new record.
        
        Args:
            data: Dictionary of column values for the new record
        
        Returns:
            Created model instance with database-generated fields populated
        
        Raises:
            RecordAlreadyExistsError: If a unique constraint is violated
            DatabaseOperationError: If database operation fails
        
        Example:
            org = await repo.create({"name": "my-org", "github_url": "..."})
        """
        try:
            instance = self.model(**data)
            self.db.add(instance)
            await self.db.flush()
            await self.db.refresh(instance)
            
            logger.info(
                "Created record",
                model=self.model.__name__,
                id=getattr(instance, "id", None),
            )
            
            return instance
        except Exception as e:
            logger.error(
                "Failed to create record",
                model=self.model.__name__,
                error=str(e),
            )
            if "unique constraint" in str(e).lower():
                raise RecordAlreadyExistsError(f"Record already exists: {e}") from e
            raise DatabaseOperationError(f"Failed to create record: {e}") from e

    @trace_async("repository.get")
    async def get(
        self,
        id: uuid.UUID,
        include_deleted: bool = False,
    ) -> ModelType | None:
        """Get a record by ID.
        
        Args:
            id: UUID of the record to retrieve
            include_deleted: If True, include soft-deleted records (default: False)
        
        Returns:
            Model instance if found, None otherwise
        
        Example:
            org = await repo.get(org_id)
            if org is None:
                raise HTTPException(404, "Organization not found")
        """
        try:
            stmt = select(self.model).where(self.model.id == id)
            
            # Filter out soft-deleted records unless explicitly requested
            if not include_deleted and hasattr(self.model, "deleted_at"):
                stmt = stmt.where(self.model.deleted_at.is_(None))
            
            result = await self.db.execute(stmt)
            instance = result.scalar_one_or_none()
            
            logger.debug(
                "Retrieved record",
                model=self.model.__name__,
                id=id,
                found=instance is not None,
            )
            
            return instance
        except Exception as e:
            logger.error(
                "Failed to get record",
                model=self.model.__name__,
                id=id,
                error=str(e),
            )
            raise DatabaseOperationError(f"Failed to get record: {e}") from e

    @trace_async("repository.update")
    async def update(
        self,
        id: uuid.UUID,
        data: dict[str, Any],
    ) -> ModelType | None:
        """Update a record by ID.
        
        Args:
            id: UUID of the record to update
            data: Dictionary of column values to update
        
        Returns:
            Updated model instance if found, None otherwise
        
        Raises:
            DatabaseOperationError: If database operation fails
        
        Example:
            org = await repo.update(org_id, {"name": "new-name"})
            if org is None:
                raise HTTPException(404, "Organization not found")
        """
        try:
            # First get the record to ensure it exists
            instance = await self.get(id)
            if instance is None:
                return None
            
            # Update the record
            stmt = (
                update(self.model)
                .where(self.model.id == id)
                .values(**data)
                .returning(self.model)
            )
            result = await self.db.execute(stmt)
            updated_instance = result.scalar_one()
            
            logger.info(
                "Updated record",
                model=self.model.__name__,
                id=id,
            )
            
            return updated_instance
        except Exception as e:
            logger.error(
                "Failed to update record",
                model=self.model.__name__,
                id=id,
                error=str(e),
            )
            raise DatabaseOperationError(f"Failed to update record: {e}") from e

    @trace_async("repository.delete")
    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID.
        
        For models with SoftDeleteMixin, this sets the deleted_at timestamp.
        For other models, this physically removes the record from the database.
        
        Args:
            id: UUID of the record to delete
        
        Returns:
            True if record was deleted, False if not found
        
        Raises:
            DatabaseOperationError: If database operation fails
        
        Example:
            deleted = await repo.delete(org_id)
            if not deleted:
                raise HTTPException(404, "Organization not found")
        """
        try:
            # Check if model supports soft delete
            if hasattr(self.model, "deleted_at"):
                # Soft delete: set deleted_at timestamp
                stmt = (
                    update(self.model)
                    .where(self.model.id == id)
                    .where(self.model.deleted_at.is_(None))
                    .values(deleted_at=func.now())
                )
                result = await self.db.execute(stmt)
                deleted = result.rowcount > 0
            else:
                # Hard delete: physically remove record
                stmt = delete(self.model).where(self.model.id == id)
                result = await self.db.execute(stmt)
                deleted = result.rowcount > 0
            
            if deleted:
                logger.info(
                    "Deleted record",
                    model=self.model.__name__,
                    id=id,
                    soft_delete=hasattr(self.model, "deleted_at"),
                )
            else:
                logger.debug(
                    "Record not found for deletion",
                    model=self.model.__name__,
                    id=id,
                )
            
            return deleted
        except Exception as e:
            logger.error(
                "Failed to delete record",
                model=self.model.__name__,
                id=id,
                error=str(e),
            )
            raise DatabaseOperationError(f"Failed to delete record: {e}") from e

    @trace_async("repository.list")
    async def list(
        self,
        pagination: PaginationParams | None = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[ModelType]:
        """List records with pagination.
        
        Args:
            pagination: Pagination parameters (default: offset=0, limit=10)
            include_deleted: If True, include soft-deleted records (default: False)
        
        Returns:
            PaginatedResult with items and pagination metadata
        
        Raises:
            DatabaseOperationError: If database operation fails
        
        Example:
            result = await repo.list(
                pagination=PaginationParams(offset=0, limit=20)
            )
            for org in result.items:
                print(org.name)
        """
        try:
            if pagination is None:
                pagination = PaginationParams()
            
            # Build base query
            stmt = select(self.model)
            
            # Filter out soft-deleted records unless explicitly requested
            if not include_deleted and hasattr(self.model, "deleted_at"):
                stmt = stmt.where(self.model.deleted_at.is_(None))
            
            # Get total count
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total_result = await self.db.execute(count_stmt)
            total = total_result.scalar_one()
            
            # Apply pagination
            stmt = stmt.offset(pagination.offset).limit(pagination.limit)
            
            # Execute query
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())
            
            logger.debug(
                "Listed records",
                model=self.model.__name__,
                total=total,
                offset=pagination.offset,
                limit=pagination.limit,
                returned=len(items),
            )
            
            return PaginatedResult(
                items=items,
                total=total,
                offset=pagination.offset,
                limit=pagination.limit,
            )
        except Exception as e:
            logger.error(
                "Failed to list records",
                model=self.model.__name__,
                error=str(e),
            )
            raise DatabaseOperationError(f"Failed to list records: {e}") from e

    async def commit(self) -> None:
        """Commit the current transaction.
        
        Raises:
            DatabaseOperationError: If commit fails
        
        Example:
            org = await repo.create({"name": "my-org"})
            await repo.commit()
        """
        try:
            await self.db.commit()
            logger.debug("Transaction committed", model=self.model.__name__)
        except Exception as e:
            logger.error(
                "Failed to commit transaction",
                model=self.model.__name__,
                error=str(e),
            )
            raise DatabaseOperationError(f"Failed to commit transaction: {e}") from e

    async def rollback(self) -> None:
        """Rollback the current transaction.
        
        Example:
            try:
                org = await repo.create({"name": "my-org"})
                await repo.commit()
            except Exception:
                await repo.rollback()
                raise
        """
        try:
            await self.db.rollback()
            logger.debug("Transaction rolled back", model=self.model.__name__)
        except Exception as e:
            logger.error(
                "Failed to rollback transaction",
                model=self.model.__name__,
                error=str(e),
            )
            # Don't raise here as rollback is often called in error handling
