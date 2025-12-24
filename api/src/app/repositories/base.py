"""Base repository class with generic CRUD operations."""

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar, Union, cast

from sqlalchemy import and_, select, update, func, CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Result

from app.core.logging import get_logger
from app.core.tracing import trace_database

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=DeclarativeBase)

logger = get_logger(__name__)


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class NotFoundError(RepositoryError):
    """Raised when a requested entity is not found."""
    pass


class ConflictError(RepositoryError):
    """Raised when an operation conflicts with existing data."""
    pass


class PaginationParams:
    """Pagination parameters for list operations."""
    
    def __init__(self, offset: int = 0, limit: int = 50) -> None:
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit <= 0 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        self.offset = offset
        self.limit = limit


class PaginatedResult(Generic[ModelType]):
    """Paginated result container."""
    
    def __init__(
        self, 
        items: list[ModelType], 
        total: int, 
        offset: int, 
        limit: int
    ) -> None:
        self.items = items
        self.total = total
        self.offset = offset
        self.limit = limit
        self.has_next = offset + limit < total
        self.has_prev = offset > 0


class BaseRepository(Generic[ModelType]):
    """Base repository class with common CRUD operations.
    
    Provides async CRUD operations with transaction support, soft delete,
    pagination, and optional caching. Integrates with OpenTelemetry tracing
    and structured logging.
    
    Args:
        session: Async SQLAlchemy session
        model: SQLAlchemy model class
        use_cache: Enable/disable caching (for future implementation)
    """
    
    def __init__(
        self, 
        session: AsyncSession, 
        model: type[ModelType],
        use_cache: bool = False
    ) -> None:
        self._session = session
        self._model = model
        self._use_cache = use_cache
        self._logger = get_logger(f"{__name__}.{model.__name__}Repository")
    
    @trace_database()
    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new entity.
        
        Args:
            **kwargs: Entity attributes
            
        Returns:
            Created entity instance
            
        Raises:
            ConflictError: If entity conflicts with existing data
            RepositoryError: For other database errors
        """
        try:
            self._logger.debug("Creating new entity", model=self._model.__name__)
            
            entity = self._model(**kwargs)
            self._session.add(entity)
            await self._session.flush()  # Get the ID without committing
            await self._session.refresh(entity)
            
            self._logger.info(
                "Entity created successfully",
                model=self._model.__name__,
                entity_id=getattr(entity, 'id', None)
            )
            
            return entity
            
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to create entity",
                model=self._model.__name__,
                error=str(e)
            )
            # Check for common constraint violations
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(f"Entity conflicts with existing data: {e}") from e
            raise RepositoryError(f"Failed to create entity: {e}") from e
    
    @trace_database()
    async def get(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """Get entity by ID.
        
        Args:
            entity_id: Entity identifier
            include_deleted: Include soft-deleted entities
            
        Returns:
            Entity instance or None if not found
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            self._logger.debug(
                "Getting entity by ID",
                model=self._model.__name__,
                entity_id=entity_id,
                include_deleted=include_deleted
            )
            
            # Use getattr for model attribute access to avoid mypy issues with mixins
            query = select(self._model).where(getattr(self._model, 'id') == entity_id)
            
            # Add soft delete filter if model has deleted_at column
            if not include_deleted and hasattr(self._model, 'deleted_at'):
                query = query.where(getattr(self._model, 'deleted_at').is_(None))
            
            result = await self._session.execute(query)
            entity = result.scalar_one_or_none()
            
            if entity:
                self._logger.debug(
                    "Entity found",
                    model=self._model.__name__,
                    entity_id=entity_id
                )
            else:
                self._logger.debug(
                    "Entity not found",
                    model=self._model.__name__,
                    entity_id=entity_id
                )
            
            return entity
            
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to get entity",
                model=self._model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            raise RepositoryError(f"Failed to get entity: {e}") from e
    
    @trace_database()
    async def get_or_404(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> ModelType:
        """Get entity by ID or raise NotFoundError.
        
        Args:
            entity_id: Entity identifier
            include_deleted: Include soft-deleted entities
            
        Returns:
            Entity instance
            
        Raises:
            NotFoundError: If entity not found
            RepositoryError: For database errors
        """
        entity = await self.get(entity_id, include_deleted=include_deleted)
        if entity is None:
            raise NotFoundError(f"{self._model.__name__} with id {entity_id} not found")
        return entity
    
    @trace_database()
    async def update(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        **kwargs: Any
    ) -> Optional[ModelType]:
        """Update entity by ID.
        
        Args:
            entity_id: Entity identifier
            **kwargs: Attributes to update
            
        Returns:
            Updated entity instance or None if not found
            
        Raises:
            ConflictError: If update conflicts with existing data
            RepositoryError: For other database errors
        """
        try:
            self._logger.debug(
                "Updating entity",
                model=self._model.__name__,
                entity_id=entity_id,
                fields=list(kwargs.keys())
            )
            
            # Add updated_at timestamp if model has it
            if hasattr(self._model, 'updated_at'):
                kwargs['updated_at'] = datetime.now(timezone.utc)
            
            # Build update query with soft delete filter
            query = update(self._model).where(getattr(self._model, 'id') == entity_id)
            
            if hasattr(self._model, 'deleted_at'):
                query = query.where(getattr(self._model, 'deleted_at').is_(None))
            
            query = query.values(**kwargs).returning(self._model)
            
            result = await self._session.execute(query)
            entity = result.scalar_one_or_none()
            
            if entity:
                self._logger.info(
                    "Entity updated successfully",
                    model=self._model.__name__,
                    entity_id=entity_id
                )
            else:
                self._logger.debug(
                    "Entity not found for update",
                    model=self._model.__name__,
                    entity_id=entity_id
                )
            
            return entity
            
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to update entity",
                model=self._model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ConflictError(f"Update conflicts with existing data: {e}") from e
            raise RepositoryError(f"Failed to update entity: {e}") from e
    
    @trace_database()
    async def delete(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        soft: bool = True
    ) -> bool:
        """Delete entity by ID.
        
        Args:
            entity_id: Entity identifier
            soft: Use soft delete (default) or hard delete
            
        Returns:
            True if entity was deleted, False if not found
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            self._logger.debug(
                "Deleting entity",
                model=self._model.__name__,
                entity_id=entity_id,
                soft_delete=soft
            )
            
            if soft and hasattr(self._model, 'deleted_at'):
                # Soft delete: set deleted_at timestamp
                update_data = {'deleted_at': datetime.now(timezone.utc)}
                if hasattr(self._model, 'updated_at'):
                    update_data['updated_at'] = datetime.now(timezone.utc)
                
                query = update(self._model).where(
                    and_(
                        getattr(self._model, 'id') == entity_id,
                        getattr(self._model, 'deleted_at').is_(None)
                    )
                ).values(**update_data)
                
                result = await self._session.execute(query)
                # Type cast to handle SQLAlchemy result type
                deleted = bool(getattr(result, 'rowcount', 0) > 0)
                
            else:
                # Hard delete: remove from database
                entity = await self.get(entity_id, include_deleted=True)
                if entity:
                    await self._session.delete(entity)
                    deleted = True
                else:
                    deleted = False
            
            if deleted:
                self._logger.info(
                    "Entity deleted successfully",
                    model=self._model.__name__,
                    entity_id=entity_id,
                    soft_delete=soft
                )
            else:
                self._logger.debug(
                    "Entity not found for deletion",
                    model=self._model.__name__,
                    entity_id=entity_id
                )
            
            return deleted
            
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to delete entity",
                model=self._model.__name__,
                entity_id=entity_id,
                error=str(e)
            )
            raise RepositoryError(f"Failed to delete entity: {e}") from e
    
    @trace_database()
    async def list(
        self, 
        pagination: Optional[PaginationParams] = None,
        include_deleted: bool = False
    ) -> PaginatedResult[ModelType]:
        """List entities with pagination.
        
        Args:
            pagination: Pagination parameters (default: offset=0, limit=50)
            include_deleted: Include soft-deleted entities
            
        Returns:
            Paginated result with entities and metadata
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            if pagination is None:
                pagination = PaginationParams()
            
            self._logger.debug(
                "Listing entities",
                model=self._model.__name__,
                offset=pagination.offset,
                limit=pagination.limit,
                include_deleted=include_deleted
            )
            
            # Base query
            query = select(self._model)
            count_query = select(func.count(getattr(self._model, 'id')))
            
            # Add soft delete filter if model has deleted_at column
            if not include_deleted and hasattr(self._model, 'deleted_at'):
                query = query.where(getattr(self._model, 'deleted_at').is_(None))
                count_query = count_query.where(getattr(self._model, 'deleted_at').is_(None))
            
            # Add ordering (by created_at if available, otherwise by id)
            if hasattr(self._model, 'created_at'):
                query = query.order_by(getattr(self._model, 'created_at').desc())
            else:
                query = query.order_by(getattr(self._model, 'id'))
            
            # Add pagination
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            # Execute queries
            items_result = await self._session.execute(query)
            items = list(items_result.scalars().all())
            
            total_result = await self._session.execute(count_query)
            total = total_result.scalar() or 0
            
            self._logger.debug(
                "Listed entities successfully",
                model=self._model.__name__,
                count=len(items),
                total=total
            )
            
            return PaginatedResult(
                items=items,
                total=total,
                offset=pagination.offset,
                limit=pagination.limit
            )
            
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to list entities",
                model=self._model.__name__,
                error=str(e)
            )
            raise RepositoryError(f"Failed to list entities: {e}") from e
    
    @trace_database()
    async def count(self, include_deleted: bool = False) -> int:
        """Count total entities.
        
        Args:
            include_deleted: Include soft-deleted entities
            
        Returns:
            Total count of entities
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            self._logger.debug(
                "Counting entities",
                model=self._model.__name__,
                include_deleted=include_deleted
            )
            
            query = select(func.count(getattr(self._model, 'id')))
            
            if not include_deleted and hasattr(self._model, 'deleted_at'):
                query = query.where(getattr(self._model, 'deleted_at').is_(None))
            
            result = await self._session.execute(query)
            total = result.scalar() or 0
            
            self._logger.debug(
                "Counted entities successfully",
                model=self._model.__name__,
                total=total
            )
            
            return total
            
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to count entities",
                model=self._model.__name__,
                error=str(e)
            )
            raise RepositoryError(f"Failed to count entities: {e}") from e
    
    async def begin_transaction(self) -> None:
        """Begin a new transaction.
        
        Use with async context manager for automatic rollback on errors:
        
        async with session.begin():
            await repo.create(...)
            await repo.update(...)
        """
        # Transaction management is handled by the session
        # This method is here for documentation and future extension
        pass
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        try:
            await self._session.commit()
            self._logger.debug("Transaction committed", model=self._model.__name__)
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to commit transaction",
                model=self._model.__name__,
                error=str(e)
            )
            raise RepositoryError(f"Failed to commit transaction: {e}") from e
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        try:
            await self._session.rollback()
            self._logger.debug("Transaction rolled back", model=self._model.__name__)
        except SQLAlchemyError as e:
            self._logger.error(
                "Failed to rollback transaction",
                model=self._model.__name__,
                error=str(e)
            )
            raise RepositoryError(f"Failed to rollback transaction: {e}") from e
