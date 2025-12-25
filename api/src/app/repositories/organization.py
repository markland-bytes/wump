from typing import Any, Optional, Union
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.organization import Organization
from app.repositories.base import (
    BaseRepository,
    PaginationParams,
    PaginatedResult,
    RepositoryError,
)

logger = get_logger(__name__)


class OrganizationRepository:
    """Repository for Organization entities using composition pattern.
    
    This class demonstrates how to build entity-specific repositories using
    composition. Standard CRUD operations are delegated to BaseRepository[Organization],
    while custom organization-specific methods can be added.
    """
    
    def __init__(self, session: AsyncSession, use_cache: bool = False) -> None:
        """Initialize OrganizationRepository with a database session.
        
        Args:
            session: Async SQLAlchemy session
            use_cache: Enable caching for queries (prepared for future use)
        """
        self._session = session
        # COMPOSITION: Inject BaseRepository as dependency, not inheritance
        self._base_repo = BaseRepository(session, Organization, use_cache=use_cache)
        self._logger = get_logger(f"{__name__}.OrganizationRepository")
    
    # ========================================================================
    # DELEGATED CRUD METHODS
    # ========================================================================
    # These methods delegate to BaseRepository[Organization]. While they look
    # like boilerplate, explicit delegation provides clarity and testability.
    # In tests, we can mock _base_repo and verify behavior independently.
    #
    
    async def create(self, **kwargs: Any) -> Organization:
        """Create a new organization.
        
        Delegates to BaseRepository. All arguments are passed through to the
        Organization model constructor via SQLAlchemy.
        
        Args:
            **kwargs: Organization attributes (e.g., name="My Org", slug="my-org")
            
        Returns:
            Created Organization instance with auto-generated ID
            
        Raises:
            ConflictError: If organization name/slug conflicts with existing
            RepositoryError: For other database errors
        """
        return await self._base_repo.create(**kwargs)
    
    async def get(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> Optional[Organization]:
        """Get organization by ID.
        
        Delegates to BaseRepository. Soft-deleted organizations are excluded
        unless include_deleted=True.
        
        Args:
            entity_id: Organization UUID, string, or integer ID
            include_deleted: If True, include soft-deleted organizations
            
        Returns:
            Organization instance or None if not found
            
        Raises:
            RepositoryError: For database errors
        """
        return await self._base_repo.get(entity_id, include_deleted=include_deleted)
    
    async def get_or_404(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> Organization:
        """Get organization by ID or raise NotFoundError.
        
        Delegates to BaseRepository. Raises NotFoundError (subclass of
        RepositoryError) if organization not found. Useful for API endpoints
        that should return 404 responses.
        
        Args:
            entity_id: Organization UUID, string, or integer ID
            include_deleted: If True, include soft-deleted organizations
            
        Returns:
            Organization instance
            
        Raises:
            NotFoundError: If organization not found
            RepositoryError: For other database errors
        """
        return await self._base_repo.get_or_404(entity_id, include_deleted=include_deleted)
    
    async def update(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        **kwargs: Any
    ) -> Optional[Organization]:
        """Update organization by ID.
        
        Delegates to BaseRepository. Automatically adds updated_at timestamp.
        Returns None if organization not found.
        
        Args:
            entity_id: Organization UUID, string, or integer ID
            **kwargs: Attributes to update (e.g., name="New Name", slug="new-slug")
            
        Returns:
            Updated Organization instance or None if not found
            
        Raises:
            ConflictError: If update conflicts with constraints (unique keys, etc)
            RepositoryError: For other database errors
        """
        return await self._base_repo.update(entity_id, **kwargs)
    
    async def delete(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        soft: bool = True
    ) -> bool:
        """Delete organization by ID (soft or hard).
        
        Delegates to BaseRepository.
        
        Soft Delete (default, recommended):
            Sets deleted_at timestamp. Organization remains in database but is
            hidden from normal queries. Can be restored by clearing deleted_at.
        
        Hard Delete (permanent):
            Removes organization from database permanently. Use with caution!
        
        Args:
            entity_id: Organization UUID, string, or integer ID
            soft: If True, soft delete; if False, permanent hard delete
            
        Returns:
            True if organization was deleted, False if not found
            
        Raises:
            RepositoryError: For database errors
        """
        return await self._base_repo.delete(entity_id, soft=soft)
    
    async def list(
        self, 
        pagination: Optional[PaginationParams] = None,
        include_deleted: bool = False
    ) -> PaginatedResult[Organization]:
        """List organizations with offset/limit pagination.
        
        Delegates to BaseRepository. Returns paginated results with metadata
        for building pagination UI (has_next, has_prev, etc).
        
        Results are ordered by created_at (descending) - newest first.
        
        Args:
            pagination: PaginationParams with offset/limit (default: 0, 50)
            include_deleted: If True, include soft-deleted organizations
            
        Returns:
            PaginatedResult with organizations and pagination metadata
            
        Raises:
            RepositoryError: For database errors
        """
        return await self._base_repo.list(
            pagination=pagination, 
            include_deleted=include_deleted
        )
    
    async def count(self, include_deleted: bool = False) -> int:
        """Count total organizations.
        
        Delegates to BaseRepository. Returns count of all organizations,
        excluding soft-deleted by default.
        
        Args:
            include_deleted: If True, include soft-deleted organizations in count
            
        Returns:
            Total count of organizations
            
        Raises:
            RepositoryError: For database errors
        """
        return await self._base_repo.count(include_deleted=include_deleted)
    
    async def commit(self) -> None:
        """Commit the current transaction.
        
        Persists all pending database changes. Use after create/update/delete
        operations when not using an async context manager.
        """
        return await self._base_repo.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction.
        
        Discards all pending changes since last commit. Use to undo operations
        after catching exceptions.
        """
        return await self._base_repo.rollback()
    
    # ========================================================================
    # CUSTOM ORGANIZATION METHODS
    # ========================================================================
    # These methods extend BaseRepository with organization-specific queries.
    # Unlike delegated methods, custom methods have custom SQL logic and
    # demonstrate how to add entity-specific functionality.
    #
    
    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name (case-sensitive).
        
        Args:
            name: Organization name to search for (case-sensitive)
            
        Returns:
            Organization instance or None if not found
            
        Raises:
            RepositoryError: For database errors
        """
        try:
            self._logger.debug(
                "Getting organization by name",
                name=name
            )

            exclude_soft_deleted = Organization.deleted_at.is_(None)
            query = select(Organization).where(
                Organization.name == name,
                exclude_soft_deleted
            )
            
            result = await self._session.execute(query)
            org = result.scalar_one_or_none()
            
            if org:
                self._logger.debug(
                    "Organization found by name",
                    name=name,
                    org_id=org.id
                )
            else:
                self._logger.debug(
                    "Organization not found by name",
                    name=name
                )
            
            return org
            
        except Exception as e:
            self._logger.error(
                "Failed to get organization by name",
                name=name,
                error=str(e)
            )
            raise RepositoryError(f"Failed to get organization by name: {e}") from e