"""Tests for request ID middleware."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.middleware import RequestIDMiddleware, get_request_id, request_id_var


class TestRequestIDMiddleware:
    """Test suite for RequestIDMiddleware functionality."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app with RequestIDMiddleware."""
        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint() -> dict[str, str]:
            return {"message": "test", "request_id": get_request_id()}

        @app.post("/echo")
        async def echo_endpoint(request: Request) -> dict[str, str | dict]:
            body = await request.json()
            return {"echoed": body, "request_id": get_request_id()}

        @app.get("/error")
        async def error_endpoint() -> None:
            raise ValueError("Test error")

        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client with the app."""
        return TestClient(app)

    def test_request_id_header_added_to_response(self, client: TestClient) -> None:
        """Test that X-Request-ID header is added to all responses."""
        response = client.get("/test")
        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # Verify it's a valid UUID
        request_id = response.headers["x-request-id"]
        uuid.UUID(request_id)  # Should not raise ValueError

    def test_request_id_is_unique_per_request(self, client: TestClient) -> None:
        """Test that each request gets a unique request ID."""
        response1 = client.get("/test")
        response2 = client.get("/test")

        request_id1 = response1.headers["x-request-id"]
        request_id2 = response2.headers["x-request-id"]

        assert request_id1 != request_id2

        # Verify both are valid UUIDs
        uuid.UUID(request_id1)
        uuid.UUID(request_id2)

    def test_request_id_available_in_endpoint_context(self, client: TestClient) -> None:
        """Test that request ID is available via get_request_id() in endpoints."""
        response = client.get("/test")
        assert response.status_code == 200

        response_data = response.json()
        header_request_id = response.headers["x-request-id"]
        context_request_id = response_data["request_id"]

        assert header_request_id == context_request_id
        uuid.UUID(context_request_id)  # Should be valid UUID

    def test_request_id_works_with_post_requests(self, client: TestClient) -> None:
        """Test that middleware works with POST requests."""
        test_data = {"key": "value", "number": 42}
        response = client.post("/echo", json=test_data)

        assert response.status_code == 200
        assert "x-request-id" in response.headers

        response_data = response.json()
        assert response_data["echoed"] == test_data
        assert response_data["request_id"] == response.headers["x-request-id"]

    @patch("app.core.middleware.logger")
    def test_request_start_logged(self, mock_logger: MagicMock, client: TestClient) -> None:
        """Test that request start is logged with correct information."""
        client.get("/test")

        # Check that logger.info was called for request start
        mock_logger.info.assert_any_call(
            "Request started",
            method="GET",
            path="/test",
            query_params=None,
        )

    @patch("app.core.middleware.logger")
    def test_request_completion_logged(self, mock_logger: MagicMock, client: TestClient) -> None:
        """Test that request completion is logged with timing."""
        response = client.get("/test")

        # Check that logger.info was called for request completion
        calls = mock_logger.info.call_args_list
        completion_calls = [call for call in calls if call[0][0] == "Request completed"]
        assert len(completion_calls) == 1

        call_args = completion_calls[0]
        assert "status_code" in call_args[1]
        assert "duration_ms" in call_args[1]
        assert call_args[1]["status_code"] == response.status_code

    @patch("app.core.middleware.logger")
    def test_request_with_query_params_logged(
        self, mock_logger: MagicMock, client: TestClient
    ) -> None:
        """Test that query parameters are included in logs."""
        client.get("/test?param1=value1&param2=value2")

        # Check for request start log with query params
        mock_logger.info.assert_any_call(
            "Request started",
            method="GET",
            path="/test",
            query_params="param1=value1&param2=value2",
        )

    @patch("app.core.middleware.logger")
    def test_error_request_logged(self, mock_logger: MagicMock, client: TestClient) -> None:
        """Test that failed requests are logged appropriately."""
        with pytest.raises(ValueError, match="Test error"):
            client.get("/error")

        # Check that error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        assert call_args[0][0] == "Request failed"
        assert "error" in call_args[1]
        assert "error_type" in call_args[1]
        assert "duration_ms" in call_args[1]
        assert call_args[1]["error"] == "Test error"
        assert call_args[1]["error_type"] == "ValueError"

    def test_request_id_context_isolated_between_requests(self, client: TestClient) -> None:
        """Test that request IDs don't leak between concurrent requests."""
        # This test simulates concurrent requests by making multiple requests
        # and ensuring each gets its own request ID context
        responses = []
        for _ in range(5):
            response = client.get("/test")
            responses.append(response)

        # All request IDs should be unique
        request_ids = [r.headers["x-request-id"] for r in responses]
        assert len(set(request_ids)) == len(request_ids)  # All unique

        # Each response should have matching header and context request IDs
        for response in responses:
            response_data = response.json()
            assert response.headers["x-request-id"] == response_data["request_id"]

    def test_get_request_id_function_outside_request_context(self) -> None:
        """Test get_request_id() returns empty string outside request context."""
        # Clear any existing context
        request_id_var.set("")
        result = get_request_id()
        assert result == ""

    def test_get_request_id_function_with_manual_context(self) -> None:
        """Test get_request_id() works when request ID is manually set."""
        test_id = str(uuid.uuid4())
        request_id_var.set(test_id)

        result = get_request_id()
        assert result == test_id

        # Clean up
        request_id_var.set("")

    def test_request_id_format_is_uuid4(self, client: TestClient) -> None:
        """Test that generated request IDs are valid UUID4 format."""
        response = client.get("/test")
        request_id_str = response.headers["x-request-id"]

        # Parse as UUID and verify it's version 4
        request_id = uuid.UUID(request_id_str)
        assert request_id.version == 4

    def test_middleware_preserves_response_status_codes(self, client: TestClient) -> None:
        """Test that middleware doesn't interfere with response status codes."""
        # Test successful response
        response = client.get("/test")
        assert response.status_code == 200
        assert "x-request-id" in response.headers

        # Test 404 response
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert "x-request-id" in response.headers

    @patch("app.core.middleware.structlog.contextvars.bind_contextvars")
    def test_structlog_context_binding(self, mock_bind: MagicMock, client: TestClient) -> None:
        """Test that request ID is bound to structlog context."""
        response = client.get("/test")
        request_id = response.headers["x-request-id"]

        # Verify bind_contextvars was called with the request ID
        mock_bind.assert_called_once_with(request_id=request_id)

    @patch("app.core.middleware.structlog.contextvars.clear_contextvars")
    def test_structlog_context_cleared_after_request(
        self, mock_clear: MagicMock, client: TestClient
    ) -> None:
        """Test that structlog context is cleared after request completion."""
        client.get("/test")

        # Verify clear_contextvars was called
        mock_clear.assert_called_once()

    @patch("app.core.middleware.structlog.contextvars.clear_contextvars")
    def test_structlog_context_cleared_even_on_error(
        self, mock_clear: MagicMock, client: TestClient
    ) -> None:
        """Test that structlog context is cleared even when request fails."""
        with pytest.raises(ValueError):
            client.get("/error")

        # Verify clear_contextvars was called even though request failed
        mock_clear.assert_called_once()

    def test_timing_accuracy(self, client: TestClient) -> None:
        """Test that request timing is reasonably accurate."""
        import time

        with patch("app.core.middleware.logger") as mock_logger:
            start_time = time.time()
            client.get("/test")
            end_time = time.time()

            # Get the logged duration
            completion_calls = [
                call for call in mock_logger.info.call_args_list
                if call[0][0] == "Request completed"
            ]
            logged_duration_ms = completion_calls[0][1]["duration_ms"]
            actual_duration_ms = (end_time - start_time) * 1000

            # Timing should be reasonably close (within 100ms tolerance)
            assert abs(logged_duration_ms - actual_duration_ms) < 100
