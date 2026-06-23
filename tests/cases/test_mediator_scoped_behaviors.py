"""
Tests for scoped pipeline behavior resolution in the mediator.

This test suite validates that the mediator can properly resolve pipeline behaviors
from a scoped service provider, enabling behaviors to use scoped dependencies.
"""

from dataclasses import dataclass

import pytest

from neuroglia.core import OperationResult
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation import Command, CommandHandler, Mediator, PipelineBehavior


# Test interfaces and implementations
class IScopedDependency:
    """Interface for a scoped dependency used by behaviors"""

    def get_value(self) -> str:
        pass


class ScopedDependency(IScopedDependency):
    """Concrete scoped dependency"""

    def __init__(self):
        self.value = "scoped-value"

    def get_value(self) -> str:
        return self.value


class ITransientDependency:
    """Interface for a transient dependency"""

    def get_value(self) -> str:
        pass


class TransientDependency(ITransientDependency):
    """Concrete transient dependency"""

    def __init__(self):
        self.value = "transient-value"

    def get_value(self) -> str:
        return self.value


# Test behaviors
class ScopedBehavior(PipelineBehavior):
    """Pipeline behavior that requires a scoped dependency"""

    def __init__(self, scoped_dep: IScopedDependency):
        self.scoped_dep = scoped_dep
        self.executed = False

    async def handle_async(self, request, next):
        self.executed = True
        result = await next()
        # Mark that this behavior executed
        if hasattr(result, "data") and isinstance(result.data, dict):
            result.data["scoped_behavior_executed"] = True
            result.data["scoped_value"] = self.scoped_dep.get_value()
        return result


class TransientBehavior(PipelineBehavior):
    """Pipeline behavior with transient lifetime"""

    def __init__(self, transient_dep: ITransientDependency):
        self.transient_dep = transient_dep
        self.executed = False

    async def handle_async(self, request, next):
        self.executed = True
        result = await next()
        if hasattr(result, "data") and isinstance(result.data, dict):
            result.data["transient_behavior_executed"] = True
            result.data["transient_value"] = self.transient_dep.get_value()
        return result


class SingletonBehavior(PipelineBehavior):
    """Pipeline behavior with singleton lifetime"""

    def __init__(self):
        self.execution_count = 0

    async def handle_async(self, request, next):
        self.execution_count += 1
        result = await next()
        if hasattr(result, "data") and isinstance(result.data, dict):
            result.data["singleton_behavior_executed"] = True
            result.data["execution_count"] = self.execution_count
        return result


# Test commands and handlers
@dataclass
class TestCommand(Command[OperationResult]):
    """Test command for validation"""

    test_value: str = "test"


class TestCommandHandler(CommandHandler[TestCommand, OperationResult]):
    """Handler for test command"""

    async def handle_async(self, command: TestCommand) -> OperationResult:
        result = OperationResult(title="OK", status=200)
        result.data = {"command_handled": True, "test_value": command.test_value}
        return result


@pytest.mark.asyncio
class TestMediatorScopedBehaviors:
    """Test suite for scoped pipeline behavior resolution"""

    def _register_handler(self, request_type, handler_type):
        """Helper to register handler in mediator registry"""
        if not hasattr(Mediator, "_handler_registry"):
            Mediator._handler_registry = {}
        Mediator._handler_registry[request_type] = handler_type

    async def test_scoped_behavior_resolution(self):
        """Test that mediator can resolve scoped pipeline behaviors"""
        # Arrange
        services = ServiceCollection()

        # Register scoped dependency
        services.add_scoped(IScopedDependency, ScopedDependency)

        # Register scoped behavior that uses scoped dependency
        services.add_scoped(
            PipelineBehavior,
            implementation_factory=lambda sp: ScopedBehavior(sp.get_required_service(IScopedDependency)),
        )

        # Register command handler
        services.add_scoped(TestCommandHandler)

        # Add mediator
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Register handler in registry
        self._register_handler(TestCommand, TestCommandHandler)

        # Act - Should NOT throw "Failed to resolve scoped service"
        command = TestCommand(test_value="scoped-test")
        result = await mediator.execute_async(command)

        # Assert
        assert result.is_success, f"Expected success but got: {result}"
        assert result.data is not None
        assert result.data["command_handled"] is True
        assert result.data.get("scoped_behavior_executed") is True
        assert result.data.get("scoped_value") == "scoped-value"

    async def test_transient_behaviors_still_work(self):
        """Test backward compatibility with transient behaviors"""
        # Arrange - use transient (old pattern)
        services = ServiceCollection()

        # Register transient dependency
        services.add_transient(ITransientDependency, TransientDependency)

        # Register transient behavior
        services.add_transient(
            PipelineBehavior,
            implementation_factory=lambda sp: TransientBehavior(sp.get_required_service(ITransientDependency)),
        )

        # Register handler
        services.add_scoped(TestCommandHandler)

        # Add mediator
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Register handler in registry
        self._register_handler(TestCommand, TestCommandHandler)

        # Act
        command = TestCommand(test_value="transient-test")
        result = await mediator.execute_async(command)

        # Assert
        assert result.is_success
        assert result.data["command_handled"] is True
        assert result.data.get("transient_behavior_executed") is True
        assert result.data.get("transient_value") == "transient-value"

    async def test_singleton_behaviors_work(self):
        """Test that singleton behaviors work correctly"""
        # Arrange
        services = ServiceCollection()

        # Register singleton behavior
        singleton_instance = SingletonBehavior()
        services.add_singleton(PipelineBehavior, singleton=singleton_instance)

        # Register handler
        services.add_scoped(TestCommandHandler)

        # Add mediator
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Register handler in registry
        self._register_handler(TestCommand, TestCommandHandler)

        # Act - Execute command multiple times
        result1 = await mediator.execute_async(TestCommand(test_value="test1"))
        result2 = await mediator.execute_async(TestCommand(test_value="test2"))

        # Assert - Singleton should maintain state across executions
        assert result1.is_success
        assert result2.is_success
        assert result1.data.get("execution_count") == 1
        assert result2.data.get("execution_count") == 2  # Same instance, incremented

    async def test_mixed_behavior_lifetimes(self):
        """Test that scoped, transient, and singleton behaviors can coexist"""
        # Arrange
        services = ServiceCollection()

        # Register dependencies
        services.add_scoped(IScopedDependency, ScopedDependency)
        services.add_transient(ITransientDependency, TransientDependency)

        # Register behaviors with different lifetimes
        singleton_instance = SingletonBehavior()
        services.add_singleton(PipelineBehavior, singleton=singleton_instance)

        services.add_transient(
            PipelineBehavior,
            implementation_factory=lambda sp: TransientBehavior(sp.get_required_service(ITransientDependency)),
        )

        services.add_scoped(
            PipelineBehavior,
            implementation_factory=lambda sp: ScopedBehavior(sp.get_required_service(IScopedDependency)),
        )

        # Register handler
        services.add_scoped(TestCommandHandler)

        # Add mediator
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Register handler in registry
        self._register_handler(TestCommand, TestCommandHandler)

        # Act
        command = TestCommand(test_value="mixed-test")
        result = await mediator.execute_async(command)

        # Assert - All three behaviors should execute
        assert result.is_success
        assert result.data["command_handled"] is True
        assert result.data.get("singleton_behavior_executed") is True
        assert result.data.get("transient_behavior_executed") is True
        assert result.data.get("scoped_behavior_executed") is True
        assert result.data.get("scoped_value") == "scoped-value"
        assert result.data.get("transient_value") == "transient-value"

    async def test_scoped_behavior_gets_fresh_dependency_per_request(self):
        """Test that scoped behaviors get fresh scoped dependencies per request"""
        # Arrange
        services = ServiceCollection()

        # Counter to track dependency instances
        instance_counter = {"count": 0}

        class CountingScopedDependency(IScopedDependency):
            def __init__(self):
                instance_counter["count"] += 1
                self.instance_id = instance_counter["count"]

            def get_value(self) -> str:
                return f"instance-{self.instance_id}"

        services.add_scoped(IScopedDependency, CountingScopedDependency)

        services.add_scoped(
            PipelineBehavior,
            implementation_factory=lambda sp: ScopedBehavior(sp.get_required_service(IScopedDependency)),
        )

        services.add_scoped(TestCommandHandler)
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Register handler in registry
        self._register_handler(TestCommand, TestCommandHandler)

        # Act - Execute multiple commands
        result1 = await mediator.execute_async(TestCommand(test_value="req1"))
        result2 = await mediator.execute_async(TestCommand(test_value="req2"))

        # Assert - Each request should get a fresh scoped dependency
        assert result1.is_success
        assert result2.is_success
        assert result1.data.get("scoped_value") == "instance-1"
        assert result2.data.get("scoped_value") == "instance-2"
        assert instance_counter["count"] == 2  # Two instances created

    async def test_backward_compatibility_without_provider_parameter(self):
        """Test that behaviors still work when resolved from root provider (old code path)"""
        # Arrange - This simulates old mediator code that doesn't pass provider
        services = ServiceCollection()

        # Must use transient when resolved from root (old limitation)
        services.add_transient(PipelineBehavior, implementation_factory=lambda sp: SingletonBehavior())

        services.add_scoped(TestCommandHandler)
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Manually test old code path by calling _get_pipeline_behaviors without provider
        command = TestCommand()
        behaviors = mediator._get_pipeline_behaviors(command)  # No provider param

        # Assert - Should still work (backward compatibility)
        assert len(behaviors) == 1
        assert isinstance(behaviors[0], SingletonBehavior)

    async def test_scoped_behavior_with_multiple_scoped_dependencies(self):
        """Test behavior with multiple scoped dependencies"""
        # Arrange
        services = ServiceCollection()

        class IOtherDependency:
            def get_name(self) -> str:
                pass

        class OtherDependency(IOtherDependency):
            def __init__(self):
                self.name = "other-dep"

            def get_name(self) -> str:
                return self.name

        class ComplexBehavior(PipelineBehavior):
            def __init__(self, dep1: IScopedDependency, dep2: IOtherDependency):
                self.dep1 = dep1
                self.dep2 = dep2

            async def handle_async(self, request, next):
                result = await next()
                if hasattr(result, "data") and isinstance(result.data, dict):
                    result.data["complex_behavior_executed"] = True
                    result.data["dep1_value"] = self.dep1.get_value()
                    result.data["dep2_value"] = self.dep2.get_name()
                return result

        services.add_scoped(IScopedDependency, ScopedDependency)
        services.add_scoped(IOtherDependency, OtherDependency)

        services.add_scoped(
            PipelineBehavior,
            implementation_factory=lambda sp: ComplexBehavior(
                sp.get_required_service(IScopedDependency),
                sp.get_required_service(IOtherDependency),
            ),
        )

        services.add_scoped(TestCommandHandler)
        services.add_mediator()

        provider = services.build()
        mediator = provider.get_required_service(Mediator)

        # Register handler in registry
        self._register_handler(TestCommand, TestCommandHandler)

        # Act
        result = await mediator.execute_async(TestCommand())

        # Assert
        assert result.is_success
        assert result.data.get("complex_behavior_executed") is True
        assert result.data.get("dep1_value") == "scoped-value"
        assert result.data.get("dep2_value") == "other-dep"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
