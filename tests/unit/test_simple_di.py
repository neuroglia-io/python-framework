"""
Simple unit test to verify framework functionality.
"""

from abc import ABC, abstractmethod

import pytest

from neuroglia.dependency_injection.service_provider import ServiceCollection

# Simple test interfaces and implementations


class ITestService(ABC):
    """Test service interface"""

    @abstractmethod
    def get_message(self) -> str:
        pass


class TestService(ITestService):
    """Test service implementation"""

    def __init__(self, message: str = "Hello World"):
        self.message = message
        self.call_count = 0

    def get_message(self) -> str:
        self.call_count += 1
        return f"{self.message} - Call #{self.call_count}"


class AnotherTestService(ITestService):
    """Alternative test service implementation"""

    def get_message(self) -> str:
        return "Another implementation"


# Simple tests for dependency injection


class TestServiceCollection:
    def test_service_collection_creation(self):
        """Test creating service collection"""
        collection = ServiceCollection()
        assert collection is not None
        assert len(collection) == 0  # ServiceCollection inherits from List

    def test_add_singleton_instance(self):
        """Test adding singleton instance"""
        collection = ServiceCollection()
        service = TestService("Test Message")

        collection.add_singleton(ITestService, singleton=service)

        assert len(collection) == 1

        # Build provider and test
        provider = collection.build()
        retrieved_service = provider.get_service(ITestService)

        assert retrieved_service is not None
        assert retrieved_service is service
        assert retrieved_service.get_message() == "Test Message - Call #1"

    def test_add_singleton_type(self):
        """Test adding singleton type"""
        collection = ServiceCollection()

        collection.add_singleton(ITestService, implementation_type=TestService)

        assert len(collection) == 1

        # Build provider and test
        provider = collection.build()

        # Get service multiple times
        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)

        assert service1 is not None
        assert isinstance(service1, TestService)
        assert service1 is service2  # Same instance for singleton

    def test_add_transient_service(self):
        """Test adding transient service"""
        collection = ServiceCollection()

        collection.add_transient(ITestService, implementation_type=TestService)

        assert len(collection) == 1

        # Build provider and test
        provider = collection.build()

        # Get service multiple times
        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)

        assert service1 is not None
        assert isinstance(service1, TestService)
        assert service2 is not None
        assert isinstance(service2, TestService)
        assert service1 is not service2  # Different instances for transient

    def test_multiple_service_registrations(self):
        """Test registering multiple services"""
        collection = ServiceCollection()

        # Add multiple implementations
        collection.add_singleton(ITestService, implementation_type=TestService)
        collection.add_singleton(ITestService, implementation_type=AnotherTestService)

        provider = collection.build()

        # Should get the last registered implementation
        service = provider.get_service(ITestService)
        assert isinstance(service, AnotherTestService)
        assert service.get_message() == "Another implementation"

    def test_get_services_multiple(self):
        """Test getting multiple services of same type"""
        collection = ServiceCollection()

        collection.add_singleton(ITestService, implementation_type=TestService)
        collection.add_singleton(ITestService, implementation_type=AnotherTestService)

        provider = collection.build()

        services = provider.get_services(ITestService)
        assert len(services) == 2

        # Check that we get both implementations
        service_types = [type(service) for service in services]
        assert TestService in service_types
        assert AnotherTestService in service_types

    def test_get_required_service_success(self):
        """Test get_required_service when service exists"""
        collection = ServiceCollection()
        collection.add_singleton(ITestService, implementation_type=TestService)

        provider = collection.build()

        service = provider.get_required_service(ITestService)
        assert service is not None
        assert isinstance(service, TestService)

    def test_get_required_service_failure(self):
        """Test get_required_service when service doesn't exist"""
        collection = ServiceCollection()
        provider = collection.build()

        with pytest.raises(Exception):  # Should raise exception for missing service
            provider.get_required_service(ITestService)

    def test_get_service_returns_none_when_missing(self):
        """Test get_service returns None when service doesn't exist"""
        collection = ServiceCollection()
        provider = collection.build()

        service = provider.get_service(ITestService)
        assert service is None


# Test basic functionality


class TestBasicFunctionality:
    def test_service_functionality(self):
        """Test that our test service works correctly"""
        service = TestService("Test")

        # Test basic functionality
        message1 = service.get_message()
        message2 = service.get_message()

        assert message1 == "Test - Call #1"
        assert message2 == "Test - Call #2"
        assert service.call_count == 2

    def test_service_inheritance(self):
        """Test that service inheritance works"""
        service = TestService()
        assert isinstance(service, ITestService)

        another_service = AnotherTestService()
        assert isinstance(another_service, ITestService)

        # Both implement the interface
        assert hasattr(service, "get_message")
        assert hasattr(another_service, "get_message")
        assert callable(service.get_message)
        assert callable(another_service.get_message)


# Test service lifetimes


class TestServiceLifetimes:
    def test_singleton_lifetime(self):
        """Test singleton service lifetime"""
        collection = ServiceCollection()
        collection.add_singleton(ITestService, implementation_type=TestService)

        provider = collection.build()

        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)

        # Same instance
        assert service1 is service2

        # State is shared
        message1 = service1.get_message()  # Call #1
        message2 = service2.get_message()  # Call #2 (same instance)

        assert message1 == "Hello World - Call #1"
        assert message2 == "Hello World - Call #2"

    def test_transient_lifetime(self):
        """Test transient service lifetime"""
        collection = ServiceCollection()
        collection.add_transient(ITestService, implementation_type=TestService)

        provider = collection.build()

        service1 = provider.get_service(ITestService)
        service2 = provider.get_service(ITestService)

        # Different instances
        assert service1 is not service2

        # Independent state
        message1 = service1.get_message()  # Call #1 on instance 1
        message2 = service2.get_message()  # Call #1 on instance 2

        assert message1 == "Hello World - Call #1"
        assert message2 == "Hello World - Call #1"  # Independent counter

    def test_scoped_lifetime(self):
        """Test scoped service lifetime"""
        collection = ServiceCollection()
        collection.add_scoped(ITestService, implementation_type=TestService)

        provider = collection.build()

        # Create scope
        with provider.create_scope() as scope:
            service1 = scope.get_service(ITestService)
            service2 = scope.get_service(ITestService)

            # Same instance within scope
            assert service1 is service2

        # New scope should create new instance
        with provider.create_scope() as scope:
            service3 = scope.get_service(ITestService)
            assert service3 is not service1
            assert service3 is not service2
