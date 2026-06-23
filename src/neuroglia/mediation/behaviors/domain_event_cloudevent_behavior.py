"""Pipeline behavior that transforms domain events into CloudEvents."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, cast
from uuid import uuid4

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.mediation.pipeline_behavior import PipelineBehavior

log = logging.getLogger(__name__)


class DomainEventCloudEventBehavior(PipelineBehavior[object, Any]):
    """Converts decorated domain events to CloudEvent payloads and emits them."""

    def __init__(self, cloud_event_bus: CloudEventBus, publishing_options: Optional[CloudEventPublishingOptions] = None) -> None:
        self._cloud_event_bus = cloud_event_bus
        self._options = publishing_options

    async def handle_async(self, request: object, next_handler: Callable[[], Awaitable[Any]]) -> Any:
        result = await next_handler()
        if not isinstance(request, DomainEvent):
            return result

        try:
            cloud_event = self._transform_domain_event(request)
            if cloud_event is not None:
                log.debug("Emitting CloudEvent '%s' for domain event '%s'", cloud_event.type, type(request).__name__)
                self._cloud_event_bus.output_stream.on_next(cloud_event)
        except Exception as exc:  # pragma: no cover - defensive guard
            log.exception("Failed to emit CloudEvent for domain event '%s': %s", type(request).__name__, exc)

        return result

    def _transform_domain_event(self, domain_event: DomainEvent) -> Optional[CloudEvent]:
        raw_type = getattr(domain_event.__class__, "__cloudevent__type__", None)
        if not raw_type:
            log.debug("Skipping domain event '%s' - no CloudEvent metadata", type(domain_event).__name__)
            return None

        event_id = uuid4().hex
        source = self._resolve_source(domain_event)
        event_type = self._resolve_type(raw_type)
        subject = self._resolve_subject(domain_event)
        payload = self._extract_payload(domain_event)

        return CloudEvent(
            id=event_id,
            source=source,
            type=event_type,
            specversion=CloudEventSpecVersion.v1_0,
            time=datetime.now(timezone.utc),
            subject=subject,
            data=payload,
        )

    def _resolve_source(self, domain_event: DomainEvent) -> str:
        if self._options and getattr(self._options, "source", None):
            return self._options.source
        return f"/{domain_event.__module__}"

    def _resolve_type(self, raw_type: str) -> str:
        if self._options and getattr(self._options, "type_prefix", None):
            prefix = self._options.type_prefix.rstrip(".")
            if raw_type.startswith(f"{prefix}.") or raw_type == prefix:
                return raw_type
            return f"{prefix}.{raw_type}"
        return raw_type

    def _resolve_subject(self, domain_event: DomainEvent) -> Optional[str]:
        aggregate_id = getattr(domain_event, "aggregate_id", None)
        if aggregate_id is None:
            aggregate_id = getattr(domain_event, "id", None)
        return str(aggregate_id) if aggregate_id is not None else None

    def _extract_payload(self, domain_event: DomainEvent) -> dict[str, Any]:
        raw_payload: dict[str, Any]
        if is_dataclass(domain_event):
            raw_payload = cast(dict[str, Any], asdict(domain_event))
        else:
            dict_callable = getattr(domain_event, "dict", None)
            model_dump_callable = getattr(domain_event, "model_dump", None)
            if callable(dict_callable):  # Pydantic v1 compatibility
                raw_payload = cast(dict[str, Any], dict_callable())
            elif callable(model_dump_callable):  # Pydantic v2 compatibility
                raw_payload = cast(dict[str, Any], model_dump_callable())
            else:
                raw_payload = {key: value for key, value in domain_event.__dict__.items() if not key.startswith("_")}

        # Ensure the aggregate id is always present in the payload for consumers.
        if "aggregate_id" not in raw_payload and hasattr(domain_event, "aggregate_id"):
            raw_payload["aggregate_id"] = getattr(domain_event, "aggregate_id")

        return self._sanitize(raw_payload)

    def _sanitize(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, DomainEvent):  # Nested domain events
            return self._extract_payload(value)
        if isinstance(value, dict):
            return {key: self._sanitize(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize(item) for item in value]
        if isinstance(value, bytes):
            return value.decode()
        return value

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
        """Registers the CloudEvent emission behavior in the pipeline."""

        builder.services.try_add_singleton(CloudEventBus)

        def factory(sp):
            bus = sp.get_required_service(CloudEventBus)
            options = sp.get_service(CloudEventPublishingOptions)
            return DomainEventCloudEventBehavior(bus, options)

        builder.services.add_scoped(
            PipelineBehavior,
            implementation_factory=factory,
        )
        return builder


__all__ = ["DomainEventCloudEventBehavior"]
