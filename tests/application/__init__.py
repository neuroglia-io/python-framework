"""
Application Layer Tests

Test suite for the application layer of the Neuroglia framework, focusing on CQRS
mediation patterns, command/query handlers, and pipeline behaviors.

Test Modules:
    - test_mediator.py: Core mediator functionality and request routing
    - test_command_handlers.py: Command execution and validation
    - test_query_handlers.py: Query handling and result processing
    - test_pipeline_behaviors.py: Cross-cutting concerns and middleware

Coverage:
    - neuroglia.mediation.mediator: Mediator pattern implementation
    - neuroglia.mediation.pipeline_behavior: Request pipeline behaviors
    - Command/Query/Event handler abstractions

Related Documentation:
    - [CQRS Patterns](../../docs/features/simple-cqrs.md)
    - [Test Architecture](../TEST_ARCHITECTURE.md)
"""
