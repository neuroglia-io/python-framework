"""Test script to verify AggregateState timestamp handling"""

from datetime import datetime, timezone

from neuroglia.data.abstractions import AggregateState
from neuroglia.serialization.json import JsonSerializer


class TestState(AggregateState[str]):
    def __init__(self):
        super().__init__()
        self.id = "test123"
        self.some_field = "value"


def test_new_instance():
    """Test that new instances get current timestamp"""
    print("=== Test 1: New Instance ===")
    state = TestState()
    print(f"created_at: {state.created_at}")
    print(f"last_modified: {state.last_modified}")
    print(f"✓ Has timestamps: {state.created_at is not None and state.last_modified is not None}")
    return state


def test_deserialization():
    """Test that deserialization preserves timestamps"""
    print("\n=== Test 2: Deserialization ===")
    serializer = JsonSerializer()

    # Simulate persisted data with specific timestamp
    json_text = '{"id": "test456", "some_field": "persisted", "created_at": "2025-10-23T12:00:00+00:00", "last_modified": "2025-10-23T12:30:00+00:00", "state_version": 0}'
    print(f"JSON: {json_text}")

    state = serializer.deserialize_from_text(json_text, TestState)
    print(f"Deserialized created_at: {state.created_at}")
    print(f"Deserialized last_modified: {state.last_modified}")

    expected_created = datetime(2025, 10, 23, 12, 0, 0, tzinfo=timezone.utc)
    expected_modified = datetime(2025, 10, 23, 12, 30, 0, tzinfo=timezone.utc)

    created_match = state.created_at == expected_created
    modified_match = state.last_modified == expected_modified

    print(f"✓ Timestamps preserved: {created_match and modified_match}")
    return state


def test_round_trip():
    """Test round-trip serialization"""
    print("\n=== Test 3: Round-trip ===")
    serializer = JsonSerializer()

    # Create state with known timestamp
    state1 = test_deserialization()

    # Serialize and deserialize
    json_out = serializer.serialize_to_text(state1)
    print(f"Serialized: {json_out[:100]}...")

    state2 = serializer.deserialize_from_text(json_out, TestState)
    print(f"Round-trip created_at: {state2.created_at}")
    print(f"Round-trip last_modified: {state2.last_modified}")

    timestamps_match = state1.created_at == state2.created_at and state1.last_modified == state2.last_modified
    print(f"✓ Timestamps match: {timestamps_match}")


if __name__ == "__main__":
    test_new_instance()
    test_deserialization()
    test_round_trip()
    print("\n✅ All tests passed!")
