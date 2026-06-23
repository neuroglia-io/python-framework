# 🎯 Architecture Patterns & Core Concepts

Welcome to architecture patterns! This section explains the patterns and principles that Neuroglia is built upon. Each pattern is explained for **beginners** - you don't need prior knowledge.

> **📖 Note**: Pattern documentation includes beginner-friendly **What & Why** sections showing problems and solutions, **Common Mistakes** with anti-patterns, and **When NOT to Use** guidance.

## 🎯 Why These Patterns?

Neuroglia enforces specific architectural patterns because they solve **real problems** in software development:

- **Maintainability**: Code that's easy to change as requirements evolve
- **Testability**: Components that can be tested in isolation
- **Scalability**: Architecture that grows with your application
- **Clarity**: Clear separation of concerns and responsibilities

## � Quick Start Learning Path

**New to these patterns?** Follow this recommended path:

1. **Foundation**: [Clean Architecture](clean-architecture.md) - Organizing code in layers
2. **Dependencies**: [Dependency Injection](dependency-injection.md) - Managing components
3. **Domain Logic**: [Domain-Driven Design](domain-driven-design.md) - Modeling business rules
4. **Application Layer**: [CQRS](cqrs.md) - Separating reads from writes
5. **Integration**: [Event-Driven Architecture](event-driven.md) - Reacting to events
6. **Data Access**: [Repository](repository.md) - Abstracting persistence

**Already familiar?** Jump to any pattern for Neuroglia-specific implementation details.

## 💡 What Each Guide Includes

- ❌ **The Problem**: What happens without this pattern
- ✅ **The Solution**: How the pattern solves it
- 🔧 **In Neuroglia**: Framework implementation details
- 🧪 **Testing**: How to test code using this pattern
- ⚠️ **Common Mistakes**: Pitfalls to avoid
- 🚫 **When NOT to Use**: Scenarios where simpler approaches work better

## 🏗️ Architectural Approaches: A Comparative Introduction

Before diving into specific patterns, it's essential to understand the different architectural philosophies that drive modern system design. The Neuroglia framework draws from multiple architectural approaches, each with distinct strengths and use cases.

### 🎯 Core Philosophy Comparison

**Domain-Driven Design (DDD)** and **Declarative Resource-Oriented Architecture** represent two powerful but different approaches to managing complex system states:

- **DDD**: Models systems around business domains, focusing on _behavior_ and _state transitions_
- **Declarative Architecture**: Defines _desired end states_ and uses automated processes to achieve them

### 🔄 Architectural Patterns Overview

| Architecture                         | Core Philosophy                                                                          | Primary Actor                                                                                         | Unit of Work                                                                   | Source of Truth                                                           | Flow of Logic                                                                                                                         | Error Handling                                                                  | Typical Domain                                                                 |
| ------------------------------------ | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **🏛️ Domain-Driven Design**          | Model around business domain with **AggregateRoot** as guardian enforcing business rules | **Imperative Command**: User/system issues explicit commands (`AddToppingToPizza`)                    | **Aggregate**: Boundary around business objects with atomic transactions       | **Application Database**: Current aggregate state in database             | **Synchronous & Explicit**: `CommandHandler` → `Repository.Get()` → `Aggregate.Method()` → `Repository.Update()`                      | **Throws Exceptions**: Business rule violations cause immediate failures        | **Complex Business Logic**: E-commerce, banking, booking systems               |
| **🌐 Declarative Resource-Oriented** | Define **desired state** and let automated processes achieve it                          | **Declarative Reconciliation**: Automated **Controller** continuously matches actual to desired state | **Resource**: Self-contained state declaration (e.g., Kubernetes Pod manifest) | **Declarative Manifest**: Configuration file (YAML) defines desired state | **Asynchronous & Looping**: `Watcher` detects change → `Controller` triggers → **Reconciliation Loop** → `Client.UpdateActualState()` | **Retries and Converges**: Failed operations retry in next reconciliation cycle | **Infrastructure & Systems Management**: Kubernetes, Terraform, CloudFormation |

### 🎨 Practical Analogies

- **DDD** is like **giving a chef specific recipe instructions**: "Add 20g of cheese to the pizza" - explicit commands executed immediately
- **Declarative Architecture** is like **giving the chef a photograph of the final pizza**: "Make it look like this" - continuous checking and adjustment until the goal is achieved

### 📡 Event-Driven Architecture: The Foundation

**Event-Driven Architecture (EDA)** serves as the **postal service** 📬 of your system - a foundational pattern enabling reactive communication without tight coupling between components.

#### 🏛️ EDA in Domain-Driven Design

In DDD, EDA handles **side effects** and communication between different business domains (Bounded Contexts):

- **Purpose**: Reacting to **significant business moments**
- **Mechanism**: `AggregateRoot` publishes **`DomainEvents`** (e.g., `OrderPaid`, `PizzaBaked`)
- **Benefit**: Highly decoupled systems where services don't need direct knowledge of each other

**Example**: `Orders` service publishes `OrderPaid` → `Kitchen` service receives event and starts pizza preparation

#### 🌐 EDA in Declarative Architecture

In declarative systems, EDA powers the **reconciliation loop**:

- **Purpose**: Reacting to **changes in configuration or state**
- **Mechanism**: **Watcher** monitors resources → generates events → **Controller** consumes events and reconciles state
- **Benefit**: Automated state management with continuous convergence toward desired state

**Example**: YAML file creates `Deployment` → API server generates "resource created" event → Deployment controller creates required pods

### 🔄 Integration Summary

| Architecture                    | How it uses Event-Driven Architecture (EDA)                                                                                          |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **🏛️ Domain-Driven Design**     | Uses **Domain Events** to announce significant business actions, triggering workflows in decoupled business domains                  |
| **🌐 Declarative Architecture** | Uses **State Change Events** (from watchers) to trigger controller reconciliation loops, ensuring actual state matches desired state |

### 🎯 Choosing Your Approach

Both patterns leverage EDA for reactive, decoupled systems but differ in **event nature and granularity**:

- **DDD**: Focus on high-level business events with rich domain behavior
- **Declarative**: Focus on low-level resource state changes with automated convergence

The Neuroglia framework provides implementations for both approaches, allowing you to choose the right pattern for each part of your system.

## �🏛️ Pattern Overview

| Pattern                                                                          | Purpose                                                                                          | Key Concepts                                                                                                                                                                          | What You'll Learn                                                                                                                                                          | Mario's Pizzeria Use Case                                                 | When to Use                                  |
| -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------- |
| **[🏗️ Clean Architecture](clean-architecture.md)**                               | Foundation pattern that organizes code into layers with clear dependency rules                   | • Domain-driven layer separation<br/>• Dependency inversion principle<br/>• Business logic isolation<br/>• Infrastructure abstraction                                                 | • Four-layer architecture implementation<br/>• Dependency flow and injection patterns<br/>• Domain entity design with business logic<br/>• Integration layer abstraction   | Order processing across API, Application, Domain, and Integration layers  | All applications - structural foundation     |
| **[🏛️ Domain Driven Design](domain-driven-design.md)**                           | Core domain abstractions and patterns for rich business models with event-driven capabilities    | • Rich domain entities with business logic<br/>• Aggregate roots and consistency boundaries<br/>• Domain events and integration events<br/>• Event sourcing vs traditional approaches | • Entity and aggregate root implementation<br/>• Domain event design and handling<br/>• Transaction flows with multiple events<br/>• Data flow across architectural layers | Pizza orders with business rules, events, and cross-layer data flow       | Complex business domains, rich models        |
| **[🏛️ Persistence Patterns](persistence-patterns.md)**                           | Alternative persistence approaches with different complexity levels and capabilities             | • Simple Entity + State Persistence<br/>• Complex AggregateRoot + Event Sourcing<br/>• Hybrid approaches<br/>• Pattern decision frameworks                                            | • Complexity level comparison<br/>• Implementation patterns for each approach<br/>• Decision criteria and guidelines<br/>• Migration strategies between patterns           | Customer profiles (simple) vs Order processing (complex) patterns         | All applications - choose right complexity   |
| **[🔄 Unit of Work Pattern](unit-of-work.md)**                                   | Coordination layer for domain event collection and dispatching across persistence patterns       | • Aggregate registration and tracking<br/>• Automatic event collection<br/>• Pipeline integration<br/>• Flexible entity support                                                       | • UnitOfWork implementation and usage<br/>• Event coordination patterns<br/>• Pipeline behavior integration<br/>• Testing strategies for event workflows                   | Order processing with automatic event dispatching after state persistence | Event-driven systems, domain coordination    |
| **[� Pipeline Behaviors](pipeline-behaviors.md)**                                | Cross-cutting concerns implemented as composable behaviors around command/query execution        | • Decorator pattern implementation<br/>• Behavior chaining and ordering<br/>• Cross-cutting concerns<br/>• Pre/post processing logic                                                  | • Creating custom pipeline behaviors<br/>• Behavior registration and ordering<br/>• Validation, logging, caching patterns<br/>• Transaction and error handling             | Validation, logging, and transaction management around order processing   | Cross-cutting concerns, AOP patterns         |
| **[�💉 Dependency Injection](dependency-injection.md)**                          | Manages object dependencies and lifecycle through inversion of control patterns                  | • Service registration and resolution<br/>• Lifetime management patterns<br/>• Constructor injection<br/>• Interface-based abstractions                                               | • Service container configuration<br/>• Lifetime scope patterns<br/>• Testing with mock dependencies<br/>• Clean dependency management                                     | PizzeriaService dependencies managed through DI container                 | Complex dependency graphs, testability       |
| **[📡 CQRS & Mediation](cqrs.md)**                                               | Separates read/write operations with mediator pattern for decoupled request handling             | • Command/Query separation<br/>• Mediator request routing<br/>• Pipeline behaviors<br/>• Handler-based processing                                                                     | • Command and query handler implementation<br/>• Mediation pattern usage<br/>• Cross-cutting concerns via behaviors<br/>• Event integration with CQRS                      | PlaceOrderCommand vs GetOrderQuery with mediator routing                  | Complex business logic, high-scale systems   |
| **[🔄 Event-Driven Architecture](event-driven.md)**                              | Implements reactive systems using domain events and event handlers                               | • Domain event patterns<br/>• Event handlers and workflows<br/>• Asynchronous processing<br/>• System decoupling                                                                      | • Domain event design and publishing<br/>• Event handler implementation<br/>• Kitchen workflow automation<br/>• CloudEvents integration                                    | OrderPlaced → Kitchen processing → OrderReady → Customer notification     | Loose coupling, reactive workflows           |
| **[🎯 Event Sourcing](event-sourcing.md)**                                       | Stores state changes as immutable events for complete audit trails and temporal queries          | • Event-based persistence<br/>• Aggregate state reconstruction<br/>• Temporal queries<br/>• Event replay capabilities                                                                 | • Event-sourced aggregate design<br/>• Event store integration<br/>• Read model projections<br/>• Business intelligence from events                                        | Order lifecycle tracked through immutable events with full history        | Audit requirements, temporal analysis        |
| **[🌊 Reactive Programming](reactive-programming.md)**                           | Enables asynchronous event-driven architectures using Observable streams                         | • Observable stream patterns<br/>• Asynchronous event processing<br/>• Stream transformations<br/>• Background service integration                                                    | • RxPY integration patterns<br/>• Stream processing and subscription<br/>• Real-time data flows<br/>• Background service implementation                                    | Real-time order tracking and kitchen capacity monitoring                  | Real-time systems, high-throughput events    |
| **[💾 Repository Pattern](repository.md)**                                       | Abstracts data access logic with multiple storage implementations                                | • Data access abstraction<br/>• Storage implementation flexibility<br/>• Consistent query interfaces<br/>• Testing with mock repositories                                             | • Repository interface design<br/>• Multiple storage backend implementation<br/>• Async data access patterns<br/>• Repository testing strategies                           | OrderRepository with File, MongoDB, and InMemory implementations          | Data persistence, testability                |
| **[🌐 Resource-Oriented Architecture](resource-oriented-architecture.md)**       | Resource-oriented design principles for building RESTful APIs and resource-centric applications  | • Resource identification and modeling<br/>• RESTful API design principles<br/>• HTTP verb mapping and semantics<br/>• Resource lifecycle management                                  | • Resource-oriented design principles<br/>• RESTful API architecture patterns<br/>• HTTP protocol integration<br/>• Resource state management                              | Orders, Menu, Kitchen as REST resources with full CRUD operations         | RESTful APIs, microservices                  |
| **[👀 Watcher & Reconciliation Patterns](watcher-reconciliation-patterns.md)**   | Kubernetes-inspired patterns for watching resource changes and implementing reconciliation loops | • Resource state observation<br/>• Reconciliation loop patterns<br/>• Event-driven state management<br/>• Declarative resource management                                             | • Resource watching implementation<br/>• Reconciliation loop design<br/>• Event-driven update patterns<br/>• State synchronization strategies                              | Kitchen capacity monitoring and order queue reconciliation                | Reactive systems, state synchronization      |
| **[⚡ Watcher & Reconciliation Execution](watcher-reconciliation-execution.md)** | Execution engine for watcher and reconciliation patterns with error handling and monitoring      | • Execution orchestration<br/>• Error handling and recovery<br/>• Performance monitoring<br/>• Reliable state persistence                                                             | • Execution pipeline design<br/>• Error handling strategies<br/>• Monitoring and observability<br/>• Performance optimization                                              | Automated kitchen workflow execution with retry logic and monitoring      | Production systems, reliability requirements |

## 🍕 Mario's Pizzeria: Unified Example

All patterns use **Mario's Pizzeria** as a consistent domain example, showing how patterns work together in a real-world system:

```mermaid
graph TB
    subgraph "🏗️ Clean Architecture Layers"
        API[🌐 API Layer<br/>Controllers & DTOs]
        APP[💼 Application Layer<br/>Commands & Queries]
        DOM[🏛️ Domain Layer<br/>Entities & Events]
        INT[🔌 Integration Layer<br/>Repositories & Services]
    end

    subgraph "📡 CQRS Implementation"
        CMD[Commands<br/>PlaceOrder, StartCooking]
        QRY[Queries<br/>GetOrder, GetMenu]
    end

    subgraph "🔄 Event-Driven Flow"
        EVT[Domain Events<br/>OrderPlaced, OrderReady]
        HDL[Event Handlers<br/>Kitchen, Notifications]
    end

    subgraph "💾 Data Access"
        REPO[Repositories<br/>Order, Menu, Customer]
        STOR[Storage<br/>File, MongoDB, Memory]
    end

    API --> APP
    APP --> DOM
    APP --> INT

    APP --> CMD
    APP --> QRY

    DOM --> EVT
    EVT --> HDL

    INT --> REPO
    REPO --> STOR

    style API fill:#e3f2fd
    style APP fill:#f3e5f5
    style DOM fill:#e8f5e8
    style INT fill:#fff3e0
```

## 🚀 Pattern Integration

### How Patterns Work Together

| Order | Pattern                      | Role in System                 | Dependencies                 | Integration Points                                |
| ----- | ---------------------------- | ------------------------------ | ---------------------------- | ------------------------------------------------- |
| 1     | **Clean Architecture**       | Structural foundation          | None                         | Provides layer structure for all other patterns   |
| 2     | **Dependency Injection**     | Service management foundation  | Clean Architecture           | Manages service lifetimes across all layers       |
| 3     | **CQRS & Mediation**         | Application layer organization | Clean Architecture, DI       | Commands/Queries with mediator routing            |
| 4     | **Event-Driven**             | Reactive domain workflows      | Clean Architecture, CQRS, DI | Domain events published by command handlers       |
| 5     | **Event Sourcing**           | Event-based persistence        | Event-Driven, Repository, DI | Events as source of truth with aggregate patterns |
| 6     | **Reactive Programming**     | Asynchronous stream processing | Event-Driven, DI             | Observable streams for real-time event processing |
| 7     | **Repository**               | Infrastructure abstraction     | Clean Architecture, DI       | Implements Integration layer data access          |
| 8     | **Resource-Oriented**        | API contract definition        | Clean Architecture, CQRS, DI | REST endpoints expose commands/queries            |
| 9     | **Watcher & Reconciliation** | Reactive resource management   | Event-Driven, Repository, DI | Observes events, updates via repositories         |

### Implementation Order

```mermaid
flowchart LR
    A[1. Clean Architecture<br/>🏗️ Layer Structure] --> B[2. Dependency Injection<br/>💉 Service Management]
    B --> C[3. CQRS & Mediation<br/>📡 Commands & Queries]
    C --> D[4. Event-Driven<br/>🔄 Domain Events]
    D --> E[5. Event Sourcing<br/>🎯 Event Persistence]
    E --> F[6. Reactive Programming<br/>🌊 Stream Processing]
    F --> G[7. Repository Pattern<br/>💾 Data Access]
    G --> H[8. Resource-Oriented<br/>🌐 API Design]
    H --> I[9. Watcher Patterns<br/>👀 Reactive Management]

    style A fill:#e8f5e8
    style B fill:#f8bbd9
    style C fill:#e3f2fd
    style D fill:#fff3e0
    style E fill:#ffecb5
    style F fill:#b3e5fc
    style G fill:#f3e5f5
    style H fill:#e1f5fe
    style I fill:#fce4ec
```

## 🎯 Business Domain Examples

| Domain Area                    | Pattern Application                                    | Implementation Details                                          | Benefits Demonstrated                                                 |
| ------------------------------ | ------------------------------------------------------ | --------------------------------------------------------------- | --------------------------------------------------------------------- |
| **🍕 Order Processing**        | Clean Architecture + CQRS + Event Sourcing + DI        | Complete workflow from placement to delivery with event history | Layer separation, mediation routing, audit trails, service management |
| **📋 Menu Management**         | Repository + Resource-Oriented + DI                    | Product catalog with pricing and availability via REST API      | Data abstraction, RESTful design, dependency management               |
| **👨‍🍳 Kitchen Operations**      | Event-Driven + Reactive Programming + Watcher Patterns | Real-time queue management with stream processing               | Reactive processing, observable streams, state synchronization        |
| **📱 Customer Communications** | Event-Driven + Reactive Programming                    | Real-time notifications through reactive event streams          | Stream processing, asynchronous messaging, real-time updates          |
| **💳 Payment Processing**      | Clean Architecture + Repository + DI                   | External service integration with proper abstraction            | Infrastructure abstraction, testability, service integration          |
| **📊 Analytics & Reporting**   | Event Sourcing + Reactive Programming                  | Business intelligence from event streams with real-time views   | Temporal queries, stream aggregation, historical analysis             |

## 🧪 Testing Strategies

| Testing Type               | Scope                    | Pattern Focus                            | Tools & Techniques                         | Example Scenarios                                 |
| -------------------------- | ------------------------ | ---------------------------------------- | ------------------------------------------ | ------------------------------------------------- |
| **🔬 Unit Testing**        | Individual components    | All patterns with isolated mocks         | pytest, Mock objects, dependency injection | Test OrderEntity business logic, Command handlers |
| **🔗 Integration Testing** | Cross-layer interactions | Clean Architecture layer communication   | TestClient, database containers            | Test API → Application → Domain flow              |
| **🌐 End-to-End Testing**  | Complete workflows       | Full pattern integration                 | Automated scenarios, real dependencies     | Complete pizza order workflow validation          |
| **⚡ Performance Testing** | Scalability validation   | CQRS read optimization, Event throughput | Load testing, metrics collection           | Query performance, event processing rates         |

## 📚 Pattern Learning Paths

| Level               | Focus Area                | Recommended Patterns                                                                                                                                                                                    | Learning Objectives                                                                                                           | Practical Outcomes                                          |
| ------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| **🌱 Beginner**     | Foundation & Structure    | 1. [Clean Architecture](clean-architecture.md)<br/>2. [Domain Driven Design](domain-driven-design.md)<br/>3. [Dependency Injection](dependency-injection.md)<br/>4. [Repository Pattern](repository.md) | • Layer separation principles<br/>• Rich domain model design<br/>• Service lifetime management<br/>• Data access abstraction  | Pizza ordering system with rich domain models and proper DI |
| **🚀 Intermediate** | Separation & Optimization | 1. [CQRS & Mediation](cqrs.md)<br/>2. [Event-Driven Architecture](event-driven.md)<br/>3. [Resource-Oriented Architecture](resource-oriented-architecture.md)                                           | • Read/write operation separation<br/>• Mediator pattern usage<br/>• Event-driven workflows<br/>• RESTful API design          | Scalable pizza API with command/query separation and events |
| **⚡ Advanced**     | Reactive & Distributed    | 1. [Event Sourcing](event-sourcing.md)<br/>2. [Reactive Programming](reactive-programming.md)<br/>3. [Watcher & Reconciliation](watcher-reconciliation-patterns.md)                                     | • Event-based persistence<br/>• Stream processing patterns<br/>• Reactive system design<br/>• State reconciliation strategies | Complete event-sourced pizzeria with real-time capabilities |

## 🔗 Related Documentation

- [🚀 Framework Features](../features/index.md) - Implementation-specific features
- [📖 Implementation Guides](../guides/index.md) - Step-by-step tutorials
- [🍕 Mario's Pizzeria](../mario-pizzeria.md) - Complete system example
- [💼 Sample Applications](../samples/index.md) - Production-ready examples
- [🔐 OAuth, OIDC & JWT](../references/oauth-oidc-jwt.md) - Authentication and authorization patterns

---

These patterns form the architectural foundation for building maintainable, testable, and scalable applications. Each pattern page includes detailed code examples, Mermaid diagrams, and practical implementation guidance using the Mario's Pizzeria domain.
