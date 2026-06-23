"""
Tests for Pydantic BaseModel deserialization in JsonSerializer.

This test suite validates the fix for the bug where Pydantic BaseModel instances
were created without proper initialization (missing __pydantic_private__ and other
internal attributes).

The bug was caused by using object.__new__() and directly assigning to __dict__,
which bypasses Pydantic's initialization.

Related issue: MotorRepository._deserialize_entity() Pydantic model deserialization
"""

from dataclasses import dataclass, field
from typing import Optional

import pytest
from pydantic import BaseModel, ConfigDict, Field

from neuroglia.serialization.json import JsonSerializer


class CanvasPosition(BaseModel):
    """Canvas grid positioning for 2D layout mode."""

    model_config = ConfigDict(populate_by_name=True)

    col_start: int = Field(default=1, ge=1, le=12)
    col_span: int = Field(default=4, ge=1, le=12)
    row: int = Field(default=1, ge=1)


class WidgetConfig(BaseModel):
    """Widget configuration with canvas positioning."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    canvas_position: Optional[CanvasPosition] = None
    format: Optional[str] = None


@dataclass
class ItemContent:
    """Content item with Pydantic model field."""

    id: str
    order: int = 0
    widget_type: str = ""
    widget_config: WidgetConfig = field(default_factory=WidgetConfig)


@dataclass
class Container:
    """Container with list of nested items."""

    id: str
    name: str
    items: list[ItemContent] = field(default_factory=list)


class TestPydanticModelDeserialization:
    """Test suite for Pydantic BaseModel deserialization."""

    @pytest.fixture
    def serializer(self) -> JsonSerializer:
        return JsonSerializer()

    def test_simple_pydantic_model_deserialization(self, serializer: JsonSerializer):
        """Simple Pydantic model should be properly initialized."""
        # Arrange
        position = CanvasPosition(col_start=1, col_span=6, row=2)

        # Act
        json_text = serializer.serialize_to_text(position)
        deserialized = serializer.deserialize_from_text(json_text, CanvasPosition)

        # Assert
        assert isinstance(deserialized, CanvasPosition)
        assert deserialized.col_start == 1
        assert deserialized.col_span == 6
        assert deserialized.row == 2
        # Verify Pydantic internals are properly initialized
        assert hasattr(deserialized, "__pydantic_private__")
        assert hasattr(deserialized, "model_fields")

    def test_nested_pydantic_models(self, serializer: JsonSerializer):
        """Nested Pydantic models should be properly initialized."""
        # Arrange
        config = WidgetConfig(
            format="markdown",
            canvas_position=CanvasPosition(col_start=1, col_span=6, row=1),
        )

        # Act
        json_text = serializer.serialize_to_text(config)
        deserialized = serializer.deserialize_from_text(json_text, WidgetConfig)

        # Assert
        assert isinstance(deserialized, WidgetConfig)
        assert deserialized.format == "markdown"
        assert deserialized.canvas_position is not None
        assert isinstance(deserialized.canvas_position, CanvasPosition)
        assert deserialized.canvas_position.col_start == 1
        assert deserialized.canvas_position.col_span == 6
        # Verify Pydantic internals on nested model
        assert hasattr(deserialized.canvas_position, "__pydantic_private__")

    def test_pydantic_model_in_dataclass(self, serializer: JsonSerializer):
        """Pydantic model as field in dataclass should be properly initialized."""
        # Arrange
        content = ItemContent(
            id="content-1",
            order=1,
            widget_type="text_display",
            widget_config=WidgetConfig(
                format="markdown",
                canvas_position=CanvasPosition(col_start=1, col_span=6, row=1),
            ),
        )

        # Act
        json_text = serializer.serialize_to_text(content)
        deserialized = serializer.deserialize_from_text(json_text, ItemContent)

        # Assert
        assert isinstance(deserialized, ItemContent)
        assert deserialized.id == "content-1"
        assert isinstance(deserialized.widget_config, WidgetConfig)
        assert deserialized.widget_config.format == "markdown"
        assert isinstance(deserialized.widget_config.canvas_position, CanvasPosition)
        assert deserialized.widget_config.canvas_position.col_start == 1
        # Verify Pydantic internals
        assert hasattr(deserialized.widget_config, "__pydantic_private__")
        assert hasattr(deserialized.widget_config.canvas_position, "__pydantic_private__")

    def test_pydantic_model_in_list_within_dataclass(self, serializer: JsonSerializer):
        """Pydantic models in nested dataclass lists should be properly initialized."""
        # Arrange
        container = Container(
            id="container-1",
            name="Test Container",
            items=[
                ItemContent(
                    id="content-1",
                    widget_config=WidgetConfig(
                        format="markdown",
                        canvas_position=CanvasPosition(col_start=1, col_span=6, row=1),
                    ),
                ),
                ItemContent(
                    id="content-2",
                    widget_config=WidgetConfig(
                        format="html",
                        canvas_position=CanvasPosition(col_start=7, col_span=6, row=1),
                    ),
                ),
            ],
        )

        # Act
        json_text = serializer.serialize_to_text(container)
        deserialized = serializer.deserialize_from_text(json_text, Container)

        # Assert
        assert isinstance(deserialized, Container)
        assert len(deserialized.items) == 2

        for item in deserialized.items:
            assert isinstance(item, ItemContent)
            assert isinstance(item.widget_config, WidgetConfig)
            assert hasattr(item.widget_config, "__pydantic_private__")
            assert isinstance(item.widget_config.canvas_position, CanvasPosition)
            assert hasattr(item.widget_config.canvas_position, "__pydantic_private__")

        # Verify specific values
        assert deserialized.items[0].widget_config.format == "markdown"
        assert deserialized.items[0].widget_config.canvas_position.col_start == 1
        assert deserialized.items[1].widget_config.format == "html"
        assert deserialized.items[1].widget_config.canvas_position.col_start == 7

    def test_list_of_pydantic_models(self, serializer: JsonSerializer):
        """Direct list of Pydantic models should be properly initialized."""
        # Arrange
        positions = [
            CanvasPosition(col_start=1, col_span=4, row=1),
            CanvasPosition(col_start=5, col_span=4, row=1),
            CanvasPosition(col_start=9, col_span=4, row=1),
        ]

        # Act
        json_text = serializer.serialize_to_text(positions)
        deserialized = serializer.deserialize_from_text(json_text, list[CanvasPosition])

        # Assert
        assert len(deserialized) == 3
        for i, pos in enumerate(deserialized):
            assert isinstance(pos, CanvasPosition)
            assert hasattr(pos, "__pydantic_private__")
            assert pos.col_start == 1 + (i * 4)

    def test_pydantic_model_with_extra_fields(self, serializer: JsonSerializer):
        """Pydantic model with extra='allow' should preserve extra fields."""
        # Arrange - WidgetConfig has extra='allow'
        config = WidgetConfig(format="markdown")
        # Manually add extra field for testing
        config_dict = config.model_dump()
        config_dict["custom_field"] = "custom_value"
        config_dict["nested_extra"] = {"key": "value"}

        # Act
        json_text = serializer.serialize_to_text(config_dict)
        # Note: We're deserializing a dict that has extra fields
        deserialized = serializer.deserialize_from_text(json_text, WidgetConfig)

        # Assert
        assert isinstance(deserialized, WidgetConfig)
        assert deserialized.format == "markdown"
        # Extra fields should be preserved with extra='allow'
        assert deserialized.custom_field == "custom_value"  # type: ignore[attr-defined]
        assert deserialized.nested_extra == {"key": "value"}  # type: ignore[attr-defined]

    def test_pydantic_model_with_validators(self, serializer: JsonSerializer):
        """Pydantic model validators should be applied during deserialization."""

        class ValidatedModel(BaseModel):
            value: int = Field(ge=0, le=100)
            name: str = Field(min_length=1)

        # Arrange
        model = ValidatedModel(value=50, name="test")

        # Act
        json_text = serializer.serialize_to_text(model)
        deserialized = serializer.deserialize_from_text(json_text, ValidatedModel)

        # Assert
        assert isinstance(deserialized, ValidatedModel)
        assert deserialized.value == 50
        assert deserialized.name == "test"
        assert hasattr(deserialized, "__pydantic_private__")

    def test_pydantic_model_with_none_optional_field(self, serializer: JsonSerializer):
        """Pydantic model with None optional field should be properly handled."""
        # Arrange
        config = WidgetConfig(format=None, canvas_position=None)

        # Act
        json_text = serializer.serialize_to_text(config)
        deserialized = serializer.deserialize_from_text(json_text, WidgetConfig)

        # Assert
        assert isinstance(deserialized, WidgetConfig)
        assert deserialized.format is None
        assert deserialized.canvas_position is None
        assert hasattr(deserialized, "__pydantic_private__")

    def test_is_pydantic_model_detection(self, serializer: JsonSerializer):
        """_is_pydantic_model should correctly identify Pydantic models."""
        # Pydantic models should return True
        assert serializer._is_pydantic_model(CanvasPosition) is True
        assert serializer._is_pydantic_model(WidgetConfig) is True

        # Non-Pydantic types should return False
        assert serializer._is_pydantic_model(dict) is False
        assert serializer._is_pydantic_model(list) is False
        assert serializer._is_pydantic_model(str) is False
        assert serializer._is_pydantic_model(ItemContent) is False  # dataclass

        # Non-types should return False
        assert serializer._is_pydantic_model("string") is False
        assert serializer._is_pydantic_model(123) is False
        assert serializer._is_pydantic_model(None) is False
