from datetime import datetime, timezone

import pytest

from neuroglia.eventing.cloud_events.cloud_event import (
    CloudEvent,
    CloudEventSpecVersion,
)
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_bus import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
    CloudEventPublishingOptions,
)
from neuroglia.serialization.json import JsonSerializer


class _DummyResponse:
    status_code = 200

    def raise_for_status(self) -> None:  # pragma: no cover - trivial
        return None


@pytest.mark.asyncio
async def test_cloud_event_publisher_posts_json_payload(monkeypatch) -> None:
    bus = CloudEventBus()
    serializer = JsonSerializer()
    options = CloudEventPublishingOptions(
        sink_uri="http://localhost/events",
        source="tests",
        type_prefix="io.tests",
    )
    publisher = CloudEventPublisher(options, bus, serializer)

    captured: dict[str, str] = {}

    def _client_factory():
        class _DummyClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *, url: str, headers: dict[str, str], content):
                captured["url"] = url
                captured["content"] = content
                captured["content_type"] = headers.get("Content-Type", "")
                return _DummyResponse()

        return _DummyClient()

    monkeypatch.setattr(
        "neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher.httpx.AsyncClient",
        _client_factory,
    )

    event = CloudEvent(
        id="evt-1",
        source="/tests",
        type="tests.event",
        specversion=CloudEventSpecVersion.v1_0,
        time=datetime.now(timezone.utc),
        data={"value": "abc"},
    )

    await publisher.on_publish_cloud_event_async(event)

    assert captured["url"] == options.sink_uri
    assert captured["content_type"] == "application/cloudevents+json"
    assert isinstance(captured["content"], str)
    assert captured["content"] == serializer.serialize_to_text(event)
