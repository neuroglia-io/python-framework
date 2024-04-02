from enum import Enum
import json
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.abstractions import Serializer, TextSerializer
from typing import Any, Optional, Type


class JsonEncoder(json.JSONEncoder):
    
    def default(self, obj):
        if issubclass(type(obj), Enum): return obj.name
        elif hasattr(obj, '__dict__'):
            filtered_dict = {key: value for key, value in obj.__dict__.items() if not key.startswith('_') and value is not None}
            return filtered_dict
        try: return super().default(obj)
        except Exception: return str(obj)


class JsonSerializer(TextSerializer):
    ''' Represents the service used to serialize/deserialize to/from JSON '''    

    def serialize(self, value: Any) -> bytearray:
        text = self.serialize_to_text(value)
        if text is None : return None
        return text.encode()

    def serialize_to_text(self, value : Any) -> str:
        return json.dumps(value, cls=JsonEncoder)

    def deserialize(self, input: bytearray, expected_type: Any | None) -> Any:
        return self.deserialize_from_text(input.decode(), expected_type)

    def deserialize_from_text(self, input: str, expected_type : Optional[Type] = None) -> Any:
        value = json.loads(input)
        if expected_type is None or not isinstance(value, dict): return value
        elif expected_type == dict: return dict(value)
        fields = {}
        for base_type in reversed(expected_type.__mro__):
            if not hasattr(base_type, "__annotations__"): continue
            for key, field_type in base_type.__annotations__.items():
                if key in value:
                    fields[key] = self._deserialize_nested(value[key], field_type)
        value = object.__new__(expected_type)
        value.__dict__ = fields
        return value

    def _deserialize_nested(self, value: Any, expected_type: Type) -> Any:
        ''' Deserializes a nested object '''
        if isinstance(value, dict):
            fields = {}
            for base_type in reversed(expected_type.__mro__):
                if not hasattr(base_type, "__annotations__"): continue
                for key, field_type in base_type.__annotations__.items():
                    if key in value:
                        fields[key] = self._deserialize_nested(value[key], field_type)
            value = object.__new__(expected_type)
            value.__dict__ = fields
            return value
        else: return value
        
    def configure(builder : ApplicationBuilderBase) -> ApplicationBuilderBase:
        ''' Configures the specified application builder to use the JsonSerializer '''
        builder.services.add_singleton(JsonSerializer)
        builder.services.add_singleton(Serializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        builder.services.add_singleton(TextSerializer, implementation_factory=lambda provider: provider.get_required_service(JsonSerializer))
        return builder