# Neuroglia Python Framework

[![PyPI version](https://badge.fury.io/py/neuroglia-python.svg?v=2)](https://badge.fury.io/py/neuroglia-python)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://bvandewe.github.io/pyneuro/)
[![Changelog](https://img.shields.io/badge/changelog-Keep%20a%20Changelog-E05735.svg)](https://github.com/bvandewe/pyneuro/blob/main/CHANGELOG.md)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![GitHub](https://img.shields.io/github/stars/bvandewe/pyneuro?style=social)](https://github.com/bvandewe/pyneuro)

Neuroglia is a lightweight, opinionated framework built on top of [FastAPI](https://fastapi.tiangolo.com/) that provides a comprehensive set of tools and patterns for building clean, maintainable, and scalable microservices. It enforces architectural best practices and provides out-of-the-box implementations of common patterns.

📚 **Read the full documentation at [bvandewe.github.io/pyneuro/](https://bvandewe.github.io/pyneuro/)** 📚

## Why Neuroglia?

**Choose Neuroglia for complex, domain-driven microservices that need to be maintained for years to come.**

### 🎯 The Philosophy

Neuroglia believes that **software architecture matters more than speed of initial development**. While you can build APIs quickly with vanilla FastAPI or Django, Neuroglia is designed for applications that will:

- **Scale in complexity** over time with changing business requirements
- **Be maintained by teams** with varying levels of domain expertise
- **Evolve and adapt** without accumulating technical debt
- **Integrate seamlessly** with complex enterprise ecosystems

### 🏗️ When to Choose Neuroglia

| **Choose Neuroglia When**                                            | **Choose Alternatives When**                  |
| -------------------------------------------------------------------- | --------------------------------------------- |
| ✅ Building **domain-rich applications** with complex business logic | ❌ Creating simple CRUD APIs or prototypes    |
| ✅ **Long-term maintenance** is a primary concern                    | ❌ You need something working "yesterday"     |
| ✅ Your team values **architectural consistency**                    | ❌ Framework learning curve is a blocker      |
| ✅ You need **enterprise patterns** (CQRS, DDD, Event Sourcing)      | ❌ Simple request-response patterns suffice   |
| ✅ **Multiple developers** will work on the codebase                 | ❌ Solo development or small, simple projects |
| ✅ Integration with **event-driven architectures**                   | ❌ Monolithic, database-first applications    |

### 🚀 The Neuroglia Advantage

**Compared to vanilla FastAPI:**

- **Enforced Structure**: No more "how should I organize this?" - clear architectural layers
- **Built-in Patterns**: CQRS, dependency injection, and event handling out of the box
- **Enterprise Ready**: Designed for complex domains, not just API endpoints

**Compared to Django:**

- **Microservice Native**: Built for distributed systems, not monolithic web apps
- **Domain-Driven**: Business logic lives in the domain layer, not mixed with web concerns
- **Modern Async**: Full async support without retrofitting legacy patterns

**Compared to Spring Boot (Java):**

- **Python Simplicity**: All the enterprise patterns without Java's verbosity
- **Lightweight**: No heavy application server - just the patterns you need
- **Developer Experience**: Pythonic APIs with comprehensive tooling

### 💡 Real-World Scenarios

**Perfect for:**

- 🏦 **Financial Services**: Complex domain rules, audit trails, event sourcing
- 🏥 **Healthcare Systems**: HIPAA compliance, complex workflows, integration needs
- 🏭 **Manufacturing**: Resource management, real-time monitoring, process orchestration
- 🛒 **E-commerce Platforms**: Order processing, inventory management, payment flows
- 🎯 **SaaS Products**: Multi-tenant architectures, feature flags, usage analytics

**Not ideal for:**

- 📝 Simple content management systems
- 🔗 Basic API proxies or data transformation services
- 📱 Mobile app backends with minimal business logic
- 🧪 Proof-of-concept or throwaway prototypes

### 🎨 The Developer Experience

Neuroglia optimizes for **code that tells a story**:

```python
# Your business logic is clear and testable
class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        # Domain logic is explicit and isolated
        order = Order(command.customer_id, command.items)
        await self.repository.save_async(order)
        return self.created(self.mapper.map(order, OrderDto))

# Infrastructure concerns are separated
class OrdersController(ControllerBase):
    @post("/orders", response_model=OrderDto)
    async def place_order(self, command: PlaceOrderCommand) -> OrderDto:
        return await self.mediator.execute_async(command)
```

**The result?** Code that's easy to understand, test, and evolve - even years later.

## 🚀 Key Features

- **🏗️ Clean Architecture**: Enforces separation of concerns with clearly defined layers (API, Application, Domain, Integration)
- **💉 Dependency Injection**: Lightweight container with automatic service discovery and registration
- **🎯 CQRS & Mediation**: Command Query Responsibility Segregation with built-in mediator pattern
- **🏛️ State-Based Persistence**: Alternative to event sourcing with automatic domain event dispatching
- **🔧 Pipeline Behaviors**: Cross-cutting concerns like validation, caching, and transactions
- **📡 Event-Driven Architecture**: Native support for CloudEvents, event sourcing, and reactive programming
- **🎯 Resource Oriented Architecture**: Declarative resource management with watchers, controllers, and reconciliation loops
- **🔌 MVC Controllers**: Class-based API controllers with automatic discovery and OpenAPI generation
- **🗄️ Repository Pattern**: Flexible data access layer with support for MongoDB, Event Store, and in-memory repositories
- **📊 Object Mapping**: Bidirectional mapping between domain models and DTOs
- **⚡ Reactive Programming**: Built-in support for RxPy and asynchronous event handling
- **🔧 12-Factor Compliance**: Implements all [12-Factor App](https://12factor.net) principles
- **📝 Rich Serialization**: JSON serialization with advanced features

## 🎯 Architecture Overview

Neuroglia promotes a clean, layered architecture that separates concerns and makes your code more maintainable:

```text
src/
├── api/           # 🌐 API Layer (Controllers, DTOs, Routes)
├── application/   # 💼 Application Layer (Commands, Queries, Handlers, Services)
├── domain/        # 🏛️ Domain Layer (Entities, Value Objects, Business Rules)
└── integration/   # 🔌 Integration Layer (External APIs, Repositories, Infrastructure)
```

## 📚 Documentation

**[📖 Complete Documentation](https://bvandewe.github.io/pyneuro/)**

### Quick Links

- **[🚀 Getting Started](docs/getting-started.md)** - Set up your first Neuroglia application
- **[🏗️ Architecture Guide](docs/patterns/clean-architecture.md)** - Understanding the framework's architecture
- **[💉 Dependency Injection](docs/patterns/dependency-injection.md)** - Service container and DI patterns
- **[🎯 CQRS & Mediation](docs/patterns/cqrs.md)** - Command and Query handling
- **[🗄️ Persistence Patterns](docs/patterns/persistence-patterns.md)** - Domain events with state persistence
- **[🔧 Pipeline Behaviors](docs/patterns/pipeline-behaviors.md)** - Cross-cutting concerns and middleware
- **[🎯 Resource Oriented Architecture](docs/patterns/resource-oriented-architecture.md)** - Declarative resource management patterns
- **[🔌 MVC Controllers](docs/features/mvc-controllers.md)** - Building REST APIs
- **[🗄️ Data Access](docs/features/data-access.md)** - Repository pattern and data persistence
- **[📡 Event Handling](docs/patterns/event-driven.md)** - CloudEvents and reactive programming
- **[📊 Object Mapping](docs/features/object-mapping.md)** - Mapping between different object types
- **[🔭 Observability](docs/features/observability.md)** - OpenTelemetry integration and monitoring

### Sample Applications

Learn by example with complete sample applications:

- **[🍕 Mario's Pizzeria](https://bvandewe.github.io/pyneuro/mario-pizzeria/)** - Complete pizzeria management system with UI, authentication, and observability
- **[🏦 OpenBank](https://bvandewe.github.io/pyneuro/samples/openbank/)** - Event-sourced banking domain with CQRS and EventStoreDB
- **[🧪 Lab Resource Manager](https://bvandewe.github.io/pyneuro/samples/lab-resource-manager/)** - Resource Oriented Architecture with watchers and reconciliation
- **[🖥️ Desktop Controller](https://bvandewe.github.io/pyneuro/samples/desktop_controller/)** - Remote desktop management API
- **[🚪 API Gateway](https://bvandewe.github.io/pyneuro/samples/api_gateway/)** - Microservice gateway with authentication

## 🐳 Quick Start with Docker

The fastest way to explore Neuroglia is through our sample applications with Docker:

### Prerequisites

- Docker and Docker Compose installed
- Git (to clone the repository)

### Get Started in 3 Steps

```bash
# 1. Clone the repository
git clone https://github.com/bvandewe/pyneuro.git
cd pyneuro

# 2. Start Mario's Pizzeria (includes shared infrastructure)
./mario-pizzeria start

# 3. Access the application
# 🍕 Application: http://localhost:8080
# 📖 API Docs: http://localhost:8080/api/docs
# 🔐 Keycloak: http://localhost:8090 (admin/admin)
```

### Available Sample Applications

Each sample comes with its own CLI tool for easy management:

```bash
# Mario's Pizzeria (State-based persistence + UI)
./mario-pizzeria start
./mario-pizzeria stop
./mario-pizzeria logs

# OpenBank (Event Sourcing with EventStoreDB)
./openbank start
./openbank stop
./openbank logs

# Simple UI Demo (Authentication patterns)
./simple-ui start
./simple-ui stop
./simple-ui logs
```

### Shared Infrastructure

All samples share common infrastructure services:

- **�️ MongoDB**: Database (port 27017)
- **� MongoDB Express**: Database UI (port 8081)
- **🔐 Keycloak**: Authentication (port 8090)
- **🎬 Event Player**: Event visualization (port 8085)
- **📊 Grafana**: Dashboards (port 3001)
- **📈 Prometheus**: Metrics (port 9090)
- **📝 Loki**: Logs aggregation
- **🔍 Tempo**: Distributed tracing (port 3200)

The shared infrastructure starts automatically with your first sample application.

### Service Ports

| Sample           | Port | Debug Port | Description                           |
| ---------------- | ---- | ---------- | ------------------------------------- |
| Mario's Pizzeria | 8080 | 5678       | Full-featured pizzeria management     |
| OpenBank         | 8899 | 5699       | Event-sourced banking with EventStore |
| Simple UI        | 8082 | 5680       | Authentication patterns demo          |
| EventStoreDB     | 2113 | -          | Event sourcing database (OpenBank)    |
| MongoDB Express  | 8081 | -          | Database admin UI                     |
| Keycloak         | 8090 | -          | SSO/OAuth2 server                     |
| Event Player     | 8085 | -          | CloudEvents visualization             |
| Grafana          | 3001 | -          | Observability dashboards              |
| Prometheus       | 9090 | -          | Metrics collection                    |
| Tempo            | 3200 | -          | Trace visualization                   |

### Test Credentials

The samples come with pre-configured test users:

```
Admin:    admin / admin123
Manager:  manager / manager123
Chef:     chef / chef123
Driver:   driver / driver123
Customer: customer / customer123
```

### Learn More

For detailed deployment documentation, see:

- **[🚀 Getting Started Guide](https://bvandewe.github.io/pyneuro/getting-started/)** - Complete setup walkthrough
- **[🐳 Docker Architecture](deployment/docker-compose/DOCKER_COMPOSE_ARCHITECTURE.md)** - Infrastructure details
- **[🍕 Mario's Pizzeria Tutorial](https://bvandewe.github.io/pyneuro/guides/mario-pizzeria-tutorial/)** - Step-by-step guide
- **[🏦 OpenBank Guide](https://bvandewe.github.io/pyneuro/samples/openbank/)** - Event sourcing patterns

## 🔧 Quick Start

```bash
# Install from PyPI
pip install neuroglia-python

# Or install from source
git clone <repository-url>
cd pyneuro
pip install -e .
```

Create your first application:

```python
from neuroglia.hosting.web import WebApplicationBuilder

# Create and configure the application
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])

# Build and run
app = builder.build()
app.use_controllers()
app.run()
```

## 🏗️ Framework Components

| Component                          | Purpose                               | Documentation                                             |
| ---------------------------------- | ------------------------------------- | --------------------------------------------------------- |
| **Dependency Injection**           | Service container and registration    | [📖 DI](docs/patterns/dependency-injection.md)            |
| **Hosting**                        | Web application hosting and lifecycle | [📖 Hosting](docs/features/hosting.md)                    |
| **MVC**                            | Controllers and routing               | [📖 MVC](docs/features/mvc-controllers.md)                |
| **Mediation**                      | CQRS, commands, queries, events       | [📖 CQRS](docs/patterns/cqrs.md)                          |
| **Persistence**                    | Domain events with state persistence  | [📖 Persistence](docs/patterns/persistence-patterns.md)   |
| **Pipeline Behaviors**             | Cross-cutting concerns, middleware    | [📖 Behaviors](docs/patterns/pipeline-behaviors.md)       |
| **Resource Oriented Architecture** | Watchers, controllers, reconciliation | [📖 ROA](docs/patterns/resource-oriented-architecture.md) |
| **Data**                           | Repository pattern, event sourcing    | [📖 Data](docs/features/data-access.md)                   |
| **Eventing**                       | CloudEvents, pub/sub, reactive        | [📖 Events](docs/patterns/event-driven.md)                |
| **Mapping**                        | Object-to-object mapping              | [📖 Mapping](docs/features/object-mapping.md)             |
| **Serialization**                  | JSON and other serialization          | [📖 Serialization](docs/features/serialization.md)        |
| **Observability**                  | OpenTelemetry, tracing, metrics       | [📖 Observability](docs/features/observability.md)        |

## 📋 Requirements

- Python 3.9+
- FastAPI
- Pydantic
- RxPy (for reactive features)
- Motor (for MongoDB support)
- Additional dependencies based on features used

## 🧪 Testing

Neuroglia includes a comprehensive test suite covering all framework features with both unit and integration tests.

### Running Tests

#### Run All Tests

```bash
# Run the complete test suite
pytest

# Run with coverage report
pytest --cov=neuroglia --cov-report=html --cov-report=term

# Run in parallel for faster execution
pytest -n auto
```

#### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run tests by marker
pytest -m "unit"
pytest -m "integration"
pytest -m "slow"
```

#### Run Feature-Specific Tests

```bash
# Test dependency injection
pytest tests/unit/test_dependency_injection.py

# Test CQRS and mediation
pytest tests/unit/test_cqrs_mediation.py

# Test data access layer
pytest tests/unit/test_data_access.py

# Test object mapping
pytest tests/unit/test_mapping.py

# Run integration tests
pytest tests/integration/test_full_framework.py
```

### Test Coverage

Our test suite provides comprehensive coverage of the framework:

- **Unit Tests**: >95% coverage for core framework components
- **Integration Tests**: End-to-end workflow validation
- **Performance Tests**: Load testing for critical paths
- **Sample Application Tests**: Real-world usage scenarios

### Test Organization

```text
tests/
├── unit/              # 🔬 Unit tests for individual components
├── integration/       # 🔗 Integration tests for workflows
├── fixtures/          # 🛠️ Shared test fixtures and utilities
└── conftest.py       # ⚙️ pytest configuration
```

### What's Tested

- Basic dependency injection service registration and resolution
- CQRS command and query handling through the mediator
- Object mapping between different types
- Repository pattern with various backend implementations
- Full framework integration workflows

### Test Fixtures

We provide comprehensive test fixtures for:

- Dependency injection container setup
- Sample services and repositories
- Mock data and test entities
- Configuration and settings

### Known Test Limitations

- Some dependency injection features (like strict service lifetimes) may have implementation-specific behavior
- MongoDB integration tests require a running MongoDB instance
- Event Store tests require EventStoreDB connection

### Adding Tests

When contributing, please include tests for new features:

```python
import pytest
from neuroglia.dependency_injection import ServiceCollection

class TestNewFeature:

    @pytest.mark.unit
    def test_my_unit_feature(self):
        """Test individual component"""
        result = self.service.do_something()
        assert result == expected_value
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 📖 Documentation

Complete documentation is available at [https://bvandewe.github.io/pyneuro/](https://bvandewe.github.io/pyneuro/)

## Disclaimer

This project was the opportunity for me (cdavernas) to learn Python while porting some of the concepts and services of the .NET version of the Neuroglia Framework

## Packaging

```sh
# Set `package-mode = true` in pyproject.toml
# Set the version tag in pyproject.toml
# Commit changes
# Create API Token in pypi.org...
# Configure credentials for pypi registry:
poetry config pypi-token.pypi  {pypi-....mytoken}
# Build package locally
poetry build
# Publish package to pypi.org:
poetry publish
```
