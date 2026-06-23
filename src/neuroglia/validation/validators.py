"""Property and entity validators for the Neuroglia framework.

This module provides a comprehensive set of validators for common validation
scenarios, including property validators, entity validators, and composite
validators that can be combined for complex validation logic.
"""

from typing import Any, Callable, List, Optional, TypeVar, Dict, Union, Type, Generic
from abc import ABC, abstractmethod
import re
from .exceptions import ValidationException
from .business_rules import ValidationResult

T = TypeVar("T")


class ValidatorBase(ABC):
    """Abstract base class for all validators.

    Validators provide a standardized way to validate data with
    detailed error reporting and composability.
    """

    def __init__(self, message: Optional[str] = None):
        self.message = message

    @abstractmethod
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Validate a value and return detailed results."""
        pass

    def is_valid(self, value: Any) -> bool:
        """Check if a value is valid (convenience method)."""
        return self.validate(value).is_valid


class PropertyValidator(ValidatorBase):
    """Validator for individual property values.

    This validator applies a predicate function to validate individual
    property values with detailed error reporting.
    """

    def __init__(
        self,
        predicate: Callable[[Any], bool],
        message: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(message)
        self.predicate = predicate
        self.error_code = error_code

    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Validate the value against the predicate."""
        result = ValidationResult([])

        if not self.predicate(value):
            message = self.message or f"Validation failed for value: {value}"
            result.add_error(message=message, field=field_name, code=self.error_code)

        return result


class EntityValidator(ValidatorBase, Generic[T]):
    """Validator for complete entities or complex objects.

    This validator can validate multiple properties of an entity
    and apply complex validation logic across properties.
    """

    def __init__(self, entity_type: Type[T], message: Optional[str] = None):
        super().__init__(message)
        self.entity_type = entity_type
        self.property_validators: Dict[str, List[ValidatorBase]] = {}
        self.entity_validators: List[Callable[[T], ValidationResult]] = []

    def add_property_validator(
        self, property_name: str, validator: ValidatorBase
    ) -> "EntityValidator[T]":
        """Add a validator for a specific property (fluent interface)."""
        if property_name not in self.property_validators:
            self.property_validators[property_name] = []
        self.property_validators[property_name].append(validator)
        return self

    def add_entity_validator(
        self, validator: Callable[[T], ValidationResult]
    ) -> "EntityValidator[T]":
        """Add an entity-level validator (fluent interface)."""
        self.entity_validators.append(validator)
        return self

    def validate(self, entity: T, field_name: Optional[str] = None) -> ValidationResult:
        """Validate the entire entity."""
        result = ValidationResult([])

        # Validate individual properties
        for prop_name, validators in self.property_validators.items():
            try:
                prop_value = getattr(entity, prop_name)
                for validator in validators:
                    prop_result = validator.validate(prop_value, prop_name)
                    result = result.combine(prop_result)
            except AttributeError:
                result.add_error(
                    message=f"Property '{prop_name}' not found on entity",
                    field=prop_name,
                    code="missing_property",
                )

        # Validate entity-level rules
        for entity_validator in self.entity_validators:
            entity_result = entity_validator(entity)
            result = result.combine(entity_result)

        return result


class CompositeValidator(ValidatorBase):
    """Validator that combines multiple validators with logical operators.

    Supports AND and OR operations on multiple validators.
    """

    def __init__(
        self, validators: List[ValidatorBase], operator: str = "AND", message: Optional[str] = None
    ):
        super().__init__(message)
        self.validators = validators
        self.operator = operator.upper()

        if self.operator not in ["AND", "OR"]:
            raise ValueError("Operator must be 'AND' or 'OR'")

    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Apply logical operator to all contained validators."""
        results = [validator.validate(value, field_name) for validator in self.validators]

        if self.operator == "AND":
            # For AND, combine all errors
            combined = ValidationResult([])
            for result in results:
                combined = combined.combine(result)
            return combined
        else:  # OR
            # For OR, return success if any validator passed
            if any(result.is_valid for result in results):
                return ValidationResult([])

            # All validators failed, combine all errors
            combined = ValidationResult([])
            for result in results:
                combined = combined.combine(result)
            return combined


# Common validator factories


def required(message: Optional[str] = None) -> PropertyValidator:
    """Create a validator that ensures a value is not None or empty."""

    def is_required(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if hasattr(value, "__len__") and len(value) == 0:
            return False
        return True

    return PropertyValidator(
        predicate=is_required, message=message or "Value is required", error_code="required"
    )


def min_length(min_len: int, message: Optional[str] = None) -> PropertyValidator:
    """Create a validator that ensures a value has minimum length."""

    def check_min_length(value: Any) -> bool:
        if value is None:
            return False
        if hasattr(value, "__len__"):
            return len(value) >= min_len
        return False

    return PropertyValidator(
        predicate=check_min_length,
        message=message or f"Value must be at least {min_len} characters long",
        error_code="min_length",
    )


def max_length(max_len: int, message: Optional[str] = None) -> PropertyValidator:
    """Create a validator that ensures a value doesn't exceed maximum length."""

    def check_max_length(value: Any) -> bool:
        if value is None:
            return True  # None is valid for max length
        if hasattr(value, "__len__"):
            return len(value) <= max_len
        return True

    return PropertyValidator(
        predicate=check_max_length,
        message=message or f"Value must not exceed {max_len} characters",
        error_code="max_length",
    )


def email_format(message: Optional[str] = None) -> PropertyValidator:
    """Create a validator that ensures a value is a valid email format."""
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def is_valid_email(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(email_pattern.match(value))

    return PropertyValidator(
        predicate=is_valid_email,
        message=message or "Invalid email format",
        error_code="invalid_email",
    )


def numeric_range(
    min_val: Optional[Union[int, float]] = None,
    max_val: Optional[Union[int, float]] = None,
    message: Optional[str] = None,
) -> PropertyValidator:
    """Create a validator that ensures a numeric value is within a range."""

    def check_range(value: Any) -> bool:
        if not isinstance(value, (int, float)):
            return False

        if min_val is not None and value < min_val:
            return False

        if max_val is not None and value > max_val:
            return False

        return True

    range_desc = ""
    if min_val is not None and max_val is not None:
        range_desc = f"between {min_val} and {max_val}"
    elif min_val is not None:
        range_desc = f"at least {min_val}"
    elif max_val is not None:
        range_desc = f"at most {max_val}"

    return PropertyValidator(
        predicate=check_range,
        message=message or f"Value must be {range_desc}",
        error_code="numeric_range",
    )


def custom_validator(
    predicate: Callable[[Any], bool], message: str, error_code: Optional[str] = None
) -> PropertyValidator:
    """Create a custom validator from a predicate function."""
    return PropertyValidator(
        predicate=predicate, message=message, error_code=error_code or "custom_validation"
    )


# Decorator for applying validators to class methods


def validate_with(*validators: ValidatorBase):
    """Decorator that applies validators to method parameters.

    Usage:
        class UserService:
            @validate_with(required(), email_format())
            def create_user(self, email: str):
                # Method implementation
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Apply validators to method arguments
            # This is a simplified implementation - full implementation would
            # inspect method signature and apply validators to specific parameters

            # Get first non-self argument (assuming it's the value to validate)
            if len(args) > 1:
                value_to_validate = args[1]
                all_errors = []

                for validator in validators:
                    result = validator.validate(value_to_validate)
                    if not result.is_valid:
                        for error in result.errors:
                            all_errors.append(
                                ValidationException(error.message, error.field, error.code)
                            )

                if all_errors:
                    if len(all_errors) == 1:
                        raise all_errors[0]
                    else:
                        from .exceptions import CompositeValidationException

                        raise CompositeValidationException(all_errors)

            return func(*args, **kwargs)

        return wrapper

    return decorator
