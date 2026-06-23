from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

import pytest
from rx.subject.subject import Subject

from neuroglia.core import OperationResult
from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.decorators import cloudevent
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mediation import Command
from neuroglia.mediation.behaviors.domain_event_cloudevent_behavior import (
    DomainEventCloudEventBehavior,
)
from neuroglia.mediation.behaviors.domain_event_dispatching_middleware import (
    TransactionBehavior,
)


class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@cloudevent("order.payment.updated.v1")
@dataclass
class PaymentUpdatedEvent(DomainEvent[str]):
    aggregate_id: str
    amount: Decimal
    occurred_at: datetime
    status: PaymentStatus
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        super().__init__(self.aggregate_id)


class UndecoratedEvent(DomainEvent[str]):
    def __init__(self, aggregate_id: str):
        super().__init__(aggregate_id)


class TestDomainEventCloudEventBehavior:
    """Tests for transforming domain events into CloudEvents."""

    def setup_method(self) -> None:
        self.bus = CloudEventBus()
        self.options = CloudEventPublishingOptions(
            sink_uri="http://example.com",
            source="/services/payments",
            type_prefix="com.example",
            retry_attempts=3,
            retry_delay=0.1,
        )
        self.behavior = DomainEventCloudEventBehavior(self.bus, self.options)
        self.bus.output_stream = Subject()
        self.captured_events: list[CloudEvent] = []
        self.bus.output_stream.subscribe(self.captured_events.append)

    @pytest.mark.asyncio
    async def test_non_domain_event_passes_through(self) -> None:
        async def next_handler() -> str:
            return "ok"

        result = await self.behavior.handle_async(object(), next_handler)

        assert result == "ok"
        assert not self.captured_events

    @pytest.mark.asyncio
    async def test_undecorated_domain_event_skips_emission(self) -> None:
        event = UndecoratedEvent("order-123")

        async def next_handler() -> str:
            return "done"

        result = await self.behavior.handle_async(event, next_handler)

        assert result == "done"
        assert not self.captured_events

    @pytest.mark.asyncio
    async def test_emits_cloudevent_for_decorated_domain_event(self) -> None:
        occurred_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        event = PaymentUpdatedEvent(
            aggregate_id="order-42",
            amount=Decimal("19.99"),
            occurred_at=occurred_at,
            status=PaymentStatus.COMPLETED,
            metadata={"notes": ["test", b"binary"], "nested": {"value": Decimal("2.5")}},
        )

        async def next_handler() -> str:
            return "processed"

        result = await self.behavior.handle_async(event, next_handler)

        assert result == "processed"
        assert len(self.captured_events) == 1
        cloud_event = self.captured_events[0]

        assert cloud_event.source == self.options.source
        assert cloud_event.type == "com.example.order.payment.updated.v1"
        assert cloud_event.subject == "order-42"
        assert cloud_event.specversion == CloudEventSpecVersion.v1_0

        assert cloud_event.data is not None
        payload = cloud_event.data
        assert payload["aggregate_id"] == "order-42"
        assert payload["amount"] == "19.99"
        assert payload["status"] == PaymentStatus.COMPLETED.value
        assert payload["occurred_at"] == occurred_at.isoformat()
        assert payload["metadata"]["notes"][1] == "binary"
        assert payload["metadata"]["nested"]["value"] == "2.5"

    @pytest.mark.asyncio
    async def test_prefix_not_applied_when_already_present(self) -> None:
        @cloudevent("com.example.preprefixed")
        class PrePrefixedEvent(DomainEvent[str]):
            def __init__(self) -> None:
                super().__init__("agg-1")

        async def next_handler() -> None:
            return None

        await self.behavior.handle_async(PrePrefixedEvent(), next_handler)

        assert self.captured_events
        cloud_event = self.captured_events[-1]
        assert cloud_event.type == "com.example.preprefixed"

    @pytest.mark.asyncio
    async def test_source_defaults_to_module_path(self) -> None:
        behavior = DomainEventCloudEventBehavior(self.bus, publishing_options=None)

        async def next_handler() -> None:
            return None

        await behavior.handle_async(
            PaymentUpdatedEvent(
                aggregate_id="agg-2",
                amount=Decimal("10"),
                occurred_at=datetime.now(timezone.utc),
                status=PaymentStatus.PENDING,
                metadata={},
            ),
            next_handler,
        )

        assert self.captured_events
        cloud_event = self.captured_events[-1]
        assert cloud_event.source.endswith("tests.cases.test_domain_event_dispatching_middleware")


class TestCommand(Command[OperationResult]):
    def __init__(self, value: str):
        self.value = value


class TestTransactionBehavior:
    """Tests for the TransactionBehavior placeholder implementation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.behavior = TransactionBehavior()

    @pytest.mark.asyncio
    async def test_successful_command_execution(self):
        """Test transaction behavior with successful command execution."""
        command = TestCommand("test")
        expected_result = OperationResult("OK", 200)

        async def mock_next_handler():
            return expected_result

        result = await self.behavior.handle_async(command, mock_next_handler)

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_failed_command_execution(self):
        """Test transaction behavior with failed command execution."""
        command = TestCommand("test")
        failed_result = OperationResult("Bad Request", 400)

        async def mock_next_handler():
            return failed_result

        result = await self.behavior.handle_async(command, mock_next_handler)

        assert result == failed_result

    @pytest.mark.asyncio
    async def test_command_exception_propagation(self):
        """Test that command handler exceptions are properly propagated."""
        command = TestCommand("test")

        async def mock_next_handler():
            raise ValueError("Command failed")

        with pytest.raises(ValueError, match="Command failed"):
            await self.behavior.handle_async(command, mock_next_handler)

    @pytest.mark.asyncio
    async def test_transaction_behavior_is_pipeline_behavior(self):
        """Test that TransactionBehavior implements PipelineBehavior interface."""
        from neuroglia.mediation.pipeline_behavior import PipelineBehavior

        assert isinstance(self.behavior, PipelineBehavior)
