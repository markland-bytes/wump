"""Example usage of BaseRepository with Organization model."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.base import BaseRepository, PaginationParams


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization entities with custom methods."""
    
    def __init__(self, session: AsyncSession, use_cache: bool = False) -> None:
        super().__init__(session, Organization, use_cache=use_cache)
    
    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name.
        
        Args:
            name: Organization name to search for
            
        Returns:
            Organization instance or None if not found
        """
        from sqlalchemy import select
        
        try:
            query = select(Organization).where(
                Organization.name == name,
                Organization.deleted_at.is_(None)  # Exclude soft-deleted
            )
            
            result = await self._session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self._logger.error(
                "Failed to get organization by name",
                name=name,
                error=str(e)
            )
            return None


# Example usage in FastAPI endpoints:
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

@app.post("/organizations/", response_model=OrganizationSchema)
async def create_organization(
    org_data: CreateOrganizationSchema,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    
    try:
        async with db.begin():  # Transaction context
            organization = await repo.create(
                name=org_data.name,
                github_url=org_data.github_url,
                description=org_data.description
            )
            await repo.commit()
            return organization
            
    except ConflictError:
        raise HTTPException(
            status_code=409,
            detail="Organization with this name already exists"
        )
    except RepositoryError as e:
        await repo.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/organizations/{org_id}")
async def get_organization(
    org_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    organization = await repo.get_or_404(org_id)
    return organization


@app.get("/organizations/")
async def list_organizations(
    offset: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
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


@app.put("/organizations/{org_id}")
async def update_organization(
    org_id: UUID,
    org_data: UpdateOrganizationSchema,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    
    try:
        async with db.begin():
            updated_org = await repo.update(org_id, **org_data.dict(exclude_unset=True))
            if updated_org is None:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            await repo.commit()
            return updated_org
            
    except RepositoryError as e:
        await repo.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: UUID,
    hard_delete: bool = False,
    db: AsyncSession = Depends(get_db)
):
    repo = OrganizationRepository(db)
    
    try:
        async with db.begin():
            deleted = await repo.delete(org_id, soft=not hard_delete)
            if not deleted:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            await repo.commit()
            return {"message": "Organization deleted successfully"}
            
    except RepositoryError as e:
        await repo.rollback()
        raise HTTPException(status_code=500, detail=str(e))
"""