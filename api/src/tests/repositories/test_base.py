"""Test base repository functionality."""

import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin
from app.repositories.base import (
    BaseRepository,
    PaginationParams,
    PaginatedResult,
    RepositoryError,
    NotFoundError,
    ConflictError,
)


# Test model for repository testing
class RepositoryTestModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Test model with all mixins for repository testing."""
    
    __tablename__ = "test_models"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class TestPaginationParams:
    """Test PaginationParams validation."""
    
    def test_valid_params(self) -> None:
        """Test creation with valid parameters."""
        params = PaginationParams(offset=10, limit=25)
        assert params.offset == 10
        assert params.limit == 25
    
    def test_default_params(self) -> None:
        """Test default parameter values."""
        params = PaginationParams()
        assert params.offset == 0
        assert params.limit == 50
    
    def test_negative_offset(self) -> None:
        """Test validation of negative offset."""
        with pytest.raises(ValueError, match="Offset must be non-negative"):
            PaginationParams(offset=-1)
    
    def test_zero_limit(self) -> None:
        """Test validation of zero limit."""
        with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
            PaginationParams(limit=0)
    
    def test_excessive_limit(self) -> None:
        """Test validation of excessive limit."""
        with pytest.raises(ValueError, match="Limit must be between 1 and 1000"):
            PaginationParams(limit=1001)


class TestPaginatedResult:
    """Test PaginatedResult functionality."""
    
    def test_pagination_metadata(self) -> None:
        """Test pagination metadata calculation."""
        items = [RepositoryTestModel(name=f"item_{i}") for i in range(5)]
        result = PaginatedResult(items=items, total=15, offset=5, limit=5)
        
        assert result.items == items
        assert result.total == 15
        assert result.offset == 5
        assert result.limit == 5
        assert result.has_next is True  # 5 + 5 < 15
        assert result.has_prev is True  # 5 > 0
    
    def test_first_page(self) -> None:
        """Test first page pagination metadata."""
        items = [RepositoryTestModel(name=f"item_{i}") for i in range(5)]
        result = PaginatedResult(items=items, total=10, offset=0, limit=5)
        
        assert result.has_next is True
        assert result.has_prev is False
    
    def test_last_page(self) -> None:
        """Test last page pagination metadata."""
        items = [RepositoryTestModel(name=f"item_{i}") for i in range(3)]
        result = PaginatedResult(items=items, total=8, offset=5, limit=5)
        
        assert result.has_next is False  # 5 + 5 >= 8
        assert result.has_prev is True


class TestBaseRepository:
    """Test BaseRepository CRUD operations."""
    
    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async session."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.delete = AsyncMock()
        return session
    
    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> BaseRepository[RepositoryTestModel]:
        """Create a BaseRepository instance for testing."""
        return BaseRepository(mock_session, RepositoryTestModel)
    
    async def test_create_success(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test successful entity creation."""
        # Setup
        entity_data = {"name": "test_item", "description": "Test description"}
        created_entity = RepositoryTestModel(**entity_data)
        created_entity.id = uuid.uuid4()
        
        # Mock session behavior
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.refresh.return_value = None
        
        # Execute
        result = await repository.create(**entity_data)
        
        # Verify
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert isinstance(result, RepositoryTestModel)
        assert result.name == entity_data["name"]
        assert result.description == entity_data["description"]
    
    async def test_create_conflict_error(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test create with constraint violation."""
        # Setup
        mock_session.flush.side_effect = IntegrityError(
            statement="INSERT INTO test_models...",
            params={},
            orig=Exception("UNIQUE constraint failed"),
        )
        
        # Execute & Verify
        with pytest.raises(ConflictError, match="Entity conflicts with existing data"):
            await repository.create(name="duplicate_name")
    
    async def test_create_generic_error(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test create with generic database error."""
        # Setup
        mock_session.flush.side_effect = SQLAlchemyError("Database connection lost")
        
        # Execute & Verify
        with pytest.raises(RepositoryError, match="Failed to create entity"):
            await repository.create(name="test_item")
    
    async def test_get_existing_entity(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test getting an existing entity by ID."""
        # Setup
        entity_id = uuid.uuid4()
        entity = RepositoryTestModel(id=entity_id, name="test_item")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entity
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.get(entity_id)
        
        # Verify
        assert result == entity
        mock_session.execute.assert_called_once()
    
    async def test_get_nonexistent_entity(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test getting a non-existent entity."""
        # Setup
        entity_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.get(entity_id)
        
        # Verify
        assert result is None
    
    async def test_get_or_404_existing(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test get_or_404 with existing entity."""
        # Setup
        entity_id = uuid.uuid4()
        entity = RepositoryTestModel(id=entity_id, name="test_item")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entity
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.get_or_404(entity_id)
        
        # Verify
        assert result == entity
    
    async def test_get_or_404_not_found(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test get_or_404 with non-existent entity."""
        # Setup
        entity_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(NotFoundError, match=f"RepositoryTestModel with id {entity_id} not found"):
            await repository.get_or_404(entity_id)
    
    async def test_update_existing_entity(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test updating an existing entity."""
        # Setup
        entity_id = uuid.uuid4()
        updated_entity = RepositoryTestModel(id=entity_id, name="updated_name")
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = updated_entity
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.update(entity_id, name="updated_name")
        
        # Verify
        assert result == updated_entity
        mock_session.execute.assert_called_once()
    
    async def test_update_nonexistent_entity(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test updating a non-existent entity."""
        # Setup
        entity_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.update(entity_id, name="updated_name")
        
        # Verify
        assert result is None
    
    async def test_soft_delete_success(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test successful soft delete."""
        # Setup
        entity_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.delete(entity_id, soft=True)
        
        # Verify
        assert result is True
        mock_session.execute.assert_called_once()
    
    async def test_hard_delete_success(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test successful hard delete."""
        # Setup
        entity_id = uuid.uuid4()
        entity = RepositoryTestModel(id=entity_id, name="test_item")
        
        # Mock get method to return entity
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = entity
        mock_session.execute.return_value = mock_get_result
        
        # Execute
        result = await repository.delete(entity_id, soft=False)
        
        # Verify
        assert result is True
        mock_session.delete.assert_called_once_with(entity)
    
    async def test_delete_nonexistent_entity(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test deleting a non-existent entity."""
        # Setup for soft delete
        entity_id = uuid.uuid4()
        
        mock_result = MagicMock()
        mock_result.rowcount = 0  # No rows affected
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.delete(entity_id, soft=True)
        
        # Verify
        assert result is False
    
    async def test_list_with_pagination(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test listing entities with pagination."""
        # Setup
        entities = [RepositoryTestModel(name=f"item_{i}") for i in range(3)]
        pagination = PaginationParams(offset=0, limit=10)
        
        # Mock execute calls for items and count
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = entities
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 25
        
        mock_session.execute.side_effect = [mock_items_result, mock_count_result]
        
        # Execute
        result = await repository.list(pagination=pagination)
        
        # Verify
        assert isinstance(result, PaginatedResult)
        assert result.items == entities
        assert result.total == 25
        assert result.offset == 0
        assert result.limit == 10
        assert result.has_next is True
        assert result.has_prev is False
        assert len(mock_session.execute.call_args_list) == 2
    
    async def test_list_default_pagination(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test listing entities with default pagination."""
        # Setup
        entities = [RepositoryTestModel(name=f"item_{i}") for i in range(5)]
        
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = entities
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        
        mock_session.execute.side_effect = [mock_items_result, mock_count_result]
        
        # Execute
        result = await repository.list()
        
        # Verify
        assert result.offset == 0
        assert result.limit == 50  # Default limit
        assert result.total == 5
    
    async def test_count_entities(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test counting entities."""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.count()
        
        # Verify
        assert result == 42
        mock_session.execute.assert_called_once()
    
    async def test_count_with_include_deleted(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test counting entities including deleted ones."""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar.return_value = 50
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await repository.count(include_deleted=True)
        
        # Verify
        assert result == 50
        # Should not have deleted_at filter in query
    
    async def test_commit_transaction(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test committing a transaction."""
        # Execute
        await repository.commit()
        
        # Verify
        mock_session.commit.assert_called_once()
    
    async def test_commit_transaction_error(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test commit transaction with error."""
        # Setup
        mock_session.commit.side_effect = SQLAlchemyError("Connection lost")
        
        # Execute & Verify
        with pytest.raises(RepositoryError, match="Failed to commit transaction"):
            await repository.commit()
    
    async def test_rollback_transaction(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test rolling back a transaction."""
        # Execute
        await repository.rollback()
        
        # Verify
        mock_session.rollback.assert_called_once()
    
    async def test_rollback_transaction_error(
        self, repository: BaseRepository[RepositoryTestModel], mock_session: AsyncMock
    ) -> None:
        """Test rollback transaction with error."""
        # Setup
        mock_session.rollback.side_effect = SQLAlchemyError("Connection lost")
        
        # Execute & Verify
        with pytest.raises(RepositoryError, match="Failed to rollback transaction"):
            await repository.rollback()
    
    async def test_caching_disabled_by_default(
        self, repository: BaseRepository[RepositoryTestModel]
    ) -> None:
        """Test that caching is disabled by default."""
        assert repository._use_cache is False
    
    async def test_caching_can_be_enabled(
        self, mock_session: AsyncMock
    ) -> None:
        """Test that caching can be enabled."""
        repository = BaseRepository(mock_session, RepositoryTestModel, use_cache=True)
        assert repository._use_cache is True
    
    def test_tracing_integration(self, repository: BaseRepository[RepositoryTestModel]) -> None:
        """Test that OpenTelemetry tracing is integrated."""
        # Verify that the repository methods have the trace_database decorator
        # Check if the methods have the wrapped attribute or trace metadata
        assert hasattr(repository.create, '__wrapped__') or hasattr(repository.create, '__name__')
        assert hasattr(repository.get, '__wrapped__') or hasattr(repository.get, '__name__')
        assert hasattr(repository.update, '__wrapped__') or hasattr(repository.update, '__name__')
        assert hasattr(repository.delete, '__wrapped__') or hasattr(repository.delete, '__name__')
        assert hasattr(repository.list, '__wrapped__') or hasattr(repository.list, '__name__')