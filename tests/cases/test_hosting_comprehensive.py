from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI

from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.hosting.web import (
    WebApplicationBuilder, WebApplicationBuilderBase, WebHost, WebHostBase,
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

    def test_web_application_builder_build(self):
        """Test building web host from builder"""
        # arrange
        builder = WebApplicationBuilder()
        builder.services.add_singleton(JsonSerializer)

        # act
        with patch('neuroglia.hosting.web.HostApplicationLifetime') as mock_lifetime:
            mock_lifetime_instance = Mock()
            mock_lifetime.return_value = mock_lifetime_instance
            builder.services.add_singleton(type(mock_lifetime_instance), implementation_factory=lambda _: mock_lifetime_instance)
            
            host = builder.build()

        # assert
        assert host is not None
        assert isinstance(host, WebHostBase)
        assert isinstance(host, FastAPI)

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


class TestWebHost:
    """Test WebHost functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.services = ServiceCollection()
        self.services.add_singleton(JsonSerializer)

    def test_web_host_creation(self):
        """Test WebHost creation with service provider"""
        # arrange
        provider = self.services.build()

        # act
        with patch('neuroglia.hosting.web.HostApplicationLifetime') as mock_lifetime:
            mock_lifetime_instance = Mock()
            mock_lifetime_instance._run_async = AsyncMock()
            provider.get_required_service = Mock(return_value=mock_lifetime_instance)
            
            host = WebHost(provider)

        # assert
        assert isinstance(host, WebHostBase)
        assert isinstance(host, HostBase)
        assert isinstance(host, FastAPI)
        assert host.services == provider

    def test_web_host_fastapi_integration(self):
        """Test WebHost integration with FastAPI"""
        # arrange
        provider = self.services.build()

        # act
        with patch('neuroglia.hosting.web.HostApplicationLifetime') as mock_lifetime:
            mock_lifetime_instance = Mock()
            mock_lifetime_instance._run_async = AsyncMock()
            provider.get_required_service = Mock(return_value=mock_lifetime_instance)
            
            host = WebHost(provider)

        # assert
        assert hasattr(host, 'docs_url')
        assert host.docs_url == "/api/docs"
        assert hasattr(host, 'routes')
        assert hasattr(host, 'mount')
        assert hasattr(host, 'add_middleware')

    @patch('neuroglia.core.ModuleLoader.load')
    @patch('neuroglia.core.TypeFinder.get_types')
    def test_use_controllers_with_module_names(self, mock_get_types, mock_load):
        """Test use_controllers with specific module names"""
        # arrange
        provider = self.services.build()
        
        # Mock controller
        class MockController:
            def get_route_prefix(self):
                return "mock"

        mock_module = Mock()
        mock_load.return_value = mock_module
        mock_get_types.return_value = [MockController]

        # act
        with patch('neuroglia.hosting.web.HostApplicationLifetime') as mock_lifetime:
            mock_lifetime_instance = Mock()
            mock_lifetime_instance._run_async = AsyncMock()
            provider.get_required_service = Mock(return_value=mock_lifetime_instance)
            
            host = WebHost(provider)
            result = host.use_controllers(["test.controllers"])

        # assert
        assert result == host
        mock_load.assert_called_once_with("test.controllers")

    @patch('neuroglia.core.ModuleLoader.load')
    def test_use_controllers_auto_discovery(self, mock_load):
        """Test use_controllers with auto-discovery"""
        # arrange
        provider = self.services.build()

        # Mock auto-discovery failure (no api.controllers module)
        mock_load.side_effect = ImportError("No module named 'api.controllers'")

        # act
        with patch('neuroglia.hosting.web.HostApplicationLifetime') as mock_lifetime:
            mock_lifetime_instance = Mock()
            mock_lifetime_instance._run_async = AsyncMock()
            provider.get_required_service = Mock(return_value=mock_lifetime_instance)
            
            host = WebHost(provider)
            result = host.use_controllers()  # No module names

        # assert
        assert result == host  # Should not fail, just continue


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
            HostBase()
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

    def test_end_to_end_application_creation(self):
        """Test complete application creation workflow"""
        # arrange
        builder = WebApplicationBuilder()

        # act
        builder.services.add_singleton(JsonSerializer)
        # Note: We can't easily test the full build() due to HostApplicationLifetime dependency
        # but we can test the builder setup

        # assert
        assert builder.services is not None
        provider = builder.services.build()
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

    def test_builder_method_chaining(self):
        """Test builder method chaining patterns"""
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
