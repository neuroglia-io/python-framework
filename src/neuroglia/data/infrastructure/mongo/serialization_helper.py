"""
MongoDB serialization helpers for complex type handling.

This module provides utilities for serializing and deserializing complex Python objects
to/from MongoDB documents, with support for enums, datetime objects, nested entities,
and value objects commonly used in domain-driven design patterns.
"""

import logging
import inspect
from typing import Type, Dict, Any, Optional, get_type_hints, TypeVar
from enum import Enum
from datetime import datetime, date
from decimal import Decimal
from bson import ObjectId

log = logging.getLogger(__name__)

T = TypeVar("T")


class MongoSerializationHelper:
    """
    Helper class for serialization and deserialization of MongoDB documents.
    
    This class provides static methods for converting between Python domain objects
    and MongoDB document representations, handling complex types that are commonly
    used in domain-driven design applications.
    """

    @staticmethod
    def serialize_to_dict(entity: Any) -> Any:
        """
        Converts an entity to a dictionary suitable for MongoDB storage.
        
        Handles Enum types, nested objects, datetime objects, and other special types
        commonly found in domain entities.

        Args:
            entity: The entity to convert to a dictionary

        Returns:
            A dictionary representation of the entity or the entity itself for basic types
        """
        if entity is None:
            return None

        if isinstance(entity, dict):
            return {k: MongoSerializationHelper.serialize_to_dict(v) for k, v in entity.items()}

        if isinstance(entity, list):
            return [MongoSerializationHelper.serialize_to_dict(item) for item in entity]

        if isinstance(entity, (str, int, float, bool, datetime, date)):
            return entity

        if isinstance(entity, Decimal):
            # Store decimals as strings to preserve precision
            return str(entity)

        if isinstance(entity, Enum):
            # Store enums as their string representation
            return entity.name

        if isinstance(entity, ObjectId):
            return str(entity)

        # Handle custom objects - convert to dict
        if hasattr(entity, "__dict__"):
            result = {}
            for key, value in entity.__dict__.items():
                # Skip private attributes
                if key.startswith("_"):
                    continue
                result[key] = MongoSerializationHelper.serialize_to_dict(value)
            return result

        # For any other type, convert to string as a fallback
        return str(entity)

    @staticmethod
    def deserialize_to_entity(data: Dict[str, Any], entity_type: Type[T]) -> T:
        """
        Converts a MongoDB document dictionary to an entity.
        
        Handles Enum types, nested objects, datetime objects, and other special types
        with intelligent constructor parameter mapping and type conversion.

        Args:
            data: The MongoDB document dictionary
            entity_type: The type of entity to create

        Returns:
            An instance of the entity type
        """
        if data is None:
            return None  # type: ignore

        # Clean MongoDB ID
        if "_id" in data:
            data = data.copy()
            if isinstance(data["_id"], ObjectId):
                # Convert ObjectId to string if needed
                data["_id"] = str(data["_id"])

        try:
            # Get constructor signature
            entity_init = entity_type.__init__
            sig = inspect.signature(entity_init)

            # Find required parameters
            required_params = {name: param for name, param in sig.parameters.items()
                               if param.default is param.empty and name != "self"}

            # Prepare constructor arguments
            constructor_args = {}
            kwargs = {}

            # Handle ID field
            if "id" in data and "id" not in required_params:
                stored_id = data["id"]
                data_copy = {k: v for k, v in data.items() if k != "id"}
            else:
                stored_id = None
                data_copy = data

            # Process parameters
            for param_name in required_params:
                if param_name == "kwargs":
                    continue

                if param_name in data_copy:
                    param_value = data_copy[param_name]
                    param_type = MongoSerializationHelper._get_parameter_type(entity_type, param_name)

                    # Convert enum values
                    if (param_type and
                            inspect.isclass(param_type) and
                            issubclass(param_type, Enum) and
                            isinstance(param_value, str)):
                        try:
                            constructor_args[param_name] = param_type[param_value]
                        except KeyError:
                            # Try by value if name lookup fails
                            constructor_args[param_name] = param_type(param_value)

                    # Convert decimal values
                    elif (param_type is Decimal and isinstance(param_value, str)):
                        constructor_args[param_name] = Decimal(param_value)

                    # Handle nested object conversion
                    elif (param_type and
                          not isinstance(param_type, (str, int, float, bool, datetime, date)) and
                          isinstance(param_value, dict)):
                        constructor_args[param_name] = MongoSerializationHelper.deserialize_to_entity(
                            param_value, param_type)

                    # Handle list of objects
                    elif (param_type and
                          getattr(param_type, "__origin__", None) is list and
                          isinstance(param_value, list)):
                        item_type = getattr(param_type, "__args__", [Any])[0] if hasattr(param_type, "__args__") else Any
                        if item_type != Any and not isinstance(item_type, TypeVar):
                            constructor_args[param_name] = [
                                MongoSerializationHelper.deserialize_to_entity(item, item_type)
                                if isinstance(item, dict) else item
                                for item in param_value
                            ]
                        else:
                            constructor_args[param_name] = param_value
                    else:
                        constructor_args[param_name] = param_value

            # Add non-required values to kwargs
            for k, v in data_copy.items():
                if k not in required_params and k != "id" and k != "_id":
                    kwargs[k] = v

            # Add kwargs to constructor_args
            constructor_args.update(kwargs)

            # Set the ID if available
            if stored_id is not None:
                constructor_args["id"] = stored_id

            # Create entity with all available parameters
            entity = entity_type(**constructor_args)

            return entity

        except Exception as e:
            log.error(f"Error creating entity of type {entity_type.__name__}: {e}")
            import traceback
            log.error(traceback.format_exc())

            # Return original data as fallback
            return data  # type: ignore

    @staticmethod
    def _get_parameter_type(entity_type: Type, param_name: str) -> Optional[Type]:
        """
        Get the type annotation for a parameter.
        
        Searches the entity type and its parent classes for type annotations
        for the specified parameter name.

        Args:
            entity_type: The entity class to search
            param_name: The parameter name to find the type for

        Returns:
            The type annotation if found, None otherwise
        """
        try:
            # Try to get type hints from the class
            type_hints = get_type_hints(entity_type)
            if param_name in type_hints:
                return type_hints[param_name]

            # Look for type annotations in parent classes
            for base in entity_type.__mro__[1:]:  # Skip the class itself
                if hasattr(base, "__annotations__"):
                    base_annotations = base.__annotations__
                    if param_name in base_annotations:
                        return base_annotations[param_name]
        except Exception as e:
            log.error(f"Error getting parameter type for {param_name}: {e}")

        return None