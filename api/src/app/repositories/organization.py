"""Repository for Organization entities with custom CRUD operations."""

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
    
    Delegates standard CRUD operations to BaseRepository while providing
    custom organization-specific methods.
    
    Args:
        session: Async SQLAlchemy session
        use_cache: Enable/disable caching (default: False)
    """
    
    def __init__(self, session: AsyncSession, use_cache: bool = False) -> None:
        self._session = session
        self._base_repo = BaseRepository(session, Organization, use_cache=use_cache)
        self._logger = get_logger(f"{__name__}.OrganizationRepository")
    
    # ========== DELEGATED CRUD METHODS ==========
    
    async def create(self, **kwargs: Any) -> Organization:
        """Create a new organization.
        
        Args:
            **kwargs: Organization attributes
            
        Returns:
            Created organization instance
            
        Raises:
            ConflictError: If organization conflicts with existing data
            RepositoryError: For other database errors
        """
        return await self._base_repo.create(**kwargs)
    
    async def get(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        include_deleted: bool = False
    ) -> Optional[Organization]:
        """Get organization by ID.
        
        Args:
            entity_id: Organization identifier
            include_deleted: Include soft-deleted organizations
            
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
        
        Args:
            entity_id: Organization identifier
            include_deleted: Include soft-deleted organizations
            
        Returns:
            Organization instance
            
        Raises:
            NotFoundError: If organization not found
            RepositoryError: For database errors
        """
        return await self._base_repo.get_or_404(entity_id, include_deleted=include_deleted)
    
    async def update(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        **kwargs: Any
    ) -> Optional[Organization]:
        """Update organization by ID.
        
        Args:
            entity_id: Organization identifier
            **kwargs: Attributes to update
            
        Returns:
            Updated organization instance or None if not found
            
        Raises:
            ConflictError: If update conflicts with existing data
            RepositoryError: For other database errors
        """
        return await self._base_repo.update(entity_id, **kwargs)
    
    async def delete(
        self, 
        entity_id: Union[uuid.UUID, str, int], 
        soft: bool = True
    ) -> bool:
        """Delete organization by ID.
        
        Args:
            entity_id: Organization identifier
            soft: Use soft delete (default) or hard delete
            
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
        """List organizations with pagination.
        
        Args:
            pagination: Pagination parameters (default: offset=0, limit=50)
            include_deleted: Include soft-deleted organizations
            
        Returns:
            Paginated result with organizations and metadata
            
        Raises:
            RepositoryError: For database errors
        """
        return await self._base_repo.list(
            pagination=pagination, 
            include_deleted=include_deleted
        )
    
    async def count(self, include_deleted: bool = False) -> int:
        """Count total organizations.
        
        Args:
            include_deleted: Include soft-deleted organizations
            
        Returns:
            Total count of organizations
            
        Raises:
            RepositoryError: For database errors
        """
        return await self._base_repo.count(include_deleted=include_deleted)
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        return await self._base_repo.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        return await self._base_repo.rollback()
    
    # ========== CUSTOM ORGANIZATION METHODS ==========
    
    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name (case-sensitive).
        
        Args:
            name: Organization name to search for
            
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
            
            query = select(Organization).where(
                Organization.name == name,
                Organization.deleted_at.is_(None)  # Exclude soft-deleted
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