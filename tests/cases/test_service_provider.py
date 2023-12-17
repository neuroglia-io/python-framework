from sys import implementation
from neuroglia.dependency_injection.service_provider import ServiceCollection, ServiceProvider
from tests.services.services import FileLogger, LoggerBase, NullLogger, PrintLogger

class TestServiceProvider:
    
    def test_build_should_work():
        #arrange
        services = ServiceCollection()
        services.add_singleton(LoggerBase, PrintLogger)
        services.add_singleton(LoggerBase, singleton = FileLogger())
        services.add_singleton(LoggerBase, implementation_factory = lambda provider: NullLogger())
        
        #act
        service_provider = services.build()
        
        #assert
        assert service_provider is not None, 'service_provider is none'
    
    def test_get_service_should_work():
        #arrange
        services = ServiceCollection()
        implementation_type = PrintLogger
        services.add_singleton(LoggerBase, implementation_type)
        service_provider = services.build()
        
        #act
        logger = service_provider.get_service(LoggerBase)
        
        #assert
        assert logger is not None, 'logger is none'
        assert isinstance(logger, implementation_type), f"logger is not of expected type '{implementation_type.__name__}'"
    
    def test_get_unregistered_service_should_work():
        #arrange
        services = ServiceCollection()
        service_provider = services.build()

        #act
        logger = service_provider.get_service(LoggerBase)
        
        #assert
        assert logger is None, 'logger is not none'

    def test_get_required_service_should_work():
        pass
    
    def test_get_required_unregistered_service_should_raise_error():
        pass
    
    def test_get_scoped_service_from_root_should_raise_error():
        pass

    def test_get_services_should_work():
        pass
    
    def test_create_scope_should_work():
        pass
    
    def test_get_scoped_service_should_work():
        pass