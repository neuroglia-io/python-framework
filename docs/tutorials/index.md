# 📖 Tutorials

Learn Neuroglia by building real applications step-by-step.

## 🍕 Mario's Pizzeria - Complete Tutorial Series

Build a production-ready pizza ordering system from scratch. This comprehensive 9-part tutorial teaches you everything you need to know about building applications with Neuroglia.

**What You'll Build**: A complete pizza ordering and management system with:

- REST API with CRUD operations
- Clean architecture with proper layer separation
- CQRS pattern for commands and queries
- Event-driven features with domain events
- MongoDB persistence with repository pattern
- OAuth2 authentication with Keycloak
- Distributed tracing with OpenTelemetry
- Docker deployment

**Prerequisites**: Complete the [Getting Started](../getting-started.md) guide first to understand the basics.

---

### Tutorial Parts

#### Part 1: Project Setup & Structure

**Learn**: Project organization, dependency injection, application bootstrapping

[→ Start Part 1: Project Setup](mario-pizzeria-01-setup.md)

---

#### Part 2: Domain Model

**Learn**: Domain-Driven Design, entities, value objects, business rules

[→ Continue to Part 2: Domain Model](mario-pizzeria-02-domain.md)

---

#### Part 3: Commands & Queries (CQRS)

**Learn**: CQRS pattern, command handlers, query handlers, mediator

[→ Continue to Part 3: CQRS](mario-pizzeria-03-cqrs.md)

---

#### Part 4: API Controllers

**Learn**: REST APIs, FastAPI integration, DTOs, request/response handling

[→ Continue to Part 4: API Controllers](mario-pizzeria-04-api.md)

---

#### Part 5: Events & Integration

**Learn**: Domain events, event handlers, event-driven architecture

[→ Continue to Part 5: Events](mario-pizzeria-05-events.md)

---

#### Part 6: Persistence & Repositories

**Learn**: Repository pattern, MongoDB integration, data access layer

[→ Continue to Part 6: Persistence](mario-pizzeria-06-persistence.md)

---

#### Part 7: Authentication & Authorization

**Learn**: OAuth2, Keycloak integration, JWT tokens, role-based access

[→ Continue to Part 7: Authentication](mario-pizzeria-07-auth.md)

---

#### Part 8: Observability

**Learn**: OpenTelemetry, distributed tracing, metrics, structured logging

[→ Continue to Part 8: Observability](mario-pizzeria-08-observability.md)

---

#### Part 9: Deployment

**Learn**: Docker containers, docker-compose, production configuration

[→ Continue to Part 9: Deployment](mario-pizzeria-09-deployment.md)

---

## 📚 What You'll Learn

### Architecture & Design

- **Clean Architecture** - Layer separation and dependency rules
- **Domain-Driven Design** - Rich domain models with business logic
- **CQRS** - Command Query Responsibility Segregation
- **Event-Driven Architecture** - Domain events and eventual consistency

### Framework Features

- **Dependency Injection** - Service registration and lifetime management
- **Mediator Pattern** - Decoupled request handling
- **Repository Pattern** - Abstract data access
- **Pipeline Behaviors** - Cross-cutting concerns

### Infrastructure

- **MongoDB** - Document database integration
- **Keycloak** - Authentication and authorization
- **OpenTelemetry** - Observability and monitoring
- **Docker** - Containerization and deployment

---

## 🎯 Learning Path

### Recommended Order

1. **[Getting Started](../getting-started.md)** - Understand the basics (30 min)
2. **Tutorial Parts 1-3** - Core architecture and patterns (4 hours)
3. **Tutorial Parts 4-6** - API and persistence (4 hours)
4. **Tutorial Parts 7-9** - Security and deployment (4 hours)

### Alternative Paths

**Already know Clean Architecture?**
→ Skip to [Part 3: CQRS](mario-pizzeria-03-cqrs.md)

**Just want to see the code?**
→ Check the [complete sample](https://github.com/bvandewe/pyneuro/tree/main/samples/mario-pizzeria)

**Need specific features?**
→ Jump to relevant parts (each part is self-contained)

---

## 💡 Tips for Success

1. **Code along** - Type the examples yourself, don't just read
2. **Experiment** - Modify the code and see what happens
3. **Take breaks** - Each part takes ~1-2 hours, pace yourself
4. **Use Git** - Commit after each part to track progress
5. **Ask questions** - Open issues if something isn't clear

---

## 🚀 Ready to Start?

Begin with [Part 1: Project Setup](mario-pizzeria-01-setup.md) to create your Mario's Pizzeria application!

Already completed the tutorial? Check out:

- **[Feature Documentation](../features/index.md)** - Deep dive into framework features
- **[Architecture Patterns](../patterns/index.md)** - Design pattern explanations
- **[Sample Applications](../samples/index.md)** - More examples
