"""Comprehensive tests for BaseRepository.

Test Coverage:
- CRUD operations (create, get, update, delete, list)
- Pagination validation and functionality
- Soft delete support
- Transaction management (commit, rollback)
- Error handling and custom exceptions
- OpenTelemetry tracing integration
- Edge cases and boundary conditions

Target: >95% code coverage
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import DateTime, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.repositories.base import (
    BaseRepository,
    DatabaseOperationError,
    PaginatedResult,
    PaginationParams,
    RecordAlreadyExistsError,
    RecordNotFoundError,
    RepositoryError,
    SoftDeleteMixin,
)


# Define Base here to avoid circular imports in tests
class Base(DeclarativeBase):
    """Base class for test models."""

    pass


class UUIDMixin:
    """Mixin for UUID primary key."""

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        """Primary key UUID."""
        return mapped_column(
            primary_key=True,
            default=uuid.uuid4,
        )


# Test model without soft delete
class TestModel(Base, UUIDMixin):
    """Test model for repository tests."""

    __tablename__ = "test_model"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)


# Test model with soft delete
class SoftDeleteTestModel(Base, UUIDMixin, SoftDeleteMixin):
    """Test model with soft delete support."""

    __tablename__ = "soft_delete_test_model"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TestPaginationParams:
    """Test PaginationParams validation."""

    def test_default_values(self) -> None:
        """Test default pagination values."""
        params = PaginationParams()
        assert params.offset == 0
        assert params.limit == 10

    def test_custom_values(self) -> None:
        """Test custom pagination values."""
        params = PaginationParams(offset=20, limit=50)
        assert params.offset == 20
        assert params.limit == 50

    def test_negative_offset_raises_error(self) -> None:
        """Test that negative offset raises ValueError."""
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            PaginationParams(offset=-1, limit=10)

    def test_zero_limit_raises_error(self) -> None:
        """Test that zero limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            PaginationParams(offset=0, limit=0)

    def test_negative_limit_raises_error(self) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            PaginationParams(offset=0, limit=-1)

    def test_limit_exceeds_max_raises_error(self) -> None:
        """Test that limit > 100 raises ValueError."""
        with pytest.raises(ValueError, match="Limit must not exceed 100"):
            PaginationParams(offset=0, limit=101)


class TestPaginatedResult:
    """Test PaginatedResult properties."""

    def test_has_next_true(self) -> None:
        """Test has_next when there are more pages."""
        result = PaginatedResult[TestModel](
            items=[],
            total=50,
            offset=0,
            limit=10,
        )
        assert result.has_next is True

    def test_has_next_false(self) -> None:
        """Test has_next when on last page."""
        result = PaginatedResult[TestModel](
            items=[],
            total=10,
            offset=0,
            limit=10,
        )
        assert result.has_next is False

    def test_has_prev_true(self) -> None:
        """Test has_prev when not on first page."""
        result = PaginatedResult[TestModel](
            items=[],
            total=50,
            offset=20,
            limit=10,
        )
        assert result.has_prev is True

    def test_has_prev_false(self) -> None:
        """Test has_prev when on first page."""
        result = PaginatedResult[TestModel](
            items=[],
            total=50,
            offset=0,
            limit=10,
        )
        assert result.has_prev is False

    def test_page_number(self) -> None:
        """Test page number calculation."""
        result = PaginatedResult[TestModel](
            items=[],
            total=50,
            offset=20,
            limit=10,
        )
        assert result.page == 3

    def test_total_pages(self) -> None:
        """Test total pages calculation."""
        result = PaginatedResult[TestModel](
            items=[],
            total=55,
            limit=10,
            offset=0,
        )
        assert result.total_pages == 6


class TestBaseRepositoryCreate:
    """Test BaseRepository.create() method."""

    @pytest.mark.asyncio
    async def test_create_success(self) -> None:
        """Test successful record creation."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()
        test_data = {"name": "test", "value": "value"}

        # Mock the model instance
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.id = test_id
        mock_instance.name = "test"

        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock the actual creation
        with patch.object(repo, "model", return_value=mock_instance) as mock_model:
            mock_model.__name__ = "TestModel"  # Add __name__ attribute
            result = await repo.create(test_data)

            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_unique_constraint_error(self) -> None:
        """Test create with unique constraint violation."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.flush = AsyncMock(
            side_effect=IntegrityError(
                "unique constraint", {}, Exception("duplicate key value")
            )
        )

        with pytest.raises(RecordAlreadyExistsError):
            await repo.create({"name": "test"})

    @pytest.mark.asyncio
    async def test_create_database_error(self) -> None:
        """Test create with generic database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.flush = AsyncMock(side_effect=Exception("database error"))

        with pytest.raises(DatabaseOperationError):
            await repo.create({"name": "test"})


class TestBaseRepositoryGet:
    """Test BaseRepository.get() method."""

    @pytest.mark.asyncio
    async def test_get_success(self) -> None:
        """Test successful record retrieval."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.id = test_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_instance)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.get(test_id)

        assert result == mock_instance
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_not_found(self) -> None:
        """Test get when record doesn't exist."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.get(test_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_soft_delete(self) -> None:
        """Test get filters soft-deleted records by default."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(SoftDeleteTestModel, mock_db)

        test_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.get(test_id, include_deleted=False)

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_database_error(self) -> None:
        """Test get with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()
        mock_db.execute = AsyncMock(side_effect=Exception("database error"))

        with pytest.raises(DatabaseOperationError):
            await repo.get(test_id)


class TestBaseRepositoryUpdate:
    """Test BaseRepository.update() method."""

    @pytest.mark.asyncio
    async def test_update_success(self) -> None:
        """Test successful record update."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()
        update_data = {"name": "updated"}

        # Mock get to return existing instance
        mock_instance = MagicMock(spec=TestModel)
        mock_instance.id = test_id
        mock_instance.name = "updated"

        with patch.object(repo, "get", return_value=mock_instance):
            mock_result = MagicMock()
            mock_result.scalar_one = MagicMock(return_value=mock_instance)
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await repo.update(test_id, update_data)

            assert result == mock_instance
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        """Test update when record doesn't exist."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()

        with patch.object(repo, "get", return_value=None):
            result = await repo.update(test_id, {"name": "updated"})

            assert result is None

    @pytest.mark.asyncio
    async def test_update_database_error(self) -> None:
        """Test update with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()
        mock_instance = MagicMock(spec=TestModel)

        with patch.object(repo, "get", return_value=mock_instance):
            mock_db.execute = AsyncMock(side_effect=Exception("database error"))

            with pytest.raises(DatabaseOperationError):
                await repo.update(test_id, {"name": "updated"})


class TestBaseRepositoryDelete:
    """Test BaseRepository.delete() method."""

    @pytest.mark.asyncio
    async def test_delete_hard_success(self) -> None:
        """Test successful hard delete."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.delete(test_id)

        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        """Test delete when record doesn't exist."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.delete(test_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_soft_success(self) -> None:
        """Test successful soft delete."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(SoftDeleteTestModel, mock_db)

        test_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await repo.delete(test_id)

        assert result is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_database_error(self) -> None:
        """Test delete with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        test_id = uuid.uuid4()
        mock_db.execute = AsyncMock(side_effect=Exception("database error"))

        with pytest.raises(DatabaseOperationError):
            await repo.delete(test_id)


class TestBaseRepositoryList:
    """Test BaseRepository.list() method."""

    @pytest.mark.asyncio
    async def test_list_success(self) -> None:
        """Test successful list with pagination."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_items = [MagicMock(spec=TestModel) for _ in range(5)]

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one = MagicMock(return_value=50)

        # Mock list query
        mock_list_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=mock_items)
        mock_list_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

        result = await repo.list(PaginationParams(offset=0, limit=10))

        assert len(result.items) == 5
        assert result.total == 50
        assert result.offset == 0
        assert result.limit == 10

    @pytest.mark.asyncio
    async def test_list_default_pagination(self) -> None:
        """Test list with default pagination."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one = MagicMock(return_value=0)

        mock_list_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_list_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

        result = await repo.list()

        assert result.offset == 0
        assert result.limit == 10

    @pytest.mark.asyncio
    async def test_list_with_soft_delete_filter(self) -> None:
        """Test list filters soft-deleted records by default."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(SoftDeleteTestModel, mock_db)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one = MagicMock(return_value=10)

        mock_list_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_list_result.scalars = MagicMock(return_value=mock_scalars)

        mock_db.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

        result = await repo.list(include_deleted=False)

        assert result.total == 10

    @pytest.mark.asyncio
    async def test_list_database_error(self) -> None:
        """Test list with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.execute = AsyncMock(side_effect=Exception("database error"))

        with pytest.raises(DatabaseOperationError):
            await repo.list()


class TestBaseRepositoryTransactions:
    """Test BaseRepository transaction management."""

    @pytest.mark.asyncio
    async def test_commit_success(self) -> None:
        """Test successful transaction commit."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.commit = AsyncMock()

        await repo.commit()

        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_error(self) -> None:
        """Test commit with database error."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.commit = AsyncMock(side_effect=Exception("commit failed"))

        with pytest.raises(DatabaseOperationError):
            await repo.commit()

    @pytest.mark.asyncio
    async def test_rollback_success(self) -> None:
        """Test successful transaction rollback."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.rollback = AsyncMock()

        await repo.rollback()

        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_error_suppressed(self) -> None:
        """Test rollback error is suppressed (doesn't raise)."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        mock_db.rollback = AsyncMock(side_effect=Exception("rollback failed"))

        # Should not raise
        await repo.rollback()

        mock_db.rollback.assert_called_once()


class TestTracingIntegration:
    """Test OpenTelemetry tracing integration."""

    @pytest.mark.asyncio
    async def test_create_with_tracing(self) -> None:
        """Test that create operation has tracing decorator."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        # Verify the method has the trace decorator
        assert hasattr(repo.create, "__wrapped__")

    @pytest.mark.asyncio
    async def test_get_with_tracing(self) -> None:
        """Test that get operation has tracing decorator."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        # Verify the method has the trace decorator
        assert hasattr(repo.get, "__wrapped__")

    @pytest.mark.asyncio
    async def test_update_with_tracing(self) -> None:
        """Test that update operation has tracing decorator."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        # Verify the method has the trace decorator
        assert hasattr(repo.update, "__wrapped__")

    @pytest.mark.asyncio
    async def test_delete_with_tracing(self) -> None:
        """Test that delete operation has tracing decorator."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        # Verify the method has the trace decorator
        assert hasattr(repo.delete, "__wrapped__")

    @pytest.mark.asyncio
    async def test_list_with_tracing(self) -> None:
        """Test that list operation has tracing decorator."""
        mock_db = AsyncMock(spec=AsyncSession)
        repo = BaseRepository(TestModel, mock_db)

        # Verify the method has the trace decorator
        assert hasattr(repo.list, "__wrapped__")
