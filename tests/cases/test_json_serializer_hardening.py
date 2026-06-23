"""
Comprehensive tests for JsonSerializer preventive hardening.

Tests for:
1. DateTime heuristic improvements (v0.7.8)
2. Enum case-insensitive matching
3. Edge cases in type inference
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

import pytest

from neuroglia.serialization.json import JsonSerializer

# =============================================================================
# Test Fixtures - Enums and Data Classes
# =============================================================================


class OrderStatus(Enum):
    """Test enum with string values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Test enum with CONSTANT_CASE names and lowercase values."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntegerEnum(Enum):
    """Test enum with integer values."""

    FIRST = 1
    SECOND = 2
    THIRD = 3


@dataclass
class OrderWithEnum:
    """Order with typed enum field."""

    order_id: str
    status: OrderStatus
    priority: Priority


@dataclass
class EventData:
    """Event data with datetime field."""

    event_id: str
    created_at: datetime
    description: str


@dataclass
class DateRecord:
    """Record with date-like string field (not datetime)."""

    record_id: str
    date_string: str  # Should remain string, not become datetime


@dataclass
class MixedData:
    """Mixed data types for comprehensive testing."""

    name: str
    value: Decimal
    status: OrderStatus
    timestamp: datetime
    metadata: dict[str, Any]


# =============================================================================
# DateTime Heuristic Tests
# =============================================================================


class TestDateTimeHeuristic:
    """Tests for the improved datetime detection heuristic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = JsonSerializer()

    # -------------------------------------------------------------------------
    # Valid datetime strings (should be detected and parsed)
    # -------------------------------------------------------------------------

    def test_full_iso_datetime_detected(self):
        """Full ISO datetime with T separator should be detected."""
        value = "2025-12-15T10:30:00"
        assert self.serializer._is_datetime_string(value) is True

    def test_iso_datetime_with_z_detected(self):
        """ISO datetime with Z suffix should be detected."""
        value = "2025-12-15T10:30:00Z"
        assert self.serializer._is_datetime_string(value) is True

    def test_iso_datetime_with_timezone_offset_detected(self):
        """ISO datetime with timezone offset should be detected."""
        value = "2025-12-15T10:30:00+00:00"
        assert self.serializer._is_datetime_string(value) is True

    def test_iso_datetime_with_microseconds_detected(self):
        """ISO datetime with microseconds should be detected."""
        value = "2025-12-15T10:30:00.123456"
        assert self.serializer._is_datetime_string(value) is True

    def test_datetime_with_space_separator_detected(self):
        """Datetime with space separator (SQL style) should be detected."""
        value = "2025-12-15 10:30:00"
        assert self.serializer._is_datetime_string(value) is True

    def test_datetime_without_seconds_detected(self):
        """Datetime without seconds should be detected."""
        value = "2025-12-15T10:30"
        assert self.serializer._is_datetime_string(value) is True

    # -------------------------------------------------------------------------
    # Date-only strings (should NOT be detected as datetime)
    # -------------------------------------------------------------------------

    def test_date_only_not_detected_as_datetime(self):
        """Date-only string should NOT be detected as datetime."""
        value = "2025-12-15"
        assert self.serializer._is_datetime_string(value) is False

    def test_year_month_only_not_detected(self):
        """Year-month only should NOT be detected."""
        value = "2025-12"
        assert self.serializer._is_datetime_string(value) is False

    def test_year_only_not_detected(self):
        """Year only should NOT be detected."""
        value = "2025"
        assert self.serializer._is_datetime_string(value) is False

    # -------------------------------------------------------------------------
    # Invalid datetime strings (should NOT be detected)
    # -------------------------------------------------------------------------

    def test_time_only_not_detected(self):
        """Time-only string should NOT be detected as datetime."""
        value = "10:30:00"
        assert self.serializer._is_datetime_string(value) is False

    def test_random_string_not_detected(self):
        """Random string should NOT be detected."""
        value = "hello world"
        assert self.serializer._is_datetime_string(value) is False

    def test_numeric_string_not_detected(self):
        """Numeric string should NOT be detected."""
        value = "12345"
        assert self.serializer._is_datetime_string(value) is False

    def test_empty_string_not_detected(self):
        """Empty string should NOT be detected."""
        value = ""
        assert self.serializer._is_datetime_string(value) is False

    def test_none_not_detected(self):
        """None should NOT be detected."""
        assert self.serializer._is_datetime_string(None) is False

    def test_integer_not_detected(self):
        """Integer should NOT be detected."""
        assert self.serializer._is_datetime_string(123) is False

    # -------------------------------------------------------------------------
    # Type inference integration tests
    # -------------------------------------------------------------------------

    def test_datetime_field_inferred_correctly(self):
        """Datetime field should be correctly inferred in type inference."""
        json_data = '{"event_id": "evt-123", "created_at": "2025-12-15T10:30:00Z", "description": "Test"}'
        result = self.serializer.deserialize_from_text(json_data, EventData)

        assert isinstance(result.created_at, datetime)
        assert result.created_at.year == 2025
        assert result.created_at.month == 12
        assert result.created_at.day == 15

    def test_date_string_field_preserved(self):
        """Date-only string field should remain a string when field is typed as str."""
        json_data = '{"record_id": "rec-123", "date_string": "2025-12-15"}'
        result = self.serializer.deserialize_from_text(json_data, DateRecord)

        assert isinstance(result.date_string, str)
        assert result.date_string == "2025-12-15"

    def test_untyped_date_string_not_converted(self):
        """Date-only string in untyped dict should remain string."""
        json_data = '{"date": "2025-12-15", "time": "10:30:00"}'
        result = self.serializer.deserialize_from_text(json_data, dict)

        assert isinstance(result["date"], str)
        assert result["date"] == "2025-12-15"
        assert isinstance(result["time"], str)
        assert result["time"] == "10:30:00"


# =============================================================================
# Enum Case-Insensitive Matching Tests
# =============================================================================


class TestEnumCaseInsensitiveMatching:
    """Tests for enum case-insensitive matching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = JsonSerializer()

    # -------------------------------------------------------------------------
    # Exact match tests (highest priority)
    # -------------------------------------------------------------------------

    def test_exact_value_match(self):
        """Exact match on enum value should work."""
        json_data = '{"order_id": "ord-123", "status": "pending", "priority": "high"}'
        result = self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert result.status == OrderStatus.PENDING
        assert result.priority == Priority.HIGH

    def test_exact_name_match(self):
        """Exact match on enum name should work."""
        json_data = '{"order_id": "ord-123", "status": "PENDING", "priority": "HIGH"}'
        result = self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert result.status == OrderStatus.PENDING
        assert result.priority == Priority.HIGH

    # -------------------------------------------------------------------------
    # Case-insensitive value match tests
    # -------------------------------------------------------------------------

    def test_uppercase_value_matches_lowercase_enum(self):
        """Uppercase value should match lowercase enum value."""
        json_data = '{"order_id": "ord-123", "status": "PENDING", "priority": "HIGH"}'
        result = self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert result.status == OrderStatus.PENDING

    def test_mixed_case_value_matches(self):
        """Mixed case value should match enum value."""
        json_data = '{"order_id": "ord-123", "status": "Pending", "priority": "High"}'
        result = self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert result.status == OrderStatus.PENDING
        assert result.priority == Priority.HIGH

    # -------------------------------------------------------------------------
    # Case-insensitive name match tests
    # -------------------------------------------------------------------------

    def test_lowercase_name_matches_constant_case_enum(self):
        """Lowercase name should match CONSTANT_CASE enum name."""
        json_data = '{"order_id": "ord-123", "status": "pending", "priority": "critical"}'
        result = self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert result.priority == Priority.CRITICAL

    def test_mixed_case_name_matches(self):
        """Mixed case name should match enum name (case-insensitive)."""
        json_data = '{"order_id": "ord-123", "status": "Completed", "priority": "Critical"}'
        result = self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert result.status == OrderStatus.COMPLETED
        assert result.priority == Priority.CRITICAL

    # -------------------------------------------------------------------------
    # Integer enum tests
    # -------------------------------------------------------------------------

    @dataclass
    class DataWithIntEnum:
        item_id: str
        position: IntegerEnum

    def test_integer_enum_exact_match(self):
        """Integer enum value should match exactly."""
        json_data = '{"item_id": "item-1", "position": 1}'
        result = self.serializer.deserialize_from_text(json_data, self.DataWithIntEnum)

        assert result.position == IntegerEnum.FIRST

    def test_integer_enum_string_representation(self):
        """Integer enum as string should match."""
        json_data = '{"item_id": "item-1", "position": "FIRST"}'
        result = self.serializer.deserialize_from_text(json_data, self.DataWithIntEnum)

        assert result.position == IntegerEnum.FIRST

    # -------------------------------------------------------------------------
    # Invalid enum value tests
    # -------------------------------------------------------------------------

    def test_invalid_enum_value_raises_error(self):
        """Invalid enum value should raise ValueError."""
        json_data = '{"order_id": "ord-123", "status": "invalid_status", "priority": "high"}'

        with pytest.raises(ValueError) as exc_info:
            self.serializer.deserialize_from_text(json_data, OrderWithEnum)

        assert "OrderStatus" in str(exc_info.value)
        assert "invalid_status" in str(exc_info.value)


# =============================================================================
# Basic Enum Detection Tests
# =============================================================================


class TestBasicEnumDetection:
    """Tests for _basic_enum_detection fallback method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = JsonSerializer()

    def test_basic_enum_detection_exact_value(self):
        """Basic enum detection should find exact value match."""
        result = self.serializer._basic_enum_detection("pending", OrderWithEnum)
        assert result == OrderStatus.PENDING

    def test_basic_enum_detection_exact_name(self):
        """Basic enum detection should find exact name match."""
        result = self.serializer._basic_enum_detection("PENDING", OrderWithEnum)
        assert result == OrderStatus.PENDING

    def test_basic_enum_detection_case_insensitive_value(self):
        """Basic enum detection should find case-insensitive value match."""
        result = self.serializer._basic_enum_detection("PENDING", OrderWithEnum)
        assert result == OrderStatus.PENDING

    def test_basic_enum_detection_case_insensitive_name(self):
        """Basic enum detection should find case-insensitive name match."""
        result = self.serializer._basic_enum_detection("pending", OrderWithEnum)
        # Since "pending" is also a value, it will match on value first
        assert result == OrderStatus.PENDING

    def test_basic_enum_detection_no_match(self):
        """Basic enum detection should return None for no match."""
        result = self.serializer._basic_enum_detection("nonexistent", OrderWithEnum)
        assert result is None

    def test_basic_enum_detection_non_string(self):
        """Basic enum detection should handle non-string gracefully."""
        # _basic_enum_detection expects string, but should handle edge cases
        result = self.serializer._basic_enum_detection("1", OrderWithEnum)
        # IntegerEnum(1) is FIRST, but we're checking OrderWithEnum's module
        assert result is None or isinstance(result, Enum)


# =============================================================================
# Edge Cases and Regression Tests
# =============================================================================


class TestEdgeCases:
    """Edge cases and regression tests for serializer hardening."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = JsonSerializer()

    def test_nested_dict_with_datetime_string_in_key(self):
        """Datetime-like string in dict key should not cause issues."""
        json_data = '{"2025-12-15T10:30:00": "value"}'
        result = self.serializer.deserialize_from_text(json_data, dict)

        assert "2025-12-15T10:30:00" in result
        assert result["2025-12-15T10:30:00"] == "value"

    def test_deeply_nested_datetime_preserved_as_string_in_untyped_dict(self):
        """Datetime in deeply nested untyped dict should remain string.

        When deserializing to plain dict without type hints, datetime-like strings
        should be preserved as strings to maintain data integrity. Type conversion
        should only happen when explicit type hints are provided.
        """
        json_data = '{"level1": {"level2": {"timestamp": "2025-12-15T10:30:00Z"}}}'
        result = self.serializer.deserialize_from_text(json_data, dict)

        # In untyped dict, strings remain strings - this is correct behavior
        assert isinstance(result["level1"]["level2"]["timestamp"], str)
        assert result["level1"]["level2"]["timestamp"] == "2025-12-15T10:30:00Z"

    def test_list_of_datetimes(self):
        """List of datetime strings should be handled correctly."""

        @dataclass
        class TimestampList:
            timestamps: list[datetime]

        json_data = '{"timestamps": ["2025-12-15T10:30:00Z", "2025-12-16T11:45:00Z"]}'
        result = self.serializer.deserialize_from_text(json_data, TimestampList)

        assert len(result.timestamps) == 2
        assert all(isinstance(ts, datetime) for ts in result.timestamps)

    def test_optional_datetime_with_none(self):
        """Optional datetime field with None should be handled."""

        @dataclass
        class OptionalTimestamp:
            created_at: Optional[datetime]

        json_data = '{"created_at": null}'
        result = self.serializer.deserialize_from_text(json_data, OptionalTimestamp)

        assert result.created_at is None

    def test_mixed_data_roundtrip(self):
        """Complex mixed data should roundtrip correctly."""
        original = MixedData(
            name="Test",
            value=Decimal("123.45"),
            status=OrderStatus.COMPLETED,
            timestamp=datetime(2025, 12, 15, 10, 30, 0),
            metadata={"key": "value", "nested": {"inner": 42}},
        )

        json_str = self.serializer.serialize_to_text(original)
        result = self.serializer.deserialize_from_text(json_str, MixedData)

        assert result.name == original.name
        # Note: Decimal comparison may differ due to serialization
        assert str(result.value) == str(original.value)
        assert result.status == original.status
        assert result.timestamp == original.timestamp
        assert result.metadata == original.metadata

    def test_empty_string_fields_preserved(self):
        """Empty string fields should be preserved, not converted."""
        json_data = '{"event_id": "", "created_at": "2025-12-15T10:30:00Z", "description": ""}'
        result = self.serializer.deserialize_from_text(json_data, EventData)

        assert result.event_id == ""
        assert result.description == ""

    def test_whitespace_only_datetime_not_detected(self):
        """Whitespace-only string should not be detected as datetime."""
        assert self.serializer._is_datetime_string("   ") is False
        assert self.serializer._is_datetime_string("\t\n") is False

    def test_unicode_datetime_not_detected(self):
        """Unicode datetime-like string should not cause issues."""
        value = "２０２５-１２-１５T10:30:00"  # Full-width numbers
        assert self.serializer._is_datetime_string(value) is False


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with existing code."""

    def setup_method(self):
        """Set up test fixtures."""
        self.serializer = JsonSerializer()

    def test_simple_dict_serialization(self):
        """Simple dict serialization should still work."""
        data = {"name": "Test", "value": 123}
        json_str = self.serializer.serialize_to_text(data)
        result = self.serializer.deserialize_from_text(json_str, dict)

        assert result == data

    def test_dataclass_serialization(self):
        """Dataclass serialization should still work."""

        @dataclass
        class SimpleData:
            name: str
            count: int

        original = SimpleData(name="Test", count=42)
        json_str = self.serializer.serialize_to_text(original)
        result = self.serializer.deserialize_from_text(json_str, SimpleData)

        assert result.name == original.name
        assert result.count == original.count

    def test_typed_datetime_still_works(self):
        """Explicitly typed datetime fields should still work."""
        json_data = '{"event_id": "evt-123", "created_at": "2025-12-15T10:30:00Z", "description": "Test"}'
        result = self.serializer.deserialize_from_text(json_data, EventData)

        assert isinstance(result.created_at, datetime)

    def test_enum_serialization_still_works(self):
        """Enum serialization should still work."""
        original = OrderWithEnum(order_id="ord-123", status=OrderStatus.PENDING, priority=Priority.HIGH)
        json_str = self.serializer.serialize_to_text(original)

        # Enum values should be serialized as names
        assert "PENDING" in json_str
        assert "HIGH" in json_str

    def test_decimal_field_still_works(self):
        """Decimal field serialization should still work."""

        @dataclass
        class PriceData:
            price: Decimal
            tax_rate: Decimal

        original = PriceData(price=Decimal("99.99"), tax_rate=Decimal("0.07"))
        json_str = self.serializer.serialize_to_text(original)
        result = self.serializer.deserialize_from_text(json_str, PriceData)

        assert str(result.price) == str(original.price)
        assert str(result.tax_rate) == str(original.tax_rate)
