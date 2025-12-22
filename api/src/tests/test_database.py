"""Test database connection management and session handling."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text

from app.core.database import (
    create_engine,
    get_db,
    check_database_connection,
    close_database,
    engine,
    async_session_maker,
)


class TestCreateEngine:
    """Test create_engine() function."""
    
    def test_create_engine_success(self) -> None:
        """Test successful engine creation with valid config."""
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.database_pool_size = 20
            mock_settings.database_max_overflow = 10
            
            with patch("app.core.database.create_async_engine") as mock_create:
                mock_async_engine = MagicMock(spec=AsyncEngine)
                mock_create.return_value = mock_async_engine
                
                result = create_engine()
                
                assert result is mock_async_engine
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["pool_size"] == 20
                assert call_kwargs["max_overflow"] == 10
                assert call_kwargs["pool_pre_ping"] is True
                assert call_kwargs["pool_recycle"] == 3600
    
    def test_create_engine_missing_database_url(self) -> None:
        """Test engine creation fails with missing DATABASE_URL."""
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = ""
            
            with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
                create_engine()
    
    def test_create_engine_invalid_pool_size(self) -> None:
        """Test engine creation fails with invalid pool size."""
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://localhost/db"
            mock_settings.database_pool_size = 0
            
            with pytest.raises(ValueError, match="DATABASE_POOL_SIZE must be at least 1"):
                create_engine()
    
    def test_create_engine_negative_max_overflow(self) -> None:
        """Test engine creation fails with negative max_overflow."""
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://localhost/db"
            mock_settings.database_pool_size = 20
            mock_settings.database_max_overflow = -1
            
            with pytest.raises(ValueError, match="DATABASE_MAX_OVERFLOW must be non-negative"):
                create_engine()
    
    def test_create_engine_unexpected_error_masked(self) -> None:
        """Test that unexpected errors during engine creation are masked."""
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://localhost/db"
            mock_settings.database_pool_size = 20
            mock_settings.database_max_overflow = 10
            
            with patch("app.core.database.create_async_engine") as mock_create:
                mock_create.side_effect = RuntimeError("Unexpected DB driver error")
                
                with pytest.raises(ValueError, match="Failed to create database engine"):
                    create_engine()


class TestCheckDatabaseConnection:
    """Test check_database_connection() function."""
    
    @pytest.mark.asyncio
    async def test_check_connection_success(self) -> None:
        """Test successful database connection check."""
        with patch("app.core.database.engine") as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_conn)
            async_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = MagicMock(return_value=async_context)
            
            result = await check_database_connection()
            
            assert result is True
            mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(self) -> None:
        """Test database connection check with connection failure."""
        with patch("app.core.database.engine") as mock_engine:
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(
                side_effect=ConnectionError("Cannot connect to database")
            )
            async_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = MagicMock(return_value=async_context)
            
            result = await check_database_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_connection_timeout(self) -> None:
        """Test database connection check with timeout."""
        with patch("app.core.database.engine") as mock_engine:
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(
                side_effect=TimeoutError("Connection timeout")
            )
            async_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = MagicMock(return_value=async_context)
            
            result = await check_database_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_connection_generic_exception(self) -> None:
        """Test database connection check with generic exception."""
        with patch("app.core.database.engine") as mock_engine:
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            async_context.__aexit__ = AsyncMock(return_value=None)
            mock_engine.begin = MagicMock(return_value=async_context)
            
            result = await check_database_connection()
            
            assert result is False


class TestGetDb:
    """Test get_db() async generator dependency."""
    
    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        """Test that get_db yields a session object."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_maker = MagicMock(return_value=mock_session)
        
        with patch("app.core.database.async_session_maker", mock_session_maker):
            async for db in get_db():
                assert db is mock_session
                break
    
    @pytest.mark.asyncio
    async def test_get_db_uses_async_context_manager(self) -> None:
        """Test that get_db properly uses async context manager."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_maker = MagicMock(return_value=mock_session)
        
        with patch("app.core.database.async_session_maker", mock_session_maker):
            # Consume the generator normally
            async for db in get_db():
                assert db is mock_session
                break
            
            # Verify session maker was called once
            mock_session_maker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_db_normal_completion(self) -> None:
        """Test that session completes normally without errors."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_maker = MagicMock(return_value=mock_session)
        
        with patch("app.core.database.async_session_maker", mock_session_maker):
            # Normal iteration without exceptions
            received_session = None
            async for db in get_db():
                received_session = db
                break
            
            assert received_session is mock_session
            # Verify session maker was called
            mock_session_maker.assert_called_once()


class TestCloseDatabase:
    """Test close_database() function."""
    
    @pytest.mark.asyncio
    async def test_close_database_success(self) -> None:
        """Test successful database closure."""
        with patch("app.core.database.engine") as mock_engine:
            mock_engine.dispose = AsyncMock()
            
            await close_database()
            
            mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_database_failure(self) -> None:
        """Test database closure with connection disposal error."""
        with patch("app.core.database.engine") as mock_engine:
            mock_engine.dispose = AsyncMock(
                side_effect=Exception("Disposal error")
            )
            
            with pytest.raises(RuntimeError, match="Failed to close database connections"):
                await close_database()
    
    @pytest.mark.asyncio
    async def test_close_database_connection_error(self) -> None:
        """Test database closure with connection error."""
        with patch("app.core.database.engine") as mock_engine:
            mock_engine.dispose = AsyncMock(
                side_effect=ConnectionError("Already disconnected")
            )
            
            with pytest.raises(RuntimeError, match="Failed to close database connections"):
                await close_database()


class TestEngineInitialization:
    """Test that engine is properly initialized at module load."""
    
    def test_engine_instance_created(self) -> None:
        """Test that engine instance is created at module load."""
        assert engine is not None
        assert isinstance(engine, AsyncEngine)
    
    def test_async_session_maker_created(self) -> None:
        """Test that async_session_maker is properly configured."""
        assert async_session_maker is not None
        # Verify that the session maker is bound to the engine
        assert async_session_maker.kw.get("expire_on_commit") is False
        assert async_session_maker.kw.get("autocommit") is False
        assert async_session_maker.kw.get("autoflush") is False
        # Verify that the session maker is bound to an engine
        assert async_session_maker.kw.get("bind") is not None
        assert isinstance(async_session_maker.kw.get("bind"), AsyncEngine)
