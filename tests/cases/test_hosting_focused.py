from unittest.mock import Mock, patch
import pytest
from fastapi import FastAPI

from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.hosting.web import (
    WebApplicationBuilder, WebApplicationBuilderBase,
    ExceptionHandlingMiddleware
)
from neuroglia.hosting.abstractions import HostBase, HostedService, ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer


class TestWebApplicationBuilder:
    """Test WebApplicationBuilder functionality"""

    def test_web_application_builder_initialization(self):
        """Test WebApplicationBuilder initialization"""
        # act
        builder = WebApplicationBuilder()

        # assert
        assert isinstance(builder, WebApplicationBuilderBase)
        assert isinstance(builder, ApplicationBuilderBase)
        assert builder.services is not None
        assert isinstance(builder.services, ServiceCollection)

    def test_web_application_builder_service_registration(self):
        """Test service registration through builder"""
        # arrange
        builder = WebApplicationBuilder()
        
        # act
        builder.services.add_singleton(JsonSerializer)
        provider = builder.services.build()

        # assert
        json_serializer = provider.get_service(JsonSerializer)
        assert json_serializer is not None
        assert isinstance(json_serializer, JsonSerializer)

    @patch('neuroglia.core.ModuleLoader.load')
    @patch('neuroglia.core.TypeFinder.get_types')
    def test_add_controllers_method(self, mock_get_types, mock_load):
        """Test add_controllers method"""
        # arrange
        builder = WebApplicationBuilder()
        
        # Mock controller class
        class MockController:
            pass

        mock_module = Mock()
        mock_load.return_value = mock_module
        mock_get_types.return_value = [MockController]

        # act
        result = builder.add_controllers(["test.controllers"])

        # assert
        assert result == builder.services
        mock_load.assert_called_once_with("test.controllers")
        mock_get_types.assert_called_once()

    def test_multiple_service_registrations(self):
        """Test multiple service registrations in builder"""
        # arrange
        builder = WebApplicationBuilder()

        class TestService:
            pass

        class AnotherService:
            pass

        # act
        builder.services.add_singleton(TestService)
        builder.services.add_singleton(AnotherService)
        builder.services.add_singleton(JsonSerializer)
        provider = builder.services.build()

        # assert
        assert provider.get_service(TestService) is not None
        assert provider.get_service(AnotherService) is not None
        assert provider.get_service(JsonSerializer) is not None


class TestExceptionHandlingMiddleware:
    """Test ExceptionHandlingMiddleware functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_service_provider = Mock()
        self.mock_json_serializer = Mock()
        self.mock_service_provider.get_required_service.return_value = self.mock_json_serializer

    def test_exception_middleware_initialization(self):
        """Test exception middleware initialization"""
        # arrange
        mock_app = Mock()

        # act
        middleware = ExceptionHandlingMiddleware(mock_app, self.mock_service_provider)

        # assert
        assert middleware.service_provider == self.mock_service_provider
        assert middleware.serializer == self.mock_json_serializer

    @pytest.mark.asyncio
    async def test_exception_middleware_normal_request(self):
        """Test middleware behavior with normal request"""
        # arrange
        mock_app = Mock()
        middleware = ExceptionHandlingMiddleware(mock_app, self.mock_service_provider)
        
        mock_request = Mock()
        mock_response = Mock()
        
        async def mock_call_next(request):
            return mock_response

        # act
        result = await middleware.dispatch(mock_request, mock_call_next)

        # assert
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_exception_middleware_handles_exception(self):
        """Test middleware behavior when exception occurs"""
        # arrange
        mock_app = Mock()
        middleware = ExceptionHandlingMiddleware(mock_app, self.mock_service_provider)
        
        mock_request = Mock()
        exception_message = "Test exception"
        
        async def mock_call_next(request):
            raise Exception(exception_message)

        # Configure serializer mock
        expected_json = '{"title": "Internal Server Error", "status": 500, "detail": "Test exception"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # act
        result = await middleware.dispatch(mock_request, mock_call_next)

        # assert
        assert result.status_code == 500
        assert result.media_type == "application/json"
        # Verify serializer was called with ProblemDetails
        self.mock_json_serializer.serialize_to_text.assert_called_once()
        call_args = self.mock_json_serializer.serialize_to_text.call_args[0][0]
        assert call_args.status == 500
        assert call_args.title == "Internal Server Error"
        assert exception_message in call_args.detail


class TestHostBase:
    """Test HostBase abstract functionality"""

    def test_host_base_is_abstract(self):
        """Test that HostBase cannot be instantiated directly"""
        # act & assert
        try:
            # This should raise TypeError due to abstract methods
            # Using type: ignore to suppress the expected type error
            HostBase()  # type: ignore
            assert False, "Should not be able to instantiate abstract class"
        except TypeError:
            pass  # Expected behavior

    def test_host_base_defines_interface(self):
        """Test that HostBase defines required interface"""
        # assert
        assert hasattr(HostBase, 'start_async')
        assert hasattr(HostBase, 'stop_async')
        assert hasattr(HostBase, 'run')
        assert hasattr(HostBase, 'dispose')

    def test_host_base_concrete_implementation(self):
        """Test concrete implementation of HostBase"""
        # arrange
        class ConcreteHost(HostBase):
            def __init__(self):
                self.services = Mock()
                self.started = False
                self.stopped = False

            async def start_async(self):
                self.started = True

            async def stop_async(self):
                self.stopped = True

            def dispose(self):
                pass

        # act
        host = ConcreteHost()

        # assert
        assert host.services is not None
        assert hasattr(host, 'start_async')
        assert hasattr(host, 'stop_async')
        assert hasattr(host, 'run')
        assert hasattr(host, 'dispose')


class TestHostedService:
    """Test HostedService functionality"""

    def test_hosted_service_initialization(self):
        """Test HostedService initialization"""
        # act
        service = HostedService()

        # assert
        assert service is not None
        assert hasattr(service, 'start_async')
        assert hasattr(service, 'stop_async')

    @pytest.mark.asyncio
    async def test_hosted_service_lifecycle(self):
        """Test HostedService lifecycle methods"""
        # arrange
        service = HostedService()

        # act
        await service.start_async()  # Should not raise
        await service.stop_async()   # Should not raise

        # assert - no exceptions means success for base implementation

    def test_hosted_service_custom_implementation(self):
        """Test custom HostedService implementation"""
        # arrange
        class CustomHostedService(HostedService):
            def __init__(self):
                self.started = False
                self.stopped = False

            async def start_async(self):
                self.started = True

            async def stop_async(self):
                self.stopped = True

        service = CustomHostedService()

        # act & assert
        assert not service.started
        assert not service.stopped

    @pytest.mark.asyncio
    async def test_custom_hosted_service_lifecycle(self):
        """Test custom HostedService lifecycle execution"""
        # arrange
        class CustomHostedService(HostedService):
            def __init__(self):
                self.started = False
                self.stopped = False

            async def start_async(self):
                self.started = True

            async def stop_async(self):
                self.stopped = True

        service = CustomHostedService()

        # act
        await service.start_async()
        await service.stop_async()

        # assert
        assert service.started
        assert service.stopped


class TestApplicationLifecycle:
    """Test application lifecycle and integration scenarios"""

    def test_end_to_end_application_setup(self):
        """Test complete application setup workflow"""
        # arrange
        builder = WebApplicationBuilder()

        # act
        builder.services.add_singleton(JsonSerializer)
        provider = builder.services.build()

        # assert
        assert builder.services is not None
        assert provider.get_service(JsonSerializer) is not None

    def test_multiple_service_types_registration(self):
        """Test registration of multiple service types"""
        # arrange
        builder = WebApplicationBuilder()

        class ServiceA:
            pass

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

        # act
        builder.services.add_singleton(ServiceA)
        builder.services.add_singleton(ServiceB)
        builder.services.add_singleton(JsonSerializer)
        provider = builder.services.build()

        # assert
        service_b = provider.get_service(ServiceB)
        assert service_b is not None
        assert service_b.service_a is not None
        assert isinstance(service_b.service_a, ServiceA)

    def test_builder_service_chaining(self):
        """Test builder service registration patterns"""
        # arrange & act
        builder = WebApplicationBuilder()
        builder.services.add_singleton(JsonSerializer)
        builder.services.add_singleton(str, implementation_factory=lambda _: "test")

        provider = builder.services.build()

        # assert
        assert provider.get_service(JsonSerializer) is not None
        assert provider.get_service(str) == "test"


class TestHostingIntegrationPatterns:
    """Test hosting integration patterns and scenarios"""

    def test_service_provider_integration(self):
        """Test service provider integration in hosting"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)

        class TestService:
            def __init__(self, json_serializer: JsonSerializer):
                self.json_serializer = json_serializer

        services.add_singleton(TestService)
        provider = services.build()

        # act
        test_service = provider.get_service(TestService)

        # assert
        assert test_service is not None
        assert isinstance(test_service.json_serializer, JsonSerializer)

    def test_middleware_integration_pattern(self):
        """Test middleware integration pattern"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        provider = services.build()

        mock_app = FastAPI()

        # act
        middleware = ExceptionHandlingMiddleware(mock_app, provider)

        # assert
        assert middleware.service_provider == provider
        assert isinstance(middleware.serializer, JsonSerializer)

    @pytest.mark.asyncio
    async def test_exception_handling_workflow(self):
        """Test complete exception handling workflow"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        provider = services.build()

        mock_app = FastAPI()
        middleware = ExceptionHandlingMiddleware(mock_app, provider)

        mock_request = Mock()
        
        async def failing_call_next(request):
            raise ValueError("Test validation error")

        # act
        response = await middleware.dispatch(mock_request, failing_call_next)

        # assert
        assert response.status_code == 500
        assert response.media_type == "application/json"
        # Response content should contain error information
        assert b"Internal Server Error" in response.body or b"Test validation error" in response.body

    def test_application_builder_patterns(self):
        """Test common application builder patterns"""
        # arrange
        builder = WebApplicationBuilder()

        class DatabaseService:
            pass

        class CacheService:
            pass

        class BusinessService:
            def __init__(self, db: DatabaseService, cache: CacheService):
                self.db = db
                self.cache = cache

        # act
        builder.services.add_singleton(DatabaseService)
        builder.services.add_singleton(CacheService)
        builder.services.add_singleton(BusinessService)
        builder.services.add_singleton(JsonSerializer)

        provider = builder.services.build()
        business_service = provider.get_service(BusinessService)

        # assert
        assert business_service is not None
        assert isinstance(business_service.db, DatabaseService)
        assert isinstance(business_service.cache, CacheService)

    @pytest.mark.asyncio
    async def test_hosted_service_integration(self):
        """Test hosted service integration patterns"""
        # arrange
        class BackgroundService(HostedService):
            def __init__(self):
                self.tasks_processed = 0
                self.is_running = False

            async def start_async(self):
                self.is_running = True

            async def stop_async(self):
                self.is_running = False

            async def process_task(self):
                if self.is_running:
                    self.tasks_processed += 1

        # act
        service = BackgroundService()
        await service.start_async()
        await service.process_task()
        await service.stop_async()

        # assert
        assert service.tasks_processed == 1
        assert not service.is_running

    def test_dependency_resolution_chain(self):
        """Test complex dependency resolution chains"""
        # arrange
        services = ServiceCollection()

        class Level1Service:
            pass

        class Level2Service:
            def __init__(self, level1: Level1Service):
                self.level1 = level1

        class Level3Service:
            def __init__(self, level2: Level2Service, json_serializer: JsonSerializer):
                self.level2 = level2
                self.json_serializer = json_serializer

        # act
        services.add_singleton(Level1Service)
        services.add_singleton(Level2Service)
        services.add_singleton(JsonSerializer)
        services.add_singleton(Level3Service)
        
        provider = services.build()
        level3_service = provider.get_service(Level3Service)

        # assert
        assert level3_service is not None
        assert isinstance(level3_service.level2, Level2Service)
        assert isinstance(level3_service.level2.level1, Level1Service)
        assert isinstance(level3_service.json_serializer, JsonSerializer)
