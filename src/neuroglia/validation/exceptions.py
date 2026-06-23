"""Enhanced validation exceptions for the Neuroglia framework.

This module provides specific exception types for different validation scenarios,
enabling precise error handling and meaningful error messages for business logic
validation failures.
"""

from typing import List, Dict, Any, Optional


class ValidationException(Exception):
    """Base exception for all validation errors in the framework.

    This exception serves as the base class for all validation-related errors,
    providing a consistent interface for handling validation failures across
    the framework.

    Attributes:
        message: The main error message describing the validation failure
        field: Optional field name where the validation failed
        code: Optional error code for programmatic error handling
        details: Additional context or details about the validation failure
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        if self.field:
            return f"Validation failed for field '{self.field}': {self.message}"
        return f"Validation failed: {self.message}"


class BusinessRuleViolationException(ValidationException):
    """Exception raised when business rules are violated.

    This exception is specifically used for business logic validation failures,
    such as when domain invariants are violated or business constraints are
    not met.

    Attributes:
        rule_name: The name of the business rule that was violated
        entity_type: The type of entity where the rule violation occurred
        entity_id: The ID of the specific entity instance (if applicable)
    """

    def __init__(
        self,
        message: str,
        rule_name: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.rule_name = rule_name
        self.entity_type = entity_type
        self.entity_id = entity_id

    def __str__(self) -> str:
        base_msg = f"Business rule '{self.rule_name}' violated: {self.message}"
        if self.entity_type:
            base_msg += f" (Entity: {self.entity_type}"
            if self.entity_id:
                base_msg += f", ID: {self.entity_id}"
            base_msg += ")"
        return base_msg


class ConditionalValidationException(ValidationException):
    """Exception raised when conditional validation rules fail.

    This exception is used when validation rules that depend on certain
    conditions are violated, providing context about the condition that
    triggered the validation.

    Attributes:
        condition: Description of the condition that triggered validation
        condition_met: Whether the condition was met or not
    """

    def __init__(self, message: str, condition: str, condition_met: bool = True, **kwargs):
        super().__init__(message, **kwargs)
        self.condition = condition
        self.condition_met = condition_met

    def __str__(self) -> str:
        status = "met" if self.condition_met else "not met"
        return (
            f"Conditional validation failed (condition '{self.condition}' {status}): {self.message}"
        )


class CompositeValidationException(ValidationException):
    """Exception that aggregates multiple validation errors.

    This exception is used when multiple validation rules fail simultaneously,
    allowing all validation errors to be collected and reported together.

    Attributes:
        errors: List of individual validation exceptions
    """

    def __init__(self, errors: List[ValidationException]):
        self.errors = errors
        message = f"Multiple validation errors occurred ({len(errors)} errors)"
        super().__init__(message)

    def __str__(self) -> str:
        error_details = []
        for i, error in enumerate(self.errors, 1):
            error_details.append(f"  {i}. {str(error)}")

        return f"{self.message}:\n" + "\n".join(error_details)

    def get_field_errors(self) -> Dict[str, List[str]]:
        """Get validation errors grouped by field name.

        Returns:
            Dictionary mapping field names to lists of error messages
        """
        field_errors: Dict[str, List[str]] = {}

        for error in self.errors:
            field_name = error.field or "general"
            if field_name not in field_errors:
                field_errors[field_name] = []
            field_errors[field_name].append(error.message)

        return field_errors
