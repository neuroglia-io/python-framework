"""
Case conversion utilities for string transformations.

This module provides comprehensive utilities for converting between different
case conventions commonly used in programming: snake_case, camelCase,
PascalCase, kebab-case, and more.

For detailed information about case conversion utilities, see:
https://bvandewe.github.io/pyneuro/features/case-conversion-utilities/
"""

import re
from typing import Any


class CamelCaseConverter:
    """
    Comprehensive case conversion utility for string transformations.

    Provides methods for converting between snake_case, camelCase, PascalCase,
    kebab-case, and other common case conventions. Essential for API
    compatibility between different naming conventions.

    For detailed information about case conversion utilities, see:
    https://bvandewe.github.io/pyneuro/features/case-conversion-utilities/
    """

    # Regular expressions for case detection and conversion
    _SNAKE_CASE_RE = re.compile(r"_([a-z])")
    _CAMEL_CASE_RE = re.compile(r"([a-z0-9])([A-Z])")
    _KEBAB_CAMEL_RE = re.compile(r"-([a-z])")
    _SPACE_CAMEL_RE = re.compile(r"\s+([a-z])")
    _WORD_BOUNDARY_RE = re.compile(r"[\s_-]+")

    @staticmethod
    def to_camel_case(string: str) -> str:
        """
        Convert a string to camelCase.

        Args:
            string: Input string in any case convention

        Returns:
            String converted to camelCase

        Examples:
            >>> to_camel_case("snake_case_string")
            "snakeCaseString"
            >>> to_camel_case("kebab-case-string")
            "kebabCaseString"
            >>> to_camel_case("PascalCaseString")
            "pascalCaseString"
        """
        if not string:
            return string

        # Handle already camelCase strings
        if "_" not in string and "-" not in string and " " not in string:
            return string[0].lower() + string[1:] if string else ""

        # Convert from snake_case
        if "_" in string:
            components = string.split("_")
            return components[0].lower() + "".join(word.capitalize() for word in components[1:])

        # Convert from kebab-case
        if "-" in string:
            components = string.split("-")
            return components[0].lower() + "".join(word.capitalize() for word in components[1:])

        # Convert from space separated
        if " " in string:
            components = string.split(" ")
            return components[0].lower() + "".join(word.capitalize() for word in components[1:])

        # Default: assume PascalCase, convert to camelCase
        return string[0].lower() + string[1:] if string else ""

    @staticmethod
    def to_snake_case(string: str) -> str:
        """
        Convert a string to snake_case.

        Args:
            string: Input string in any case convention

        Returns:
            String converted to snake_case

        Examples:
            >>> to_snake_case("camelCaseString")
            "camel_case_string"
            >>> to_snake_case("PascalCaseString")
            "pascal_case_string"
            >>> to_snake_case("kebab-case-string")
            "kebab_case_string"
        """
        if not string:
            return string

        # Handle kebab-case and space-separated
        string = string.replace("-", "_").replace(" ", "_")

        # Handle camelCase and PascalCase
        # Insert underscore before uppercase letters that follow lowercase letters or digits
        s1 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", string)

        # Handle sequences of uppercase letters followed by lowercase letters
        s2 = re.sub("([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)

        return s2.lower()

    @staticmethod
    def to_pascal_case(string: str) -> str:
        """
        Convert a string to PascalCase.

        Args:
            string: Input string in any case convention

        Returns:
            String converted to PascalCase

        Examples:
            >>> to_pascal_case("snake_case_string")
            "SnakeCaseString"
            >>> to_pascal_case("camelCaseString")
            "CamelCaseString"
            >>> to_pascal_case("kebab-case-string")
            "KebabCaseString"
        """
        if not string:
            return string

        camel_case = CamelCaseConverter.to_camel_case(string)
        return camel_case[0].upper() + camel_case[1:] if camel_case else ""

    @staticmethod
    def to_kebab_case(string: str) -> str:
        """
        Convert a string to kebab-case.

        Args:
            string: Input string in any case convention

        Returns:
            String converted to kebab-case

        Examples:
            >>> to_kebab_case("camelCaseString")
            "camel-case-string"
            >>> to_kebab_case("snake_case_string")
            "snake-case-string"
            >>> to_kebab_case("PascalCaseString")
            "pascal-case-string"
        """
        if not string:
            return string

        snake_case = CamelCaseConverter.to_snake_case(string)
        return snake_case.replace("_", "-")

    @staticmethod
    def to_title_case(string: str) -> str:
        """
        Convert a string to Title Case with spaces.

        Args:
            string: Input string in any case convention

        Returns:
            String converted to Title Case

        Examples:
            >>> to_title_case("camelCaseString")
            "Camel Case String"
            >>> to_title_case("snake_case_string")
            "Snake Case String"
        """
        if not string:
            return string

        snake_case = CamelCaseConverter.to_snake_case(string)
        return " ".join(word.capitalize() for word in snake_case.split("_"))

    @staticmethod
    def transform_dict_keys(data: Any, transform_func) -> Any:
        """
        Transform all keys in a dictionary using the specified transform function.

        Args:
            data: Dictionary with keys to transform (or any other type)
            transform_func: Function to apply to each key

        Returns:
            New dictionary with transformed keys, or original data if not a dict

        Examples:
            >>> transform_dict_keys({"snake_key": "value"}, to_camel_case)
            {"snakeKey": "value"}
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            new_key = transform_func(key) if isinstance(key, str) else key

            # Recursively transform nested dictionaries
            if isinstance(value, dict):
                result[new_key] = CamelCaseConverter.transform_dict_keys(value, transform_func)
            elif isinstance(value, list):
                result[new_key] = [(CamelCaseConverter.transform_dict_keys(item, transform_func) if isinstance(item, dict) else item) for item in value]
            else:
                result[new_key] = value

        return result

    @staticmethod
    def to_camel_case_dict(data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert all dictionary keys to camelCase recursively.

        Args:
            data: Dictionary with keys to convert

        Returns:
            New dictionary with camelCase keys
        """
        return CamelCaseConverter.transform_dict_keys(data, CamelCaseConverter.to_camel_case)

    @staticmethod
    def to_snake_case_dict(data: dict[str, Any]) -> dict[str, Any]:
        """
        Convert all dictionary keys to snake_case recursively.

        Args:
            data: Dictionary with keys to convert

        Returns:
            New dictionary with snake_case keys
        """
        return CamelCaseConverter.transform_dict_keys(data, CamelCaseConverter.to_snake_case)


# Convenience functions for direct usage
def to_camel_case(string: str) -> str:
    """Convert string to camelCase."""
    return CamelCaseConverter.to_camel_case(string)


def to_snake_case(string: str) -> str:
    """Convert string to snake_case."""
    return CamelCaseConverter.to_snake_case(string)


def to_pascal_case(string: str) -> str:
    """Convert string to PascalCase."""
    return CamelCaseConverter.to_pascal_case(string)


def to_kebab_case(string: str) -> str:
    """Convert string to kebab-case."""
    return CamelCaseConverter.to_kebab_case(string)


def to_title_case(string: str) -> str:
    """Convert string to Title Case."""
    return CamelCaseConverter.to_title_case(string)


def camel_case_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Convert dictionary keys to camelCase."""
    return CamelCaseConverter.to_camel_case_dict(data)


def snake_case_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Convert dictionary keys to snake_case."""
    return CamelCaseConverter.to_snake_case_dict(data)
