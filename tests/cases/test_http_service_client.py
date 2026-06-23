"""Tests for the HTTP Service Client module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import pytest

from neuroglia.integration.http_service_client import (
    HttpServiceClient,
    HttpServiceClientException,
    HttpRequestOptions,
    HttpResponse,
    RetryPolicy,
    CircuitBreakerState,
    CircuitBreakerStats,
    RequestInterceptor,
    ResponseInterceptor,
    BearerTokenInterceptor,
    LoggingInterceptor,
    CircuitBreaker,
    HttpServiceClientBuilder,
    create_authenticated_client,
    create_logging_client,
)

# Check httpx availability for conditional tests
try:
    import httpx  # noqa: F401

    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False


class TestHttpRequestOptions:
    """Test HttpRequestOptions functionality."""

    def test_options_creation(self):
        """Test creating HTTP request options."""
        options = HttpRequestOptions(
            timeout=60.0,
            max_retries=5,
            retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            retry_delay=2.0,
        )

        assert options.timeout == 60.0
        assert options.max_retries == 5
        assert options.retry_policy == RetryPolicy.EXPONENTIAL_BACKOFF
        assert options.retry_delay == 2.0

    def test_options_defaults(self):
        """Test default values in options."""
        options = HttpRequestOptions()

        assert options.timeout == 30.0
        assert options.max_retries == 3
        assert options.retry_policy == RetryPolicy.EXPONENTIAL_BACKOFF
        assert options.retry_delay == 1.0
        assert options.retry_multiplier == 2.0
        assert options.verify_ssl is True
        assert options.follow_redirects is True


class TestHttpResponse:
    """Test HttpResponse functionality."""

    def test_response_creation(self):
        """Test creating HTTP response."""
        response = HttpResponse(
            status_code=200,
            content=b'{"message": "success"}',
            headers={"content-type": "application/json"},
            request_url="https://api.example.com/test",
            elapsed_time=0.5,
        )

        assert response.status_code == 200
        assert response.success is True
        assert response.request_url == "https://api.example.com/test"
        assert response.elapsed_time == 0.5

    def test_response_json_parsing(self):
        """Test JSON parsing in response."""
        response = HttpResponse(
            status_code=200,
            content=b'{"name": "John", "age": 30}',
            headers={"content-type": "application/json"},
            request_url="https://api.example.com/user",
            elapsed_time=0.3,
        )

        data = response.json()
        assert data["name"] == "John"
        assert data["age"] == 30

    def test_response_text_parsing(self):
        """Test text parsing in response."""
        response = HttpResponse(
            status_code=200,
            content=b"Hello, World!",
            headers={"content-type": "text/plain"},
            request_url="https://api.example.com/greeting",
            elapsed_time=0.2,
        )

        text = response.text()
        assert text == "Hello, World!"

    def test_response_success_status_codes(self):
        """Test success determination for various status codes."""
        # Success codes
        for code in [200, 201, 202, 204, 299]:
            response = HttpResponse(
                status_code=code,
                content=b"",
                headers={},
                request_url="https://example.com",
                elapsed_time=0.1,
            )
            assert response.success is True

        # Failure codes
        for code in [400, 404, 500, 503]:
            response = HttpResponse(
                status_code=code,
                content=b"",
                headers={},
                request_url="https://example.com",
                elapsed_time=0.1,
            )
            assert response.success is False

    def test_response_json_parsing_error(self):
        """Test JSON parsing error handling."""
        response = HttpResponse(
            status_code=200,
            content=b"invalid json{",
            headers={},
            request_url="https://example.com",
            elapsed_time=0.1,
        )

        with pytest.raises(HttpServiceClientException) as exc_info:
            response.json()

        assert "Failed to parse JSON response" in str(exc_info.value)


class TestCircuitBreakerStats:
    """Test CircuitBreakerStats functionality."""

    def test_stats_creation(self):
        """Test creating circuit breaker stats."""
        stats = CircuitBreakerStats()

        assert stats.state == CircuitBreakerState.CLOSED
        assert stats.failure_count == 0
        assert stats.success_count == 0
        assert stats.total_requests == 0
        assert stats.total_failures == 0


class MockRequestInterceptor(RequestInterceptor):
    """Mock request interceptor for testing."""

    def __init__(self, header_name: str, header_value: str):
        self.header_name = header_name
        self.header_value = header_value

    async def intercept_request(self, request):
        request.headers[self.header_name] = self.header_value
        return request


class MockResponseInterceptor(ResponseInterceptor):
    """Mock response interceptor for testing."""

    def __init__(self):
        self.intercepted_responses = []

    async def intercept_response(self, response: HttpResponse) -> HttpResponse:
        self.intercepted_responses.append(response)
        return response


class TestBearerTokenInterceptor:
    """Test BearerTokenInterceptor functionality."""

    @pytest.mark.asyncio
    async def test_bearer_token_added(self):
        """Test Bearer token is added to request."""

        async def token_provider():
            return "test-token-123"

        interceptor = BearerTokenInterceptor(token_provider)

        # Mock request
        mock_request = Mock()
        mock_request.headers = {}

        result = await interceptor.intercept_request(mock_request)

        assert result.headers["Authorization"] == "Bearer test-token-123"

    @pytest.mark.asyncio
    async def test_bearer_token_provider_error(self):
        """Test handling of token provider errors."""

        async def failing_token_provider():
            raise Exception("Token service unavailable")

        interceptor = BearerTokenInterceptor(failing_token_provider)

        # Mock request
        mock_request = Mock()
        mock_request.headers = {}

        # Should not raise exception, just log warning
        result = await interceptor.intercept_request(mock_request)

        assert "Authorization" not in result.headers


class TestLoggingInterceptor:
    """Test LoggingInterceptor functionality."""

    @pytest.mark.asyncio
    async def test_response_logging(self):
        """Test response logging."""
        mock_logger = Mock()
        interceptor = LoggingInterceptor(mock_logger)

        response = HttpResponse(
            status_code=200,
            content=b'{"success": true}',
            headers={},
            request_url="https://api.example.com/test",
            elapsed_time=0.5,
        )

        result = await interceptor.intercept_response(response)

        assert result == response
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "HTTP 200" in log_message
        assert "https://api.example.com/test" in log_message


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def setup_method(self):
        """Set up test dependencies."""
        self.options = HttpRequestOptions(
            circuit_breaker_failure_threshold=3,
            circuit_breaker_timeout=60.0,
            circuit_breaker_success_threshold=2,
        )
        self.circuit_breaker = CircuitBreaker(self.options)

    async def test_initial_state_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        assert await self.circuit_breaker.can_execute() is True
        assert self.circuit_breaker.stats.state == CircuitBreakerState.CLOSED

    async def test_failure_threshold_opens_circuit(self):
        """Test circuit opens after failure threshold."""
        # Record failures up to threshold
        for _ in range(self.options.circuit_breaker_failure_threshold):
            await self.circuit_breaker.record_failure()

        assert self.circuit_breaker.stats.state == CircuitBreakerState.OPEN
        assert await self.circuit_breaker.can_execute() is False

    async def test_timeout_moves_to_half_open(self):
        """Test circuit moves to HALF_OPEN after timeout."""
        # Force circuit to OPEN state
        for _ in range(self.options.circuit_breaker_failure_threshold):
            await self.circuit_breaker.record_failure()

        # Manually set last failure time to past
        self.circuit_breaker.stats.last_failure_time = datetime.now() - timedelta(
            seconds=self.options.circuit_breaker_timeout + 1
        )

        assert await self.circuit_breaker.can_execute() is True
        assert self.circuit_breaker.stats.state == CircuitBreakerState.HALF_OPEN

    async def test_half_open_success_closes_circuit(self):
        """Test successful requests in HALF_OPEN close the circuit."""
        # Set to HALF_OPEN state
        self.circuit_breaker.stats.state = CircuitBreakerState.HALF_OPEN

        # Record successful requests
        for _ in range(self.options.circuit_breaker_success_threshold):
            await self.circuit_breaker.record_success()

        assert self.circuit_breaker.stats.state == CircuitBreakerState.CLOSED

    async def test_half_open_failure_opens_circuit(self):
        """Test failure in HALF_OPEN reopens the circuit."""
        # Set to HALF_OPEN state
        self.circuit_breaker.stats.state = CircuitBreakerState.HALF_OPEN

        # Record failure
        await self.circuit_breaker.record_failure()

        assert self.circuit_breaker.stats.state == CircuitBreakerState.OPEN


@pytest.mark.skipif(not HTTP_CLIENT_AVAILABLE, reason="httpx not available")
@pytest.mark.asyncio
class TestHttpServiceClient:
    """Test HttpServiceClient functionality."""

    def setup_method(self):
        """Set up test dependencies."""
        self.options = HttpRequestOptions(
            timeout=10.0, max_retries=2, retry_policy=RetryPolicy.FIXED_DELAY, retry_delay=0.1
        )

    async def test_client_creation(self):
        """Test creating HTTP service client."""
        client = HttpServiceClient(base_url="https://api.example.com", options=self.options)

        assert client.base_url == "https://api.example.com"
        assert client.options == self.options

        await client.close()

    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with HttpServiceClient(base_url="https://api.example.com") as client:
            assert client is not None

    async def test_build_url(self):
        """Test URL building functionality."""
        client = HttpServiceClient(base_url="https://api.example.com/v1/")

        # Test relative URL
        url = client._build_url("users/123")
        assert url == "https://api.example.com/v1/users/123"

        # Test absolute URL
        url = client._build_url("https://other-api.com/data")
        assert url == "https://other-api.com/data"

        await client.close()

    async def test_request_interceptors(self):
        """Test request interceptor application."""
        interceptor = MockRequestInterceptor("X-Test-Header", "test-value")
        client = HttpServiceClient(
            base_url="https://api.example.com", request_interceptors=[interceptor]
        )

        # Mock request
        mock_request = Mock()
        mock_request.headers = {}

        result = await client._apply_request_interceptors(mock_request)

        assert result.headers["X-Test-Header"] == "test-value"
        await client.close()

    async def test_response_interceptors(self):
        """Test response interceptor application."""
        interceptor = MockResponseInterceptor()
        client = HttpServiceClient(
            base_url="https://api.example.com", response_interceptors=[interceptor]
        )

        response = HttpResponse(
            status_code=200,
            content=b'{"test": true}',
            headers={},
            request_url="https://api.example.com/test",
            elapsed_time=0.1,
        )

        await client._apply_response_interceptors(response)

        assert len(interceptor.intercepted_responses) == 1
        assert interceptor.intercepted_responses[0] == response
        await client.close()

    async def test_retry_delay_calculation(self):
        """Test retry delay calculations for different policies."""
        # Fixed delay
        client = HttpServiceClient(
            options=HttpRequestOptions(retry_policy=RetryPolicy.FIXED_DELAY, retry_delay=2.0)
        )

        delay = await client._calculate_retry_delay(1)
        assert delay == 2.0

        delay = await client._calculate_retry_delay(3)
        assert delay == 2.0

        await client.close()

        # Exponential backoff
        client = HttpServiceClient(
            options=HttpRequestOptions(
                retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                retry_delay=1.0,
                retry_multiplier=2.0,
                retry_max_delay=10.0,
            )
        )

        delay = await client._calculate_retry_delay(1)
        assert delay == 1.0

        delay = await client._calculate_retry_delay(2)
        assert delay == 2.0

        delay = await client._calculate_retry_delay(3)
        assert delay == 4.0

        delay = await client._calculate_retry_delay(10)  # Should be capped
        assert delay == 10.0

        await client.close()

    async def test_should_retry_logic(self):
        """Test retry decision logic."""
        client = HttpServiceClient(options=HttpRequestOptions(max_retries=3))

        # Test retry on 5xx errors
        response_500 = HttpResponse(500, b"", {}, "http://test.com", 0.1)
        assert await client._should_retry(response_500, 1) is True
        assert await client._should_retry(response_500, 3) is False

        # Test retry on specific 4xx errors
        response_429 = HttpResponse(429, b"", {}, "http://test.com", 0.1)
        assert await client._should_retry(response_429, 1) is True

        # Test no retry on general 4xx errors
        response_404 = HttpResponse(404, b"", {}, "http://test.com", 0.1)
        assert await client._should_retry(response_404, 1) is False

        # Test no retry on 2xx success
        response_200 = HttpResponse(200, b"", {}, "http://test.com", 0.1)
        assert await client._should_retry(response_200, 1) is False

        await client.close()

    async def test_circuit_breaker_stats_access(self):
        """Test circuit breaker statistics access."""
        client = HttpServiceClient()

        stats = client.get_circuit_breaker_stats()
        assert isinstance(stats, CircuitBreakerStats)
        assert stats.state == CircuitBreakerState.CLOSED

        await client.close()

    async def test_circuit_breaker_reset(self):
        """Test circuit breaker reset functionality."""
        client = HttpServiceClient()

        # Manually set some stats
        client._circuit_breaker.stats.failure_count = 5
        client._circuit_breaker.stats.total_requests = 10

        await client.reset_circuit_breaker()

        stats = client.get_circuit_breaker_stats()
        assert stats.failure_count == 0
        assert stats.total_requests == 0

        await client.close()


class TestHttpServiceClientBuilder:
    """Test HttpServiceClientBuilder functionality."""

    def test_configure_success(self):
        """Test successful HTTP service client configuration."""
        # Mock builder
        mock_builder = Mock()
        mock_builder.services = Mock()
        mock_builder.services.add_scoped = Mock()

        result = HttpServiceClientBuilder.configure(
            mock_builder, base_url="https://api.example.com", options=HttpRequestOptions()
        )

        assert result == mock_builder
        mock_builder.services.add_scoped.assert_called_once()

    def test_configure_missing_httpx(self):
        """Test configuration failure when httpx not available."""
        mock_builder = Mock()

        with patch("neuroglia.integration.http_service_client.HTTP_CLIENT_AVAILABLE", False):
            with pytest.raises(HttpServiceClientException) as exc_info:
                HttpServiceClientBuilder.configure(mock_builder)

            assert "httpx is required" in str(exc_info.value)


@pytest.mark.skipif(not HTTP_CLIENT_AVAILABLE, reason="httpx not available")
class TestUtilityFunctions:
    """Test utility functions for HTTP client creation."""

    @pytest.mark.asyncio
    async def test_create_authenticated_client(self):
        """Test creating authenticated HTTP client."""

        async def token_provider():
            return "test-token"

        client = create_authenticated_client(
            base_url="https://api.example.com", token_provider=token_provider
        )

        assert len(client.request_interceptors) == 1
        assert isinstance(client.request_interceptors[0], BearerTokenInterceptor)
        assert len(client.response_interceptors) == 1
        assert isinstance(client.response_interceptors[0], LoggingInterceptor)

        await client.close()

    def test_create_logging_client(self):
        """Test creating logging HTTP client."""
        client = create_logging_client(base_url="https://api.example.com")

        assert len(client.response_interceptors) == 1
        assert isinstance(client.response_interceptors[0], LoggingInterceptor)

        # Test with custom logger
        import logging

        custom_logger = logging.getLogger("test")

        client_with_logger = create_logging_client(
            base_url="https://api.example.com", logger=custom_logger
        )

        assert client_with_logger.response_interceptors[0].logger == custom_logger


@pytest.mark.skipif(HTTP_CLIENT_AVAILABLE, reason="Testing without httpx")
class TestHttpServiceClientWithoutHttpx:
    """Test HTTP service client behavior when httpx is not available."""

    def test_client_creation_without_httpx(self):
        """Test client creation fails without httpx."""
        with pytest.raises(HttpServiceClientException) as exc_info:
            HttpServiceClient()

        assert "httpx is required" in str(exc_info.value)


# Integration tests with mocked httpx responses
@pytest.mark.skipif(not HTTP_CLIENT_AVAILABLE, reason="httpx not available")
@pytest.mark.asyncio
class TestHttpServiceClientIntegration:
    """Integration tests for HTTP service client with mocked responses."""

    async def test_successful_get_request(self):
        """Test successful GET request with mocked response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"message": "success"}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/test"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client.build_request = Mock(return_value=Mock())

            client = HttpServiceClient(base_url="https://api.example.com")

            response = await client.get("/test")

            assert response.status_code == 200
            assert response.success is True
            assert response.json()["message"] == "success"

            await client.close()

    async def test_retry_on_server_error(self):
        """Test retry behavior on server errors."""
        # First call fails, second succeeds
        mock_responses = [
            Mock(
                status_code=500,
                content=b"Server Error",
                headers={},
                url="https://api.example.com/test",
            ),
            Mock(
                status_code=200,
                content=b'{"success": true}',
                headers={},
                url="https://api.example.com/test",
            ),
        ]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.send = AsyncMock(side_effect=mock_responses)
            mock_client.build_request = Mock(return_value=Mock())

            client = HttpServiceClient(
                base_url="https://api.example.com",
                options=HttpRequestOptions(max_retries=2, retry_delay=0.01),
            )

            response = await client.get("/test")

            assert response.status_code == 200
            assert response.success is True
            assert mock_client.send.call_count == 2

            await client.close()

    async def test_json_convenience_methods(self):
        """Test JSON convenience methods."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": 123, "name": "test"}'
        mock_response.headers = {}
        mock_response.url = "https://api.example.com/data"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client.build_request = Mock(return_value=Mock())

            client = HttpServiceClient(base_url="https://api.example.com")

            # Test get_json
            data = await client.get_json("/data")
            assert data["id"] == 123
            assert data["name"] == "test"

            # Test post_json
            post_data = {"name": "new item"}
            result = await client.post_json("/data", post_data)
            assert result["id"] == 123

            await client.close()
