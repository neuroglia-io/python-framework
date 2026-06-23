from unittest.mock import AsyncMock

import pytest

from neuroglia.core import OperationResult
from neuroglia.mediation.pipeline_behavior import BasePipelineBehavior, PipelineBehavior


class TestRequest:
    """Test request for pipeline behavior testing."""

    def __init__(self, value: str):
        self.value = value


class TestPipelineBehavior(PipelineBehavior):
    """Test pipeline behavior implementation."""

    def __init__(self, name: str):
        self.name = name
        self.called = False
        self.call_order = []

    async def handle_async(self, request, next_handler):
        self.called = True
        self.call_order.append(f"{self.name}_start")

        # Call next handler
        result = await next_handler()

        self.call_order.append(f"{self.name}_end")
        return result


class ModifyingPipelineBehavior(PipelineBehavior):
    """Test pipeline behavior that modifies the result."""

    def __init__(self, prefix: str):
        self.prefix = prefix

    async def handle_async(self, request, next_handler):
        result = await next_handler()

        # Modify the result
        if isinstance(result, OperationResult) and result.data:
            result.data = f"{self.prefix}_{result.data}"

        return result


class ExceptionPipelineBehavior(PipelineBehavior):
    """Test pipeline behavior that raises an exception."""

    def __init__(self, should_raise: bool = True):
        self.should_raise = should_raise

    async def handle_async(self, request, next_handler):
        if self.should_raise:
            raise ValueError("Test exception from pipeline behavior")

        return await next_handler()


class TestPipelineBehaviorInterface:
    """Tests for the PipelineBehavior interface and base implementations."""

    def test_pipeline_behavior_is_abstract(self):
        """Test that PipelineBehavior cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PipelineBehavior()

    def test_base_pipeline_behavior_default_implementation(self):
        """Test that BasePipelineBehavior provides default pass-through behavior."""
        behavior = BasePipelineBehavior()
        assert behavior is not None

    @pytest.mark.asyncio
    async def test_base_pipeline_behavior_calls_next_handler(self):
        """Test that BasePipelineBehavior calls the next handler by default."""
        behavior = BasePipelineBehavior()
        request = TestRequest("test")

        # Mock next handler
        next_handler = AsyncMock(return_value="handler_result")

        result = await behavior.handle_async(request, next_handler)

        assert result == "handler_result"
        next_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_pipeline_behavior_execution(self):
        """Test that custom pipeline behaviors execute correctly."""
        behavior = TestPipelineBehavior("test_behavior")
        request = TestRequest("test")

        next_handler = AsyncMock(return_value="handler_result")

        result = await behavior.handle_async(request, next_handler)

        assert result == "handler_result"
        assert behavior.called
        assert "test_behavior_start" in behavior.call_order
        assert "test_behavior_end" in behavior.call_order
        next_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_behavior_can_modify_result(self):
        """Test that pipeline behaviors can modify the result from handlers."""
        behavior = ModifyingPipelineBehavior("MODIFIED")
        request = TestRequest("test")

        # Create a mock result
        original_result = OperationResult("OK", 200)
        original_result.data = "original_data"

        next_handler = AsyncMock(return_value=original_result)

        result = await behavior.handle_async(request, next_handler)

        assert result.data == "MODIFIED_original_data"
        next_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_behavior_exception_propagation(self):
        """Test that exceptions from pipeline behaviors are properly propagated."""
        behavior = ExceptionPipelineBehavior(should_raise=True)
        request = TestRequest("test")

        next_handler = AsyncMock(return_value="should_not_reach")

        with pytest.raises(ValueError, match="Test exception from pipeline behavior"):
            await behavior.handle_async(request, next_handler)

        # Next handler should not be called if behavior raises exception
        next_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_pipeline_behavior_exception_from_handler(self):
        """Test that exceptions from handlers propagate through behaviors."""
        behavior = TestPipelineBehavior("test_behavior")
        request = TestRequest("test")

        # Mock handler that raises exception
        next_handler = AsyncMock(side_effect=RuntimeError("Handler exception"))

        with pytest.raises(RuntimeError, match="Handler exception"):
            await behavior.handle_async(request, next_handler)

        assert behavior.called
        # Should have started but not ended due to exception
        assert "test_behavior_start" in behavior.call_order
        assert "test_behavior_end" not in behavior.call_order


class TestPipelineBehaviorChaining:
    """Tests for chaining multiple pipeline behaviors together."""

    @pytest.mark.asyncio
    async def test_multiple_behaviors_execution_order(self):
        """Test that multiple behaviors execute in the correct order."""
        behavior1 = TestPipelineBehavior("first")
        behavior2 = TestPipelineBehavior("second")

        # Manually chain behaviors
        async def create_chain():
            request = TestRequest("test")

            async def final_handler():
                return "final_result"

            async def second_chain():
                return await behavior2.handle_async(request, final_handler)

            return await behavior1.handle_async(request, second_chain)

        result = await create_chain()

        assert result == "final_result"
        assert behavior1.called
        assert behavior2.called

        # Check execution order: first starts, second starts, second ends, first ends
        expected_order = ["first_start", "second_start", "second_end", "first_end"]
        actual_order = behavior1.call_order + behavior2.call_order

        # Verify the order
        first_start = actual_order.index("first_start")
        second_start = actual_order.index("second_start")
        second_end = actual_order.index("second_end")
        first_end = actual_order.index("first_end")

        assert first_start < second_start < second_end < first_end

    @pytest.mark.asyncio
    async def test_behavior_chain_with_result_modification(self):
        """Test behavior chain where each behavior modifies the result."""
        behavior1 = ModifyingPipelineBehavior("FIRST")
        behavior2 = ModifyingPipelineBehavior("SECOND")

        # Chain behaviors manually
        async def create_chain():
            request = TestRequest("test")

            async def final_handler():
                result = OperationResult("OK", 200)
                result.data = "original"
                return result

            async def second_chain():
                return await behavior2.handle_async(request, final_handler)

            return await behavior1.handle_async(request, second_chain)

        result = await create_chain()

        # Result should be modified by both behaviors: FIRST_SECOND_original
        assert result.data == "FIRST_SECOND_original"

    @pytest.mark.asyncio
    async def test_behavior_chain_exception_handling(self):
        """Test exception handling in behavior chains."""
        behavior1 = TestPipelineBehavior("first")
        behavior2 = ExceptionPipelineBehavior(should_raise=True)

        async def create_chain():
            request = TestRequest("test")

            async def final_handler():
                return "should_not_reach"

            async def second_chain():
                return await behavior2.handle_async(request, final_handler)

            return await behavior1.handle_async(request, second_chain)

        with pytest.raises(ValueError, match="Test exception from pipeline behavior"):
            await create_chain()

        # First behavior should have started but not completed
        assert behavior1.called
        assert "first_start" in behavior1.call_order
        assert "first_end" not in behavior1.call_order
