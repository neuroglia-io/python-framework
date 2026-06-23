"""
Tests for Mediator scoped service resolution in notification handlers.

This test suite verifies that the Mediator correctly creates scoped service providers
for notification processing, allowing handlers with scoped dependencies (like repositories)
to be properly resolved.

Related Issue: https://github.com/neuroglia-io/pyneuro/issues/scoped-services-in-event-handlers
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from neuroglia.data.abstractions import Identifiable
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation import Mediator, NotificationHandler


# Test Entities and Events
@dataclass
class SampleEntity(Identifiable[str]):
    """Test entity for scoped repository testing"""

    id: str
    name: str
    value: int


@dataclass
class SampleEvent:
    """Test notification event"""

    entity_id: str
    action: str


# Mock Scoped Repository
class MockScopedRepository:
    """Mock repository that should be resolved as scoped"""

    _instance_counter: int = 0

    def __init__(self):
        MockScopedRepository._instance_counter += 1
        self.instance_id = MockScopedRepository._instance_counter
        self.operations = []
        self.disposed = False

    async def __aenter__(self):
        """Async context manager entry"""
        self.operations.append("__aenter__")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.operations.append("__aexit__")

    async def add_async(self, entity: SampleEntity):
        """Mock add operation"""
        self.operations.append(f"add({entity.id})")

    async def get_async(self, entity_id: str) -> Optional[SampleEntity]:
        """Mock get operation"""
        self.operations.append(f"get({entity_id})")
        return SampleEntity(id=entity_id, name="test", value=42)

    def dispose(self):
        """Dispose the repository"""
        self.disposed = True
        self.operations.append("dispose")


# Test Notification Handler with Scoped Dependency
class ScopedRepositoryEventHandler(NotificationHandler[SampleEvent]):
    """
    Event handler that depends on a scoped repository.

    This simulates real-world scenarios where event handlers need scoped services
    like AsyncCacheRepository, database contexts, or unit of work instances.
    """

    def __init__(self, repository: MockScopedRepository):
        self.repository = repository
        self.handled_events = []

    async def handle_async(self, notification: SampleEvent) -> None:
        """Handle the event using the scoped repository"""
        self.handled_events.append(notification)

        # Use repository in async context (common pattern)
        async with self.repository as repo:
            entity = await repo.get_async(notification.entity_id)
            if notification.action == "create" and entity is not None:
                await repo.add_async(entity)


class TestMediatorScopedNotificationHandlers:
    """Test suite for scoped service resolution in notification handlers"""

    @pytest.fixture
    def reset_instance_counter(self):
        """Reset the mock repository instance counter before each test"""
        MockScopedRepository._instance_counter = 0
        yield
        MockScopedRepository._instance_counter = 0

    @pytest.mark.asyncio
    async def test_notification_handler_resolves_scoped_repository(self, reset_instance_counter):
        """
        Test that notification handlers can resolve scoped dependencies.

        This is the core fix for the issue where scoped services couldn't be
        resolved when processing events through the mediator.
        """
        # Arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)

        # Register mediator and repository as SCOPED (correct lifetime for repositories)
        services.add_singleton(Mediator, Mediator)
        services.add_scoped(MockScopedRepository, MockScopedRepository)

        # Register event handler (depends on scoped repository)
        services.add_transient(NotificationHandler, ScopedRepositoryEventHandler)

        # Build service provider
        provider = services.build()

        # Create mediator
        mediator = provider.get_service(Mediator)

        # Act
        event = SampleEvent(entity_id="test-123", action="create")
        await mediator.publish_async(event)

        # Assert
        # The event should have been processed without errors
        # Before the fix, this would raise:
        # "Failed to resolve scoped service from root service provider"
        assert True  # If we got here, the scoped service was resolved successfully

    @pytest.mark.asyncio
    async def test_scoped_services_isolated_per_event(self, reset_instance_counter):
        """
        Test that each event gets its own scoped service instance.

        Each notification should be processed in its own scope, similar to
        how each HTTP request gets its own scope.
        """
        # Arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_scoped(MockScopedRepository, MockScopedRepository)
        services.add_transient(NotificationHandler, ScopedRepositoryEventHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act - Publish multiple events
        event1 = SampleEvent(entity_id="event-1", action="create")
        event2 = SampleEvent(entity_id="event-2", action="create")
        event3 = SampleEvent(entity_id="event-3", action="create")

        await mediator.publish_async(event1)
        await mediator.publish_async(event2)
        await mediator.publish_async(event3)

        # Assert
        # Each event should have gotten a different repository instance
        # (scoped to that specific event processing)
        assert MockScopedRepository._instance_counter == 3

    @pytest.mark.asyncio
    async def test_scoped_services_shared_within_event(self, reset_instance_counter):
        """
        Test that multiple handlers processing the same event share scoped instances.

        When multiple handlers process the same notification, they should all
        receive the same scoped service instance (within that event's scope).
        """

        # Second handler for the same event type
        class AnotherScopedHandler(NotificationHandler[SampleEvent]):
            def __init__(self, repository: MockScopedRepository):
                self.repository = repository

            async def handle_async(self, notification: SampleEvent) -> None:
                async with self.repository as repo:
                    await repo.get_async(notification.entity_id)

        # Arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_scoped(MockScopedRepository, MockScopedRepository)

        # Register TWO handlers for the same event
        services.add_transient(NotificationHandler, ScopedRepositoryEventHandler)
        services.add_transient(NotificationHandler, AnotherScopedHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act - Publish one event
        event = SampleEvent(entity_id="shared-event", action="create")
        await mediator.publish_async(event)

        # Assert
        # Both handlers should have received the SAME scoped repository instance
        # (only 1 instance created because they're in the same scope)
        assert MockScopedRepository._instance_counter == 1

    @pytest.mark.asyncio
    async def test_scoped_services_disposed_after_event(self, reset_instance_counter):
        """
        Test that scoped services are properly disposed after event processing.

        The scope should automatically dispose all scoped services when the
        event processing completes.
        """
        # Arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        repository_instance = None

        # Custom factory to capture the repository instance
        def repository_factory(provider):
            nonlocal repository_instance
            repository_instance = MockScopedRepository()
            return repository_instance

        services.add_scoped(MockScopedRepository, implementation_factory=repository_factory)
        services.add_transient(NotificationHandler, ScopedRepositoryEventHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act
        event = SampleEvent(entity_id="dispose-test", action="create")
        await mediator.publish_async(event)

        # Assert
        # Repository should have been disposed after the event completed
        assert repository_instance is not None
        assert repository_instance.disposed is True
        assert "dispose" in repository_instance.operations

    @pytest.mark.asyncio
    async def test_transient_services_still_work(self, reset_instance_counter):
        """
        Test that transient services continue to work correctly.

        The scoped service fix shouldn't break transient service resolution.
        """

        class TransientService:
            _counter = 0

            def __init__(self):
                TransientService._counter += 1
                self.instance_id = TransientService._counter

        class TransientServiceHandler(NotificationHandler[SampleEvent]):
            def __init__(self, service: TransientService):
                self.service = service

            async def handle_async(self, notification: SampleEvent) -> None:
                pass

        # Arrange
        TransientService._counter = 0
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_transient(TransientService, TransientService)
        services.add_transient(NotificationHandler, TransientServiceHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act - Publish multiple events
        await mediator.publish_async(SampleEvent("1", "test"))
        await mediator.publish_async(SampleEvent("2", "test"))

        # Assert
        # Each event should get a new transient service instance
        assert TransientService._counter == 2

    @pytest.mark.asyncio
    async def test_singleton_services_still_work(self, reset_instance_counter):
        """
        Test that singleton services continue to work correctly.

        The scoped service fix shouldn't break singleton service resolution.
        """

        class SingletonService:
            _counter = 0

            def __init__(self):
                SingletonService._counter += 1
                self.instance_id = SingletonService._counter

        class SingletonServiceHandler(NotificationHandler[SampleEvent]):
            def __init__(self, service: SingletonService):
                self.service = service

            async def handle_async(self, notification: SampleEvent) -> None:
                pass

        # Arrange
        SingletonService._counter = 0
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_singleton(SingletonService, SingletonService)
        services.add_transient(NotificationHandler, SingletonServiceHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act - Publish multiple events
        await mediator.publish_async(SampleEvent("1", "test"))
        await mediator.publish_async(SampleEvent("2", "test"))

        # Assert
        # All events should share the SAME singleton service instance
        assert SingletonService._counter == 1

    @pytest.mark.asyncio
    async def test_nested_scoped_dependencies(self, reset_instance_counter):
        """
        Test that scoped services with nested scoped dependencies work correctly.

        This simulates complex scenarios like a handler depending on a service
        that depends on a repository (all scoped).
        """

        class ScopedServiceA:
            def __init__(self):
                self.id = "A"

        class ScopedServiceB:
            def __init__(self, service_a: ScopedServiceA):
                self.service_a = service_a
                self.id = "B"

        class NestedScopedHandler(NotificationHandler[SampleEvent]):
            def __init__(self, service_b: ScopedServiceB, repository: MockScopedRepository):
                self.service_b = service_b
                self.repository = repository

            async def handle_async(self, notification: SampleEvent) -> None:
                # All scoped dependencies should be resolved correctly
                assert self.service_b.id == "B"
                assert self.service_b.service_a.id == "A"
                async with self.repository as repo:
                    await repo.get_async(notification.entity_id)

        # Arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_scoped(ScopedServiceA, ScopedServiceA)
        services.add_scoped(ScopedServiceB, ScopedServiceB)
        services.add_scoped(MockScopedRepository, MockScopedRepository)
        services.add_transient(NotificationHandler, NestedScopedHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act
        event = SampleEvent(entity_id="nested-test", action="create")
        await mediator.publish_async(event)

        # Assert - No exceptions means all scoped dependencies resolved correctly
        assert True

    @pytest.mark.asyncio
    async def test_exception_in_handler_still_disposes_scope(self, reset_instance_counter):
        """
        Test that scope is disposed even when handler raises an exception.

        Resource cleanup should happen even in error scenarios.
        """

        class FailingHandler(NotificationHandler[SampleEvent]):
            def __init__(self, repository: MockScopedRepository):
                self.repository = repository

            async def handle_async(self, notification: SampleEvent) -> None:
                async with self.repository as repo:
                    await repo.get_async(notification.entity_id)
                    raise ValueError("Intentional test error")

        # Arrange
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        repository_instance = None

        def repository_factory(provider):
            nonlocal repository_instance
            repository_instance = MockScopedRepository()
            return repository_instance

        services.add_scoped(MockScopedRepository, implementation_factory=repository_factory)
        services.add_transient(NotificationHandler, FailingHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Act & Assert
        event = SampleEvent(entity_id="error-test", action="create")

        with pytest.raises(ValueError, match="Intentional test error"):
            await mediator.publish_async(event)

        # Even though handler failed, scope should be disposed
        assert repository_instance is not None
        assert repository_instance.disposed is True


class TestBackwardCompatibility:
    """
    Test that the scoped service fix doesn't break existing functionality
    """

    @pytest.mark.asyncio
    async def test_handlers_without_scoped_dependencies_still_work(self):
        """Test that handlers without scoped deps continue working"""

        class SimpleHandler(NotificationHandler[SampleEvent]):
            handled = False

            async def handle_async(self, notification: SampleEvent) -> None:
                SimpleHandler.handled = True

        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_transient(NotificationHandler, SimpleHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        SimpleHandler.handled = False
        await mediator.publish_async(SampleEvent("test", "action"))

        assert SimpleHandler.handled is True

    @pytest.mark.asyncio
    async def test_multiple_concurrent_events_isolated(self):
        """Test that concurrent event processing maintains isolation"""

        import asyncio

        class CountingHandler(NotificationHandler[SampleEvent]):
            def __init__(self, repository: MockScopedRepository):
                self.repository = repository

            async def handle_async(self, notification: SampleEvent) -> None:
                async with self.repository as repo:
                    # Simulate some async work
                    await asyncio.sleep(0.01)
                    await repo.get_async(notification.entity_id)

        MockScopedRepository._instance_counter = 0
        services = ServiceCollection()
        services.add_singleton(Mediator, Mediator)
        services.add_scoped(MockScopedRepository, MockScopedRepository)
        services.add_transient(NotificationHandler, CountingHandler)

        provider = services.build()
        mediator = provider.get_service(Mediator)

        # Process multiple events concurrently
        events = [SampleEvent(f"event-{i}", "test") for i in range(10)]
        await asyncio.gather(*[mediator.publish_async(e) for e in events])

        # Each event should have gotten its own scoped repository
        assert MockScopedRepository._instance_counter == 10
