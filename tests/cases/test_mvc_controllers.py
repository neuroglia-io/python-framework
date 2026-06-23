from unittest.mock import Mock
from fastapi import Response

from neuroglia.core import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase
from neuroglia.serialization.json import JsonSerializer
from tests.data import UserDto


class SimpleController(ControllerBase):
    """Simple controller for testing base functionality"""
    pass


class TestControllerBasicFunctionality:
    """Test basic controller functionality"""

    def setup_method(self):
        """Setup for each test method"""
        # Create mock dependencies
        self.mock_service_provider = Mock()
        self.mock_mapper = Mock(spec=Mapper)
        self.mock_mediator = Mock(spec=Mediator)
        self.mock_json_serializer = Mock(spec=JsonSerializer)

        # Setup mock service provider to return json serializer
        self.mock_service_provider.get_required_service.return_value = self.mock_json_serializer

    def test_controller_initialization(self):
        """Test controller initialization with dependencies"""
        # act
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # assert
        assert controller.service_provider == self.mock_service_provider
        assert controller.mapper == self.mock_mapper
        assert controller.mediator == self.mock_mediator
        assert controller.json_serializer == self.mock_json_serializer
        assert controller.name == "Simple"

    def test_controller_name_extraction(self):
        """Test controller name extraction from class name"""
        # arrange
        class UsersController(ControllerBase):
            pass

        # act
        controller = UsersController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )

        # assert
        assert controller.name == "Users"

    def test_process_successful_result(self):
        """Test processing successful operation result"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        user_data = UserDto("123", "John", "john@example.com")
        
        # Create successful result
        operation_result = OperationResult("OK", 200)
        operation_result.data = user_data
        
        # Configure mock serializer
        expected_json = '{"id": "123", "name": "John", "email": "john@example.com"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # act
        response = controller.process(operation_result)

        # assert
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body == expected_json.encode()
        assert response.media_type == "application/json"

    def test_process_error_result(self):
        """Test processing error operation result"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        
        # Create error result
        operation_result = OperationResult("Bad Request", 400, "Invalid input")
        
        # Configure mock serializer
        expected_json = '{"status": 400, "detail": "Invalid input"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # act
        response = controller.process(operation_result)

        # assert
        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.body == expected_json.encode()
        assert response.media_type == "application/json"

    def test_process_created_result(self):
        """Test processing created operation result"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        user_data = UserDto("456", "Jane", "jane@example.com")
        
        # Create created result
        operation_result = OperationResult("Created", 201)
        operation_result.data = user_data
        
        # Configure mock serializer
        expected_json = '{"id": "456", "name": "Jane", "email": "jane@example.com"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # act
        response = controller.process(operation_result)

        # assert
        assert isinstance(response, Response)
        assert response.status_code == 201
        assert response.body == expected_json.encode()
        assert response.media_type == "application/json"

    def test_process_not_found_result(self):
        """Test processing not found operation result"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        
        # Create not found result
        operation_result = OperationResult("Not Found", 404, "User not found")
        
        # Configure mock serializer
        expected_json = '{"status": 404, "detail": "User not found"}'
        self.mock_json_serializer.serialize_to_text.return_value = expected_json

        # act
        response = controller.process(operation_result)

        # assert
        assert isinstance(response, Response)
        assert response.status_code == 404
        assert response.body == expected_json.encode()

    def test_process_result_with_none_data(self):
        """Test processing result with None data"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        
        # Create result with no data
        operation_result = OperationResult("OK", 200)
        operation_result.data = None
        
        # Configure mock serializer to return None
        self.mock_json_serializer.serialize_to_text.return_value = None

        # act
        response = controller.process(operation_result)

        # assert
        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.body == b""  # Empty body for None content


class TestControllerWithRealDependencies:
    """Test controller with actual service provider"""

    def test_controller_with_service_collection(self):
        """Test controller with real service provider"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Mapper)
        services.add_singleton(Mediator)
        provider = services.build()

        # act
        controller = SimpleController(
            provider,
            provider.get_required_service(Mapper),
            provider.get_required_service(Mediator)
        )

        # assert
        assert controller.service_provider == provider
        assert isinstance(controller.mapper, Mapper)
        assert isinstance(controller.mediator, Mediator)
        assert isinstance(controller.json_serializer, JsonSerializer)

    def test_multiple_controllers_shared_dependencies(self):
        """Test multiple controllers sharing dependencies"""
        # arrange
        services = ServiceCollection()
        services.add_singleton(JsonSerializer)
        services.add_singleton(Mapper)
        services.add_singleton(Mediator)
        provider = services.build()

        class Controller1(ControllerBase):
            pass

        class Controller2(ControllerBase):
            pass

        mapper = provider.get_required_service(Mapper)
        mediator = provider.get_required_service(Mediator)

        # act
        controller1 = Controller1(provider, mapper, mediator)
        controller2 = Controller2(provider, mapper, mediator)

        # assert
        assert controller1.service_provider == provider
        assert controller2.service_provider == provider
        assert controller1.json_serializer == controller2.json_serializer  # Same singleton
        assert controller1.name == "Controller1"
        assert controller2.name == "Controller2"


class TestControllerIntegrationScenarios:
    """Test realistic controller integration scenarios"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_service_provider = Mock()
        self.mock_mapper = Mock(spec=Mapper)
        self.mock_mediator = Mock(spec=Mediator)
        self.mock_json_serializer = Mock(spec=JsonSerializer)
        self.mock_service_provider.get_required_service.return_value = self.mock_json_serializer

    def test_success_workflow_simulation(self):
        """Test simulating a successful request workflow"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        
        # Simulate successful operation
        user_data = UserDto("789", "Alice", "alice@example.com")
        success_result = OperationResult("OK", 200)
        success_result.data = user_data
        
        self.mock_json_serializer.serialize_to_text.return_value = '{"id": "789", "name": "Alice"}'

        # act
        response = controller.process(success_result)

        # assert
        assert response.status_code == 200
        assert response.media_type == "application/json"
        self.mock_json_serializer.serialize_to_text.assert_called_once_with(user_data)

    def test_validation_error_workflow_simulation(self):
        """Test simulating a validation error workflow"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        
        # Simulate validation error
        error_result = OperationResult("Bad Request", 400, "Email is required")
        self.mock_json_serializer.serialize_to_text.return_value = '{"error": "Email is required"}'

        # act
        response = controller.process(error_result)

        # assert
        assert response.status_code == 400
        self.mock_json_serializer.serialize_to_text.assert_called_once_with(error_result)

    def test_internal_server_error_workflow_simulation(self):
        """Test simulating an internal server error workflow"""
        # arrange
        controller = SimpleController(
            self.mock_service_provider,
            self.mock_mapper,
            self.mock_mediator
        )
        
        # Simulate internal error
        error_result = OperationResult("Internal Server Error", 500, "Database unavailable")
        self.mock_json_serializer.serialize_to_text.return_value = '{"error": "Internal error"}'

        # act
        response = controller.process(error_result)

        # assert
        assert response.status_code == 500
        self.mock_json_serializer.serialize_to_text.assert_called_once_with(error_result)


class TestControllerHelperPatterns:
    """Test common controller helper patterns"""

    def setup_method(self):
        """Setup for each test method"""
        self.services = ServiceCollection()
        self.services.add_singleton(JsonSerializer)
        self.services.add_singleton(Mapper)
        self.services.add_singleton(Mediator)

    def test_controller_error_responses_configuration(self):
        """Test controller error responses configuration"""
        # arrange
        provider = self.services.build()
        controller = SimpleController(
            provider,
            provider.get_required_service(Mapper),
            provider.get_required_service(Mediator)
        )

        # assert
        assert controller.error_responses is not None
        assert 400 in controller.error_responses
        assert 404 in controller.error_responses
        assert 500 in controller.error_responses
        assert controller.error_responses[400]["description"] == "Bad Request"
        assert controller.error_responses[404]["description"] == "Not Found"
        assert controller.error_responses[500]["description"] == "Internal Server Error"

    def test_controller_inheritance_patterns(self):
        """Test controller inheritance patterns"""
        # arrange
        class BaseApiController(ControllerBase):
            def common_method(self):
                return "common functionality"

        class SpecificController(BaseApiController):
            pass

        provider = self.services.build()

        # act
        controller = SpecificController(
            provider,
            provider.get_required_service(Mapper),
            provider.get_required_service(Mediator)
        )

        # assert
        assert controller.name == "Specific"
        assert hasattr(controller, 'common_method')
        assert controller.common_method() == "common functionality"
        assert isinstance(controller, ControllerBase)
        assert isinstance(controller, BaseApiController)
