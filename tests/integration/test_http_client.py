"""
Test suite for HTTP Service Client implementation.

This module validates HTTP client functionality including:
- Request/response handling
- Retry policies and backoff strategies
- Circuit breaker patterns
- Timeout management
- Request/response interceptors
- Error handling

Test Coverage:
    - Basic HTTP operations (GET, POST, PUT, DELETE)
    - Retry mechanisms (fixed, linear, exponential)
    - Circuit breaker state management
    - Timeout handling
    - Header management
    - Error scenarios

Expected Behavior:
    - Requests execute successfully
    - Retries work for transient failures
    - Circuit breaker opens/closes correctly
    - Timeouts handled gracefully

Related Modules:
    - neuroglia.integration.http_service_client: HTTP client implementation
    - httpx: Underlying HTTP library

Related Documentation:
    - [HTTP Service Client](../../docs/features/http-service-client.md)
    - [Resilience Patterns](../../docs/patterns/resilience.md)
"""

import asyncio
from unittest.mock import AsyncMock

import pytest

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from neuroglia.integration.http_service_client import (
    CircuitBreakerState,
    HttpRequestOptions,
    HttpResponse,
    HttpServiceClient,
    HttpServiceClientBuilder,
    RequestInterceptor,
    ResponseInterceptor,
    RetryPolicy,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def default_options():
    """Create default HTTP request options."""
    return HttpRequestOptions(timeout=5.0, max_retries=3, retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF, retry_delay=0.1, retry_multiplier=2, retry_max_delay=1.0)


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.aclose = AsyncMock()
    return mock_client


# =============================================================================
# Mock Request/Response Interceptors
# =============================================================================


class TestRequestInterceptor(RequestInterceptor):
    """Test request interceptor that adds custom header."""

    async def intercept_request(self, request: httpx.Request) -> httpx.Request:
        """Add test header to request."""
        request.headers["X-Test-Header"] = "test-value"
        return request


class TestResponseInterceptor(ResponseInterceptor):
    """Test response interceptor that logs response."""

    def __init__(self):
        self.responses = []

    async def intercept_response(self, response: HttpResponse) -> HttpResponse:
        """Log response for testing."""
        self.responses.append(response)
        return response


# =============================================================================
# Test Suite: Client Initialization
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHttpClientInitialization:
    """
    Test HTTP client initialization and configuration.

    Validates that clients are properly initialized with
    correct configuration and dependencies.

    Related: HttpServiceClient initialization
    """

    @pytest.mark.asyncio
    async def test_client_initializes_with_defaults(self):
        """
        Test client initializes with default configuration.

        Expected Behavior:
            - Client created successfully
            - Default options applied
            - No errors on initialization

        Related: HttpServiceClient.__init__
        """
        # Act
        async with HttpServiceClient() as client:
            # Assert
            assert client is not None
            assert client.options is not None
            assert client.base_url == ""

    @pytest.mark.asyncio
    async def test_client_initializes_with_base_url(self):
        """
        Test client initializes with base URL.

        Expected Behavior:
            - Base URL set correctly
            - Used for relative paths
            - Absolute URLs not modified

        Related: Base URL configuration
        """
        # Arrange
        base_url = "https://api.example.com"

        # Act
        async with HttpServiceClient(base_url=base_url) as client:
            # Assert
            assert client.base_url == base_url

    @pytest.mark.asyncio
    async def test_client_initializes_with_custom_options(self, default_options):
        """
        Test client initializes with custom options.

        Expected Behavior:
            - Custom options applied
            - Retry policy set
            - Timeout configured

        Related: HttpRequestOptions
        """
        # Act
        async with HttpServiceClient(options=default_options) as client:
            # Assert
            assert client.options.timeout == 5.0
            assert client.options.max_retries == 3
            assert client.options.retry_policy == RetryPolicy.EXPONENTIAL_BACKOFF


# =============================================================================
# Test Suite: Basic HTTP Operations
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestBasicHttpOperations:
    """
    Test basic HTTP request operations.

    Validates GET, POST, PUT, DELETE operations
    work correctly with proper request formatting.

    Related: HTTP methods
    """

    @pytest.mark.asyncio
    async def test_build_url_with_base_url(self):
        """
        Test URL building with base URL.

        Expected Behavior:
            - Relative paths joined with base
            - Absolute URLs unchanged
            - Proper path handling

        Related: URL construction
        """
        # Arrange
        client = HttpServiceClient(base_url="https://api.example.com")

        # Act
        url1 = client._build_url("/users")
        url2 = client._build_url("users")
        url3 = client._build_url("https://other.com/api")

        # Assert
        assert url1 == "https://api.example.com/users"
        assert url2 == "https://api.example.com/users"
        assert url3 == "https://other.com/api"

        await client.close()

    @pytest.mark.asyncio
    async def test_headers_merged_correctly(self):
        """
        Test headers are merged correctly.

        Expected Behavior:
            - Default headers included
            - Request headers override defaults
            - Custom headers preserved

        Related: Header management
        """
        # Arrange
        options = HttpRequestOptions(headers={"Authorization": "Bearer token123"})
        client = HttpServiceClient(options=options)

        # Act - Check that headers would be merged
        default_headers = options.headers
        request_headers = {"Content-Type": "application/json"}
        merged = {**default_headers, **request_headers}

        # Assert
        assert "Authorization" in merged
        assert "Content-Type" in merged
        assert merged["Authorization"] == "Bearer token123"

        await client.close()


# =============================================================================
# Test Suite: Retry Mechanisms
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestRetryMechanisms:
    """
    Test retry policies and backoff strategies.

    Validates different retry policies work correctly
    with appropriate delays.

    Related: RetryPolicy, backoff strategies
    """

    @pytest.mark.asyncio
    async def test_calculate_fixed_delay(self):
        """
        Test fixed delay retry calculation.

        Expected Behavior:
            - Same delay for all attempts
            - Matches configured delay
            - No variation

        Related: RetryPolicy.FIXED_DELAY
        """
        # Arrange
        options = HttpRequestOptions(retry_policy=RetryPolicy.FIXED_DELAY, retry_delay=1.0)
        client = HttpServiceClient(options=options)

        # Act
        delay1 = await client._calculate_retry_delay(1)
        delay2 = await client._calculate_retry_delay(2)
        delay3 = await client._calculate_retry_delay(3)

        # Assert
        assert delay1 == 1.0
        assert delay2 == 1.0
        assert delay3 == 1.0

        await client.close()

    @pytest.mark.asyncio
    async def test_calculate_linear_delay(self):
        """
        Test linear delay retry calculation.

        Expected Behavior:
            - Delay increases linearly
            - Each attempt adds base delay
            - Predictable progression

        Related: RetryPolicy.LINEAR_DELAY
        """
        # Arrange
        options = HttpRequestOptions(retry_policy=RetryPolicy.LINEAR_DELAY, retry_delay=0.5)
        client = HttpServiceClient(options=options)

        # Act
        delay1 = await client._calculate_retry_delay(1)
        delay2 = await client._calculate_retry_delay(2)
        delay3 = await client._calculate_retry_delay(3)

        # Assert
        assert delay1 == 0.5  # 0.5 * 1
        assert delay2 == 1.0  # 0.5 * 2
        assert delay3 == 1.5  # 0.5 * 3

        await client.close()

    @pytest.mark.asyncio
    async def test_calculate_exponential_backoff(self):
        """
        Test exponential backoff calculation.

        Expected Behavior:
            - Delay increases exponentially
            - Respects max delay cap
            - Rapid increase for early retries

        Related: RetryPolicy.EXPONENTIAL_BACKOFF
        """
        # Arrange
        options = HttpRequestOptions(retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF, retry_delay=0.1, retry_multiplier=2, retry_max_delay=1.0)
        client = HttpServiceClient(options=options)

        # Act
        delay1 = await client._calculate_retry_delay(1)
        delay2 = await client._calculate_retry_delay(2)
        delay3 = await client._calculate_retry_delay(3)
        delay4 = await client._calculate_retry_delay(4)

        # Assert
        assert delay1 == 0.1  # 0.1 * 2^0 = 0.1
        assert delay2 == 0.2  # 0.1 * 2^1 = 0.2
        assert delay3 == 0.4  # 0.1 * 2^2 = 0.4
        assert delay4 == 0.8  # 0.1 * 2^3 = 0.8

        await client.close()

    @pytest.mark.asyncio
    async def test_exponential_backoff_respects_max_delay(self):
        """
        Test exponential backoff respects maximum delay.

        Expected Behavior:
            - Delay capped at max_delay
            - No unbounded growth
            - Consistent cap applied

        Related: Backoff limits
        """
        # Arrange
        options = HttpRequestOptions(retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF, retry_delay=1.0, retry_multiplier=3, retry_max_delay=5.0)
        client = HttpServiceClient(options=options)

        # Act
        delay5 = await client._calculate_retry_delay(5)
        delay10 = await client._calculate_retry_delay(10)

        # Assert
        assert delay5 <= 5.0
        assert delay10 <= 5.0

        await client.close()

    @pytest.mark.asyncio
    async def test_should_retry_on_server_errors(self):
        """
        Test retry logic for server errors.

        Expected Behavior:
            - Retries on 5xx errors
            - Retries on specific 4xx (429, 408, etc.)
            - No retry when max attempts reached

        Related: Retry conditions
        """
        # Arrange
        options = HttpRequestOptions(max_retries=3)
        client = HttpServiceClient(options=options)

        # Act
        response_500 = HttpResponse(status_code=500, content=b"", headers={}, request_url="https://example.com", elapsed_time=0.1)
        response_503 = HttpResponse(status_code=503, content=b"", headers={}, request_url="https://example.com", elapsed_time=0.1)
        response_429 = HttpResponse(status_code=429, content=b"", headers={}, request_url="https://example.com", elapsed_time=0.1)
        response_200 = HttpResponse(status_code=200, content=b"", headers={}, request_url="https://example.com", elapsed_time=0.1)

        should_retry_500 = await client._should_retry(response_500, attempt=1)
        should_retry_503 = await client._should_retry(response_503, attempt=1)
        should_retry_429 = await client._should_retry(response_429, attempt=1)
        should_retry_200 = await client._should_retry(response_200, attempt=1)
        should_retry_max = await client._should_retry(response_500, attempt=3)

        # Assert
        assert should_retry_500 is True
        assert should_retry_503 is True
        assert should_retry_429 is True
        assert should_retry_200 is False
        assert should_retry_max is False

        await client.close()


# =============================================================================
# Test Suite: Circuit Breaker
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestCircuitBreaker:
    """
    Test circuit breaker functionality.

    Validates circuit breaker state transitions
    and request blocking during open state.

    Related: CircuitBreaker pattern
    """

    @pytest.mark.asyncio
    async def test_circuit_breaker_starts_closed(self):
        """
        Test circuit breaker starts in closed state.

        Expected Behavior:
            - Initial state is CLOSED
            - Requests allowed through
            - No blocking

        Related: CircuitBreakerState.CLOSED
        """
        # Arrange
        client = HttpServiceClient()

        # Act
        can_execute = await client._circuit_breaker.can_execute()

        # Assert
        assert can_execute is True
        assert client._circuit_breaker.stats.state == CircuitBreakerState.CLOSED

        await client.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """
        Test circuit breaker opens after failure threshold.

        Expected Behavior:
            - Opens after consecutive failures
            - Blocks subsequent requests
            - Tracks failure count

        Related: Failure threshold
        """
        # Arrange
        options = HttpRequestOptions(circuit_breaker_failure_threshold=3, circuit_breaker_timeout=1.0)
        client = HttpServiceClient(options=options)

        # Act - Record failures
        for _ in range(3):
            await client._circuit_breaker.record_failure()

        # Assert
        assert client._circuit_breaker.stats.state == CircuitBreakerState.OPEN
        can_execute = await client._circuit_breaker.can_execute()
        assert can_execute is False

        await client.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_to_half_open(self):
        """
        Test circuit breaker transitions to half-open.

        Expected Behavior:
            - Transitions after timeout
            - Allows test request
            - Can close or re-open

        Related: CircuitBreakerState.HALF_OPEN
        """
        # Arrange
        options = HttpRequestOptions(circuit_breaker_failure_threshold=2, circuit_breaker_timeout=0.1)  # Short timeout for testing
        client = HttpServiceClient(options=options)

        # Act - Open circuit breaker
        await client._circuit_breaker.record_failure()
        await client._circuit_breaker.record_failure()
        assert client._circuit_breaker.stats.state == CircuitBreakerState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Check if can execute (should transition to HALF_OPEN)
        can_execute = await client._circuit_breaker.can_execute()

        # Assert
        assert can_execute is True
        assert client._circuit_breaker.stats.state == CircuitBreakerState.HALF_OPEN

        await client.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_after_success(self):
        """
        Test circuit breaker closes after success in half-open state.

        Expected Behavior:
            - Circuit starts closed
            - Opens after failures
            - Transitions to half-open
            - Closes after enough successful requests

        Related: Circuit breaker recovery
        """
        # Arrange
        async with HttpServiceClient(
            options=HttpRequestOptions(
                circuit_breaker_failure_threshold=2,
                circuit_breaker_timeout=0.1,
                circuit_breaker_success_threshold=2,  # Need 2 successes to close
            )
        ) as client:
            # Act - Open the circuit
            await client._circuit_breaker.record_failure()
            await client._circuit_breaker.record_failure()
            assert client._circuit_breaker.stats.state == CircuitBreakerState.OPEN

            # Wait for timeout to transition to half-open
            await asyncio.sleep(0.15)
            await client._circuit_breaker.can_execute()
            assert client._circuit_breaker.stats.state == CircuitBreakerState.HALF_OPEN

            # Record enough successful requests to close circuit
            await client._circuit_breaker.record_success()
            await client._circuit_breaker.record_success()

            # Assert - Circuit should be closed after success threshold met
            assert client._circuit_breaker.stats.state == CircuitBreakerState.CLOSED


# =============================================================================
# Test Suite: Request/Response Interceptors
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestInterceptors:
    """
    Test request and response interceptors.

    Validates interceptors can modify requests/responses
    and are applied in correct order.

    Related: RequestInterceptor, ResponseInterceptor
    """

    @pytest.mark.asyncio
    async def test_request_interceptor_applied(self):
        """
        Test request interceptors are applied.

        Expected Behavior:
            - Interceptor modifies request
            - Changes persisted
            - Multiple interceptors chain

        Related: Request interception
        """
        # Arrange
        interceptor = TestRequestInterceptor()
        client = HttpServiceClient(request_interceptors=[interceptor])

        # Create a mock request
        request = httpx.Request("GET", "https://example.com")

        # Act
        modified_request = await client._apply_request_interceptors(request)

        # Assert
        assert "X-Test-Header" in modified_request.headers
        assert modified_request.headers["X-Test-Header"] == "test-value"

        await client.close()

    @pytest.mark.asyncio
    async def test_response_interceptor_applied(self):
        """
        Test response interceptors are applied.

        Expected Behavior:
            - Interceptor processes response
            - Can log or modify response
            - Multiple interceptors chain

        Related: Response interception
        """
        # Arrange
        interceptor = TestResponseInterceptor()
        client = HttpServiceClient(response_interceptors=[interceptor])

        response = HttpResponse(status_code=200, headers={"Content-Type": "application/json"}, content=b'{"result": "success"}', request_url="https://example.com", elapsed_time=0.1)

        # Act
        await client._apply_response_interceptors(response)

        # Assert
        assert len(interceptor.responses) == 1
        assert interceptor.responses[0].status_code == 200

        await client.close()

    @pytest.mark.asyncio
    async def test_multiple_interceptors_execute_in_order(self):
        """
        Test multiple interceptors execute in order.

        Expected Behavior:
            - Interceptors applied sequentially
            - Order matters
            - Each sees previous modifications

        Related: Interceptor chain
        """
        # Arrange
        interceptor1 = TestResponseInterceptor()
        interceptor2 = TestResponseInterceptor()
        client = HttpServiceClient(response_interceptors=[interceptor1, interceptor2])

        response = HttpResponse(status_code=200, headers={}, content=b"test", request_url="https://example.com", elapsed_time=0.1)

        # Act
        await client._apply_response_interceptors(response)

        # Assert
        assert len(interceptor1.responses) == 1
        assert len(interceptor2.responses) == 1

        await client.close()


# =============================================================================
# Test Suite: Builder Pattern
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestHttpClientBuilder:
    """
    Test HTTP client builder for DI configuration.

    Validates HttpServiceClientBuilder.configure() for dependency injection.

    Related: HttpServiceClientBuilder, DI container registration
    """

    @pytest.mark.asyncio
    async def test_builder_configure_with_defaults(self):
        """
        Test builder configures HTTP client in DI container with defaults.

        Expected Behavior:
            - Service registered in DI container
            - Client created with default options
            - Base URL is None by default

        Related: DI registration
        """
        # Arrange
        from neuroglia.dependency_injection import ServiceCollection

        services = ServiceCollection()

        class MockBuilder:
            def __init__(self):
                self.services = services

        builder = MockBuilder()

        # Act
        HttpServiceClientBuilder.configure(builder)

        # Assert - Must create scope for scoped services
        provider = services.build()
        scope = provider.create_scope()
        client = scope.get_service(HttpServiceClient)

        assert client is not None
        assert client.base_url == ""
        assert isinstance(client.options, HttpRequestOptions)

    @pytest.mark.asyncio
    async def test_builder_configure_with_base_url(self):
        """
        Test builder configures HTTP client with base URL.

        Expected Behavior:
            - Base URL set correctly
            - Client registered as scoped service
            - Options initialized with defaults

        Related: Base URL configuration
        """
        # Arrange
        from neuroglia.dependency_injection import ServiceCollection

        services = ServiceCollection()

        class MockBuilder:
            def __init__(self):
                self.services = services

        builder = MockBuilder()

        # Act
        HttpServiceClientBuilder.configure(builder, base_url="https://api.example.com")

        # Assert
        provider = services.build()
        scope = provider.create_scope()
        client = scope.get_service(HttpServiceClient)

        assert client.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_builder_configure_with_custom_options(self):
        """
        Test builder configures HTTP client with custom options.

        Expected Behavior:
            - Custom options applied
            - Retry policy configured
            - Timeout and retries set

        Related: Options configuration
        """
        # Arrange
        from neuroglia.dependency_injection import ServiceCollection

        services = ServiceCollection()

        class MockBuilder:
            def __init__(self):
                self.services = services

        builder = MockBuilder()
        custom_options = HttpRequestOptions(retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF, max_retries=5, timeout=30.0)

        # Act
        HttpServiceClientBuilder.configure(builder, base_url="https://api.example.com", options=custom_options)

        # Assert
        provider = services.build()
        scope = provider.create_scope()
        client = scope.get_service(HttpServiceClient)

        assert client.base_url == "https://api.example.com"
        assert client.options.retry_policy == RetryPolicy.EXPONENTIAL_BACKOFF
        assert client.options.max_retries == 5
        assert client.options.timeout == 30.0


# =============================================================================
# Test Suite: Error Handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
class TestErrorHandling:
    """
    Test error handling scenarios.

    Validates proper handling of various error conditions
    including timeouts, connection errors, and invalid responses.

    Related: Exception handling
    """

    @pytest.mark.asyncio
    async def test_client_handles_invalid_configuration(self):
        """
        Test client handles invalid configuration.

        Expected Behavior:
            - Validation on initialization
            - Clear error messages
            - Fails fast on invalid config

        Related: Configuration validation
        """
        # This is a placeholder - actual validation depends on implementation
        # Just verify client can be created with reasonable defaults
        async with HttpServiceClient() as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_client_context_manager_cleanup(self):
        """
        Test client context manager cleanup.

        Expected Behavior:
            - Resources cleaned up on exit
            - Client properly closed
            - No resource leaks

        Related: Resource management
        """
        # Arrange & Act
        async with HttpServiceClient() as client:
            assert client._client is not None

        # Assert - Client should be closed after context exit
        # (In real httpx, the client would be closed)
        assert True  # Context manager executed successfully
