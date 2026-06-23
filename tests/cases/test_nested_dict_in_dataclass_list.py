"""
Tests for nested dict[str, Any] fields in dataclass lists.

This test suite validates the fix for the bug where nested dataclass fields
with dict[str, Any] types lose their deeply nested values during deserialization.

The bug was caused by using field.type directly instead of get_type_hints() when
deserializing dataclasses within lists.

Related issue: MotorRepository._deserialize_entity() nested dataclass deserialization
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from neuroglia.serialization.json import JsonSerializer


@dataclass
class ItemContent:
    """Content item with flexible widget configuration."""

    id: str
    order: int = 0
    widget_type: str = ""
    widget_config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "widget_type": self.widget_type,
            "widget_config": self.widget_config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ItemContent":
        return cls(
            id=data.get("id", ""),
            order=data.get("order", 0),
            widget_type=data.get("widget_type", ""),
            widget_config=data.get("widget_config", {}),
        )


@dataclass
class ConversationItem:
    """Item containing multiple content pieces."""

    id: str
    order: int = 0
    title: Optional[str] = None
    contents: list[ItemContent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "title": self.title,
            "contents": [c.to_dict() for c in self.contents],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationItem":
        return cls(
            id=data.get("id", ""),
            order=data.get("order", 0),
            title=data.get("title"),
            contents=[ItemContent.from_dict(c) for c in data.get("contents", [])],
        )


@dataclass
class Template:
    """Container with list of nested dataclasses."""

    id: str
    name: str
    items: list[ConversationItem] = field(default_factory=list)


class TestNestedDictInDataclassList:
    """Test suite for nested dict[str, Any] preservation in dataclass lists."""

    @pytest.fixture
    def serializer(self) -> JsonSerializer:
        return JsonSerializer()

    def test_nested_dict_preserved_through_serialization(self, serializer: JsonSerializer):
        """
        Nested dict[str, Any] should survive JSON serialization round-trip.

        This test verifies the bug fix where widget_config with nested dicts
        was being dropped during deserialization.
        """
        # Arrange
        original_config = {
            "format": "markdown",
            "canvas_position": {
                "col_start": 1,
                "col_span": 6,
                "row": 1,
            },
        }

        content = ItemContent(
            id="content-1",
            order=1,
            widget_type="text_display",
            widget_config=original_config,
        )

        item = ConversationItem(
            id="item-1",
            order=1,
            title="Test Item",
            contents=[content],
        )

        template = Template(
            id="template-123",
            name="Test Template",
            items=[item],
        )

        # Act
        json_text = serializer.serialize_to_text(template)
        deserialized = serializer.deserialize_from_text(json_text, Template)

        # Assert
        assert isinstance(deserialized, Template)
        assert deserialized.id == "template-123"
        assert len(deserialized.items) == 1

        deser_item = deserialized.items[0]
        assert isinstance(deser_item, ConversationItem)
        assert deser_item.id == "item-1"
        assert len(deser_item.contents) == 1

        deser_content = deser_item.contents[0]
        assert isinstance(deser_content, ItemContent)
        assert deser_content.id == "content-1"
        assert deser_content.widget_type == "text_display"

        # This was the failing assertion before the fix
        assert deser_content.widget_config == original_config
        assert deser_content.widget_config["format"] == "markdown"
        assert deser_content.widget_config["canvas_position"]["col_start"] == 1
        assert deser_content.widget_config["canvas_position"]["col_span"] == 6
        assert deser_content.widget_config["canvas_position"]["row"] == 1

    def test_deeply_nested_dict_preserved(self, serializer: JsonSerializer):
        """Test even deeper nesting levels in dict[str, Any] fields."""
        # Arrange
        deep_config = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deeply_nested",
                            "number": 42,
                        }
                    }
                }
            },
            "array_in_dict": [1, 2, {"nested_in_array": True}],
        }

        content = ItemContent(
            id="deep-content",
            order=1,
            widget_config=deep_config,
        )

        template = Template(
            id="deep-template",
            name="Deep Nesting Test",
            items=[ConversationItem(id="item", contents=[content])],
        )

        # Act
        json_text = serializer.serialize_to_text(template)
        deserialized = serializer.deserialize_from_text(json_text, Template)

        # Assert
        deser_config = deserialized.items[0].contents[0].widget_config
        assert deser_config["level1"]["level2"]["level3"]["level4"]["value"] == "deeply_nested"
        assert deser_config["level1"]["level2"]["level3"]["level4"]["number"] == 42
        assert deser_config["array_in_dict"][2]["nested_in_array"] is True

    def test_empty_dict_preserved(self, serializer: JsonSerializer):
        """Empty dict[str, Any] should remain empty, not become None."""
        # Arrange
        content = ItemContent(
            id="empty-config",
            order=1,
            widget_config={},  # Empty dict
        )

        template = Template(
            id="empty-template",
            name="Empty Config Test",
            items=[ConversationItem(id="item", contents=[content])],
        )

        # Act
        json_text = serializer.serialize_to_text(template)
        deserialized = serializer.deserialize_from_text(json_text, Template)

        # Assert
        deser_config = deserialized.items[0].contents[0].widget_config
        assert deser_config == {}
        assert isinstance(deser_config, dict)

    def test_multiple_items_with_different_configs(self, serializer: JsonSerializer):
        """Multiple items in a list should each preserve their own dict contents."""
        # Arrange
        contents = [
            ItemContent(
                id="c1",
                widget_config={"type": "text", "settings": {"bold": True}},
            ),
            ItemContent(
                id="c2",
                widget_config={"type": "image", "settings": {"width": 100}},
            ),
            ItemContent(
                id="c3",
                widget_config={"type": "chart", "data": [1, 2, 3]},
            ),
        ]

        template = Template(
            id="multi-template",
            name="Multiple Items Test",
            items=[ConversationItem(id="item", contents=contents)],
        )

        # Act
        json_text = serializer.serialize_to_text(template)
        deserialized = serializer.deserialize_from_text(json_text, Template)

        # Assert
        deser_contents = deserialized.items[0].contents
        assert len(deser_contents) == 3

        assert deser_contents[0].widget_config["type"] == "text"
        assert deser_contents[0].widget_config["settings"]["bold"] is True

        assert deser_contents[1].widget_config["type"] == "image"
        assert deser_contents[1].widget_config["settings"]["width"] == 100

        assert deser_contents[2].widget_config["type"] == "chart"
        assert deser_contents[2].widget_config["data"] == [1, 2, 3]

    def test_optional_fields_in_list_items_populated(self, serializer: JsonSerializer):
        """Optional fields in list items should be properly populated."""
        # Arrange
        template = Template(
            id="optional-test",
            name="Optional Fields Test",
            items=[
                ConversationItem(id="item-with-title", title="Has Title", contents=[]),
                ConversationItem(id="item-without-title", title=None, contents=[]),
            ],
        )

        # Act
        json_text = serializer.serialize_to_text(template)
        deserialized = serializer.deserialize_from_text(json_text, Template)

        # Assert
        assert deserialized.items[0].title == "Has Title"
        assert deserialized.items[1].title is None

    def test_list_directly_at_top_level(self, serializer: JsonSerializer):
        """Test deserializing a list of dataclasses with dict[str, Any] directly."""
        # Arrange
        contents = [
            ItemContent(id="1", widget_config={"key": "value1"}),
            ItemContent(id="2", widget_config={"key": "value2", "nested": {"a": 1}}),
        ]

        # Act
        json_text = serializer.serialize_to_text(contents)
        deserialized = serializer.deserialize_from_text(json_text, list[ItemContent])

        # Assert
        assert len(deserialized) == 2
        assert all(isinstance(c, ItemContent) for c in deserialized)
        assert deserialized[0].widget_config["key"] == "value1"
        assert deserialized[1].widget_config["nested"]["a"] == 1
