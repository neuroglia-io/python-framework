"""
Integration tests for state-based persistence with domain event dispatching.

These tests demonstrate the complete workflow from command execution through
domain event dispatching, showing how all components work together.
"""

from unittest.mock import Mock

import pytest

from neuroglia.core import OperationResult
from neuroglia.data.abstractions import DomainEvent, Entity
from neuroglia.data.unit_of_work import IUnitOfWork, UnitOfWork
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation import Command, CommandHandler
from neuroglia.mediation.behaviors.domain_event_dispatching_middleware import (
    DomainEventDispatchingMiddleware,
)
from neuroglia.mediation.mediator import Mediator


# Test Domain Events
class UserCreatedEvent(DomainEvent):
    """Domain event raised when a user is created."""

    def __init__(self, user_id: str, email: str):
        super().__init__(aggregate_id=user_id)
        self.user_id = user_id
        self.email = email


class UserActivatedEvent(DomainEvent):
    """Domain event raised when a user is activated."""

    def __init__(self, user_id: str):
        super().__init__(aggregate_id=user_id)
        self.user_id = user_id


# Test Domain Entity
class User(Entity):
    """Test user entity for state-based persistence."""

    def __init__(self, id: str, email: str, name: str):
        super().__init__()
        self._id = id
        self.email = email
        self.name = name
        self.is_active = False

        # Raise domain event
        self.register_event(UserCreatedEvent(id, email))

    @property
    def id(self):
        return self._id

    def activate(self):
        """Activates the user and raises domain event."""
        if not self.is_active:
            self.is_active = True
            self.register_event(UserActivatedEvent(self.id))

    def register_event(self, event: DomainEvent):
        """Registers a domain event with this entity."""
        if not hasattr(self, "_pending_events"):
            self._pending_events = []
        self._pending_events.append(event)

    @property
    def domain_events(self):
        """Gets the pending domain events for state-based persistence."""
        return getattr(self, "_pending_events", [])

    def clear_pending_events(self):
        """Clears all pending domain events."""
        if hasattr(self, "_pending_events"):
            self._pending_events.clear()


# Test Repository
class UserRepository:
    """Mock user repository for testing."""

    def __init__(self):
        self._users = {}

    async def save_async(self, user: User):
        """Saves a user (mock implementation)."""
        self._users[user.id] = user

    async def get_by_id_async(self, user_id: str) -> User | None:
        """Gets a user by ID (mock implementation)."""
        return self._users.get(user_id)


# Test Commands
class CreateUserCommand(Command[OperationResult]):
    """Command to create a new user."""

    def __init__(self, email: str, name: str):
        self.email = email
        self.name = name


class ActivateUserCommand(Command[OperationResult]):
    """Command to activate an existing user."""

    def __init__(self, user_id: str):
        self.user_id = user_id


# Test Command Handlers
class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult]):
    """Handler for creating users with state-based persistence."""

    def __init__(self, user_repository: UserRepository, unit_of_work: IUnitOfWork):
        self.user_repository = user_repository
        self.unit_of_work = unit_of_work

    async def handle_async(self, request: CreateUserCommand) -> OperationResult:
        """Handles user creation command."""
        # Create user entity (raises UserCreatedEvent)
        user = User(
            id=f"user_{len(self.user_repository._users) + 1}",
            email=request.email,
            name=request.name,
        )

        # Save to repository
        await self.user_repository.save_async(user)

        # Register with unit of work for automatic event dispatching
        self.unit_of_work.register_aggregate(user)  # type: ignore[arg-type]

        return self.created({"user_id": user.id, "email": user.email})


class ActivateUserHandler(CommandHandler[ActivateUserCommand, OperationResult]):
    """Handler for activating users with state-based persistence."""

    def __init__(self, user_repository: UserRepository, unit_of_work: IUnitOfWork):
        self.user_repository = user_repository
        self.unit_of_work = unit_of_work

    async def handle_async(self, request: ActivateUserCommand) -> OperationResult:
        """Handles user activation command."""
        # Get user from repository
        user = await self.user_repository.get_by_id_async(request.user_id)
        if not user:
            return self.not_found(User, request.user_id)

        # Activate user (raises UserActivatedEvent)
        user.activate()

        # Save changes
        await self.user_repository.save_async(user)

        # Register with unit of work for automatic event dispatching
        self.unit_of_work.register_aggregate(user)  # type: ignore[arg-type]

        return self.ok({"user_id": user.id, "is_active": user.is_active})


# Test Event Handlers
class UserCreatedEventHandler:
    """Handler for UserCreatedEvent."""

    def __init__(self):
        self.handled_events = []

    async def handle_async(self, event: UserCreatedEvent):
        """Handles user created event."""
        self.handled_events.append(event)


class UserActivatedEventHandler:
    """Handler for UserActivatedEvent."""

    def __init__(self):
        self.handled_events = []

    async def handle_async(self, event: UserActivatedEvent):
        """Handles user activated event."""
        self.handled_events.append(event)


@pytest.mark.integration
@pytest.mark.skip(reason="DomainEventDispatchingMiddleware is deprecated and no longer dispatches events; state-based persistence workflow is retained only for reference.")
class TestStateBasedPersistenceIntegration:
    """Integration tests for the complete state-based persistence workflow."""

    def setup_method(self):
        """Setup test dependencies."""
        # Create dependencies
        self.services = ServiceCollection()
        self.user_repository = UserRepository()
        self.unit_of_work = UnitOfWork()

        # Create event handlers
        self.user_created_handler = UserCreatedEventHandler()
        self.user_activated_handler = UserActivatedEventHandler()

        # Mock mediator that dispatches to our test handlers
        self.mock_mediator = Mock(spec=Mediator)

        async def mock_publish_async(event):
            if isinstance(event, UserCreatedEvent):
                await self.user_created_handler.handle_async(event)
            elif isinstance(event, UserActivatedEvent):
                await self.user_activated_handler.handle_async(event)

        self.mock_mediator.publish_async = mock_publish_async

        # Create middleware
        self.domain_event_middleware = DomainEventDispatchingMiddleware(self.unit_of_work, self.mock_mediator)

        # Create handlers
        self.create_user_handler = CreateUserHandler(self.user_repository, self.unit_of_work)
        self.activate_user_handler = ActivateUserHandler(self.user_repository, self.unit_of_work)

    @pytest.mark.asyncio
    async def test_create_user_workflow(self):
        """Test complete workflow for creating a user with automatic event dispatching."""
        # Setup
        command = CreateUserCommand("john@example.com", "John Doe")

        async def handler_execution():
            return await self.create_user_handler.handle_async(command)

        # Execute through middleware
        result = await self.domain_event_middleware.handle_async(command, handler_execution)

        # Verify command result
        assert result.is_success
        assert result.data["email"] == "john@example.com"

        # Verify user was saved
        user_id = result.data["user_id"]
        saved_user = await self.user_repository.get_by_id_async(user_id)
        assert saved_user is not None
        assert saved_user.email == "john@example.com"
        assert saved_user.name == "John Doe"

        # Verify domain event was dispatched
        assert len(self.user_created_handler.handled_events) == 1
        event = self.user_created_handler.handled_events[0]
        assert isinstance(event, UserCreatedEvent)
        assert event.user_id == user_id
        assert event.email == "john@example.com"

        # Verify unit of work is cleared
        assert not self.unit_of_work.has_changes()

    @pytest.mark.asyncio
    async def test_activate_user_workflow(self):
        """Test complete workflow for activating a user with automatic event dispatching."""
        # Setup - create a user first
        user = User("user_1", "john@example.com", "John Doe")
        await self.user_repository.save_async(user)

        # Clear any events from user creation
        user.clear_pending_events()

        # Execute activation command
        command = ActivateUserCommand("user_1")

        async def handler_execution():
            return await self.activate_user_handler.handle_async(command)

        # Execute through middleware
        result = await self.domain_event_middleware.handle_async(command, handler_execution)

        # Verify command result
        assert result.is_success
        assert result.data["is_active"] is True

        # Verify user was updated
        updated_user = await self.user_repository.get_by_id_async("user_1")
        assert updated_user is not None
        assert updated_user.is_active is True

        # Verify domain event was dispatched
        assert len(self.user_activated_handler.handled_events) == 1
        event = self.user_activated_handler.handled_events[0]
        assert isinstance(event, UserActivatedEvent)
        assert event.user_id == "user_1"

        # Verify unit of work is cleared
        assert not self.unit_of_work.has_changes()

    @pytest.mark.asyncio
    async def test_failed_command_skips_event_dispatching(self):
        """Test that failed commands don't trigger event dispatching."""
        # Setup - try to activate non-existent user
        command = ActivateUserCommand("non_existent_user")

        async def handler_execution():
            return await self.activate_user_handler.handle_async(command)

        # Execute through middleware
        result = await self.domain_event_middleware.handle_async(command, handler_execution)

        # Verify command failed
        assert not result.is_success
        assert result.status_code == 404

        # Verify no events were dispatched
        assert len(self.user_activated_handler.handled_events) == 0

        # Verify unit of work is cleared
        assert not self.unit_of_work.has_changes()

    @pytest.mark.asyncio
    async def test_multiple_aggregates_in_single_command(self):
        """Test handling multiple aggregates with events in a single command."""
        # This would be a more complex scenario where a single command
        # modifies multiple aggregates, each raising their own events

        # For this test, we'll simulate by manually registering multiple users
        user1 = User("user_1", "user1@example.com", "User One")
        user2 = User("user_2", "user2@example.com", "User Two")

        # Simulate a command that affects both users
        self.unit_of_work.register_aggregate(user1)  # type: ignore[arg-type]
        self.unit_of_work.register_aggregate(user2)  # type: ignore[arg-type]

        # Create a dummy successful command
        command = CreateUserCommand("dummy@example.com", "Dummy")

        async def handler_execution():
            return OperationResult("OK", 200)

        # Execute through middleware
        result = await self.domain_event_middleware.handle_async(command, handler_execution)

        # Verify command succeeded
        assert result.is_success

        # Verify events from both users were dispatched
        assert len(self.user_created_handler.handled_events) == 2

        # Verify correct events were dispatched
        user_ids = [event.user_id for event in self.user_created_handler.handled_events]
        assert "user_1" in user_ids
        assert "user_2" in user_ids

    @pytest.mark.asyncio
    async def test_entity_compatibility_with_existing_patterns(self):
        """Test that entities work with both event sourcing and state-based patterns."""
        user = User("user_1", "test@example.com", "Test User")

        # Test domain_events property (state-based)
        events_via_property = user.domain_events
        assert len(events_via_property) == 1
        assert isinstance(events_via_property[0], UserCreatedEvent)

        # Test get_uncommitted_events (event sourcing compatibility)
        if hasattr(user, "get_uncommitted_events"):
            events_via_method = user.get_uncommitted_events()  # type: ignore[attr-defined]
            assert len(events_via_method) == 1
            assert events_via_method[0] == events_via_property[0]

        # Test clearing events
        user.clear_pending_events()
        assert len(user.domain_events) == 0
