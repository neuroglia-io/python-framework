# Building a Simple UI Application with Neuroglia

## 🎯 Overview

This guide walks you through building a complete single-page application (SPA) with:

- **Backend**: FastAPI with CQRS pattern, stateless JWT authentication, and RBAC
- **Frontend**: Bootstrap 5 UI with modals, compiled with Parcel
- **Architecture**: Clean separation of concerns following Mario's Pizzeria patterns
- **Authentication**: Pure JWT-based (no server-side sessions), stored client-side in localStorage
- **Features**: User authentication, role-based access control, dynamic content

**What You'll Build**: A task management system where users see different tasks based on their role (admin, manager, user).

## 📋 Prerequisites

- Python 3.9+
- Node.js 16+ and npm
- Basic knowledge of FastAPI and JavaScript
- Understanding of CQRS pattern (see [Simple CQRS Guide](simple-cqrs.md))

## 🏗️ Project Structure

```
samples/simple-ui/
├── main.py                      # Application entry point
├── static/                      # Static assets (generated)
│   └── dist/                    # Parcel build output
├── ui/                          # Frontend source
│   ├── package.json             # Node.js dependencies
│   ├── src/
│   │   ├── scripts/
│   │   │   └── main.js          # JavaScript logic
│   │   └── styles/
│   │       └── main.scss        # SASS styles
│   ├── templates/
│   │   └── index.html           # Jinja2 template
│   └── controllers/
│       └── ui_controller.py     # UI routes
├── api/                         # Backend API
│   └── controllers/
│       ├── auth_controller.py   # Authentication
│       └── tasks_controller.py  # Task management
├── application/                 # CQRS layer
│   ├── commands/
│   │   └── create_task_command.py
│   └── queries/
│       └── get_tasks_query.py
├── domain/                      # Domain models
│   ├── entities/
│   │   └── task.py
│   └── repositories/
│       └── task_repository.py
└── integration/                 # Infrastructure
    └── repositories/
        └── in_memory_task_repository.py
```

## 🚀 Step 1: Set Up the Project

### 1.1 Create Directory Structure

```bash
cd samples
mkdir -p simple-ui/{api/controllers,application/{commands,queries},domain/{entities,repositories},integration/repositories,ui/{src/{scripts,styles},templates,controllers},static}
cd simple-ui
```

### 1.2 Initialize Frontend

```bash
cd ui
npm init -y
npm install bootstrap@^5.3.2 chart.js@^4.4.0
npm install --save-dev parcel@^2.10.3 @parcel/transformer-sass@^2.10.3 sass@^1.69.5
```

Update `ui/package.json`:

```json
{
  "name": "simple-ui-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "parcel watch 'src/scripts/*.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist",
    "build": "parcel build 'src/scripts/*.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist --no-source-maps",
    "clean": "rm -rf ../static/dist .parcel-cache node_modules/.cache"
  },
  "dependencies": {
    "bootstrap": "^5.3.2",
    "chart.js": "^4.4.0"
  },
  "devDependencies": {
    "@parcel/transformer-sass": "^2.10.3",
    "parcel": "^2.10.3",
    "sass": "^1.69.5"
  }
}
```

## 📝 Step 2: Domain Layer - Define Your Business Models

### 2.1 Create Task Entity (`domain/entities/task.py`)

```python
"""Task domain entity."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from neuroglia.data.abstractions import Entity


@dataclass
class Task(Entity):
    """Represents a task in the system."""

    title: str
    description: str
    assigned_to: str
    priority: str  # low, medium, high
    status: str  # pending, in_progress, completed
    created_at: datetime
    created_by: str

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        assigned_to: str,
        priority: str = "medium",
        status: str = "pending",
        created_by: str = "system"
    ):
        super().__init__()
        self.id = id
        self.title = title
        self.description = description
        self.assigned_to = assigned_to
        self.priority = priority
        self.status = status
        self.created_at = datetime.now()
        self.created_by = created_by

    def complete(self):
        """Mark task as completed."""
        self.status = "completed"

    def assign_to(self, user: str):
        """Assign task to a user."""
        self.assigned_to = user
```

### 2.2 Create Task Repository Interface (`domain/repositories/task_repository.py`)

```python
"""Task repository interface."""
from abc import ABC, abstractmethod
from typing import List, Optional

from domain.entities.task import Task


class TaskRepository(ABC):
    """Abstract repository for task persistence."""

    @abstractmethod
    async def get_all_async(self) -> List[Task]:
        """Get all tasks."""
        pass

    @abstractmethod
    async def get_by_id_async(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        pass

    @abstractmethod
    async def get_by_user_async(self, username: str) -> List[Task]:
        """Get tasks assigned to a specific user."""
        pass

    @abstractmethod
    async def save_async(self, task: Task) -> None:
        """Save a task."""
        pass

    @abstractmethod
    async def delete_async(self, task_id: str) -> None:
        """Delete a task."""
        pass
```

## 🔧 Step 3: Infrastructure Layer - Implement Repository

### 3.1 In-Memory Task Repository (`integration/repositories/in_memory_task_repository.py`)

```python
"""In-memory implementation of task repository."""
from typing import Dict, List, Optional

from domain.entities.task import Task
from domain.repositories.task_repository import TaskRepository


class InMemoryTaskRepository(TaskRepository):
    """In-memory task repository for demo purposes."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._initialize_sample_data()

    def _initialize_sample_data(self):
        """Initialize with sample tasks."""
        sample_tasks = [
            Task("1", "Review code PR #123", "Critical bug fix needed", "john.doe", "high", "in_progress", "admin"),
            Task("2", "Update documentation", "Add API docs for new endpoints", "jane.smith", "medium", "pending", "admin"),
            Task("3", "Deploy to staging", "Deploy v2.1.0 to staging environment", "admin", "high", "pending", "admin"),
            Task("4", "Client meeting prep", "Prepare slides for Q4 review", "jane.smith", "medium", "in_progress", "manager"),
            Task("5", "Database optimization", "Optimize slow queries in reports", "john.doe", "medium", "pending", "manager"),
            Task("6", "Bug fix: Login timeout", "Users reporting session timeouts", "john.doe", "high", "pending", "user"),
        ]

        for task in sample_tasks:
            self._tasks[task.id] = task

    async def get_all_async(self) -> List[Task]:
        """Get all tasks."""
        return list(self._tasks.values())

    async def get_by_id_async(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def get_by_user_async(self, username: str) -> List[Task]:
        """Get tasks assigned to a specific user."""
        return [task for task in self._tasks.values() if task.assigned_to == username]

    async def save_async(self, task: Task) -> None:
        """Save a task."""
        self._tasks[task.id] = task

    async def delete_async(self, task_id: str) -> None:
        """Delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
```

## 💼 Step 4: Application Layer - CQRS Commands and Queries

### 4.1 Create Task Command (`application/commands/create_task_command.py`)

```python
"""Command for creating a new task."""
from dataclasses import dataclass

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler

from domain.entities.task import Task
from domain.repositories.task_repository import TaskRepository


@dataclass
class CreateTaskCommand(Command[OperationResult['TaskDto']]):
    """Command to create a new task."""
    title: str
    description: str
    assigned_to: str
    priority: str
    created_by: str


@dataclass
class TaskDto:
    """Data transfer object for tasks."""
    id: str
    title: str
    description: str
    assigned_to: str
    priority: str
    status: str
    created_by: str


class CreateTaskHandler(CommandHandler[CreateTaskCommand, OperationResult[TaskDto]]):
    """Handler for creating tasks."""

    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, command: CreateTaskCommand) -> OperationResult[TaskDto]:
        """Handle task creation."""
        # Validation
        if not command.title or not command.title.strip():
            return self.bad_request("Task title is required")

        if not command.assigned_to or not command.assigned_to.strip():
            return self.bad_request("Task must be assigned to a user")

        # Generate ID (in production, use proper ID generation)
        import uuid
        task_id = str(uuid.uuid4())[:8]

        # Create task entity
        task = Task(
            id=task_id,
            title=command.title,
            description=command.description,
            assigned_to=command.assigned_to,
            priority=command.priority,
            created_by=command.created_by
        )

        # Save to repository
        await self.task_repository.save_async(task)

        # Return DTO
        dto = TaskDto(
            id=task.id,
            title=task.title,
            description=task.description,
            assigned_to=task.assigned_to,
            priority=task.priority,
            status=task.status,
            created_by=task.created_by
        )

        return self.created(dto)
```

### 4.2 Get Tasks Query (`application/queries/get_tasks_query.py`)

```python
"""Query for retrieving tasks."""
from dataclasses import dataclass
from typing import List, Optional

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from application.commands.create_task_command import TaskDto
from domain.repositories.task_repository import TaskRepository


@dataclass
class GetTasksQuery(Query[OperationResult[List[TaskDto]]]):
    """Query to get tasks, optionally filtered by user."""
    username: Optional[str] = None
    role: Optional[str] = None


class GetTasksHandler(QueryHandler[GetTasksQuery, OperationResult[List[TaskDto]]]):
    """Handler for retrieving tasks."""

    def __init__(self, task_repository: TaskRepository):
        super().__init__()
        self.task_repository = task_repository

    async def handle_async(self, query: GetTasksQuery) -> OperationResult[List[TaskDto]]:
        """Handle task retrieval with role-based filtering."""

        # Get tasks based on role
        if query.role == "admin":
            # Admins see all tasks
            tasks = await self.task_repository.get_all_async()
        elif query.role == "manager":
            # Managers see all tasks except admin-created ones
            all_tasks = await self.task_repository.get_all_async()
            tasks = [t for t in all_tasks if t.created_by != "admin"]
        else:
            # Regular users see only their assigned tasks
            if not query.username:
                return self.bad_request("Username required for user role")
            tasks = await self.task_repository.get_by_user_async(query.username)

        # Convert to DTOs
        dtos = [
            TaskDto(
                id=task.id,
                title=task.title,
                description=task.description,
                assigned_to=task.assigned_to,
                priority=task.priority,
                status=task.status,
                created_by=task.created_by
            )
            for task in tasks
        ]

        return self.ok(dtos)
```

## ⚙️ Step 5: Application Settings

Before implementing authentication, create a settings file for configuration.

### 5.1 Create Settings File (`application/settings.py`)

```python
"""Application settings and configuration."""
import logging
import os
import sys
from dataclasses import dataclass


@dataclass
class AppSettings:
    """Application settings for JWT authentication."""

    # Application
    app_name: str = "Simple UI"
    app_version: str = "1.0.0"
    debug: bool = True

    # JWT Settings
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60


# Global settings instance
app_settings = AppSettings()


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
```

**Key Points**:

- ✅ **JWT Configuration**: Centralized JWT settings for consistency
- ✅ **Environment Variables**: Use `JWT_SECRET_KEY` env var in production
- ✅ **No Session Settings**: Removed session_secret_key (not needed for JWT-only auth)
- ✅ **Logging Setup**: Standardized logging configuration

## 🔐 Step 6: Authentication and Authorization

### 6.1 JWT-Only Authentication Architecture

This application uses **stateless JWT-only authentication**:

- ✅ **JWT Token**: Created on login, stored in localStorage (client-side)
- ✅ **Authorization Header**: Token sent with every API request as `Bearer <token>`
- ✅ **No Server Sessions**: Completely stateless - no session cookies or server-side state
- ✅ **Token Payload**: Contains user identity, roles, and metadata
- ✅ **Validation**: API endpoints validate JWT signature and expiration

**Why JWT-Only?**

- Stateless and scalable (no session storage needed)
- Works seamlessly with microservices and distributed systems
- Frontend can decode JWT for user info display
- Standard modern SPA authentication pattern

### 6.2 Create Auth Controller (`api/controllers/auth_controller.py`)

```python
"""Authentication controller - JWT-only, no sessions."""
from datetime import datetime, timedelta
from typing import Optional

from application.settings import app_settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from classy_fastapi import post

# JWT Configuration - use shared settings
SECRET_KEY = app_settings.jwt_secret_key
ALGORITHM = app_settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = app_settings.jwt_expiration_minutes

# Mock user database (in production, use real database)
USERS_DB = {
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
    "manager": {"username": "manager", "password": "manager123", "role": "manager"},
    "john.doe": {"username": "john.doe", "password": "user123", "role": "user"},
    "jane.smith": {"username": "jane.smith", "password": "user123", "role": "user"},
}


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    username: str
    role: str


class UserInfo(BaseModel):
    """User information."""
    username: str
    role: str


security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Use 'username' field from token, not 'sub' (which contains user ID)
        username: str = payload.get("username")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return UserInfo(username=username, role=role)
    except JWTError:
        raise credentials_exception


class AuthController(ControllerBase):
    """Authentication controller."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @post("/login", response_model=TokenResponse)
    async def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate user and return JWT token."""
        # Validate credentials
        user = USERS_DB.get(request.username)
        if not user or user["password"] != request.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=access_token_expires
        )

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            username=user["username"],
            role=user["role"]
        )
```

### 6.3 Create Tasks API Controller (`api/controllers/tasks_controller.py`)

```python
"""Tasks API controller."""
from typing import List

from fastapi import Depends

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from classy_fastapi import get, post

from api.controllers.auth_controller import get_current_user, UserInfo
from application.commands.create_task_command import CreateTaskCommand, TaskDto
from application.queries.get_tasks_query import GetTasksQuery


class TasksController(ControllerBase):
    """Tasks management controller."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_model=List[TaskDto])
    async def get_tasks(self, current_user: UserInfo = Depends(get_current_user)) -> List[TaskDto]:
        """Get tasks based on user role."""
        query = GetTasksQuery(username=current_user.username, role=current_user.role)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/", response_model=TaskDto, status_code=201)
    async def create_task(
        self,
        command: CreateTaskCommand,
        current_user: UserInfo = Depends(get_current_user)
    ) -> TaskDto:
        """Create a new task (admin only)."""
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can create tasks")

        command.created_by = current_user.username
        result = await self.mediator.execute_async(command)
        return self.process(result)
```

## 🎨 Step 7: Frontend - UI Controller and Templates

### 7.1 Create UI Controller (`ui/controllers/ui_controller.py`)

```python
"""UI controller for serving HTML pages."""
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from classy_fastapi import get


templates = Jinja2Templates(directory="ui/templates")


class UIController(ControllerBase):
    """Controller for UI pages."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_class=HTMLResponse)
    async def index(self, request: Request):
        """Render main application page."""
        return templates.TemplateResponse("index.html", {"request": request})
```

### 7.2 Create HTML Template (`ui/templates/index.html`)

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Simple Task Manager</title>
    <link rel="stylesheet" href="{{ url_for('static', path='dist/main.css') }}" />
  </head>
  <body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container-fluid">
        <a class="navbar-brand" href="#"> <i class="bi bi-check2-square"></i> Task Manager </a>
        <div class="navbar-nav ms-auto">
          <span class="navbar-text me-3" id="userInfo">
            <i class="bi bi-person-circle"></i> <span id="username"></span> (<span id="userRole"></span>)
          </span>
          <button class="btn btn-outline-light btn-sm" onclick="logout()">
            <i class="bi bi-box-arrow-right"></i> Logout
          </button>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <div class="container mt-4">
      <!-- Login Form (hidden after login) -->
      <div id="loginSection" class="row justify-content-center">
        <div class="col-md-6">
          <div class="card shadow">
            <div class="card-body">
              <h2 class="card-title text-center mb-4"><i class="bi bi-box-arrow-in-right"></i> Login</h2>
              <form id="loginForm">
                <div class="mb-3">
                  <label for="loginUsername" class="form-label">Username</label>
                  <input type="text" class="form-control" id="loginUsername" required />
                  <small class="form-text text-muted"> Try: admin, manager, john.doe, or jane.smith </small>
                </div>
                <div class="mb-3">
                  <label for="loginPassword" class="form-label">Password</label>
                  <input type="password" class="form-control" id="loginPassword" required />
                  <small class="form-text text-muted"> Password: admin123, manager123, or user123 </small>
                </div>
                <div id="loginError" class="alert alert-danger d-none"></div>
                <button type="submit" class="btn btn-primary w-100">
                  <i class="bi bi-box-arrow-in-right"></i> Login
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>

      <!-- Tasks Section (shown after login) -->
      <div id="tasksSection" class="d-none">
        <div class="row mb-3">
          <div class="col">
            <h2><i class="bi bi-list-task"></i> My Tasks</h2>
            <p class="text-muted" id="taskDescription"></p>
          </div>
          <div class="col-auto" id="createTaskBtn" style="display: none;">
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createTaskModal">
              <i class="bi bi-plus-circle"></i> Create Task
            </button>
          </div>
        </div>

        <!-- Tasks Grid -->
        <div id="tasksGrid" class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
          <!-- Tasks will be loaded here -->
        </div>
      </div>
    </div>

    <!-- Create Task Modal -->
    <div class="modal fade" id="createTaskModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"><i class="bi bi-plus-circle"></i> Create New Task</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <form id="createTaskForm">
              <div class="mb-3">
                <label for="taskTitle" class="form-label">Title</label>
                <input type="text" class="form-control" id="taskTitle" required />
              </div>
              <div class="mb-3">
                <label for="taskDescription" class="form-label">Description</label>
                <textarea class="form-control" id="taskDescription" rows="3" required></textarea>
              </div>
              <div class="mb-3">
                <label for="taskAssignedTo" class="form-label">Assign To</label>
                <select class="form-select" id="taskAssignedTo" required>
                  <option value="john.doe">John Doe</option>
                  <option value="jane.smith">Jane Smith</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div class="mb-3">
                <label for="taskPriority" class="form-label">Priority</label>
                <select class="form-select" id="taskPriority" required>
                  <option value="low">Low</option>
                  <option value="medium" selected>Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="createTask()">
              <i class="bi bi-check-circle"></i> Create
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Task Details Modal -->
    <div class="modal fade" id="taskDetailsModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="taskDetailsTitle"></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <dl class="row">
              <dt class="col-sm-4">Description:</dt>
              <dd class="col-sm-8" id="taskDetailsDescription"></dd>

              <dt class="col-sm-4">Assigned To:</dt>
              <dd class="col-sm-8" id="taskDetailsAssignedTo"></dd>

              <dt class="col-sm-4">Priority:</dt>
              <dd class="col-sm-8" id="taskDetailsPriority"></dd>

              <dt class="col-sm-4">Status:</dt>
              <dd class="col-sm-8" id="taskDetailsStatus"></dd>

              <dt class="col-sm-4">Created By:</dt>
              <dd class="col-sm-8" id="taskDetailsCreatedBy"></dd>
            </dl>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>

    <script src="{{ url_for('static', path='dist/main.js') }}"></script>
  </body>
</html>
```

### 7.3 Create SASS Styles (`ui/src/styles/main.scss`)

```scss
// Import Bootstrap
@import "~bootstrap/scss/bootstrap";
@import "~bootstrap-icons/font/bootstrap-icons.css";

// Custom variables
$primary-color: #0d6efd;
$success-color: #198754;
$warning-color: #ffc107;
$danger-color: #dc3545;

// Global styles
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f8f9fa;
}

// Navbar customization
.navbar-brand {
  font-weight: 600;
  font-size: 1.25rem;

  i {
    font-size: 1.5rem;
    vertical-align: middle;
  }
}

// Task cards
.task-card {
  transition:
    transform 0.2s,
    box-shadow 0.2s;
  cursor: pointer;
  border-left: 4px solid transparent;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &.priority-high {
    border-left-color: $danger-color;
  }

  &.priority-medium {
    border-left-color: $warning-color;
  }

  &.priority-low {
    border-left-color: $success-color;
  }
}

// Status badges
.badge {
  &.status-pending {
    background-color: #6c757d;
  }

  &.status-in_progress {
    background-color: $primary-color;
  }

  &.status-completed {
    background-color: $success-color;
  }
}

// Priority badges
.badge-priority {
  &.high {
    background-color: $danger-color;
  }

  &.medium {
    background-color: $warning-color;
  }

  &.low {
    background-color: $success-color;
  }
}

// Loading spinner
.spinner-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

// Login form
#loginSection {
  margin-top: 100px;

  .card {
    border: none;
    border-radius: 12px;
  }
}

// Empty state
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;

  i {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  h3 {
    margin-bottom: 0.5rem;
  }
}
```

### 7.4 Create JavaScript Logic (`ui/src/scripts/main.js`)

```javascript
// Import Bootstrap
import "bootstrap/dist/js/bootstrap.bundle";

// API base URL
const API_BASE = "/api";

// State management
let currentUser = null;
let authToken = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  // Check for existing token
  const savedToken = localStorage.getItem("authToken");
  const savedUser = localStorage.getItem("currentUser");

  if (savedToken && savedUser) {
    authToken = savedToken;
    currentUser = JSON.parse(savedUser);
    showTasksSection();
    loadTasks();
  }

  // Setup login form
  document.getElementById("loginForm").addEventListener("submit", handleLogin);
});

// Handle login
async function handleLogin(e) {
  e.preventDefault();

  const username = document.getElementById("loginUsername").value;
  const password = document.getElementById("loginPassword").value;
  const errorDiv = document.getElementById("loginError");

  errorDiv.classList.add("d-none");

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Login failed");
    }

    const data = await response.json();
    authToken = data.access_token;
    currentUser = {
      username: data.username,
      role: data.role,
    };

    // Save to localStorage
    localStorage.setItem("authToken", authToken);
    localStorage.setItem("currentUser", JSON.stringify(currentUser));

    // Show tasks section
    showTasksSection();
    loadTasks();
  } catch (error) {
    errorDiv.textContent = error.message;
    errorDiv.classList.remove("d-none");
  }
}

// Logout
function logout() {
  localStorage.removeItem("authToken");
  localStorage.removeItem("currentUser");
  authToken = null;
  currentUser = null;

  document.getElementById("loginSection").classList.remove("d-none");
  document.getElementById("tasksSection").classList.add("d-none");
  document.getElementById("loginForm").reset();
}

// Show tasks section after login
function showTasksSection() {
  document.getElementById("loginSection").classList.add("d-none");
  document.getElementById("tasksSection").classList.remove("d-none");

  // Update user info
  document.getElementById("username").textContent = currentUser.username;
  document.getElementById("userRole").textContent = currentUser.role;

  // Update task description based on role
  const descriptions = {
    admin: "You can see all tasks in the system.",
    manager: "You can see all tasks except admin-created ones.",
    user: "You can see tasks assigned to you.",
  };
  document.getElementById("taskDescription").textContent = descriptions[currentUser.role];

  // Show create button for admins
  if (currentUser.role === "admin") {
    document.getElementById("createTaskBtn").style.display = "block";
  }
}

// Load tasks
async function loadTasks() {
  const grid = document.getElementById("tasksGrid");
  grid.innerHTML =
    '<div class="col-12"><div class="spinner-container"><div class="spinner-border text-primary"></div></div></div>';

  try {
    const response = await fetch(`${API_BASE}/tasks/`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        logout();
        return;
      }
      throw new Error("Failed to load tasks");
    }

    const tasks = await response.json();
    displayTasks(tasks);
  } catch (error) {
    grid.innerHTML = `
      <div class="col-12">
        <div class="alert alert-danger">
          <i class="bi bi-exclamation-triangle"></i> ${error.message}
        </div>
      </div>
    `;
  }
}

// Display tasks
function displayTasks(tasks) {
  const grid = document.getElementById("tasksGrid");

  if (tasks.length === 0) {
    grid.innerHTML = `
      <div class="col-12">
        <div class="empty-state">
          <i class="bi bi-inbox"></i>
          <h3>No Tasks Found</h3>
          <p>There are no tasks to display.</p>
        </div>
      </div>
    `;
    return;
  }

  grid.innerHTML = tasks
    .map(
      task => `
    <div class="col">
      <div class="card task-card priority-${task.priority}" onclick='showTaskDetails(${JSON.stringify(task)})'>
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="card-title mb-0">${escapeHtml(task.title)}</h5>
            <span class="badge badge-priority ${task.priority}">${task.priority}</span>
          </div>
          <p class="card-text text-muted small">${escapeHtml(task.description)}</p>
          <div class="d-flex justify-content-between align-items-center mt-3">
            <small class="text-muted">
              <i class="bi bi-person"></i> ${escapeHtml(task.assigned_to)}
            </small>
            <span class="badge status-${task.status}">${task.status.replace("_", " ")}</span>
          </div>
        </div>
      </div>
    </div>
  `
    )
    .join("");
}

// Show task details in modal
function showTaskDetails(task) {
  document.getElementById("taskDetailsTitle").innerHTML = `<i class="bi bi-card-checklist"></i> ${escapeHtml(
    task.title
  )}`;
  document.getElementById("taskDetailsDescription").textContent = task.description;
  document.getElementById("taskDetailsAssignedTo").textContent = task.assigned_to;
  document.getElementById(
    "taskDetailsPriority"
  ).innerHTML = `<span class="badge badge-priority ${task.priority}">${task.priority}</span>`;
  document.getElementById("taskDetailsStatus").innerHTML = `<span class="badge status-${
    task.status
  }">${task.status.replace("_", " ")}</span>`;
  document.getElementById("taskDetailsCreatedBy").textContent = task.created_by;

  const modal = new bootstrap.Modal(document.getElementById("taskDetailsModal"));
  modal.show();
}

// Create task
async function createTask() {
  const title = document.getElementById("taskTitle").value;
  const description = document.getElementById("taskDescription").value;
  const assignedTo = document.getElementById("taskAssignedTo").value;
  const priority = document.getElementById("taskPriority").value;

  try {
    const response = await fetch(`${API_BASE}/tasks/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title,
        description,
        assigned_to: assignedTo,
        priority,
        created_by: currentUser.username,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to create task");
    }

    // Close modal and reload tasks
    const modal = bootstrap.Modal.getInstance(document.getElementById("createTaskModal"));
    modal.hide();
    document.getElementById("createTaskForm").reset();
    loadTasks();
  } catch (error) {
    alert(error.message);
  }
}

// Utility function to escape HTML
function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// Make functions globally available
window.logout = logout;
window.showTaskDetails = showTaskDetails;
window.createTask = createTask;
```

## 🚀 Step 8: Application Entry Point

### 8.1 Create Main Application (`main.py`)

**Note**: This example uses the modern `SubAppConfig` pattern for multi-app architecture. The application uses **JWT-only authentication** with no server-side sessions.

```python
"""Simple UI application entry point."""
import logging
import sys
from pathlib import Path

from fastapi import FastAPI

# Add parent directories to Python path for framework imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from neuroglia.hosting.web import WebApplicationBuilder, SubAppConfig
from neuroglia.mediation import Mediator
from neuroglia.mapping import Mapper
from neuroglia.serialization.json import JsonSerializer

from domain.repositories.task_repository import TaskRepository
from integration.repositories.in_memory_task_repository import InMemoryTaskRepository

# Configure logging
from application.settings import configure_logging
configure_logging(log_level="INFO")
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create Simple UI application with JWT-only authentication.

    Architecture:
    - API sub-app (/api prefix) - REST API with JWT authentication
    - UI sub-app (/ prefix) - Web interface (no session middleware)

    Authentication: Pure stateless JWT - tokens stored client-side in localStorage
    """

    log.info("🚀 Creating Simple UI application...")

    # Create application builder
    builder = WebApplicationBuilder()

    # Configure services
    services = builder.services

    # Register repositories
    services.add_singleton(TaskRepository, InMemoryTaskRepository)

    # Configure Core services using native .configure() methods
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.commands", "domain.entities"])
    JsonSerializer.configure(builder, ["domain.entities"])

    # Configure sub-applications declaratively
    # API sub-app: REST API with JWT authentication
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title="Simple UI API",
            description="Task management REST API with JWT authentication",
            version="1.0.0",
            controllers=["api.controllers"],
            docs_url="/docs",
        )
    )

    # UI sub-app: Web interface (JWT-only auth, no session middleware needed)
    static_dir = Path(__file__).parent / "static"
    templates_dir = Path(__file__).parent / "ui" / "templates"

    builder.add_sub_app(
        SubAppConfig(
            path="/",
            name="ui",
            title="Simple UI",
            description="Task management web interface",
            version="1.0.0",
            controllers=["ui.controllers"],
            static_files={"/static": str(static_dir)},
            templates_dir=str(templates_dir),
            docs_url=None,  # Disable docs for UI
            # No SessionMiddleware - using JWT-only authentication
        )
    )

    # Build the complete application
    app = builder.build_app_with_lifespan(
        title="Simple UI",
        description="Task management application with JWT-only authentication",
        version="1.0.0",
        debug=True,
    )

    log.info("✅ Application created successfully!")
    log.info("📊 Access points:")
    log.info("   - UI: http://localhost:8082/")
    log.info("   - API Docs: http://localhost:8082/api/docs")
    log.info("   - Auth: POST /api/auth/login")
    log.info("   - Tasks: GET /api/tasks/")

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()

    log.info("🌐 Starting server on http://localhost:8000")
    log.info("👤 Demo users:")
    log.info("   - admin / admin123 (can see all tasks, can create)")
    log.info("   - manager / manager123 (can see non-admin tasks)")
    log.info("   - john.doe / user123 (can see own tasks)")
    log.info("   - jane.smith / user123 (can see own tasks)")

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 🔨 Step 9: Build and Run

### 9.1 Build Frontend Assets

```bash
# Install dependencies
cd ui
npm install

# Build for production
npm run build

# Or run in watch mode for development
npm run dev
```

### 9.2 Run the Application

```bash
# From the simple-ui directory
cd ..
poetry run python main.py
```

### 9.3 Test the Application

1. Open browser to `http://localhost:8000`
2. Login with different users to see role-based access:
   - **admin / admin123**: See all tasks, can create new tasks
   - **manager / manager123**: See all non-admin tasks
   - **john.doe / user123**: See only tasks assigned to john.doe
   - **jane.smith / user123**: See only tasks assigned to jane.smith

## 📚 Key Concepts Explained

### Role-Based Access Control (RBAC)

The application implements RBAC at the query level:

```python
# In GetTasksHandler
if query.role == "admin":
    tasks = await self.task_repository.get_all_async()
elif query.role == "manager":
    all_tasks = await self.task_repository.get_all_async()
    tasks = [t for t in all_tasks if t.created_by != "admin"]
else:
    tasks = await self.task_repository.get_by_user_async(query.username)
```

### JWT Authentication Flow (Stateless)

This application uses **pure stateless JWT authentication** with no server-side sessions:

1. **User Login**:

   - User submits credentials to `/api/auth/login`
   - Server validates and creates JWT token containing user info
   - Token returned to client in response

2. **Client Storage**:

   - Client stores JWT in `localStorage` (client-side only)
   - No session cookies sent from server
   - No server-side session storage

3. **API Requests**:

   - Client includes token in `Authorization: Bearer <token>` header
   - Server validates JWT signature and expiration
   - Server extracts user info directly from token payload

4. **Authorization**:

   - Role and username extracted from JWT payload
   - No database lookup needed for user info
   - Completely stateless validation

5. **Logout**:
   - Client removes token from localStorage
   - No server-side state to clear

**Benefits of JWT-Only Architecture**:

- ✅ **Stateless**: No server-side session storage needed
- ✅ **Scalable**: Works with load balancers and multiple server instances
- ✅ **Microservices Ready**: Easy to share authentication across services
- ✅ **Client Decoding**: Frontend can read user info from JWT without API call
- ✅ **No Session Cookies**: Eliminates CSRF concerns and cookie management
- ✅ **Modern Standard**: Industry best practice for SPA authentication

### Single Page Architecture

- **One HTML file** with multiple sections (login, tasks)
- **JavaScript controls visibility** based on authentication state
- **Modals for interactions** (create task, view details)
- **No page refreshes** - all updates via API calls

### Parcel Build Process

Parcel compiles:

- **SASS → CSS**: Processes `main.scss` with Bootstrap imports
- **JavaScript modules**: Bundles with Bootstrap JS
- **Output**: Minified files in `static/dist/`

## 🎯 Next Steps

### Enhancements to Consider

1. **Persistence**: Replace in-memory repository with MongoDB/PostgreSQL
2. **Real-time Updates**: Add WebSocket support for live task updates
3. **Task Editing**: Add update/delete operations
4. **File Uploads**: Attach files to tasks
5. **Notifications**: Email/push notifications for task assignments
6. **Search & Filters**: Advanced task filtering and search
7. **Drag & Drop**: Kanban board for task management
8. **Analytics**: Dashboard with charts using Chart.js
9. **Dark Mode**: Theme switcher
10. **Mobile App**: React Native/Flutter mobile client

## 🔗 Related Documentation

- [Simple CQRS Guide](simple-cqrs.md)
- [Mario's Pizzeria Sample](../mario-pizzeria.md)
- [MVC Controllers](../features/mvc-controllers.md)
- [Dependency Injection](../features/dependency-injection.md)

## 💡 Tips and Best Practices

1. **Keep DTOs separate** from domain entities
2. **Validate at multiple layers**: client, API, and command handler
3. **Use HTTPS in production** with proper JWT secret keys
4. **Implement refresh tokens** for better security
5. **Add request logging** for debugging and monitoring
6. **Use proper password hashing** (bcrypt, argon2)
7. **Implement rate limiting** to prevent abuse
8. **Add comprehensive error handling**
9. **Write tests** for commands, queries, and controllers
10. **Document your API** with OpenAPI/Swagger

## 🐛 Troubleshooting

### Frontend not loading

- Check Parcel build completed successfully
- Verify static files mount path in `main.py`
- Check browser console for errors

### Authentication failing

- Verify JWT token is being sent in Authorization header
- Check token hasn't expired
- Ensure SECRET_KEY matches between token creation and validation

### Tasks not displaying

- Check browser network tab for API errors
- Verify user role is being passed correctly
- Check repository has sample data

### CORS errors

- Ensure CORS middleware is configured
- Check origin is allowed
- Verify credentials flag is set correctly

---

**Congratulations!** 🎉 You now have a complete single-page application with authentication, authorization, and clean architecture!
