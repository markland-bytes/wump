"""Base repository class with generic CRUD operations.

This module implements a composition-based repository pattern that provides
reusable database access operations (CRUD) for any SQLAlchemy model.

Key Concepts:
- COMPOSITION PATTERN: BaseRepository is injected as a dependency, not inherited
- GENERIC TYPE SAFETY: Uses TypeVar[ModelType] for compile-time type checking
- SOFT DELETE: Automatic filtering of deleted_at timestamps
- PAGINATION: Built-in offset/limit with total count and has_next/has_prev flags
- TRANSACTION SUPPORT: Explicit commit/rollback control for multi-step operations
- TRACING: @trace_database decorators integrate with OpenTelemetry

Usage Example:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.organization import Organization
    
    session: AsyncSession
    repo = BaseRepository(session, Organization)
    org = await repo.get(org_id)
    orgs = await repo.list(pagination=PaginationParams(offset=0, limit=50))
    new_org = await repo.create(name="My Org")
    await repo.update(org_id, name="Updated Org")
    await repo.delete(org_id, soft=True)  # Soft delete
    await repo.commit()

See app/repositories/organization.py for an example of composition pattern usage.
"""

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

# ============================================================================
# GENERIC TYPE DEFINITION
# ============================================================================
# ModelType is a type variable bound to SQLAlchemy DeclarativeBase, enabling
# BaseRepository[ModelType] to work with any SQLAlchemy model while maintaining
# full type safety and IDE autocomplete support.
ModelType = TypeVar("ModelType", bound=DeclarativeBase)

logger = get_logger(__name__)


# ============================================================================
# CUSTOM EXCEPTION HIERARCHY
# ============================================================================
# These exceptions provide fine-grained error handling for repository operations.
# Applications should catch these to implement appropriate error responses.


class RepositoryError(Exception):
    """Base exception for all repository operations.
    
    Raised when database operations fail. Other exceptions (NotFoundError,
    ConflictError) inherit from this for more specific error handling.
    
    Example:
        try:
            org = await repo.create(name="Test")
        except RepositoryError as e:
            logger.error(f"Database operation failed: {e}")
    """
    pass


class NotFoundError(RepositoryError):
    """Raised when a requested entity is not found.
    
    This exception indicates a lookup operation (get, get_or_404) did not
    find the requested entity. Applications can use this to return HTTP 404
    responses or set default values.
    
    Example:
        try:
            org = await repo.get_or_404(org_id)
        except NotFoundError:
            raise HTTPException(status_code=404, detail="Organization not found")
    """
    pass


class ConflictError(RepositoryError):
    """Raised when an operation conflicts with existing data.
    
    Typically indicates a database constraint violation (unique, foreign key, etc.).
    This is useful for detecting duplicate keys or constraint violations in
    business logic.
    
    Example:
        try:
            org = await repo.create(name="Test")
        except ConflictError as e:
            raise HTTPException(status_code=409, detail="Organization already exists")
    """
    pass


# ============================================================================
# PAGINATION SUPPORT
# ============================================================================
# These classes implement offset/limit pagination with validation to prevent
# common errors like requesting too many records or negative offsets.



class PaginationParams:
    """Pagination parameters for list operations.
    
    Implements offset/limit pagination with validation to ensure reasonable
    values. Limit is capped at 1000 to prevent denial-of-service attacks.
    
    Attributes:
        offset: Number of records to skip (default: 0, must be >= 0)
        limit: Number of records to return (default: 50, must be 1-1000)
    
    Example:
        # Get records 100-150
        pagination = PaginationParams(offset=100, limit=50)
        result = await repo.list(pagination=pagination)
        print(f"Page has {len(result.items)} items, total: {result.total}")
    
    Raises:
        ValueError: If offset is negative or limit is out of range
    """
    
    def __init__(self, offset: int = 0, limit: int = 50) -> None:
        if offset < 0:
            raise ValueError("Offset must be non-negative")
        if limit <= 0 or limit > 1000:
            raise ValueError("Limit must be between 1 and 1000")
        
        self.offset = offset
        self.limit = limit


class PaginatedResult(Generic[ModelType]):
    """Paginated result container with metadata.
    
    Returned by list() operations, this container holds the result items
    plus metadata needed for pagination controls (total count, next/previous).
    
    Attributes:
        items: List of entities in this page
        total: Total count of all entities (across all pages)
        offset: Current page offset
        limit: Current page limit
        has_next: Boolean indicating if more pages exist after this one
        has_prev: Boolean indicating if previous pages exist before this one
    
    Example:
        result = await repo.list(pagination=PaginationParams(offset=0, limit=50))
        
        for item in result.items:
            print(item)
        
        if result.has_next:
            next_result = await repo.list(
                pagination=PaginationParams(offset=result.offset + result.limit)
            )
    """
    
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
        # Calculate navigation flags based on total and pagination
        self.has_next = offset + limit < total
        self.has_prev = offset > 0


# ============================================================================
# BASE REPOSITORY - MAIN CRUD IMPLEMENTATION
# ============================================================================



class BaseRepository(Generic[ModelType]):
    """Generic repository class providing CRUD operations for any SQLAlchemy model.
    
    This is the core of the composition-based repository pattern. Instead of
    inheriting from this class, entity repositories inject BaseRepository as a
    dependency (composition). This provides better testability and flexibility.
    
    Key Features:
    - GENERIC TYPE SAFETY: Works with any SQLAlchemy model via TypeVar
    - SOFT DELETE: Automatic deleted_at filtering (models using SoftDeleteMixin)
    - PAGINATION: Built-in offset/limit with total count and navigation flags
    - TRANSACTIONS: Explicit commit/rollback for multi-step operations
    - TRACING: OpenTelemetry integration via @trace_database decorators
    - STRUCTURED LOGGING: All operations logged with contextual information
    - ERROR HANDLING: Custom exception hierarchy for granular error handling
    
    Args:
        session: AsyncSession for database communication
        model: SQLAlchemy model class (e.g., Organization, User)
        use_cache: Enable caching (prepared for future implementation)
    
    Example (Composition Pattern):
        class UserRepository:
            def __init__(self, session: AsyncSession) -> None:
                self._base_repo = BaseRepository(session, User)
            
            async def get(self, user_id: uuid.UUID) -> Optional[User]:
                return await self._base_repo.get(user_id)
    
    Type Safety:
        repo: BaseRepository[Organization] = BaseRepository(session, Organization)
        org: Organization = await repo.get_or_404(org_id)  # Type-safe return
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
    
    # ========================================================================
    # CREATE OPERATION
    # ========================================================================

    
    @trace_database()
    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new entity and return it.
        
        Instantiates a new model with the provided attributes, adds it to
        the session, and flushes to get the auto-generated ID without
        committing the transaction.
        
        Args:
            **kwargs: Model attributes (e.g., name="Test", email="test@example.com")
            
        Returns:
            Created entity instance with auto-generated fields populated
            
        Raises:
            ConflictError: If creation conflicts with constraints (unique, foreign key)
            RepositoryError: For other database errors
        
        Example:
            org = await repo.create(name="My Organization", slug="my-org")
            # org.id is now populated from database auto-increment/sequence
        """
        try:
            self._logger.debug("Creating new entity", model=self._model.__name__)
            
            # Instantiate model with provided attributes
            entity = self._model(**kwargs)
            
            # Add to session and flush to get auto-generated ID
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
    
    # ========================================================================
    # READ OPERATIONS (GET)
    # ========================================================================
    
    @trace_database()
    async def get(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """Get entity by ID.
        
        Performs a database lookup by primary key. Soft-deleted entities are
        automatically excluded unless include_deleted=True.
        
        Note: Uses getattr() for model attribute access to maintain type safety
        with mixins that add attributes to models at runtime.
        
        Args:
            entity_id: Entity identifier (UUID, string, or integer)
            include_deleted: If True, include soft-deleted entities (deleted_at is not None)
            
        Returns:
            Entity instance if found, None if not found
            
        Raises:
            RepositoryError: For database errors
        
        Example:
            org = await repo.get(org_id)
            if org is None:
                print("Organization not found")
            
            # Include soft-deleted organizations
            deleted_org = await repo.get(org_id, include_deleted=True)
        """
        try:
            self._logger.debug(
                "Getting entity by ID",
                model=self._model.__name__,
                entity_id=entity_id,
                include_deleted=include_deleted
            )
            
            # Build SELECT query by ID
            # Using getattr() to handle attributes added by mixins (e.g., SoftDeleteMixin)
            query = select(self._model).where(getattr(self._model, 'id') == entity_id)
            
            # Add soft delete filter if model has deleted_at column
            # This is how we implement soft delete: just filter on deleted_at IS NULL
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
        """Get entity by ID, raising NotFoundError if not found.
        
        Convenience method that calls get() and raises NotFoundError if
        the entity doesn't exist. Useful for API endpoints that should
        return 404 when entity is missing.
        
        Args:
            entity_id: Entity identifier
            include_deleted: If True, include soft-deleted entities
            
        Returns:
            Entity instance
            
        Raises:
            NotFoundError: If entity not found (includes model name and ID in message)
            RepositoryError: For other database errors
        
        Example:
            try:
                org = await repo.get_or_404(org_id)
            except NotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
        """
        entity = await self.get(entity_id, include_deleted=include_deleted)
        if entity is None:
            raise NotFoundError(f"{self._model.__name__} with id {entity_id} not found")
        return entity
    
    # ========================================================================
    # UPDATE OPERATION
    # ========================================================================
    
    @trace_database()
    async def update(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        **kwargs: Any
    ) -> Optional[ModelType]:
        """Update entity by ID.
        
        Performs an UPDATE query on the entity, filtering by ID and soft-deleted
        status. Automatically adds updated_at timestamp if the model has that field.
        Returns the updated entity with all new values populated.
        
        Args:
            entity_id: Entity identifier
            **kwargs: Attributes to update (e.g., name="New Name", status="active")
            
        Returns:
            Updated entity instance or None if entity not found
            
        Raises:
            ConflictError: If update conflicts with constraints (unique, foreign key)
            RepositoryError: For other database errors
        
        Example:
            org = await repo.update(org_id, name="New Name", slug="new-slug")
            if org is None:
                print("Organization not found")
            else:
                print(f"Updated to {org.name}")
        """
        try:
            self._logger.debug(
                "Updating entity",
                model=self._model.__name__,
                entity_id=entity_id,
                fields=list(kwargs.keys())
            )
            
            # Automatically add updated_at timestamp if model supports it
            # This ensures every update records when it happened
            if hasattr(self._model, 'updated_at'):
                kwargs['updated_at'] = datetime.now(timezone.utc)
            
            # Build UPDATE query with soft delete filter
            # Only update entities that haven't been soft-deleted
            query = update(self._model).where(getattr(self._model, 'id') == entity_id)
            
            if hasattr(self._model, 'deleted_at'):
                query = query.where(getattr(self._model, 'deleted_at').is_(None))
            
            # Apply the update and return the updated entity
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
    
    # ========================================================================
    # DELETE OPERATIONS
    # ========================================================================
    
    @trace_database()
    async def delete(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        soft: bool = True
    ) -> bool:
        """Delete entity by ID (soft or hard).
        
        Soft Delete (default):
            Sets deleted_at timestamp to current UTC time. The entity remains
            in the database but is hidden from normal queries. Can be restored
            by clearing the deleted_at field.
        
        Hard Delete:
            Permanently removes the entity from the database. Use with caution!
        
        Args:
            entity_id: Entity identifier
            soft: If True, use soft delete; if False, hard delete from database
            
        Returns:
            True if entity was deleted, False if entity not found
            
        Raises:
            RepositoryError: For database errors
        
        Example:
            # Soft delete (recommended)
            deleted = await repo.delete(org_id, soft=True)
            
            # Hard delete (permanent removal)
            deleted = await repo.delete(org_id, soft=False)
        """
        try:
            self._logger.debug(
                "Deleting entity",
                model=self._model.__name__,
                entity_id=entity_id,
                soft_delete=soft
            )
            
            if soft and hasattr(self._model, 'deleted_at'):
                # SOFT DELETE: Set deleted_at timestamp instead of removing
                # Also updates updated_at if the model has it
                update_data = {'deleted_at': datetime.now(timezone.utc)}
                if hasattr(self._model, 'updated_at'):
                    update_data['updated_at'] = datetime.now(timezone.utc)
                
                # Build update query that only affects non-deleted entities
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
                # HARD DELETE: Remove entity from database permanently
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
    
    # ========================================================================
    # LIST OPERATION (WITH PAGINATION)
    # ========================================================================
    
    @trace_database()
    async def list(
        self, 
        pagination: Optional[PaginationParams] = None,
        include_deleted: bool = False
    ) -> PaginatedResult[ModelType]:
        """List entities with offset/limit pagination.
        
        Returns all entities (excluding soft-deleted by default) in pages
        of configurable size. Results include total count for building
        pagination UI (has_next, has_prev, etc).
        
        Ordering: Results are ordered by created_at (descending) if available,
        otherwise by ID.
        
        Args:
            pagination: PaginationParams with offset/limit (default: 0, 50)
            include_deleted: If True, include soft-deleted entities
            
        Returns:
            PaginatedResult with items, total, offset, limit, has_next, has_prev
            
        Raises:
            RepositoryError: For database errors
        
        Example:
            # First page
            result = await repo.list(pagination=PaginationParams(offset=0, limit=50))
            print(f"Page 1: {len(result.items)} items, total: {result.total}")
            
            # Next page
            if result.has_next:
                result = await repo.list(
                    pagination=PaginationParams(
                        offset=result.offset + result.limit,
                        limit=50
                    )
                )
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
            
            # Base SELECT query
            query = select(self._model)
            # Separate query for counting total (doesn't need pagination)
            count_query = select(func.count(getattr(self._model, 'id')))
            
            # Add soft delete filter if model has deleted_at column
            # This makes soft-deleted entities invisible by default
            if not include_deleted and hasattr(self._model, 'deleted_at'):
                query = query.where(getattr(self._model, 'deleted_at').is_(None))
                count_query = count_query.where(getattr(self._model, 'deleted_at').is_(None))
            
            # Add ordering (by created_at if available, otherwise by id)
            # Descending order shows most recent items first
            if hasattr(self._model, 'created_at'):
                query = query.order_by(getattr(self._model, 'created_at').desc())
            else:
                query = query.order_by(getattr(self._model, 'id'))
            
            # Add pagination (offset and limit)
            query = query.offset(pagination.offset).limit(pagination.limit)
            
            # Execute both queries
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
    
    # ========================================================================
    # COUNT OPERATION
    # ========================================================================
    
    @trace_database()
    async def count(self, include_deleted: bool = False) -> int:
        """Count total entities.
        
        Returns the total number of entities, excluding soft-deleted
        entities by default.
        
        Args:
            include_deleted: If True, include soft-deleted entities in count
            
        Returns:
            Total count of entities
            
        Raises:
            RepositoryError: For database errors
        
        Example:
            total = await repo.count()
            print(f"Total organizations: {total}")
            
            # Include deleted
            deleted_count = await repo.count(include_deleted=True)
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
    
    # ========================================================================
    # TRANSACTION MANAGEMENT
    # ========================================================================
    
    async def begin_transaction(self) -> None:
        """Begin a new transaction (documentation only).
        
        Transaction management is typically handled via FastAPI dependency
        injection or async context managers. This method documents the pattern.
        
        Example:
            # Using async context manager (recommended)
            async with session.begin():
                await repo.create(name="Test")
                await repo.update(id, status="active")
                # Auto-committed on successful exit
        """
        # Transaction management is handled by the session
        # This method is here for documentation and future extension
        pass
    
    async def commit(self) -> None:
        """Commit the current transaction.
        
        Persists all pending changes to the database. Call after create/update
        operations when not using an async context manager.
        
        Example:
            org = await repo.create(name="Test")
            await repo.commit()  # Persist the new organization
            
        Raises:
            RepositoryError: If commit fails
        """
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
        """Rollback the current transaction.
        
        Discards all pending changes since the last commit. Use after catching
        exceptions to undo operations.
        
        Example:
            try:
                org = await repo.create(name="Test")
                user = await repo.create(...)  # Fails due to constraint
            except ConflictError:
                await repo.rollback()  # Undo the org creation too
        
        Raises:
            RepositoryError: If rollback fails
        """
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
