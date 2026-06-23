# Menu View with Shopping Cart Implementation

**Date:** October 22, 2025
**Status:** ✅ Complete
**Type:** Feature Implementation

---

## Feature Overview

Created a complete menu browsing and ordering interface for authenticated users with:

- Menu display showing available pizzas
- Shopping cart with add-to-cart functionality
- Order form pre-filled with customer profile data
- Order placement via PlaceOrderCommand

---

## Implementation

### 1. UI Menu Controller

**File:** `ui/controllers/menu_controller.py`

**Routes:**

- `GET /menu` - Display menu with shopping cart
- `POST /menu/order` - Place order from cart

**Features:**

- Fetches menu via `GetMenuQuery`
- Pre-fills order form from customer profile
- Validates authentication (login required to order)
- Parses shopping cart data from form
- Creates order via `PlaceOrderCommand`

```python
class UIMenuController(ControllerBase):
    """UI menu controller"""

    def __init__(self, service_provider, mapper, mediator):
        # ...
        Routable.__init__(
            self,
            prefix="/menu",  # Routes: /menu, /menu/order
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def view_menu(self, request: Request):
        """Display menu page"""
        # Get authentication status
        authenticated = request.session.get("authenticated", False)

        # Get menu
        menu_result = await self.mediator.execute_async(GetMenuQuery())
        pizzas = menu_result.data if menu_result.is_success else []

        # Get customer profile if authenticated
        customer_profile = None
        if authenticated and user_id:
            profile_query = GetCustomerProfileByUserIdQuery(user_id=str(user_id))
            profile_result = await self.mediator.execute_async(profile_query)
            customer_profile = profile_result.data if profile_result.is_success else None

        return templates.TemplateResponse("menu/index.html", {
            "authenticated": authenticated,
            "pizzas": pizzas,
            "customer_profile": customer_profile,
            ...
        })
```

### 2. Menu Template

**File:** `ui/templates/menu/index.html`

**Features:**

- Responsive grid layout for pizza cards
- Pizza card UI with price badges
- "Add to Cart" buttons (disabled when not authenticated)
- Shopping cart sidebar with real-time updates
- Order form with delivery details
- JavaScript cart management

**UI Components:**

#### Pizza Card

```html
<div class="card pizza-card h-100">
  <div class="position-relative">
    <div class="card-img-top">🍕</div>
    <span class="price-badge">${{ pizza.total_price }}</span>
  </div>
  <div class="card-body">
    <h5>{{ pizza.name }}</h5>
    <span class="badge bg-secondary">{{ pizza.size }}</span>
    <p><small>{{ pizza.toppings|join(", ") }}</small></p>

    {% if authenticated %}
    <button
      class="btn btn-primary w-100 add-to-cart-btn"
      data-pizza-id="{{ pizza.id }}"
      data-pizza-name="{{ pizza.name }}"
      data-pizza-size="{{ pizza.size }}"
      data-pizza-price="{{ pizza.total_price }}"
      data-pizza-toppings="{{ pizza.toppings|join(',') }}"
    >
      <i class="bi bi-cart-plus"></i> Add to Order
    </button>
    {% else %}
    <button class="btn btn-secondary w-100" disabled><i class="bi bi-lock"></i> Login to Order</button>
    {% endif %}
  </div>
</div>
```

#### Shopping Cart (Authenticated Users Only)

```html
{% if authenticated %}
<div class="order-form">
  <div class="order-summary">
    <h4>Your Order</h4>
    <div id="cart-items">
      <p class="text-muted">No items in cart</p>
    </div>
    <hr />
    <div class="d-flex justify-content-between">
      <strong>Total:</strong>
      <strong id="cart-total">$0.00</strong>
    </div>
  </div>

  <form method="post" action="/menu/order" id="order-form">
    <!-- Delivery details pre-filled from profile -->
    <input name="customer_name" value="{{ customer_profile.name }}" required />
    <input name="customer_email" value="{{ customer_profile.email }}" />
    <input name="customer_phone" value="{{ customer_profile.phone }}" required />
    <textarea name="customer_address" required>{{ customer_profile.address }}</textarea>

    <select name="payment_method" required>
      <option value="cash">Cash on Delivery</option>
      <option value="credit_card">Credit Card</option>
      <option value="debit_card">Debit Card</option>
    </select>

    <textarea name="notes" placeholder="Special instructions"></textarea>

    <!-- Hidden fields populated by JavaScript -->
    <div id="pizza-fields"></div>

    <button type="submit" id="place-order-btn" disabled><i class="bi bi-check-circle"></i> Place Order</button>
  </form>
</div>
{% endif %}
```

### 3. JavaScript Cart Management

**File:** `ui/src/scripts/menu.js` (bundled by Parcel)

**Features:**

- Add items to cart
- Remove items from cart
- Calculate running total
- Update cart display dynamically
- Generate hidden form fields for submission
- Toast notifications

**Key Functions:**

```javascript
/**
 * Menu page shopping cart functionality
 */

let cart = [];

function updateCart() {
  // Update cart items display
  // Update total price
  // Enable/disable "Place Order" button
  // Populate hidden form fields (pizza_0_name, etc.)
}

function addToCart(pizzaName, pizzaSize, pizzaPrice, pizzaToppings) {
  cart.push({ name, size, price, toppings });
  updateCart();
  showToast("Added to cart!", "success");
}

function removeFromCart(index) {
  cart.splice(index, 1);
  updateCart();
  showToast("Removed from cart", "info");
}

function showToast(message, type = "success") {
  // Display temporary notification
}

// Initialize on page load
function initMenuPage() {
  document.querySelectorAll(".add-to-cart-btn").forEach(button => {
    button.addEventListener("click", function () {
      const pizzaName = this.dataset.pizzaName;
      const pizzaSize = this.dataset.pizzaSize;
      const pizzaPrice = this.dataset.pizzaPrice;
      const pizzaToppings = this.dataset.pizzaToppings;

      addToCart(pizzaName, pizzaSize, pizzaPrice, pizzaToppings);
    });
  });
}
```

**Build Configuration:**

The JavaScript is compiled and optimized by Parcel:

```json
// ui/package.json
{
  "scripts": {
    "dev": "parcel watch 'src/scripts/app.js' 'src/scripts/menu.js' 'src/styles/main.scss' ...",
    "build": "parcel build 'src/scripts/app.js' 'src/scripts/menu.js' 'src/styles/main.scss' ..."
  }
}
```

**Template Integration:**

```html
{% block scripts %}
<script src="{{ url_for('static', path='/dist/scripts/menu.js') }}"></script>
{% endblock %}
```

### 4. Order Form Submission

**Flow:**

1. User adds pizzas to cart
2. Fills out delivery details (pre-filled from profile)
3. Selects payment method
4. Clicks "Place Order"
5. Form submits to `POST /menu/order`
6. Controller parses pizza data from hidden fields
7. Creates `PlaceOrderCommand` with pizzas as `CreatePizzaDto` objects
8. Executes command via mediator
9. Redirects to orders page with success/error message

**Controller Logic:**

```python
@post("/order", response_class=HTMLResponse)
async def create_order_from_menu(
    self,
    request: Request,
    customer_name: str = Form(...),
    customer_phone: str = Form(...),
    customer_address: str = Form(...),
    customer_email: Optional[str] = Form(None),
    payment_method: str = Form(...),
    notes: Optional[str] = Form(None),
):
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/auth/login?next=/menu", status_code=302)

    # Parse cart data from form
    form_data = await request.form()
    pizzas = []
    pizza_index = 0

    while f"pizza_{pizza_index}_name" in form_data:
        pizza_name = str(form_data.get(f"pizza_{pizza_index}_name"))
        pizza_size = str(form_data.get(f"pizza_{pizza_index}_size"))
        pizza_toppings = str(form_data.get(f"pizza_{pizza_index}_toppings", ""))

        toppings_list = [t.strip() for t in pizza_toppings.split(",") if t.strip()]

        pizzas.append(CreatePizzaDto(
            name=pizza_name,
            size=pizza_size,
            toppings=toppings_list
        ))
        pizza_index += 1

    # Validate
    if not pizzas:
        return RedirectResponse(url="/menu?error=Please+select+at+least+one+pizza", status_code=303)

    # Create order
    command = PlaceOrderCommand(
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        customer_email=customer_email,
        pizzas=pizzas,
        payment_method=payment_method,
        notes=notes,
    )

    result = await self.mediator.execute_async(command)

    if result.is_success:
        return RedirectResponse(url=f"/orders?success=Order+created", status_code=303)
    else:
        return RedirectResponse(url=f"/menu?error={result.error_message}", status_code=303)
```

---

## User Experience

### For Guest Users (Not Authenticated)

**Menu View:**

- ✅ Can browse menu
- ✅ See pizza prices and toppings
- ❌ Cannot add to cart (buttons disabled)
- ❌ No order form displayed
- 📝 Badge shows: "Login to place orders" with Login button

### For Authenticated Users

**Menu View:**

- ✅ Can browse menu
- ✅ Can add pizzas to cart
- ✅ Shopping cart sidebar visible
- ✅ Order form pre-filled with profile data
- ✅ Can remove items from cart
- ✅ Real-time total calculation
- ✅ Place order button enabled when cart has items

**Order Flow:**

1. Browse menu and add pizzas to cart
2. Review cart contents and total
3. Verify/edit delivery details
4. Select payment method
5. Add special instructions (optional)
6. Click "Place Order"
7. Redirect to orders page with confirmation

---

## Navigation Updates

The menu link is already in the navigation (base.html):

```html
<li class="nav-item">
  <a class="nav-link {% if active_page == 'menu' %}active{% endif %}" href="/menu"> Menu </a>
</li>
```

This menu link is visible to both authenticated and guest users, but only authenticated users can place orders.

---

## Integration with Existing Features

### GetMenuQuery

Reuses existing query to fetch available pizzas:

```python
menu_query = GetMenuQuery()
menu_result = await self.mediator.execute_async(menu_query)
pizzas = menu_result.data if menu_result.is_success else []
```

### GetCustomerProfileByUserIdQuery

Fetches customer profile to pre-fill order form:

```python
if authenticated and user_id:
    profile_query = GetCustomerProfileByUserIdQuery(user_id=str(user_id))
    profile_result = await self.mediator.execute_async(profile_query)
    customer_profile = profile_result.data if profile_result.is_success else None
```

### PlaceOrderCommand

Uses existing command for order creation:

```python
command = PlaceOrderCommand(
    customer_name=customer_name,
    customer_phone=customer_phone,
    customer_address=customer_address,
    customer_email=customer_email,
    pizzas=pizzas,  # List[CreatePizzaDto]
    payment_method=payment_method,
    notes=notes,
)

result = await self.mediator.execute_async(command)
```

---

## Files Created/Modified

### Created

- ✅ `ui/controllers/menu_controller.py` - Menu controller with cart logic
- ✅ `ui/templates/menu/index.html` - Menu view with shopping cart
- ✅ `ui/src/scripts/menu.js` - Shopping cart JavaScript (bundled by Parcel)

### Modified

- ✅ `ui/package.json` - Updated Parcel build to use glob pattern (`src/scripts/*.js`)

**Benefits of glob pattern:**

- Automatically includes all JavaScript files in `src/scripts/`
- No need to manually update config when adding new scripts
- Better scalability as the application grows

### No Changes Needed

- ✅ `main.py` - Auto-discovery finds UIMenuController
- ✅ `ui/templates/layouts/base.html` - Menu link already present
- ✅ Application queries and commands - All reused

---

## Testing

### Manual Test Steps

1. **As Guest User:**

   ```
   Visit: http://localhost:8080/menu
   Expected:
     - ✅ See pizza menu
     - ✅ "Login to place orders" badge
     - ✅ "Login to Order" buttons (disabled)
     - ❌ No shopping cart
   ```

2. **Login:**

   ```
   Click: Login button in menu page badge
   Login: customer / password123
   Expected: Redirect back to /menu
   ```

3. **As Authenticated User:**

   ```
   Visit: http://localhost:8080/menu
   Expected:
     - ✅ See "Ready to order!" badge
     - ✅ "Add to Order" buttons (enabled)
     - ✅ Shopping cart sidebar visible
     - ✅ Order form pre-filled with profile data
   ```

4. **Add Items to Cart:**

   ```
   Click: "Add to Order" on Margherita
   Expected:
     - ✅ Toast notification: "Added to cart!"
     - ✅ Cart shows 1 item
     - ✅ Total updated
     - ✅ "Place Order" button enabled
   ```

5. **Place Order:**

   ```
   Fill: Delivery details (should be pre-filled)
   Select: Payment method
   Click: Place Order
   Expected:
     - ✅ Redirect to /orders with success message
     - ✅ Order created in MongoDB
   ```

---

## CSS Styling

Custom styles for menu page:

```css
.pizza-card {
  transition:
    transform 0.2s,
    box-shadow 0.2s;
  height: 100%;
}

.pizza-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.price-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(211, 47, 47, 0.9);
  color: white;
  padding: 5px 15px;
  border-radius: 20px;
}

.order-form {
  position: sticky;
  top: 20px; /* Sticky cart sidebar */
}

.cart-item {
  background: white;
  border-radius: 5px;
  padding: 10px;
  margin-bottom: 10px;
  border-left: 3px solid #d32f2f;
}
```

---

## Summary

✅ **Complete menu browsing interface**
✅ **Shopping cart with real-time updates**
✅ **Authentication-aware functionality**
✅ **Order form pre-filled from profile**
✅ **Integration with existing CQRS commands**
✅ **Responsive design with hover effects**
✅ **Toast notifications for user feedback**
✅ **Proper error handling and validation**

**Status:** ✅ Implementation Complete - Ready for Testing
