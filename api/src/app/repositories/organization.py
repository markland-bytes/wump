"""Organization repository with composition-based architecture.

This repository demonstrates the composition pattern instead of inheritance.
Composition provides better separation of concerns, explicit delegation,
and aligns with FastAPI's dependency injection patterns.

Benefits of Composition:
- Explicit method delegation (no magic __getattr__)
- Better testability and mocking
- Clearer intent and easier to understand
- Can compose multiple concerns (e.g., caching, logging)
- Easier to extend with cross-cutting concerns

Example Usage:
    async def create_organization(
        org_data: OrganizationCreate,
        db: AsyncSession = Depends(get_db)
    ):
        repo = OrganizationRepository(db)
        org = await repo.create(org_data.dict())
        await repo.commit()
        return org
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.base import BaseRepository, PaginatedResult, PaginationParams


class OrganizationRepository:
    """Repository for Organization model using composition pattern.
    
    This repository wraps BaseRepository and delegates CRUD operations.
    The composition approach provides better separation of concerns and
    makes it easier to add organization-specific methods.
    
    Attributes:
        _base: BaseRepository instance for Organization model
    
    Example:
        repo = OrganizationRepository(db_session)
        
        # Create
        org = await repo.create({"name": "my-org"})
        
        # Get
        org = await repo.get(org_id)
        
        # Update
        org = await repo.update(org_id, {"name": "new-name"})
        
        # Delete (soft delete if model has deleted_at)
        deleted = await repo.delete(org_id)
        
        # List with pagination
        result = await repo.list(PaginationParams(offset=0, limit=10))
        
        # Commit transaction
        await repo.commit()
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self._base = BaseRepository(Organization, db)

    async def create(self, data: dict[str, Any]) -> Organization:
        """Create a new organization.
        
        Args:
            data: Dictionary with organization fields
        
        Returns:
            Created Organization instance
        """
        return await self._base.create(data)

    async def get(self, org_id: str, include_deleted: bool = False) -> Organization | None:
        """Get an organization by ID.
        
        Args:
            org_id: Organization UUID
            include_deleted: Include soft-deleted organizations
        
        Returns:
            Organization instance or None if not found
        """
        from uuid import UUID
        return await self._base.get(UUID(org_id) if isinstance(org_id, str) else org_id, include_deleted)

    async def update(self, org_id: str, data: dict[str, Any]) -> Organization | None:
        """Update an organization.
        
        Args:
            org_id: Organization UUID
            data: Dictionary with fields to update
        
        Returns:
            Updated Organization instance or None if not found
        """
        from uuid import UUID
        return await self._base.update(UUID(org_id) if isinstance(org_id, str) else org_id, data)

    async def delete(self, org_id: str) -> bool:
        """Delete an organization.
        
        Args:
            org_id: Organization UUID
        
        Returns:
            True if deleted, False if not found
        """
        from uuid import UUID
        return await self._base.delete(UUID(org_id) if isinstance(org_id, str) else org_id)

    async def list(
        self,
        pagination: PaginationParams | None = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[Organization]:
        """List organizations with pagination.
        
        Args:
            pagination: Pagination parameters
            include_deleted: Include soft-deleted organizations
        
        Returns:
            PaginatedResult with organizations and metadata
        """
        return await self._base.list(pagination, include_deleted)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._base.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._base.rollback()
