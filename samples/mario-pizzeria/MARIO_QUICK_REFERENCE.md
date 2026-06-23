# 🍕 Mario's Pizzeria - Quick Reference

This document provides a quick reference for managing Mario's Pizzeria with the complete observability stack.

## 🚀 Getting Started (Clean Commands)

All the scripts have been cleaned up to use the `mario-docker.sh` utility for consistent Docker management:

```bash
# Start the complete stack (Mario's Pizzeria + Observability)
make mario-start

# Check status of all services
make mario-status

# Generate test data for dashboards
make mario-test-data

# Open key services in browser (Pizzeria UI + Grafana)
make mario-open

# View logs from all services
make mario-logs

# Stop the stack
make mario-stop
```

## 🛠️ Available Make Commands

| Command                        | Description                                                      |
| ------------------------------ | ---------------------------------------------------------------- |
| `make mario-start`             | Start Mario's Pizzeria with full observability stack             |
| `make mario-stop`              | Stop Mario's Pizzeria and observability stack                    |
| `make mario-restart`           | Restart Mario's Pizzeria and observability stack                 |
| `make mario-status`            | Check Mario's Pizzeria and observability stack status            |
| `make mario-logs`              | View logs for Mario's Pizzeria and observability stack           |
| `make mario-clean`             | Stop and clean Mario's Pizzeria environment (destructive)        |
| `make mario-reset`             | Complete reset of Mario's Pizzeria environment (destructive)     |
| `make mario-open`              | Open key Mario's Pizzeria services in browser                    |
| `make mario-test-data`         | Generate test data for Mario's Pizzeria observability dashboards |
| `make mario-clean-orders`      | Remove all order data from Mario's Pizzeria MongoDB              |
| `make mario-create-menu`       | Create default pizza menu in Mario's Pizzeria                    |
| `make mario-remove-validation` | Remove MongoDB validation schemas (use app validation only)      |

## 🌐 Service URLs

Once started, access your services at:

### Core Application

- 🍕 **Mario's Pizzeria UI**: http://localhost:8080/ui
- 🍕 **Mario's Pizzeria API**: http://localhost:8080/api/docs

### Observability Stack

- 📊 **Grafana Dashboards**: http://localhost:3001 (admin/admin)
- 📈 **Prometheus Metrics**: http://localhost:9090
- 🔍 **Tempo Traces**: http://localhost:3200
- 📝 **Loki Logs**: http://localhost:3100
- 📡 **OTEL Collector**: http://localhost:8888

### Supporting Services

- 🗄️ **MongoDB Express**: http://localhost:8081 (admin/admin123)
- 🎬 **Event Player**: http://localhost:8085
- 🔐 **Keycloak Admin**: http://localhost:8090/admin (admin/admin)

## 🎯 Quick Workflow

1. **Start Everything**: `make mario-start`
2. **Generate Data**: `make mario-test-data`
3. **Open Dashboards**: `make mario-open`
4. **Monitor Logs**: `make mario-logs` (Ctrl+C to exit)
5. **Stop When Done**: `make mario-stop`

## 🔧 Direct Docker Commands

If you prefer using the mario-docker.sh script directly:

```bash
# All the same functionality available directly
./mario-docker.sh start
./mario-docker.sh status
./mario-docker.sh logs
./mario-docker.sh clean-orders      # Remove only order data from MongoDB
./mario-docker.sh create-menu       # Initialize default pizza menu
./mario-docker.sh remove-validation # Remove MongoDB validation schemas
./mario-docker.sh stop
./mario-docker.sh clean         # Destructive - removes all data
./mario-docker.sh reset         # Destructive - complete rebuild
./mario-docker.sh help          # Show all options
```

## 📊 Pre-configured Dashboards

The stack includes two pre-configured Grafana dashboards:

1. **Mario's Pizzeria - Overview**

   - Business metrics (orders, revenue, customer stats)
   - Order workflow traces
   - Application logs with trace correlation

2. **Neuroglia Framework - CQRS & Tracing**
   - Command traces (PlaceOrder, StartCooking, CompleteOrder)
   - Query traces (GetOrder, GetCustomer, etc.)
   - Repository operation traces

## 🐛 Troubleshooting

- **Services not starting**: Check `make mario-status` for health checks
- **No data in dashboards**: Run `make mario-test-data` to generate test orders
- **Too much test data**: Use `make mario-clean-orders` to clear only order data
- **Port conflicts**: Make sure ports 8080, 3001, 9090, etc. are available
- **Clean restart**: Use `make mario-clean` followed by `make mario-start`
- **Keycloak issues**: Use `make keycloak-reset` to reset Keycloak volume and configuration

## 🧹 What Changed

The previous mario commands in the Makefile used the CLI (`pyneuroctl.py`) which only managed the application without the observability stack. The new commands use `mario-docker.sh` which manages the complete Docker Compose environment including:

- Mario's Pizzeria application
- Grafana + dashboards
- Tempo distributed tracing
- Prometheus metrics
- Loki log aggregation
- OpenTelemetry Collector
- MongoDB + Mongo Express
- Keycloak authentication
- Event Player

This provides a complete, production-like observability environment for testing and development.
