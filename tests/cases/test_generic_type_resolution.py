"""
Test suite for generic type resolution in dependency injection.

This test suite validates that the DI container can properly resolve
generic types when they are used as constructor parameters.

Bug Report Reference: Generic Type Resolution in Dependency Injection
Issue: AttributeError when resolving parameterized generic types
Fix: Use typing.get_origin() and get_args() instead of manual __getitem__ calls
"""

from typing import Generic, TypeVar

import pytest

from neuroglia.dependency_injection import ServiceCollection

# Define generic type variables
TEntity = TypeVar("TEntity")
TKey = TypeVar("TKey")


# Test domain models
class User:
    """Test entity: User"""

    def __init__(self, user_id: int, name: str):
        self.id = user_id
        self.name = name


class Product:
    """Test entity: Product"""

    def __init__(self, product_id: str, title: str):
        self.id = product_id
        self.title = title


# Generic repository (the type that was failing)
class GenericRepository(Generic[TEntity, TKey]):
    """
    Generic repository implementation.

    This mimics the AsyncStringCacheRepository pattern that was failing.
    """

    def __init__(self, name: str):
        self.name = name
        self.entity_type = TEntity
        self.key_type = TKey

    def get_by_id(self, key: TKey) -> TEntity:
        """Mock method"""


# Service that depends on parameterized generic types
class UserService:
    """
    Service that depends on a parameterized generic repository.

    This pattern was causing: AttributeError: type object 'GenericRepository'
    has no attribute '__getitem__'
    """

    def __init__(self, user_repo: GenericRepository[User, int]):
        self.user_repo = user_repo


class MultiRepositoryService:
    """
    Service that depends on multiple parameterized generic repositories.

    This is the pattern used in MozartSessionCreatedEventHandler that was failing.
    """

    def __init__(
        self,
        user_repo: GenericRepository[User, int],
        product_repo: GenericRepository[Product, str],
    ):
        self.user_repo = user_repo
        self.product_repo = product_repo


class TestGenericTypeResolution:
    """Test cases for generic type resolution in DI container"""

    def test_resolve_single_parameterized_generic_dependency(self):
        """
        Test: Resolve service with single parameterized generic dependency

        This tests the exact scenario from the bug report:
        - Register a parameterized generic type (GenericRepository[User, int])
        - Try to resolve a service that depends on it (UserService)
        - Should succeed without AttributeError
        """
        # Arrange
        services = ServiceCollection()

        # Register the parameterized generic repository
        services.add_singleton(
            GenericRepository[User, int],
            implementation_factory=lambda _: GenericRepository[User, int]("users"),
        )

        # Register the service that depends on it
        services.add_transient(UserService, UserService)

        provider = services.build()

        # Act
        service = provider.get_required_service(UserService)

        # Assert
        assert service is not None
        assert isinstance(service, UserService)
        assert service.user_repo is not None
        assert service.user_repo.name == "users"

    def test_resolve_multiple_parameterized_generic_dependencies(self):
        """
        Test: Resolve service with multiple different parameterized generic dependencies

        This tests the MozartSessionCreatedEventHandler pattern:
        - Register multiple parameterized generic types with different type parameters
        - Try to resolve a service that depends on both
        - Should succeed and inject the correct instances
        """
        # Arrange
        services = ServiceCollection()

        # Register different parameterized versions of the same generic type
        services.add_singleton(
            GenericRepository[User, int],
            implementation_factory=lambda _: GenericRepository[User, int]("users"),
        )
        services.add_singleton(
            GenericRepository[Product, str],
            implementation_factory=lambda _: GenericRepository[Product, str]("products"),
        )

        # Register the service that depends on both
        services.add_transient(MultiRepositoryService, MultiRepositoryService)

        provider = services.build()

        # Act
        service = provider.get_required_service(MultiRepositoryService)

        # Assert
        assert service is not None
        assert isinstance(service, MultiRepositoryService)
        assert service.user_repo is not None
        assert service.user_repo.name == "users"
        assert service.product_repo is not None
        assert service.product_repo.name == "products"

    def test_resolve_generic_with_transient_lifetime(self):
        """
        Test: Generic type resolution with transient lifetime

        Ensures the fix works with different service lifetimes
        """
        # Arrange
        services = ServiceCollection()

        # Register as transient (new instance each time)
        services.add_transient(
            GenericRepository[User, int],
            implementation_factory=lambda _: GenericRepository[User, int]("users"),
        )
        services.add_transient(UserService, UserService)

        provider = services.build()

        # Act - Get service twice
        service1 = provider.get_required_service(UserService)
        service2 = provider.get_required_service(UserService)

        # Assert - Different instances due to transient lifetime
        assert service1 is not None
        assert service2 is not None
        assert service1 is not service2  # Different instances
        assert service1.user_repo is not service2.user_repo  # Different repo instances

    def test_resolve_generic_with_scoped_lifetime(self):
        """
        Test: Generic type resolution with scoped lifetime

        Ensures the fix works within scoped contexts
        """
        # Arrange
        services = ServiceCollection()

        # Register as scoped
        services.add_scoped(
            GenericRepository[User, int],
            implementation_factory=lambda _: GenericRepository[User, int]("users"),
        )
        services.add_scoped(UserService, UserService)

        provider = services.build()

        # Act - Create two scopes
        scope1 = provider.create_scope()
        service1a = scope1.get_required_service(UserService)
        service1b = scope1.get_required_service(UserService)
        scope1.dispose()

        scope2 = provider.create_scope()
        service2 = scope2.get_required_service(UserService)
        scope2.dispose()

        # Assert
        # Within same scope: same instances
        assert service1a is service1b
        assert service1a.user_repo is service1b.user_repo

        # Different scopes: different instances
        assert service1a is not service2
        assert service1a.user_repo is not service2.user_repo

    def test_non_generic_dependency_still_works(self):
        """
        Test: Ensure non-generic dependencies still work after the fix

        Regression test to ensure the fix doesn't break normal (non-generic) resolution
        """

        # Simple non-generic classes
        class Logger:
            def __init__(self):
                self.name = "Logger"

        class SimpleService:
            def __init__(self, logger: Logger):
                self.logger = logger

        # Arrange
        services = ServiceCollection()
        services.add_singleton(Logger, Logger)
        services.add_transient(SimpleService, SimpleService)

        provider = services.build()

        # Act
        service = provider.get_required_service(SimpleService)

        # Assert
        assert service is not None
        assert service.logger is not None
        assert service.logger.name == "Logger"

    def test_mixed_generic_and_non_generic_dependencies(self):
        """
        Test: Service with both generic and non-generic dependencies

        Real-world scenario where services have mixed dependency types
        """

        class Logger:
            def __init__(self):
                self.name = "Logger"

        class MixedService:
            def __init__(self, logger: Logger, user_repo: GenericRepository[User, int]):
                self.logger = logger
                self.user_repo = user_repo

        # Arrange
        services = ServiceCollection()
        services.add_singleton(Logger, Logger)
        services.add_singleton(
            GenericRepository[User, int],
            implementation_factory=lambda _: GenericRepository[User, int]("users"),
        )
        services.add_transient(MixedService, MixedService)

        provider = services.build()

        # Act
        service = provider.get_required_service(MixedService)

        # Assert
        assert service is not None
        assert service.logger is not None
        assert service.logger.name == "Logger"
        assert service.user_repo is not None
        assert service.user_repo.name == "users"

    def test_error_message_when_generic_not_registered(self):
        """
        Test: Clear error message when parameterized generic type is not registered

        Should get a clear error, not AttributeError about __getitem__
        """

        # Arrange
        services = ServiceCollection()
        # Intentionally NOT registering GenericRepository[User, int]
        services.add_transient(UserService, UserService)

        provider = services.build()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            provider.get_required_service(UserService)

        # Should be a meaningful DI error, not AttributeError about __getitem__
        assert "AttributeError" not in str(exc_info.value)
        assert "__getitem__" not in str(exc_info.value)


class TestRegressionScenarios:
    """
    Regression tests for specific scenarios from the bug report
    """

    def test_async_string_cache_repository_pattern(self):
        """
        Test: The exact pattern from AsyncStringCacheRepository that was failing

        This mimics:
        - AsyncStringCacheRepository[MozartSession, str]
        - AsyncStringCacheRepository[LdsSession, str]
        """

        # Mock domain models
        class MozartSession:
            pass

        class LdsSession:
            pass

        # Mock the AsyncStringCacheRepository pattern
        class AsyncStringCacheRepository(Generic[TEntity, TKey]):
            def __init__(self, cache_name: str):
                self.cache_name = cache_name

        # Mock the event handler that was failing
        class MozartSessionCreatedEventHandler:
            def __init__(
                self,
                mozart_repo: AsyncStringCacheRepository[MozartSession, str],
                lds_repo: AsyncStringCacheRepository[LdsSession, str],
            ):
                self.mozart_repo = mozart_repo
                self.lds_repo = lds_repo

        # Arrange
        services = ServiceCollection()
        services.add_transient(
            AsyncStringCacheRepository[MozartSession, str],
            implementation_factory=lambda _: AsyncStringCacheRepository[MozartSession, str]("mozart"),
        )
        services.add_transient(
            AsyncStringCacheRepository[LdsSession, str],
            implementation_factory=lambda _: AsyncStringCacheRepository[LdsSession, str]("lds"),
        )
        services.add_transient(MozartSessionCreatedEventHandler, MozartSessionCreatedEventHandler)

        provider = services.build()

        # Act - This was throwing AttributeError before the fix
        handler = provider.get_required_service(MozartSessionCreatedEventHandler)

        # Assert
        assert handler is not None
        assert handler.mozart_repo.cache_name == "mozart"
        assert handler.lds_repo.cache_name == "lds"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
