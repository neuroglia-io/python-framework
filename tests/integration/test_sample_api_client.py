"""Simple integration tests for the HTTP Service Client."""

import pytest

from neuroglia.integration.http_service_client import (
    HttpRequestOptions,
    HttpServiceClient,
    RetryPolicy,
    create_authenticated_client,
)

# Check if httpx is available for tests
try:
    import httpx  # noqa: F401

    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False


@pytest.mark.skipif(not HTTP_CLIENT_AVAILABLE, reason="httpx not available")
@pytest.mark.asyncio
class TestHttpServiceClientIntegration:
    """Simple integration tests for HTTP Service Client."""

    async def test_basic_client_creation(self):
        """Test basic HTTP client creation and configuration."""

        options = HttpRequestOptions(timeout=30.0, max_retries=3, retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF)

        client = HttpServiceClient("https://api.example.com", options)

        # Verify configuration
        assert client.base_url == "https://api.example.com"
        assert client.options.timeout == 30.0
        assert client.options.max_retries == 3
        assert client.options.retry_policy == RetryPolicy.EXPONENTIAL_BACKOFF

        await client.close()

    async def test_authenticated_client_creation(self):
        """Test authenticated client creation."""

        async def mock_token_provider():
            return "test-token-123"

        client = create_authenticated_client(base_url="https://api.secure.com", token_provider=mock_token_provider)

        assert client.base_url == "https://api.secure.com"
        assert len(client.request_interceptors) == 1  # Bearer token
        assert len(client.response_interceptors) == 1  # Logging

        await client.close()

    async def test_circuit_breaker_configuration(self):
        """Test circuit breaker configuration."""

        options = HttpRequestOptions(circuit_breaker_failure_threshold=5, circuit_breaker_timeout=30.0)

        client = HttpServiceClient("https://api.test.com", options)

        # Verify circuit breaker stats are accessible
        stats = client.get_circuit_breaker_stats()
        assert stats.state.value == "closed"
        assert stats.total_requests == 0
        assert stats.total_failures == 0

        await client.close()

    async def test_retry_policy_configurations(self):
        """Test different retry policy configurations."""

        # Test exponential backoff
        exp_options = HttpRequestOptions(
            max_retries=3,
            retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            retry_delay=0.1,
            retry_multiplier=2.0,
        )
        exp_client = HttpServiceClient("https://api.exp.com", exp_options)
        assert exp_client.base_url == "https://api.exp.com"
        await exp_client.close()

        # Test linear delay
        lin_options = HttpRequestOptions(max_retries=5, retry_policy=RetryPolicy.LINEAR_DELAY, retry_delay=0.5)
        lin_client = HttpServiceClient("https://api.lin.com", lin_options)
        assert lin_client.base_url == "https://api.lin.com"
        await lin_client.close()

        # Test fixed delay
        fix_options = HttpRequestOptions(max_retries=2, retry_policy=RetryPolicy.FIXED_DELAY, retry_delay=1.0)
        fix_client = HttpServiceClient("https://api.fix.com", fix_options)
        assert fix_client.base_url == "https://api.fix.com"
        await fix_client.close()

    async def test_service_specific_configurations(self):
        """Test configurations for different service types."""

        # Payment service configuration (high reliability)
        payment_options = HttpRequestOptions(
            timeout=30.0,
            max_retries=3,
            retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
            circuit_breaker_failure_threshold=5,
        )
        payment_client = HttpServiceClient("https://payments.api.com", payment_options)
        assert payment_client.base_url == "https://payments.api.com"
        await payment_client.close()

        # Notification service configuration (high retry)
        notify_options = HttpRequestOptions(timeout=10.0, max_retries=5, retry_policy=RetryPolicy.LINEAR_DELAY)
        notify_client = HttpServiceClient("https://notifications.api.com", notify_options)
        assert notify_client.base_url == "https://notifications.api.com"
        await notify_client.close()

        # Fast service configuration (low timeout)
        fast_options = HttpRequestOptions(timeout=5.0, max_retries=1, retry_policy=RetryPolicy.FIXED_DELAY)
        fast_client = HttpServiceClient("https://fast.api.com", fast_options)
        assert fast_client.base_url == "https://fast.api.com"
        await fast_client.close()

    async def test_interceptor_setup(self):
        """Test request and response interceptor setup."""

        async def token_provider():
            return "secure-token"

        client = create_authenticated_client(
            base_url="https://secure.api.com",
            token_provider=token_provider,
            options=HttpRequestOptions(timeout=15.0),
        )

        # Should have bearer token and logging interceptors
        assert len(client.request_interceptors) == 1  # Bearer token
        assert len(client.response_interceptors) == 1  # Logging

        await client.close()


@pytest.mark.skipif(HTTP_CLIENT_AVAILABLE, reason="Testing without httpx")
class TestHttpServiceClientWithoutHttpx:
    """Test behavior when httpx is not available."""

    def test_import_availability(self):
        """Test that HTTP_CLIENT_AVAILABLE flag works correctly."""
        # This test runs when httpx is NOT available
        # The flag should be False in that case
        assert not HTTP_CLIENT_AVAILABLE
