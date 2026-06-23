# Core Concepts

Welcome to the Core Concepts guide! This section explains the architectural patterns and principles that Neuroglia is built upon. Each concept is explained for **beginners** - you don't need prior knowledge of these patterns.

## 🎯 Why These Patterns?

Neuroglia enforces specific architectural patterns because they solve **real problems** in software development:

- **Maintainability**: Code that's easy to change as requirements evolve
- **Testability**: Components that can be tested in isolation
- **Scalability**: Architecture that grows with your application
- **Clarity**: Clear separation of concerns and responsibilities

## 📚 Concepts Overview

### Architecture Patterns

- **[Clean Architecture](clean-architecture.md)** - Organizing code in layers with clear dependencies

  - _Problem it solves_: Tangled code where everything depends on everything
  - _Key benefit_: Business logic independent of frameworks and databases

- **[Dependency Injection](dependency-injection.md)** - Providing dependencies instead of creating them
  - _Problem it solves_: Hard-coded dependencies that make testing difficult
  - _Key benefit_: Loosely coupled, testable components

### Domain-Driven Design

- **[Domain-Driven Design Basics](domain-driven-design.md)** - Modeling your business domain

  - _Problem it solves_: Business logic scattered across services
  - _Key benefit_: Rich domain models that encapsulate business rules

- **[Aggregates & Entities](aggregates-entities.md)** - Building blocks of your domain
  - _Problem it solves_: Unclear boundaries and consistency rules
  - _Key benefit_: Clear transaction boundaries and data consistency

### Application Patterns

- **[CQRS (Command Query Responsibility Segregation)](cqrs.md)** - Separating reads from writes

  - _Problem it solves_: Single model trying to serve both read and write operations
  - _Key benefit_: Optimized read and write paths, better scalability

- **[Mediator Pattern](mediator.md)** - Request routing and handling

  - _Problem it solves_: Controllers knowing about specific handlers
  - _Key benefit_: Loose coupling, easy to add cross-cutting concerns

- **[Event-Driven Architecture](event-driven.md)** - Reacting to business occurrences
  - _Problem it solves_: Tight coupling between components
  - _Key benefit_: Extensible, loosely coupled systems

### Data Patterns

- **[Repository Pattern](repository.md)** - Abstracting data access

  - _Problem it solves_: Domain code coupled to database
  - _Key benefit_: Testable, swappable data access

- **[Unit of Work](../patterns/unit-of-work.md)** - Managing transactions
  - _Problem it solves_: Manual transaction management and event publishing
  - _Key benefit_: Consistent transactional boundaries

## 🚦 Learning Path

**New to these concepts?** Follow this path:

1. **Start here**: [Clean Architecture](clean-architecture.md)
2. **Then learn**: [Dependency Injection](dependency-injection.md)
3. **Domain modeling**: [Domain-Driven Design](domain-driven-design.md)
4. **Application layer**: [CQRS](cqrs.md) → [Mediator](mediator.md)
5. **Integration**: [Event-Driven Architecture](event-driven.md)
6. **Data access**: [Repository](repository.md) → [Unit of Work](../patterns/unit-of-work.md)

**Already familiar?** Jump to any concept for Neuroglia-specific implementation details.

## 💡 How to Use These Guides

Each concept guide includes:

- ❌ **The Problem**: What happens without this pattern
- ✅ **The Solution**: How the pattern solves it
- 🔧 **In Neuroglia**: How to implement it in the framework
- 🧪 **Testing**: How to test code using this pattern
- ⚠️ **Common Mistakes**: Pitfalls to avoid
- 🚫 **When NOT to Use**: Scenarios where simpler approaches work better

## 🍕 See It In Action

All concepts are demonstrated in the **[Mario's Pizzeria tutorial](../tutorials/index.md)**:

- Part 1 shows Clean Architecture and Dependency Injection
- Part 2 covers Domain-Driven Design and Aggregates
- Part 3 demonstrates CQRS and Mediator
- Part 5 explores Event-Driven Architecture
- Part 6 implements Repository and Unit of Work

## 🎓 Additional Resources

- **Tutorials**: [Step-by-step Mario's Pizzeria guide](../tutorials/index.md)
- **Features**: [Framework feature documentation](../features/index.md)
- **Patterns**: [Advanced pattern examples](../patterns/index.md)
- **Case Study**: [Complete Mario's Pizzeria analysis](../mario-pizzeria.md)

---

Ready to dive in? Start with [Clean Architecture](clean-architecture.md) to understand the foundation of Neuroglia's approach!
