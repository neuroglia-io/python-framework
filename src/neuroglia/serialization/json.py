import json
from datetime import datetime
from enum import Enum
import typing
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.abstractions import Serializer, TextSerializer
from typing import Any, Dict, Optional, Type, Union, get_args, get_origin
from dataclasses import is_dataclass, fields


class JsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if issubclass(type(obj), Enum):
            return obj.name
        elif issubclass(type(obj), datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            filtered_dict = {
                key: value
                for key, value in obj.__dict__.items()
                if not key.startswith("_") and value is not None
            }
            return filtered_dict
        try:
            return super().default(obj)
        except Exception:
            return str(obj)


class JsonSerializer(TextSerializer):
    """Represents the service used to serialize/deserialize to/from JSON"""

    def serialize(self, value: Any) -> bytearray:
        text = self.serialize_to_text(value)
        if text is None:
            return None
        return text.encode()

    def serialize_to_text(self, value: Any) -> str:
        return json.dumps(value, cls=JsonEncoder)

    def deserialize(self, input: bytearray, expected_type: Any | None) -> Any:
        return self.deserialize_from_text(input.decode(), expected_type)

    def deserialize_from_text(
        self, input: str, expected_type: Optional[Type] = None
    ) -> Any:
        value = json.loads(input)
        if expected_type is None or not isinstance(value, dict):
            return value
        elif expected_type == dict:
            return dict(value)
        fields = {}
        for base_type in reversed(expected_type.__mro__):
            if not hasattr(base_type, "__annotations__"):
                continue
            for key, field_type in base_type.__annotations__.items():
                if key in value:
                    fields[key] = self._deserialize_nested(value[key], field_type)
        value = object.__new__(expected_type)
        value.__dict__ = fields
        return value

    def _deserialize_nested(self, value: Any, expected_type: Type) -> Any:
        """Recursively deserializes a nested object. Support native types (str, int, float, bool) as well as Generic Types that also include subtypes (typing.Dict, typing.List)."""

        # Handle None for Optional types
        if value is None:
            return None

        origin_type = get_origin(expected_type)
        if origin_type is not None:
            # This is a generic type (e.g., Optional[SomeType], List[SomeType])
            type_args = get_args(expected_type)
            if origin_type is Union and type(None) in type_args:
                # This is an Optional type
                non_optional_type = next(t for t in type_args if t is not type(None))
                return self._deserialize_nested(value, non_optional_type)

            elif origin_type in (list, typing.List):
                # Handle List deserialization
                if len(type_args) > 0:
                    # List with type hints (e.g. typing.List[str])
                    item_type = type_args[0]
                else:
                    item_type = type(value[0]) if value else object

                # Deserialize each item in the list
                return [self._deserialize_nested(v, item_type) for v in value]

            elif origin_type is dict:
                # Handle Dict deserialization
                if len(type_args) > 0:
                    # Dictionary with type hints (e.g. typing.Dict[str, int])
                    key_type, val_type = type_args
                    return {
                        self._deserialize_nested(k, key_type): self._deserialize_nested(
                            v, val_type
                        )
                        for k, v in value.items()
                    }
                else:
                    # Dictionary without type hints, use the actual type of each value
                    return {
                        k: self._deserialize_nested(v, type(v))
                        for k, v in value.items()
                    }

        if isinstance(value, dict):
            # Handle Dataclass deserialization
            if is_dataclass(expected_type):
                field_dict = {}
                for field in fields(expected_type):
                    if field.name in value:
                        field_value = self._deserialize_nested(
                            value[field.name], field.type
                        )
                        field_dict[field.name] = field_value
                value = object.__new__(expected_type)
                value.__dict__ = field_dict
                return value

            # If the expected type is a plain dict, we need to deserialize each value in the dict.
            if hasattr(expected_type, "__args__") and expected_type.__args__:
                # Dictionary with type hints (e.g. typing.Dict[str, int])
                key_type, val_type = expected_type.__args__
                return {
                    self._deserialize_nested(k, key_type): self._deserialize_nested(
                        v, val_type
                    )
                    for k, v in value.items()
                }
            else:
                # Dictionary without type hints, use the actual type of each value
                return {
                    k: self._deserialize_nested(v, type(v)) for k, v in value.items()
                }

        elif isinstance(value, list):
            # List with type hints (e.g. typing.List[str])
            if hasattr(expected_type, "__args__") and expected_type.__args__:
                # Extract the actual type from the generic alias
                item_type = expected_type.__args__[0]
                if hasattr(item_type, "__origin__"):  # Check if it's a generic alias
                    if len(item_type.__args__) == 1:
                        item_type = item_type.__args__[0]  # Get the actual type
                    else:
                        item_type = item_type.__origin__

            else:
                item_type = type(value[0]) if value else object

            # Deserialize each item in the list
            items = [self._deserialize_nested(v, item_type) for v in value]
            values = []

            for item in items:
                if isinstance(item, (int, str, float, bool)):
                    # For simple types, the deserialized item is already in the correct form
                    values.append(item)
                elif isinstance(item_type, type):
                    # For complex types or custom classes, instantiate using __new__
                    new_item = object.__new__(item_type)
                    if hasattr(new_item, "__dict__"):
                        # If the new item has a __dict__, we can directly update it
                        new_item.__dict__.update(item)
                    elif isinstance(item, dict):
                        new_item = item
                    values.append(new_item)
                else:
                    # If item_type is not a class type, just use the item as is
                    values.append(item)
            return values

        elif isinstance(value, str) and expected_type == datetime:
            return datetime.fromisoformat(value)

        elif (
            hasattr(expected_type, "__bases__")
            and expected_type.__bases__
            and issubclass(expected_type, Enum)
        ):
            # Handle Enum deserialization
            for enum_member in expected_type:
                if enum_member.value == value:
                    return enum_member
            raise ValueError(
                f"Invalid enum value for {
                             expected_type.__name__}: {value}"
            )

        else:
            # Return the value as is for types that do not require deserialization
            return value

    def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
        """Configures the specified application builder to use the JsonSerializer"""
        builder.services.add_singleton(JsonSerializer)
        builder.services.add_singleton(
            Serializer,
            implementation_factory=lambda provider: provider.get_required_service(
                JsonSerializer
            ),
        )
        builder.services.add_singleton(
            TextSerializer,
            implementation_factory=lambda provider: provider.get_required_service(
                JsonSerializer
            ),
        )
        return builder
