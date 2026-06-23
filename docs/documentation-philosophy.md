# 📖 Documentation Philosophy & Usage Guide

## ⚠️ Critical Disclaimer: Eventual Accuracy & Interpretation

!!! warning "This Documentation Requires Critical Thinking"

    **This documentation is NOT a prescriptive manual.** It is designed as an entry point and reference for both **human developers** and **AI agents**, serving as a **conceptual toolbox** of architectural patterns, not rigid instructions.

## 🎯 How to Use This Documentation

### For Human Developers

This documentation presents **patterns, principles, and practical examples** that have proven useful across various microservices architectures. However:

- **Context Matters**: What works brilliantly for a financial trading system may be unnecessary overhead for a simple API
- **Trade-offs Exist**: Every architectural decision involves trade-offs between complexity, maintainability, performance, and development speed
- **You Decide**: Use your domain knowledge and business context to determine which patterns apply to your situation
- **Adapt, Don't Copy**: Treat examples as starting points for adaptation, not templates for blind copying

### For AI Agents

This documentation is structured to enable AI-assisted development with proper architectural guardrails:

- **Pattern Recognition**: Understand the "what" and "why" of architectural patterns
- **Context-Aware Suggestions**: Generate code that respects clean architecture principles while adapting to specific domains
- **Trade-off Analysis**: Help developers evaluate when patterns should (or should not) be applied
- **Domain Adaptation**: Transform generic patterns into domain-specific implementations
- **Critical Evaluation**: Question and validate architectural decisions rather than blindly applying patterns

**Remember**: Even with AI assistance, human domain expertise, business understanding, and critical evaluation remain essential for successful software architecture.

---

## 🏗️ Clean Architecture Starts with Business Modeling

!!! info "Architecture Before Implementation"

    **Code is the last step**, not the first. Clean architecture begins with understanding your business domain and ecosystem.

### 1. **Business Domain Understanding**

Before opening your IDE:

- Map business processes and workflows
- Identify core domain entities and their relationships
- Understand business rules and invariants
- Define ubiquitous language with stakeholders
- Identify bounded contexts and domain boundaries

**Question to ask**: _What problem are we actually solving, and for whom?_

### 2. **Ecosystem Perspective**

Your microservice doesn't exist in isolation:

- How does it interact with other services?
- What external systems does it integrate with?
- What are the failure modes and cascade effects?
- How do we handle eventual consistency?
- What are the communication patterns (sync, async, event-driven)?

**Question to ask**: _How does this service fit into the larger system landscape?_

### 3. **Event-Driven Thinking**

Modern microservices architectures thrive on autonomy and decoupling:

- Services emit **domain events** when important business actions occur
- Services subscribe to events they care about from other services
- Events are persisted in **queryable streams** (CloudEvents specification recommended)
- Event streams become the source of truth for system state
- Services remain autonomous and loosely coupled

**Question to ask**: _What business events does this service emit, and what events does it need to react to?_

### 4. **Bounded Contexts & Integration**

Clear boundaries prevent coupling and enable independent evolution:

- Each service owns its domain model within its bounded context
- Services communicate through well-defined contracts (events, APIs)
- Shared concepts are explicitly translated at boundaries
- Anti-corruption layers protect core domain models
- Integration patterns (saga, CQRS, event sourcing) are chosen based on requirements

**Question to ask**: _What are our service boundaries, and how do we maintain them?_

---

## 🛠️ The Framework as a Toolbox

!!! tip "Tools, Not Rules"

    Neuroglia provides **mechanisms**, not mandates. You provide the **domain insight** to know when and how to apply them.

### What the Framework Provides

| **Mechanism**                         | **Use When**                                                                 | **Skip When**                                       |
| ------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------- |
| **CQRS (Command/Query Separation)**   | Complex business logic, different read/write needs                           | Simple CRUD operations                              |
| **Event Sourcing**                    | Audit requirements, temporal queries, complex state reconstruction           | Simple state management suffices                    |
| **Domain Events**                     | Decoupled workflows, integration with other services                         | Single-service, linear workflows                    |
| **Repository Pattern**                | Multiple data sources, testability, domain isolation                         | Direct database access is simpler                   |
| **Mediator Pattern**                  | Cross-cutting concerns, pipeline behaviors, request/response decoupling      | Tight coupling between controller and logic is fine |
| **Resource-Oriented Architecture**    | Kubernetes-style resource management, declarative reconciliation             | Traditional request/response suffices               |
| **CloudEvents**                       | Event interoperability, standardized event schemas across services           | Internal events within a single service             |
| **Background Task Scheduler (Redis)** | Distributed task processing, scheduled jobs across instances                 | Single-instance in-memory tasks suffice             |
| **OpenTelemetry Observability**       | Production systems, debugging distributed traces, performance monitoring     | Local development or simple scripts                 |
| **Dependency Injection**              | Testability, flexibility, complex dependency graphs                          | Simple scripts with few dependencies                |
| **Validation (Business Rules)**       | Complex domain validation, reusable rules across handlers                    | Simple input validation with Pydantic               |
| **Reactive Programming (RxPy)**       | Complex async data streams, event transformation pipelines                   | Simple async/await patterns suffice                 |
| **State Machines**                    | Complex state transitions with multiple possible paths                       | Simple status enums suffice                         |
| **Aggregate Roots**                   | Transactional consistency boundaries, complex invariants spanning entities   | Simple entities without complex relationships       |
| **Read Models (Projections)**         | Optimized queries, denormalized views, eventual consistency acceptable       | Direct querying of write model is sufficient        |
| **Pipeline Behaviors**                | Logging, validation, caching, transaction management across many handlers    | Handler-specific logic                              |
| **Value Objects**                     | Domain concepts with validation rules, immutability requirements             | Simple primitive types suffice                      |
| **Anti-Corruption Layer**             | Protecting domain from external APIs, legacy system integration              | Direct integration with well-designed external APIs |
| **Saga Pattern**                      | Distributed transactions, multi-service workflows with compensation          | Single-service atomic transactions                  |
| **Mapper (DTOs)**                     | API/domain separation, versioning, security (hiding internal structure)      | Domain objects can be safely exposed                |
| **SubApp Pattern**                    | UI/API separation, different middleware for different routes                 | Single monolithic app structure                     |
| **Hosted Services**                   | Background processing, scheduled tasks, health checks                        | Request-scoped operations only                      |
| **Type Registry & Discovery**         | Dynamic handler registration, plugin architectures                           | Static, explicitly registered types                 |
| **HTTP Service Client**               | Resilient external API calls with retries, circuit breakers                  | Simple HTTP requests without resilience needs       |
| **Async Cache Repository**            | Distributed caching with Redis, cross-instance cache consistency             | In-memory caching or no caching needed              |
| **CloudEvent Middleware**             | FastAPI middleware for cloud event ingestion and transformation              | Standard FastAPI middleware suffices                |
| **Role-Based Access Control (RBAC)**  | Complex permission systems, authorization at application layer               | Simple authentication suffices                      |
| **Flexible Repository (Queryable)**   | LINQ-style query composition, dynamic filtering                              | Simple repository methods suffice                   |
| **Snapshot Strategy**                 | Event sourcing with many events, performance optimization for aggregate load | Full event replay is fast enough                    |
| **Resource Watchers**                 | React to resource changes, trigger reconciliation loops                      | Polling or direct updates suffice                   |
| **Configuration Management**          | 12-factor app compliance, environment-specific settings                      | Hardcoded configuration is acceptable               |
| **JSON Serialization (Custom Types)** | Enums, decimals, datetime, UUID handling in APIs                             | Default JSON serialization works                    |
| **Case Conversion (CamelModel)**      | API compatibility (camelCase) with Python conventions (snake_case)           | Single naming convention throughout                 |
| **Queryable Providers**               | Abstracting query languages (MongoDB, SQL, etc.) with common interface       | Direct database queries                             |
| **Resource Controllers**              | Kubernetes-style reconciliation loops, desired vs actual state management    | Traditional request/response controllers            |

### The Illusion of "One-Size-Fits-All"

There is **no universal architecture** that works for every use case. Neuroglia acknowledges this by:

- Providing **optional** patterns you can adopt incrementally
- Documenting **trade-offs** so you understand costs and benefits
- Including **"When NOT to Use"** sections in pattern documentation
- Encouraging **critical evaluation** rather than blind adoption

**Your responsibility**: Understand your domain, evaluate your constraints, and choose patterns that align with your specific context.

---

## 🔄 Eventual Accuracy & Living Documentation

!!! note "Documentation as a Work in Progress"

    This documentation evolves as the framework matures and real-world usage reveals better patterns.

### What "Eventual Accuracy" Means

- **Content Refinement**: Examples, patterns, and explanations improve over time based on feedback and usage
- **Conceptual Stability**: Core architectural principles remain consistent, but their presentation evolves
- **Illustration Evolution**: Diagrams, code samples, and tutorials are updated to reflect best practices
- **Known Gaps**: Some areas are better documented than others; contributions and feedback are welcome

### How to Provide Feedback

If you find:

- **Inaccuracies**: Content that doesn't match reality or leads to incorrect implementations
- **Ambiguities**: Explanations that are unclear or could be misinterpreted
- **Missing Context**: Patterns presented without sufficient "when to use" guidance
- **Outdated Examples**: Code samples that don't align with current framework features

Please contribute via:

- GitHub Issues: Report documentation bugs or request clarifications
- Pull Requests: Propose improvements or corrections
- Discussions: Share real-world experiences and lessons learned

---

## 🎯 Quick Start Options

Before diving into learning, choose your starting approach:

### 🏃 **Option 1: Production Template (Recommended for Teams)**

**[Starter App Repository](https://bvandewe.github.io/starter-app/)** - Start with a complete, production-ready template:

- **What**: Fully-configured application demonstrating all framework capabilities
- **Includes**: SubApp architecture, OAuth2/OIDC, RBAC, clean architecture, modular frontend, OTEL
- **Best For**: Teams building production applications who want proven patterns out-of-the-box
- **Approach**: Clone, configure, and customize to your domain

```bash
git clone https://github.com/bvandewe/starter-app.git my-project
cd my-project
# Follow setup instructions
```

### 📚 **Option 2: Learning Path (Recommended for Individuals)**

- **What**: Step-by-step tutorials and sample applications
- **Includes**: Mario's Pizzeria, OpenBank, Simple UI samples with detailed guides
- **Best For**: Developers learning clean architecture and DDD patterns
- **Approach**: Read docs, explore samples, build understanding incrementally

### 🔧 **Option 3: Minimal Bootstrap**

- **What**: Bare-bones setup to understand core concepts
- **Includes**: [3-Minute Bootstrap](guides/3-min-bootstrap.md) and minimal examples
- **Best For**: Experienced developers who want minimal scaffolding
- **Approach**: Start small, add complexity as needed

---

## 🎓 Recommended Learning Pathways

### For Beginners

### You're Building a Simple REST API

**Start Here**:

1. [Getting Started](getting-started.md) - Basic setup
2. [MVC Controllers](features/mvc-controllers.md) - API endpoints
3. [Simple CQRS](features/simple-cqrs.md) - Basic command/query pattern

**Skip Initially**: Event sourcing, complex domain models, resource-oriented architecture

---

### You're Building a Complex Domain-Driven System

**Start Here**:

1. [Clean Architecture](patterns/clean-architecture.md) - Foundational principles
2. [Domain-Driven Design](patterns/domain-driven-design.md) - Strategic and tactical patterns
3. [CQRS Pattern](patterns/cqrs.md) - Command/Query separation
4. [Mario's Pizzeria Tutorial](tutorials/index.md) - Complete walkthrough

**Explore Next**: Event sourcing, domain events, aggregate roots, bounded contexts

---

### You're Building Event-Driven Microservices

**Start Here**:

1. [Event-Driven Architecture](patterns/event-driven.md) - Core concepts
2. [OpenBank Sample](samples/openbank.md) - Event sourcing example
3. [CloudEvents](features/observability.md) - Event standardization
4. [Background Task Scheduler](features/background-task-scheduling.md) - Distributed processing

**Explore Next**: Saga patterns, eventual consistency, read model projections

---

### You're Building Internal Tools or Admin Dashboards

**Start Here**:

1. [Simple UI Sample](samples/simple-ui.md) - SubApp pattern with authentication
2. [RBAC & Authorization](guides/rbac-authorization.md) - Role-based access control
3. [OpenTelemetry Integration](guides/opentelemetry-integration.md) - Observability

**Skip Initially**: Event sourcing, complex domain models, distributed transactions

---

## 🤝 AI-Assisted Development Principles

!!! info "Human-AI Collaboration"

    This documentation is structured to enable effective collaboration between human developers and AI agents.

### For AI Agents: Effective Pattern Application

When assisting with development using Neuroglia:

1. **Understand Context First**: Ask about the business domain, requirements, and constraints before suggesting patterns
2. **Evaluate Trade-offs**: Present options with their pros and cons rather than prescribing a single solution
3. **Start Simple**: Suggest simpler patterns initially; complex patterns can be introduced incrementally
4. **Domain-Specific Adaptation**: Transform generic examples into domain-specific implementations
5. **Test Coverage**: Always include test cases for generated code
6. **Documentation Alignment**: Ensure suggestions follow documented patterns and naming conventions

### Critical Questions AI Agents Should Ask

Before suggesting CQRS:

- Does this operation have complex business logic or simple CRUD?
- Are read and write needs significantly different?

Before suggesting Event Sourcing:

- Are there audit requirements or temporal query needs?
- Is the complexity of event sourcing justified?

Before suggesting Microservices:

- Can this be a modular monolith initially?
- What are the operational capabilities of the team?

Before suggesting Domain Events:

- Is there a need for decoupled workflows or integrations?
- Would a direct method call be simpler?

### Human Developer Responsibility

Even with AI assistance:

- **Validate Suggestions**: AI can generate valid code that doesn't solve your actual problem
- **Provide Context**: The more context you provide, the better the AI suggestions
- **Think Critically**: AI doesn't understand your business constraints, technical debt, or team capabilities
- **Review and Adapt**: AI-generated code should be reviewed, tested, and adapted to your specific needs

---

## 📊 Architecture Decision Records (Recommended)

!!! tip "Document Your Decisions"

    For any non-trivial project, maintain Architecture Decision Records (ADRs) explaining **why** you chose specific patterns.

Example ADR template:

```markdown
# ADR-001: Use CQRS for Order Management

## Status

Accepted

## Context

Our order management system has complex business rules for write operations
(pricing, inventory, discounts) but simple read requirements (list orders).

## Decision

We will use CQRS to separate write and read models.

## Consequences

**Positive**:

- Simplified read model optimized for queries
- Write model focuses on business rules
- Independent scaling of read/write paths

**Negative**:

- Increased complexity
- Eventual consistency between read/write
- More code to maintain

## Alternatives Considered

- Simple CRUD: Rejected due to complex write logic
- Event Sourcing: Overkill for current requirements
```

---

## 🎯 Summary: How to Use Neuroglia Successfully

1. **Understand Your Domain** before choosing patterns
2. **Start Simple**, add complexity only when justified
3. **Evaluate Trade-offs** - no pattern is universally good
4. **Adapt Examples** to your specific context
5. **Question Everything** - including this documentation
6. **Document Decisions** so future maintainers understand the "why"
7. **Collaborate with AI** but maintain critical thinking
8. **Contribute Back** - share learnings and improve documentation

**Neuroglia is a toolbox, not a rulebook. Use it wisely.** 🧠✨

---

_"The map is not the territory, and the documentation is not the system. Use critical thinking always."_
