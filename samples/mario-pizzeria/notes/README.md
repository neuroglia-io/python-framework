# Mario's Pizzeria - Implementation Notes

This directory contains application-specific documentation for the Mario's Pizzeria sample application, a comprehensive demonstration of the Neuroglia framework in action.

## 🍕 About Mario's Pizzeria

Mario's Pizzeria is a full-featured pizza ordering and management system that showcases:

- CQRS and event-driven architecture
- Domain-Driven Design patterns
- Real-time order tracking
- Role-based access control with Keycloak
- Distributed tracing and observability
- MongoDB state persistence
- Responsive web UI with htmx

## 📁 Directory Structure

### `/architecture` - System Architecture

Domain modeling, event flow, and architectural decisions specific to Mario's Pizzeria.

- **ARCHITECTURE_REVIEW.md** - Complete system architecture review
- **DOMAIN_EVENTS_FLOW_EXPLAINED.md** - Event-driven workflow documentation
- **ENTITY_VS_AGGREGATEROOT_ANALYSIS.md** - Domain model design decisions
- **VISUAL_FLOW_DIAGRAMS.md** - System flow visualizations

### `/implementation` - Feature Implementation

Detailed implementation notes for core features and refactoring efforts.

- **Implementation Plans**: IMPLEMENTATION_PLAN.md, IMPLEMENTATION_SUMMARY.md, PROGRESS.md
- **Phase Documentation**: PHASE2_COMPLETE.md, PHASE2.6_COMPLETE.md, PHASE2_IMPLEMENTATION_COMPLETE.md
- **Refactoring Notes**: All refactoring completion and summary documents
- **Repository Implementation**: Database access layer documentation
- **Delivery System**: Complete delivery tracking implementation
- **User Profiles**: Customer profile and tracking system
- **Order Management**: Order lifecycle implementation
- **Menu Management**: Pizza menu CRUD operations

### `/ui` - User Interface

Frontend implementation, styling, and user experience.

- **View Implementations**: Menu, Orders, Kitchen, Management dashboards
- **UI Fixes**: Authentication, profile auto-creation, status updates
- **Styling**: Pizza cards, modals, dropdowns, unified styling
- **Build System**: Parcel bundler configuration and optimization
- **Static Files**: Asset management and serving

### `/infrastructure` - Infrastructure & DevOps

Authentication, deployment, database setup, and external integrations.

- **Keycloak Integration**: OAuth2 setup, user management, role configuration
- **Docker Setup**: Container orchestration and deployment
- **MongoDB Repositories**: Database-specific implementations
- **Session Management**: Keycloak-based session persistence

### `/guides` - User Guides

Quick start, testing, and operational guides.

- **QUICK_START.md** - Getting started with Mario's Pizzeria
- **PHASE2_BUILD_TEST_GUIDE.md** - Build and testing instructions
- **PHASE2_TEST_RESULTS.md** - Test execution results
- **USER_PROFILE_IMPLEMENTATION_PLAN.md** - Profile feature guide

### `/observability` - Monitoring & Tracing

OpenTelemetry integration, distributed tracing, and metrics collection.

- **OTEL Integration**: OpenTelemetry setup and configuration
- **Framework Tracing**: Automatic CQRS instrumentation
- **Progress Tracking**: Observability implementation status

### `/migrations` - Version Upgrades

Framework upgrade notes and integration issue resolutions.

- **UPGRADE_NOTES_v0.4.6.md** - Framework version 0.4.6 upgrade guide
- **INTEGRATION_TEST_ISSUES.md** - Test integration problems and solutions

## 🎯 Key Features Documented

### Order Management System

- Customer order placement and tracking
- Real-time status updates
- Order cancellation workflow
- Historical order viewing

### Kitchen Management

- Active order queue
- Cooking workflow automation
- Order preparation tracking
- Completion notifications

### Delivery System

- Driver assignment and tracking
- Delivery status management
- Location-based routing
- Delivery completion workflow

### Menu Management

- Pizza CRUD operations
- Size and pricing management
- Ingredient tracking
- Menu item availability

### User & Profile Management

- Customer profile creation
- Order history tracking
- Authentication with Keycloak
- Role-based access (Customer, Kitchen Staff, Delivery Driver, Manager)

### Observability

- Distributed tracing with Tempo
- Structured logging with Loki
- Business metrics with Prometheus
- Grafana dashboards for visualization

## 🏗️ Architecture Highlights

### Domain Model

```
Order (Aggregate Root)
  ├── LineItems (Value Objects)
  ├── DeliveryAddress (Value Object)
  └── Domain Events: OrderPlaced, OrderInProgress, OrderCompleted, OrderCancelled

Pizza (Entity)
  ├── Sizes and Prices
  └── Domain Events: PizzaCreated, PizzaUpdated

UserProfile (Aggregate Root)
  └── Domain Events: UserProfileCreated
```

### CQRS Commands & Queries

**Commands** (Write Operations):

- PlaceOrderCommand
- StartCookingCommand
- CompleteOrderCommand
- CancelOrderCommand
- AssignDeliveryCommand
- CompleteDeliveryCommand
- CreatePizzaCommand
- UpdatePizzaCommand

**Queries** (Read Operations):

- GetOrderByIdQuery
- GetOrdersByCustomerQuery
- GetActiveOrdersQuery
- GetKitchenOrdersQuery
- GetDeliveryOrdersQuery
- GetMenuQuery
- GetPizzaByIdQuery

### Event-Driven Workflows

1. **Order Placement**: Customer → OrderPlaced Event → Kitchen Notification
2. **Cooking**: Kitchen Staff → OrderInProgress Event → Status Update
3. **Delivery**: Driver Assignment → DeliveryInProgress Event → Completion
4. **Notifications**: All domain events trigger real-time UI updates

## 📚 Related Documentation

- **Framework Notes**: See `/notes/` for reusable Neuroglia patterns
- **MkDocs Documentation**: Comprehensive sample application guide
- **API Documentation**: Swagger UI at http://localhost:8080/docs
- **Grafana Dashboards**: http://localhost:3001 (observability)

## 🚀 Getting Started

1. **Setup**: See `guides/QUICK_START.md` for installation instructions
2. **Architecture**: Review `architecture/ARCHITECTURE_REVIEW.md` for system overview
3. **Implementation**: Check `implementation/IMPLEMENTATION_PLAN.md` for feature breakdown
4. **Testing**: Follow `guides/PHASE2_BUILD_TEST_GUIDE.md` for test execution

## 🔄 Maintenance

When implementing new features or making changes:

1. Document architectural decisions in `/architecture`
2. Track implementation progress in `/implementation`
3. Update UI documentation in `/ui` for frontend changes
4. Maintain infrastructure guides in `/infrastructure`
5. Keep observability docs current as instrumentation evolves

## 🎓 Learning Resource

These notes serve as a comprehensive learning resource for:

- Building event-driven microservices with Neuroglia
- Implementing CQRS patterns in real applications
- Integrating authentication and authorization
- Setting up distributed tracing and observability
- Structuring domain models with DDD principles
- Building responsive web UIs with htmx
