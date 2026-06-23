/**
 * Menu page shopping cart functionality
 * Handles add-to-cart, cart updates, and order form population
 */

// Shopping cart state
let cart = [];

/**
 * Update cart display and form fields
 */
function updateCart() {
    const cartItemsDiv = document.getElementById('cart-items');
    const cartTotalSpan = document.getElementById('cart-total');
    const placeOrderBtn = document.getElementById('place-order-btn');
    const pizzaFieldsDiv = document.getElementById('pizza-fields');

    if (!cartItemsDiv || !cartTotalSpan || !placeOrderBtn || !pizzaFieldsDiv) {
        return; // Elements not present on this page
    }

    if (cart.length === 0) {
        cartItemsDiv.innerHTML = '<p class="text-muted text-center py-3"><i class="bi bi-cart"></i> No items in cart</p>';
        cartTotalSpan.textContent = '$0.00';
        placeOrderBtn.disabled = true;
        pizzaFieldsDiv.innerHTML = '';
        return;
    }

    // Update cart items display
    let html = '';
    let total = 0;

    cart.forEach((item, index) => {
        total += parseFloat(item.price);
        html += `
            <div class="cart-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <strong>${item.name}</strong><br>
                        <small class="text-muted">${item.size}</small><br>
                        ${item.toppings ? `<small class="text-muted">${item.toppings}</small><br>` : ''}
                        <strong class="text-primary">$${parseFloat(item.price).toFixed(2)}</strong>
                    </div>
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-danger"
                        onclick="removeFromCart(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
    });

    cartItemsDiv.innerHTML = html;
    cartTotalSpan.textContent = `$${total.toFixed(2)}`;
    placeOrderBtn.disabled = false;

    // Update hidden form fields for submission
    let fieldsHtml = '';
    cart.forEach((item, index) => {
        fieldsHtml += `
            <input type="hidden" name="pizza_${index}_name" value="${item.name}">
            <input type="hidden" name="pizza_${index}_size" value="${item.size}">
            <input type="hidden" name="pizza_${index}_toppings" value="${item.toppings || ''}">
        `;
    });
    pizzaFieldsDiv.innerHTML = fieldsHtml;
}

/**
 * Add a pizza to the shopping cart
 * @param {string} pizzaName - Name of the pizza
 * @param {string} pizzaSize - Size of the pizza
 * @param {string|number} pizzaPrice - Price of the pizza
 * @param {string} pizzaToppings - Comma-separated list of toppings
 */
function addToCart(pizzaName, pizzaSize, pizzaPrice, pizzaToppings) {
    cart.push({
        name: pizzaName,
        size: pizzaSize,
        price: pizzaPrice,
        toppings: pizzaToppings
    });
    updateCart();

    // Show toast notification
    showToast('Added to cart!', 'success');
}

/**
 * Remove a pizza from the shopping cart
 * @param {number} index - Index of the item in the cart array
 */
function removeFromCart(index) {
    cart.splice(index, 1);
    updateCart();
    showToast('Removed from cart', 'info');
}

/**
 * Show a temporary toast notification
 * @param {string} message - Message to display
 * @param {string} type - Bootstrap alert type (success, info, warning, danger)
 */
function showToast(message, type = 'success') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    toast.style.zIndex = '9999';
    toast.innerHTML = `<i class="bi bi-check-circle"></i> ${message}`;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 2000);
}

/**
 * Initialize menu page functionality
 */
function initMenuPage() {
    // Add event listeners to all "Add to Cart" buttons
    document.querySelectorAll('.add-to-cart-btn').forEach(button => {
        button.addEventListener('click', function () {
            const pizzaName = this.dataset.pizzaName;
            const pizzaSize = this.dataset.pizzaSize;
            const pizzaPrice = this.dataset.pizzaPrice;
            const pizzaToppings = this.dataset.pizzaToppings;

            addToCart(pizzaName, pizzaSize, pizzaPrice, pizzaToppings);
        });
    });

    // Initialize empty cart display
    updateCart();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMenuPage);
} else {
    // DOM already loaded
    initMenuPage();
}

// Export functions for global access (for inline onclick handlers)
window.addToCart = addToCart;
window.removeFromCart = removeFromCart;
window.showToast = showToast;
