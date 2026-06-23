# Customer Profile Created Event Implementation

## Summary

Added `CustomerProfileCreatedEvent` domain event to track profile creation separately from customer registration. This enables profile-specific side effects like welcome emails, onboarding workflows, and analytics tracking.

## Problem

The application was creating customer profiles (both explicitly via UI and automatically during Keycloak login) without raising a specific domain event. This meant:

- No welcome emails sent to new profile users
- No onboarding workflows triggered
- No analytics tracking for profile creation source (web vs SSO)
- No distinction between "customer registered" and "profile created"

## Solution

### 1. Created `CustomerProfileCreatedEvent`

**File**: `samples/mario-pizzeria/domain/events.py`

```python
@dataclass
class CustomerProfileCreatedEvent(DomainEvent):
    """
    Event raised when a customer profile is created (either explicitly or auto-created from Keycloak).

    This is distinct from CustomerRegisteredEvent - this specifically indicates
    profile creation which may trigger welcome emails, onboarding workflows, etc.
    """

    aggregate_id: str  # Customer ID
    user_id: str  # Keycloak user ID
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

    def __post_init__(self):
        """Initialize parent class fields after dataclass initialization"""
        if not hasattr(self, "created_at"):
            self.created_at = datetime.now()
        if not hasattr(self, "aggregate_version"):
            self.aggregate_version = 0
```

### 2. Created Event Handler

**File**: `samples/mario-pizzeria/application/event_handlers.py`

```python
class CustomerProfileCreatedEventHandler(DomainEventHandler[CustomerProfileCreatedEvent]):
    """
    Handles customer profile creation events.

    This is triggered when a profile is explicitly created (via UI or auto-created from Keycloak).
    This is a distinct business event from general customer registration.
    """

    async def handle_async(self, event: CustomerProfileCreatedEvent) -> Any:
        """Process customer profile created event"""
        logger.info(
            f"✨ Customer profile created for {event.name} ({event.email}) - "
            f"Customer ID: {event.aggregate_id}, User ID: {event.user_id}"
        )

        # In a real application, you might:
        # - Send welcome/onboarding email with profile setup confirmation
        # - Create initial loyalty account with welcome bonus
        # - Send first-order discount code
        # - Add to marketing lists (with consent)
        # - Trigger onboarding workflow
        # - Send SMS confirmation of profile creation
        # - Update CRM systems with new profile
        # - Initialize recommendation engine with user preferences
        # - Track profile creation source (web, mobile, SSO auto-creation)

        return None
```

### 3. Updated Command Handler to Publish Event

**File**: `samples/mario-pizzeria/application/commands/create_customer_profile_command.py`

**Changes:**

- Added `Mediator` dependency injection
- Added `CustomerProfileCreatedEvent` import
- **Publish event after saving customer**

```python
class CreateCustomerProfileHandler(
    CommandHandler[CreateCustomerProfileCommand, OperationResult[CustomerProfileDto]]
):
    """Handler for creating customer profiles"""

    def __init__(self, customer_repository: ICustomerRepository, mediator: Mediator):
        self.customer_repository = customer_repository
        self.mediator = mediator

    async def handle_async(
        self, request: CreateCustomerProfileCommand
    ) -> OperationResult[CustomerProfileDto]:
        """Handle profile creation"""

        # ... validation and customer creation ...

        # Save (this persists the Customer entity with CustomerRegisteredEvent)
        await self.customer_repository.add_async(customer)

        # Publish CustomerProfileCreatedEvent for profile-specific side effects
        # (welcome emails, onboarding workflows, etc.)
        profile_created_event = CustomerProfileCreatedEvent(
            aggregate_id=customer.id(),
            user_id=request.user_id,
            name=request.name,
            email=request.email,
            phone=request.phone,
            address=request.address,
        )
        await self.mediator.publish_async(profile_created_event)

        # ... return result ...
```

## Event Flow

### Scenario 1: Explicit Profile Creation (via UI/API)

```
User submits profile form
    ↓
ProfileController receives CreateProfileDto
    ↓
Mediator executes CreateCustomerProfileCommand
    ↓
CreateCustomerProfileHandler:
    1. Creates Customer entity (raises CustomerRegisteredEvent internally)
    2. Saves to repository
    3. Publishes CustomerProfileCreatedEvent via Mediator
    ↓
Mediator dispatches to CustomerProfileCreatedEventHandler
    ↓
Handler logs profile creation, sends welcome email, triggers onboarding
```

### Scenario 2: Auto-Creation During Keycloak Login

```
User logs in with Keycloak
    ↓
AuthController receives OAuth callback
    ↓
_ensure_customer_profile() checks if profile exists
    ↓
If not exists:
    Mediator executes CreateCustomerProfileCommand
    ↓
    [Same flow as Scenario 1]
    ↓
Profile created + CustomerProfileCreatedEvent published
    ↓
Welcome workflow triggered automatically
```

## Key Design Points

### 1. **Separation of Concerns**

- **CustomerRegisteredEvent**: Domain event raised by `Customer` entity during construction

  - Part of the aggregate's event sourcing
  - Represents the business fact: "A customer was registered in the system"
  - Used for state reconstruction if using event sourcing

- **CustomerProfileCreatedEvent**: Application-level event published by command handler
  - Represents the business process: "A user profile was created"
  - Triggers side effects: welcome emails, onboarding, analytics
  - Can include additional context (user_id, creation source)

### 2. **Event Publishing Pattern**

The framework supports two event patterns:

1. **Domain Events** (raised by aggregates):

   ```python
   self.state.on(self.register_event(CustomerRegisteredEvent(...)))
   ```

   - Automatically persisted with aggregate
   - Part of aggregate history
   - Used for state reconstruction

2. **Application Events** (published by handlers):

   ```python
   await self.mediator.publish_async(CustomerProfileCreatedEvent(...))
   ```

   - Dispatched to event handlers immediately
   - Used for cross-cutting concerns and side effects
   - Not part of aggregate state

### 3. **Dependency Injection**

The handler now requires both dependencies:

- `ICustomerRepository`: For data access
- `Mediator`: For event publishing

DI container automatically resolves both during handler registration.

### 4. **Idempotency Consideration**

The `CreateCustomerProfileHandler` checks for existing customers by email:

```python
existing = await self.customer_repository.get_by_email_async(request.email)
if existing:
    return self.bad_request("A customer with this email already exists")
```

This prevents:

- Duplicate profile creation
- Multiple welcome emails
- Duplicate event publishing

## Testing

### Manual Testing Steps

1. **Start application**:

   ```bash
   make sample-mario-bg
   ```

2. **Test Scenario 1 - Auto-creation during login**:

   - Navigate to http://localhost:8080/
   - Login with new Keycloak user (customer/password123)
   - Check logs for:
     - `👋 New customer registered:` (from CustomerRegisteredEvent)
     - `✨ Customer profile created for` (from CustomerProfileCreatedEvent)

3. **Test Scenario 2 - Explicit profile creation**:
   - Login as admin
   - Create new profile via API or UI
   - Check logs for both events

### Expected Log Output

```
INFO: 👋 New customer registered: John Doe (john@example.com) - ID: customer-abc123
INFO: ✨ Customer profile created for John Doe (john@example.com) - Customer ID: customer-abc123, User ID: keycloak-xyz789
```

### Unit Test (Future)

```python
@pytest.mark.asyncio
async def test_create_profile_publishes_event():
    # Arrange
    mock_repo = Mock(spec=ICustomerRepository)
    mock_repo.get_by_email_async.return_value = None

    mock_mediator = Mock(spec=Mediator)

    handler = CreateCustomerProfileHandler(mock_repo, mock_mediator)
    command = CreateCustomerProfileCommand(
        user_id="user-123",
        name="John Doe",
        email="john@example.com"
    )

    # Act
    result = await handler.handle_async(command)

    # Assert
    assert result.is_success
    mock_mediator.publish_async.assert_called_once()

    published_event = mock_mediator.publish_async.call_args[0][0]
    assert isinstance(published_event, CustomerProfileCreatedEvent)
    assert published_event.user_id == "user-123"
    assert published_event.email == "john@example.com"
```

## Benefits

### 1. **Welcome Workflow Automation**

- Welcome emails sent automatically
- Onboarding sequences triggered
- First-order discount codes delivered

### 2. **Analytics & Tracking**

- Track profile creation sources (web, mobile, SSO)
- Measure conversion rates
- Analyze user onboarding patterns

### 3. **Integration Points**

- CRM system updates
- Marketing automation triggers
- Customer success platform notifications

### 4. **Extensibility**

- Easy to add new side effects without modifying core logic
- Multiple handlers can respond to same event
- Loose coupling between profile creation and side effects

## Future Enhancements

### 1. **Profile Creation Source Tracking**

Add `source` field to event:

```python
@dataclass
class CustomerProfileCreatedEvent(DomainEvent):
    aggregate_id: str
    user_id: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    source: str = "unknown"  # "web", "mobile", "sso_auto", "admin"
```

### 2. **Separate Event Handlers by Concern**

- `WelcomeEmailHandler`: Sends welcome email
- `LoyaltyAccountHandler`: Creates loyalty account
- `AnalyticsHandler`: Tracks profile creation metrics
- `CRMSyncHandler`: Updates external CRM

### 3. **Event Metadata**

Add contextual information:

```python
profile_created_event = CustomerProfileCreatedEvent(
    aggregate_id=customer.id(),
    user_id=request.user_id,
    name=request.name,
    email=request.email,
    phone=request.phone,
    address=request.address,
    metadata={
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "referrer": request.session.get("referrer"),
        "creation_source": "keycloak_sso",
    }
)
```

## Related Documentation

- **Domain Events**: `samples/mario-pizzeria/domain/events.py`
- **Event Handlers**: `samples/mario-pizzeria/application/event_handlers.py`
- **Command Handlers**: `samples/mario-pizzeria/application/commands/`
- **Neuroglia Mediation**: Framework documentation on CQRS and event dispatching
- **DDD Patterns**: `notes/DDD.md`

## Conclusion

The `CustomerProfileCreatedEvent` provides a clean separation between:

1. **Domain fact**: Customer entity was created (`CustomerRegisteredEvent`)
2. **Business process**: User profile was established (`CustomerProfileCreatedEvent`)

This enables flexible, decoupled side effects for onboarding, marketing, and customer engagement workflows without coupling these concerns to the core domain logic.
