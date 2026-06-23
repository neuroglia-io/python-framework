# 🍕 Mario's Pizzeria - User Profile & Order History Implementation Plan

## 🎯 Overview

This plan implements comprehensive user profile management and order history features for logged-in users, including:

- **User Profile Management**: View and edit customer information without placing orders
- **Order History**: Display past orders with status, dates, and details
- **Enhanced UI Header**: Show user avatar, name, and dropdown menu with profile/logout
- **Keycloak Integration**: Properly extract and display user information from tokens

---

## 📋 Current State Analysis

### ✅ What We Have

- Basic authentication with Keycloak (session-based for UI, JWT for API)
- Customer entity with contact information (name, email, phone, address)
- Order placement and tracking
- Customer repository with email/phone lookups
- Auth service with placeholder user authentication

### ❌ What's Missing

- User profile display and editing capabilities
- Order history by customer
- UI header doesn't show user details prominently
- Profile management without requiring order placement
- Integration between Keycloak user data and Customer entities
- Visual indication of logged-in state

---

## 🏗️ Architecture Changes

### New Components

```
api/
├── dtos/
│   └── profile_dtos.py                 # CustomerProfileDto, UpdateProfileDto
├── controllers/
│   └── profile_controller.py           # Profile management API endpoints

application/
├── commands/
│   ├── create_customer_profile_command.py
│   └── update_customer_profile_command.py
├── queries/
│   ├── get_customer_profile_query.py
│   ├── get_customer_by_user_id_query.py
│   └── get_orders_by_customer_query.py
├── handlers/
│   ├── customer_profile_handler.py     # Profile command/query handlers
│   └── customer_orders_query_handler.py

ui/
├── controllers/
│   └── profile_controller.py           # UI profile page routes
├── templates/
│   ├── profile/
│   │   ├── view.html                   # View profile page
│   │   └── edit.html                   # Edit profile page
│   └── orders/
│       └── history.html                # Order history page
└── src/
    └── scripts/
        └── profile.js                  # Profile management JS
```

---

## 📐 Detailed Implementation Plan

### Phase 1: Backend - Profile Management (2-3 hours)

#### 1.1 Create Profile DTOs

**File: `api/dtos/profile_dtos.py`**

```python
"""DTOs for customer profile management"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class CustomerProfileDto(BaseModel):
    """DTO for customer profile information"""

    id: Optional[str] = None
    user_id: str  # Keycloak user ID
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')
    address: Optional[str] = Field(None, max_length=200)

    # Order statistics (read-only)
    total_orders: int = 0
    favorite_pizza: Optional[str] = None

    class Config:
        from_attributes = True


class CreateProfileDto(BaseModel):
    """DTO for creating a new customer profile"""

    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')
    address: Optional[str] = Field(None, max_length=200)


class UpdateProfileDto(BaseModel):
    """DTO for updating customer profile"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')
    address: Optional[str] = Field(None, max_length=200)
```

#### 1.2 Create Profile Commands

**File: `application/commands/create_customer_profile_command.py`**

```python
"""Command for creating customer profile"""
from dataclasses import dataclass
from typing import Optional

from neuroglia.core import OperationResult
from neuroglia.mapping import map_from, map_to
from neuroglia.mediation import Command, CommandHandler

from api.dtos.profile_dtos import CreateProfileDto, CustomerProfileDto
from domain.entities import Customer
from domain.repositories import ICustomerRepository


@dataclass
class CreateCustomerProfileCommand(Command[OperationResult[CustomerProfileDto]]):
    """Command to create a new customer profile"""

    user_id: str  # Keycloak user ID
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None


class CreateCustomerProfileHandler(CommandHandler[CreateCustomerProfileCommand, OperationResult[CustomerProfileDto]]):
    """Handler for creating customer profiles"""

    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

    async def handle_async(self, command: CreateCustomerProfileCommand) -> OperationResult[CustomerProfileDto]:
        """Handle profile creation"""

        # Check if customer already exists by email
        existing = await self.customer_repository.get_by_email_async(command.email)
        if existing:
            return self.conflict("A customer with this email already exists")

        # Create new customer
        customer = Customer(
            name=command.name,
            email=command.email,
            phone=command.phone,
            address=command.address
        )

        # Store user_id in customer metadata
        customer.state.metadata = {"user_id": command.user_id}

        # Save
        await self.customer_repository.add_async(customer)

        # Map to DTO
        profile_dto = CustomerProfileDto(
            id=customer.id,
            user_id=command.user_id,
            name=customer.state.name,
            email=customer.state.email,
            phone=customer.state.phone,
            address=customer.state.address,
            total_orders=0
        )

        return self.created(profile_dto)
```

**File: `application/commands/update_customer_profile_command.py`**

```python
"""Command for updating customer profile"""
from dataclasses import dataclass
from typing import Optional

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler

from api.dtos.profile_dtos import CustomerProfileDto
from domain.repositories import ICustomerRepository


@dataclass
class UpdateCustomerProfileCommand(Command[OperationResult[CustomerProfileDto]]):
    """Command to update customer profile"""

    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class UpdateCustomerProfileHandler(CommandHandler[UpdateCustomerProfileCommand, OperationResult[CustomerProfileDto]]):
    """Handler for updating customer profiles"""

    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

    async def handle_async(self, command: UpdateCustomerProfileCommand) -> OperationResult[CustomerProfileDto]:
        """Handle profile update"""

        # Retrieve customer
        customer = await self.customer_repository.get_by_id_async(command.customer_id)
        if not customer:
            return self.not_found(f"Customer {command.customer_id} not found")

        # Update contact information
        if command.phone or command.address:
            customer.update_contact_info(
                phone=command.phone if command.phone else customer.state.phone,
                address=command.address if command.address else customer.state.address
            )

        # Update name/email if provided
        if command.name:
            customer.state.name = command.name
        if command.email:
            # Check if email is already taken by another customer
            existing = await self.customer_repository.get_by_email_async(command.email)
            if existing and existing.id != customer.id:
                return self.bad_request("Email already in use by another customer")
            customer.state.email = command.email

        # Save
        await self.customer_repository.update_async(customer)

        # Get order count for user
        # TODO: Query order repository for statistics

        # Map to DTO
        user_id = customer.state.metadata.get("user_id", "") if customer.state.metadata else ""
        profile_dto = CustomerProfileDto(
            id=customer.id,
            user_id=user_id,
            name=customer.state.name,
            email=customer.state.email,
            phone=customer.state.phone,
            address=customer.state.address,
            total_orders=0  # TODO: Get from order stats
        )

        return self.ok(profile_dto)
```

#### 1.3 Create Profile Queries

**File: `application/queries/get_customer_profile_query.py`**

```python
"""Query for retrieving customer profile"""
from dataclasses import dataclass
from typing import Optional

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from api.dtos.profile_dtos import CustomerProfileDto
from domain.repositories import ICustomerRepository, IOrderRepository


@dataclass
class GetCustomerProfileQuery(Query[OperationResult[CustomerProfileDto]]):
    """Query to get customer profile by customer ID"""

    customer_id: str


@dataclass
class GetCustomerProfileByUserIdQuery(Query[OperationResult[CustomerProfileDto]]):
    """Query to get customer profile by Keycloak user ID"""

    user_id: str


class GetCustomerProfileHandler(QueryHandler[GetCustomerProfileQuery, OperationResult[CustomerProfileDto]]):
    """Handler for customer profile queries"""

    def __init__(self, customer_repository: ICustomerRepository, order_repository: IOrderRepository):
        self.customer_repository = customer_repository
        self.order_repository = order_repository

    async def handle_async(self, query: GetCustomerProfileQuery) -> OperationResult[CustomerProfileDto]:
        """Handle profile retrieval"""

        customer = await self.customer_repository.get_by_id_async(query.customer_id)
        if not customer:
            return self.not_found(f"Customer {query.customer_id} not found")

        # Get order statistics
        all_orders = await self.order_repository.get_all_async()
        customer_orders = [o for o in all_orders if o.state.customer_id == customer.id]

        # Calculate favorite pizza
        favorite_pizza = None
        if customer_orders:
            pizza_counts = {}
            for order in customer_orders:
                for item in order.state.items:
                    pizza_counts[item.pizza_name] = pizza_counts.get(item.pizza_name, 0) + item.quantity
            if pizza_counts:
                favorite_pizza = max(pizza_counts, key=pizza_counts.get)

        # Map to DTO
        user_id = customer.state.metadata.get("user_id", "") if customer.state.metadata else ""
        profile_dto = CustomerProfileDto(
            id=customer.id,
            user_id=user_id,
            name=customer.state.name,
            email=customer.state.email,
            phone=customer.state.phone,
            address=customer.state.address,
            total_orders=len(customer_orders),
            favorite_pizza=favorite_pizza
        )

        return self.ok(profile_dto)


class GetCustomerProfileByUserIdHandler(QueryHandler[GetCustomerProfileByUserIdQuery, OperationResult[CustomerProfileDto]]):
    """Handler for getting customer profile by Keycloak user ID"""

    def __init__(self, customer_repository: ICustomerRepository, order_repository: IOrderRepository):
        self.customer_repository = customer_repository
        self.order_repository = order_repository
        self.profile_handler = GetCustomerProfileHandler(customer_repository, order_repository)

    async def handle_async(self, query: GetCustomerProfileByUserIdQuery) -> OperationResult[CustomerProfileDto]:
        """Handle profile retrieval by user ID"""

        # Find customer by user_id in metadata
        all_customers = await self.customer_repository.get_all_async()
        customer = None
        for c in all_customers:
            if c.state.metadata and c.state.metadata.get("user_id") == query.user_id:
                customer = c
                break

        if not customer:
            return self.not_found(f"No customer profile found for user {query.user_id}")

        # Reuse profile handler
        return await self.profile_handler.handle_async(GetCustomerProfileQuery(customer_id=customer.id))
```

**File: `application/queries/get_orders_by_customer_query.py`**

```python
"""Query for retrieving customer order history"""
from dataclasses import dataclass
from typing import List

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

from api.dtos import OrderDto
from domain.repositories import IOrderRepository
from neuroglia.mapping import Mapper


@dataclass
class GetOrdersByCustomerQuery(Query[OperationResult[List[OrderDto]]]):
    """Query to get all orders for a specific customer"""

    customer_id: str
    limit: int = 50


class GetOrdersByCustomerHandler(QueryHandler[GetOrdersByCustomerQuery, OperationResult[List[OrderDto]]]):
    """Handler for customer order history queries"""

    def __init__(self, order_repository: IOrderRepository, mapper: Mapper):
        self.order_repository = order_repository
        self.mapper = mapper

    async def handle_async(self, query: GetOrdersByCustomerQuery) -> OperationResult[List[OrderDto]]:
        """Handle order history retrieval"""

        # Get all orders for customer
        all_orders = await self.order_repository.get_all_async()
        customer_orders = [o for o in all_orders if o.state.customer_id == query.customer_id]

        # Sort by created date (most recent first)
        customer_orders.sort(key=lambda o: o.state.created_at, reverse=True)

        # Limit results
        customer_orders = customer_orders[:query.limit]

        # Map to DTOs
        order_dtos = [self.mapper.map(o, OrderDto) for o in customer_orders]

        return self.ok(order_dtos)
```

#### 1.4 Create Profile API Controller

**File: `api/controllers/profile_controller.py`**

```python
"""Customer profile management API endpoints"""
from typing import List

from classy_fastapi import get, post, put
from fastapi import Depends, HTTPException, status

from api.dtos import OrderDto
from api.dtos.profile_dtos import CreateProfileDto, CustomerProfileDto, UpdateProfileDto
from application.commands.create_customer_profile_command import CreateCustomerProfileCommand
from application.commands.update_customer_profile_command import UpdateCustomerProfileCommand
from application.queries.get_customer_profile_query import GetCustomerProfileByUserIdQuery, GetCustomerProfileQuery
from application.queries.get_orders_by_customer_query import GetOrdersByCustomerQuery
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase


class ProfileController(ControllerBase):
    """Customer profile management endpoints"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/me", response_model=CustomerProfileDto, responses=ControllerBase.error_responses)
    async def get_my_profile(self, user_id: str):
        """Get current user's profile"""
        query = GetCustomerProfileByUserIdQuery(user_id=user_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/", response_model=CustomerProfileDto, status_code=201, responses=ControllerBase.error_responses)
    async def create_profile(self, request: CreateProfileDto, user_id: str):
        """Create a new customer profile"""
        command = CreateCustomerProfileCommand(
            user_id=user_id,
            name=request.name,
            email=request.email,
            phone=request.phone,
            address=request.address
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @put("/me", response_model=CustomerProfileDto, responses=ControllerBase.error_responses)
    async def update_my_profile(self, request: UpdateProfileDto, user_id: str):
        """Update current user's profile"""
        # First get customer by user_id
        query = GetCustomerProfileByUserIdQuery(user_id=user_id)
        profile_result = await self.mediator.execute_async(query)

        if not profile_result.is_success:
            return self.process(profile_result)

        profile = profile_result.data

        # Update profile
        command = UpdateCustomerProfileCommand(
            customer_id=profile.id,
            name=request.name,
            email=request.email,
            phone=request.phone,
            address=request.address
        )
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @get("/me/orders", response_model=List[OrderDto], responses=ControllerBase.error_responses)
    async def get_my_orders(self, user_id: str, limit: int = 50):
        """Get current user's order history"""
        # First get customer by user_id
        profile_query = GetCustomerProfileByUserIdQuery(user_id=user_id)
        profile_result = await self.mediator.execute_async(profile_query)

        if not profile_result.is_success:
            return self.process(profile_result)

        profile = profile_result.data

        # Get orders
        orders_query = GetOrdersByCustomerQuery(customer_id=profile.id, limit=limit)
        result = await self.mediator.execute_async(orders_query)
        return self.process(result)
```

---

### Phase 2: Backend - Keycloak Integration Enhancement (1-2 hours)

#### 2.1 Update Auth Service to Extract Keycloak User Info

**File: `application/services/auth_service.py`** (update)

```python
# Add new method to AuthService class

async def get_keycloak_user_info(self, access_token: str) -> Optional[dict[str, Any]]:
    """
    Retrieve user information from Keycloak using access token.

    Returns user info including: sub (user_id), preferred_username, email, name, etc.
    """
    import httpx
    from application.settings import app_settings

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{app_settings.keycloak_server_url}/realms/{app_settings.keycloak_realm}/protocol/openid-connect/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None
```

#### 2.2 Update UI Auth Controller

**File: `ui/controllers/auth_controller.py`** (update login handler)

```python
# In login method, after successful authentication:

# Get Keycloak user info
user_info = await self.auth_service.get_keycloak_user_info(access_token)

if user_info:
    # Store additional user info in session
    request.session["email"] = user_info.get("email", "")
    request.session["name"] = user_info.get("name", user_info.get("preferred_username", username))
    request.session["user_id"] = user_info.get("sub", "")  # Keycloak user ID

    # Check if customer profile exists, create if not
    from application.queries.get_customer_profile_query import GetCustomerProfileByUserIdQuery
    profile_query = GetCustomerProfileByUserIdQuery(user_id=user_info.get("sub"))
    profile_result = await self.mediator.execute_async(profile_query)

    if not profile_result.is_success:
        # Create profile automatically
        from application.commands.create_customer_profile_command import CreateCustomerProfileCommand
        create_profile_cmd = CreateCustomerProfileCommand(
            user_id=user_info.get("sub"),
            name=user_info.get("name", username),
            email=user_info.get("email", f"{username}@mario-pizzeria.com")
        )
        await self.mediator.execute_async(create_profile_cmd)
```

---

### Phase 3: UI - Enhanced Header & Navigation (1-2 hours)

#### 3.1 Update Base Template Header

**File: `ui/templates/layouts/base.html`** (update navbar section)

```html
<div class="collapse navbar-collapse" id="navbarNav">
  <ul class="navbar-nav me-auto">
    <li class="nav-item">
      <a class="nav-link {% if active_page == 'home' %}active{% endif %}" href="/">Home</a>
    </li>
    <li class="nav-item">
      <a class="nav-link {% if active_page == 'menu' %}active{% endif %}" href="/menu">Menu</a>
    </li>
    {% if authenticated %}
    <li class="nav-item">
      <a class="nav-link {% if active_page == 'orders' %}active{% endif %}" href="/orders">My Orders</a>
    </li>
    {% endif %}
  </ul>

  <!-- User Info Section -->
  <div class="d-flex align-items-center">
    {% if authenticated %}
    <!-- User Dropdown Menu -->
    <div class="dropdown">
      <button
        class="btn btn-outline-light dropdown-toggle d-flex align-items-center"
        type="button"
        id="userDropdown"
        data-bs-toggle="dropdown"
        aria-expanded="false"
      >
        <i class="bi bi-person-circle me-2"></i>
        <span class="d-none d-md-inline">{{ name or username }}</span>
      </button>
      <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
        <li>
          <div class="dropdown-header">
            <strong>{{ name or username }}</strong>
            <br />
            <small class="text-muted">{{ email or '' }}</small>
          </div>
        </li>
        <li><hr class="dropdown-divider" /></li>
        <li>
          <a class="dropdown-item" href="/profile"> <i class="bi bi-person"></i> My Profile </a>
        </li>
        <li>
          <a class="dropdown-item" href="/orders/history"> <i class="bi bi-clock-history"></i> Order History </a>
        </li>
        <li><hr class="dropdown-divider" /></li>
        <li>
          <a class="dropdown-item" href="/auth/logout"> <i class="bi bi-box-arrow-right"></i> Logout </a>
        </li>
      </ul>
    </div>
    {% else %}
    <!-- Guest State -->
    <span class="navbar-text me-3 text-white"> <i class="bi bi-person"></i> Guest </span>
    <a href="/auth/login" class="btn btn-outline-light btn-sm"> <i class="bi bi-box-arrow-in-right"></i> Login </a>
    {% endif %}
  </div>
</div>
```

---

### Phase 4: UI - Profile Pages (2-3 hours)

#### 4.1 Create Profile UI Controller

**File: `ui/controllers/profile_controller.py`**

```python
"""UI controller for customer profile pages"""
from typing import Optional

from classy_fastapi import get, post
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from application.commands.update_customer_profile_command import UpdateCustomerProfileCommand
from application.queries.get_customer_profile_query import GetCustomerProfileByUserIdQuery
from application.settings import app_settings
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase


class UIProfileController(ControllerBase):
    """UI profile management controller"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_class=HTMLResponse)
    async def view_profile(self, request: Request):
        """Display user profile page"""
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/profile", status_code=302)

        user_id = request.session.get("user_id")

        # Get profile
        query = GetCustomerProfileByUserIdQuery(user_id=user_id)
        result = await self.mediator.execute_async(query)

        profile = result.data if result.is_success else None
        error = None if result.is_success else result.error_message

        return request.app.state.templates.TemplateResponse(
            "profile/view.html",
            {
                "request": request,
                "title": "My Profile",
                "active_page": "profile",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "profile": profile,
                "error": error,
                "app_version": app_settings.app_version,
            }
        )

    @get("/edit", response_class=HTMLResponse)
    async def edit_profile_page(self, request: Request):
        """Display profile edit form"""
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/profile/edit", status_code=302)

        user_id = request.session.get("user_id")

        # Get current profile
        query = GetCustomerProfileByUserIdQuery(user_id=user_id)
        result = await self.mediator.execute_async(query)

        profile = result.data if result.is_success else None

        return request.app.state.templates.TemplateResponse(
            "profile/edit.html",
            {
                "request": request,
                "title": "Edit Profile",
                "active_page": "profile",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "profile": profile,
                "app_version": app_settings.app_version,
            }
        )

    @post("/edit")
    async def update_profile(
        self,
        request: Request,
        name: str = Form(...),
        email: str = Form(...),
        phone: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
    ):
        """Handle profile update form submission"""
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login", status_code=302)

        user_id = request.session.get("user_id")

        # Get current profile to get customer_id
        query = GetCustomerProfileByUserIdQuery(user_id=user_id)
        profile_result = await self.mediator.execute_async(query)

        if not profile_result.is_success:
            return request.app.state.templates.TemplateResponse(
                "profile/edit.html",
                {
                    "request": request,
                    "title": "Edit Profile",
                    "error": "Profile not found",
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "app_version": app_settings.app_version,
                },
                status_code=404
            )

        profile = profile_result.data

        # Update profile
        command = UpdateCustomerProfileCommand(
            customer_id=profile.id,
            name=name,
            email=email,
            phone=phone,
            address=address
        )

        result = await self.mediator.execute_async(command)

        if result.is_success:
            # Update session
            request.session["name"] = name
            request.session["email"] = email
            return RedirectResponse(url="/profile?success=true", status_code=302)
        else:
            return request.app.state.templates.TemplateResponse(
                "profile/edit.html",
                {
                    "request": request,
                    "title": "Edit Profile",
                    "profile": profile,
                    "error": result.error_message,
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "name": name,
                    "email": email,
                    "app_version": app_settings.app_version,
                },
                status_code=400
            )
```

#### 4.2 Create Profile View Template

**File: `ui/templates/profile/view.html`**

```html
{% extends "layouts/base.html" %} {% block content %}
<div class="row">
  <div class="col-md-8 mx-auto">
    <div class="card shadow">
      <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
        <h4 class="mb-0"><i class="bi bi-person-circle"></i> My Profile</h4>
        <a href="/profile/edit" class="btn btn-light btn-sm"> <i class="bi bi-pencil"></i> Edit Profile </a>
      </div>
      <div class="card-body">
        {% if error %}
        <div class="alert alert-danger" role="alert"><i class="bi bi-exclamation-triangle"></i> {{ error }}</div>
        {% endif %} {% if request.args.get('success') %}
        <div class="alert alert-success" role="alert">
          <i class="bi bi-check-circle"></i> Profile updated successfully!
        </div>
        {% endif %} {% if profile %}
        <div class="row mb-4">
          <div class="col-md-6">
            <h6 class="text-muted mb-2">Full Name</h6>
            <p class="lead">{{ profile.name }}</p>
          </div>
          <div class="col-md-6">
            <h6 class="text-muted mb-2">Email Address</h6>
            <p class="lead">{{ profile.email }}</p>
          </div>
        </div>

        <div class="row mb-4">
          <div class="col-md-6">
            <h6 class="text-muted mb-2">Phone Number</h6>
            <p class="lead">{{ profile.phone or 'Not provided' }}</p>
          </div>
          <div class="col-md-6">
            <h6 class="text-muted mb-2">Delivery Address</h6>
            <p class="lead">{{ profile.address or 'Not provided' }}</p>
          </div>
        </div>

        <hr />

        <h5 class="mb-3">Order Statistics</h5>
        <div class="row">
          <div class="col-md-6">
            <div class="card bg-light">
              <div class="card-body text-center">
                <h3 class="text-primary">{{ profile.total_orders }}</h3>
                <p class="mb-0">Total Orders</p>
              </div>
            </div>
          </div>
          <div class="col-md-6">
            <div class="card bg-light">
              <div class="card-body text-center">
                <h3 class="text-primary">🍕</h3>
                <p class="mb-0">{{ profile.favorite_pizza or 'No orders yet' }}</p>
                <small class="text-muted">Favorite Pizza</small>
              </div>
            </div>
          </div>
        </div>
        {% else %}
        <div class="alert alert-info"><i class="bi bi-info-circle"></i> No profile information available.</div>
        {% endif %}
      </div>
    </div>

    <div class="mt-4 text-center">
      <a href="/orders/history" class="btn btn-outline-primary">
        <i class="bi bi-clock-history"></i> View Order History
      </a>
    </div>
  </div>
</div>
{% endblock %}
```

#### 4.3 Create Profile Edit Template

**File: `ui/templates/profile/edit.html`**

```html
{% extends "layouts/base.html" %} {% block content %}
<div class="row">
  <div class="col-md-8 mx-auto">
    <div class="card shadow">
      <div class="card-header bg-primary text-white">
        <h4 class="mb-0"><i class="bi bi-pencil"></i> Edit Profile</h4>
      </div>
      <div class="card-body">
        {% if error %}
        <div class="alert alert-danger" role="alert"><i class="bi bi-exclamation-triangle"></i> {{ error }}</div>
        {% endif %}

        <form method="POST" action="/profile/edit">
          <div class="mb-3">
            <label for="name" class="form-label">Full Name *</label>
            <input
              type="text"
              class="form-control"
              id="name"
              name="name"
              value="{{ profile.name if profile else name }}"
              required
              maxlength="100"
            />
          </div>

          <div class="mb-3">
            <label for="email" class="form-label">Email Address *</label>
            <input
              type="email"
              class="form-control"
              id="email"
              name="email"
              value="{{ profile.email if profile else email }}"
              required
            />
          </div>

          <div class="mb-3">
            <label for="phone" class="form-label">Phone Number</label>
            <input
              type="tel"
              class="form-control"
              id="phone"
              name="phone"
              value="{{ profile.phone if profile else '' }}"
              placeholder="+1234567890"
              pattern="^\+?1?\d{9,15}$"
            />
            <small class="form-text text-muted"> Optional. Format: +1234567890 (9-15 digits) </small>
          </div>

          <div class="mb-3">
            <label for="address" class="form-label">Delivery Address</label>
            <textarea class="form-control" id="address" name="address" rows="3" maxlength="200">
{{ profile.address if profile else '' }}</textarea
            >
            <small class="form-text text-muted"> Optional. Your default delivery address. </small>
          </div>

          <div class="d-grid gap-2">
            <button type="submit" class="btn btn-primary"><i class="bi bi-check-circle"></i> Save Changes</button>
            <a href="/profile" class="btn btn-outline-secondary"> <i class="bi bi-x-circle"></i> Cancel </a>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

---

### Phase 5: UI - Order History Page (2 hours)

#### 5.1 Update Orders UI Controller

**File: `ui/controllers/orders_controller.py`** (add history route)

```python
@get("/history", response_class=HTMLResponse)
async def order_history(self, request: Request):
    """Display user's order history"""
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/auth/login?next=/orders/history", status_code=302)

    user_id = request.session.get("user_id")

    # Get customer profile
    from application.queries.get_customer_profile_query import GetCustomerProfileByUserIdQuery
    profile_query = GetCustomerProfileByUserIdQuery(user_id=user_id)
    profile_result = await self.mediator.execute_async(profile_query)

    orders = []
    if profile_result.is_success:
        profile = profile_result.data

        # Get order history
        from application.queries.get_orders_by_customer_query import GetOrdersByCustomerQuery
        orders_query = GetOrdersByCustomerQuery(customer_id=profile.id, limit=50)
        orders_result = await self.mediator.execute_async(orders_query)

        if orders_result.is_success:
            orders = orders_result.data

    return request.app.state.templates.TemplateResponse(
        "orders/history.html",
        {
            "request": request,
            "title": "Order History",
            "active_page": "orders",
            "authenticated": True,
            "username": request.session.get("username"),
            "name": request.session.get("name"),
            "email": request.session.get("email"),
            "orders": orders,
            "app_version": app_settings.app_version,
        }
    )
```

#### 5.2 Create Order History Template

**File: `ui/templates/orders/history.html`**

```html
{% extends "layouts/base.html" %} {% block content %}
<div class="row">
  <div class="col-12">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2><i class="bi bi-clock-history"></i> My Order History</h2>
      <a href="/menu" class="btn btn-primary"> <i class="bi bi-plus-circle"></i> Place New Order </a>
    </div>

    {% if orders %}
    <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">
      {% for order in orders %}
      <div class="col">
        <div class="card h-100 shadow-sm">
          <div class="card-header d-flex justify-content-between align-items-center">
            <span
              class="badge bg-{{ 'success' if order.status == 'ready' else 'warning' if order.status == 'cooking' else 'secondary' }}"
            >
              {{ order.status|upper }}
            </span>
            <small class="text-muted"> {{ order.created_at.strftime('%b %d, %Y') if order.created_at else '' }} </small>
          </div>
          <div class="card-body">
            <h6 class="card-subtitle mb-2 text-muted">Order #{{ order.id[:8] }}</h6>

            <div class="mb-3">
              <strong>Items:</strong>
              <ul class="list-unstyled mb-0">
                {% for item in order.items %}
                <li>
                  <i class="bi bi-pizza"></i>
                  {{ item.quantity }}x {{ item.pizza_name }} {% if item.size != 'medium' %}
                  <span class="badge bg-light text-dark">{{ item.size }}</span>
                  {% endif %}
                </li>
                {% endfor %}
              </ul>
            </div>

            <div class="d-flex justify-content-between align-items-center">
              <span class="h5 mb-0 text-primary">${{ "%.2f"|format(order.total_price) }}</span>
              <a href="/orders/{{ order.id }}" class="btn btn-sm btn-outline-primary"> View Details </a>
            </div>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% else %}
    <div class="card shadow-sm">
      <div class="card-body text-center py-5">
        <i class="bi bi-inbox" style="font-size: 4rem; color: #ccc;"></i>
        <h4 class="mt-3">No Orders Yet</h4>
        <p class="text-muted">You haven't placed any orders yet. Start by browsing our menu!</p>
        <a href="/menu" class="btn btn-primary mt-3"> <i class="bi bi-list-ul"></i> Browse Menu </a>
      </div>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

---

### Phase 6: Service Registration & Routes (1 hour)

#### 6.1 Register New Commands/Queries/Handlers

**File: `main.py`** (update service registration)

```python
# Add imports
from application.commands.create_customer_profile_command import CreateCustomerProfileHandler
from application.commands.update_customer_profile_command import UpdateCustomerProfileHandler
from application.queries.get_customer_profile_query import (
    GetCustomerProfileHandler,
    GetCustomerProfileByUserIdHandler
)
from application.queries.get_orders_by_customer_query import GetOrdersByCustomerHandler

# In configure_services():
services.add_scoped(CreateCustomerProfileHandler)
services.add_scoped(UpdateCustomerProfileHandler)
services.add_scoped(GetCustomerProfileHandler)
services.add_scoped(GetCustomerProfileByUserIdHandler)
services.add_scoped(GetOrdersByCustomerHandler)
```

#### 6.2 Register New Controllers

Controllers are auto-discovered, but ensure they're in the correct locations:

- `api/controllers/profile_controller.py` - API endpoints
- `ui/controllers/profile_controller.py` - UI pages

---

### Phase 7: Testing (2 hours)

#### 7.1 Create Unit Tests

**File: `tests/cases/test_profile_management.py`**

```python
"""Tests for customer profile management"""
import pytest
from unittest.mock import Mock, AsyncMock

from application.commands.create_customer_profile_command import (
    CreateCustomerProfileCommand,
    CreateCustomerProfileHandler
)
from application.commands.update_customer_profile_command import (
    UpdateCustomerProfileCommand,
    UpdateCustomerProfileHandler
)
from domain.entities import Customer


@pytest.mark.asyncio
class TestProfileManagement:

    def setup_method(self):
        self.customer_repository = Mock()
        self.order_repository = Mock()

    async def test_create_profile_success(self):
        """Test successful profile creation"""
        self.customer_repository.get_by_email_async = AsyncMock(return_value=None)
        self.customer_repository.add_async = AsyncMock()

        handler = CreateCustomerProfileHandler(self.customer_repository)
        command = CreateCustomerProfileCommand(
            user_id="keycloak-user-123",
            name="John Doe",
            email="john@example.com",
            phone="+1234567890"
        )

        result = await handler.handle_async(command)

        assert result.is_success
        assert result.data.name == "John Doe"
        assert result.data.email == "john@example.com"
        self.customer_repository.add_async.assert_called_once()

    async def test_create_profile_duplicate_email(self):
        """Test profile creation with duplicate email"""
        existing_customer = Mock(spec=Customer)
        self.customer_repository.get_by_email_async = AsyncMock(return_value=existing_customer)

        handler = CreateCustomerProfileHandler(self.customer_repository)
        command = CreateCustomerProfileCommand(
            user_id="keycloak-user-123",
            name="John Doe",
            email="existing@example.com"
        )

        result = await handler.handle_async(command)

        assert not result.is_success
        assert result.status_code == 409
```

#### 7.2 Create Integration Tests

**File: `tests/integration/test_profile_controller.py`**

```python
"""Integration tests for profile management"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestProfileController:

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self, test_client: AsyncClient):
        """Test getting profile without authentication"""
        response = await test_client.get("/api/profile/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_and_retrieve_profile(self, test_client: AsyncClient, auth_headers):
        """Test full profile creation and retrieval workflow"""
        # Create profile
        profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+1234567890",
            "address": "123 Main St"
        }

        create_response = await test_client.post(
            "/api/profile/",
            json=profile_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201

        # Retrieve profile
        get_response = await test_client.get(
            "/api/profile/me",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        profile = get_response.json()
        assert profile["name"] == "Test User"
        assert profile["email"] == "test@example.com"
```

---

## 📝 Summary

This implementation plan provides:

1. ✅ **Backend Profile Management** - Full CQRS implementation with commands, queries, and handlers
2. ✅ **Keycloak Integration** - Automatic profile creation and user info extraction
3. ✅ **Enhanced UI Header** - User dropdown menu with profile/logout options
4. ✅ **Profile Pages** - View and edit profile information
5. ✅ **Order History** - Display past orders with filtering
6. ✅ **Comprehensive Testing** - Unit and integration tests

### Implementation Order

1. Phase 1: Backend Profile Management (Core functionality)
2. Phase 2: Keycloak Integration (User data extraction)
3. Phase 3: UI Header Enhancement (Visual improvements)
4. Phase 4: Profile Pages (UI implementation)
5. Phase 5: Order History Page (Historical data)
6. Phase 6: Service Registration (Wiring everything together)
7. Phase 7: Testing (Quality assurance)

### Estimated Total Time: 12-16 hours

This follows Neuroglia framework best practices and maintains clean architecture throughout!
