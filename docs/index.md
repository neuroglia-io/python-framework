# 🧠 Neuroglia Python Framework

> **Keywords**: Python microservices, FastAPI framework, clean architecture Python, CQRS Python, domain-driven design Python, event-driven architecture, dependency injection Python, microservices patterns

---

## ⚠️ Documentation Philosophy & Critical Disclaimer

!!! warning "Eventual Accuracy & Critical Interpretation Required"

    **This documentation is designed as an entry point for both human developers and AI agents**, serving as a conceptual toolbox rather than prescriptive instructions.

    ### 🎯 Intended Interpretation

    - **Eventual Accuracy**: Content and illustrations represent patterns and concepts that evolve with real-world usage. Expect refinement over time.
    - **No One-Size-Fits-All**: These are **patterns, not prescriptions**. Your domain, constraints, and business context will require critical adaptation.
    - **Toolbox Approach**: Consider this a collection of architectural tools and techniques. Select, combine, and adapt based on your specific use case.
    - **Critical Mindset Required**: You must evaluate each pattern's applicability to your context. What works for a banking system may be overkill for a simple API.

    ### 🏗️ Clean Architecture Starts with Business Modeling

    **Before writing code**, proper clean architecture requires:

    1. **Business Domain Understanding**: Map your business processes, entities, and rules
    2. **Ecosystem Perspective**: Identify how your microservice(s) interact within the broader system
    3. **Event-Driven Thinking**: Consider autonomous services that emit and subscribe to **persisted, queryable streams of CloudEvents**
    4. **Bounded Contexts**: Define clear boundaries for your domain models and services
    5. **Integration Patterns**: Plan for eventual consistency, event sourcing, saga patterns, or CQRS based on actual requirements

    **The framework provides the mechanisms** (CQRS, event sourcing, repositories, mediators), **but you provide the domain insight** to know when and how to apply them.

    ### 🤖 For AI Agents

    This documentation is structured to enable AI-assisted development. Use it to:

    - Understand architectural patterns and their trade-offs
    - Generate code that respects clean architecture principles
    - Suggest implementations based on documented patterns
    - Critically evaluate when patterns should (or should not) be applied
    - Adapt examples to specific business domains and constraints

    **Remember**: Even with AI assistance, human domain expertise and critical evaluation remain essential.

---

A lightweight, opinionated Python framework built on [FastAPI](https://fastapi.tiangolo.com/) that enforces clean architecture principles and provides comprehensive tooling for building production-ready microservices.

## 🎯 Perfect For

- **Microservices**: Clean architecture for scalable service development
- **Event-Driven Systems**: Built-in CloudEvents and domain event support
- **API Development**: FastAPI-based with automatic OpenAPI documentation
- **Domain-Driven Design**: Enforce DDD patterns and bounded contexts
- **Clean Code**: Opinionated structure that promotes maintainable code

---

## 🚀 Quick Start Options

### 🎯 **Option 1: Start with a Full-Featured Template**

**[📦 Starter App Repository](https://bvandewe.github.io/starter-app/)** - Clone a production-ready template and start building immediately:

```bash
git clone https://github.com/bvandewe/starter-app.git my-project
cd my-project
# Follow the setup instructions in the repo
```

**What's Included:**

- ✅ **SubApp Architecture** - REST API + Frontend separation
- ✅ **OAuth2/OIDC with RBAC** - Complete authentication and authorization
- ✅ **Clean Architecture** - DDD and CQRS patterns implemented
- ✅ **Modular Frontend** - Vanilla JS/SASS/ES6 with modern tooling
- ✅ **OpenTelemetry** - Automatic instrumentation for observability
- ✅ **Docker Compose** - Ready for local development
- ✅ **Production Patterns** - All common concerns pre-configured

**Perfect for**: Starting a new project with best practices baked in.

---

### 🎯 **Option 2: Learn from Samples**

Explore complete, production-ready sample applications to understand specific patterns.

---

### 🎯 **Option 3: Build from Scratch**

Follow the [Getting Started Guide](getting-started.md) to understand every concept step-by-step.

---

## 🚀 What's Included

### 🏗️ **Framework Core**

Clean architecture patterns with dependency injection, CQRS, event-driven design, and comprehensive testing utilities.

### 📦 **Production-Ready Sample Applications**

Learn by example with complete, runnable applications:

- **[🏦 OpenBank](samples/openbank.md)** - Event Sourcing & CQRS banking system demonstrating:

  - Complete event sourcing with KurrentDB (EventStoreDB)
  - CQRS with separate write and read models
  - Domain-driven design with rich aggregates
  - Read model reconciliation and eventual consistency
  - Snapshot strategy for performance
  - Perfect for financial systems and audit-critical applications

- **[🎨 Simple UI](samples/simple-ui.md)** - SubApp pattern with JWT authentication showing:

  - FastAPI SubApp mounting for UI/API separation
  - Stateless JWT authentication architecture
  - Role-based access control (RBAC) at application layer
  - Bootstrap 5 frontend with Parcel bundler
  - Perfect for internal dashboards and admin tools

- **[🍕 Mario's Pizzeria](mario-pizzeria.md)** - Complete e-commerce platform featuring:
  - Order management and kitchen workflows
  - Real-time event-driven processes
  - Keycloak authentication integration
  - MongoDB persistence with domain events
  - Perfect for learning all framework patterns

### �🍕 **Real-World Samples**

Complete production examples like [Mario's Pizzeria](mario-pizzeria.md) demonstrating every framework feature in realistic business scenarios.

### 📚 **Comprehensive Documentation**

- **[9-Part Tutorial Series](tutorials/index.md)** - Step-by-step hands-on learning
- **[Core Concepts Guide](concepts/index.md)** - Architectural pattern explanations
- **[Pattern Documentation](patterns/index.md)** - Includes "Common Mistakes" and "When NOT to Use"
- **[Complete Case Study](mario-pizzeria.md)** - From business analysis to production deployment

### ⚙️ **CLI Tooling**

PyNeuroctl command-line interface for managing, testing, and deploying your applications with zero configuration.

---

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

## 🚀 Quick Start

**Coming soon**: Get started with Neuroglia in minutes:

```bash
# Install the framework
pip install neuroglia-python

# Create your first app
pyneuroctl new myapp --template minimal
cd myapp

# Run the application
python main.py
```

Visit `http://localhost:8000/docs` to explore the auto-generated API documentation.

## 📚 Learn More

### 🎓 Learning Paths

**New to the Framework?**

1. Start with **[Getting Started](getting-started.md)** - Build your first app in 30 minutes
2. Follow the **[9-Part Tutorial Series](tutorials/index.md)** - Comprehensive hands-on guide
3. Study **[Core Concepts](concepts/index.md)** - Understand the architectural patterns

**Ready to Build?**

1. Explore **[Mario's Pizzeria Case Study](mario-pizzeria.md)** - Complete real-world example
2. Review **[Architectural Patterns](patterns/index.md)** - Design patterns with anti-patterns to avoid
3. Browse **[Framework Features](features/index.md)** - Detailed feature documentation

**Need Help?**

1. Check **[Guides & How-Tos](guides/index.md)** - Practical procedures and troubleshooting
2. See **[Sample Applications](samples/index.md)** - More complete working examples
3. Consult **[Reference Documentation](references/oauth-oidc-jwt.md)** - Technical specifications

### 📖 Quick Links

- **[Tutorials](tutorials/index.md)** - Step-by-step learning with the 9-part Mario's Pizzeria tutorial
- **[Sample Applications](samples/index.md)** - Complete working examples:
  - **[🏦 OpenBank](samples/openbank.md)** - Event sourcing & CQRS banking system
  - **[🎨 Simple UI](samples/simple-ui.md)** - SubApp pattern with JWT auth & RBAC
  - **[API Gateway](samples/api_gateway.md)** - Microservice orchestration
- **[Core Concepts](concepts/index.md)** - Understand Clean Architecture, DDD, CQRS, and more
- **[Mario's Pizzeria](mario-pizzeria.md)** - Complete case study with business analysis and implementation
- **[Patterns](patterns/index.md)** - Architectural patterns with "What & Why" and "Common Mistakes"
- **[Features](features/index.md)** - Framework capabilities and how to use them
- **[Guides](guides/index.md)** - Practical how-to procedures
  - **[RBAC & Authorization](guides/rbac-authorization.md)** - Role-based access control patterns
  - **[Simple UI Development](guides/simple-ui-app.md)** - Step-by-step UI integration guide

### 📖 Reference Documentation

- **[OAuth, OIDC & JWT](references/oauth-oidc-jwt.md)** - Authentication and authorization patterns
- **[12-Factor App Compliance](references/12-factor-app.md)** - Cloud-native application standards
- **[Source Code Naming Conventions](references/source_code_naming_convention.md)** - Maintainable code patterns
- **[Python Typing Guide](references/python_typing_guide.md)** - Type hints, generics, and advanced typing

---

_Neuroglia Python Framework - Building better software through better architecture_ 🧠✨
