import json
from dataclasses import dataclass
from typing import ClassVar, Optional

import pytest

from neuroglia.serialization.json import JsonSerializer


@dataclass
class DataclassTaskState:
    name: str
    assignee_id: Optional[str] = None
    effort_hours: Optional[int] = None


class PlainTaskState:
    # Simulate a pre-existing class attribute that should not be copied to instances
    serializer_version: ClassVar[str] = "v1"

    name: str
    description: Optional[str]
    assignee_id: Optional[str]


@pytest.fixture()
def serializer() -> JsonSerializer:
    return JsonSerializer()


def test_dataclass_optional_fields_are_populated_with_none(serializer: JsonSerializer) -> None:
    payload = {"name": "Demo Task"}

    state = serializer.deserialize_from_text(json.dumps(payload), DataclassTaskState)

    assert state.name == "Demo Task"
    assert state.assignee_id is None
    assert state.effort_hours is None


def test_plain_class_optional_fields_are_populated_with_none(serializer: JsonSerializer) -> None:
    payload = {"name": "Plain Task"}

    state = serializer.deserialize_from_text(json.dumps(payload), PlainTaskState)

    assert state.name == "Plain Task"
    assert state.assignee_id is None
    assert state.description is None
    # Ensure ClassVars are not treated as instance attributes
    assert "serializer_version" not in state.__dict__
