"""Test Valkey/Redis cache connection management."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from redis.asyncio import Redis

from app.core.cache import (
    CacheErrorMessage,
    create_client,
    get_cache,
    check_cache_connection,
    close_cache,
    cache_client,
)


class TestCreateClient:
    """Test create_client() function."""

    def test_create_client_success(self) -> None:
        """Test successful client creation with valid config."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = "redis://localhost:6379/0"

            with patch("app.core.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock(spec=Redis)
                mock_from_url.return_value = mock_client

                result = create_client()

                assert result is mock_client
                mock_from_url.assert_called_once()
                call_kwargs = mock_from_url.call_args[1]
                assert call_kwargs["encoding"] == "utf-8"
                assert call_kwargs["decode_responses"] is True
                assert call_kwargs["max_connections"] == 20
                assert call_kwargs["socket_connect_timeout"] == 5
                assert call_kwargs["socket_keepalive"] is True
                assert call_kwargs["health_check_interval"] == 30

    def test_create_client_with_service_name(self) -> None:
        """Test client creation with docker-compose service name."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = "redis://valkey:6379/0"

            with patch("app.core.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock(spec=Redis)
                mock_from_url.return_value = mock_client

                result = create_client()

                assert result is mock_client
                # Verify the URL passed to from_url
                call_args = mock_from_url.call_args[0]
                assert "valkey" in call_args[0]

    def test_create_client_missing_valkey_url(self) -> None:
        """Test client creation fails with missing VALKEY_URL."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = ""

            with pytest.raises(ValueError, match=CacheErrorMessage.CREATE_CLIENT_NO_URL):
                create_client()

    def test_create_client_none_valkey_url(self) -> None:
        """Test client creation fails with None VALKEY_URL."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = None

            with pytest.raises(ValueError, match=CacheErrorMessage.CREATE_CLIENT_NO_URL):
                create_client()

    def test_create_client_unexpected_error_masked(self) -> None:
        """Test that unexpected errors during client creation are masked."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = "redis://localhost:6379/0"

            with patch("app.core.cache.redis.from_url") as mock_from_url:
                mock_from_url.side_effect = RuntimeError("Unexpected Redis driver error")

                with pytest.raises(ValueError, match=CacheErrorMessage.CREATE_CLIENT_FAILED):
                    create_client()

    def test_create_client_connection_error(self) -> None:
        """Test client creation with connection-related errors."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = "redis://invalid-host:6379/0"

            with patch("app.core.cache.redis.from_url") as mock_from_url:
                mock_from_url.side_effect = ConnectionError("Cannot resolve hostname")

                with pytest.raises(ValueError, match=CacheErrorMessage.CREATE_CLIENT_FAILED):
                    create_client()


class TestGetCache:
    """Test get_cache() async dependency."""

    @pytest.mark.asyncio
    async def test_get_cache_success(self) -> None:
        """Test successful cache dependency injection."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock()

        with patch("app.core.cache.cache_client", mock_client):
            result = await get_cache()

            assert result is mock_client
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_connection_failure(self) -> None:
        """Test cache dependency with connection failure."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(
            side_effect=ConnectionError("Cannot connect to Valkey")
        )

        with patch("app.core.cache.cache_client", mock_client):
            with pytest.raises(RuntimeError, match=CacheErrorMessage.GET_CACHE_FAILED):
                await get_cache()

    @pytest.mark.asyncio
    async def test_get_cache_timeout(self) -> None:
        """Test cache dependency with timeout error."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(side_effect=TimeoutError("Connection timeout"))

        with patch("app.core.cache.cache_client", mock_client):
            with pytest.raises(RuntimeError, match=CacheErrorMessage.GET_CACHE_FAILED):
                await get_cache()

    @pytest.mark.asyncio
    async def test_get_cache_generic_exception(self) -> None:
        """Test cache dependency with generic exception."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(side_effect=Exception("Unexpected error"))

        with patch("app.core.cache.cache_client", mock_client):
            with pytest.raises(RuntimeError, match=CacheErrorMessage.GET_CACHE_FAILED):
                await get_cache()


class TestCheckCacheConnection:
    """Test check_cache_connection() function."""

    @pytest.mark.asyncio
    async def test_check_connection_success(self) -> None:
        """Test successful cache connection check."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock()

        with patch("app.core.cache.cache_client", mock_client):
            result = await check_cache_connection()

            assert result is True
            mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_failure(self) -> None:
        """Test cache connection check with connection failure."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(
            side_effect=ConnectionError("Cannot connect to Valkey")
        )

        with patch("app.core.cache.cache_client", mock_client):
            result = await check_cache_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_timeout(self) -> None:
        """Test cache connection check with timeout."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(side_effect=TimeoutError("Connection timeout"))

        with patch("app.core.cache.cache_client", mock_client):
            result = await check_cache_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_generic_exception(self) -> None:
        """Test cache connection check with generic exception."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock(side_effect=Exception("Unexpected error"))

        with patch("app.core.cache.cache_client", mock_client):
            result = await check_cache_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_returns_boolean(self) -> None:
        """Test that check_cache_connection always returns boolean."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.ping = AsyncMock()

        with patch("app.core.cache.cache_client", mock_client):
            result = await check_cache_connection()

            assert isinstance(result, bool)
            assert result is True


class TestCloseCache:
    """Test close_cache() function."""

    @pytest.mark.asyncio
    async def test_close_cache_success(self) -> None:
        """Test successful cache closure."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.close = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.disconnect = AsyncMock()
        mock_client.connection_pool = mock_pool

        with patch("app.core.cache.cache_client", mock_client):
            await close_cache()

            mock_client.close.assert_called_once()
            mock_pool.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_cache_close_failure(self) -> None:
        """Test cache closure with close() error."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.close = AsyncMock(side_effect=Exception("Close error"))
        mock_pool = AsyncMock()
        mock_client.connection_pool = mock_pool

        with patch("app.core.cache.cache_client", mock_client):
            with pytest.raises(RuntimeError, match=CacheErrorMessage.CLOSE_CACHE_FAILED):
                await close_cache()

    @pytest.mark.asyncio
    async def test_close_cache_disconnect_failure(self) -> None:
        """Test cache closure with pool disconnect error."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.close = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.disconnect = AsyncMock(side_effect=Exception("Disconnect error"))
        mock_client.connection_pool = mock_pool

        with patch("app.core.cache.cache_client", mock_client):
            with pytest.raises(RuntimeError, match=CacheErrorMessage.CLOSE_CACHE_FAILED):
                await close_cache()

    @pytest.mark.asyncio
    async def test_close_cache_connection_already_closed(self) -> None:
        """Test cache closure when connection is already closed."""
        mock_client = AsyncMock(spec=Redis)
        mock_client.close = AsyncMock(
            side_effect=ConnectionError("Connection already closed")
        )
        mock_pool = AsyncMock()
        mock_client.connection_pool = mock_pool

        with patch("app.core.cache.cache_client", mock_client):
            with pytest.raises(RuntimeError, match=CacheErrorMessage.CLOSE_CACHE_FAILED):
                await close_cache()


class TestClientInitialization:
    """Test that client is properly initialized at module load."""

    def test_cache_client_instance_created(self) -> None:
        """Test that cache_client instance is created at module load."""
        assert cache_client is not None


class TestConnectionPoolConfiguration:
    """Test connection pool configuration and behavior."""

    def test_create_client_pool_configuration(self) -> None:
        """Test that connection pool is configured with correct settings."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = "redis://localhost:6379/0"

            with patch("app.core.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock(spec=Redis)
                mock_from_url.return_value = mock_client

                create_client()

                call_kwargs = mock_from_url.call_args[1]

                # Verify pool configuration
                assert call_kwargs["max_connections"] == 20
                assert call_kwargs["socket_connect_timeout"] == 5
                assert call_kwargs["health_check_interval"] == 30
                assert call_kwargs["socket_keepalive"] is True

    def test_create_client_encoding_configuration(self) -> None:
        """Test that client is configured with proper encoding."""
        with patch("app.core.cache.settings") as mock_settings:
            mock_settings.valkey_url = "redis://localhost:6379/0"

            with patch("app.core.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock(spec=Redis)
                mock_from_url.return_value = mock_client

                create_client()

                call_kwargs = mock_from_url.call_args[1]

                # Verify encoding for string responses
                assert call_kwargs["encoding"] == "utf-8"
                assert call_kwargs["decode_responses"] is True


class TestErrorMessages:
    """Test error message constants."""

    def test_error_messages_defined(self) -> None:
        """Test that all error messages are properly defined."""
        assert CacheErrorMessage.CREATE_CLIENT_NO_URL
        assert CacheErrorMessage.CREATE_CLIENT_POOL_MIN_SIZE
        assert CacheErrorMessage.CREATE_CLIENT_FAILED
        assert CacheErrorMessage.GET_CACHE_FAILED
        assert CacheErrorMessage.CLOSE_CACHE_FAILED

    def test_error_messages_are_strings(self) -> None:
        """Test that error messages are non-empty strings."""
        assert isinstance(CacheErrorMessage.CREATE_CLIENT_NO_URL, str)
        assert isinstance(CacheErrorMessage.CREATE_CLIENT_POOL_MIN_SIZE, str)
        assert isinstance(CacheErrorMessage.CREATE_CLIENT_FAILED, str)
        assert isinstance(CacheErrorMessage.GET_CACHE_FAILED, str)
        assert isinstance(CacheErrorMessage.CLOSE_CACHE_FAILED, str)
        assert len(CacheErrorMessage.CREATE_CLIENT_NO_URL) > 0
        assert len(CacheErrorMessage.CREATE_CLIENT_FAILED) > 0
