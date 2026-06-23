"""
Test suite for DI container error handling with string annotations (forward references).

This tests the bug fix for AttributeError when dependency resolution fails
on services with string-annotated constructor parameters.
"""

from typing import Generic, TypeVar

import pytest

from neuroglia.dependency_injection import ServiceCollection

# Test types
TEntity = TypeVar("TEntity")


class ForwardReferencedService:
    """A service that will be referenced as a string annotation."""

    def __init__(self):
        self.name = "ForwardReferencedService"


class ServiceWithStringAnnotation:
    """
    A service with string annotation (forward reference) in constructor.

    This simulates the pattern used in AsyncCacheRepository where JsonSerializer
    is quoted to avoid circular imports.
    """

    def __init__(self, dependency: "ForwardReferencedService"):
        self.dependency = dependency


class GenericServiceWithStringAnnotation(Generic[TEntity]):
    """Generic service with string annotation in constructor."""

    def __init__(self, dependency: "ForwardReferencedService", entity_type: type):
        self.dependency = dependency
        self.entity_type = entity_type


# Module-level classes for test_simulated_cache_repository_successful_resolution
# These must be at module level for get_type_hints() to resolve them correctly
class JsonSerializer:
    """Module-level JsonSerializer for testing."""


class CacheRepositoryOptions(Generic[TEntity]):
    """Module-level CacheRepositoryOptions for testing."""

    def __init__(self, host: str):
        self.host = host


class AsyncCacheRepository(Generic[TEntity]):
    """Module-level AsyncCacheRepository for testing."""

    def __init__(self, options: CacheRepositoryOptions[TEntity], serializer: "JsonSerializer"):
        self.options = options
        self.serializer = serializer


class MyEntity:
    """Module-level entity for testing."""


class TestStringAnnotationErrorHandling:
    """Test error handling for string annotations in constructor parameters."""

    def test_error_message_with_string_annotation_missing_dependency(self):
        """
        Test that missing dependency with string annotation shows helpful error.

        Before the fix: AttributeError: 'str' object has no attribute '__name__'
        After the fix: Exception with helpful message about missing dependency
        """
        services = ServiceCollection()

        # Register service WITH string annotation but WITHOUT its dependency
        # This should trigger the error path
        services.add_singleton(ServiceWithStringAnnotation, ServiceWithStringAnnotation)

        # Note: NOT registering ForwardReferencedService - this causes the error

        provider = services.build()

        # Try to resolve - should get helpful error message, not AttributeError
        with pytest.raises(Exception) as exc_info:
            provider.get_required_service(ServiceWithStringAnnotation)

        # Verify we got the helpful error message, not AttributeError
        error_message = str(exc_info.value)

        # Should mention the service type
        assert "ServiceWithStringAnnotation" in error_message or "string annotation" in error_message.lower()

        # Should mention the missing dependency (as string)
        assert "ForwardReferencedService" in error_message

        # Should NOT be an AttributeError about 'str' object
        assert not isinstance(exc_info.value, AttributeError)
        assert "'str' object has no attribute" not in error_message

    def test_error_message_with_string_annotation_successful_resolution(self):
        """
        Test that string annotation works correctly when dependency IS registered.
        """
        services = ServiceCollection()

        # Register BOTH service and its dependency
        services.add_singleton(ForwardReferencedService, ForwardReferencedService)
        services.add_singleton(ServiceWithStringAnnotation, ServiceWithStringAnnotation)

        provider = services.build()

        # Should resolve successfully
        service = provider.get_required_service(ServiceWithStringAnnotation)

        assert service is not None
        assert isinstance(service.dependency, ForwardReferencedService)
        assert service.dependency.name == "ForwardReferencedService"

    def test_generic_service_with_string_annotation_error(self):
        """
        Test error handling for generic service with string annotation.

        This simulates AsyncCacheRepository[Entity, str] with JsonSerializer dependency.
        """
        services = ServiceCollection()

        # Define a concrete entity type
        class MyEntity:
            pass

        # Register generic service WITHOUT the string-annotated dependency
        services.add_singleton(
            GenericServiceWithStringAnnotation[MyEntity],
            implementation_factory=lambda p: GenericServiceWithStringAnnotation(p.get_required_service(ForwardReferencedService), MyEntity),
        )

        # Note: NOT registering ForwardReferencedService

        provider = services.build()

        # Should get helpful error, not AttributeError
        with pytest.raises(Exception) as exc_info:
            provider.get_required_service(GenericServiceWithStringAnnotation[MyEntity])

        error_message = str(exc_info.value)

        # Should be a resolution error, not AttributeError
        assert not isinstance(exc_info.value, AttributeError)
        assert "ForwardReferencedService" in error_message

    def test_multiple_string_annotations_error_shows_first_missing(self):
        """
        Test that when multiple string-annotated dependencies are missing,
        the error shows the first one encountered.
        """

        class AnotherForwardRef:
            pass

        class ServiceWithMultipleStringAnnotations:
            def __init__(self, dep1: "ForwardReferencedService", dep2: "AnotherForwardRef"):
                self.dep1 = dep1
                self.dep2 = dep2

        services = ServiceCollection()
        services.add_singleton(ServiceWithMultipleStringAnnotations, ServiceWithMultipleStringAnnotations)

        provider = services.build()

        with pytest.raises(Exception) as exc_info:
            provider.get_required_service(ServiceWithMultipleStringAnnotations)

        error_message = str(exc_info.value)

        # Should mention one of the missing dependencies
        assert "ForwardReferencedService" in error_message or "AnotherForwardRef" in error_message

        # Should not be AttributeError
        assert not isinstance(exc_info.value, AttributeError)


class TestActualAsyncCacheRepositoryPattern:
    """
    Test the actual pattern used in AsyncCacheRepository to ensure the fix works.
    """

    def test_simulated_cache_repository_error_handling(self):
        """
        Simulate the exact AsyncCacheRepository pattern with JsonSerializer dependency.
        """

        # Simulate the actual imports and pattern from cache_repository.py
        class JsonSerializer:
            """Simulated JsonSerializer class."""

        class CacheRepositoryOptions(Generic[TEntity]):
            def __init__(self, host: str):
                self.host = host

        class AsyncCacheRepository(Generic[TEntity]):
            """
            Simulates the real AsyncCacheRepository with quoted JsonSerializer.
            """

            def __init__(self, options: CacheRepositoryOptions[TEntity], serializer: "JsonSerializer"):
                self.options = options
                self.serializer = serializer

        class MyEntity:
            pass

        services = ServiceCollection()

        # Register options but NOT JsonSerializer (triggers the bug)
        services.add_singleton(
            CacheRepositoryOptions[MyEntity],
            implementation_factory=lambda p: CacheRepositoryOptions("localhost"),
        )

        services.add_singleton(AsyncCacheRepository[MyEntity], AsyncCacheRepository[MyEntity])

        provider = services.build()

        # Should get helpful error about JsonSerializer, not AttributeError
        with pytest.raises(Exception) as exc_info:
            provider.get_required_service(AsyncCacheRepository[MyEntity])

        error_message = str(exc_info.value)

        # Should mention the missing JsonSerializer
        assert "JsonSerializer" in error_message

        # Should NOT be AttributeError about string
        assert not isinstance(exc_info.value, AttributeError)
        assert "'str' object has no attribute '__name__'" not in error_message

    def test_simulated_cache_repository_successful_resolution(self):
        """
        Test that AsyncCacheRepository pattern works when all dependencies are registered.

        Uses module-level classes so get_type_hints() can resolve forward references correctly.
        """
        services = ServiceCollection()

        # Register ALL dependencies (using module-level classes)
        services.add_singleton(JsonSerializer, JsonSerializer)
        services.add_singleton(
            CacheRepositoryOptions[MyEntity],
            implementation_factory=lambda p: CacheRepositoryOptions("localhost"),
        )
        services.add_singleton(AsyncCacheRepository[MyEntity], AsyncCacheRepository[MyEntity])

        provider = services.build()

        # Should resolve successfully
        repo = provider.get_required_service(AsyncCacheRepository[MyEntity])

        assert repo is not None
        assert isinstance(repo.serializer, JsonSerializer)
        assert repo.options.host == "localhost"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
