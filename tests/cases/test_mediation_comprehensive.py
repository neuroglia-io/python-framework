import pytest
from typing import Optional
from uuid import uuid4

from neuroglia.core import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mediation.mediator import (
    Mediator, Command, Query, RequestHandler, CommandHandler, QueryHandler,
    NotificationHandler
)
from tests.data import GreetCommand, UserCreatedDomainEventV1, UserDto
from tests.services import GreetCommandHandler


class SimpleTestCommand(Command[OperationResult[str]]):
    """Simple test command"""
    def __init__(self, message: str):
        self.message = message


class SimpleTestQuery(Query[OperationResult[int]]):
    """Simple test query"""
    def __init__(self, value: int):
        self.value = value


class SimpleTestCommandHandler(CommandHandler[SimpleTestCommand, OperationResult[str]]):
    """Simple test command handler"""
    async def handle_async(self, request: SimpleTestCommand) -> OperationResult[str]:
        return self.ok(f"Handled: {request.message}")


class SimpleTestQueryHandler(QueryHandler[SimpleTestQuery, OperationResult[int]]):
    """Simple test query handler"""
    async def handle_async(self, request: SimpleTestQuery) -> OperationResult[int]:
        return self.ok(request.value * 3)


class SimpleNotification:
    """Simple notification for testing"""
    def __init__(self, data: str):
        self.data = data


class SimpleNotificationHandler(NotificationHandler[SimpleNotification]):
    """Simple notification handler"""
    def __init__(self):
        self.handled_notifications = []
    
    async def handle_async(self, notification: SimpleNotification) -> None:
        self.handled_notifications.append(notification)


class TestMediationFramework:
    """Comprehensive tests for the mediation framework"""

    def setup_method(self):
        """Setup for each test method"""
        self.services = ServiceCollection()

    @pytest.mark.asyncio
    async def test_mediator_command_execution(self):
        """Test basic command execution through mediator"""
        # arrange
        self.services.add_singleton(Mediator)
        self.services.add_singleton(RequestHandler, GreetCommandHandler)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        command = GreetCommand("Hello World")

        # act
        result = await mediator.execute_async(command)

        # assert
        assert result is not None
        assert result.is_success
        assert result.status == 200
        assert result.data == "Hello, world!"  # This is what the handler actually returns

    @pytest.mark.asyncio
    async def test_mediator_custom_command_handler(self):
        """Test custom command handler"""
        # arrange
        self.services.add_singleton(Mediator)
        self.services.add_singleton(RequestHandler, SimpleTestCommandHandler)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        command = SimpleTestCommand("test message")

        # act
        result = await mediator.execute_async(command)

        # assert
        assert result is not None
        assert result.is_success
        assert result.status == 200
        assert result.data == "Handled: test message"

    @pytest.mark.asyncio
    async def test_mediator_query_execution(self):
        """Test query execution through mediator"""
        # arrange
        self.services.add_singleton(Mediator)
        self.services.add_singleton(RequestHandler, SimpleTestQueryHandler)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        query = SimpleTestQuery(10)

        # act
        result = await mediator.execute_async(query)

        # assert
        assert result is not None
        assert result.is_success
        assert result.status == 200
        assert result.data == 30

    @pytest.mark.asyncio
    async def test_mediator_notification_publishing(self):
        """Test notification publishing through mediator"""
        # arrange
        notification_handler = SimpleNotificationHandler()
        self.services.add_singleton(Mediator)
        self.services.add_singleton(NotificationHandler, implementation_factory=lambda _: notification_handler)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        notification = SimpleNotification("test notification")

        # act
        await mediator.publish_async(notification)

        # assert
        assert len(notification_handler.handled_notifications) == 1
        assert notification_handler.handled_notifications[0].data == "test notification"

    @pytest.mark.asyncio
    async def test_mediator_domain_event_handling(self):
        """Test domain event handling through mediator"""
        # arrange
        class SimpleDomainEventHandler(NotificationHandler[UserCreatedDomainEventV1]):
            def __init__(self):
                self.handled_events = []
            
            async def handle_async(self, notification: UserCreatedDomainEventV1) -> None:
                self.handled_events.append(notification)

        domain_event_handler = SimpleDomainEventHandler()
        self.services.add_singleton(Mediator)
        self.services.add_singleton(NotificationHandler, implementation_factory=lambda _: domain_event_handler)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        domain_event = UserCreatedDomainEventV1(str(uuid4()), "John Doe", "john@example.com")

        # act
        await mediator.publish_async(domain_event)

        # assert - event should be handled
        assert len(domain_event_handler.handled_events) == 1
        assert domain_event_handler.handled_events[0].name == "John Doe"

    @pytest.mark.asyncio
    async def test_mediator_no_handler_found(self):
        """Test mediator behavior when no handler is found"""
        # arrange
        self.services.add_singleton(Mediator)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        command = SimpleTestCommand("unhandled")

        # act & assert
        with pytest.raises(Exception) as exc_info:
            await mediator.execute_async(command)
        
        assert "Failed to find a handler" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_mediator_notification_no_handlers(self):
        """Test mediator behavior when no notification handlers exist"""
        # arrange
        self.services.add_singleton(Mediator)
        provider = self.services.build()
        mediator = provider.get_required_service(Mediator)
        notification = SimpleNotification("no handlers")

        # act - should not raise exception
        await mediator.publish_async(notification)

        # assert - no exception raised indicates success


class TestRequestHandlers:
    """Test request handler base functionality"""

    def test_command_handler_ok_response(self):
        """Test command handler OK response creation"""
        # arrange
        handler = SimpleTestCommandHandler()
        test_data = "success"

        # act
        result = handler.ok(test_data)

        # assert
        assert result.is_success
        assert result.status == 200
        assert result.data == test_data

    def test_command_handler_created_response(self):
        """Test command handler Created response creation"""
        # arrange
        handler = SimpleTestCommandHandler()
        test_data = "created entity"

        # act
        result = handler.created(test_data)

        # assert
        assert result.is_success
        assert result.status == 201
        assert result.data == test_data

    def test_command_handler_bad_request_response(self):
        """Test command handler Bad Request response creation"""
        # arrange
        handler = SimpleTestCommandHandler()
        error_message = "Invalid data"

        # act
        result = handler.bad_request(error_message)

        # assert
        assert not result.is_success
        assert result.status == 400
        assert result.detail == error_message

    def test_query_handler_not_found_response(self):
        """Test query handler Not Found response creation"""
        # arrange
        handler = SimpleTestQueryHandler()
        entity_type = UserDto
        entity_id = "user-123"

        # act
        result = handler.not_found(entity_type, entity_id)

        # assert
        assert not result.is_success
        assert result.status == 404
        assert result.detail is not None
        assert "UserDto" in result.detail
        assert "user-123" in result.detail


class TestCQRSPatterns:
    """Test CQRS pattern implementations"""

    @pytest.mark.asyncio
    async def test_command_with_validation(self):
        """Test command handling with validation logic"""
        # arrange
        class ValidatedCommand(Command[OperationResult[str]]):
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class ValidatedCommandHandler(CommandHandler[ValidatedCommand, OperationResult[str]]):
            async def handle_async(self, request: ValidatedCommand) -> OperationResult[str]:
                # Validation logic
                if not request.name:
                    return self.bad_request("Name is required")
                if not request.email or "@" not in request.email:
                    return self.bad_request("Valid email is required")
                
                # Business logic
                return self.created(f"User {request.name} created with email {request.email}")

        handler = ValidatedCommandHandler()

        # act & assert - valid command
        valid_command = ValidatedCommand("John", "john@example.com")
        result = await handler.handle_async(valid_command)
        assert result.is_success
        assert result.status == 201

        # act & assert - invalid command
        invalid_command = ValidatedCommand("", "invalid")
        result = await handler.handle_async(invalid_command)
        assert not result.is_success
        assert result.status == 400

    @pytest.mark.asyncio
    async def test_query_with_data_access(self):
        """Test query handling with data access patterns"""
        # arrange
        class UserQuery(Query[OperationResult[Optional[dict]]]):
            def __init__(self, user_id: str):
                self.user_id = user_id

        class UserQueryHandler(QueryHandler[UserQuery, OperationResult[Optional[dict]]]):
            def __init__(self):
                self.users = {
                    "1": {"name": "John", "email": "john@example.com"},
                    "2": {"name": "Jane", "email": "jane@example.com"}
                }

            async def handle_async(self, request: UserQuery) -> OperationResult[Optional[dict]]:
                user = self.users.get(request.user_id)
                if user is None:
                    return self.not_found(dict, request.user_id)
                return self.ok(user)

        handler = UserQueryHandler()

        # act & assert - existing user
        existing_query = UserQuery("1")
        result = await handler.handle_async(existing_query)
        assert result.is_success
        assert result.data is not None
        assert result.data["name"] == "John"

        # act & assert - non-existing user
        missing_query = UserQuery("999")
        result = await handler.handle_async(missing_query)
        assert not result.is_success
        assert result.status == 404

    @pytest.mark.asyncio
    async def test_notification_handler_side_effects(self):
        """Test notification handler managing side effects"""
        # arrange
        class UserRegisteredEvent:
            def __init__(self, user_id: str, email: str):
                self.user_id = user_id
                self.email = email

        class EmailNotificationHandler(NotificationHandler[UserRegisteredEvent]):
            def __init__(self):
                self.sent_emails = []

            async def handle_async(self, notification: UserRegisteredEvent) -> None:
                # Simulate sending email
                email = {
                    "to": notification.email,
                    "subject": "Welcome!",
                    "user_id": notification.user_id
                }
                self.sent_emails.append(email)

        handler = EmailNotificationHandler()
        event = UserRegisteredEvent("user-1", "user@example.com")

        # act
        await handler.handle_async(event)

        # assert
        assert len(handler.sent_emails) == 1
        assert handler.sent_emails[0]["to"] == "user@example.com"
        assert handler.sent_emails[0]["user_id"] == "user-1"

