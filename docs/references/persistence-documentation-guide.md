# 📚 Documentation Cross-References

This document provides cross-references between all the persistence-related documentation in the Neuroglia framework.

## 🏛️ Persistence Documentation Hierarchy

### **Primary Guides**

1. **[🏛️ Persistence Patterns](../patterns/persistence-patterns.md)** - _Start Here_

   - **Purpose**: Complete overview and decision framework for choosing persistence approaches
   - **Contains**: Pattern comparison, complexity levels, decision matrix, implementation examples
   - **When to Read**: When starting a new feature or project and need to choose persistence approach

2. **[🔄 Unit of Work Pattern](../patterns/unit-of-work.md)** - _Core Infrastructure_
   - **Purpose**: Deep dive into the coordination layer that works with all persistence patterns
   - **Contains**: UnitOfWork implementation, event collection, pipeline integration
   - **When to Read**: When implementing command handlers or need to understand event coordination

### **Feature-Specific Guides**

3. **[🏛️ State-Based Persistence](../features/state-based-persistence.md)** - _Simple Approach_

   - **Purpose**: Detailed implementation guide for Entity + State persistence pattern
   - **Contains**: Entity design, repositories, command handlers, event integration
   - **When to Read**: When implementing the simple persistence pattern

4. **[🎯 Simple CQRS](../features/simple-cqrs.md)** - _Command/Query Handling_

   - **Purpose**: CQRS implementation that works with both persistence patterns
   - **Contains**: Command/Query handlers, mediator usage, pipeline behaviors
   - **When to Read**: When implementing application layer handlers

5. **[🔧 Pipeline Behaviors](../patterns/pipeline-behaviors.md)** - _Cross-Cutting Concerns_
   - **Purpose**: Middleware patterns for validation, transactions, event dispatching
   - **Contains**: Pipeline behavior implementation, ordering, integration patterns
   - **When to Read**: When implementing cross-cutting concerns like validation or logging

### **Pattern Documentation**

6. **[🏛️ Domain Driven Design](../patterns/domain-driven-design.md)** - _Foundation Patterns_
   - **Purpose**: Core DDD patterns and abstractions used by all approaches
   - **Contains**: Entity vs AggregateRoot patterns, domain events, DDD principles
   - **When to Read**: When learning DDD concepts or designing domain models

## 🗺️ Reading Path by Use Case

### **New to Neuroglia Framework**

1. Start with **[Persistence Patterns](../patterns/persistence-patterns.md)** for overview
2. Read **[Domain Driven Design](../patterns/domain-driven-design.md)** for foundation concepts
3. Choose specific pattern guide based on your needs:
   - Simple: **[Persistence Patterns - Simple Entity](../patterns/persistence-patterns.md#pattern-1-simple-entity--state-persistence)**
   - Complex: **[Domain Driven Design](../patterns/domain-driven-design.md)** Event Sourcing sections
4. Learn coordination with **[Unit of Work](../patterns/unit-of-work.md)**
5. Implement handlers with **[Simple CQRS](../features/simple-cqrs.md)**

### **Implementing Simple CRUD Application**

1. **[Persistence Patterns](../patterns/persistence-patterns.md)** → Choose Entity + State Persistence
2. **[Persistence Patterns - Simple Entity](../patterns/persistence-patterns.md#pattern-1-simple-entity--state-persistence)** → Implementation guide
3. **[Unit of Work](../patterns/unit-of-work.md)** → Event coordination
4. **[Simple CQRS](../features/simple-cqrs.md)** → Command/Query handlers

### **Building Complex Domain with Event Sourcing**

1. **[Persistence Patterns](../patterns/persistence-patterns.md)** → Choose AggregateRoot + Event Sourcing
2. **[Domain Driven Design](../patterns/domain-driven-design.md)** → Full DDD patterns
3. **[Unit of Work](../patterns/unit-of-work.md)** → Event coordination
4. **[Simple CQRS](../features/simple-cqrs.md)** → Command/Query handlers
5. **[Pipeline Behaviors](../patterns/pipeline-behaviors.md)** → Cross-cutting concerns

### **Migrating Between Patterns**

1. **[Persistence Patterns](../patterns/persistence-patterns.md)** → Hybrid approach section
2. **[Unit of Work](../patterns/unit-of-work.md)** → Same infrastructure for both patterns
3. Specific implementation guides based on source and target patterns

### **Understanding Event Coordination**

1. **[Unit of Work](../patterns/unit-of-work.md)** → Core coordination patterns
2. **[Pipeline Behaviors](../patterns/pipeline-behaviors.md)** → Event dispatching middleware
3. **[Domain Driven Design](../patterns/domain-driven-design.md)** → Domain event patterns

### **Implementing Cross-Cutting Concerns**

1. **[Pipeline Behaviors](../patterns/pipeline-behaviors.md)** → Core patterns
2. **[Unit of Work](../patterns/unit-of-work.md)** → Integration with event coordination
3. **[Simple CQRS](../features/simple-cqrs.md)** → Handler integration

## 🔗 Key Relationships

### **All Patterns Use Same Infrastructure**

- **Unit of Work** coordinates events for both Entity and AggregateRoot patterns
- **Pipeline Behaviors** provide cross-cutting concerns for both approaches
- **CQRS/Mediator** handles commands/queries regardless of persistence pattern
- **Domain Events** work the same way in both simple and complex patterns

### **Complexity Progression**

```
Entity + State Persistence (⭐⭐☆☆☆)
    ↓ (add business complexity)
AggregateRoot + Event Sourcing (⭐⭐⭐⭐⭐)
    ↓ (mix both approaches)
Hybrid Approach (⭐⭐⭐☆☆)
```

### **Framework Integration Points**

- **Unit of Work** ← All persistence patterns use this for event coordination
- **Pipeline Behaviors** ← All handlers use this for cross-cutting concerns
- **Mediator** ← All commands/queries route through this
- **Domain Events** ← All patterns raise events, same dispatching mechanism

## 📖 Quick Reference

| **I Need To...**            | **Read This First**                                                                                                    | **Then Read**                                               |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Choose persistence approach | [Persistence Patterns](../patterns/persistence-patterns.md)                                                            | Pattern-specific guide                                      |
| Implement simple CRUD       | [Persistence Patterns - Simple Entity](../patterns/persistence-patterns.md#pattern-1-simple-entity--state-persistence) | [Unit of Work](../patterns/unit-of-work.md)                 |
| Build complex domain        | [Domain Driven Design](../patterns/domain-driven-design.md)                                                            | [Unit of Work](../patterns/unit-of-work.md)                 |
| Coordinate events           | [Unit of Work](../patterns/unit-of-work.md)                                                                            | [Pipeline Behaviors](../patterns/pipeline-behaviors.md)     |
| Implement handlers          | [Simple CQRS](../features/simple-cqrs.md)                                                                              | [Pipeline Behaviors](../patterns/pipeline-behaviors.md)     |
| Add validation/logging      | [Pipeline Behaviors](../patterns/pipeline-behaviors.md)                                                                | [Unit of Work](../patterns/unit-of-work.md)                 |
| Understand DDD concepts     | [Domain Driven Design](../patterns/domain-driven-design.md)                                                            | [Persistence Patterns](../patterns/persistence-patterns.md) |

---

_This documentation structure ensures you can find the right information for your specific use case while understanding how all the pieces work together in the Neuroglia framework._
