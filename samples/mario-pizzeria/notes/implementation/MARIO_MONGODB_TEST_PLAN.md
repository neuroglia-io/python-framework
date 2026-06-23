# Mario's Pizzeria - MongoDB Integration Test Plan

**Date:** October 22, 2025
**Feature:** Async Motor MongoDB Integration with Profile Management

## 🎯 Test Objectives

Verify that the Motor async MongoDB driver correctly persists and retrieves:

1. Customer profiles (auto-created on Keycloak login)
2. Order history for customers
3. All repository operations work asynchronously

## 📋 Pre-Test Checklist

- [x] Motor package installed (`poetry add motor`)
- [x] Docker image rebuilt with Motor dependency
- [x] All repository methods implemented
- [x] Main.py configured with AsyncIOMotorClient
- [ ] Docker containers running successfully
- [ ] Application starts without errors

## 🧪 Test Scenarios

### Test 1: Customer Profile Auto-Creation on Login

**Objective:** Verify profile is created in MongoDB when user logs in via Keycloak

**Steps:**

1. Navigate to http://localhost:8080
2. Click "Login" or access protected page
3. Login with Keycloak credentials:
   - Username: `customer`
   - Password: `password123`
4. Verify redirect to profile or home page
5. Check MongoDB for customer document

**Expected Results:**

- ✅ Login successful
- ✅ Profile page shows user information
- ✅ MongoDB `mario_pizzeria.customers` collection contains document
- ✅ Document has user_id from Keycloak (sub claim)

**MongoDB Verification:**

```bash
docker exec -it mario-pizzeria-mongodb-1 mongosh
use mario_pizzeria
db.customers.find().pretty()
```

**Expected Document Structure:**

```json
{
  "id": "uuid-string",
  "state": {
    "user_id": "keycloak-sub-id",
    "email": "customer@mario.io",
    "first_name": "Customer",
    "last_name": "User",
    "phone": null,
    "address": null
  },
  "version": 1
}
```

---

### Test 2: Profile Retrieval and Display

**Objective:** Verify profile can be retrieved from MongoDB

**Steps:**

1. Login as customer (if not already logged in)
2. Navigate to Profile page (http://localhost:8080/profile)
3. Verify profile information displays

**Expected Results:**

- ✅ Profile page loads successfully
- ✅ Shows email, name from Keycloak
- ✅ Shows empty fields for phone/address (if not yet filled)
- ✅ No errors in browser console
- ✅ No errors in Docker logs

**Verification:**

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 --tail 50
```

---

### Test 3: Profile Update (MongoDB Write)

**Objective:** Verify profile updates are persisted to MongoDB

**Steps:**

1. Navigate to Profile page
2. Click "Edit Profile"
3. Update fields:
   - Phone: `555-1234`
   - Address: `123 Pizza Street`
4. Save changes
5. Verify success message
6. Check MongoDB for updated document

**Expected Results:**

- ✅ Update successful message displayed
- ✅ Profile page shows updated information
- ✅ MongoDB document updated with new phone/address
- ✅ Version number incremented

**MongoDB Verification:**

```bash
docker exec -it mario-pizzeria-mongodb-1 mongosh
use mario_pizzeria
db.customers.find({"state.email": "customer@mario.io"}).pretty()
```

**Expected Updated Document:**

```json
{
  "id": "uuid-string",
  "state": {
    "user_id": "keycloak-sub-id",
    "email": "customer@mario.io",
    "first_name": "Customer",
    "last_name": "User",
    "phone": "555-1234",
    "address": "123 Pizza Street"
  },
  "version": 2
}
```

---

### Test 4: Order History with Multiple Logins

**Objective:** Verify order history retrieves correctly from MongoDB

**Steps:**

1. Login as customer
2. Place an order (use existing order UI)
3. Navigate to Order History page
4. Verify orders display
5. Logout and login as different user
6. Verify only their orders show

**Expected Results:**

- ✅ Order saved to MongoDB `orders` collection
- ✅ Order history page loads
- ✅ Shows only orders for logged-in customer
- ✅ Order details correct (items, status, timestamp)

**MongoDB Verification:**

```bash
docker exec -it mario-pizzeria-mongodb-1 mongosh
use mario_pizzeria
db.orders.find({"state.customer_id": "customer-id-here"}).pretty()
```

---

### Test 5: Concurrent User Sessions

**Objective:** Verify async operations handle multiple concurrent users

**Steps:**

1. Open 3 different browsers/incognito windows
2. Login as different users in each:
   - customer / password123
   - chef / password123
   - manager / password123
3. Perform operations simultaneously:
   - Customer: View profile
   - Chef: View kitchen orders
   - Manager: View all orders
4. Verify no conflicts or errors

**Expected Results:**

- ✅ All sessions work independently
- ✅ No database connection errors
- ✅ No async operation blocking
- ✅ Response times remain fast (<500ms)

---

### Test 6: Repository Method Coverage

**Objective:** Verify all repository methods work with Motor

**Repository Methods to Test:**

#### CustomerRepository

- [x] `get_async(id)` - Get by ID
- [x] `add_async(entity)` - Create customer
- [x] `update_async(entity)` - Update customer
- [x] `get_by_email_async(email)` - Find by email
- [x] `get_by_user_id_async(user_id)` - Find by Keycloak user_id
- [x] `get_all_async()` - List all customers

#### OrderRepository

- [x] `get_async(id)` - Get by ID
- [x] `add_async(entity)` - Create order
- [x] `update_async(entity)` - Update order
- [x] `get_by_customer_id_async(customer_id)` - Orders by customer
- [x] `get_by_customer_phone_async(phone)` - Orders by phone
- [x] `get_orders_by_status_async(status)` - Orders by status
- [x] `get_active_orders_async()` - Active orders only
- [x] `get_orders_by_date_range_async(start, end)` - Date range query
- [x] `get_all_async()` - List all orders

---

## 🐛 Common Issues to Check

### Issue 1: Motor Not Installed in Container

**Symptom:** `ModuleNotFoundError: No module named 'motor'`
**Solution:** Rebuild Docker image or `docker exec mario-pizzeria-mario-pizzeria-app-1 pip install motor`

### Issue 2: MongoDB Connection Timeout

**Symptom:** `ServerSelectionTimeoutError`
**Check:**

- Is MongoDB container running?
- Is connection string correct? `mongodb://mongodb:27017`
- Network connectivity between containers?

### Issue 3: Serialization Errors

**Symptom:** `TypeError: argument should be a string`
**Check:** Using `serialize_to_text()` not `serialize()`

### Issue 4: Empty Collections

**Symptom:** Profile shows but MongoDB empty
**Check:**

- Are we connecting to correct database?
- Check database name: `mario_pizzeria`
- Check collection names: `customers`, `orders`

---

## 📊 Performance Metrics to Monitor

**Async Performance Indicators:**

- Login → Profile Creation: < 500ms
- Profile Retrieval: < 200ms
- Order History Load: < 300ms
- Concurrent requests: No blocking

**MongoDB Query Performance:**

```bash
# Enable profiling in MongoDB
docker exec -it mario-pizzeria-mongodb-1 mongosh
use mario_pizzeria
db.setProfilingLevel(2)

# View slow queries
db.system.profile.find().sort({ts: -1}).limit(5).pretty()
```

---

## ✅ Success Criteria

Integration is successful when:

1. ✅ All 3 Keycloak users can login
2. ✅ Profiles auto-create in MongoDB
3. ✅ Profile updates persist correctly
4. ✅ Order history retrieves accurately
5. ✅ No async/await errors in logs
6. ✅ Multiple concurrent users work smoothly
7. ✅ MongoDB shows correct documents
8. ✅ Response times remain fast

---

## 🔧 Debugging Commands

**Check Application Logs:**

```bash
docker logs mario-pizzeria-mario-pizzeria-app-1 -f
```

**Check MongoDB Collections:**

```bash
docker exec -it mario-pizzeria-mongodb-1 mongosh
use mario_pizzeria
db.getCollectionNames()
db.customers.countDocuments()
db.orders.countDocuments()
```

**Check Container Status:**

```bash
docker-compose -f docker-compose.mario.yml ps
```

**Restart Application:**

```bash
docker-compose -f docker-compose.mario.yml restart mario-pizzeria-app
```

**Full Rebuild:**

```bash
docker-compose -f docker-compose.mario.yml down
docker-compose -f docker-compose.mario.yml build --no-cache mario-pizzeria-app
docker-compose -f docker-compose.mario.yml up -d
```

---

## 📝 Test Results Log

**Test Date:** **\*\***\_\_\_**\*\***
**Tester:** **\*\***\_\_\_**\*\***
**Environment:** Docker (mario-pizzeria-app)

| Test                          | Status | Notes |
| ----------------------------- | ------ | ----- |
| Test 1: Profile Auto-Creation | ⏳     |       |
| Test 2: Profile Retrieval     | ⏳     |       |
| Test 3: Profile Update        | ⏳     |       |
| Test 4: Order History         | ⏳     |       |
| Test 5: Concurrent Users      | ⏳     |       |
| Test 6: Repository Methods    | ⏳     |       |

**Overall Result:** ⏳ Pending

**Issues Found:** **\*\***\_**\*\***

**Resolution:** **\*\***\_**\*\***
