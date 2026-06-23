"""
CamelCase model utilities for Pydantic models.

This module provides a CamelModel base class that automatically handles
camelCase serialization and deserialization for Pydantic models, making
it easy to work with APIs that expect camelCase field names.
"""

from typing import Any, Optional

try:
    from pydantic import BaseModel, ConfigDict

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object  # Fallback for type hints
    ConfigDict = dict

from neuroglia.utils.case_conversion import to_camel_case


class CamelModel(BaseModel if PYDANTIC_AVAILABLE else object):
    """
    A Pydantic BaseModel with automatic camelCase aliases.

    Automatically converts snake_case field names to camelCase aliases
    for JSON serialization, enabling seamless API compatibility with
    JavaScript/TypeScript frontends.

    For detailed information about case conversion and API compatibility, see:
    https://bvandewe.github.io/pyneuro/features/case-conversion-utilities/

    This model automatically converts snake_case field names to camelCase
    for JSON serialization while maintaining snake_case field names in Python.
    It also supports deserialization from both camelCase and snake_case formats.

    Examples:
        >>> class UserModel(CamelModel):
        ...     first_name: str
        ...     last_name: str
        ...     email_address: str
        ...
        >>> user = UserModel(first_name="John", last_name="Doe", email_address="john@example.com")
        >>> user.model_dump_json()
        '{"firstName":"John","lastName":"Doe","emailAddress":"john@example.com"}'
        >>>
        >>> # Can also accept camelCase input
        >>> user2 = UserModel.model_validate({
        ...     "firstName": "Jane",
        ...     "lastName": "Smith",
        ...     "emailAddress": "jane@example.com"
        ... })
        >>> user2.first_name
        'Jane'
    """

    if PYDANTIC_AVAILABLE:
        model_config = ConfigDict(
            alias_generator=to_camel_case,
            populate_by_name=True,  # Allow both camelCase and snake_case during deserialization
            from_attributes=True,  # Allow creation from object attributes
            validate_assignment=True,  # Validate on assignment
        )

    def to_camel_case_dict(self, **kwargs) -> dict[str, Any]:
        """
        Convert model to dictionary with camelCase keys.

        Args:
            **kwargs: Additional arguments passed to model_dump()

        Returns:
            Dictionary representation with camelCase keys
        """
        if not PYDANTIC_AVAILABLE:
            raise RuntimeError("Pydantic is required for CamelModel functionality")

        return self.model_dump(by_alias=True, **kwargs)

    def to_snake_case_dict(self, **kwargs) -> dict[str, Any]:
        """
        Convert model to dictionary with snake_case keys.

        Args:
            **kwargs: Additional arguments passed to model_dump()

        Returns:
            Dictionary representation with snake_case keys
        """
        if not PYDANTIC_AVAILABLE:
            raise RuntimeError("Pydantic is required for CamelModel functionality")

        return self.model_dump(by_alias=False, **kwargs)

    @classmethod
    def from_camel_case_dict(cls, data: dict[str, Any]) -> "CamelModel":
        """
        Create model instance from dictionary with camelCase keys.

        Args:
            data: Dictionary with camelCase keys

        Returns:
            Model instance
        """
        if not PYDANTIC_AVAILABLE:
            raise RuntimeError("Pydantic is required for CamelModel functionality")

        return cls.model_validate(data)

    @classmethod
    def from_snake_case_dict(cls, data: dict[str, Any]) -> "CamelModel":
        """
        Create model instance from dictionary with snake_case keys.

        Args:
            data: Dictionary with snake_case keys

        Returns:
            Model instance
        """
        if not PYDANTIC_AVAILABLE:
            raise RuntimeError("Pydantic is required for CamelModel functionality")

        return cls.model_validate(data)


def create_camel_model(model_name: str, fields: dict[str, Any], base_class: Optional[type] = None) -> type:
    """
    Dynamically create a CamelModel class with specified fields.

    Args:
        model_name: Name for the new model class
        fields: Dictionary of field names and their types/defaults
        base_class: Optional base class (defaults to CamelModel)

    Returns:
        New CamelModel class

    Examples:
        >>> UserModel = create_camel_model("UserModel", {
        ...     "first_name": str,
        ...     "last_name": str,
        ...     "age": int
        ... })
        >>> user = UserModel(first_name="John", last_name="Doe", age=30)
    """
    if not PYDANTIC_AVAILABLE:
        raise RuntimeError("Pydantic is required for create_camel_model functionality")

    if base_class is None:
        base_class = CamelModel

    # Create the new class dynamically
    new_class = type(
        model_name,
        (base_class,),
        {
            "__annotations__": fields,
            "__module__": __name__,
        },
    )

    return new_class


# Utility functions for working with existing models
def add_camel_case_aliases(model_class: type) -> type:
    """
    Add camelCase aliases to an existing Pydantic model class.

    Args:
        model_class: Existing Pydantic model class

    Returns:
        New model class with camelCase aliases (does not modify original)
    """
    if not PYDANTIC_AVAILABLE:
        raise RuntimeError("Pydantic is required for add_camel_case_aliases functionality")

    # Create a new class with camelCase configuration
    # We need to create a subclass to avoid modifying the original
    class_name = f"{model_class.__name__}WithCamelCase"

    # Get the original annotations
    annotations = getattr(model_class, "__annotations__", {})

    # Create new class with CamelModel as base and original annotations
    new_class = type(
        class_name,
        (CamelModel,),
        {
            "__annotations__": annotations,
            "__module__": model_class.__module__,
        },
    )

    # Copy any default values from the original class
    for field_name in annotations:
        if hasattr(model_class, field_name):
            default_value = getattr(model_class, field_name)
            setattr(new_class, field_name, default_value)

    return new_class
