"""
Tests for the decimal heuristic fix in JsonSerializer._infer_and_deserialize.

This test suite verifies that:
1. The decimal heuristic only triggers for fields that END with monetary patterns
2. Nested dictionaries with 'price' in the path don't cause InvalidOperation errors
3. Valid decimal strings in monetary fields are still correctly converted
4. The InvalidOperation exception is properly handled

Note: The decimal heuristic only applies to fields WITHOUT type annotations.
If a field has a type annotation (e.g., `price: str`), the type annotation takes
precedence and no Decimal conversion is attempted.
"""

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Optional

import pytest

from neuroglia.serialization.json import JsonSerializer


@dataclass
class ProductWithTypedPrice:
    """Dataclass with an explicitly typed price field - no Decimal conversion."""

    name: str
    price: str  # String type annotation - should remain as string


@dataclass
class OpenApiSchema:
    """Dataclass representing an OpenAPI schema with nested Dict[str, Any]."""

    name: str
    input_schema: dict[str, Any]
    output_schema: Optional[dict[str, Any]] = None


@dataclass
class ConfigWithNestedPricing:
    """Configuration object with nested pricing structures."""

    service_name: str
    pricing_config: dict[str, Any]


class UntypedProduct:
    """
    Class without type annotations - allows _infer_and_deserialize to be used.
    The decimal heuristic only triggers for fields without type annotations.
    """

    def __init__(self):
        pass


class TestDecimalHeuristicFix:
    """Tests for the decimal heuristic in _infer_and_deserialize."""

    @pytest.fixture
    def serializer(self) -> JsonSerializer:
        return JsonSerializer()

    # =========================================================================
    # Regression Tests - These should NOT raise InvalidOperation
    # =========================================================================

    def test_nested_dict_with_price_field_type_string(self, serializer: JsonSerializer):
        """
        Ensure nested dicts with 'price' in path don't trigger Decimal conversion
        when the value is not a number (e.g., JSON Schema "type": "number").

        This was the original bug: 'input_schema_properties_price_type' contains 'price'
        but the value "number" is not a valid decimal.
        """
        data = {
            "name": "create_order",
            "input_schema": {"properties": {"price": {"type": "number", "description": "Price in USD"}}},
        }

        json_str = json.dumps(data)

        # This should NOT raise InvalidOperation
        result = serializer.deserialize_from_text(json_str, OpenApiSchema)

        assert result.name == "create_order"
        assert result.input_schema["properties"]["price"]["type"] == "number"
        assert result.input_schema["properties"]["price"]["description"] == "Price in USD"

    def test_nested_dict_with_multiple_monetary_keywords_in_path(self, serializer: JsonSerializer):
        """
        Test deeply nested paths containing multiple monetary keywords.
        """
        data = {
            "name": "pricing_service",
            "input_schema": {
                "definitions": {
                    "price_calculation": {
                        "properties": {
                            "base_cost": {
                                "type": "integer",
                                "minimum": 0,
                            },
                            "total_amount": {
                                "type": "string",
                                "format": "decimal",
                            },
                        }
                    }
                }
            },
        }

        json_str = json.dumps(data)
        result = serializer.deserialize_from_text(json_str, OpenApiSchema)

        # Values like "integer", "string", "decimal" should remain as strings
        base_cost_type = result.input_schema["definitions"]["price_calculation"]["properties"]["base_cost"]["type"]
        assert base_cost_type == "integer"

        total_amount_type = result.input_schema["definitions"]["price_calculation"]["properties"]["total_amount"]["type"]
        assert total_amount_type == "string"

    def test_openapi_schema_with_pricing_endpoint(self, serializer: JsonSerializer):
        """
        Real-world OpenAPI schema snippet with pricing-related fields.
        """
        data = {
            "name": "get_product_price",
            "input_schema": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "price": {
                        "type": "number",
                        "description": "Unit price",
                        "minimum": 0,
                    },
                    "discount_amount": {
                        "type": "number",
                        "description": "Discount in dollars",
                    },
                },
                "required": ["product_id", "price"],
            },
        }

        json_str = json.dumps(data)
        result = serializer.deserialize_from_text(json_str, OpenApiSchema)

        # All type strings should remain as strings
        assert result.input_schema["properties"]["product_id"]["type"] == "string"
        assert result.input_schema["properties"]["price"]["type"] == "number"
        assert result.input_schema["properties"]["discount_amount"]["type"] == "number"

    def test_config_with_nested_fee_structure(self, serializer: JsonSerializer):
        """
        Configuration with nested fee structures shouldn't trigger false positives.
        """
        data = {
            "service_name": "payment_processor",
            "pricing_config": {
                "fee_tiers": {
                    "standard": {"type": "percentage", "value": "2.5"},
                    "premium": {"type": "flat", "value": "0.30"},
                },
                "total_fee_calculation": {
                    "method": "sum",
                    "components": ["base", "processing"],
                },
            },
        }

        json_str = json.dumps(data)
        result = serializer.deserialize_from_text(json_str, ConfigWithNestedPricing)

        # "percentage" and "flat" should not be converted to Decimal
        assert result.pricing_config["fee_tiers"]["standard"]["type"] == "percentage"
        assert result.pricing_config["fee_tiers"]["premium"]["type"] == "flat"
        # "value" is not a terminal monetary field, so it should remain as string
        assert result.pricing_config["fee_tiers"]["standard"]["value"] == "2.5"

    # =========================================================================
    # Type Annotation Tests - Explicit types take precedence
    # =========================================================================

    def test_typed_price_field_remains_string(self, serializer: JsonSerializer):
        """
        When a field has an explicit type annotation (str), it should remain as that type.
        The Decimal heuristic only applies to fields WITHOUT type annotations.
        """
        data = {"name": "Widget", "price": "19.99"}

        json_str = json.dumps(data)
        result = serializer.deserialize_from_text(json_str, ProductWithTypedPrice)

        # The price field should remain as string because of the type annotation
        assert result.price == "19.99"
        assert isinstance(result.price, str)

    # =========================================================================
    # _infer_and_deserialize Tests - For untyped fields
    # =========================================================================

    def test_infer_and_deserialize_terminal_price_field(self, serializer: JsonSerializer):
        """
        Direct test of _infer_and_deserialize for a terminal 'price' field.
        """
        result = serializer._infer_and_deserialize("price", "19.99", object)
        assert result == Decimal("19.99")

    def test_infer_and_deserialize_terminal_cost_field(self, serializer: JsonSerializer):
        """
        Direct test of _infer_and_deserialize for a terminal 'cost' field.
        """
        result = serializer._infer_and_deserialize("item_cost", "99.50", object)
        assert result == Decimal("99.50")

    def test_infer_and_deserialize_negative_decimal(self, serializer: JsonSerializer):
        """
        Negative decimal values should be correctly converted.
        """
        result = serializer._infer_and_deserialize("refund_amount", "-25.50", object)
        assert result == Decimal("-25.50")

    def test_infer_and_deserialize_scientific_notation(self, serializer: JsonSerializer):
        """
        Scientific notation should be recognized as valid decimal.
        """
        result = serializer._infer_and_deserialize("price", "1.5e-2", object)
        assert result == Decimal("1.5e-2")
        assert result == Decimal("0.015")

    def test_infer_and_deserialize_non_terminal_price_no_conversion(self, serializer: JsonSerializer):
        """
        A path with 'price' in the middle should NOT trigger Decimal conversion.
        """
        result = serializer._infer_and_deserialize("input_schema_properties_price_type", "number", object)
        assert result == "number"
        assert isinstance(result, str)

    def test_infer_and_deserialize_non_decimal_value(self, serializer: JsonSerializer):
        """
        Non-numeric strings in terminal monetary fields should remain as strings.
        """
        result = serializer._infer_and_deserialize("price", "Call for quote", object)
        assert result == "Call for quote"
        assert isinstance(result, str)

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_empty_string_not_converted(self, serializer: JsonSerializer):
        """
        Empty string should not cause an error and should remain as empty string.
        """
        result = serializer._infer_and_deserialize("price", "", object)
        assert result == ""

    def test_whitespace_only_string_not_converted(self, serializer: JsonSerializer):
        """
        Whitespace-only string should not cause an error.
        """
        result = serializer._infer_and_deserialize("price", "   ", object)
        assert result == "   "

    def test_text_value_in_price_field_not_converted(self, serializer: JsonSerializer):
        """
        Text values in price fields should remain as strings.
        """
        result = serializer._infer_and_deserialize("price", "Free", object)
        assert result == "Free"

    def test_price_with_currency_symbol_not_converted(self, serializer: JsonSerializer):
        """
        Price with currency symbol should remain as string.
        """
        result = serializer._infer_and_deserialize("price", "$19.99", object)
        assert result == "$19.99"

    def test_price_with_commas_not_converted(self, serializer: JsonSerializer):
        """
        Price with thousand separators should remain as string.
        """
        result = serializer._infer_and_deserialize("price", "1,234.56", object)
        assert result == "1,234.56"


class TestIsMonetaryField:
    """Tests for the _is_monetary_field helper method."""

    @pytest.fixture
    def serializer(self) -> JsonSerializer:
        return JsonSerializer()

    def test_simple_price_field(self, serializer: JsonSerializer):
        assert serializer._is_monetary_field("price") is True

    def test_simple_cost_field(self, serializer: JsonSerializer):
        assert serializer._is_monetary_field("cost") is True

    def test_simple_amount_field(self, serializer: JsonSerializer):
        assert serializer._is_monetary_field("amount") is True

    def test_simple_total_field(self, serializer: JsonSerializer):
        assert serializer._is_monetary_field("total") is True

    def test_simple_fee_field(self, serializer: JsonSerializer):
        assert serializer._is_monetary_field("fee") is True

    def test_prefixed_price_field(self, serializer: JsonSerializer):
        """Fields ending with _price should match."""
        assert serializer._is_monetary_field("unit_price") is True
        assert serializer._is_monetary_field("total_price") is True
        assert serializer._is_monetary_field("base_price") is True

    def test_nested_path_with_price_in_middle(self, serializer: JsonSerializer):
        """Paths with 'price' in the middle should NOT match."""
        assert serializer._is_monetary_field("price_type") is False
        assert serializer._is_monetary_field("input_schema_properties_price_type") is False
        assert serializer._is_monetary_field("price_description") is False

    def test_nested_path_ending_with_monetary_pattern(self, serializer: JsonSerializer):
        """Nested paths ending with monetary pattern should match."""
        assert serializer._is_monetary_field("order_total_price") is True
        assert serializer._is_monetary_field("shipping_fee") is True
        assert serializer._is_monetary_field("item_cost") is True

    def test_case_insensitivity(self, serializer: JsonSerializer):
        """Field names should be case-insensitive."""
        assert serializer._is_monetary_field("PRICE") is True
        assert serializer._is_monetary_field("Price") is True
        assert serializer._is_monetary_field("TOTAL_COST") is True

    def test_additional_monetary_patterns(self, serializer: JsonSerializer):
        """Test additional monetary patterns like balance, rate, tax."""
        assert serializer._is_monetary_field("account_balance") is True
        assert serializer._is_monetary_field("interest_rate") is True
        assert serializer._is_monetary_field("sales_tax") is True


class TestLooksLikeDecimal:
    """Tests for the _looks_like_decimal helper method."""

    @pytest.fixture
    def serializer(self) -> JsonSerializer:
        return JsonSerializer()

    def test_simple_integer(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("123") is True

    def test_decimal_number(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("123.45") is True

    def test_negative_number(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("-123.45") is True

    def test_zero(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("0") is True

    def test_zero_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("0.00") is True

    def test_scientific_notation(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("1.5e10") is True
        assert serializer._looks_like_decimal("1.5E-10") is True
        assert serializer._looks_like_decimal("1e+5") is True

    def test_leading_whitespace(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("  123.45") is True

    def test_trailing_whitespace(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("123.45  ") is True

    def test_text_not_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("number") is False
        assert serializer._looks_like_decimal("string") is False
        assert serializer._looks_like_decimal("hello") is False

    def test_currency_symbol_not_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("$19.99") is False
        assert serializer._looks_like_decimal("€50.00") is False

    def test_commas_not_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("1,234.56") is False

    def test_empty_string_not_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("") is False

    def test_whitespace_only_not_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("   ") is False

    def test_mixed_content_not_decimal(self, serializer: JsonSerializer):
        assert serializer._looks_like_decimal("123abc") is False
        assert serializer._looks_like_decimal("abc123") is False


class TestInvalidOperationHandling:
    """Tests to ensure InvalidOperation is properly caught."""

    @pytest.fixture
    def serializer(self) -> JsonSerializer:
        return JsonSerializer()

    def test_inf_string_handled_gracefully(self, serializer: JsonSerializer):
        """
        Infinity strings might pass the regex but fail Decimal conversion.
        They should be handled gracefully via _infer_and_deserialize.
        """
        # "Inf" doesn't match our decimal regex, so it won't be attempted
        result = serializer._infer_and_deserialize("price", "Inf", object)
        assert result == "Inf"

    def test_nan_string_handled_gracefully(self, serializer: JsonSerializer):
        """
        NaN strings should be handled gracefully via _infer_and_deserialize.
        """
        # "NaN" doesn't match our decimal regex, so it won't be attempted
        result = serializer._infer_and_deserialize("price", "NaN", object)
        assert result == "NaN"
