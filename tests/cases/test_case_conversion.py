"""Tests for CamelCase utility functions."""

from neuroglia.utils.case_conversion import (
    CamelCaseConverter,
    to_camel_case,
    to_snake_case,
    to_pascal_case,
    to_kebab_case,
    to_title_case,
    camel_case_dict,
    snake_case_dict,
)


class TestCamelCaseConverter:
    """Test the CamelCaseConverter class."""

    def test_to_camel_case_from_snake_case(self):
        """Test converting from snake_case to camelCase."""
        assert CamelCaseConverter.to_camel_case("snake_case_string") == "snakeCaseString"
        assert CamelCaseConverter.to_camel_case("simple_case") == "simpleCase"
        assert CamelCaseConverter.to_camel_case("single") == "single"
        assert CamelCaseConverter.to_camel_case("") == ""

    def test_to_camel_case_from_kebab_case(self):
        """Test converting from kebab-case to camelCase."""
        assert CamelCaseConverter.to_camel_case("kebab-case-string") == "kebabCaseString"
        assert CamelCaseConverter.to_camel_case("simple-case") == "simpleCase"
        assert CamelCaseConverter.to_camel_case("single") == "single"

    def test_to_camel_case_from_space_separated(self):
        """Test converting from space separated to camelCase."""
        assert CamelCaseConverter.to_camel_case("space separated string") == "spaceSeparatedString"
        assert CamelCaseConverter.to_camel_case("simple case") == "simpleCase"

    def test_to_camel_case_from_pascal_case(self):
        """Test converting from PascalCase to camelCase."""
        assert CamelCaseConverter.to_camel_case("PascalCaseString") == "pascalCaseString"
        assert CamelCaseConverter.to_camel_case("SimpleCase") == "simpleCase"
        assert CamelCaseConverter.to_camel_case("A") == "a"

    def test_to_camel_case_already_camel_case(self):
        """Test that already camelCase strings remain unchanged."""
        assert CamelCaseConverter.to_camel_case("camelCaseString") == "camelCaseString"
        assert CamelCaseConverter.to_camel_case("simpleCase") == "simpleCase"

    def test_to_snake_case_from_camel_case(self):
        """Test converting from camelCase to snake_case."""
        assert CamelCaseConverter.to_snake_case("camelCaseString") == "camel_case_string"
        assert CamelCaseConverter.to_snake_case("simpleCase") == "simple_case"
        assert CamelCaseConverter.to_snake_case("single") == "single"

    def test_to_snake_case_from_pascal_case(self):
        """Test converting from PascalCase to snake_case."""
        assert CamelCaseConverter.to_snake_case("PascalCaseString") == "pascal_case_string"
        assert CamelCaseConverter.to_snake_case("SimpleCase") == "simple_case"
        assert CamelCaseConverter.to_snake_case("A") == "a"

    def test_to_snake_case_from_kebab_case(self):
        """Test converting from kebab-case to snake_case."""
        assert CamelCaseConverter.to_snake_case("kebab-case-string") == "kebab_case_string"
        assert CamelCaseConverter.to_snake_case("simple-case") == "simple_case"

    def test_to_snake_case_complex_cases(self):
        """Test snake_case conversion with complex cases."""
        assert CamelCaseConverter.to_snake_case("HTTPResponse") == "http_response"
        assert CamelCaseConverter.to_snake_case("XMLParser") == "xml_parser"
        assert CamelCaseConverter.to_snake_case("APIKey") == "api_key"
        assert CamelCaseConverter.to_snake_case("JSONData") == "json_data"

    def test_to_pascal_case(self):
        """Test converting to PascalCase."""
        assert CamelCaseConverter.to_pascal_case("snake_case_string") == "SnakeCaseString"
        assert CamelCaseConverter.to_pascal_case("camelCaseString") == "CamelCaseString"
        assert CamelCaseConverter.to_pascal_case("kebab-case-string") == "KebabCaseString"
        assert CamelCaseConverter.to_pascal_case("space separated") == "SpaceSeparated"
        assert CamelCaseConverter.to_pascal_case("single") == "Single"
        assert CamelCaseConverter.to_pascal_case("") == ""

    def test_to_kebab_case(self):
        """Test converting to kebab-case."""
        assert CamelCaseConverter.to_kebab_case("camelCaseString") == "camel-case-string"
        assert CamelCaseConverter.to_kebab_case("PascalCaseString") == "pascal-case-string"
        assert CamelCaseConverter.to_kebab_case("snake_case_string") == "snake-case-string"
        assert CamelCaseConverter.to_kebab_case("single") == "single"
        assert CamelCaseConverter.to_kebab_case("") == ""

    def test_to_title_case(self):
        """Test converting to Title Case."""
        assert CamelCaseConverter.to_title_case("camelCaseString") == "Camel Case String"
        assert CamelCaseConverter.to_title_case("snake_case_string") == "Snake Case String"
        assert CamelCaseConverter.to_title_case("PascalCaseString") == "Pascal Case String"
        assert CamelCaseConverter.to_title_case("single") == "Single"
        assert CamelCaseConverter.to_title_case("") == ""

    def test_transform_dict_keys_simple(self):
        """Test transforming dictionary keys."""
        data = {"snake_key": "value", "another_key": "value2"}
        result = CamelCaseConverter.transform_dict_keys(data, CamelCaseConverter.to_camel_case)
        expected = {"snakeKey": "value", "anotherKey": "value2"}
        assert result == expected

    def test_transform_dict_keys_nested(self):
        """Test transforming nested dictionary keys."""
        data = {
            "outer_key": {"inner_key": "value", "another_inner": "value2"},
            "simple_key": "simple_value",
        }
        result = CamelCaseConverter.transform_dict_keys(data, CamelCaseConverter.to_camel_case)
        expected = {
            "outerKey": {"innerKey": "value", "anotherInner": "value2"},
            "simpleKey": "simple_value",
        }
        assert result == expected

    def test_transform_dict_keys_with_lists(self):
        """Test transforming dictionary keys with lists containing dictionaries."""
        data = {
            "list_key": [{"item_key": "value1"}, {"another_item": "value2"}],
            "simple_key": "value",
        }
        result = CamelCaseConverter.transform_dict_keys(data, CamelCaseConverter.to_camel_case)
        expected = {
            "listKey": [{"itemKey": "value1"}, {"anotherItem": "value2"}],
            "simpleKey": "value",
        }
        assert result == expected

    def test_to_camel_case_dict(self):
        """Test camelCase dictionary conversion."""
        data = {"snake_key": "value", "another_key": {"nested_key": "nested_value"}}
        result = CamelCaseConverter.to_camel_case_dict(data)
        expected = {"snakeKey": "value", "anotherKey": {"nestedKey": "nested_value"}}
        assert result == expected

    def test_to_snake_case_dict(self):
        """Test snake_case dictionary conversion."""
        data = {"camelKey": "value", "anotherKey": {"nestedKey": "nested_value"}}
        result = CamelCaseConverter.to_snake_case_dict(data)
        expected = {"camel_key": "value", "another_key": {"nested_key": "nested_value"}}
        assert result == expected


class TestConvenienceFunctions:
    """Test the convenience functions."""

    def test_to_camel_case_function(self):
        """Test the to_camel_case convenience function."""
        assert to_camel_case("snake_case_string") == "snakeCaseString"
        assert to_camel_case("PascalCase") == "pascalCase"

    def test_to_snake_case_function(self):
        """Test the to_snake_case convenience function."""
        assert to_snake_case("camelCaseString") == "camel_case_string"
        assert to_snake_case("PascalCase") == "pascal_case"

    def test_to_pascal_case_function(self):
        """Test the to_pascal_case convenience function."""
        assert to_pascal_case("snake_case_string") == "SnakeCaseString"
        assert to_pascal_case("camelCase") == "CamelCase"

    def test_to_kebab_case_function(self):
        """Test the to_kebab_case convenience function."""
        assert to_kebab_case("camelCaseString") == "camel-case-string"
        assert to_kebab_case("snake_case_string") == "snake-case-string"

    def test_to_title_case_function(self):
        """Test the to_title_case convenience function."""
        assert to_title_case("camelCaseString") == "Camel Case String"
        assert to_title_case("snake_case_string") == "Snake Case String"

    def test_camel_case_dict_function(self):
        """Test the camel_case_dict convenience function."""
        data = {"snake_key": "value"}
        result = camel_case_dict(data)
        expected = {"snakeKey": "value"}
        assert result == expected

    def test_snake_case_dict_function(self):
        """Test the snake_case_dict convenience function."""
        data = {"camelKey": "value"}
        result = snake_case_dict(data)
        expected = {"camel_key": "value"}
        assert result == expected


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_strings(self):
        """Test handling of empty strings."""
        assert to_camel_case("") == ""
        assert to_snake_case("") == ""
        assert to_pascal_case("") == ""
        assert to_kebab_case("") == ""
        assert to_title_case("") == ""

    def test_single_characters(self):
        """Test handling of single characters."""
        assert to_camel_case("a") == "a"
        assert to_snake_case("A") == "a"
        assert to_pascal_case("a") == "A"
        assert to_kebab_case("A") == "a"
        assert to_title_case("a") == "A"

    def test_numbers_in_strings(self):
        """Test handling of strings with numbers."""
        assert to_camel_case("snake_case_2") == "snakeCase2"
        assert to_snake_case("camelCase2String") == "camel_case2_string"
        assert to_pascal_case("snake_2_case") == "Snake2Case"

    def test_special_characters(self):
        """Test handling of strings with special characters."""
        # These should be handled gracefully
        assert to_camel_case("test@string") == "test@string"
        assert to_snake_case("test@String") == "test@string"

    def test_transform_dict_non_dict_input(self):
        """Test transform_dict_keys with non-dictionary input."""
        # Should return the input unchanged
        assert CamelCaseConverter.transform_dict_keys("not_a_dict", to_camel_case) == "not_a_dict"
        assert CamelCaseConverter.transform_dict_keys(123, to_camel_case) == 123
        assert CamelCaseConverter.transform_dict_keys(None, to_camel_case) is None

    def test_transform_dict_non_string_keys(self):
        """Test transform_dict_keys with non-string keys."""
        data = {123: "value", "string_key": "value2"}
        result = CamelCaseConverter.transform_dict_keys(data, to_camel_case)
        expected = {123: "value", "stringKey": "value2"}
        assert result == expected
