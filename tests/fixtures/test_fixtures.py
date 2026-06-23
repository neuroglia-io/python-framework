"""
Test fixtures and shared test utilities for Neuroglia tests.
"""

import pytest
import asyncio
from typing import List, Optional, Dict, Any
from unittest.mock import Mock
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from neuroglia.dependency_injection.service_provider import ServiceCollection, ServiceProviderBase
from neuroglia.data.abstractions import Entity, AggregateRoot, DomainEvent, AggregateState
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation.mediator import (
    Command,
    Query,
    CommandHandler,
    QueryHandler,
    DomainEventHandler,
)
from neuroglia.core.operation_result import OperationResult
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator


# Test Data Models


@dataclass
class TestUser(Entity[str]):
    """Test user entity"""

    id: str
    email: str
    first_name: str
    last_name: str
    is_active: bool = True
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class TestUserDto:
    """Test user DTO"""

    id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    is_active: bool
    created_at: datetime = None


@dataclass
class CreateTestUserDto:
    """DTO for creating test user"""

    email: str
    first_name: str
    last_name: str


@dataclass
class TestAddress:
    """Test address value object"""

    street: str
    city: str
    postal_code: str
    country: str


# Test Events


@dataclass
class TestUserCreatedEvent(DomainEvent):
    """Test domain event for user creation"""

    user_id: str
    email: str
    first_name: str
    last_name: str
    created_at: datetime


@dataclass
class TestUserEmailChangedEvent(DomainEvent):
    """Test domain event for email change"""

    user_id: str
    old_email: str
    new_email: str
    changed_at: datetime


# Test Aggregate


class TestUserState(AggregateState[str]):
    """Test aggregate state"""

    def __init__(self):
        super().__init__()
        self.email: Optional[str] = None
        self.first_name: Optional[str] = None
        self.last_name: Optional[str] = None


class TestUserAggregate(AggregateRoot[TestUserState, str]):
    """Test aggregate for event sourcing tests"""

    def __init__(self, id: str = None):
        super().__init__(id or str(uuid4()))
        self.email = None
        self.first_name = None
        self.last_name = None
        self.is_active = True
        self.created_at = None

    def create(self, email: str, first_name: str, last_name: str):
        """Create a new user"""
        if not email or "@" not in email:
            raise ValueError("Valid email is required")

        if not first_name or not last_name:
            raise ValueError("First name and last name are required")

        event = TestUserCreatedEvent(
            user_id=self.id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            created_at=datetime.utcnow(),
        )
        self.apply(event)

    def change_email(self, new_email: str):
        """Change user email"""
        if not new_email or "@" not in new_email:
            raise ValueError("Valid email is required")

        if new_email == self.email:
            return  # No change needed

        old_email = self.email
        event = TestUserEmailChangedEvent(
            user_id=self.id, old_email=old_email, new_email=new_email, changed_at=datetime.utcnow()
        )
        self.apply(event)

    def deactivate(self):
        """Deactivate the user"""
        self.is_active = False

    # Event handlers
    def on_test_user_created(self, event: TestUserCreatedEvent):
        self.email = event.email
        self.first_name = event.first_name
        self.last_name = event.last_name
        self.created_at = event.created_at

    def on_test_user_email_changed(self, event: TestUserEmailChangedEvent):
        self.email = event.new_email


# Test Commands and Queries


@dataclass
class CreateTestUserCommand(Command[OperationResult[TestUserDto]]):
    """Test command for creating users"""

    email: str
    first_name: str
    last_name: str


@dataclass
class GetTestUserQuery(Query[OperationResult[TestUserDto]]):
    """Test query for getting user by ID"""

    user_id: str


@dataclass
class ListTestUsersQuery(Query[OperationResult[List[TestUserDto]]]):
    """Test query for listing users"""

    active_only: bool = True


@dataclass
class ChangeUserEmailCommand(Command[OperationResult[TestUserDto]]):
    """Test command for changing user email"""

    user_id: str
    new_email: str


# Test Handlers


class CreateTestUserCommandHandler(
    CommandHandler[CreateTestUserCommand, OperationResult[TestUserDto]]
):
    """Test command handler"""

    def __init__(self, user_repository: Repository[TestUser, str], mapper: Mapper):
        self.user_repository = user_repository
        self.mapper = mapper

    async def handle_async(self, command: CreateTestUserCommand) -> OperationResult[TestUserDto]:
        try:
            # Check if user already exists
            existing_users = await self.user_repository.find_async(
                lambda u: u.email == command.email
            )
            if existing_users:
                return self.conflict("User with this email already exists")

            # Create new user
            user = TestUser(
                id=str(uuid4()),
                email=command.email,
                first_name=command.first_name,
                last_name=command.last_name,
            )

            # Save user
            saved_user = await self.user_repository.add_async(user)

            # Map to DTO
            user_dto = self.mapper.map(saved_user, TestUserDto)
            return self.created(user_dto)

        except Exception as ex:
            return self.internal_error(f"Failed to create user: {ex}")


class GetTestUserQueryHandler(QueryHandler[GetTestUserQuery, OperationResult[TestUserDto]]):
    """Test query handler"""

    def __init__(self, user_repository: Repository[TestUserDto, str]):
        self.user_repository = user_repository

    async def handle_async(self, query: GetTestUserQuery) -> OperationResult[TestUserDto]:
        user = await self.user_repository.get_by_id_async(query.user_id)

        if user is None:
            return self.not_found(f"User with ID {query.user_id} not found")

        return self.ok(user)


class ListTestUsersQueryHandler(
    QueryHandler[ListTestUsersQuery, OperationResult[List[TestUserDto]]]
):
    """Test query handler for listing users"""

    def __init__(self, user_repository: Repository[TestUserDto, str]):
        self.user_repository = user_repository

    async def handle_async(self, query: ListTestUsersQuery) -> OperationResult[List[TestUserDto]]:
        if query.active_only:
            users = await self.user_repository.find_async(lambda u: u.is_active)
        else:
            users = await self.user_repository.find_async(lambda u: True)

        return self.ok(users)


class TestUserCreatedEventHandler(DomainEventHandler[TestUserCreatedEvent]):
    """Test event handler"""

    def __init__(self):
        self.handled_events: List[TestUserCreatedEvent] = []

    async def handle_async(self, notification: TestUserCreatedEvent) -> None:
        self.handled_events.append(notification)


# Test Repository Implementation


class InMemoryTestUserRepository(Repository[TestUser, str]):
    """In-memory repository for testing"""

    def __init__(self):
        self._users: Dict[str, TestUser] = {}
        self._next_id = 1

    async def get_by_id_async(self, user_id: str) -> Optional[TestUser]:
        return self._users.get(user_id)

    async def add_async(self, user: TestUser) -> TestUser:
        if user.id is None:
            user.id = str(self._next_id)
            self._next_id += 1

        self._users[user.id] = user
        return user

    async def update_async(self, user: TestUser) -> TestUser:
        if user.id not in self._users:
            raise ValueError(f"User with ID {user.id} not found")

        self._users[user.id] = user
        return user

    async def remove_async(self, user: TestUser):
        if user.id in self._users:
            del self._users[user.id]

    async def find_async(self, predicate) -> List[TestUser]:
        return [user for user in self._users.values() if predicate(user)]

    async def get_by_email_async(self, email: str) -> Optional[TestUser]:
        """Custom method for finding by email"""
        for user in self._users.values():
            if user.email == email:
                return user
        return None


class InMemoryTestUserDtoRepository(Repository[TestUserDto, str]):
    """In-memory DTO repository for testing"""

    def __init__(self):
        self._users: Dict[str, TestUserDto] = {}

    async def get_by_id_async(self, user_id: str) -> Optional[TestUserDto]:
        return self._users.get(user_id)

    async def add_async(self, user: TestUserDto) -> TestUserDto:
        self._users[user.id] = user
        return user

    async def update_async(self, user: TestUserDto) -> TestUserDto:
        self._users[user.id] = user
        return user

    async def remove_async(self, user: TestUserDto):
        if user.id in self._users:
            del self._users[user.id]

    async def find_async(self, predicate) -> List[TestUserDto]:
        return [user for user in self._users.values() if predicate(user)]


# Test Services


class TestEmailService:
    """Mock email service for testing"""

    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []

    async def send_welcome_email(self, email: str, name: str):
        self.sent_emails.append(
            {"type": "welcome", "to": email, "name": name, "sent_at": datetime.utcnow()}
        )

    async def send_email_change_notification(self, email: str, old_email: str):
        self.sent_emails.append(
            {
                "type": "email_change",
                "to": email,
                "old_email": old_email,
                "sent_at": datetime.utcnow(),
            }
        )

    def clear(self):
        """Clear all sent emails for test isolation"""
        self.sent_emails.clear()


# Pytest Fixtures


@pytest.fixture
def service_collection():
    """Fresh service collection for each test"""
    return ServiceCollection()


@pytest.fixture
def user_repository():
    """In-memory user repository for testing"""
    return InMemoryTestUserRepository()


@pytest.fixture
def user_dto_repository():
    """In-memory user DTO repository for testing"""
    return InMemoryTestUserDtoRepository()


@pytest.fixture
def email_service():
    """Mock email service for testing"""
    return TestEmailService()


@pytest.fixture
def test_mapper():
    """Configured mapper for tests"""
    mapper = Mapper()
    # Configure mappings
    mapper.create_map(TestUser, TestUserDto).add_member_mapping(
        lambda src: src.full_name, lambda dst: dst.full_name
    )
    mapper.create_map(CreateTestUserDto, CreateTestUserCommand)
    return mapper


@pytest.fixture
def test_mediator(service_collection, user_repository, user_dto_repository, test_mapper):
    """Configured mediator for tests"""
    # Register handlers
    service_collection.add_singleton(
        CreateTestUserCommandHandler,
        lambda: CreateTestUserCommandHandler(user_repository, test_mapper),
    )
    service_collection.add_singleton(
        GetTestUserQueryHandler, lambda: GetTestUserQueryHandler(user_dto_repository)
    )
    service_collection.add_singleton(
        ListTestUsersQueryHandler, lambda: ListTestUsersQueryHandler(user_dto_repository)
    )

    provider = service_collection.build_service_provider()
    return Mediator(provider)


@pytest.fixture
def test_user_data():
    """Sample test user data"""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": True,
        "created_at": datetime.utcnow(),
    }


@pytest.fixture
def test_user(test_user_data):
    """Test user instance"""
    return TestUser(**test_user_data)


@pytest.fixture
def test_user_dto(test_user_data):
    """Test user DTO instance"""
    return TestUserDto(
        **test_user_data, full_name=f"{test_user_data['first_name']} {test_user_data['last_name']}"
    )


@pytest.fixture
def create_user_dto():
    """Create user DTO for testing"""
    return CreateTestUserDto(email="newuser@example.com", first_name="Jane", last_name="Smith")


@pytest.fixture
def mock_service_provider():
    """Mock service provider for unit tests"""
    mock = Mock(spec=ServiceProviderBase)
    mock.get_service = Mock()
    mock.get_required_service = Mock()
    mock.get_services = Mock(return_value=[])
    return mock


@pytest.fixture
def event_loop():
    """Event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_mapper():
    """Reset mapper state between tests"""
    # Clear any existing mappings to avoid test interference
    Mapper._mappings = {}
    yield
    Mapper._mappings = {}


# Helper Functions


def create_test_users(count: int = 3) -> List[TestUser]:
    """Create multiple test users"""
    users = []
    for i in range(count):
        user = TestUser(
            id=str(uuid4()),
            email=f"user{i}@example.com",
            first_name=f"User{i}",
            last_name="Test",
            is_active=i % 2 == 0,  # Alternate active/inactive
            created_at=datetime.utcnow(),
        )
        users.append(user)
    return users


def create_test_user_dtos(count: int = 3) -> List[TestUserDto]:
    """Create multiple test user DTOs"""
    dtos = []
    for i in range(count):
        dto = TestUserDto(
            id=str(uuid4()),
            email=f"user{i}@example.com",
            first_name=f"User{i}",
            last_name="Test",
            full_name=f"User{i} Test",
            is_active=i % 2 == 0,
            created_at=datetime.utcnow(),
        )
        dtos.append(dto)
    return dtos


async def populate_repository(repository: Repository, entities: List):
    """Helper to populate repository with test data"""
    for entity in entities:
        await repository.add_async(entity)


def assert_operation_result_success(result: OperationResult, expected_data=None):
    """Assert that operation result is successful"""
    assert result.is_success, f"Operation failed: {result.error_message}"
    if expected_data is not None:
        assert result.data == expected_data


def assert_operation_result_error(result: OperationResult, expected_status_code: int = None):
    """Assert that operation result is an error"""
    assert not result.is_success, "Expected operation to fail"
    if expected_status_code is not None:
        assert result.status_code == expected_status_code
