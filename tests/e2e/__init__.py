"""
End-to-End Test Suite

Comprehensive end-to-end tests validating complete workflows across all layers
of the Neuroglia framework. These tests simulate real-world business scenarios
and verify that all components work together correctly.

Test Modules:
    - test_complete_order_workflow.py: Full order lifecycle from creation to delivery
    - test_customer_journey_e2e.py: Multi-aggregate customer workflows
    - test_event_driven_scenarios.py: Event-driven architecture patterns

Test Scope:
    E2E tests span all architectural layers:
    - Domain: Aggregates, entities, domain events, business rules
    - Application: Commands, queries, handlers, services
    - API: Controllers, routing, request/response handling
    - Integration: Repositories, external services, messaging

Expected Behavior:
    - Complete workflows execute successfully
    - Data persists correctly across layers
    - Events propagate through the system
    - Business rules are enforced consistently
    - Error handling works end-to-end

Related Documentation:
    - [E2E Testing Strategy](../TEST_ARCHITECTURE.md)
    - [Mario's Pizzeria Sample](../../samples/mario-pizzeria/)
"""
