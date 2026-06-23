# Part 9: Deployment & Production

**Time: 30 minutes** | **Prerequisites: [Part 8](mario-pizzeria-08-observability.md)**

In this final tutorial, you'll learn how to containerize and deploy Mario's Pizzeria. You'll create Docker images, orchestrate services with Docker Compose, and configure for production.

## 🎯 What You'll Learn

- Docker containerization for Python apps
- Multi-service orchestration with Docker Compose
- Production configuration and secrets
- Scaling and performance considerations
- Deployment best practices

## 🐳 Containerizing the Application

### Step 1: Create Dockerfile

Create `Dockerfile`:

```dockerfile
# Multi-stage build for smaller images
FROM python:3.11-slim as builder

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev dependencies)
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run application
CMD ["python", "main.py"]
```

**Key features:**

- **Multi-stage build**: Smaller final image
- **Poetry**: Dependency management
- **Health check**: Container health monitoring
- **Non-root user**: Security best practice

### Step 2: Build and Test

```bash
# Build image
docker build -t mario-pizzeria:latest .

# Run container
docker run -d \
  -p 8080:8080 \
  --name mario-app \
  -e MONGODB_URI=mongodb://host.docker.internal:27017 \
  mario-pizzeria:latest

# Check logs
docker logs -f mario-app

# Test
curl http://localhost:8080/health
```

## 🎼 Docker Compose Orchestration

### Step 1: Create docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  # MongoDB database
  mongodb:
    image: mongo:7.0
    container_name: mario-mongodb
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD_FILE: /run/secrets/db_root_password
      MONGO_INITDB_DATABASE: mario_pizzeria
    volumes:
      - mongodb_data:/data/db
      - ./deployment/mongo/init-mario-db.js:/docker-entrypoint-initdb.d/init.js:ro
    secrets:
      - db_root_password
    networks:
      - mario-network
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Mario's Pizzeria application
  mario-app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mario-app
    ports:
      - "8080:8080"
    environment:
      # Database
      MONGODB_URI: mongodb://admin:password@mongodb:27017
      MONGODB_DATABASE: mario_pizzeria

      # Application
      LOG_LEVEL: INFO

      # Observability
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4318
      OTEL_SERVICE_NAME: mario-pizzeria

      # Security
      SESSION_SECRET_KEY_FILE: /run/secrets/session_secret
    depends_on:
      mongodb:
        condition: service_healthy
      otel-collector:
        condition: service_started
    secrets:
      - session_secret
    networks:
      - mario-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector:latest
    container_name: mario-otel-collector
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./deployment/otel/otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317" # OTLP gRPC
      - "4318:4318" # OTLP HTTP
    networks:
      - mario-network

  # Jaeger for tracing
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: mario-jaeger
    ports:
      - "16686:16686" # Jaeger UI
      - "14250:14250" # Collector
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - mario-network

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: mario-prometheus
    volumes:
      - ./deployment/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
    networks:
      - mario-network

  # Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: mario-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD_FILE=/run/secrets/grafana_admin_password
    volumes:
      - ./deployment/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./deployment/grafana/datasources:/etc/grafana/provisioning/datasources
      - grafana_data:/var/lib/grafana
    secrets:
      - grafana_admin_password
    networks:
      - mario-network
    depends_on:
      - prometheus

# Docker secrets (production: use Docker Swarm or Kubernetes secrets)
secrets:
  db_root_password:
    file: ./deployment/secrets/db_root_password.txt
  session_secret:
    file: ./deployment/secrets/session_secret.txt
  grafana_admin_password:
    file: ./deployment/secrets/grafana_admin_password.txt

# Persistent volumes
volumes:
  mongodb_data:
  prometheus_data:
  grafana_data:

# Network
networks:
  mario-network:
    driver: bridge
```

### Step 2: Create Secrets

```bash
# Create secrets directory
mkdir -p deployment/secrets

# Generate secrets
echo "StrongDatabasePassword123!" > deployment/secrets/db_root_password.txt
openssl rand -base64 32 > deployment/secrets/session_secret.txt
echo "admin" > deployment/secrets/grafana_admin_password.txt

# Secure permissions
chmod 600 deployment/secrets/*
```

### Step 3: Start All Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mario-app

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## ⚙️ Production Configuration

### Environment Variables

Create `.env.production`:

```bash
# Database
MONGODB_URI=mongodb://admin:${DB_PASSWORD}@mongodb-cluster:27017/?replicaSet=rs0
MONGODB_DATABASE=mario_pizzeria

# Security
SESSION_SECRET_KEY=${SESSION_SECRET}
JWT_SECRET_KEY=${JWT_SECRET}

# Keycloak
KEYCLOAK_SERVER_URL=https://auth.mario-pizzeria.com
KEYCLOAK_REALM=mario-pizzeria
KEYCLOAK_CLIENT_ID=mario-pizzeria-api

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.mario-pizzeria.com:4318
OTEL_SERVICE_NAME=mario-pizzeria
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # Sample 10% in production

# Application
LOG_LEVEL=WARNING
DEBUG=false
WORKERS=4  # Uvicorn workers
```

### Production main.py

Update for production settings:

```python
import os
from neuroglia.hosting.web import WebApplicationBuilder

def create_pizzeria_app():
    # Load settings based on environment
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        from application.settings import ProductionSettings
        settings = ProductionSettings()
    else:
        from application.settings import DevelopmentSettings
        settings = DevelopmentSettings()

    builder = WebApplicationBuilder(settings)

    # ... configuration ...

    app = builder.build_app_with_lifespan(
        title="Mario's Pizzeria",
        description="Pizza ordering system",
        version="1.0.0",
        debug=(env != "production")
    )

    return app


if __name__ == "__main__":
    import uvicorn

    # Production: Multiple workers
    workers = int(os.getenv("WORKERS", "1"))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        workers=workers,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        proxy_headers=True,  # Behind reverse proxy
        forwarded_allow_ips="*"
    )
```

## 📊 Scaling Considerations

### Horizontal Scaling

Scale app instances:

```bash
# Scale to 3 instances
docker-compose up -d --scale mario-app=3
```

Add load balancer (nginx):

```yaml
# Add to docker-compose.yml
nginx:
  image: nginx:latest
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./deployment/nginx/nginx.conf:/etc/nginx/nginx.conf
    - ./deployment/nginx/ssl:/etc/nginx/ssl
  depends_on:
    - mario-app
  networks:
    - mario-network
```

### Database Replication

MongoDB replica set:

```yaml
services:
  mongodb-primary:
    image: mongo:7.0
    command: --replSet rs0
    # ...

  mongodb-secondary:
    image: mongo:7.0
    command: --replSet rs0
    # ...
```

## 🚀 Deployment Checklist

**Before Production:**

- [ ] Set strong secrets (database, JWT, sessions)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Enable rate limiting
- [ ] Set up monitoring alerts
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Load test application

## 📝 Key Takeaways

1. **Docker**: Containerize for consistency
2. **Docker Compose**: Orchestrate multi-service applications
3. **Secrets Management**: Never commit secrets to git
4. **Health Checks**: Monitor container health
5. **Observability**: Logs, traces, metrics in production
6. **Scaling**: Horizontal scaling with load balancer
7. **Security**: HTTPS, secrets, rate limiting

## 🎉 Congratulations

You've completed the Mario's Pizzeria tutorial series! You now know how to:

✅ Set up clean architecture projects with Neuroglia
✅ Model domains with DDD patterns
✅ Implement CQRS with commands and queries
✅ Build REST APIs with FastAPI
✅ Use event-driven architecture
✅ Persist data with repositories
✅ Secure applications with auth
✅ Add observability with OpenTelemetry
✅ Deploy with Docker

## 🔗 Additional Resources

- [Neuroglia Documentation](../index.md)
- [Core Concepts](../concepts/index.md)
- [Feature Guides](../features/index.md)
- [Pattern Examples](../patterns/index.md)
- [Mario's Pizzeria Case Study](../mario-pizzeria.md)

## 💬 Get Help

- GitHub Issues: [Report bugs or request features](https://github.com/neuroglia-io/python-framework)
- Discussions: [Ask questions and share ideas](https://github.com/neuroglia-io/python-framework/discussions)

---

**Previous:** [← Part 8: Observability](mario-pizzeria-08-observability.md) | **Back to:** [Tutorial Index](index.md)
