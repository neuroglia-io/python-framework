"""
Mario's Pizzeria - Complete Sample Application

This sample application demonstrates all major Neuroglia framework features
through a realistic pizza ordering and management system.

Features demonstrated:
- Clean Architecture with API, Application, Domain, and Integration layers
- CQRS with Commands, Queries, and Event Handlers
- Dependency Injection with service registration patterns
- Repository Pattern with file-based persistence
- Domain Events and Event-Driven Architecture
- MVC Controllers with automatic discovery
- Object Mapping between entities and DTOs
- Comprehensive error handling and validation

The application models a complete pizzeria management system including:
- Order placement and tracking
- Menu management
- Kitchen workflow management
- Payment processing simulation
- Customer notifications

Usage:
    python -m samples.mario-pizzeria

Or with CLI tool:
    pyneuroctl start pizzeria --port 8001
"""
