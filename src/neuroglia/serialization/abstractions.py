from abc import ABC, abstractmethod
from typing import Any, Optional


class Serializer(ABC):
    """
    Represents the abstraction for binary serialization services in the framework.

    This abstraction defines the contract for converting Python objects to and from
    binary representations, enabling data persistence, network communication, and
    inter-service messaging with type safety and automatic conversion handling.

    Examples:
        ```python
        class BinarySerializer(Serializer):
            def serialize(self, value: Any) -> bytearray:
                # Convert object to binary format
                return pickle.dumps(value)

            def deserialize(self, input: bytearray, expected_type: Optional[Type]) -> Any:
                # Convert binary back to object
                obj = pickle.loads(input)
                return self._convert_to_type(obj, expected_type)

        # Usage
        serializer = provider.get_service(Serializer)

        # Serialize
        user = User("John", "john@example.com")
        binary_data = serializer.serialize(user)

        # Deserialize
        restored_user = serializer.deserialize(binary_data, User)
        assert restored_user.name == "John"
        ```

    See Also:
        - Serialization Guide: https://bvandewe.github.io/pyneuro/features/serialization/
        - Type Handling: https://bvandewe.github.io/pyneuro/patterns/
    """

    @abstractmethod
    def serialize(self, value: Any) -> bytearray:
        """
        Serializes a Python object into a binary representation.

        Args:
            value (Any): The object to serialize

        Returns:
            bytearray: Binary representation of the object
        """
        raise NotImplementedError()

    @abstractmethod
    def deserialize(self, input: bytearray, expected_type: Optional[type]) -> Any:
        """
        Deserializes binary data back into a Python object with optional type conversion.

        Args:
            input (bytearray): Binary data to deserialize
            expected_type (Optional[Type]): Target type for conversion (enables type safety)

        Returns:
            Any: Deserialized Python object, optionally converted to expected_type
        """
        raise NotImplementedError()


class TextSerializer(Serializer, ABC):
    """
    Represents the abstraction for text-based serialization services with human-readable output.

    This abstraction extends binary serialization to provide text-based formats like JSON, XML,
    YAML, or CSV, enabling human-readable data exchange, configuration files, API responses,
    and debugging-friendly data representations.

    Examples:
        ```python
        class JsonTextSerializer(TextSerializer):
            def serialize_to_text(self, value: Any) -> str:
                return json.dumps(value, cls=CustomEncoder)

            def deserialize_from_text(self, input: str, expected_type: Optional[Type] = None) -> Any:
                data = json.loads(input)
                return self._convert_to_type(data, expected_type)

            def serialize(self, value: Any) -> bytearray:
                return self.serialize_to_text(value).encode('utf-8')

            def deserialize(self, input: bytearray, expected_type: Optional[Type]) -> Any:
                text = input.decode('utf-8')
                return self.deserialize_from_text(text, expected_type)

        # Usage scenarios
        serializer = provider.get_service(TextSerializer)

        # Configuration serialization
        config = AppConfiguration(api_key="123", timeout=30)
        config_json = serializer.serialize_to_text(config)
        # Output: '{"api_key": "123", "timeout": 30}'

        # API response serialization
        users = [User("Alice"), User("Bob")]
        response_text = serializer.serialize_to_text(users)

        # Type-safe deserialization
        user_data = '{"name": "Charlie", "email": "charlie@example.com"}'
        user = serializer.deserialize_from_text(user_data, User)
        ```

    See Also:
        - JSON Serialization: https://bvandewe.github.io/pyneuro/features/serialization/
        - API Response Handling: https://bvandewe.github.io/pyneuro/features/mvc-controllers/
    """

    @abstractmethod
    def serialize_to_text(self, value: Any) -> str:
        """
        Serializes a Python object into a human-readable text representation.

        Args:
            value (Any): The object to serialize

        Returns:
            str: Text representation of the object (JSON, XML, YAML, etc.)
        """
        raise NotImplementedError()

    @abstractmethod
    def deserialize_from_text(self, input: str, expected_type: Optional[type] = None) -> Any:
        """
        Deserializes text data back into a Python object with optional type conversion.

        Args:
            input (str): Text data to deserialize
            expected_type (Optional[Type]): Target type for conversion and validation

        Returns:
            Any: Deserialized Python object, optionally converted to expected_type
        """
        raise NotImplementedError()
