# 🍕 Mario's Pizzeria - Complete Sample Application

A comprehensive sample application demonstrating all major Neuroglia framework features through a realistic pizza ordering and management system with modern web UI, authentication, and observability.

> **📢 Framework Compatibility**: This sample is fully compatible with Neuroglia v0.4.8+
> See [MARIO_QUICK_REFERENCE.md](./MARIO_QUICK_REFERENCE.md) for quick setup and management commands.

## 🎯 Overview

Mario's Pizzeria showcases the complete Neuroglia framework implementation including:

- **Clean Architecture**: Proper layer separation (API, Application, Domain, Integration)
- **CQRS Pattern**: Commands for writes, Queries for reads with distributed tracing
- **Domain-Driven Design**: Rich domain entities with business logic and events
- **Event-Driven Architecture**: CloudEvents integration with domain event publishing
- **Repository Pattern**: MongoDB async persistence with Motor driver
- **Dependency Injection**: Enhanced service registration and scoped resolution
- **MVC Controllers**: Dual-app architecture with separate API and UI controllers
- **Authentication**: Keycloak SSO with role-based access control (RBAC)
- **Web UI**: Modern responsive interface with Parcel bundling and SCSS styling
- **Observability**: OpenTelemetry tracing, Prometheus metrics, Grafana dashboards

## 🏗️ Architecture

### Framework Integration

The application uses `EnhancedWebApplicationBuilder` with comprehensive observability:

```python
def create_pizzeria_app():
    # Enhanced builder with automatic observability integration
    builder = EnhancedWebApplicationBuilder(app_settings)

    # Core Framework Services
    Mediator.configure(builder, ["application.commands", "application.queries", "application.events"])
    Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])
    JsonSerializer.configure(builder, ["domain.entities.enums", "domain.entities"])
    UnitOfWork.configure(builder)
    DomainEventDispatchingMiddleware.configure(builder)

    # CloudEvent Integration
    CloudEventPublisher.configure(builder)
    CloudEventIngestor.configure(builder, ["application.events.integration"])

    # Comprehensive Observability (Three Pillars + Standard Endpoints + TracingPipelineBehavior)
    Observability.configure(builder)  # Auto-configures from app_settings

    # MongoDB Motor Integration
    MotorRepository.configure(builder, Customer, str, "mario_pizzeria", "customers")
    MotorRepository.configure(builder, Order, str, "mario_pizzeria", "orders")
    # ... additional entities

    # Multi-app architecture with separate authentication strategies
    app = builder.build_app_with_lifespan(title="Mario's Pizzeria")
    api_app = FastAPI(title="Mario's Pizzeria API")  # OAuth2/JWT
    ui_app = FastAPI(title="Mario's Pizzeria UI")    # Session-based
```

### Directory Structure

```
mario-pizzeria/
├── api/                     # 🌐 API Layer (OAuth2/JWT)
│   ├── controllers/         # RESTful API endpoints with authentication
│   ├── dtos/               # Data transfer objects
│   └── services/           # OpenAPI configuration
├── application/            # 💼 Application Layer
│   ├── commands/           # Write operations with auto-tracing
│   ├── queries/            # Read operations with metrics
│   ├── events/             # Integration event handlers
│   ├── services/           # Application services (auth, etc.)
│   └── settings.py         # Enhanced configuration with observability
├── domain/                 # 🏛️ Domain Layer
│   ├── entities/           # Business entities with event sourcing
│   ├── events.py           # CloudEvent-decorated domain events
│   └── repositories/       # Repository interfaces
├── integration/            # 🔌 Integration Layer
│   └── repositories/       # MongoDB Motor async implementations
├── ui/                     # 🎨 Web UI Layer (Session-based auth)
│   ├── controllers/        # Web page controllers with Keycloak SSO
│   ├── templates/          # Jinja2 HTML templates
│   ├── src/               # TypeScript/SCSS source files
│   └── static/            # Built assets (Parcel)
├── observability/          # 📊 Observability
│   └── metrics.py         # Business-specific metrics
└── deployment/            # 🐳 Infrastructure
    ├── keycloak/          # Identity provider config
    ├── mongo/             # Database initialization
    ├── prometheus/        # Metrics collection config
    └── otel/              # OpenTelemetry collector config
```

## 🚀 Features

### Multi-Application Architecture

- **API App**: RESTful backend with OAuth2/JWT authentication (`/api`)
- **UI App**: Web interface with Keycloak SSO session authentication (`/`)
- **Dual Authentication**: Supports both token-based (API) and session-based (UI) auth
- **Role-Based Access**: Customer, Kitchen Staff, Manager, and Admin roles

### Order Management

- Place new pizza orders with customer profiles
- Real-time order status tracking with notifications
- Support for multiple pizzas per order with line items
- Automatic pricing calculations with tax and discounts
- Order cancellation and modification support

### Kitchen Operations

- Dedicated kitchen dashboard for staff
- View kitchen status, capacity, and current load
- Start cooking orders with automatic status transitions
- Complete orders when ready with delivery coordination
- Queue management with priority handling for rush periods

### Menu System

- Dynamic pizza menu with availability tracking
- Configurable toppings with seasonal pricing
- Size variations (small, medium, large) with scaling prices
- Real-time pricing calculations with promotions
- Menu management interface for administrators

### Customer Management

- Customer profile creation and management
- Order history with detailed tracking
- Contact details and delivery preferences
- Loyalty program integration
- Customer analytics and insights

### Delivery System

- Delivery tracking with real-time updates
- Route optimization for delivery drivers
- Delivery time estimates and notifications
- Driver assignment and coordination

### Authentication & Authorization

- **Keycloak SSO**: Single sign-on with role management
- **OAuth2/OIDC**: Modern authentication standards
- **JWT Tokens**: Secure API access with claims
- **Session Management**: Web UI authentication
- **Role-Based Access Control**: Fine-grained permissions

### Web Interface

- **Responsive Design**: Mobile-first responsive UI
- **Modern Bundling**: Parcel build system with hot reload
- **SCSS Styling**: Maintainable CSS with variables and mixins
- **Real-time Updates**: WebSocket integration for live order status
- **Progressive Web App**: Offline capability and push notifications

### Observability & Monitoring (Three Pillars)

- **OpenTelemetry Integration**: Comprehensive tracing, metrics, and logging
- **Prometheus Metrics**: Business and system metrics at `/metrics`
- **Grafana Dashboards**: Pre-configured visualization dashboards
- **Structured Logging**: Loki log aggregation with trace correlation
- **Health Checks**: Dependency-aware health monitoring at `/health`
- **Readiness Probes**: Kubernetes-ready health checks at `/ready`
- **Automatic Instrumentation**: HTTP requests, database operations, and CQRS pipeline
- **TracingPipelineBehavior**: Automatic tracing for all Commands and Queries

## 🏃‍♂️ Quick Start

### 1. Start the Complete Stack

```bash
# Start Mario's Pizzeria with full observability stack
make mario-start

# Check that all services are running
make mario-status
```

### 2. Initialize Sample Data

```bash
# Generate test orders and menu data for dashboards
make mario-test-data
```

### 3. Access the Applications

- **🍕 Web UI**: http://localhost:8080/ (Keycloak SSO login)
- **📖 API Docs**: http://localhost:8080/api/docs (OAuth2 authentication)
- **🏥 Health Check**: http://localhost:8080/health (service health status)
- **📊 Metrics**: http://localhost:8080/metrics (Prometheus metrics endpoint)
- **🚀 Ready Check**: http://localhost:8080/ready (Kubernetes readiness probe)
- **� Grafana**: http://localhost:3001 (admin/admin)
- **🔐 Keycloak Admin**: http://localhost:8090/admin (admin/admin)

### 4. Alternative: Development Mode

```bash
# For local development without Docker (requires MongoDB)
cd samples/mario-pizzeria
python main.py --host 0.0.0.0 --port 8080
```

### 5. Sample API Requests (with Authentication)

First, get an OAuth2 token from Keycloak:

```bash
# Get access token - this command works correctly and returns HTTP 200 OK
TOKEN=$(curl -s -X POST "http://localhost:8090/realms/mario-pizzeria/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=mario-app&client_secret=mario-secret-123" \
  | jq -r '.access_token')

# Verify token was retrieved successfully
echo "Token received: ${TOKEN:0:50}..."
```

**✅ Verified Working**: This command successfully authenticates and returns a valid JWT token.

#### Place an Order

```bash
curl -X POST "http://localhost:8080/api/orders" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Mario Rossi",
    "customer_phone": "+1-555-0123",
    "customer_address": "123 Pizza Street, Little Italy",
    "pizzas": [
      {
        "pizza_name": "Margherita",
        "size": "large",
        "toppings": ["extra_cheese"],
        "quantity": 1
      }
    ],
    "payment_method": "credit_card",
    "special_instructions": "Extra crispy crust"
  }'
```

#### Get Order Status

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/orders/{order_id}"
```

#### View Menu

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/menu"
```

#### Check Kitchen Status (Kitchen Staff role required)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/kitchen/status"
```

## 📊 Order Lifecycle

1. **Placed** → Order received, validated, and payment processed
2. **Confirmed** → Order confirmed and added to kitchen queue
3. **Cooking** → Kitchen starts preparation with estimated time
4. **Ready** → Pizza is ready, customer notified for pickup/delivery
5. **Out for Delivery** → Driver assigned, en route to customer
6. **Delivered** → Order completed successfully, customer confirmation
7. **Cancelled** → Order cancelled (with refund processing if applicable)

Each status transition triggers domain events and CloudEvent notifications for real-time updates.

## 💾 Data Storage

The application uses **MongoDB** with async Motor driver for all persistence:

- **Customers**: MongoDB collection with customer profiles and preferences
- **Orders**: MongoDB collection with full order details and status history
- **Pizzas**: MongoDB collection with menu items, pricing, and availability
- **Kitchen**: MongoDB collection with kitchen status, capacity, and queue
- **CloudEvents**: Event streaming with optional EventStore integration
- **Sessions**: Redis-compatible session storage for UI authentication

### Development Data Access

- **MongoDB Express**: http://localhost:8081 (admin/admin123)
- **Database**: `mario_pizzeria`
- **Collections**: `customers`, `orders`, `pizzas`, `kitchen`

## 🔧 Configuration & Settings

The application uses comprehensive configuration management with environment variable support and computed properties.

### Core Application Settings (`MarioPizzeriaApplicationSettings`)

The main configuration class inherits from `ApplicationSettingsWithObservability`, providing:

#### **Application Identity**

```python
service_name: str = "mario-pizzeria"          # Used by observability systems
service_version: str = "1.0.0"               # Application version
deployment_environment: str = "development"   # Environment identifier
```

#### **Application Configuration**

```python
app_name: str = "Mario's Pizzeria"           # Display name
debug: bool = True                           # Debug mode
log_level: str = "DEBUG"                     # Logging level
local_dev: bool = True                       # Development mode flag
app_url: str = "http://localhost:8080"       # External application URL
```

#### **Authentication & Security**

```python
# Keycloak Configuration (Internal Docker network URLs)
keycloak_server_url: str = "http://keycloak:8080"
keycloak_realm: str = "mario-pizzeria"
keycloak_client_id: str = "mario-app"
keycloak_client_secret: str = "mario-secret-123"

# JWT Validation
jwt_audience: str = "mario-app"
required_scope: str = "openid profile email"

# Session Management
session_secret_key: str = "change-me-in-production"
session_max_age: int = 3600  # 1 hour
```

#### **CloudEvent Configuration**

```python
cloud_event_sink: str = "http://event-player:8080/events/pub"
cloud_event_source: str = "https://mario-pizzeria.io"
cloud_event_type_prefix: str = "io.mario-pizzeria"
cloud_event_retry_attempts: int = 5
cloud_event_retry_delay: float = 1.0
```

#### **Observability Configuration (Three Pillars)**

```python
# Main Toggle
observability_enabled: bool = True

# Three Pillars Control
observability_metrics_enabled: bool = True
observability_tracing_enabled: bool = True
observability_logging_enabled: bool = True

# Standard Endpoints
observability_health_endpoint: bool = True      # /health
observability_metrics_endpoint: bool = True    # /metrics
observability_ready_endpoint: bool = True      # /ready

# Health Check Dependencies
observability_health_checks: List[str] = ["mongodb", "keycloak"]

# OpenTelemetry Configuration
otel_endpoint: str = "http://otel-collector:4317"  # OTLP endpoint
otel_console_export: bool = False                  # Debug console output
```

#### **Computed Properties**

The settings class includes computed fields that automatically generate URLs:

```python
@computed_field
def jwt_authority(self) -> str:
    """Internal Keycloak authority for backend token validation"""
    return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"

@computed_field
def swagger_ui_jwt_authority(self) -> str:
    """External Keycloak authority for browser/Swagger UI"""
    if self.local_dev:
        return f"http://localhost:8090/realms/{self.keycloak_realm}"
    else:
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}"
```

### Docker Environment Variables

The application supports configuration via environment variables:

```bash
# Application
LOCAL_DEV=true
LOG_LEVEL=DEBUG
APP_NAME="Mario's Pizzeria"

# Database
CONNECTION_STRINGS='{"mongo": "mongodb://root:mario123@mongodb:27017/?authSource=admin"}'

# Observability
OBSERVABILITY_ENABLED=true
OTEL_ENDPOINT=http://otel-collector:4317
OBSERVABILITY_HEALTH_CHECKS='["mongodb", "keycloak"]'

# Authentication
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_CLIENT_SECRET=mario-secret-123

# CloudEvents
CLOUD_EVENT_SINK=http://event-player:8080/events/pub
```

### Framework Integration

The application uses `EnhancedWebApplicationBuilder` with automatic observability integration:

```python
# Create builder with settings
builder = EnhancedWebApplicationBuilder(app_settings)

# Framework automatically configures observability based on settings
Observability.configure(builder)  # Uses settings.observability_* fields
```

### Command Line Options (Development Mode)

```bash
python main.py --port 8080 --host 0.0.0.0
```

- `--port <port>`: Set the application port (default: 8080)
- `--host <host>`: Set the bind address (default: 0.0.0.0)

## 🧪 Testing

```bash
# Run all Mario's Pizzeria tests
pytest samples/mario-pizzeria/tests/ -v

# Run tests with coverage
pytest samples/mario-pizzeria/tests/ --cov=samples.mario-pizzeria -v

# Run specific test categories
pytest samples/mario-pizzeria/tests/unit/ -v           # Unit tests
pytest samples/mario-pizzeria/tests/integration/ -v    # Integration tests
pytest samples/mario-pizzeria/tests/api/ -v           # API endpoint tests

# Test with live MongoDB (requires Docker stack)
make mario-start  # Start the stack first
pytest samples/mario-pizzeria/tests/integration/ -v --live-db
```

### Test Environment

The test suite includes:

- **Unit Tests**: Domain entities, handlers, and business logic
- **Integration Tests**: Repository implementations and database operations
- **API Tests**: HTTP endpoints with authentication flows
- **UI Tests**: Web interface and form submissions
- **Contract Tests**: CloudEvent schemas and API contracts

## 📝 API Endpoints

All API endpoints require OAuth2 Bearer token authentication and are prefixed with `/api`.

### Authentication

- `POST /api/auth/login` - OAuth2 token exchange
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/profile` - Get current user profile
- `POST /api/auth/logout` - Invalidate token

### Orders

- `GET /api/orders` - List orders (filtered by user role)
- `POST /api/orders` - Place a new order
- `GET /api/orders/{id}` - Get specific order details
- `PUT /api/orders/{id}/status` - Update order status (kitchen staff+)
- `GET /api/orders/status/{status}` - Get orders by status
- `GET /api/orders/active` - Get active orders for kitchen
- `DELETE /api/orders/{id}` - Cancel order (time restrictions apply)

### Menu

- `GET /api/menu` - Get full menu with availability
- `GET /api/menu/{pizza_name}` - Get specific pizza details
- `POST /api/menu` - Add new menu item (admin only)
- `PUT /api/menu/{pizza_name}` - Update menu item (admin only)
- `DELETE /api/menu/{pizza_name}` - Remove menu item (admin only)

### Kitchen

- `GET /api/kitchen/status` - Get kitchen status and capacity
- `POST /api/kitchen/start-cooking/{order_id}` - Start cooking (kitchen staff+)
- `POST /api/kitchen/complete/{order_id}` - Mark ready (kitchen staff+)
- `GET /api/kitchen/queue` - Get cooking queue (kitchen staff+)
- `PUT /api/kitchen/capacity` - Update kitchen capacity (manager+)

### Delivery

- `GET /api/delivery/active` - Get active deliveries (driver+)
- `POST /api/delivery/{order_id}/assign` - Assign driver (manager+)
- `PUT /api/delivery/{order_id}/status` - Update delivery status (driver+)
- `GET /api/delivery/routes` - Get optimized delivery routes (driver+)

### Customer Profile

- `GET /api/profile` - Get customer profile
- `PUT /api/profile` - Update customer profile
- `GET /api/profile/orders` - Get customer order history
- `GET /api/profile/favorites` - Get favorite orders

### Analytics & Reporting (Manager+ roles)

- `GET /api/reports/sales` - Sales analytics
- `GET /api/reports/performance` - Kitchen performance metrics
- `GET /api/reports/customers` - Customer analytics

### Observability Endpoints (No authentication required)

- `GET /health` - Application health with dependency checks
- `GET /ready` - Kubernetes readiness probe
- `GET /metrics` - Prometheus metrics endpoint

## 🎨 Domain Model

### Core Entities

#### Order (Aggregate Root)

- **Properties**: ID, Customer, Line Items, Status, Totals, Payment, Timestamps
- **Business Logic**: Status transitions, pricing calculations, validation rules
- **Events**: OrderCreatedEvent, CookingStartedEvent, OrderReadyEvent, OrderDeliveredEvent
- **CloudEvents**: Decorated for external integration and event streaming

#### Customer (Aggregate Root)

- **Properties**: ID, Profile, Contact Details, Preferences, Order History
- **Business Logic**: Profile validation, loyalty calculations, preference management
- **Events**: CustomerRegisteredEvent, PreferencesUpdatedEvent
- **Authentication**: Linked to Keycloak user identity

#### Pizza (Entity)

- **Properties**: Name, Description, Sizes, Base Price, Available Toppings
- **Business Logic**: Dynamic pricing, availability checks, nutritional info
- **Validation**: Size constraints, topping compatibility, seasonal availability

#### Kitchen (Aggregate Root)

- **Properties**: Capacity, Current Load, Queue, Staff Assignment
- **Business Logic**: Capacity management, queue optimization, load balancing
- **Events**: KitchenCapacityChangedEvent, QueueFullEvent
- **Real-time**: Live status updates for dashboard

#### LineItem (Entity)

- **Properties**: Pizza Reference, Quantity, Size, Toppings, Price, Special Instructions
- **Business Logic**: Individual item pricing, customization validation
- **Immutability**: Once order is confirmed, line items are locked

### Value Objects

- **Money**: Currency, amount with precision handling
- **Address**: Street, city, postal code with validation
- **PhoneNumber**: Formatted phone with country code
- **OrderStatus**: Strongly-typed status with transition rules
- **PizzaSize**: Enum with pricing multipliers

## 🔄 CQRS Implementation

### Commands (Write Operations)

- `PlaceOrderCommand` - Create new orders with validation and payment
- `StartCookingCommand` - Begin order preparation with kitchen assignment
- `CompleteOrderCommand` - Mark orders as ready with notification
- `CancelOrderCommand` - Cancel orders with refund processing
- `UpdateOrderStatusCommand` - Status transitions with business rules
- `CreateCustomerProfileCommand` - Register new customers
- `AssignDeliveryCommand` - Assign delivery driver to orders

### Queries (Read Operations)

- `GetOrderByIdQuery` - Retrieve specific order with authorization checks
- `GetActiveOrdersQuery` - Get orders for kitchen dashboard
- `GetOrdersByStatusQuery` - Filter orders by status with pagination
- `GetMenuQuery` - Get available menu items with pricing
- `GetKitchenStatusQuery` - Real-time kitchen capacity and queue
- `GetCustomerProfileQuery` - Customer details and preferences
- `GetOrderHistoryQuery` - Customer order history with filtering
- `GetDeliveryRoutesQuery` - Optimized delivery route planning

### Event Handlers (Domain Event Processing)

- `OrderPlacedHandler` - Send confirmation emails, update inventory
- `CookingStartedHandler` - Notify customer of preparation start
- `OrderReadyHandler` - Trigger delivery assignment, customer notification
- `DeliveryCompletedHandler` - Process payment completion, update loyalty points

All commands and queries are automatically traced with OpenTelemetry via `TracingPipelineBehavior` and include comprehensive error handling with typed results. The observability framework provides three pillars integration with standard endpoints.

## 🎯 Learning Objectives

This sample demonstrates:

1. **Clean Architecture & Domain-Driven Design**

   - Strict layer separation with dependency inversion
   - Rich domain models with business logic and invariants
   - Bounded contexts and aggregate design patterns
   - Ubiquitous language throughout the codebase

2. **CQRS with Distributed Tracing**

   - Complete separation of read and write operations
   - OpenTelemetry tracing for all command/query flows
   - Performance monitoring and bottleneck identification
   - Cross-cutting concerns with pipeline behaviors

3. **Event-Driven Architecture & CloudEvents**

   - Domain events for business workflow coordination
   - CloudEvents standard for external integrations
   - Event sourcing patterns with MongoDB
   - Asynchronous processing and event publishing

4. **Modern Authentication & Authorization**

   - OAuth2/OIDC with Keycloak integration
   - Role-based access control (RBAC) implementation
   - JWT token validation and claims processing
   - Session management for web applications

5. **Multi-Application Architecture**

   - API-first design with separate UI application
   - Different authentication strategies per application type
   - Shared services and dependency injection
   - FastAPI sub-application mounting patterns

6. **Production-Ready Observability (Three Pillars)**

   - Comprehensive OpenTelemetry integration (metrics, tracing, logging)
   - Standard endpoints: `/health`, `/ready`, `/metrics`
   - TracingPipelineBehavior for automatic CQRS tracing
   - Dependency-aware health checks (MongoDB, Keycloak)
   - Grafana dashboards with business KPIs
   - Prometheus metrics collection and alerting
   - OTLP export to centralized collectors

7. **Async Data Persistence**

   - MongoDB with Motor async driver
   - Repository pattern with interface abstractions
   - Unit of Work pattern for transaction management
   - Data consistency and concurrent access handling

8. **Modern Web UI Development**

   - Server-side rendering with Jinja2 templates
   - Modern asset bundling with Parcel
   - SCSS styling with component organization
   - Progressive enhancement and accessibility

9. **Infrastructure as Code**

   - Docker Compose for complete development environment
   - Keycloak configuration and realm management
   - MongoDB initialization with validation schemas
   - Observability stack orchestration (Grafana, Prometheus, etc.)

10. **Testing Strategies**

    - Unit testing with comprehensive mocking
    - Integration testing with live databases
    - API testing with authentication flows
    - Contract testing for event schemas

## � Management Commands

Quick commands for managing the complete environment:

```bash
# Complete stack management
make mario-start              # Start everything (app + observability)
make mario-stop               # Stop everything
make mario-status             # Check all service health
make mario-logs               # View all service logs
make mario-test-data          # Generate sample data

# Data management
make mario-clean-orders       # Remove all orders (keep other data)
make mario-create-menu        # Initialize default pizza menu
make mario-reset              # Complete environment reset

# Monitoring shortcuts
make mario-open               # Open key services in browser
```

See [MARIO_QUICK_REFERENCE.md](./MARIO_QUICK_REFERENCE.md) for detailed setup and operational guidance.

## �🔗 Related Documentation

### Framework Features

- [Getting Started](../../docs/getting-started.md) - Framework setup and basics
- [CQRS & Mediation](../../docs/features/cqrs-mediation.md) - Command/Query patterns
- [MVC Controllers](../../docs/features/mvc-controllers.md) - API and UI controller development
- [Data Access](../../docs/features/data-access.md) - Repository patterns and MongoDB
- [Dependency Injection](../../docs/features/dependency-injection.md) - Service registration
- [OpenTelemetry Guide](../../docs/guides/otel-framework-integration-analysis.md) - Observability setup

### Sample Documentation

- [Mario's Pizzeria Overview](../../docs/samples/mario-pizzeria.md) - Detailed sample walkthrough
- [Quick Reference](./MARIO_QUICK_REFERENCE.md) - Operational commands and URLs
- [Migration Notes](./notes/migrations/) - Framework upgrade guidance

## 📞 Support & Contribution

This sample is part of the Neuroglia Python framework ecosystem:

- **Framework Documentation**: [docs/](../../docs/)
- **Sample Applications**: [samples/](../)
- **Framework Issues**: Create an issue in the main repository
- **Sample Issues**: Use the mario-pizzeria label for sample-specific issues

### Development Notes

- **Framework Version**: Neuroglia v0.4.8+ with enhanced observability
- **Python Version**: 3.11+
- **Key Dependencies**: FastAPI, MongoDB Motor, Keycloak, OpenTelemetry
- **Observability Stack**: Grafana, Prometheus, Loki, Tempo, OTEL Collector
- **Development Setup**: Docker Compose with hot reload support
- **Production Ready**: Complete observability, security, and deployment configurations

### Recent Updates

- **Enhanced Observability**: Integrated three pillars (metrics, tracing, logging)
- **Standard Endpoints**: `/health`, `/ready`, `/metrics` for modern deployment
- **TracingPipelineBehavior**: Automatic CQRS operation tracing
- **ApplicationSettingsWithObservability**: Comprehensive configuration management
- **OTLP Export**: Proper OpenTelemetry collector integration
