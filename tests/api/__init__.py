"""
API Layer Tests

This module contains tests for the API layer of the Neuroglia framework,
including FastAPI controllers, routing, request validation, and response formatting.

Test Organization:
    - test_controllers.py: ControllerBase functionality and HTTP methods
    - test_routing.py: Route registration and auto-mounting
    - test_request_validation.py: Pydantic validation and error handling
    - test_response_formatting.py: Response serialization and status codes

Coverage Areas:
    - FastAPI integration
    - HTTP method handling (GET, POST, PUT, DELETE, PATCH)
    - Request/response mapping
    - Error handling and status codes
    - Authentication and authorization
    - Dependency injection in controllers
    - DTO validation

Related Modules:
    - neuroglia.mvc: ControllerBase and routing
    - neuroglia.mediation: Mediator integration
    - neuroglia.mapping: DTO mapping

Related Documentation:
    - [MVC Controllers](../../docs/features/mvc-controllers.md)
    - [FastAPI Integration](../../docs/guides/fastapi-integration.md)
"""
