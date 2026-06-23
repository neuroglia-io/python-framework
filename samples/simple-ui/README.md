# Simple UI Sample Application

A clean architecture FastAPI application demonstrating role-based access control (RBAC), JWT authentication, and a modern single-page application (SPA) interface.

## 🎯 Overview

This sample showcases:

- **Clean Architecture**: Domain, Application, Infrastructure, API, and UI layers
- **CQRS Pattern**: Separate commands (write) and queries (read) with Mediator
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Tasks filtered by user role (Admin, Manager, User)
- **Modern Frontend**: Bootstrap 5 SPA with modals and SASS styling
- **Neuroglia Framework**: Dependency injection, MVC controllers, and CQRS mediation

## 🏗️ Architecture

```
simple-ui/
├── domain/              # Business entities and repository contracts
│   ├── entities/        # Task entity
│   └── repositories/    # Abstract TaskRepository
├── integration/         # Infrastructure implementations
│   └── repositories/    # InMemoryTaskRepository with sample data
├── application/         # CQRS command and query handlers
│   ├── commands/        # CreateTaskCommand + Handler
│   └── queries/         # GetTasksQuery + Handler (RBAC logic)
├── api/                 # REST API controllers
│   └── controllers/     # AuthController, TasksController
├── ui/                  # Frontend interface
│   ├── controllers/     # UIController (serves HTML)
│   ├── templates/       # Jinja2 HTML templates
│   ├── src/
│   │   ├── scripts/     # JavaScript SPA logic
│   │   └── styles/      # SASS stylesheets
│   └── package.json     # Node.js dependencies
└── main.py              # Application entry point
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended for Full Stack)

```bash
# Start shared infrastructure and Simple UI
make simple-ui-start

# Or manually:
docker-compose -f ../../docker-compose.shared.yml -f ../../docker-compose.simple-ui.yml up -d
```

The application will be available at: **http://localhost:8082**

Includes:

- MongoDB database
- OpenTelemetry observability stack
- Grafana dashboards (http://localhost:3001)

### Option 2: Standalone (No Docker)

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Poetry (Python dependency management)

### 1. Install Backend Dependencies

```bash
cd samples/simple-ui
poetry install
```

**Note**: If you encounter issues with `python-jose`, install it separately:

```bash
poetry add python-jose[cryptography]
```

### 2. Install Frontend Dependencies

```bash
cd ui
npm install
```

### 3. Build Frontend Assets

```bash
npm run build
```

This compiles SASS and bundles JavaScript using Parcel, outputting to `static/dist/`.

### 4. Run the Application

```bash
cd ..  # Back to samples/simple-ui
poetry run python main.py
```

The application will start at: **http://localhost:8000**

## 👥 Demo User Accounts

| Username     | Password     | Role    | Access Level                              |
| ------------ | ------------ | ------- | ----------------------------------------- |
| `admin`      | `admin123`   | Admin   | See all 6 tasks, can create new tasks     |
| `manager`    | `manager123` | Manager | See 3 tasks (excludes admin-created)      |
| `john.doe`   | `user123`    | User    | See 3 tasks (only assigned to john.doe)   |
| `jane.smith` | `user123`    | User    | See 2 tasks (only assigned to jane.smith) |

## 📋 Sample Tasks

The application comes pre-loaded with 6 tasks:

1. **Review code PR #123** (High) - Assigned: john.doe, Created by: admin
2. **Update documentation** (Medium) - Assigned: jane.smith, Created by: admin
3. **Deploy to staging** (High) - Assigned: admin, Created by: admin
4. **Client meeting prep** (Medium) - Assigned: jane.smith, Created by: manager
5. **Database optimization** (Medium) - Assigned: john.doe, Created by: manager
6. **Bug fix: Login timeout** (High) - Assigned: john.doe, Created by: john.doe

## 🎨 Features

### Authentication

- JWT token-based authentication with 30-minute expiry
- HTTPBearer security scheme
- Automatic token refresh on page load
- Logout with local storage cleanup

### Role-Based Task Filtering

- **Admin**: Views all tasks
- **Manager**: Views all tasks except those created by admin
- **User**: Views only tasks assigned to them

### Task Management

- View task list with priority indicators (High 🔴, Medium 🟡, Low 🟢)
- View detailed task information in modal
- Create new tasks (admin only)
- Real-time status updates

### Modern UI

- Bootstrap 5 responsive design
- Priority-colored task cards with hover effects
- Modal dialogs for task details and creation
- Empty state messages
- Loading indicators

## 🧪 Testing

### Manual Testing Flow

1. **Login as Admin** (`admin` / `admin123`)

   - Verify you see all 6 tasks
   - Click "Create Task" and add a new task
   - Verify the new task appears in the list
   - Click a task card to view details

2. **Login as Manager** (`manager` / `manager123`)

   - Verify you see 3 tasks (excludes admin-created)
   - Verify "Create Task" button is hidden
   - Try to view task details

3. **Login as User** (`john.doe` / `user123`)

   - Verify you see 3 tasks assigned to john.doe
   - Verify "Create Task" button is hidden

4. **Test Logout**
   - Click logout button
   - Verify redirect to login page
   - Verify localStorage is cleared

### API Endpoints

- **POST** `/api/auth/login` - Authenticate and receive JWT token
- **GET** `/api/tasks/` - Get tasks (filtered by role)
- **POST** `/api/tasks/` - Create task (admin only)
- **GET** `/` - Serve UI template

## 🔧 Development

### Frontend Development

Run Parcel in watch mode for automatic rebuilds:

```bash
cd ui
npm run dev
```

### Backend Development

The application uses uvicorn with hot reload enabled by default.

### Project Structure Best Practices

- **Domain Layer**: Pure business logic, no external dependencies
- **Application Layer**: CQRS handlers orchestrate use cases
- **Infrastructure Layer**: Concrete implementations (repositories, external services)
- **API Layer**: Thin controllers that delegate to Mediator
- **UI Layer**: Templates and static assets

## 📦 Dependencies

### Backend

- `fastapi` - Web framework
- `neuroglia` - CQRS, DI, MVC patterns
- `python-jose[cryptography]` - JWT handling
- `uvicorn` - ASGI server
- `jinja2` - Template engine

### Frontend

- `bootstrap@5.3.2` - UI framework
- `bootstrap-icons@1.11.1` - Icon library
- `chart.js@4.4.0` - Charting (for future enhancements)
- `parcel@2.10.3` - Build tool
- `sass@1.69.5` - CSS preprocessor

## 🔐 Security Notes

**⚠️ This is a sample application for demonstration purposes.**

For production use:

1. Change the JWT secret key in `api/controllers/auth_controller.py`
2. Use environment variables for configuration
3. Implement password hashing (bcrypt, argon2)
4. Add HTTPS/TLS
5. Implement rate limiting
6. Add CSRF protection
7. Use a real database instead of in-memory storage
8. Add comprehensive input validation
9. Implement proper error handling and logging
10. Add security headers

## 📚 Related Documentation

- [Simple UI App Guide](../../docs/guides/simple-ui-app.md) - Detailed tutorial
- [Mario's Pizzeria Sample](../mario-pizzeria/README.md) - Advanced example
- [Neuroglia Framework Docs](../../docs/index.md) - Framework documentation

## 🤝 Contributing

This sample follows the Neuroglia framework conventions. When making changes:

1. Maintain clean architecture boundaries
2. Use CQRS for all business operations
3. Keep controllers thin (delegate to Mediator)
4. Follow existing naming conventions
5. Update tests when modifying code
6. Keep documentation in sync

## 📝 License

See the main project LICENSE file.

---

**Built with ❤️ using the Neuroglia Python Framework**
