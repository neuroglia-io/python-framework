# 🏢 Mario's Pizzeria: Business Analysis & Requirements

> **Customer**: Mario's Family Restaurant
> **Project**: Digital Transformation Initiative
> **Consultant**: Neuroglia Architecture Team
> **Date**: 2025

📂 **[View Complete Implementation on GitHub](https://github.com/bvandewe/pyneuro/tree/main/samples/mario-pizzeria)**

---

> 💡 **Pattern in Action**: This document demonstrates how [**Clean Architecture**](../patterns/clean-architecture.md) and [**Domain-Driven Design**](../patterns/domain-driven-design.md) principles translate business requirements into maintainable software architecture.

---

## 📊 Executive Summary

Mario's Pizzeria represents a typical small business digital transformation case study. This family-owned restaurant requires a modern ordering system to compete in today's digital marketplace while maintaining operational efficiency and customer satisfaction.

**Project Scope**: Design and implement a comprehensive digital ordering platform that streamlines operations, improves customer experience, and provides real-time visibility into business operations.

**Architectural Approach**: This project demonstrates **[event-driven architecture](../patterns/event-driven.md)** where business workflows (like kitchen operations) respond automatically to domain events, reducing coupling and improving scalability.

---

## 🎯 Business Overview

**Mario's Pizzeria** is a local pizza restaurant that needs a digital ordering system to handle:

- **Customer Orders**: Online pizza ordering with customizations
- **Menu Management**: Pizza catalog with sizes, toppings, and pricing
- **Kitchen Operations**: Order queue management and preparation workflow
- **Payment Processing**: Multiple payment methods and transaction handling
- **Customer Notifications**: SMS alerts for order status updates

The pizzeria demonstrates how a simple restaurant business can be modeled using domain-driven design principles:

- Takes pizza orders from customers
- Manages pizza recipes and inventory
- Cooks pizzas in the kitchen with capacity management
- Tracks order status through complete lifecycle
- Handles payments and customer notifications
- Provides real-time status updates to customers and staff

## 🏗️ System Architecture

The pizzeria system demonstrates **[clean architecture](../patterns/clean-architecture.md)** with clear layer separation and dependency rules:

> 🎯 **Why This Matters**: Clean architecture ensures business logic remains independent of frameworks, databases, and UI choices. See the [Common Mistakes](../patterns/clean-architecture.md#common-mistakes) section to learn why mixing layers causes maintenance nightmares.

```mermaid
graph TB
    %% Actors
    Customer[👤 Customer<br/>Pizza lover who wants to place orders]
    KitchenStaff[👨‍🍳 Kitchen Staff<br/>Cooks who prepare orders]
    Manager[👨‍💼 Manager<br/>Manages menu and monitors operations]

    %% System Boundary
    subgraph PizzeriaSystem[Mario's Pizzeria System]
        PizzeriaApp[🍕 Pizzeria Application<br/>FastAPI app with clean architecture]
    end

    %% External Systems
    PaymentSystem[💳 Payment System<br/>Processes credit card payments]
    SMSService[📱 SMS Service<br/>Sends order notifications]
    FileStorage[💾 File Storage<br/>JSON files for development]

    %% Relationships
    Customer -->|Places orders, checks status| PizzeriaApp
    KitchenStaff -->|Views orders, updates status| PizzeriaApp
    Manager -->|Manages menu, monitors operations| PizzeriaApp

    PizzeriaApp -->|Processes payments via HTTPS| PaymentSystem
    PizzeriaApp -->|Sends notifications via API| SMSService
    PizzeriaApp -->|Stores orders and menu via File I/O| FileStorage

    %% Styling
    classDef customer fill:#FFF3E0,stroke:#E65100,stroke-width:2px
    classDef system fill:#E1F5FE,stroke:#01579B,stroke-width:3px
    classDef external fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
    classDef storage fill:#E8F5E8,stroke:#2E7D32,stroke-width:2px

    class Customer,KitchenStaff,Manager customer
    class PizzeriaApp system
    class PaymentSystem,SMSService external
        class FileStorage storage
```

---

## 🔄 Main System Interactions

The following sequence diagram illustrates the complete pizza ordering workflow using **[CQRS](../patterns/cqrs.md)** (commands for writes) and **[event-driven architecture](../patterns/event-driven.md)** (events for workflow automation):

> 🎯 **Why Commands and Events?**: Commands represent intent ("place this order"), while events represent facts ("order was placed"). This separation enables loose coupling and better scalability. Learn more in [CQRS Pattern](../patterns/cqrs.md#what--why-the-cqrs-pattern).

```mermaid
sequenceDiagram
    participant C as Customer
    participant API as Orders Controller
    participant M as Mediator
    participant PH as PlaceOrder Handler
    participant OR as Order Repository
    participant PS as Payment Service
    participant K as Kitchen
    participant SMS as SMS Service

    Note over C,SMS: Complete Pizza Ordering Workflow

    C->>+API: POST /orders (pizza order)
    API->>+M: Execute PlaceOrderCommand
    M->>+PH: Handle command

    PH->>PH: Validate order & calculate total
    PH->>+PS: Process payment
    PS-->>-PH: Payment successful

    PH->>+OR: Save order
    OR-->>-PH: Order saved

    PH->>PH: Raise OrderPlacedEvent
    PH-->>-M: Return OrderDto
    M-->>-API: Return result
    API-->>-C: 201 Created + OrderDto

    Note over K,SMS: Event-Driven Kitchen Workflow

    M->>+K: OrderPlacedEvent → Add to queue
    K-->>-M: Order queued

    rect rgb(255, 245, 235)
        Note over K: Kitchen processes order
        K->>K: Start cooking
        K->>+M: Publish OrderCookingEvent
        M-->>-K: Event processed
    end

    rect rgb(240, 255, 240)
        Note over K: Order ready
        K->>+M: Publish OrderReadyEvent
        M->>+SMS: Send ready notification
        SMS->>C: "Your order is ready!"
        SMS-->>-M: Notification sent
        M-->>-K: Event processed
    end

    C->>+API: GET /orders/{id}
    API->>+M: Execute GetOrderQuery
    M-->>-API: Return OrderDto
    API-->>-C: Order details
```

--- storage

```

---mermaid
sequenceDiagram
    participant C as Customer
    participant API as Orders Controller
    participant M as Mediator
    participant PH as PlaceOrder Handler
    participant OR as Order Repository
    participant PS as Payment Service
    participant K as Kitchen
    participant SMS as SMS Service

    Note over C,SMS: Complete Pizza Ordering Workflow

    C->>+API: POST /orders (pizza order)
    API->>+M: Execute PlaceOrderCommand
    M->>+PH: Handle command

    PH->>PH: Validate order & calculate total
    PH->>+PS: Process payment
    PS-->>-PH: Payment successful

    PH->>+OR: Save order
    OR-->>-PH: Order saved

    PH->>PH: Raise OrderPlacedEvent
    PH-->>-M: Return OrderDto
    M-->>-API: Return result
    API-->>-C: 201 Created + OrderDto

    Note over K,SMS: Event-Driven Kitchen Workflow

    M->>+K: OrderPlacedEvent → Add to queue
    K-->>-M: Order queued

    rect rgb(255, 245, 235)
        Note over K: Kitchen processes order
        K->>K: Start cooking
        K->>+M: Publish OrderCookingEvent
        M-->>-K: Event processed
    end

    rect rgb(240, 255, 240)
        Note over K: Order ready
        K->>+M: Publish OrderReadyEvent
        M->>+SMS: Send ready notification
        SMS->>C: "Your order is ready!"
        SMS-->>-M: Notification sent
        M-->>-K: Event processed
    end

    C->>+API: GET /orders/{id}
    API->>+M: Execute GetOrderQuery
    M-->>-API: Return OrderDto
    API-->>-C: Order details
```

## 💼 Business Requirements Analysis

### Primary Stakeholders

| Stakeholder       | Role               | Key Needs                                                |
| ----------------- | ------------------ | -------------------------------------------------------- |
| **Customers**     | Order pizza online | Easy ordering, real-time status, reliable delivery       |
| **Kitchen Staff** | Prepare orders     | Clear order queue, cooking instructions, status updates  |
| **Management**    | Business oversight | Sales reporting, inventory tracking, performance metrics |
| **Delivery**      | Order fulfillment  | Route optimization, customer contact, payment collection |

### Functional Requirements

| Category          | Requirement                     | Priority | Complexity |
| ----------------- | ------------------------------- | -------- | ---------- |
| **Ordering**      | Browse menu with customizations | High     | Medium     |
| **Ordering**      | Calculate pricing with taxes    | High     | Low        |
| **Ordering**      | Process secure payments         | High     | High       |
| **Kitchen**       | Manage cooking queue            | High     | Medium     |
| **Kitchen**       | Track preparation time          | Medium   | Low        |
| **Notifications** | SMS order updates               | Medium   | Medium     |
| **Management**    | Sales analytics                 | Low      | High       |

### Non-Functional Requirements

| Requirement       | Target                | Rationale           |
| ----------------- | --------------------- | ------------------- |
| **Response Time** | < 2 seconds           | Customer experience |
| **Availability**  | 99.5% uptime          | Business continuity |
| **Scalability**   | 100 concurrent orders | Peak dinner rush    |
| **Security**      | PCI DSS compliance    | Payment processing  |
| **Usability**     | Mobile-first design   | Customer preference |

## 🚀 Success Metrics

### Business KPIs

- **Order Volume**: 30% increase in daily orders
- **Average Order Value**: $25 → $30 target
- **Customer Satisfaction**: > 4.5/5 rating
- **Order Accuracy**: > 98% correct orders
- **Kitchen Efficiency**: < 15 minute average prep time

### Technical Metrics

- **API Response Time**: < 500ms average
- **System Uptime**: > 99.5%
- **Error Rate**: < 0.1%
- **Payment Success**: > 99.9%

## 🔗 Related Documentation

### Case Study Documents

- [Technical Architecture](technical-architecture.md) - System design and infrastructure
- [Domain Design](domain-design.md) - Business logic and data models
- [Implementation Guide](implementation-guide.md) - Development patterns and APIs
- [Testing & Deployment](testing-deployment.md) - Quality assurance and operations

### Framework Patterns Demonstrated

- **[Clean Architecture](../patterns/clean-architecture.md)** - Four-layer separation seen throughout the system
- **[Event-Driven Architecture](../patterns/event-driven.md)** - Kitchen workflow automation with domain events
- **[CQRS Pattern](../patterns/cqrs.md)** - Commands (PlaceOrder) vs Queries (GetOrder) separation
- **[Domain-Driven Design](../patterns/domain-driven-design.md)** - Business concepts as rich domain models

> 💡 **Learning Tip**: Each pattern page includes "Common Mistakes" and "When NOT to Use" sections derived from real-world implementations like Mario's Pizzeria!

---

_This analysis serves as the foundation for Mario's Pizzeria digital transformation, demonstrating modern software architecture principles applied to real-world business scenarios._
