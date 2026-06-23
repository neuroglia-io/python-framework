# ⚡ 3-Minute Bootstrap: Hello World

Get up and running with Neuroglia in under 3 minutes! This quick-start guide gets you from zero to a working API in the fastest way possible.

!!! tip "🚀 Want a Production-Ready Starting Point?"
For a fully-featured application template with authentication, frontend, and all common concerns pre-configured, check out the [**Starter App Repository**](https://bvandewe.github.io/starter-app/). This guide shows the minimal hello-world approach.

!!! info "🎯 What You'll Build"
A minimal "Hello Pizzeria" API with one endpoint that demonstrates the basic framework setup.## 🚀 Quick Setup

### Prerequisites

- Python 3.8+ installed
- pip package manager

### Installation

```bash
# Create new directory
mkdir hello-pizzeria && cd hello-pizzeria

# Install Neuroglia
pip install neuroglia-python[web]
```

## 📝 Create Your First API

Create `main.py`:

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mvc import ControllerBase
from classy_fastapi.decorators import get

class HelloController(ControllerBase):
    """Simple hello world controller"""

    @get("/hello")
    async def hello_world(self) -> dict:
        """Say hello to Mario's Pizzeria!"""
        return {
            "message": "Welcome to Mario's Pizzeria! 🍕",
            "status": "We're open for business!",
            "framework": "Neuroglia Python"
        }

def create_app():
    """Create the web application"""
    builder = WebApplicationBuilder()

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            controllers=[HelloController]
        )
    )

    # Build app
    app = builder.build()

    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🏃‍♂️ Run Your API

```bash
python main.py
```

## 🎉 Test Your API

Open your browser and visit:

- **API Endpoint**: [http://localhost:8000/hello](http://localhost:8000/hello)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

You should see:

```json
{
  "message": "Welcome to Mario's Pizzeria! 🍕",
  "status": "We're open for business!",
  "framework": "Neuroglia Python"
}
```

## ✅ What You've Accomplished

In just 3 minutes, you've created:

- ✅ A working FastAPI application with Neuroglia
- ✅ Automatic API documentation (Swagger UI)
- ✅ Controller-based routing with clean architecture
- ✅ Automatic module discovery
- ✅ Dependency injection container setup

## 🔄 Next Steps

Now that you have the basics working:

1. **[🛠️ Local Development Setup](local-development.md)** - Set up a proper development environment
2. **[🍕 Mario's Pizzeria Tutorial](mario-pizzeria-tutorial.md)** - Build a complete application (1 hour)
3. **[🎯 Architecture Patterns](../patterns/index.md)** - Learn the design principles
4. **[🚀 Framework Features](../features/index.md)** - Explore advanced capabilities

## 🔗 Key Concepts Introduced

This hello world example demonstrates:

- **[Controller Pattern](../patterns/clean-architecture.md#api-layer)** - Web request handling
- **[Dependency Injection](../patterns/dependency-injection.md)** - Service container setup
- **[WebApplicationBuilder](../features/mvc-controllers.md)** - Application bootstrapping

---

!!! tip "🎯 Pro Tip"
This is just the beginning! The framework includes powerful features like CQRS, event sourcing, and advanced data access patterns. Continue with the [Local Development Setup](local-development.md) to explore more.
