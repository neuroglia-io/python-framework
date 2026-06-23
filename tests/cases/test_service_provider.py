from neuroglia.dependency_injection.service_provider import ServiceProviderBase, ServiceCollection
from tests.services import FileLogger, LoggerBase, NullLogger, PrintLogger
import pytest


class ITestService:
    """Test service interface"""
    pass


class TestServiceImplementation(ITestService):
    """Basic test service implementation"""
    def __init__(self):
        self.instance_id = id(self)


class TestServiceWithDependency(ITestService):
    """Test service that depends on another service"""
    def __init__(self, logger: LoggerBase):
        self.logger = logger
        self.instance_id = id(self)


class TestServiceProvider:

    def test_build_should_work(self):
        # arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(LoggerBase, singleton=FileLogger())
        services.add_singleton(LoggerBase, implementation_factory=self._build_null_logger)

        # act
        service_provider = services.build()

        # assert
        assert service_provider is not None, 'service_provider is none'

    def test_get_service_should_work(self):
        # arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_singleton(LoggerBase, implementation_type)
        service_provider = services.build()

        # act
        logger = service_provider.get_service(LoggerBase)

        # assert
        assert logger is not None, 'logger is none'
        assert isinstance(logger, implementation_type), f"logger is not of expected type '{implementation_type.__name__}'"

    def test_get_unregistered_service_should_work(self):
        # arrange
        services = ServiceCollection()
        service_provider = services.build()

        # act
        logger = service_provider.get_service(LoggerBase)

        # assert
        assert logger is None, 'logger is not none'

    def test_get_required_service_should_work(self):
        # arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_singleton(LoggerBase, implementation_type)
        service_provider = services.build()

        # act
        logger = service_provider.get_required_service(LoggerBase)

        # assert
        assert logger is not None, 'logger is none'
        assert isinstance(logger, implementation_type), f"logger is not of expected type '{implementation_type.__name__}'"

    def test_get_required_unregistered_service_should_raise_error(self):
        # arrange
        services = ServiceCollection()
        service_provider = services.build()

        # assert
        with pytest.raises(Exception):
            service_provider.get_required_service(LoggerBase)

    def test_get_scoped_service_from_root_should_raise_error(self):
        # arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_scoped(LoggerBase, implementation_type)
        service_provider = services.build()

        # assert
        with pytest.raises(Exception):
            service_provider.get_service(LoggerBase)

    def test_get_services_should_work(self):
        # arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(LoggerBase, singleton=FileLogger())
        services.add_singleton(LoggerBase, implementation_factory=self._build_null_logger)
        service_provider = services.build()

        # act
        loggers = service_provider.get_services(LoggerBase)

        # assert
        assert len(loggers) == 3, f'expected 3 loggers, got {len(loggers)}'

    def test_singleton_service_returns_same_instance(self):
        """Test that singleton services return the same instance"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(ITestService, TestServiceImplementation)
        service_provider = services.build()

        # act
        service1 = service_provider.get_service(ITestService)
        service2 = service_provider.get_service(ITestService)

        # assert
        assert service1 is service2, 'singleton services should return same instance'
        assert service1.instance_id == service2.instance_id

    def test_transient_service_returns_different_instances(self):
        """Test that transient services return different instances"""
        # arrange
        services = ServiceCollection()
        services.add_transient(ITestService, TestServiceImplementation)
        service_provider = services.build()

        # act
        service1 = service_provider.get_service(ITestService)
        service2 = service_provider.get_service(ITestService)

        # assert
        assert service1 is not service2, 'transient services should return different instances'
        assert service1.instance_id != service2.instance_id

    def test_scoped_service_with_scope(self):
        """Test that scoped services work correctly within scopes"""
        # arrange
        services = ServiceCollection()
        services.add_scoped(ITestService, TestServiceImplementation)
        service_provider = services.build()

        # act & assert
        scope = service_provider.create_scope()
        try:
            scoped_provider = scope.get_service_provider()
            service1 = scoped_provider.get_service(ITestService)
            service2 = scoped_provider.get_service(ITestService)
            
            assert service1 is not None, 'service1 should not be none'
            assert service2 is not None, 'service2 should not be none'
            assert service1 is service2, 'scoped services should return same instance within scope'
            if hasattr(service1, 'instance_id') and hasattr(service2, 'instance_id'):
                assert service1.instance_id == service2.instance_id
        finally:
            scope.dispose()

    def test_service_with_dependency_injection(self):
        """Test that dependency injection works correctly"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(ITestService, TestServiceWithDependency)
        service_provider = services.build()

        # act
        service = service_provider.get_service(ITestService)

        # assert
        assert service is not None, 'service should not be none'
        assert isinstance(service, TestServiceWithDependency), 'service should be correct type'
        assert service.logger is not None, 'dependency should be injected'
        assert isinstance(service.logger, PrintLogger), 'dependency should be correct type'

    def test_implementation_factory(self):
        """Test that implementation factories work correctly"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(ITestService, implementation_factory=lambda _: TestServiceImplementation())
        service_provider = services.build()

        # act
        service = service_provider.get_service(ITestService)

        # assert
        assert service is not None, 'service should not be none'
        assert isinstance(service, TestServiceImplementation), 'service should be correct type'

    def test_singleton_instance_registration(self):
        """Test that singleton instance registration works correctly"""
        # arrange
        singleton_instance = TestServiceImplementation()
        services = ServiceCollection()
        services.add_singleton(ITestService, singleton=singleton_instance)
        service_provider = services.build()

        # act
        service1 = service_provider.get_service(ITestService)
        service2 = service_provider.get_service(ITestService)

        # assert
        assert service1 is singleton_instance, 'should return the registered singleton instance'
        assert service2 is singleton_instance, 'should return the same singleton instance'
        assert service1 is service2, 'should return same instance'

    def test_try_add_prevents_duplicate_registration(self):
        """Test that try_add methods prevent duplicate registrations"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(ITestService, TestServiceImplementation)
        
        # act
        services.try_add_singleton(ITestService, PrintLogger)  # This should be ignored
        service_provider = services.build()
        service = service_provider.get_service(ITestService)

        # assert
        assert isinstance(service, TestServiceImplementation), 'should use first registration'

    def test_service_provider_self_registration(self):
        """Test that ServiceProviderBase is automatically available"""
        # arrange
        services = ServiceCollection()
        service_provider = services.build()

        # act
        provider = service_provider.get_service(ServiceProviderBase)

        # assert
        assert provider is service_provider, 'should return self as ServiceProviderBase'

    def test_multiple_services_of_same_type(self):
        """Test that multiple services of the same type can be registered and retrieved"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(LoggerBase, NullLogger)
        service_provider = services.build()

        # act
        loggers = service_provider.get_services(LoggerBase)

        # assert
        assert len(loggers) == 2, 'should have 2 logger services'
        types = [type(logger) for logger in loggers]
        assert PrintLogger in types, 'should contain PrintLogger'
        assert NullLogger in types, 'should contain NullLogger'

    def test_create_scope_should_work(self):
        """Test that create_scope returns a valid scope"""
        # arrange
        services = ServiceCollection()
        service_provider = services.build()

        # act
        scope = service_provider.create_scope()

        # assert
        assert scope is not None, 'scope should not be none'
        assert scope.get_service_provider() is not None, 'scoped provider should not be none'

    def _build_null_logger(self, provider: ServiceProviderBase) -> NullLogger:
        return NullLogger()
