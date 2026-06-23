import pytest
from unittest.mock import Mock
from fastapi import Response
from classy_fastapi.decorators import get, post

from neuroglia.core import OperationResult
from neuroglia.core.problem_details import ProblemDetails
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator, Command, Query
from neuroglia.mvc.controller_base import ControllerBase, generate_unique_id_function
from neuroglia.serialization.json import JsonSerializer
from tests.data import UserDto


class TestUserCommand(Command[OperationResult[UserDto]]):
    """Test command for user creation"""
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email


class TestUserQuery(Query[OperationResult[UserDto]]):
    """Test query for user retrieval"""
    def __init__(self, user_id: str):
        self.user_id = user_id


class TestController(ControllerBase):
    """Test controller for testing base functionality"""

    @get("/{user_id}")
    async def get_user(self, user_id: str) -> UserDto:
        query = TestUserQuery(user_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/")
    async def create_user(self, name: str, email: str) -> UserDto:
        command = TestUserCommand(name, email)
        result = await self.mediator.execute_async(command)
        return self.process(result)


class TestControllerBase:
    """Comprehensive tests for ControllerBase functionality"""

    def setup_method(self):
        """Setup for each test method"""
        self.services = ServiceCollection()
        self.services.add_singleton(JsonSerializer)
        self.services.add_singleton(Mapper)
        self.services.add_singleton(Mediator)

        # Mock service provider, mapper, and mediator
        self.mock_service_provider = Mock()
        self.mock_mapper = Mock(spec=Mapper)
        self.mock_mediator = Mock(spec=Mediator)
        self.mock_json_serializer = Mock(spec=JsonSerializer)

        # Setup mock service provider to return required services
        self.mock_service_provider.get_required_service.return_value = self.mock_json_serializer

    def test_controller_initialization(self):
        """Test controller initialization with dependencies"""
        # ac
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # asser
        assert controller.service_provider == self.mock_service_provider
        assert controller.mapper == self.mock_mapper
        assert controller.mediator == self.mock_mediator
        assert controller.json_serializer == self.mock_json_serializer
        assert controller.name == "Test"  # "TestController" -> "Test"

    def test_controller_name_extraction(self):
        """Test controller name extraction from class name"""
        # arrange
        class UsersController(ControllerBase):
            def __init__(self, service_provider, mapper, mediator):
                super().__init__(service_provider, mapper, mediator)

        class ProductsController(ControllerBase):
            def __init__(self, service_provider, mapper, mediator):
                super().__init__(service_provider, mapper, mediator)

        # ac
        users_controller = UsersController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        products_controller = ProductsController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # asser
        assert users_controller.name == "Users"
        assert products_controller.name == "Products"

    def test_controller_prefix_and_tags_configuration(self):
        """Test controller router prefix and tags configuration"""
        # ac
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # asser
        assert controller.prefix == "/test"  # lowercased name
        assert "Test" in controller.tags

    def test_controller_error_responses_configuration(self):
        """Test controller error responses configuration"""
        # ac
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # asser
        assert controller.error_responses is not None
        assert 400 in controller.error_responses
        assert 404 in controller.error_responses
        assert 500 in controller.error_responses
        assert controller.error_responses[400]["model"] == ProblemDetails
        assert controller.error_responses[404]["model"] == ProblemDetails
        assert controller.error_responses[500]["model"] == ProblemDetails

    def test_process_successful_operation_result(self):
        """Test processing successful operation result"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        user_data = UserDto("123", "John Doe", "john@example.com")
        operation_result = OperationResult("OK", 200)
        operation_result.data = user_data

        # Configure mock serializer
        expected_json = '{"id": "123", "name": "John Doe", "email": "john@example.com"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = controller.process(operation_result)

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body.decode() == expected_json
        assert response.media_type == "application/json"
        self.mock_json_serializer.serialize_to_text.assert_called_once_with(user_data)

    def test_process_created_operation_result(self):
        """Test processing created operation result"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        user_data = UserDto("123", "John Doe", "john@example.com")
        operation_result = OperationResult.created(user_data)

        # Configure mock serializer
        expected_json = '{"id": "123", "name": "John Doe", "email": "john@example.com"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = controller.process(operation_result)

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 201
        assert response.body.decode() == expected_json
        assert response.media_type == "application/json"

    def test_process_error_operation_result(self):
        """Test processing error operation result"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        operation_result = OperationResult.bad_request("Invalid input data")

        # Configure mock serializer to return the operation result as JSON
        expected_json = '{"status": 400, "detail": "Invalid input data", "is_success": false}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = controller.process(operation_result)

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.body.decode() == expected_json
        assert response.media_type == "application/json"
        # Should serialize the entire operation result, not just data
        self.mock_json_serializer.serialize_to_text.assert_called_once_with(operation_result)

    def test_process_not_found_operation_result(self):
        """Test processing not found operation result"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        operation_result = OperationResult.not_found(UserDto, "user-123")

        # Configure mock serializer
        expected_json = '{"status": 404, "detail": "Not found", "is_success": false}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = controller.process(operation_result)

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.body.decode() == expected_json

    def test_process_internal_server_error_operation_result(self):
        """Test processing internal server error operation result"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        operation_result = OperationResult.internal_server_error("Database connection failed")

        # Configure mock serializer
        expected_json = '{"status": 500, "detail": "Database connection failed", "is_success": false}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = controller.process(operation_result)

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 500
        assert response.body.decode() == expected_json

    def test_process_operation_result_with_none_data(self):
        """Test processing operation result with None data"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        operation_result = OperationResult.ok(None)

        # Configure mock serializer to handle None
        self.mock_json_serializer.serialize_to_text.return_value = None

        # ac
        response = controller.process(operation_result)

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body == b""  # Empty body for None conten
        assert response.media_type == "application/json"

    @pytest.mark.asyncio
    async def test_controller_endpoint_integration_success(self):
        """Test controller endpoint integration with successful mediation"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # Configure mocks
        user_data = UserDto("123", "John Doe", "john@example.com")
        operation_result = OperationResult.ok(user_data)
        self.mock_mediator.execute_async.return_value = operation_resul

        expected_json = '{"id": "123", "name": "John Doe", "email": "john@example.com"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = await controller.get_user("123")

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 200
        # Verify mediator was called with correct query
        self.mock_mediator.execute_async.assert_called_once()
        call_args = self.mock_mediator.execute_async.call_args[0][0]
        assert isinstance(call_args, TestUserQuery)
        assert call_args.user_id == "123"

    @pytest.mark.asyncio
    async def test_controller_endpoint_integration_error(self):
        """Test controller endpoint integration with error from mediation"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # Configure mocks
        operation_result = OperationResult.not_found(UserDto, "999")
        self.mock_mediator.execute_async.return_value = operation_resul

        expected_json = '{"status": 404, "detail": "Not found", "is_success": false}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # ac
        response = await controller.get_user("999")

        # asser
        assert isinstance(response, Response)
        assert response.status_code == 404
        # Verify correct query was executed
        call_args = self.mock_mediator.execute_async.call_args[0][0]
        assert call_args.user_id == "999"


class TestControllerUtilities:
    """Test controller utility functions"""

    def test_generate_unique_id_function_with_tags_and_name(self):
        """Test unique ID generation with tags and name"""
        # arrange
        route = Mock()
        route.tags = ["Users"]
        route.name = "get_user"
        route.methods = {"GET"}

        # ac
        result = generate_unique_id_function(route)

        # asser
        assert result == "users_get_user"

    def test_generate_unique_id_function_with_methods_and_name(self):
        """Test unique ID generation with methods and name only"""
        # arrange
        route = Mock()
        route.tags = None
        route.name = "create_user"
        route.methods = {"POST"}

        # ac
        result = generate_unique_id_function(route)

        # asser
        assert result == "create_user_post"

    def test_generate_unique_id_function_fallback(self):
        """Test unique ID generation fallback scenario"""
        # arrange
        route = Mock()
        route.tags = None
        route.name = "test_endpoint"
        route.methods = {"PUT"}

        # ac
        result = generate_unique_id_function(route)

        # asser
        assert result == "test_endpoint"


class TestControllerDependencyInjection:
    """Test controller dependency injection patterns"""

    def test_controller_with_real_service_provider(self):
        """Test controller with actual service provider"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Mapper)
        services.add_singleton(Mediator)
        provider = services.build()

        # ac
        controller = TestController(
            provider,
            provider.get_required_service(Mapper),
            provider.get_required_service(Mediator)
        )

        # asser
        assert controller.service_provider == provider
        assert isinstance(controller.mapper, Mapper)
        assert isinstance(controller.mediator, Mediator)
        assert isinstance(controller.json_serializer, JsonSerializer)

    def test_controller_dependency_resolution(self):
        """Test controller dependency resolution patterns"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Mapper)
        services.add_singleton(Mediator)
        provider = services.build()

        mapper = provider.get_required_service(Mapper)
        mediator = provider.get_required_service(Mediator)

        # ac
        controller = TestController(provider, mapper, mediator)

        # asser
        assert controller.json_serializer is not None
        assert controller.service_provider == provider
        assert controller.mapper == mapper
        assert controller.mediator == mediator

    def test_multiple_controllers_with_shared_dependencies(self):
        """Test multiple controllers sharing the same dependencies"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Mapper)
        services.add_singleton(Mediator)
        provider = services.build()

        mapper = provider.get_required_service(Mapper)
        mediator = provider.get_required_service(Mediator)

        class UsersController(ControllerBase):
            pass

        class ProductsController(ControllerBase):
            pass

        # ac
        users_controller = UsersController(provider, mapper, mediator)
        products_controller = ProductsController(provider, mapper, mediator)

        # asser
        assert users_controller.service_provider == provider
        assert products_controller.service_provider == provider
        assert users_controller.mapper == mapper
        assert products_controller.mapper == mapper
        assert users_controller.mediator == mediator
        assert products_controller.mediator == mediator
        # JSON serializer should be the same singleton instance
        assert users_controller.json_serializer == products_controller.json_serializer


class TestControllerPatterns:
    """Test common controller patterns and scenarios"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_service_provider = Mock()
        self.mock_mapper = Mock(spec=Mapper)
        self.mock_mediator = Mock(spec=Mediator)
        self.mock_json_serializer = Mock(spec=JsonSerializer)
        self.mock_service_provider.get_required_service.return_value = self.mock_json_serializer

    def test_controller_command_query_separation(self):
        """Test controller properly separates commands and queries"""
        # arrange
        class CQRSController(ControllerBase):
            @get("/{id}")
            async def get_item(self, id: str):
                # Query pattern
                query = TestUserQuery(id)
                result = await self.mediator.execute_async(query)
                return self.process(result)

            @post("/")
            async def create_item(self, name: str, email: str):
                # Command pattern
                command = TestUserCommand(name, email)
                result = await self.mediator.execute_async(command)
                return self.process(result)

        controller = CQRSController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # asser
        assert hasattr(controller, 'get_item')
        assert hasattr(controller, 'create_item')
        assert controller.name == "CQRS"

    @pytest.mark.asyncio
    async def test_controller_validation_and_error_handling(self):
        """Test controller validation and error handling patterns"""
        # arrange
        class ValidatingController(ControllerBase):
            async def create_user_with_validation(self, name: str, email: str):
                # Validation logic
                if not name or not email:
                    bad_request = OperationResult.bad_request("Name and email are required")
                    return self.process(bad_request)
                if "@" not in email:
                    bad_request = OperationResult.bad_request("Invalid email format")
                    return self.process(bad_request)

                # Business logic through mediator
                command = TestUserCommand(name, email)
                result = await self.mediator.execute_async(command)
                return self.process(result)

        controller = ValidatingController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # Configure mock serializer
        self.mock_json_serializer.serialize_to_text.return_value = '{"error": "validation failed"}'

        # act & assert - invalid input
        response_missing_name = await controller.create_user_with_validation("", "test@example.com")
        assert response_missing_name.status_code == 400

        response_invalid_email = await controller.create_user_with_validation("John", "invalid-email")
        assert response_invalid_email.status_code == 400

    @pytest.mark.asyncio
    async def test_controller_mediator_integration_patterns(self):
        """Test controller integration with mediator for various scenarios"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # Test successful command execution
        success_result = OperationResult.created(UserDto("123", "John", "john@example.com"))
        self.mock_mediator.execute_async.return_value = success_result
        self.mock_json_serializer.serialize_to_text.return_value = '{"id": "123"}'

        # act
        response = await controller.create_user("John", "john@example.com")

        # assert
        assert response.status_code == 201
        self.mock_mediator.execute_async.assert_called_once()
        command_arg = self.mock_mediator.execute_async.call_args[0][0]
        assert isinstance(command_arg, TestUserCommand)
        assert command_arg.name == "John"
        assert command_arg.email == "john@example.com"

    @pytest.mark.asyncio
    async def test_controller_mediator_integration_patterns(self):
        """Test controller integration with mediator for various scenarios"""
        # arrange
        controller = TestController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # Test successful command execution
        success_result = OperationResult.created(UserDto("123", "John", "john@example.com"))
        self.mock_mediator.execute_async.return_value = success_result
        self.mock_json_serializer.serialize_to_text.return_value = '{"id": "123"}'

        # act
        response = await controller.create_user("John", "john@example.com")

        # assert
        assert response.status_code == 201
        self.mock_mediator.execute_async.assert_called_once()
        command_arg = self.mock_mediator.execute_async.call_args[0][0]
        assert isinstance(command_arg, TestUserCommand)
        assert command_arg.name == "John"
        assert command_arg.email == "john@example.com"
