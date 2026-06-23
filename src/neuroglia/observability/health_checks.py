"""
Pluggable health check providers for common dependencies.

This module provides an abstract base class for health check providers
and concrete implementations for common infrastructure dependencies.

Health check providers are used by the Observability framework to check
the status of dependencies when the /health endpoint is called.

Usage:
    from neuroglia.observability.health_checks import (
        MongoDBHealthCheck,
        RedisHealthCheck,
    )

    Observability.configure(
        builder,
        health_check_providers=[
            MongoDBHealthCheck(app_settings.connection_strings["mongo"]),
            RedisHealthCheck(app_settings.redis_url),
        ]
    )
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional

log = logging.getLogger(__name__)

# Type alias for health status
HealthStatus = Literal["healthy", "unhealthy", "degraded"]


@dataclass
class HealthCheckResult:
    """Result of a health check operation.

    Attributes:
        status: The health status (healthy, unhealthy, or degraded).
        message: Optional message providing details about the status.
        latency_ms: Optional latency measurement in milliseconds.
    """

    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthCheckProvider(ABC):
    """Abstract base class for health check providers.

    Subclass this to create custom health check providers for your dependencies.

    Example:
        class MyCustomHealthCheck(HealthCheckProvider):
            @property
            def name(self) -> str:
                return "my-service"

            async def check(self) -> HealthCheckResult:
                # Check your dependency
                return HealthCheckResult(status="healthy")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the dependency being checked.

        This name is used to match against the `observability_health_checks`
        setting and as the key in the health check response.
        """

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Check dependency health.

        Returns:
            HealthCheckResult with status and optional message.
        """


class MongoDBHealthCheck(HealthCheckProvider):
    """Health check for MongoDB connection.

    Uses the motor async MongoDB driver to ping the database server.

    Args:
        connection_string: MongoDB connection string (e.g., mongodb://localhost:27017).
        timeout_ms: Connection timeout in milliseconds (default: 2000).
    """

    def __init__(self, connection_string: str, timeout_ms: int = 2000):
        self._connection_string = connection_string
        self._timeout_ms = timeout_ms

    @property
    def name(self) -> str:
        return "mongodb"

    async def check(self) -> HealthCheckResult:
        import time

        start = time.perf_counter()
        try:
            # Lazy import to avoid hard dependency
            from motor.motor_asyncio import AsyncIOMotorClient

            client = AsyncIOMotorClient(
                self._connection_string,
                serverSelectionTimeoutMS=self._timeout_ms,
            )
            await client.admin.command("ping")
            client.close()

            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(status="healthy", latency_ms=latency_ms)

        except ImportError:
            return HealthCheckResult(
                status="degraded",
                message="motor package not installed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(f"MongoDB health check failed: {e}")
            return HealthCheckResult(
                status="unhealthy",
                message=str(e),
                latency_ms=latency_ms,
            )


class RedisHealthCheck(HealthCheckProvider):
    """Health check for Redis connection.

    Uses redis-py async client to ping the Redis server.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379).
        timeout: Connection timeout in seconds (default: 2.0).
    """

    def __init__(self, redis_url: str, timeout: float = 2.0):
        self._redis_url = redis_url
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "redis"

    async def check(self) -> HealthCheckResult:
        import time

        start = time.perf_counter()
        try:
            # Lazy import to avoid hard dependency
            import redis.asyncio as redis_async

            client = redis_async.from_url(
                self._redis_url,
                socket_timeout=self._timeout,
            )
            await client.ping()
            await client.aclose()

            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(status="healthy", latency_ms=latency_ms)

        except ImportError:
            return HealthCheckResult(
                status="degraded",
                message="redis package not installed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(f"Redis health check failed: {e}")
            return HealthCheckResult(
                status="unhealthy",
                message=str(e),
                latency_ms=latency_ms,
            )


class Neo4jHealthCheck(HealthCheckProvider):
    """Health check for Neo4j graph database connection.

    Uses the neo4j async driver to verify connectivity.

    Args:
        uri: Neo4j connection URI (e.g., bolt://localhost:7687).
        username: Neo4j username.
        password: Neo4j password.
    """

    def __init__(self, uri: str, username: str, password: str):
        self._uri = uri
        self._username = username
        self._password = password

    @property
    def name(self) -> str:
        return "neo4j"

    async def check(self) -> HealthCheckResult:
        import time

        start = time.perf_counter()
        try:
            # Lazy import to avoid hard dependency
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._username, self._password),
            )
            await driver.verify_connectivity()
            await driver.close()

            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(status="healthy", latency_ms=latency_ms)

        except ImportError:
            return HealthCheckResult(
                status="degraded",
                message="neo4j package not installed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(f"Neo4j health check failed: {e}")
            return HealthCheckResult(
                status="unhealthy",
                message=str(e),
                latency_ms=latency_ms,
            )


class QdrantHealthCheck(HealthCheckProvider):
    """Health check for Qdrant vector database.

    Uses the qdrant-client async API to verify connectivity.

    Args:
        url: Qdrant server URL (e.g., http://localhost:6333).
        api_key: Optional API key for authentication.
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        self._url = url
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "qdrant"

    async def check(self) -> HealthCheckResult:
        import time

        start = time.perf_counter()
        try:
            # Lazy import to avoid hard dependency
            from qdrant_client import AsyncQdrantClient

            client = AsyncQdrantClient(url=self._url, api_key=self._api_key)
            # Simple connectivity check - get collections list
            await client.get_collections()
            await client.close()

            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(status="healthy", latency_ms=latency_ms)

        except ImportError:
            return HealthCheckResult(
                status="degraded",
                message="qdrant-client package not installed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(f"Qdrant health check failed: {e}")
            return HealthCheckResult(
                status="unhealthy",
                message=str(e),
                latency_ms=latency_ms,
            )


class HttpServiceHealthCheck(HealthCheckProvider):
    """Health check for external HTTP services.

    Makes a GET request to the specified URL and checks for a 2xx response.

    Args:
        name: Name to identify this service in health check responses.
        url: URL to check (typically a /health endpoint).
        timeout: Request timeout in seconds (default: 5.0).
        expected_status_codes: Set of acceptable status codes (default: 200-299).
    """

    def __init__(
        self,
        name: str,
        url: str,
        timeout: float = 5.0,
        expected_status_codes: Optional[set[int]] = None,
    ):
        self._name = name
        self._url = url
        self._timeout = timeout
        self._expected_status_codes = expected_status_codes or set(range(200, 300))

    @property
    def name(self) -> str:
        return self._name

    async def check(self) -> HealthCheckResult:
        import time

        start = time.perf_counter()
        try:
            # Lazy import to avoid hard dependency
            import httpx

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._url)
                latency_ms = (time.perf_counter() - start) * 1000

                if response.status_code in self._expected_status_codes:
                    return HealthCheckResult(status="healthy", latency_ms=latency_ms)
                else:
                    return HealthCheckResult(
                        status="degraded",
                        message=f"HTTP {response.status_code}",
                        latency_ms=latency_ms,
                    )

        except ImportError:
            return HealthCheckResult(
                status="degraded",
                message="httpx package not installed",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            log.warning(f"HTTP health check failed for {self._name}: {e}")
            return HealthCheckResult(
                status="unhealthy",
                message=str(e),
                latency_ms=latency_ms,
            )
