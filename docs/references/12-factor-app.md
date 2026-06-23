# 🏭 The Twelve-Factor App with Neuroglia

The [Twelve-Factor App](https://12factor.net/) is a methodology for building software-as-a-service applications that
are portable, scalable, and maintainable. The Neuroglia framework was designed from the ground up to support and
enforce these principles, making it easy to build cloud-native applications that follow best practices.

## 🎯 What You'll Learn

- How each of the 12 factors applies to modern cloud-native applications
- How Neuroglia framework features directly support 12-factor compliance
- Practical implementation patterns using Mario's Pizzeria as an example
- Best practices for deploying and managing 12-factor applications

---

## I. Codebase 📁

**Principle**: _One codebase tracked in revision control, many deploys_

### Requirements

- Single codebase in version control (Git)
- Multiple deployments from same codebase (dev, staging, production)
- No shared code between apps - use libraries instead

### How Neuroglia Supports This

The framework enforces clean separation of concerns through its modular architecture:

```python
# Single codebase structure
src/
├── marios_pizzeria/           # Single application codebase
│   ├── api/                   # API layer
│   ├── application/           # Business logic
│   ├── domain/                # Core domain
│   └── integration/           # External integrations
├── shared_libs/               # Reusable libraries
│   └── neuroglia/            # Framework as separate library
└── deployment/                # Environment-specific configs
    ├── dev/
    ├── staging/
    └── production/
```

**Example**: Mario's Pizzeria has one codebase but deploys to multiple environments:

```python
# main.py - Same code, different configs
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper

def create_app():
    builder = WebApplicationBuilder()

    # Configuration varies by environment
    # but same codebase everywhere
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos"])

    builder.add_sub_app(
        SubAppConfig(path="/api", name="api", controllers=["api.controllers"])
    )

    return builder.build()
```

---

## II. Dependencies 📦

**Principle**: _Explicitly declare and isolate dependencies_

### Requirements

- Explicit dependency declaration
- Dependency isolation (no system-wide packages)
- No implicit dependencies on system tools

### How Neuroglia Supports This

The framework uses Poetry and virtual environments for complete dependency isolation:

```toml
# pyproject.toml - Explicit dependency declaration
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
pydantic = "^2.4.0"
motor = "^3.3.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
```

**Dependency Injection Container** ensures services are properly declared:

```python
from neuroglia.dependency_injection import ServiceLifetime
from neuroglia.mediation import Mediator

def configure_services(builder):
    # Explicit service dependencies
    builder.services.add_singleton(OrderService)
    builder.services.add_scoped(PizzaRepository, MongoDbPizzaRepository)
    builder.services.add_transient(EmailService, SmtpEmailService)

    # Framework handles dependency resolution
    Mediator.configure(builder, ["application.commands", "application.queries"])
```

**No System Dependencies** - Everything runs in isolated containers:

```dockerfile
# Dockerfile - Isolated environment
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
COPY src/ ./src/
CMD ["poetry", "run", "python", "main.py"]
```

---

## III. Config ⚙️

**Principle**: _Store config in the environment_

### Requirements

- Configuration in environment variables
- Strict separation of config from code
- No passwords or API keys in code

### How Neuroglia Supports This

**Environment-Based Configuration**:

```python
import os
from pydantic import BaseSettings

class AppSettings(BaseSettings):
    # Database configuration
    mongodb_connection_string: str
    database_name: str = "marios_pizzeria"

    # External service configuration
    payment_api_key: str
    email_smtp_host: str
    email_smtp_port: int = 587

    # Application configuration
    jwt_secret_key: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage in application
settings = AppSettings()

services.add_singleton(AppSettings, lambda _: settings)
```

**Environment-Specific Deployment**:

```bash
# Development environment
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
export PAYMENT_API_KEY="test_key_123"
export JWT_SECRET_KEY="dev-secret"

# Production environment
export MONGODB_CONNECTION_STRING="mongodb://prod-cluster:27017/marios"
export PAYMENT_API_KEY="pk_live_abc123"
export JWT_SECRET_KEY="$(openssl rand -base64 32)"
```

**Configuration Injection**:

```python
class OrderController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase,
                 mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        # Settings injected automatically
        self._settings = service_provider.get_service(AppSettings)

    @post("/orders")
    async def create_order(self, order_dto: CreateOrderDto):
        # Use configuration without hardcoding
        if self._settings.payment_api_key:
            # Process payment
            pass
```

---

## IV. Backing Services 🔌

**Principle**: _Treat backing services as attached resources_

### Requirements

- Database, message queues, caches as attached resources
- No distinction between local and third-party services
- Services attachable via configuration

### How Neuroglia Supports This

**Repository Pattern** abstracts backing services:

```python
# Abstract repository - same interface for all backing services
from abc import ABC, abstractmethod

class PizzaRepository(ABC):
    @abstractmethod
    async def save_async(self, pizza: Pizza) -> None:
        pass

    @abstractmethod
    async def get_by_id_async(self, pizza_id: str) -> Optional[Pizza]:
        pass

# MongoDB implementation
class MongoDbPizzaRepository(PizzaRepository):
    def __init__(self, connection_string: str):
        self._client = AsyncIOMotorClient(connection_string)

    async def save_async(self, pizza: Pizza) -> None:
        await self._collection.insert_one(pizza.to_dict())

# In-memory implementation (for testing)
class InMemoryPizzaRepository(PizzaRepository):
    def __init__(self):
        self._store = {}

    async def save_async(self, pizza: Pizza) -> None:
        self._store[pizza.id] = pizza
```

**Service Registration** based on environment:

```python
def configure_backing_services(services, settings: AppSettings):
    # Database service - swappable via config
    if settings.environment == "production":
        services.add_scoped(PizzaRepository,
            lambda sp: MongoDbPizzaRepository(settings.mongodb_connection_string))
    else:
        services.add_scoped(PizzaRepository, InMemoryPizzaRepository)

    # Cache service - Redis in prod, memory in dev
    if settings.redis_url:
        services.add_singleton(CacheService,
            lambda sp: RedisCacheService(settings.redis_url))
    else:
        services.add_singleton(CacheService, InMemoryCacheService)

    # Message queue - RabbitMQ in prod, in-memory in dev
    if settings.rabbitmq_url:
        services.add_scoped(EventBus,
            lambda sp: RabbitMqEventBus(settings.rabbitmq_url))
    else:
        services.add_scoped(EventBus, InMemoryEventBus)
```

**Service Abstraction** through dependency injection:

```python
class ProcessOrderHandler(CommandHandler[ProcessOrderCommand, OperationResult]):
    def __init__(self, pizza_repository: PizzaRepository,
                 cache_service: CacheService,
                 event_bus: EventBus):
        # Handler doesn't know which implementations it's using
        self._pizza_repository = pizza_repository
        self._cache_service = cache_service
        self._event_bus = event_bus

    async def handle_async(self, command: ProcessOrderCommand):
        # Same code works with any backing service implementation
        pizza = await self._pizza_repository.get_by_id_async(command.pizza_id)
        await self._cache_service.set_async(f"order:{command.order_id}", pizza)
        await self._event_bus.publish_async(OrderProcessedEvent(command.order_id))
```

---

## V. Build, Release, Run 🚀

**Principle**: _Strictly separate build and run stages_

### Requirements

- Build stage: convert code into executable bundle
- Release stage: combine build with configuration
- Run stage: execute the release in runtime environment

### How Neuroglia Supports This

**Build Stage** - Create deployable artifacts:

```bash
#!/bin/bash
# build.sh - Build stage
set -e

echo "🔨 Building Neuroglia application..."

# Install dependencies
poetry install --no-dev

# Run tests
poetry run pytest

# Build wheel package
poetry build

echo "✅ Build complete: dist/marios_pizzeria-1.0.0-py3-none-any.whl"
```

**Release Stage** - Combine build with configuration:

```python
# release.py - Release stage
import os
import shutil
from pathlib import Path

def create_release(build_artifact: str, environment: str, version: str):
    release_dir = Path(f"releases/{version}-{environment}")
    release_dir.mkdir(parents=True, exist_ok=True)

    # Copy build artifact
    shutil.copy(build_artifact, release_dir / "app.whl")

    # Copy environment-specific configuration
    env_config = Path(f"deployment/{environment}")
    shutil.copytree(env_config, release_dir / "config")

    # Create release manifest
    manifest = {
        "version": version,
        "environment": environment,
        "build_artifact": "app.whl",
        "configuration": "config/",
        "created_at": datetime.utcnow().isoformat()
    }

    with open(release_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return release_dir
```

**Run Stage** - Execute specific release:

```python
# run.py - Run stage
def run_release(release_path: Path):
    # Load release manifest
    with open(release_path / "manifest.json") as f:
        manifest = json.load(f)

    # Set environment from release configuration
    config_dir = release_path / manifest["configuration"]
    load_environment_from_config(config_dir)

    # Install and run the exact build artifact
    app_wheel = release_path / manifest["build_artifact"]
    subprocess.run(["pip", "install", str(app_wheel)])

    # Start the application
    from marios_pizzeria.main import create_app
    app = create_app()
    app.run()
```

**Docker Integration** for immutable releases:

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /build
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev
COPY src/ ./src/
RUN poetry build

FROM python:3.11-slim as runtime
WORKDIR /app
# Copy only the build artifact
COPY --from=builder /build/dist/*.whl ./
RUN pip install *.whl
# Configuration comes from environment
CMD ["python", "-m", "marios_pizzeria"]
```

---

## VI. Processes 🔄

**Principle**: _Execute the app as one or more stateless processes_

### Requirements

- Processes are stateless and share-nothing
- Persistent data stored in backing services
- No sticky sessions or in-process caching

### How Neuroglia Supports This

**Stateless Design** through dependency injection:

```python
class PizzaController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase,
                 mapper: Mapper, mediator: Mediator):
        # Controller has no instance state
        super().__init__(service_provider, mapper, mediator)

    @get("/pizzas/{pizza_id}")
    async def get_pizza(self, pizza_id: str) -> PizzaDto:
        # All state comes from request and backing services
        query = GetPizzaByIdQuery(pizza_id=pizza_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)
```

**Repository Pattern** for persistent data:

```python
class GetPizzaByIdHandler(QueryHandler[GetPizzaByIdQuery, PizzaDto]):
    def __init__(self, pizza_repository: PizzaRepository, mapper: Mapper):
        self._pizza_repository = pizza_repository  # Stateless service
        self._mapper = mapper

    async def handle_async(self, query: GetPizzaByIdQuery) -> PizzaDto:
        # No process state - all data from backing service
        pizza = await self._pizza_repository.get_by_id_async(query.pizza_id)
        if pizza is None:
            raise NotFoundException(f"Pizza {query.pizza_id} not found")

        return self._mapper.map(pizza, PizzaDto)
```

**Process Scaling** configuration:

```yaml
# docker-compose.yml - Horizontal scaling
version: "3.8"
services:
  web:
    image: marios-pizzeria:latest
    ports:
      - "8000-8003:8000" # Multiple process instances
    environment:
      - MONGODB_CONNECTION_STRING=${MONGODB_URL}
      - REDIS_URL=${REDIS_URL}
    deploy:
      replicas: 4 # 4 stateless processes

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - web
    # Load balancer - no session affinity needed
```

**Session State** externalization:

```python
class SessionService:
    def __init__(self, cache_service: CacheService):
        self._cache = cache_service  # External session store

    async def get_user_session(self, session_id: str) -> Optional[UserSession]:
        # Session stored in external cache, not process memory
        return await self._cache.get_async(f"session:{session_id}")

    async def save_user_session(self, session: UserSession) -> None:
        await self._cache.set_async(
            f"session:{session.id}",
            session,
            ttl=timedelta(hours=24)
        )
```

---

## VII. Port Binding 🌐

**Principle**: _Export services via port binding_

### Requirements

- App is self-contained and exports HTTP via port binding
- No reliance on runtime injection by webserver
- One app can become backing service for another

### How Neuroglia Supports This

**Self-Contained HTTP Server**:

```python
# main.py - Self-contained application
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper
import uvicorn

def create_app():
    builder = WebApplicationBuilder()

    # Configure core services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos"])

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(path="/api", name="api", controllers=["api.controllers"])
    )

    # Build FastAPI application
    app = builder.build()

    return app

if __name__ == "__main__":
    app = create_app()

    # Self-contained HTTP server via port binding
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**Port Configuration** via environment:

```python
class ServerSettings(BaseSettings):
    port: int = 8000
    host: str = "0.0.0.0"
    workers: int = 1

    class Config:
        env_prefix = "SERVER_"

def run_server():
    settings = ServerSettings()
    app = create_app()

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        workers=settings.workers
    )
```

**Service-to-Service Communication**:

```python
# Pizza service exports HTTP interface
class PizzaServiceClient:
    def __init__(self, base_url: str):
        self._base_url = base_url  # Port-bound service URL
        self._client = httpx.AsyncClient()

    async def get_pizza_async(self, pizza_id: str) -> PizzaDto:
        # Call another 12-factor app via its port binding
        response = await self._client.get(f"{self._base_url}/pizzas/{pizza_id}")
        return PizzaDto.model_validate(response.json())

# Order service uses Pizza service as backing service
class OrderService:
    def __init__(self, pizza_service: PizzaServiceClient):
        self._pizza_service = pizza_service

    async def create_order_async(self, order: CreateOrderRequest) -> Order:
        # Verify pizza exists via HTTP call
        pizza = await self._pizza_service.get_pizza_async(order.pizza_id)
        # Create order...
```

**Docker Port Mapping**:

```dockerfile
# Dockerfile - Port binding configuration
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Expose port for binding
EXPOSE 8000

# Run self-contained server
CMD ["python", "main.py"]
```

---

## VIII. Concurrency 🔀

**Principle**: _Scale out via the process model_

### Requirements

- Scale horizontally by adding more processes
- Different process types for different work
- Processes handle their own internal multiplexing

### How Neuroglia Supports This

**Process Types** definition:

````python
**Process Types** definition:

```python
# Different process types for different workloads
# web.py - HTTP request handler processes
def create_web_app():
    builder = WebApplicationBuilder()
    Mediator.configure(builder, ["application.commands", "application.queries"])
    builder.add_sub_app(
        SubAppConfig(path="/api", name="api", controllers=["api.controllers"])
    )
    return builder.build()

# worker.py - Background task processes
def create_worker_app():
    builder = WebApplicationBuilder()
    Mediator.configure(builder, ["application.handlers"])
    builder.services.add_background_tasks()
````

# scheduler.py - Periodic task processes

def create_scheduler_app():
builder = WebApplicationBuilder()
services = builder.services
services.add_scheduled_tasks()
return builder.build()

````

**Process Scaling** configuration:

```yaml
# Procfile - Process type definitions
web: python web.py
worker: python worker.py
scheduler: python scheduler.py
````

**Horizontal Scaling** with different process counts:

```yaml
# docker-compose.yml
version: "3.8"
services:
  web:
    image: marios-pizzeria:latest
    command: python web.py
    ports:
      - "8000-8003:8000"
    deploy:
      replicas: 4 # 4 web processes

  worker:
    image: marios-pizzeria:latest
    command: python worker.py
    deploy:
      replicas: 2 # 2 worker processes

  scheduler:
    image: marios-pizzeria:latest
    command: python scheduler.py
    deploy:
      replicas: 1 # 1 scheduler process
```

**Internal Multiplexing** with async/await:

```python
class OrderController(ControllerBase):
    @post("/orders")
    async def create_order(self, order_dto: CreateOrderDto):
        # Single process handles multiple concurrent requests
        # via async/await internal multiplexing
        command = self.mapper.map(order_dto, CreateOrderCommand)
        result = await self.mediator.execute_async(command)
        return self.process(result)

class BackgroundTaskService(HostedService):
    async def start_async(self, cancellation_token):
        # Single worker process handles multiple tasks concurrently
        tasks = [
            self.process_emails(),
            self.process_notifications(),
            self.process_analytics()
        ]
        await asyncio.gather(*tasks)

    async def process_emails(self):
        while True:
            # Internal multiplexing within single process
            async for email in self.email_queue:
                await self.send_email(email)
```

**Process Management** with supervision:

```python
# supervisor.conf - Process supervision
[program:marios-web]
command=python web.py
numprocs=4
autostart=true
autorestart=true

[program:marios-worker]
command=python worker.py
numprocs=2
autostart=true
autorestart=true
```

---

## IX. Disposability ♻️

**Principle**: _Maximize robustness with fast startup and graceful shutdown_

### Requirements

- Fast startup for elastic scaling
- Graceful shutdown on SIGTERM
- Robust against sudden termination

### How Neuroglia Supports This

**Fast Startup** through optimized initialization:

```python
class WebApplicationBuilder:
    def build(self) -> FastAPI:
        app = FastAPI(
            title="Mario's Pizzeria API",
            # Fast startup - minimal initialization
            docs_url="/docs" if self._is_development else None,
            redoc_url="/redoc" if self._is_development else None
        )

        # Lazy service initialization
        app.state.service_provider = LazyServiceProvider(self._services)

        # Fast health check endpoint
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.utcnow()}

        return app

def create_app():
    # Optimized for fast startup
    builder = WebApplicationBuilder()

    # Register services (no initialization yet)
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos"])

    builder.add_sub_app(
        SubAppConfig(path="/api", name="api", controllers=["api.controllers"])
    )

    # Build returns immediately
    return builder.build()
```

**Graceful Shutdown** handling:

```python
import signal
import asyncio
from contextlib import asynccontextmanager

class GracefulShutdownHandler:
    def __init__(self, app: FastAPI):
        self._app = app
        self._shutdown_event = asyncio.Event()
        self._background_tasks = set()

    def setup_signal_handlers(self):
        # Handle SIGTERM gracefully
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self._graceful_shutdown())

    async def _graceful_shutdown(self):
        # Stop accepting new requests
        self._app.state.accepting_requests = False

        # Wait for current requests to complete (max 30 seconds)
        try:
            await asyncio.wait_for(
                self._wait_for_requests_to_complete(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            print("Timeout waiting for requests to complete")

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Close connections
        if hasattr(self._app.state, 'database'):
            await self._app.state.database.close()

        self._shutdown_event.set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    shutdown_handler = GracefulShutdownHandler(app)
    shutdown_handler.setup_signal_handlers()

    yield

    # Shutdown
    await shutdown_handler._shutdown_event.wait()

def create_app():
    return FastAPI(lifespan=lifespan)
```

**Background Task Resilience**:

```python
class BackgroundTaskService(HostedService):
    async def start_async(self, cancellation_token):
        while not cancellation_token.is_cancelled:
            try:
                # Process work with checkpoints
                async for work_item in self.get_work_items():
                    if cancellation_token.is_cancelled:
                        # Return work to queue on shutdown
                        await self.return_to_queue(work_item)
                        break

                    await self.process_work_item(work_item)

            except Exception as ex:
                # Log error but continue running
                self._logger.error(f"Background task error: {ex}")
                await asyncio.sleep(5)  # Brief pause before retry

class OrderProcessingService:
    async def process_order(self, order_id: str):
        # Idempotent processing - safe to retry
        order = await self._repository.get_by_id_async(order_id)
        if order.status == OrderStatus.COMPLETED:
            return  # Already processed

        # Process with database transaction
        async with self._repository.begin_transaction():
            order.status = OrderStatus.PROCESSING
            await self._repository.save_async(order)

            # Do work...

            order.status = OrderStatus.COMPLETED
            await self._repository.save_async(order)
```

**Container Health Checks**:

```dockerfile
# Dockerfile with health check
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Health check for fast failure detection
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
```

---

## X. Dev/Prod Parity 🔄

**Principle**: _Keep development, staging, and production as similar as possible_

### Requirements

- Minimize time gap between development and production
- Same people involved in development and deployment
- Use same backing services in all environments

### How Neuroglia Supports This

**Same Backing Services** across environments:

```python
# Use same service types everywhere
class DatabaseSettings(BaseSettings):
    connection_string: str
    database_name: str

    @property
    def is_mongodb(self) -> bool:
        return self.connection_string.startswith("mongodb://")

def configure_database(services, settings: DatabaseSettings):
    if settings.is_mongodb:
        # MongoDB in all environments (dev uses local, prod uses cluster)
        services.add_scoped(
            PizzaRepository,
            lambda sp: MongoDbPizzaRepository(settings.connection_string)
        )
    else:
        # Don't use SQLite in dev and PostgreSQL in prod
        # Use PostgreSQL everywhere via Docker
        services.add_scoped(
            PizzaRepository,
            lambda sp: PostgreSQLPizzaRepository(settings.connection_string)
        )
```

**Docker Development Environment**:

```yaml
# docker-compose.dev.yml - Same services as production
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - MONGODB_CONNECTION_STRING=mongodb://mongo:27017/marios_dev
      - REDIS_URL=redis://redis:6379
    depends_on:
      - mongo
      - redis

  mongo:
    image: mongo:7.0 # Same version as production
    ports:
      - "27017:27017"

  redis:
    image: redis:7.2 # Same version as production
    ports:
      - "6379:6379"
```

**Environment Parity Validation**:

```python
class EnvironmentValidator:
    def __init__(self, settings: AppSettings):
        self._settings = settings

    def validate_parity(self):
        """Ensure dev/staging/prod use compatible services"""
        warnings = []

        # Check database compatibility
        if self._settings.environment == "development":
            if "sqlite" in self._settings.mongodb_connection_string.lower():
                warnings.append(
                    "Development uses SQLite but production uses MongoDB. "
                    "Use MongoDB in development for better parity."
                )

        # Check cache compatibility
        if not self._settings.redis_url and self._settings.environment != "test":
            warnings.append(
                "No Redis configuration found. "
                "Use Redis in all environments for dev/prod parity."
            )

        return warnings

# Application startup validation
def create_app():
    settings = AppSettings()
    validator = EnvironmentValidator(settings)

    parity_warnings = validator.validate_parity()
    if parity_warnings:
        for warning in parity_warnings:
            logger.warning(f"Dev/Prod Parity: {warning}")

    builder = WebApplicationBuilder()
    # ... configure app
    return builder.build()
```

**Continuous Deployment Pipeline**:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongo:
        image: mongo:7.0
      redis:
        image: redis:7.2
    steps:
      - uses: actions/checkout@v3
      - name: Run tests against production-like services
        run: |
          export MONGODB_CONNECTION_STRING=mongodb://mongo:27017/test
          export REDIS_URL=redis://redis:6379
          poetry run pytest

  deploy-staging:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: |
          # Same deployment process as production
          docker build -t marios-pizzeria:${{ github.sha }} .
          docker push registry/marios-pizzeria:${{ github.sha }}
          kubectl set image deployment/app app=registry/marios-pizzeria:${{ github.sha }}

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Identical process to staging
          kubectl set image deployment/app app=registry/marios-pizzeria:${{ github.sha }}
```

---

## XI. Logs 📊

**Principle**: _Treat logs as event streams_

### Requirements

- Write unbuffered logs to stdout
- No log file management by the application
- Log aggregation handled by execution environment

### How Neuroglia Supports This

**Structured Logging** to stdout:

```python
import structlog
import sys

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()  # JSON for structured logs
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Application logger - writes to stdout only
logger = structlog.get_logger()

class OrderController(ControllerBase):
    @post("/orders")
    async def create_order(self, order_dto: CreateOrderDto):
        # Structured logging with context
        logger.info(
            "Order creation started",
            customer_id=order_dto.customer_id,
            pizza_count=len(order_dto.pizzas),
            total_amount=order_dto.total_amount,
            correlation_id=self.get_correlation_id()
        )

        try:
            command = self.mapper.map(order_dto, CreateOrderCommand)
            result = await self.mediator.execute_async(command)

            logger.info(
                "Order created successfully",
                order_id=result.value.id,
                correlation_id=self.get_correlation_id()
            )

            return self.process(result)

        except Exception as ex:
            logger.error(
                "Order creation failed",
                error=str(ex),
                error_type=type(ex).__name__,
                correlation_id=self.get_correlation_id()
            )
            raise
```

**Request/Response Logging Middleware**:

```python
import time
from fastapi import Request, Response

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = time.time()

        # Log request
        logger.info(
            "HTTP request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host if request.client else None
        )

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Log response
                duration = time.time() - start_time
                logger.info(
                    "HTTP request completed",
                    method=request.method,
                    path=request.url.path,
                    status_code=message["status"],
                    duration_ms=round(duration * 1000, 2)
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)

# Add middleware to application
def create_app():
    builder = WebApplicationBuilder()
    app = builder.build()

    # Add logging middleware
    app.add_middleware(LoggingMiddleware)

    return app
```

**No Log File Management**:

```python
# main.py - No log files, only stdout
import logging
import sys

def configure_logging():
    # Only configure stdout handler
    root_logger = logging.getLogger()

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Add only stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )

    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(logging.INFO)

if __name__ == "__main__":
    configure_logging()  # No file handlers
    app = create_app()

    # Application logs go to stdout, captured by container runtime
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
```

**Log Aggregation** via deployment environment:

```yaml
# kubernetes deployment with log aggregation
apiVersion: apps/v1
kind: Deployment
metadata:
  name: marios-pizzeria
spec:
  template:
    spec:
      containers:
        - name: app
          image: marios-pizzeria:latest
          # Logs go to stdout, captured by Kubernetes
          env:
            - name: LOG_LEVEL
              value: "INFO"
          # No volume mounts for log files
---
# Fluentd configuration for log aggregation
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/marios-pizzeria-*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      format json
    </source>

    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name marios-pizzeria
    </match>
```

---

## XII. Admin Processes 🔧

**Principle**: _Run admin/management tasks as one-off processes_

### Requirements

- Admin tasks run in identical environment as regular processes
- Use same codebase and configuration
- Run against specific releases

### How Neuroglia Supports This

**Admin Command Framework**:

```python
# cli/admin.py - Admin process framework
import asyncio
import sys
from abc import ABC, abstractmethod
from neuroglia.hosting.web import WebApplicationBuilder

class AdminCommand(ABC):
    @abstractmethod
    async def execute_async(self, service_provider) -> int:
        """Execute admin command, return exit code"""
        pass

class MigrateDatabaseCommand(AdminCommand):
    async def execute_async(self, service_provider) -> int:
        logger.info("Starting database migration...")

        try:
            # Use same services as web processes
            repository = service_provider.get_service(PizzaRepository)
            await repository.migrate_schema_async()

            logger.info("Database migration completed successfully")
            return 0

        except Exception as ex:
            logger.error(f"Database migration failed: {ex}")
            return 1

class SeedDataCommand(AdminCommand):
    async def execute_async(self, service_provider) -> int:
        logger.info("Seeding initial data...")

        try:
            # Use same repositories as application
            pizza_repo = service_provider.get_service(PizzaRepository)

            # Create default pizzas
            default_pizzas = [
                Pizza("margherita", "Margherita", 12.99),
                Pizza("pepperoni", "Pepperoni", 14.99),
                Pizza("hawaiian", "Hawaiian", 15.99)
            ]

            for pizza in default_pizzas:
                await pizza_repo.save_async(pizza)

            logger.info(f"Seeded {len(default_pizzas)} default pizzas")
            return 0

        except Exception as ex:
            logger.error(f"Data seeding failed: {ex}")
            return 1

# Admin process runner
async def run_admin_command(command_name: str) -> int:
    # Create same application context as web processes
    builder = WebApplicationBuilder()

    # Same service configuration as main application
    builder.services.add_scoped(PizzaRepository, MongoDbPizzaRepository)
    Mediator.configure(builder, ["application.commands"])

    service_provider = builder.services.build_provider()

    # Map commands
    commands = {
        "migrate": MigrateDatabaseCommand(),
        "seed": SeedDataCommand(),
    }

    if command_name not in commands:
        logger.error(f"Unknown command: {command_name}")
        return 1
```

    # Execute command with same environment
    return await commands[command_name].execute_async(service_provider)

if **name** == "**main**":
if len(sys.argv) != 2:
print("Usage: python admin.py <command>")
sys.exit(1)

    command = sys.argv[1]
    exit_code = asyncio.run(run_admin_command(command))
    sys.exit(exit_code)

````

**Container-Based Admin Tasks**:

```dockerfile
# Same image for web and admin processes
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Default command is web process
CMD ["python", "main.py"]

# Admin processes use same image with different command
# docker run marios-pizzeria:latest python admin.py migrate
# docker run marios-pizzeria:latest python admin.py seed
````

**Kubernetes Jobs** for admin processes:

```yaml
# Database migration job
apiVersion: batch/v1
kind: Job
metadata:
  name: marios-pizzeria-migrate
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: marios-pizzeria:v1.2.3 # Same image as web deployment
          command: ["python", "admin.py", "migrate"]
          env:
            # Same environment as web processes
            - name: MONGODB_CONNECTION_STRING
              valueFrom:
                secretKeyRef:
                  name: database-secret
                  key: connection-string
            - name: ENVIRONMENT
              value: "production"
      restartPolicy: OnFailure
---
# Data seeding job
apiVersion: batch/v1
kind: Job
metadata:
  name: marios-pizzeria-seed
spec:
  template:
    spec:
      containers:
        - name: seed
          image: marios-pizzeria:v1.2.3 # Exact same release
          command: ["python", "admin.py", "seed"]
          env:
            # Identical configuration
            - name: MONGODB_CONNECTION_STRING
              valueFrom:
                secretKeyRef:
                  name: database-secret
                  key: connection-string
      restartPolicy: OnFailure
```

**Production Admin Process Examples**:

```bash
# Run admin processes in production using same deployment
# Database migration before release
kubectl create job --from=deployment/marios-pizzeria migrate-v1-2-3 \
  --dry-run=client -o yaml | \
  sed 's/app/migrate/' | \
  sed 's/main.py/admin.py migrate/' | \
  kubectl apply -f -

# One-off data fix
kubectl run data-fix --image=marios-pizzeria:v1.2.3 \
  --env="MONGODB_CONNECTION_STRING=$PROD_DB" \
  --restart=Never \
  --rm -it -- python admin.py fix-corrupted-orders

# Interactive shell for debugging
kubectl run debug-shell --image=marios-pizzeria:v1.2.3 \
  --env="MONGODB_CONNECTION_STRING=$PROD_DB" \
  --restart=Never \
  --rm -it -- python -c "
from main import create_app
app = create_app()
# Interactive Python shell with full application context
import IPython; IPython.embed()
"
```

---

## 🎯 Summary

The Neuroglia framework was designed from the ground up to support the Twelve-Factor App methodology. Here's how each principle is addressed:

| Factor                   | Neuroglia Support                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------ |
| **I. Codebase**          | Modular architecture with clean separation, single codebase for multiple deployments |
| **II. Dependencies**     | Poetry dependency management, dependency injection container, Docker isolation       |
| **III. Config**          | Pydantic settings with environment variables, no hardcoded configuration             |
| **IV. Backing Services** | Repository pattern, service abstractions, configurable implementations               |
| **V. Build/Release/Run** | Docker builds, immutable releases, environment-specific deployments                  |
| **VI. Processes**        | Stateless controllers, repository persistence, horizontal scaling support            |
| **VII. Port Binding**    | Self-contained FastAPI server, uvicorn HTTP binding, service-to-service HTTP         |
| **VIII. Concurrency**    | Process types, async/await concurrency, container orchestration                      |
| **IX. Disposability**    | Fast startup, graceful shutdown handlers, idempotent operations                      |
| **X. Dev/Prod Parity**   | Docker dev environments, same backing services, continuous deployment                |
| **XI. Logs**             | Structured logging to stdout, no file management, aggregation-ready                  |
| **XII. Admin Processes** | CLI command framework, same environment as web processes, container jobs             |

## 🚀 Building 12-Factor Apps with Neuroglia

When building applications with Neuroglia, following these patterns ensures your application is:

- **Portable**: Runs consistently across different environments
- **Scalable**: Horizontal scaling through stateless processes
- **Maintainable**: Clean separation of concerns and dependency management
- **Observable**: Comprehensive logging and health monitoring
- **Resilient**: Graceful handling of failures and shutdowns
- **Cloud-Native**: Ready for container orchestration and continuous deployment

The framework's opinionated architecture guides you toward 12-factor compliance naturally, making it easier to build modern, cloud-native applications that follow industry best practices.

## 🔗 Related Documentation

- [Getting Started](../getting-started.md) - Framework setup and basic usage
- [Dependency Injection](../patterns/dependency-injection.md) - Service container and lifetime management
- [CQRS & Mediation](../patterns/cqrs.md) - Command and query patterns
- [MVC Controllers](../features/mvc-controllers.md) - HTTP API development
- [Data Access](../features/data-access.md) - Repository pattern and backing services
- [OpenBank Sample](../samples/openbank.md) - Complete 12-factor application example
