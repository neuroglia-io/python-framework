"""
Unit tests for CQRS and Mediation functionality.
"""

from dataclasses import dataclass
from datetime import datetime

import pytest

from neuroglia.data.abstractions import DomainEvent
from neuroglia.dependency_injection.service_provider import ServiceCollection
from neuroglia.mediation.mediator import (
    Command,
    CommandHandler,
    DomainEventHandler,
    Mediator,
    NotificationHandler,
    Query,
    QueryHandler,
)

# Import test fixtures
from tests.fixtures.test_fixtures import (
    CreateTestUserCommand,
    CreateTestUserCommandHandler,
    GetTestUserQuery,
    GetTestUserQueryHandler,
    InMemoryTestUserDtoRepository,
    InMemoryTestUserRepository,
    ListTestUsersQuery,
    ListTestUsersQueryHandler,
    TestUser,
    TestUserCreatedEvent,
    TestUserCreatedEventHandler,
    TestUserDto,
)

# Additional test models for comprehensive testing


@dataclass
class SimpleCommand(Command[str]):
    """Simple command for testing"""

    message: str


@dataclass
class SimpleQuery(Query[int]):
    """Simple query for testing"""

    value: int


@dataclass
class SimpleEvent(DomainEvent):
    """Simple event for testing"""

    data: str
    timestamp: datetime


@dataclass
class TestNotification:
    """Test notification"""

    message: str
    priority: int = 1


class SimpleCommandHandler(CommandHandler[SimpleCommand, str]):
    """Simple command handler for testing"""

    def __init__(self):
        self.handled_commands: list[SimpleCommand] = []

    async def handle_async(self, command: SimpleCommand) -> str:
        self.handled_commands.append(command)
        return f"Handled: {command.message}"


class SimpleQueryHandler(QueryHandler[SimpleQuery, int]):
    """Simple query handler for testing"""

    def __init__(self):
        self.handled_queries: list[SimpleQuery] = []

    async def handle_async(self, query: SimpleQuery) -> int:
        self.handled_queries.append(query)
        return query.value * 2


class SimpleEventHandler(DomainEventHandler[SimpleEvent]):
    """Simple event handler for testing"""

    def __init__(self):
        self.handled_events: list[SimpleEvent] = []

    async def handle_async(self, event: SimpleEvent):
        self.handled_events.append(event)


class FirstNotificationHandler(NotificationHandler[TestNotification]):
    """First notification handler for testing"""

    def __init__(self):
        self.handled_notifications: list[TestNotification] = []

    async def handle_async(self, notification: TestNotification):
        self.handled_notifications.append(notification)


class SecondNotificationHandler(NotificationHandler[TestNotification]):
    """Second notification handler for testing"""

    def __init__(self):
        self.handled_notifications: list[TestNotification] = []

    async def handle_async(self, notification: TestNotification):
        self.handled_notifications.append(notification)


class FailingCommandHandler(CommandHandler[SimpleCommand, str]):
    """Command handler that fails for testing error scenarios"""

    async def handle_async(self, command: SimpleCommand) -> str:
        raise ValueError(f"Intentional error for command: {command.message}")


# Test Command/Query/Event base classes


class TestCommandQueryEventBases:
    def test_command_creation(self):
        """Test Command base class"""
        command = SimpleCommand(message="test")

        assert command.message == "test"
        assert isinstance(command, Command)

    def test_query_creation(self):
        """Test Query base class"""
        query = SimpleQuery(value=42)

        assert query.value == 42
        assert isinstance(query, Query)

    def test_event_creation(self):
        """Test Event base class"""
        timestamp = datetime.now(timezone.utc)
        event = SimpleEvent(data="test data", timestamp=timestamp)

        assert event.data == "test data"
        assert event.timestamp == timestamp
        assert isinstance(event, Event)

    def test_notification_creation(self):
        """Test INotification base class"""
        notification = TestNotification(message="test", priority=5)

        assert notification.message == "test"
        assert notification.priority == 5
        assert isinstance(notification, INotification)


# Test Handler base classes


class TestHandlerBases:
    @pytest.mark.asyncio
    async def test_command_handler(self):
        """Test CommandHandler base class"""
        handler = SimpleCommandHandler()
        command = SimpleCommand(message="test command")

        result = await handler.handle_async(command)

        assert result == "Handled: test command"
        assert len(handler.handled_commands) == 1
        assert handler.handled_commands[0] == command

    @pytest.mark.asyncio
    async def test_query_handler(self):
        """Test QueryHandler base class"""
        handler = SimpleQueryHandler()
        query = SimpleQuery(value=21)

        result = await handler.handle_async(query)

        assert result == 42
        assert len(handler.handled_queries) == 1
        assert handler.handled_queries[0] == query

    @pytest.mark.asyncio
    async def test_event_handler(self):
        """Test EventHandler base class"""
        handler = SimpleEventHandler()
        event = SimpleEvent(data="test", timestamp=datetime.utcnow())

        await handler.handle_async(event)

        assert len(handler.handled_events) == 1
        assert handler.handled_events[0] == event

    @pytest.mark.asyncio
    async def test_notification_handler(self):
        """Test NotificationHandler base class"""
        handler = FirstNotificationHandler()
        notification = TestNotification(message="test", priority=3)

        await handler.handle_async(notification)

        assert len(handler.handled_notifications) == 1
        assert handler.handled_notifications[0] == notification


# Test Mediator


class TestMediator:
    def setup_method(self):
        """Set up test mediator with handlers"""
        self.service_collection = ServiceCollection()

        # Register handlers
        self.command_handler = SimpleCommandHandler()
        self.query_handler = SimpleQueryHandler()
        self.event_handler = SimpleEventHandler()
        self.notification_handler1 = FirstNotificationHandler()
        self.notification_handler2 = SecondNotificationHandler()

        self.service_collection.add_singleton(SimpleCommandHandler, self.command_handler)
        self.service_collection.add_singleton(SimpleQueryHandler, self.query_handler)
        self.service_collection.add_singleton(SimpleEventHandler, self.event_handler)
        self.service_collection.add_singleton(FirstNotificationHandler, self.notification_handler1)
        self.service_collection.add_singleton(SecondNotificationHandler, self.notification_handler2)

        self.service_provider = self.service_collection.build_service_provider()
        self.mediator = Mediator(self.service_provider)

    @pytest.mark.asyncio
    async def test_send_command(self):
        """Test sending command through mediator"""
        command = SimpleCommand(message="test command")

        result = await self.mediator.send_async(command)

        assert result == "Handled: test command"
        assert len(self.command_handler.handled_commands) == 1
        assert self.command_handler.handled_commands[0] == command

    @pytest.mark.asyncio
    async def test_send_query(self):
        """Test sending query through mediator"""
        query = SimpleQuery(value=15)

        result = await self.mediator.send_async(query)

        assert result == 30
        assert len(self.query_handler.handled_queries) == 1
        assert self.query_handler.handled_queries[0] == query

    @pytest.mark.asyncio
    async def test_publish_event(self):
        """Test publishing event through mediator"""
        event = SimpleEvent(data="test event", timestamp=datetime.utcnow())

        await self.mediator.publish_async(event)

        assert len(self.event_handler.handled_events) == 1
        assert self.event_handler.handled_events[0] == event

    @pytest.mark.asyncio
    async def test_publish_notification(self):
        """Test publishing notification to multiple handlers"""
        notification = TestNotification(message="test notification", priority=2)

        await self.mediator.publish_async(notification)

        # Both handlers should have received the notification
        assert len(self.notification_handler1.handled_notifications) == 1
        assert len(self.notification_handler2.handled_notifications) == 1
        assert self.notification_handler1.handled_notifications[0] == notification
        assert self.notification_handler2.handled_notifications[0] == notification

    @pytest.mark.asyncio
    async def test_send_command_no_handler(self):
        """Test sending command with no registered handler"""
        # Create mediator with empty service provider
        empty_collection = ServiceCollection()
        empty_provider = empty_collection.build_service_provider()
        empty_mediator = Mediator(empty_provider)

        command = SimpleCommand(message="no handler")

        with pytest.raises(Exception):  # Should raise exception for missing handler
            await empty_mediator.send_async(command)

    @pytest.mark.asyncio
    async def test_send_command_handler_error(self):
        """Test command handler that throws exception"""
        collection = ServiceCollection()
        failing_handler = FailingCommandHandler()
        collection.add_singleton(FailingCommandHandler, failing_handler)

        provider = collection.build_service_provider()
        mediator = Mediator(provider)

        command = SimpleCommand(message="will fail")

        with pytest.raises(ValueError, match="Intentional error"):
            await mediator.send_async(command)

    @pytest.mark.asyncio
    async def test_publish_event_no_handler(self):
        """Test publishing event with no registered handler"""
        # Create mediator with empty service provider
        empty_collection = ServiceCollection()
        empty_provider = empty_collection.build_service_provider()
        empty_mediator = Mediator(empty_provider)

        event = SimpleEvent(data="no handler", timestamp=datetime.utcnow())

        # Should not raise exception - events can have zero handlers
        await empty_mediator.publish_async(event)


# Test comprehensive CQRS scenarios


class TestCQRSScenarios:
    def setup_method(self):
        """Set up comprehensive CQRS test scenario"""
        self.service_collection = ServiceCollection()

        # Set up repositories
        self.user_repository = InMemoryTestUserRepository()
        self.user_dto_repository = InMemoryTestUserDtoRepository()

        # Set up mapper
        from neuroglia.mapping.mapper import Mapper

        self.mapper = Mapper()
        self.mapper.create_map(TestUser, TestUserDto).add_member_mapping(lambda src: src.full_name, lambda dst: dst.full_name)

        # Set up handlers
        self.create_user_handler = CreateTestUserCommandHandler(self.user_repository, self.mapper)
        self.get_user_handler = GetTestUserQueryHandler(self.user_dto_repository)
        self.list_users_handler = ListTestUsersQueryHandler(self.user_dto_repository)
        self.user_created_event_handler = TestUserCreatedEventHandler()

        # Register handlers
        self.service_collection.add_singleton(CreateTestUserCommandHandler, self.create_user_handler)
        self.service_collection.add_singleton(GetTestUserQueryHandler, self.get_user_handler)
        self.service_collection.add_singleton(ListTestUsersQueryHandler, self.list_users_handler)
        self.service_collection.add_singleton(TestUserCreatedEventHandler, self.user_created_event_handler)

        self.service_provider = self.service_collection.build_service_provider()
        self.mediator = Mediator(self.service_provider)

    @pytest.mark.asyncio
    async def test_create_user_command(self):
        """Test complete user creation workflow"""
        command = CreateTestUserCommand(email="test@example.com", first_name="John", last_name="Doe")

        result = await self.mediator.send_async(command)

        assert result.is_success
        assert result.data is not None
        assert result.data.email == "test@example.com"
        assert result.data.first_name == "John"
        assert result.data.last_name == "Doe"
        assert result.data.full_name == "John Doe"

        # Verify user was saved to repository
        users = await self.user_repository.find_async(lambda u: u.email == "test@example.com")
        assert len(users) == 1
        assert users[0].first_name == "John"

    @pytest.mark.asyncio
    async def test_create_duplicate_user_command(self):
        """Test creating user with duplicate email"""
        # Create first user
        await self.user_repository.add_async(TestUser(id="1", email="duplicate@example.com", first_name="First", last_name="User"))

        # Try to create user with same email
        command = CreateTestUserCommand(email="duplicate@example.com", first_name="Second", last_name="User")

        result = await self.mediator.send_async(command)

        assert not result.is_success
        assert result.status_code == 409  # Conflict
        assert "already exists" in result.error_message

    @pytest.mark.asyncio
    async def test_get_user_query(self):
        """Test getting user by ID"""
        # Add user to DTO repository
        user_dto = TestUserDto(
            id="123",
            email="query@example.com",
            first_name="Query",
            last_name="User",
            full_name="Query User",
            is_active=True,
        )
        await self.user_dto_repository.add_async(user_dto)

        query = GetTestUserQuery(user_id="123")
        result = await self.mediator.send_async(query)

        assert result.is_success
        assert result.data.id == "123"
        assert result.data.email == "query@example.com"
        assert result.data.full_name == "Query User"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_query(self):
        """Test getting user that doesn't exist"""
        query = GetTestUserQuery(user_id="nonexistent")
        result = await self.mediator.send_async(query)

        assert not result.is_success
        assert result.status_code == 404  # Not Found
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_list_users_query(self):
        """Test listing users"""
        # Add test users
        users = [
            TestUserDto(
                id="1",
                email="user1@example.com",
                first_name="User",
                last_name="One",
                full_name="User One",
                is_active=True,
            ),
            TestUserDto(
                id="2",
                email="user2@example.com",
                first_name="User",
                last_name="Two",
                full_name="User Two",
                is_active=False,
            ),
            TestUserDto(
                id="3",
                email="user3@example.com",
                first_name="User",
                last_name="Three",
                full_name="User Three",
                is_active=True,
            ),
        ]

        for user in users:
            await self.user_dto_repository.add_async(user)

        # Query active users only
        query = ListTestUsersQuery(active_only=True)
        result = await self.mediator.send_async(query)

        assert result.is_success
        assert len(result.data) == 2  # Only active users
        assert all(user.is_active for user in result.data)

        # Query all users
        query_all = ListTestUsersQuery(active_only=False)
        result_all = await self.mediator.send_async(query_all)

        assert result_all.is_success
        assert len(result_all.data) == 3  # All users

    @pytest.mark.asyncio
    async def test_event_publishing(self):
        """Test publishing domain events"""
        event = TestUserCreatedEvent(
            user_id="123",
            email="event@example.com",
            first_name="Event",
            last_name="User",
            created_at=datetime.utcnow(),
        )

        await self.mediator.publish_async(event)

        assert len(self.user_created_event_handler.handled_events) == 1
        assert self.user_created_event_handler.handled_events[0] == event


# Test error handling and edge cases


class TestMediatorErrorHandling:
    @pytest.mark.asyncio
    async def test_mediator_with_null_service_provider(self):
        """Test mediator behavior with null service provider"""
        with pytest.raises(Exception):  # Should raise exception
            Mediator(None)

    @pytest.mark.asyncio
    async def test_send_null_command(self):
        """Test sending null command"""
        collection = ServiceCollection()
        provider = collection.build_service_provider()
        mediator = Mediator(provider)

        with pytest.raises(Exception):  # Should raise exception
            await mediator.send_async(None)

    @pytest.mark.asyncio
    async def test_publish_null_event(self):
        """Test publishing null event"""
        collection = ServiceCollection()
        provider = collection.build_service_provider()
        mediator = Mediator(provider)

        with pytest.raises(Exception):  # Should raise exception
            await mediator.publish_async(None)


# Integration tests combining multiple features


class TestMediatorIntegration:
    @pytest.mark.asyncio
    async def test_full_user_lifecycle(self):
        """Test complete user lifecycle using CQRS"""
        # Set up
        service_collection = ServiceCollection()
        user_repository = InMemoryTestUserRepository()
        user_dto_repository = InMemoryTestUserDtoRepository()

        from neuroglia.mapping.mapper import Mapper

        mapper = Mapper()
        mapper.create_map(TestUser, TestUserDto).add_member_mapping(lambda src: src.full_name, lambda dst: dst.full_name)

        # Register handlers
        create_handler = CreateTestUserCommandHandler(user_repository, mapper)
        get_handler = GetTestUserQueryHandler(user_dto_repository)
        list_handler = ListTestUsersQueryHandler(user_dto_repository)

        service_collection.add_singleton(CreateTestUserCommandHandler, create_handler)
        service_collection.add_singleton(GetTestUserQueryHandler, get_handler)
        service_collection.add_singleton(ListTestUsersQueryHandler, list_handler)

        provider = service_collection.build_service_provider()
        mediator = Mediator(provider)

        # 1. Create user
        create_command = CreateTestUserCommand(email="lifecycle@example.com", first_name="Life", last_name="Cycle")

        create_result = await mediator.send_async(create_command)
        assert create_result.is_success
        user_id = create_result.data.id

        # Sync to DTO repository (normally done by event handler)
        user_dto = TestUserDto(
            id=user_id,
            email="lifecycle@example.com",
            first_name="Life",
            last_name="Cycle",
            full_name="Life Cycle",
            is_active=True,
        )
        await user_dto_repository.add_async(user_dto)

        # 2. Get user
        get_query = GetTestUserQuery(user_id=user_id)
        get_result = await mediator.send_async(get_query)
        assert get_result.is_success
        assert get_result.data.email == "lifecycle@example.com"

        # 3. List users
        list_query = ListTestUsersQuery(active_only=True)
        list_result = await mediator.send_async(list_query)
        assert list_result.is_success
        assert len(list_result.data) == 1
        assert list_result.data[0].id == user_id
