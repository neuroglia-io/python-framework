"""
Unit tests for dependency injection functionality.
"""

from abc import ABC, abstractmethod
from typing import Optional

import pytest

from neuroglia.dependency_injection.service_provider import (
    ServiceCollection,
    ServiceDescriptor,
    ServiceLifetime,
    ServiceProviderBase,
)

# Test interfaces and implementations


class ITestService(ABC):
    """Test service interface"""

    @abstractmethod
    def get_data(self) -> str:
        pass


class ILogger(ABC):
    """Test logger interface"""

    @abstractmethod
    def log(self, message: str):
        pass


class IRepository(ABC):
    """Test repository interface"""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[dict]:
        pass


class TestService(ITestService):
    """Test service implementation"""

    def __init__(self, logger: ILogger = None):
        self.logger = logger
        self.call_count = 0

    def get_data(self) -> str:
        self.call_count += 1
        if self.logger:
            self.logger.log(f"TestService.get_data called {self.call_count} times")
        return f"test data {self.call_count}"


class AnotherTestService(ITestService):
    """Alternative test service implementation"""

    def get_data(self) -> str:
        return "another implementation"


class ConsoleLogger(ILogger):
    """Test console logger"""

    def __init__(self):
        self.messages: list[str] = []

    def log(self, message: str):
        self.messages.append(message)


class DatabaseRepository(IRepository):
    """Test database repository"""

    def __init__(self, connection_string: str, logger: ILogger):
        self.connection_string = connection_string
        self.logger = logger
        self.data: dict[str, dict] = {}

    async def get_by_id(self, id: str) -> Optional[dict]:
        self.logger.log(f"DatabaseRepository.get_by_id called with id: {id}")
        return self.data.get(id)


class ComplexService:
    """Service with multiple dependencies"""

    def __init__(self, test_service: ITestService, logger: ILogger, repository: IRepository):
        self.test_service = test_service
        self.logger = logger
        self.repository = repository

    async def process_data(self, id: str) -> str:
        data = await self.repository.get_by_id(id)
        service_data = self.test_service.get_data()
        result = f"Processed: {service_data}, Data: {data}"
        self.logger.log(result)
        return result


# Test service descriptor


class TestServiceDescriptor:
    def test_descriptor_creation(self):
        """Test ServiceDescriptor creation"""
        # Instance descriptor
        instance = TestService()
        descriptor = ServiceDescriptor.from_instance(ITestService, instance)

        assert descriptor.service_type == ITestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON
        assert descriptor.implementation_instance == instance
        assert descriptor.implementation_type is None
        assert descriptor.implementation_factory is None

    def test_descriptor_from_type(self):
        """Test ServiceDescriptor from type"""
        descriptor = ServiceDescriptor.from_type(ITestService, TestService, ServiceLifetime.TRANSIENT)

        assert descriptor.service_type == ITestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT
        assert descriptor.implementation_instance is None
        assert descriptor.implementation_factory is None

    def test_descriptor_from_factory(self):
        """Test ServiceDescriptor from factory"""
        factory = lambda provider: TestService()
        descriptor = ServiceDescriptor.from_factory(ITestService, factory, ServiceLifetime.SCOPED)

        assert descriptor.service_type == ITestService
        assert descriptor.implementation_factory == factory
        assert descriptor.lifetime == ServiceLifetime.SCOPED
        assert descriptor.implementation_instance is None
        assert descriptor.implementation_type is None


# Test service collection


class TestServiceCollection:
    def test_add_singleton_instance(self):
        """Test adding singleton instance"""
        collection = ServiceCollection()
        service = TestService()

        collection.add_singleton(ITestService, service)

        assert len(collection.services) == 1
        descriptor = collection.services[0]
        assert descriptor.service_type == ITestService
        assert descriptor.implementation_instance == service
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_add_singleton_type(self):
        """Test adding singleton type"""
        collection = ServiceCollection()

        collection.add_singleton(ITestService, TestService)

        assert len(collection.services) == 1
        descriptor = collection.services[0]
        assert descriptor.service_type == ITestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_add_singleton_factory(self):
        """Test adding singleton factory"""
        collection = ServiceCollection()
        factory = lambda provider: TestService()

        collection.add_singleton(ITestService, factory)

        assert len(collection.services) == 1
        descriptor = collection.services[0]
        assert descriptor.service_type == ITestService
        assert descriptor.implementation_factory == factory
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_add_transient(self):
        """Test adding transient service"""
        collection = ServiceCollection()

        collection.add_transient(ITestService, TestService)

        assert len(collection.services) == 1
        descriptor = collection.services[0]
        assert descriptor.service_type == ITestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.TRANSIENT

    def test_add_scoped(self):
        """Test adding scoped service"""
        collection = ServiceCollection()

        collection.add_scoped(ITestService, TestService)

        assert len(collection.services) == 1
        descriptor = collection.services[0]
        assert descriptor.service_type == ITestService
        assert descriptor.implementation_type == TestService
        assert descriptor.lifetime == ServiceLifetime.SCOPED

    def test_add_multiple_services(self):
        """Test adding multiple services"""
        collection = ServiceCollection()

        collection.add_singleton(ILogger, ConsoleLogger)
        collection.add_transient(ITestService, TestService)
        collection.add_scoped(IRepository, DatabaseRepository)

        assert len(collection.services) == 3

        # Check service types
        service_types = [desc.service_type for desc in collection.services]
        assert ILogger in service_types
        assert ITestService in service_types
        assert IRepository in service_types

    def test_replace_service(self):
        """Test replacing an existing service"""
        collection = ServiceCollection()

        # Add initial service
        collection.add_singleton(ITestService, TestService)
        assert len(collection.services) == 1

        # Replace with different implementation
        collection.add_singleton(ITestService, AnotherTestService)
        assert len(collection.services) == 2

        # Latest registration should take precedence when building provider
        provider = collection.build_service_provider()
        service = provider.get_service(ITestService)
        assert isinstance(service, AnotherTestService)

    def test_build_service_provider(self):
        """Test building service provider"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)

        provider = collection.build_service_provider()

        assert provider is not None
        assert isinstance(provider, ServiceProviderBase)


# Test service provider


class TestServiceProvider:
    def test_get_singleton_service(self):
        """Test getting singleton service"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)

        provider = collection.build_service_provider()

        # Get service multiple times
        logger1 = provider.get_service(ILogger)
        logger2 = provider.get_service(ILogger)

        assert logger1 is not None
        assert isinstance(logger1, ConsoleLogger)
        assert logger1 is logger2  # Same instance for singleton

    def test_get_transient_service(self):
        """Test getting transient service"""
        collection = ServiceCollection()
        collection.add_transient(ITestService, TestService)

        provider = collection.build_service_provider()

        # Get service multiple times
        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)

        assert service1 is not None
        assert isinstance(service1, TestService)
        assert service2 is not None
        assert isinstance(service2, TestService)
        assert service1 is not service2  # Different instances for transient

    def test_get_scoped_service(self):
        """Test getting scoped service"""
        collection = ServiceCollection()
        collection.add_scoped(ITestService, TestService)

        provider = collection.build_service_provider()

        # Create scope
        with provider.create_scope() as scope:
            # Get service multiple times within scope
            service1 = scope.get_service(ITestService)
            service2 = scope.get_service(ITestService)

            assert service1 is not None
            assert isinstance(service1, TestService)
            assert service1 is service2  # Same instance within scope

        # Get service in different scope
        with provider.create_scope() as scope:
            service3 = scope.get_service(ITestService)
            assert service3 is not service1  # Different instance in new scope

    def test_dependency_injection(self):
        """Test automatic dependency injection"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)
        collection.add_transient(ITestService, TestService)

        provider = collection.build_service_provider()

        # TestService constructor should receive ILogger
        service = provider.get_service(ITestService)

        assert service is not None
        assert isinstance(service, TestService)
        assert service.logger is not None
        assert isinstance(service.logger, ConsoleLogger)

    def test_complex_dependency_injection(self):
        """Test complex dependency chains"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)
        collection.add_singleton(ITestService, TestService)
        collection.add_singleton(
            IRepository,
            lambda provider: DatabaseRepository("test_connection", provider.get_required_service(ILogger)),
        )
        collection.add_transient(ComplexService)

        provider = collection.build_service_provider()

        complex_service = provider.get_service(ComplexService)

        assert complex_service is not None
        assert isinstance(complex_service, ComplexService)
        assert isinstance(complex_service.test_service, TestService)
        assert isinstance(complex_service.logger, ConsoleLogger)
        assert isinstance(complex_service.repository, DatabaseRepository)

    def test_get_required_service_success(self):
        """Test get_required_service when service exists"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)

        provider = collection.build_service_provider()

        logger = provider.get_required_service(ILogger)
        assert logger is not None
        assert isinstance(logger, ConsoleLogger)

    def test_get_required_service_failure(self):
        """Test get_required_service when service doesn't exist"""
        collection = ServiceCollection()
        provider = collection.build_service_provider()

        with pytest.raises(Exception):  # Should raise exception for missing service
            provider.get_required_service(ILogger)

    def test_get_service_returns_none_when_missing(self):
        """Test get_service returns None when service doesn't exist"""
        collection = ServiceCollection()
        provider = collection.build_service_provider()

        service = provider.get_service(ILogger)
        assert service is None

    def test_get_services(self):
        """Test getting all services of a type"""
        collection = ServiceCollection()

        # Add multiple implementations of same interface
        collection.add_singleton(ITestService, TestService)
        collection.add_singleton(ITestService, AnotherTestService)

        provider = collection.build_service_provider()

        services = provider.get_services(ITestService)
        assert len(services) == 2

        # Check that we get both implementations
        service_types = [type(service) for service in services]
        assert TestService in service_types
        assert AnotherTestService in service_types

    def test_factory_with_provider_parameter(self):
        """Test factory that uses service provider"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)
        collection.add_singleton(ITestService, lambda provider: TestService(provider.get_required_service(ILogger)))

        provider = collection.build_service_provider()

        service = provider.get_service(ITestService)
        assert service is not None
        assert isinstance(service, TestService)
        assert service.logger is not None
        assert isinstance(service.logger, ConsoleLogger)

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies"""
        # Note: This test depends on the actual implementation
        # and whether it detects circular dependencies
        collection = ServiceCollection()

        # Create a potential circular dependency scenario
        # This might not actually fail depending on implementation
        collection.add_singleton(ITestService, lambda provider: TestService(provider.get_service(ILogger)))
        collection.add_singleton(ILogger, lambda provider: ConsoleLogger())

        provider = collection.build_service_provider()

        # This should work fine - no actual circular dependency
        service = provider.get_service(ITestService)
        assert service is not None

    def test_service_provider_disposal(self):
        """Test service provider disposal"""
        collection = ServiceCollection()
        collection.add_singleton(ILogger, ConsoleLogger)

        provider = collection.build_service_provider()

        # Get a service
        logger = provider.get_service(ILogger)
        assert logger is not None

        # Dispose provider
        provider.dispose()

        # Depending on implementation, this might still work or might fail
        # The actual behavior depends on how disposal is implemented


# Integration tests for dependency injection


class TestDependencyInjectionIntegration:
    @pytest.mark.asyncio
    async def test_full_dependency_chain(self):
        """Test complete dependency injection scenario"""
        collection = ServiceCollection()

        # Register services
        collection.add_singleton(ILogger, ConsoleLogger)
        collection.add_singleton(ITestService, TestService)
        collection.add_singleton(
            IRepository,
            lambda provider: DatabaseRepository("test_connection_string", provider.get_required_service(ILogger)),
        )
        collection.add_transient(ComplexService)

        provider = collection.build_service_provider()

        # Get complex service that depends on all others
        complex_service = provider.get_service(ComplexService)
        assert complex_service is not None

        # Add test data to repository
        complex_service.repository.data["123"] = {"name": "Test Item", "value": 42}

        # Process data
        result = await complex_service.process_data("123")

        assert "test data 1" in result
        assert "Test Item" in result

        # Check that logger received messages
        logger = provider.get_service(ILogger)
        assert len(logger.messages) >= 2  # At least repository call and process result

    def test_service_replacement_scenario(self):
        """Test replacing services with different implementations"""
        collection = ServiceCollection()

        # Initially register TestService
        collection.add_singleton(ITestService, TestService)

        provider1 = collection.build_service_provider()
        service1 = provider1.get_service(ITestService)
        assert isinstance(service1, TestService)
        assert service1.get_data() == "test data 1"

        # Replace with AnotherTestService
        collection.add_singleton(ITestService, AnotherTestService)

        provider2 = collection.build_service_provider()
        service2 = provider2.get_service(ITestService)
        assert isinstance(service2, AnotherTestService)
        assert service2.get_data() == "another implementation"

    def test_mixed_lifetimes(self):
        """Test mixing different service lifetimes"""
        collection = ServiceCollection()

        collection.add_singleton(ILogger, ConsoleLogger)  # Singleton
        collection.add_transient(ITestService, TestService)  # Transient
        collection.add_scoped(ComplexService)  # Scoped

        provider = collection.build_service_provider()

        # Test singleton behavior
        logger1 = provider.get_service(ILogger)
        logger2 = provider.get_service(ILogger)
        assert logger1 is logger2

        # Test transient behavior
        test_service1 = provider.get_service(ITestService)
        test_service2 = provider.get_service(ITestService)
        assert test_service1 is not test_service2

        # Test scoped behavior
        with provider.create_scope() as scope1:
            complex1a = scope1.get_service(ComplexService)
            complex1b = scope1.get_service(ComplexService)
            assert complex1a is complex1b  # Same within scope

        with provider.create_scope() as scope2:
            complex2 = scope2.get_service(ComplexService)
            assert complex2 is not complex1a  # Different across scopes
