"""
Test fixtures package for Neuroglia framework tests.

This package provides reusable test data factories, fixtures, and utilities
for comprehensive framework testing using Mario's Pizzeria as the domain model.

Modules:
    test_data: Mario's Pizzeria domain test data factories
    domain_fixtures: Domain layer test fixtures (entities, value objects, events)
    application_fixtures: Application layer test fixtures (commands, queries, handlers)
    integration_fixtures: Integration layer test fixtures (repositories, services)

Usage:
    from tests.fixtures.test_data import create_margherita_pizza, create_order
    from tests.fixtures import domain_fixtures

    def test_order_workflow():
        pizza = create_margherita_pizza()
        order = create_order(pizzas=[pizza])

References:
    - Test Architecture: tests/TEST_ARCHITECTURE.md
    - Sample Application: samples/mario-pizzeria/
"""

# Re-export commonly used factories for convenience
from .test_data import (  # Enums; Value Objects; Pizza factories; Customer factories; Order factories; Command factories; Query factories; Event factories; Batch generators
    Address,
    Money,
    OrderStatus,
    PaymentMethod,
    PizzaSize,
    create_confirmed_order,
    create_cooking_order,
    create_custom_pizza,
    create_customer,
    create_get_menu_query_data,
    create_get_order_query_data,
    create_get_orders_by_status_query_data,
    create_margherita_pizza,
    create_order,
    create_order_confirmed_event_data,
    create_order_created_event_data,
    create_pepperoni_pizza,
    create_pizza_added_event_data,
    create_place_order_command_data,
    create_premium_customer,
    create_ready_order,
    create_sample_customers,
    create_sample_menu,
    create_sample_orders,
    create_supreme_pizza,
    create_update_order_status_command_data,
)

__all__ = [
    # Enums
    "PizzaSize",
    "OrderStatus",
    "PaymentMethod",
    # Value Objects
    "Money",
    "Address",
    # Pizza factories
    "create_margherita_pizza",
    "create_pepperoni_pizza",
    "create_supreme_pizza",
    "create_custom_pizza",
    # Customer factories
    "create_customer",
    "create_premium_customer",
    # Order factories
    "create_order",
    "create_confirmed_order",
    "create_cooking_order",
    "create_ready_order",
    # Command factories
    "create_place_order_command_data",
    "create_update_order_status_command_data",
    # Query factories
    "create_get_order_query_data",
    "create_get_orders_by_status_query_data",
    "create_get_menu_query_data",
    # Event factories
    "create_order_created_event_data",
    "create_order_confirmed_event_data",
    "create_pizza_added_event_data",
    # Batch generators
    "create_sample_menu",
    "create_sample_orders",
    "create_sample_customers",
]
