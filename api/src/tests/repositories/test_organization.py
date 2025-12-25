"""Tests for OrganizationRepository composition pattern.

Tests verify:
- Composition pattern implementation
- Proper delegation to BaseRepository
- Organization-specific functionality
- UUID string conversion handling
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.base import PaginatedResult, PaginationParams
from app.repositories.organization import OrganizationRepository


class TestOrganizationRepository:
    """Test OrganizationRepository composition pattern."""

    @pytest.mark.asyncio
    async def test_init_creates_base_repository(self) -> None:
        """Test initialization creates BaseRepository instance."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        assert repo._base is not None
        assert repo._base.model == Organization
        assert repo._base.db == mock_db

    @pytest.mark.asyncio
    async def test_create_delegates_to_base(self) -> None:
        """Test create delegates to BaseRepository.create."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        mock_org = MagicMock(spec=Organization)
        mock_org.id = uuid.uuid4()
        mock_org.name = "test-org"

        with patch.object(repo._base, "create", return_value=mock_org) as mock_create:
            org_data = {"name": "test-org"}
            result = await repo.create(org_data)

            mock_create.assert_called_once_with(org_data)
            assert result == mock_org

    @pytest.mark.asyncio
    async def test_get_with_uuid_string(self) -> None:
        """Test get accepts UUID string and converts it."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        test_id = uuid.uuid4()
        mock_org = MagicMock(spec=Organization)
        mock_org.id = test_id

        with patch.object(repo._base, "get", return_value=mock_org) as mock_get:
            result = await repo.get(str(test_id))

            mock_get.assert_called_once()
            assert result == mock_org

    @pytest.mark.asyncio
    async def test_get_with_uuid_object(self) -> None:
        """Test get accepts UUID object directly."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        test_id = uuid.uuid4()
        mock_org = MagicMock(spec=Organization)

        with patch.object(repo._base, "get", return_value=mock_org) as mock_get:
            result = await repo.get(test_id)

            mock_get.assert_called_once()
            assert result == mock_org

    @pytest.mark.asyncio
    async def test_get_include_deleted(self) -> None:
        """Test get passes include_deleted parameter."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        test_id = uuid.uuid4()

        with patch.object(repo._base, "get", return_value=None) as mock_get:
            await repo.get(str(test_id), include_deleted=True)

            mock_get.assert_called_once_with(test_id, True)

    @pytest.mark.asyncio
    async def test_update_delegates_to_base(self) -> None:
        """Test update delegates to BaseRepository.update."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        test_id = uuid.uuid4()
        update_data = {"name": "updated-org"}
        mock_org = MagicMock(spec=Organization)

        with patch.object(repo._base, "update", return_value=mock_org) as mock_update:
            result = await repo.update(str(test_id), update_data)

            mock_update.assert_called_once()
            assert result == mock_org

    @pytest.mark.asyncio
    async def test_delete_delegates_to_base(self) -> None:
        """Test delete delegates to BaseRepository.delete."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        test_id = uuid.uuid4()

        with patch.object(repo._base, "delete", return_value=True) as mock_delete:
            result = await repo.delete(str(test_id))

            mock_delete.assert_called_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_list_delegates_to_base(self) -> None:
        """Test list delegates to BaseRepository.list."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        pagination = PaginationParams(offset=10, limit=20)
        mock_result = PaginatedResult[Organization](
            items=[],
            total=50,
            offset=10,
            limit=20,
        )

        with patch.object(repo._base, "list", return_value=mock_result) as mock_list:
            result = await repo.list(pagination, include_deleted=False)

            mock_list.assert_called_once_with(pagination, False)
            assert result == mock_result

    @pytest.mark.asyncio
    async def test_list_default_pagination(self) -> None:
        """Test list with default pagination."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        mock_result = PaginatedResult[Organization](
            items=[],
            total=0,
            offset=0,
            limit=10,
        )

        with patch.object(repo._base, "list", return_value=mock_result) as mock_list:
            result = await repo.list()

            mock_list.assert_called_once_with(None, False)
            assert result == mock_result

    @pytest.mark.asyncio
    async def test_commit_delegates_to_base(self) -> None:
        """Test commit delegates to BaseRepository.commit."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        with patch.object(repo._base, "commit") as mock_commit:
            await repo.commit()

            mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_delegates_to_base(self) -> None:
        """Test rollback delegates to BaseRepository.rollback."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        with patch.object(repo._base, "rollback") as mock_rollback:
            await repo.rollback()

            mock_rollback.assert_called_once()


class TestOrganizationRepositoryIntegration:
    """Integration tests for OrganizationRepository composition."""

    @pytest.mark.asyncio
    async def test_complete_crud_workflow(self) -> None:
        """Test complete CRUD workflow with composition pattern."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        # Mock all base repository methods
        test_id = uuid.uuid4()
        mock_org = MagicMock(spec=Organization)
        mock_org.id = test_id
        mock_org.name = "test-org"

        with patch.object(repo._base, "create", return_value=mock_org):
            with patch.object(repo._base, "get", return_value=mock_org):
                with patch.object(repo._base, "update", return_value=mock_org):
                    with patch.object(repo._base, "delete", return_value=True):
                        with patch.object(repo._base, "commit"):
                            # Create
                            created = await repo.create({"name": "test-org"})
                            assert created == mock_org

                            # Get
                            retrieved = await repo.get(str(test_id))
                            assert retrieved == mock_org

                            # Update
                            updated = await repo.update(str(test_id), {"name": "updated"})
                            assert updated == mock_org

                            # Delete
                            deleted = await repo.delete(str(test_id))
                            assert deleted is True

                            # Commit
                            await repo.commit()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self) -> None:
        """Test transaction rollback on error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = OrganizationRepository(mock_db)

        with patch.object(repo._base, "create", side_effect=Exception("error")):
            with patch.object(repo._base, "rollback") as mock_rollback:
                try:
                    await repo.create({"name": "test"})
                except Exception:
                    await repo.rollback()
                    mock_rollback.assert_called_once()
