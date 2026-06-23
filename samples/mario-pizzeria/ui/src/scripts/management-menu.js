/**
 * Menu Management JavaScript
 * Handles CRUD operations for pizza menu
 */

// State
let currentPizzas = [];
let currentEditPizzaId = null;
let currentDeletePizzaId = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Menu management page loaded');
    loadPizzas();
    setupModalClickHandlers();
    exposeGlobalFunctions();
});

/**
 * Expose functions to global scope for onclick handlers
 */
function exposeGlobalFunctions() {
    window.showAddPizzaModal = showAddPizzaModal;
    window.closeAddPizzaModal = closeAddPizzaModal;
    window.handleAddPizza = handleAddPizza;
    window.showEditPizzaModal = showEditPizzaModal;
    window.closeEditPizzaModal = closeEditPizzaModal;
    window.handleEditPizza = handleEditPizza;
    window.showDeletePizzaModal = showDeletePizzaModal;
    window.closeDeletePizzaModal = closeDeletePizzaModal;
    window.confirmDeletePizza = confirmDeletePizza;
    console.log('Global functions exposed for onclick handlers');
}

/**
 * Setup modal click handlers for closing on overlay click
 */
function setupModalClickHandlers() {
    // Close modals when clicking outside (on the overlay)
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                // Clicked on overlay, not modal content
                if (modal.id === 'add-pizza-modal') {
                    closeAddPizzaModal();
                } else if (modal.id === 'edit-pizza-modal') {
                    closeEditPizzaModal();
                } else if (modal.id === 'delete-pizza-modal') {
                    closeDeletePizzaModal();
                }
            }
        });
    });

    // Close modals on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAddPizzaModal();
            closeEditPizzaModal();
            closeDeletePizzaModal();
        }
    });
}

/**
 * Load all pizzas from the API
 */
async function loadPizzas() {
    console.log('loadPizzas() called');
    const loadingState = document.getElementById('loading-state');
    const pizzaGrid = document.getElementById('pizza-grid');
    const emptyState = document.getElementById('empty-state');

    console.log('Elements:', { loadingState, pizzaGrid, emptyState });

    if (!loadingState || !pizzaGrid || !emptyState) {
        console.error('Required DOM elements not found!', {
            loadingState: !!loadingState,
            pizzaGrid: !!pizzaGrid,
            emptyState: !!emptyState
        });
        return;
    }

    try {
        // Show loading state
        loadingState.style.display = 'flex';
        pizzaGrid.style.display = 'none';
        emptyState.style.display = 'none';

        console.log('Fetching pizzas from /api/menu/...');

        // Fetch pizzas using GetMenuQuery (note trailing slash is required)
        const response = await fetch('/api/menu/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        console.log('Response received:', response.status, response.statusText);

        if (!response.ok) {
            throw new Error(`Failed to load pizzas: ${response.statusText}`);
        }

        const pizzas = await response.json();
        console.log('Pizzas loaded:', pizzas.length, pizzas);
        currentPizzas = pizzas;

        // Hide loading state
        loadingState.style.display = 'none';

        if (pizzas.length === 0) {
            // Show empty state
            console.log('No pizzas found, showing empty state');
            emptyState.style.display = 'flex';
        } else {
            // Show pizza grid
            pizzaGrid.style.display = 'grid';
            renderPizzas(pizzas);
        }
    } catch (error) {
        console.error('Error loading pizzas:', error);
        loadingState.style.display = 'none';
        showNotification('Failed to load pizzas. Please try again.', 'error');
    }
}

/**
 * Render pizzas to the grid
 */
function renderPizzas(pizzas) {
    const pizzaGrid = document.getElementById('pizza-grid');
    pizzaGrid.innerHTML = '';

    // Add "Add Pizza" card
    const addCard = document.createElement('div');
    addCard.className = 'add-pizza-card';
    addCard.onclick = showAddPizzaModal;
    addCard.innerHTML = `
        <div class="add-icon">➕</div>
        <h3>Add New Pizza</h3>
    `;
    pizzaGrid.appendChild(addCard);

    // Add pizza cards
    pizzas.forEach(pizza => {
        const card = createPizzaCard(pizza);
        pizzaGrid.appendChild(card);
    });
}

/**
 * Create a pizza card element
 */
function createPizzaCard(pizza) {
    const card = document.createElement('div');
    card.className = 'pizza-card';

    // Make entire card clickable to edit (except delete button)
    card.style.cursor = 'pointer';
    card.onclick = (e) => {
        // Don't trigger if clicking delete button
        if (!e.target.closest('.btn-delete')) {
            showEditPizzaModal(pizza.id);
        }
    };

    const toppingsHtml = pizza.toppings && pizza.toppings.length > 0
        ? pizza.toppings.map(t => `<span class="topping-tag">${t}</span>`).join('')
        : '<span class="no-toppings">No toppings</span>';

    card.innerHTML = `
        <div class="pizza-image">
            <div class="pizza-badge">${pizza.size ? pizza.size.toUpperCase() : 'MEDIUM'}</div>
        </div>
        <div class="pizza-details">
            <h3 class="pizza-name">${pizza.name}</h3>
            <div class="pizza-toppings">
                <div class="topping-tags">
                    ${toppingsHtml}
                </div>
            </div>
            <div class="pizza-price">
                <span class="price-label">Base Price</span>
                $${parseFloat(pizza.base_price).toFixed(2)}
            </div>
            <div class="pizza-actions">
                <button class="btn btn-danger w-100 btn-delete" onclick="event.stopPropagation(); showDeletePizzaModal('${pizza.id}', '${pizza.name}')">
                    <i class="bi bi-trash"></i> Delete
                </button>
            </div>
        </div>
    `;

    return card;
}

/**
 * Show Add Pizza Modal
 */
function showAddPizzaModal() {
    console.log('showAddPizzaModal called');
    const modal = document.getElementById('add-pizza-modal');
    const form = document.getElementById('add-pizza-form');

    console.log('Modal element:', modal);
    console.log('Form element:', form);

    if (!modal) {
        console.error('Modal element #add-pizza-modal not found in DOM!');
        return;
    }

    if (!form) {
        console.error('Form element #add-pizza-form not found in DOM!');
        // Continue anyway - form might not need reset on first open
    } else {
        // Reset form
        form.reset();
    }

    // Show modal with class (matches CSS)
    modal.classList.add('show');
    document.body.style.overflow = 'hidden'; // Prevent scrolling
    console.log('Modal should now be visible');
}

/**
 * Close Add Pizza Modal
 */
function closeAddPizzaModal() {
    const modal = document.getElementById('add-pizza-modal');
    modal.classList.remove('show');
    document.body.style.overflow = ''; // Restore scrolling
}

/**
 * Handle Add Pizza Form Submission
 */
async function handleAddPizza(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Get selected toppings
    const toppings = [];
    form.querySelectorAll('input[name="toppings"]:checked').forEach(checkbox => {
        toppings.push(checkbox.value);
    });

    // Build command
    const command = {
        name: formData.get('name'),
        base_price: parseFloat(formData.get('basePrice')),
        size: formData.get('size'),
        toppings: toppings,
    };

    try {
        // Send command to API
        console.log('Sending add pizza command:', command);
        const response = await fetch('/api/menu/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(command),
        });

        console.log('Add pizza response:', response.status, response.statusText);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || errorData.message || 'Failed to add pizza');
        }

        const result = await response.json();
        console.log('Add pizza result:', result);

        // Success!
        showNotification(`Pizza "${command.name}" added successfully!`, 'success');
        closeAddPizzaModal();

        // Reload pizzas
        await loadPizzas();
    } catch (error) {
        console.error('Error adding pizza:', error);
        showNotification(error.message || 'Failed to add pizza. Please try again.', 'error');
    }
}

/**
 * Show Edit Pizza Modal
 */
function showEditPizzaModal(pizzaId) {
    const pizza = currentPizzas.find(p => p.id === pizzaId);
    if (!pizza) {
        showNotification('Pizza not found', 'error');
        return;
    }

    currentEditPizzaId = pizzaId;

    const modal = document.getElementById('edit-pizza-modal');
    const form = document.getElementById('edit-pizza-form');

    // Populate form
    document.getElementById('edit-pizza-id').value = pizza.id;
    document.getElementById('edit-name').value = pizza.name;
    document.getElementById('edit-base-price').value = parseFloat(pizza.base_price);
    document.getElementById('edit-size').value = pizza.size;

    // Set toppings checkboxes
    form.querySelectorAll('input[name="toppings"]').forEach(checkbox => {
        checkbox.checked = pizza.toppings && pizza.toppings.includes(checkbox.value);
    });

    // Show modal with class (matches CSS)
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

/**
 * Close Edit Pizza Modal
 */
function closeEditPizzaModal() {
    const modal = document.getElementById('edit-pizza-modal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
    currentEditPizzaId = null;
}

/**
 * Handle Edit Pizza Form Submission
 */
async function handleEditPizza(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Get selected toppings
    const toppings = [];
    form.querySelectorAll('input[name="toppings"]:checked').forEach(checkbox => {
        toppings.push(checkbox.value);
    });

    // Build command
    const command = {
        pizza_id: currentEditPizzaId,
        name: formData.get('name'),
        base_price: parseFloat(formData.get('basePrice')),
        size: formData.get('size'),
        toppings: toppings,
    };

    try {
        // Send command to API
        console.log('Sending update pizza command:', command);
        const response = await fetch('/api/menu/update', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(command),
        });

        console.log('Update pizza response:', response.status, response.statusText);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || errorData.message || 'Failed to update pizza');
        }

        const result = await response.json();
        console.log('Update pizza result:', result);

        // Success!
        showNotification(`Pizza "${command.name}" updated successfully!`, 'success');
        closeEditPizzaModal();

        // Reload pizzas
        await loadPizzas();
    } catch (error) {
        console.error('Error updating pizza:', error);
        showNotification(error.message || 'Failed to update pizza. Please try again.', 'error');
    }
}

/**
 * Show Delete Confirmation Modal
 */
function showDeletePizzaModal(pizzaId, pizzaName) {
    currentDeletePizzaId = pizzaId;

    const modal = document.getElementById('delete-pizza-modal');
    document.getElementById('delete-pizza-name').textContent = pizzaName;

    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

/**
 * Close Delete Confirmation Modal
 */
function closeDeletePizzaModal() {
    const modal = document.getElementById('delete-pizza-modal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
    currentDeletePizzaId = null;
}

/**
 * Confirm and execute pizza deletion
 */
async function confirmDeletePizza() {
    if (!currentDeletePizzaId) return;

    const command = {
        pizza_id: currentDeletePizzaId,
    };

    try {
        // Send command to API
        console.log('Sending delete pizza command:', command);
        const response = await fetch('/api/menu/remove', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(command),
        });

        console.log('Delete pizza response:', response.status, response.statusText);

        // DELETE returns 204 No Content on success, so no JSON to parse
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || errorData.message || 'Failed to delete pizza');
        }

        // Success!
        showNotification('Pizza removed from menu successfully!', 'success');
        closeDeletePizzaModal();

        // Reload pizzas
        await loadPizzas();
    } catch (error) {
        console.error('Error deleting pizza:', error);
        showNotification(error.message || 'Failed to delete pizza. Please try again.', 'error');
    }
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    const notificationArea = document.getElementById('notification-area');

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;

    const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';

    notification.innerHTML = `
        <span class="notification-icon">${icon}</span>
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;

    notificationArea.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Close modals when clicking outside
document.addEventListener('click', (event) => {
    const addModal = document.getElementById('add-pizza-modal');
    const editModal = document.getElementById('edit-pizza-modal');
    const deleteModal = document.getElementById('delete-pizza-modal');

    if (event.target === addModal) {
        closeAddPizzaModal();
    } else if (event.target === editModal) {
        closeEditPizzaModal();
    } else if (event.target === deleteModal) {
        closeDeletePizzaModal();
    }
});
