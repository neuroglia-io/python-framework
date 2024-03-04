from abc import ABC, abstractmethod
from typing import Any, Optional, Type


class Serializer(ABC):
    ''' Represents the base class for all serializers '''

    @abstractmethod
    def serialize(self, value: Any) -> bytearray:
        ''' Serializes the specified value '''
        raise NotImplementedError()

    @abstractmethod
    def deserialize(self, input: bytearray, expected_type: Optional[Type]) -> Any:
        ''' Deserializes the specified input into a new value of the specified type, if any '''
        raise NotImplementedError()


class TextSerializer(Serializer, ABC):
    ''' Represents the base class for all text serializers '''

    @abstractmethod
    def serialize_to_text(self, value: Any) -> str:
        ''' Serializes the specified value to text '''
        raise NotImplementedError()

    @abstractmethod
    def deserialize_from_text(self, input: str, expected_type: Optional[Type] = None) -> Any:
        ''' Deserializes the specified input into a new value of the specified type, if any '''
        raise NotImplementedError()
