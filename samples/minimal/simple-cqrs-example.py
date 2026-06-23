"""
Simple CQRS Example
==================

This example demonstrates how to use Neuroglia's simplified CQRS patterns
for basic applications without requiring complex cloud events infrastructure.

This example shows:
- Basic command and query handling
- Simple dependency injection setup
- In-memory repository for testing
- Minimal configuration requirements
"""

import asyncio
import uuid
from dataclasses import dataclass
from typing import Optional

from neuroglia.core.operation_result import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection

# Import Neuroglia framework components
from neuroglia.mediation import (
    Command,
    CommandHandler,
    InMemoryRepository,
    Mediator,
    Query,
    QueryHandler,
)

# ====================
# DOMAIN MODELS
# ====================


@dataclass
class User:
    """Domain entity representing a user"""

    id: str
    name: str
    email: str
    is_active: bool = True

    def deactivate(self):
        """Business method to deactivate user"""
        self.is_active = False


@dataclass
class UserDto:
    """Data transfer object for API responses"""

    id: str
    name: str
    email: str
    is_active: bool


# ====================
# CQRS COMMANDS & QUERIES
# ====================


@dataclass
class CreateUserCommand(Command[OperationResult[UserDto]]):
    """Command to create a new user"""

    name: str
    email: str


@dataclass
class UpdateUserCommand(Command[OperationResult[UserDto]]):
    """Command to update an existing user"""

    user_id: str
    name: str
    email: str


@dataclass
class DeactivateUserCommand(Command[OperationResult[UserDto]]):
    """Command to deactivate a user"""

    user_id: str


@dataclass
class GetUserByIdQuery(Query[Optional[UserDto]]):
    """Query to get a user by ID"""

    user_id: str


@dataclass
class GetUserByEmailQuery(Query[Optional[UserDto]]):
    """Query to get a user by email"""

    email: str


@dataclass
class ListActiveUsersQuery(Query[list[UserDto]]):
    """Query to get all active users"""


# ====================
# REPOSITORIES
# ====================


class UserRepository(InMemoryRepository[User]):
    """User repository extending the in-memory base repository"""

    async def get_by_email_async(self, email: str) -> Optional[User]:
        """Find user by email address"""
        for user in self._storage.values():
            if user.email == email:
                return user
        return None

    async def get_active_users_async(self) -> list[User]:
        """Get all active users"""
        return [user for user in self._storage.values() if user.is_active]


# ====================
# COMMAND HANDLERS
# ====================


class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
    """Handler for creating new users"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
        # Validate input
        if not command.name.strip():
            return self.bad_request("Name cannot be empty")

        if not command.email.strip():
            return self.bad_request("Email cannot be empty")

        if "@" not in command.email:
            return self.bad_request("Invalid email format")

        # Check if user already exists
        existing_user = await self.user_repository.get_by_email_async(command.email)
        if existing_user:
            return self.conflict(f"User with email {command.email} already exists")

        # Create new user
        user = User(id=str(uuid.uuid4()), name=command.name.strip(), email=command.email.strip().lower())

        # Save user
        await self.user_repository.save_async(user)

        # Return success
        user_dto = UserDto(user.id, user.name, user.email, user.is_active)
        return self.created(user_dto)


class UpdateUserHandler(CommandHandler[UpdateUserCommand, OperationResult[UserDto]]):
    """Handler for updating existing users"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    async def handle_async(self, command: UpdateUserCommand) -> OperationResult[UserDto]:
        # Get existing user
        user = await self.user_repository.get_by_id_async(command.user_id)
        if not user:
            return self.not_found(f"User with ID {command.user_id} not found")

        # Validate input
        if not command.name.strip():
            return self.bad_request("Name cannot be empty")

        if not command.email.strip():
            return self.bad_request("Email cannot be empty")

        if "@" not in command.email:
            return self.bad_request("Invalid email format")

        # Check if email is taken by another user
        existing_user = await self.user_repository.get_by_email_async(command.email)
        if existing_user and existing_user.id != user.id:
            return self.conflict(f"User with email {command.email} already exists")

        # Update user
        user.name = command.name.strip()
        user.email = command.email.strip().lower()

        # Save user
        await self.user_repository.save_async(user)

        # Return success
        user_dto = UserDto(user.id, user.name, user.email, user.is_active)
        return self.ok(user_dto)


class DeactivateUserHandler(CommandHandler[DeactivateUserCommand, OperationResult[UserDto]]):
    """Handler for deactivating users"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    async def handle_async(self, command: DeactivateUserCommand) -> OperationResult[UserDto]:
        # Get existing user
        user = await self.user_repository.get_by_id_async(command.user_id)
        if not user:
            return self.not_found(f"User with ID {command.user_id} not found")

        # Check if already deactivated
        if not user.is_active:
            return self.bad_request("User is already deactivated")

        # Deactivate user using domain method
        user.deactivate()

        # Save user
        await self.user_repository.save_async(user)

        # Return success
        user_dto = UserDto(user.id, user.name, user.email, user.is_active)
        return self.ok(user_dto)


# ====================
# QUERY HANDLERS
# ====================


class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, Optional[UserDto]]):
    """Handler for getting user by ID"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    async def handle_async(self, query: GetUserByIdQuery) -> Optional[UserDto]:
        user = await self.user_repository.get_by_id_async(query.user_id)
        if not user:
            return None

        return UserDto(user.id, user.name, user.email, user.is_active)


class GetUserByEmailHandler(QueryHandler[GetUserByEmailQuery, Optional[UserDto]]):
    """Handler for getting user by email"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    async def handle_async(self, query: GetUserByEmailQuery) -> Optional[UserDto]:
        user = await self.user_repository.get_by_email_async(query.email)
        if not user:
            return None

        return UserDto(user.id, user.name, user.email, user.is_active)


class ListActiveUsersHandler(QueryHandler[ListActiveUsersQuery, list[UserDto]]):
    """Handler for listing all active users"""

    def __init__(self, user_repository: UserRepository):
        super().__init__()
        self.user_repository = user_repository

    async def handle_async(self, query: ListActiveUsersQuery) -> list[UserDto]:
        users = await self.user_repository.get_active_users_async()
        return [UserDto(user.id, user.name, user.email, user.is_active) for user in users]


# ====================
# APPLICATION SETUP
# ====================


def create_application():
    """
    Create and configure the application with simple CQRS setup.

    This shows the minimal configuration needed for a basic CQRS application.
    """
    # Create service collection
    services = ServiceCollection()

    # Add mediator
    services.add_singleton(Mediator)

    # Register repository
    services.add_singleton(UserRepository)

    # Register command handlers
    services.add_scoped(CreateUserHandler)
    services.add_scoped(UpdateUserHandler)
    services.add_scoped(DeactivateUserHandler)

    # Register query handlers
    services.add_scoped(GetUserByIdHandler)
    services.add_scoped(GetUserByEmailHandler)
    services.add_scoped(ListActiveUsersHandler)

    # Build service provider
    provider = services.build()

    # Register handlers in mediator's handler registry
    if not hasattr(Mediator, "_handler_registry"):
        Mediator._handler_registry = {}
    Mediator._handler_registry[CreateUserCommand] = CreateUserHandler
    Mediator._handler_registry[UpdateUserCommand] = UpdateUserHandler
    Mediator._handler_registry[DeactivateUserCommand] = DeactivateUserHandler
    Mediator._handler_registry[GetUserByIdQuery] = GetUserByIdHandler
    Mediator._handler_registry[GetUserByEmailQuery] = GetUserByEmailHandler
    Mediator._handler_registry[ListActiveUsersQuery] = ListActiveUsersHandler

    return provider


# ====================
# EXAMPLE USAGE
# ====================


async def run_example():
    """Run a complete example demonstrating all CQRS operations"""

    print("🚀 Starting Simple CQRS Example")
    print("=" * 50)

    # Create application
    provider = create_application()
    mediator: Mediator = provider.get_service(Mediator)  # type: ignore

    print("\n📝 Creating users...")

    # Create first user
    create_user1 = CreateUserCommand("John Doe", "john.doe@example.com")
    result1 = await mediator.execute_async(create_user1)

    if result1.is_success:
        print(f"✅ Created user: {result1.data.name} ({result1.data.email})")
        user1_id = result1.data.id
    else:
        print(f"❌ Failed to create user: {result1.error_message}")
        return

    # Create second user
    create_user2 = CreateUserCommand("Jane Smith", "jane.smith@example.com")
    result2 = await mediator.execute_async(create_user2)

    if result2.is_success:
        print(f"✅ Created user: {result2.data.name} ({result2.data.email})")
        user2_id = result2.data.id
    else:
        print(f"❌ Failed to create user: {result2.error_message}")
        return

    # Try to create duplicate user (should fail)
    create_duplicate = CreateUserCommand("John Duplicate", "john.doe@example.com")
    result_duplicate = await mediator.execute_async(create_duplicate)

    if not result_duplicate.is_success:
        print(f"✅ Correctly rejected duplicate email: {result_duplicate.error_message}")

    print("\n🔍 Querying users...")

    # Get user by ID
    get_by_id = GetUserByIdQuery(user1_id)
    user = await mediator.execute_async(get_by_id)

    if user:
        print(f"✅ Found user by ID: {user.name} ({user.email})")
    else:
        print("❌ User not found by ID")

    # Get user by email
    get_by_email = GetUserByEmailQuery("jane.smith@example.com")
    user = await mediator.execute_async(get_by_email)

    if user:
        print(f"✅ Found user by email: {user.name} ({user.email})")
    else:
        print("❌ User not found by email")

    # List all active users
    list_users = ListActiveUsersQuery()
    users = await mediator.execute_async(list_users)

    print(f"✅ Found {len(users)} active users:")
    for user in users:
        print(f"   - {user.name} ({user.email}) [Active: {user.is_active}]")

    print("\n✏️  Updating user...")

    # Update user
    update_user = UpdateUserCommand(user1_id, "John Updated", "john.updated@example.com")
    result_update = await mediator.execute_async(update_user)

    if result_update.is_success:
        print(f"✅ Updated user: {result_update.data.name} ({result_update.data.email})")
    else:
        print(f"❌ Failed to update user: {result_update.error_message}")

    print("\n🚫 Deactivating user...")

    # Deactivate user
    deactivate_user = DeactivateUserCommand(user2_id)
    result_deactivate = await mediator.execute_async(deactivate_user)

    if result_deactivate.is_success:
        print(f"✅ Deactivated user: {result_deactivate.data.name} [Active: {result_deactivate.data.is_active}]")
    else:
        print(f"❌ Failed to deactivate user: {result_deactivate.error_message}")

    # List active users again
    print("\n📋 Final active users list:")
    users = await mediator.execute_async(list_users)

    print(f"✅ Found {len(users)} active users:")
    for user in users:
        print(f"   - {user.name} ({user.email}) [Active: {user.is_active}]")

    print("\n🎉 Example completed successfully!")


# ====================
# MAIN ENTRY POINT
# ====================

if __name__ == "__main__":
    # Run the example
    asyncio.run(run_example())
