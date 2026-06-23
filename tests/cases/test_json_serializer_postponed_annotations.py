from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from neuroglia.serialization.json import JsonSerializer

if TYPE_CHECKING:  # pragma: no cover - runtime resolution should fail

    class NotDefinedType:  # noqa: D401 - stub for typing only
        """Placeholder to satisfy static analysis for forward references."""


class DeferredChild:
    value: int


class DeferredParent:
    child: DeferredChild | None
    label: str

    def __init__(self) -> None:
        self.child = None
        self.label = ""


class UnknownAnnotationModel:
    payload: "NotDefinedType"


@pytest.fixture
def serializer() -> JsonSerializer:
    return JsonSerializer()


def test_deserialize_postponed_annotations(serializer: JsonSerializer) -> None:
    source = json.dumps({"child": {"value": 7}, "label": "task"})

    result = serializer.deserialize_from_text(source, DeferredParent)

    assert isinstance(result.child, DeferredChild)
    assert result.child.value == 7
    assert result.label == "task"


def test_unresolved_annotation_falls_back(serializer: JsonSerializer) -> None:
    source = json.dumps({"payload": {"unexpected": True}})

    result = serializer.deserialize_from_text(source, UnknownAnnotationModel)

    assert result.payload == {"unexpected": True}
