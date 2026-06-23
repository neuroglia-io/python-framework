"""
Comprehensive integration components for external systems and service communication.

This module provides enterprise-grade integration patterns including resilient HTTP clients,
distributed caching, integration events, and external service communication patterns.
Designed to support microservice architectures, API integrations, and distributed system
communication with reliability, resilience, and observability built-in.

Key Components:
    - HttpServiceClient: Resilient HTTP client with circuit breakers and retry policies
    - AsyncCacheRepository: Distributed Redis-based caching with async operations
    - IntegrationEvent: Standardized events for external system integration
    - Request/Response Interceptors: Middleware for authentication, logging, and monitoring

Features:
    - Circuit breaker pattern for fault tolerance
    - Exponential backoff retry policies with jitter
    - Connection pooling and timeout management
    - Request/response interceptors for cross-cutting concerns
    - Authentication token management (Bearer, API keys)
    - Comprehensive logging and monitoring integration
    - Redis-based distributed caching with clustering support
    - Integration event patterns for external system notifications

Examples:
    ```python
    from neuroglia.integration import (
        HttpServiceClient, HttpRequestOptions,
        AsyncCacheRepository, CacheRepositoryOptions,
        BearerTokenInterceptor, LoggingInterceptor
    )

    # Resilient HTTP client setup
    http_options = HttpRequestOptions(
        timeout=30.0,
        max_retries=3,
        retry_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
        circuit_breaker_failure_threshold=5
    )

    # Create authenticated HTTP client
    client = HttpServiceClient(
        base_url="https://api.example.com",
        options=http_options,
        interceptors=[
            BearerTokenInterceptor(token="your-api-token"),
            LoggingInterceptor()
        ]
    )

    # Make resilient API calls
    response = await client.get_async("/users/123")
    if response.success:
        user_data = response.json()

    # Distributed caching
    cache_options = CacheRepositoryOptions(
        connection_string="redis://localhost:6379",
        default_ttl=timedelta(hours=1),
        key_prefix="app:"
    )

    cache = AsyncCacheRepository(cache_options)

    # Cache operations
    await cache.set_async("user:123", user_data, ttl=timedelta(minutes=30))
    cached_user = await cache.get_async("user:123", dict)

    # Service integration with caching
    class UserService:
        def __init__(self, http_client: HttpServiceClient, cache: AsyncCacheRepository):
            self.http_client = http_client
            self.cache = cache

        async def get_user_async(self, user_id: str) -> dict:
            # Check cache first
            cache_key = f"user:{user_id}"
            cached = await self.cache.get_async(cache_key, dict)
            if cached:
                return cached

            # Fetch from API with resilience
            response = await self.http_client.get_async(f"/users/{user_id}")
            if response.success:
                user_data = response.json()
                await self.cache.set_async(cache_key, user_data)
                return user_data

            raise HttpServiceClientException(f"Failed to fetch user {user_id}")
    ```

See Also:
    - HTTP Service Client Guide: https://bvandewe.github.io/pyneuro/features/http-service-client/
    - Redis Cache Repository: https://bvandewe.github.io/pyneuro/features/redis-cache-repository/
    - Integration Patterns: https://bvandewe.github.io/pyneuro/patterns/
"""

from .models import IntegrationEvent

# Cache repository imports - optional dependencies
try:
    from .cache_repository import (
        AsyncCacheRepository,
        AsyncHashCacheRepository,
        CacheClientPool,
        CacheRepositoryException,
        CacheRepositoryOptions,
    )

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    AsyncCacheRepository = None
    AsyncHashCacheRepository = None
    CacheRepositoryOptions = None
    CacheClientPool = None
    CacheRepositoryException = None

# HTTP service client imports - httpx dependency
try:
    from .http_service_client import (
        BearerTokenInterceptor,
        CircuitBreakerState,
        CircuitBreakerStats,
        HttpRequestOptions,
        HttpResponse,
        HttpServiceClient,
        HttpServiceClientBuilder,
        HttpServiceClientException,
        LoggingInterceptor,
        RequestInterceptor,
        ResponseInterceptor,
        RetryPolicy,
        create_authenticated_client,
        create_logging_client,
    )

    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False
    HttpServiceClient = None
    HttpServiceClientException = None
    HttpRequestOptions = None
    HttpResponse = None
    RetryPolicy = None
    CircuitBreakerState = None
    CircuitBreakerStats = None
    RequestInterceptor = None
    ResponseInterceptor = None
    BearerTokenInterceptor = None
    LoggingInterceptor = None
    HttpServiceClientBuilder = None
    create_authenticated_client = None
    create_logging_client = None

__all__ = [
    "IntegrationEvent",
    # Cache repositories (when available)
    "AsyncCacheRepository",
    "AsyncHashCacheRepository",
    "CacheRepositoryOptions",
    "CacheClientPool",
    "CacheRepositoryException",
    "CACHE_AVAILABLE",
    # HTTP service client (when available)
    "HttpServiceClient",
    "HttpServiceClientException",
    "HttpRequestOptions",
    "HttpResponse",
    "RetryPolicy",
    "CircuitBreakerState",
    "CircuitBreakerStats",
    "RequestInterceptor",
    "ResponseInterceptor",
    "BearerTokenInterceptor",
    "LoggingInterceptor",
    "HttpServiceClientBuilder",
    "create_authenticated_client",
    "create_logging_client",
    "HTTP_CLIENT_AVAILABLE",
]
