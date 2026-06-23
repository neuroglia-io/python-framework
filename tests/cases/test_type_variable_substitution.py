"""
Test type variable substitution in generic dependency injection.

This test validates the v0.4.3 enhancement that enables constructor parameters
with type variables (TEntity, TKey) to be correctly substituted with concrete
types (MozartSession, str) during dependency resolution.

Example scenario:
    class AsyncCacheRepository(Generic[TEntity, TKey]):
        def __init__(
            self,
            options: CacheRepositoryOptions[TEntity, TKey],  # Type variables!
            pool: CacheClientPool[TEntity, TKey],            # Type variables!
        ):
            ...

When building AsyncCacheRepository[MozartSession, str], the DI container must:
1. Inspect constructor and find 'options: CacheRepositoryOptions[TEntity, TKey]'
2. Substitute TEntity -> MozartSession, TKey -> str
3. Resolve CacheRepositoryOptions[MozartSession, str] from registry
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from neuroglia.dependency_injection import ServiceCollection

TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey")


@dataclass
class CacheRepositoryOptions(Generic[TEntity, TKey]):
    """Configuration options with generic type parameters."""

    host: str
    port: int
    entity_name: str = ""
    key_name: str = ""


@dataclass
class CacheClientPool(Generic[TEntity, TKey]):
    """Connection pool with generic type parameters."""

    max_connections: int
    entity_type: type = None
    key_type: type = None


class Repository(Generic[TEntity, TKey]):
    """Base repository interface."""


class AsyncCacheRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """
    Repository with constructor parameters that use TYPE VARIABLES.

    This is the critical test case for type variable substitution.
    The constructor parameters CacheRepositoryOptions[TEntity, TKey] and
    CacheClientPool[TEntity, TKey] use type variables that must be substituted
    with concrete types when resolving dependencies.
    """

    def __init__(
        self,
        options: CacheRepositoryOptions[TEntity, TKey],
        pool: CacheClientPool[TEntity, TKey],
    ):
        self.options = options
        self.pool = pool


@dataclass
class MozartSession:
    """Example entity type."""

    id: str
    user_id: str = ""
    status: str = "active"


@dataclass
class User:
    """Another example entity."""

    id: int
    name: str = ""


class TestTypeVariableSubstitution:
    """Test suite for type variable substitution in DI container."""

    def test_single_type_variable_substitution(self):
        """Test substitution of a single type variable (TEntity -> MozartSession, TKey -> str)."""
        services = ServiceCollection()

        # Register concrete parameterized dependencies
        options = CacheRepositoryOptions[MozartSession, str](host="localhost", port=6379, entity_name="MozartSession", key_name="str")
        services.add_singleton(CacheRepositoryOptions[MozartSession, str], implementation_factory=lambda _: options)

        pool = CacheClientPool[MozartSession, str](max_connections=20, entity_type=MozartSession, key_type=str)
        services.add_singleton(CacheClientPool[MozartSession, str], implementation_factory=lambda _: pool)

        # Register repository with type variables in constructor
        services.add_transient(AsyncCacheRepository[MozartSession, str], AsyncCacheRepository[MozartSession, str])

        provider = services.build()

        # Attempt to build - this triggers type variable substitution
        repo = provider.get_required_service(AsyncCacheRepository[MozartSession, str])

        # Verify correct injection
        assert repo is not None
        assert isinstance(repo, AsyncCacheRepository)
        assert repo.options is options  # Same instance (singleton)
        assert repo.pool is pool  # Same instance (singleton)
        assert repo.options.host == "localhost"
        assert repo.pool.max_connections == 20

    def test_multiple_different_type_substitutions(self):
        """Test multiple repositories with different type substitutions."""
        services = ServiceCollection()

        # Register MozartSession options and pool
        session_options = CacheRepositoryOptions[MozartSession, str](host="session-redis", port=6379, entity_name="MozartSession")
        services.add_singleton(
            CacheRepositoryOptions[MozartSession, str],
            implementation_factory=lambda _: session_options,
        )

        session_pool = CacheClientPool[MozartSession, str](max_connections=10, entity_type=MozartSession)
        services.add_singleton(CacheClientPool[MozartSession, str], implementation_factory=lambda _: session_pool)

        # Register User options and pool (different types!)
        user_options = CacheRepositoryOptions[User, int](host="user-redis", port=6380, entity_name="User")
        services.add_singleton(CacheRepositoryOptions[User, int], implementation_factory=lambda _: user_options)

        user_pool = CacheClientPool[User, int](max_connections=20, entity_type=User)
        services.add_singleton(CacheClientPool[User, int], implementation_factory=lambda _: user_pool)

        # Register both repositories
        services.add_transient(AsyncCacheRepository[MozartSession, str], AsyncCacheRepository[MozartSession, str])
        services.add_transient(AsyncCacheRepository[User, int], AsyncCacheRepository[User, int])

        provider = services.build()

        # Build both repositories
        session_repo = provider.get_required_service(AsyncCacheRepository[MozartSession, str])
        user_repo = provider.get_required_service(AsyncCacheRepository[User, int])

        # Verify each got the correct dependencies
        assert session_repo.options.host == "session-redis"
        assert session_repo.pool.max_connections == 10
        assert user_repo.options.host == "user-redis"
        assert user_repo.pool.max_connections == 20

    def test_scoped_lifetime_with_type_variables(self):
        """Test type variable substitution works with scoped lifetime."""
        services = ServiceCollection()

        options = CacheRepositoryOptions[MozartSession, str](host="localhost", port=6379)
        services.add_singleton(CacheRepositoryOptions[MozartSession, str], implementation_factory=lambda _: options)

        pool = CacheClientPool[MozartSession, str](max_connections=20)
        services.add_singleton(CacheClientPool[MozartSession, str], implementation_factory=lambda _: pool)

        # Register as SCOPED
        services.add_scoped(AsyncCacheRepository[MozartSession, str], AsyncCacheRepository[MozartSession, str])

        provider = services.build()

        # Create scope and resolve
        scope = provider.create_scope()
        repo = scope.get_required_service(AsyncCacheRepository[MozartSession, str])

        assert repo is not None
        assert repo.options is options
        assert repo.pool is pool

        scope.dispose()

    def test_error_when_substituted_type_not_registered(self):
        """Test error message when substituted type cannot be resolved."""
        services = ServiceCollection()

        # Register pool but NOT options
        pool = CacheClientPool[MozartSession, str](max_connections=20)
        services.add_singleton(CacheClientPool[MozartSession, str], implementation_factory=lambda _: pool)

        # Register repository - will fail because options missing
        services.add_transient(AsyncCacheRepository[MozartSession, str], AsyncCacheRepository[MozartSession, str])

        provider = services.build()

        # Should raise exception with clear error message
        with pytest.raises(Exception) as exc_info:
            provider.get_required_service(AsyncCacheRepository[MozartSession, str])

        assert "CacheRepositoryOptions" in str(exc_info.value)

    def test_complex_nested_type_variable_substitution(self):
        """Test type variable substitution with nested generic types."""

        @dataclass
        class ComplexOptions(Generic[TEntity, TKey]):
            """Options that themselves have parameterized fields."""

            cache_options: CacheRepositoryOptions[TEntity, TKey]
            entity_type: type = None

        class ComplexRepository(Generic[TEntity, TKey]):
            def __init__(self, complex_opts: ComplexOptions[TEntity, TKey]):
                self.complex_opts = complex_opts

        services = ServiceCollection()

        # Register nested dependencies
        cache_options = CacheRepositoryOptions[MozartSession, str](host="localhost", port=6379)
        services.add_singleton(
            CacheRepositoryOptions[MozartSession, str],
            implementation_factory=lambda _: cache_options,
        )

        complex_options = ComplexOptions[MozartSession, str](cache_options=cache_options, entity_type=MozartSession)
        services.add_singleton(ComplexOptions[MozartSession, str], implementation_factory=lambda _: complex_options)

        services.add_transient(ComplexRepository[MozartSession, str], ComplexRepository[MozartSession, str])

        provider = services.build()

        # Build repository with nested generics
        repo = provider.get_required_service(ComplexRepository[MozartSession, str])

        assert repo is not None
        assert repo.complex_opts is complex_options
        assert repo.complex_opts.cache_options.host == "localhost"


class TestRegressionTypeVariableSubstitution:
    """Regression tests for specific reported issues."""

    def test_original_async_cache_repository_with_type_vars(self):
        """
        Test the exact pattern from the user's original bug report.

        This ensures that AsyncCacheRepository with constructor parameters
        using type variables (not concrete types) works correctly.
        """
        services = ServiceCollection()

        # This is the exact pattern that was failing before
        options = CacheRepositoryOptions[MozartSession, str](host="localhost", port=6379, entity_name="MozartSession", key_name="str")
        services.add_singleton(CacheRepositoryOptions[MozartSession, str], implementation_factory=lambda _: options)

        pool = CacheClientPool[MozartSession, str](max_connections=20, entity_type=MozartSession, key_type=str)
        services.add_singleton(CacheClientPool[MozartSession, str], implementation_factory=lambda _: pool)

        services.add_transient(AsyncCacheRepository[MozartSession, str], AsyncCacheRepository[MozartSession, str])

        provider = services.build()

        # This was throwing:
        # "Failed to build service of type 'AsyncCacheRepository' because the service provider
        #  failed to resolve service 'CacheRepositoryOptions'"
        # Because it was looking for CacheRepositoryOptions (base type) instead of
        # CacheRepositoryOptions[MozartSession, str] (substituted type)

        repo = provider.get_required_service(AsyncCacheRepository[MozartSession, str])

        assert repo is not None
        assert isinstance(repo, AsyncCacheRepository)
        assert repo.options.host == "localhost"
        assert repo.options.entity_name == "MozartSession"
        assert repo.pool.max_connections == 20
        assert repo.pool.entity_type == MozartSession
