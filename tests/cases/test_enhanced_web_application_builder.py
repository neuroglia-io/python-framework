"""
Tests for WebApplicationBuilder - Advanced web application builder with multi-app support.

This test suite validates the unified web application builder functionality including
multi-FastAPI application support, controller management, and advanced middleware features.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI

from neuroglia.dependency_injection import ServiceCollection
from neuroglia.hosting.web import (
    EnhancedWebHost,
    ExceptionHandlingMiddleware,
    WebApplicationBuilder,
)


class TestEnhancedWebApplicationBuilder:
    """Test suite for WebApplicationBuilder (unified builder)"""

    def setup_method(self):
        """Setup method called before each test"""
        self.builder = WebApplicationBuilder()

    def test_builder_initialization(self):
        """Test builder initialization with proper defaults"""
        assert isinstance(self.builder.services, ServiceCollection)
        assert self.builder.app is None  # No app built yet
        assert self.builder._registered_controllers == {}
        assert self.builder._pending_controller_modules == []

    def test_builder_inherits_from_web_application_builder(self):
        """Test that EnhancedWebApplicationBuilder properly inherits functionality"""
        # Should have the basic WebApplicationBuilder functionality
        assert hasattr(self.builder, "services")
        assert hasattr(self.builder, "build")
        assert hasattr(self.builder, "add_controllers")

    def test_build_creates_enhanced_web_host(self):
        """Test that build() creates an EnhancedWebHost"""
        host = self.builder.build()

        assert isinstance(host, EnhancedWebHost)
        assert self.builder.app is not None  # App should be set after building
        assert isinstance(self.builder.app, FastAPI)

    def test_add_controllers_with_no_app_queues_for_main_app(self):
        """Test that add_controllers without app parameter queues controllers for main app"""
        modules = ["test.controllers"]
        prefix = "/api/v1"

        # Mock the _register_controller_types method
        with patch.object(self.builder, "_register_controller_types") as mock_register:
            self.builder.add_controllers(modules, app=None, prefix=prefix)

            # Should register controller types
            mock_register.assert_called_once_with(modules)

            # Should queue for main app
            assert len(self.builder._pending_controller_modules) == 1
            pending = self.builder._pending_controller_modules[0]
            assert pending["modules"] == modules
            assert pending["app"] is None
            assert pending["prefix"] == prefix

    def test_add_controllers_with_app_registers_immediately(self):
        """Test that add_controllers with app parameter registers immediately"""
        modules = ["test.controllers"]
        app = FastAPI()
        prefix = "/api/v1"

        with patch.object(self.builder, "_register_controller_types") as mock_register_types:
            with patch.object(self.builder, "_register_controllers_to_app") as mock_register_app:
                self.builder.add_controllers(modules, app=app, prefix=prefix)

                # Should register controller types
                mock_register_types.assert_called_once_with(modules)

                # Should register to app immediately
                mock_register_app.assert_called_once_with(modules, app, prefix)

                # Should not queue for later
                assert len(self.builder._pending_controller_modules) == 0

    def test_add_exception_handling_without_app_before_build_raises_error(self):
        """Test that add_exception_handling without app before build raises error"""
        with pytest.raises(ValueError) as exc_info:
            self.builder.add_exception_handling()

        assert "No FastAPI app available" in str(exc_info.value)

    def test_add_exception_handling_with_app_parameter(self):
        """Test adding exception handling to specific app"""
        app = FastAPI()

        with patch.object(app, "add_middleware") as mock_add_middleware:
            with patch.object(self.builder.services, "build") as mock_build:
                mock_service_provider = Mock()
                mock_build.return_value = mock_service_provider

                self.builder.add_exception_handling(app)

                # Should add middleware to the app
                mock_add_middleware.assert_called_once_with(ExceptionHandlingMiddleware, service_provider=mock_service_provider)

    def test_build_processes_pending_controller_modules(self):
        """Test that build processes pending controller modules"""
        modules = ["test.controllers"]
        prefix = "/api/v1"

        # Queue some controllers
        with patch.object(self.builder, "_register_controller_types"):
            self.builder.add_controllers(modules, prefix=prefix)

        # Mock the registration method
        with patch.object(self.builder, "_register_controllers_to_app") as mock_register:
            host = self.builder.build()

            # Should process the pending registration
            mock_register.assert_called_once_with(modules, host, prefix)

            # Should clear the pending registrations for main app
            remaining_pending = [reg for reg in self.builder._pending_controller_modules if reg.get("app") is None]
            assert len(remaining_pending) == 0


class TestExceptionHandlingMiddleware:
    """Test suite for ExceptionHandlingMiddleware"""

    def setup_method(self):
        """Setup test environment"""
        self.app = FastAPI()
        self.mock_service_provider = Mock()
        self.mock_serializer = Mock()
        self.mock_service_provider.get_required_service.return_value = self.mock_serializer

        self.middleware = ExceptionHandlingMiddleware(self.app, self.mock_service_provider)

    def test_middleware_initialization(self):
        """Test middleware initialization"""
        assert self.middleware.service_provider is self.mock_service_provider
        assert self.middleware.serializer is self.mock_serializer

    @pytest.mark.asyncio
    async def test_middleware_with_no_exception(self):
        """Test middleware behavior when no exception occurs"""
        mock_request = Mock()
        mock_response = Mock()

        async def mock_call_next(request):
            return mock_response

        result = await self.middleware.dispatch(mock_request, mock_call_next)

        assert result is mock_response

    @pytest.mark.asyncio
    async def test_middleware_with_exception_creates_problem_details(self):
        """Test middleware handling an exception with problem details format"""
        mock_request = Mock()
        test_exception = Exception("Test error message")

        async def mock_call_next(request):
            raise test_exception

        # Mock the serializer
        self.mock_serializer.serialize_to_text.return_value = '{"error": "serialized"}'

        result = await self.middleware.dispatch(mock_request, mock_call_next)

        # Should return a Response with problem details
        assert result.status_code == 500
        assert result.media_type == "application/json"

        # Should serialize problem details
        self.mock_serializer.serialize_to_text.assert_called_once()
        call_args = self.mock_serializer.serialize_to_text.call_args[0][0]
        assert call_args.title == "Internal Server Error"
        assert call_args.status == 500
        assert call_args.detail == "Test error message"


class TestEnhancedWebHost:
    """Test suite for EnhancedWebHost"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_service_provider = Mock()
        self.host = EnhancedWebHost(self.mock_service_provider)

    def test_host_initialization(self):
        """Test host initialization"""
        assert isinstance(self.host, EnhancedWebHost)
        assert isinstance(self.host, FastAPI)

    def test_use_controllers_does_nothing(self):
        """Test that use_controllers method is overridden to do nothing"""
        # Should not raise any exceptions and not add controllers automatically
        try:
            self.host.use_controllers()
            # If we get here, the method executed without error
            assert True
        except Exception as e:
            pytest.fail(f"use_controllers raised an exception: {e}")


class TestIntegrationScenarios:
    """Integration tests for the enhanced web application builder"""

    def test_complete_build_workflow(self):
        """Test complete workflow from builder to host"""
        builder = EnhancedWebApplicationBuilder()

        # Build should work without any configuration
        host = builder.build()

        assert isinstance(host, EnhancedWebHost)
        assert builder.app is host
        assert isinstance(host, FastAPI)

    def test_controller_registration_workflow(self):
        """Test controller registration workflow"""
        builder = EnhancedWebApplicationBuilder()

        # Add controllers for later registration
        with patch.object(builder, "_register_controller_types") as mock_register:
            builder.add_controllers(["test.module1", "test.module2"], prefix="/api")

            # Should register types
            mock_register.assert_called_once_with(["test.module1", "test.module2"])

            # Should queue for main app
            assert len(builder._pending_controller_modules) == 1

    def test_exception_handling_after_build(self):
        """Test adding exception handling after building"""
        builder = EnhancedWebApplicationBuilder()
        host = builder.build()

        # Now should be able to add exception handling
        with patch.object(host, "add_middleware") as mock_add_middleware:
            with patch.object(builder.services, "build") as mock_build_services:
                mock_service_provider = Mock()
                mock_build_services.return_value = mock_service_provider

                builder.add_exception_handling()

                mock_add_middleware.assert_called_once_with(ExceptionHandlingMiddleware, service_provider=mock_service_provider)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
