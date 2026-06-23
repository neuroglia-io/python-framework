# 🍕 Mario's Pizzeria Docker Environment - Setup Summary

## 📁 Files Created

This Docker setup includes the following new files for Mario's Pizzeria:

### Core Docker Configuration

- **`docker-compose.mario.yml`** - Complete multi-service Docker Compose configuration
- **`mario-docker.sh`** - Convenient management script for the Docker environment

### Database Setup

- **`deployment/mongo/init-mario-db.js`** - MongoDB initialization with schema, indexes, and sample data
- **`deployment/keycloak/realm-export.json`** - Keycloak realm configuration with users and roles

### Documentation

- **`deployment/README-mario-docker.md`** - Comprehensive Docker setup documentation

## 🏗️ Services Architecture

The Docker environment provides a complete microservices setup:

```
┌─────────────────────────────────────────────────────────────┐
│                    Mario's Pizzeria Stack                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🍕 Mario App          🎬 Event Player     🔐 Keycloak       │
│  (FastAPI+Neuroglia)   (Event Viz)        (Auth)            │
│  Port: 8080           Port: 8085          Port: 8090        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🗄️ MongoDB            🎪 EventStoreDB     🐘 PostgreSQL     │
│  (App Data)           (Events)            (Keycloak DB)     │
│  Port: 27017          Port: 2113          Internal          │
│                                                             │
│  📊 Mongo Express                                           │
│  (DB Admin UI)                                              │
│  Port: 8081                                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Key Features

### Application Services

- **Mario's Pizzeria API**: Full FastAPI application with Neuroglia framework
- **Remote Debugging**: VS Code compatible debugging on port 5678
- **Hot Reload**: Automatic code reloading during development
- **CORS Enabled**: Ready for frontend development

### Data Persistence

- **MongoDB**: Primary application database with optimized schema
- **EventStoreDB**: Event sourcing and domain events
- **Automatic Initialization**: Database setup with sample data
- **Admin Interface**: MongoDB Express for database management

### Authentication & Authorization

- **Keycloak**: Complete OAuth2/OpenID Connect provider
- **Pre-configured Realm**: Mario Pizzeria realm with roles
- **Sample Users**: Ready-to-use test accounts (customers, staff, managers)
- **Role-based Access**: Customer, Chef, Manager, Admin roles

### Event Streaming

- **Event Player**: Visualization and replay of CloudEvents
- **Event Publishing**: Integrated with Mario's Pizzeria events
- **Real-time Monitoring**: Live event stream visualization

### Development Tools

- **Health Checks**: Built-in service health monitoring
- **Logging**: Centralized log management
- **Management Script**: Easy service control with `mario-docker.sh`
- **Network Isolation**: Dedicated Docker network for security

## 🚀 Quick Usage

### Start Everything

```bash
./mario-docker.sh start
```

### Access Services

- **🍕 API Documentation**: http://localhost:8080/api/docs
- **🗄️ Database Admin**: http://localhost:8081 (admin/admin123)
- **🎪 EventStore**: http://localhost:2113
- **🎬 Event Player**: http://localhost:8085
- **🔐 Keycloak Admin**: http://localhost:8090/admin (admin/admin)

### Test Authentication

Use these pre-configured accounts:

- **Customer**: `mario.rossi` / `pizza123`
- **Chef**: `giuseppe.chef` / `chef123`
- **Manager**: `antonio.manager` / `manager123`

### Sample Data

The environment comes with:

- **5 Pizza varieties** (Margherita, Pepperoni, Quattro Stagioni, etc.)
- **2 Sample customers** with addresses and loyalty points
- **Optimized database indexes** for performance
- **Validation schemas** for data integrity

## 🔧 Management Commands

```bash
# Service lifecycle
./mario-docker.sh start     # Start all services
./mario-docker.sh stop      # Stop all services
./mario-docker.sh restart   # Restart services

# Monitoring
./mario-docker.sh status    # Check service health
./mario-docker.sh logs      # Follow logs

# Maintenance
./mario-docker.sh clean     # Remove all data (destructive!)
./mario-docker.sh reset     # Complete rebuild (destructive!)
```

## 🧪 Development Workflow

1. **Start Environment**: `./mario-docker.sh start`
2. **Develop**: Edit code in `samples/mario-pizzeria/`
3. **Debug**: Attach VS Code debugger to port 5678
4. **Test APIs**: Use Swagger UI at http://localhost:8080/api/docs
5. **Monitor Events**: Watch events in Event Player
6. **Manage Data**: Use MongoDB Express for data inspection
7. **Test Auth**: Log in with sample users in Keycloak

## 📊 Resource Usage

Typical resource consumption:

- **CPU**: 2-4 cores (during startup and active development)
- **Memory**: ~4GB RAM total across all services
- **Disk**: ~2GB for images + data volumes
- **Network**: Isolated Docker bridge network (172.20.0.0/16)

## 🔒 Security Features

- **Development Mode**: All services configured for local development
- **Network Isolation**: Services communicate via internal Docker network
- **Authentication Ready**: Keycloak provides enterprise-grade auth
- **Role-based Access**: Proper RBAC with realistic roles
- **Secure Defaults**: Following security best practices for containers

## 🎓 Learning Outcomes

This environment teaches:

- **Microservices Architecture**: Multiple interconnected services
- **Event-Driven Design**: CloudEvents and event sourcing patterns
- **Authentication Integration**: OAuth2/OIDC with Keycloak
- **Database Design**: MongoDB schema design and optimization
- **Container Orchestration**: Docker Compose service management
- **Development Tooling**: Complete DevX with debugging and monitoring

## 🔗 Integration Points

The setup integrates with:

- **Neuroglia Framework**: Full framework feature showcase
- **VS Code**: Debug configuration and tasks
- **FastAPI**: Modern Python web framework
- **CloudEvents**: Standardized event format
- **MongoDB**: Document database patterns
- **Keycloak**: Enterprise authentication

This complete environment provides everything needed to explore, learn, and develop with the Neuroglia framework using Mario's Pizzeria as a comprehensive example.
