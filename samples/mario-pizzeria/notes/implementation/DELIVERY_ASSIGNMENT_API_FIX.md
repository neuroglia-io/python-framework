# Delivery Assignment API Fix

## Issue

User reported error when trying to assign order to delivery:

```
POST http://localhost:8080/delivery/3d0e65f5-5b6b-4b22-a988-dfb21632a539/assign
Response: {
    "success": false,
    "error": "Failed to assign order to delivery: Only ready orders can be assigned to delivery"
}
```

## Root Cause

**Two potential issues:**

### 1. Missing API Endpoint

The `/delivery/{order_id}/assign` endpoint did not exist in the API layer (port 8080).

- The endpoint only existed in the UI layer (port 8000) at `ui/controllers/delivery_controller.py`
- API calls to port 8080 would result in 404 Not Found

### 2. Order Status Validation

The error message "Only ready orders can be assigned to delivery" comes from the domain entity's business rule:

```python
# domain/entities/order.py
def assign_to_delivery(self, delivery_person_id: str) -> None:
    """Assign order to a delivery driver"""
    if self.state.status != OrderStatus.READY:
        raise ValueError("Only ready orders can be assigned to delivery")
```

This means the order was NOT in `READY` status when the assignment was attempted.

## Solution Implemented

### Created New API Controller: `api/controllers/delivery_controller.py`

Added a proper delivery controller to the API layer with the following endpoints:

#### 1. Get Ready Orders

```
GET /delivery/ready
```

Returns all orders that are ready for delivery pickup.

#### 2. Assign Order to Delivery Person

```
POST /delivery/{order_id}/assign
```

**Request Body:**

```json
{
  "delivery_person_id": "driver-123"
}
```

**Response (Success):**

```json
{
    "id": "3d0e65f5-5b6b-4b22-a988-dfb21632a539",
    "status": "delivering",
    "delivery_person_id": "driver-123",
    ...
}
```

**Response (Failure - Wrong Status):**

```json
{
  "success": false,
  "error": "Only ready orders can be assigned to delivery"
}
```

## Order Status Flow

For an order to be assignable to delivery, it must follow this status progression:

1. **PENDING** - Order created
2. **CONFIRMED** - Order confirmed by restaurant
3. **COOKING** - Order being prepared
4. **READY** - Order ready for pickup ⭐ **(Required for assignment)**
5. **DELIVERING** - Assigned to driver and out for delivery
6. **DELIVERED** - Successfully delivered

## How to Properly Assign an Order

### Step 1: Ensure Order is READY

Check order status:

```bash
curl http://localhost:8080/orders/{order_id}
```

If not READY, progress the order through the workflow:

```bash
# If PENDING → Mark as confirmed (usually automatic)
curl -X PUT http://localhost:8080/orders/{order_id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'

# If CONFIRMED → Start cooking
curl -X PUT http://localhost:8080/orders/{order_id}/cook

# If COOKING → Mark as ready
curl -X PUT http://localhost:8080/orders/{order_id}/ready
```

### Step 2: Assign to Delivery Person

Once order is in READY status:

```bash
curl -X POST http://localhost:8080/delivery/{order_id}/assign \
  -H "Content-Type: application/json" \
  -d '{"delivery_person_id": "driver-456"}'
```

## Updated Files

1. **Created:** `api/controllers/delivery_controller.py`

   - New API controller for delivery operations
   - Handles order assignment via POST endpoint
   - Uses AssignOrderToDeliveryCommand

2. **Updated:** `api/controllers/orders_controller.py`
   - Added import for AssignOrderToDeliveryCommand
   - Added PUT /orders/{order_id}/assign endpoint (alternative route)

## API Documentation

### Port Configuration

- **Port 8080**: API layer (stateless JSON API)
- **Port 8000**: UI layer (web interface with sessions)

### Available Delivery Endpoints (Port 8080)

| Method | Endpoint                      | Description            | Status Required |
| ------ | ----------------------------- | ---------------------- | --------------- |
| GET    | `/delivery/ready`             | Get all ready orders   | N/A             |
| POST   | `/delivery/{order_id}/assign` | Assign order to driver | READY           |

### Alternative Order Endpoints (Port 8080)

| Method | Endpoint                    | Description        |
| ------ | --------------------------- | ------------------ |
| PUT    | `/orders/{order_id}/cook`   | Start cooking      |
| PUT    | `/orders/{order_id}/ready`  | Mark as ready      |
| PUT    | `/orders/{order_id}/assign` | Assign to delivery |

## Testing the Fix

### Test Scenario 1: Successful Assignment

```bash
# 1. Create an order (returns order_id)
ORDER_ID=$(curl -X POST http://localhost:8080/orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test-customer",
    "pizzas": [{"name": "Margherita", "size": "medium"}]
  }' | jq -r '.id')

# 2. Progress through workflow
curl -X PUT "http://localhost:8080/orders/$ORDER_ID/cook"
curl -X PUT "http://localhost:8080/orders/$ORDER_ID/ready"

# 3. Assign to delivery
curl -X POST "http://localhost:8080/delivery/$ORDER_ID/assign" \
  -H "Content-Type: application/json" \
  -d '{"delivery_person_id": "driver-123"}'
```

### Test Scenario 2: Wrong Status Error

```bash
# Try to assign PENDING order (should fail)
ORDER_ID="some-pending-order-id"

curl -X POST "http://localhost:8080/delivery/$ORDER_ID/assign" \
  -H "Content-Type: application/json" \
  -d '{"delivery_person_id": "driver-123"}'

# Expected response:
# {
#   "success": false,
#   "error": "Only ready orders can be assigned to delivery"
# }
```

## Business Rules Enforced

The domain entity enforces these invariants:

1. **Only READY orders can be assigned** - Prevents assigning orders that aren't prepared
2. **Delivery person ID required** - Must specify who is delivering
3. **Assignment creates event** - OrderAssignedToDeliveryEvent is raised
4. **Status transitions automatically** - Assignment triggers DELIVERING status

## Next Steps

If the error persists after this fix:

1. **Verify order status:**

   ```bash
   curl http://localhost:8080/orders/{order_id} | jq '.status'
   ```

2. **Check order progression:**

   - Ensure order has been cooked
   - Ensure order has been marked ready
   - Verify no business rule violations

3. **Review logs:**

   ```bash
   docker logs mario-pizzeria-mario-pizzeria-app-1 --tail 50
   ```

4. **Check MongoDB directly:**
   ```bash
   docker exec mario-pizzeria-mongodb-1 mongosh mario_pizzeria --eval 'db.orders.findOne({_id: "{order_id}"})'
   ```

## Summary

✅ **Created** API delivery controller with proper endpoints
✅ **Added** POST `/delivery/{order_id}/assign` to API layer
✅ **Documented** order status requirements
✅ **Provided** test scenarios and examples
✅ **Explained** business rules and validation

The endpoint is now available on port 8080 and will properly validate order status before assignment.
