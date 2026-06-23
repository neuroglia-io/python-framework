# Part 1: Project Setup & Structure

**Time: 30 minutes** | **Prerequisites: Python 3.11+, Poetry**

Welcome to the Mario's Pizzeria tutorial series! In this first part, you'll set up your development environment and understand the project structure that supports clean architecture principles.

## 🎯 What You'll Learn

By the end of this tutorial, you'll understand:

- How to structure a Neuroglia application using clean architecture layers
- The role of the `WebApplicationBuilder` in bootstrapping applications
- How dependency injection works in the framework
- How to configure multiple sub-applications (API + UI)

## 📦 Project Setup

### 1. Install Dependencies

First, let's install the framework and required packages:

```bash
# Create a new project directory
mkdir mario-pizzeria
cd mario-pizzeria

# Initialize poetry project
poetry init -n

# Add Neuroglia framework
poetry add neuroglia

# Add additional dependencies
poetry add fastapi uvicorn motor pymongo
poetry add python-multipart jinja2  # For UI support
poetry add starlette  # For session middleware

# Install all dependencies
poetry install
```

### 2. Create Directory Structure

Neuroglia enforces **clean architecture** with strict layer separation. Create this structure:

```bash
mario-pizzeria/
├── main.py                    # Application entry point
├── api/                       # 🌐 API Layer (REST controllers, DTOs)
│   ├── __init__.py
│   ├── controllers/
│   │   └── __init__.py
│   └── dtos/
│       └── __init__.py
├── application/               # 💼 Application Layer (Commands, Queries, Handlers)
│   ├── __init__.py
│   ├── commands/
│   │   └── __init__.py
│   ├── queries/
│   │   └── __init__.py
│   ├── events/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
├── domain/                    # 🏛️ Domain Layer (Entities, Business Rules)
│   ├── __init__.py
│   ├── entities/
│   │   └── __init__.py
│   └── repositories/
│       └── __init__.py
├── integration/               # 🔌 Integration Layer (Database, External APIs)
│   ├── __init__.py
│   └── repositories/
│       └── __init__.py
└── ui/                        # Web UI (templates, static files)
    ├── controllers/
    │   └── __init__.py
    └── templates/
```

**Why this structure?**

The **Dependency Rule** states that dependencies only point inward:

```
API → Application → Domain ← Integration
```

- **Domain**: Pure business logic, no external dependencies
- **Application**: Orchestrates domain logic, defines use cases
- **Integration**: Implements technical concerns (database, HTTP clients)
- **API**: Exposes functionality via REST endpoints

This separation makes code testable, maintainable, and replaceable.

## 🚀 Creating the Application Entry Point

Let's create `main.py` - the heart of your application:

```python
#!/usr/bin/env python3
"""
Mario's Pizzeria - A Clean Architecture Sample Application
"""

import logging
from neuroglia.hosting.web import WebApplicationBuilder, SubAppConfig
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper
from neuroglia.serialization.json import JsonSerializer

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def create_pizzeria_app():
    """
    Create Mario's Pizzeria application using WebApplicationBuilder.

    This demonstrates the framework's opinionated approach to application
    bootstrapping with dependency injection and modular configuration.
    """

    # 1️⃣ Create the application builder
    builder = WebApplicationBuilder()

    # 2️⃣ Configure core framework services
    # Mediator: Handles commands and queries (CQRS pattern)
    Mediator.configure(
        builder,
        [
            "application.commands",   # Command handlers
            "application.queries",    # Query handlers
            "application.events"      # Event handlers
        ]
    )

    # Mapper: Object-to-object transformations (entities ↔ DTOs)
    Mapper.configure(
        builder,
        [
            "application.mapping",
            "api.dtos",
            "domain.entities"
        ]
    )

    # JsonSerializer: Type-aware JSON serialization
    JsonSerializer.configure(
        builder,
        [
            "domain.entities"
        ]
    )

    # 3️⃣ Configure sub-applications
    # API sub-app: REST API with JSON responses
    builder.add_sub_app(
        SubAppConfig(
            path="/api",                    # Mounted at /api prefix
            name="api",
            title="Mario's Pizzeria API",
            description="Pizza ordering REST API",
            version="1.0.0",
            controllers=["api.controllers"],  # Auto-discover controllers
            docs_url="/docs",                # OpenAPI docs at /api/docs
        )
    )

    # UI sub-app: Web interface with templates
    builder.add_sub_app(
        SubAppConfig(
            path="/",                       # Mounted at root
            name="ui",
            title="Mario's Pizzeria UI",
            description="Pizza ordering web interface",
            version="1.0.0",
            controllers=["ui.controllers"],
            static_files={"/static": "static"},  # Serve static assets
            templates_dir="ui/templates",        # Jinja2 templates
            docs_url=None,                  # No API docs for UI
        )
    )

    # 4️⃣ Build the complete application
    app = builder.build_app_with_lifespan(
        title="Mario's Pizzeria",
        description="Complete pizza ordering system",
        version="1.0.0",
        debug=True
    )

    log.info("🍕 Mario's Pizzeria is ready!")
    return app


def main():
    """Entry point for running the application"""
    import uvicorn

    print("🍕 Starting Mario's Pizzeria on http://localhost:8080")
    print("📖 API Documentation: http://localhost:8080/api/docs")
    print("🌐 UI: http://localhost:8080/")

    # Run with hot reload for development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )


# Create app instance for uvicorn
app = create_pizzeria_app()

if __name__ == "__main__":
    main()
```

## 🔍 Understanding the Code

### WebApplicationBuilder

The `WebApplicationBuilder` is the **central bootstrapping mechanism** in Neuroglia:

```python
builder = WebApplicationBuilder()
```

It provides:

- **Service Container**: Dependency injection with scoped, singleton, transient lifetimes
- **Configuration**: Automatic scanning and registration
- **Sub-App Support**: Multiple FastAPI apps mounted to a main host
- **Lifespan Management**: Startup/shutdown hooks for resources

### Mediator Pattern

The `Mediator` decouples request handling from execution:

```python
Mediator.configure(builder, ["application.commands", "application.queries"])
```

**Why use mediator?**

❌ **Without Mediator (tight coupling):**

```python
# Controller directly calls service
class PizzaController:
    def __init__(self, pizza_service: PizzaService):
        self.service = pizza_service

    def create_pizza(self, data):
        return self.service.create_pizza(data)  # Direct dependency
```

✅ **With Mediator (loose coupling):**

```python
# Controller sends command to mediator
class PizzaController:
    def __init__(self, mediator: Mediator):
        self.mediator = mediator

    async def create_pizza(self, data):
        command = CreatePizzaCommand(name=data.name)
        return await self.mediator.execute_async(command)  # Mediator routes it
```

The mediator automatically finds and executes the right handler. Controllers stay thin and testable.

### Sub-Application Architecture

Neuroglia supports **multiple FastAPI apps** mounted to a main host:

```python
builder.add_sub_app(SubAppConfig(path="/api", ...))   # API at /api
builder.add_sub_app(SubAppConfig(path="/", ...))      # UI at /
```

**Benefits:**

- **Separation of Concerns**: API logic separate from UI logic
- **Different Authentication**: JWT for API, sessions for UI
- **Independent Documentation**: OpenAPI docs only for API
- **Static File Handling**: Serve assets efficiently for UI

This is **Mario's Pizzeria's actual architecture**.

## 🧪 Test Your Setup

Run the application:

```bash
poetry run python main.py
```

You should see:

```
🍕 Starting Mario's Pizzeria on http://localhost:8080
📖 API Documentation: http://localhost:8080/api/docs
🌐 UI: http://localhost:8080/
INFO:     Started server process
INFO:     Waiting for application startup.
🍕 Mario's Pizzeria is ready!
INFO:     Application startup complete.
```

Visit http://localhost:8080/api/docs - you'll see the OpenAPI documentation (empty for now).

## 📝 Key Takeaways

1. **Clean Architecture Layers**: Domain → Application → API/Integration
2. **WebApplicationBuilder**: Central bootstrapping with DI container
3. **Mediator Pattern**: Decouples controllers from business logic
4. **Sub-Applications**: Multiple FastAPI apps with different concerns
5. **Auto-Discovery**: Framework automatically finds and registers controllers/handlers

## 🚀 What's Next?

In [Part 2: Domain Model](mario-pizzeria-02-domain.md), you'll learn:

- How to create domain entities with business rules
- The difference between `Entity` and `AggregateRoot`
- Domain events and why they matter
- Value objects for type safety

## 💡 Common Issues

**ImportError: No module named 'neuroglia'**

```bash
# Make sure you're in the poetry shell
poetry install
poetry shell
```

**Port 8080 already in use**

```bash
# Change the port in main()
uvicorn.run("main:app", port=8081, ...)
```

**Module not found when running**

```bash
# Run from project root directory
cd mario-pizzeria
poetry run python main.py
```

---

**Next:** [Part 2: Domain Model →](mario-pizzeria-02-domain.md)
