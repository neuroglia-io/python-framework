import json
from datetime import datetime
from enum import Enum
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
        elif hasattr(obj, '__dict__'):
            filtered_dict = {key: value for key, value in obj.__dict__.items() if not key.startswith('_') and value is not None}
            return filtered_dict
        try:
            return super().default(obj)
        except Exception:
            return str(obj)


class JsonSerializer(TextSerializer):
    ''' Represents the service used to serialize/deserialize to/from JSON '''    

    def serialize(self, value: Any) -> bytearray:
        text = self.serialize_to_text(value)
        if text is None:
            return None
        return text.encode()

    def serialize_to_text(self, value: Any) -> str:
        return json.dumps(value, cls=JsonEncoder)

    def deserialize(self, input: bytearray, expected_type: Any | None) -> Any:
        return self.deserialize_from_text(input.decode(), expected_type)

    def deserialize_from_text(self, input: str, expected_type: Optional[Type] = None) -> Any:
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
        ''' Deserializes a nested object '''
        if value is None:
            # Handle None for Optional types
            return None

        origin_type = get_origin(expected_type)
        if origin_type is not None:
            # This is a generic type (e.g., Optional[SomeType], List[SomeType])
            type_args = get_args(expected_type)
            if origin_type is Union and type(None) in type_args:
                # This is an Optional type
                non_optional_type = next(t for t in type_args if t is not type(None))
                return self._deserialize_nested(value, non_optional_type)
            # Add more handling for other generic types like List, Dict, etc. if needed

        if isinstance(value, dict):
            # Handle dict deserialization
            if is_dataclass(expected_type):
                field_dict = {}
                for field in fields(expected_type):
                    if field.name in value:
                        field_value = self._deserialize_nested(value[field.name], field.type)
                        field_dict[field.name] = field_value
                value = object.__new__(expected_type)
                value.__dict__ = field_dict
                return value

            # If the expected type is a plain dict, we need to deserialize each value in the dict.
            if hasattr(expected_type, '__args__') and expected_type.__args__:
                # Dictionary with type hints
                key_type, val_type = expected_type.__args__
                return {self._deserialize_nested(k, key_type): self._deserialize_nested(v, val_type) for k, v in value.items()}
            else:
                # Dictionary without type hints, use the actual type of each value
                return {k: self._deserialize_nested(v, type(v)) for k, v in value.items()}

        elif isinstance(value, str) and expected_type == datetime:
            return datetime.fromisoformat(value)

        elif hasattr(expected_type, '__bases__') and expected_type.__bases__ and issubclass(expected_type, Enum):
            # Handle Enum deserialization
            for enum_member in expected_type:
                if enum_member.value == value:
                    return enum_member
            raise ValueError(f"Invalid enum value for {expected_type.__name__}: {value}")

        else:
            # Return the value as is for types that do not require deserialization
            return value

    def configure(builder : ApplicationBuilderBase) -> ApplicationBuilderBase:
        ''' Configures the specified application builder to use the JsonSerializer '''
        builder.services.add_singleton(JsonSerializer)
        builder.services.add_singleton(Serializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        builder.services.add_singleton(TextSerializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        return builder
