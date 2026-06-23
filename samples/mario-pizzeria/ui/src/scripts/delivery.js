/**
 * Mario's Pizzeria - Delivery Dashboard JavaScript
 *
 * Handles SSE connections, order updates, and delivery driver interactions
 */

// SSE Connection Management
let eventSource = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

/**
 * Connect to delivery SSE stream
 */
export function connectDeliveryStream() {
    console.log('Connecting to delivery stream...');
    eventSource = new EventSource('/delivery/stream');

    eventSource.onopen = function () {
        console.log('Delivery stream connected');
        updateConnectionStatus(true);
        reconnectAttempts = 0;
    };

    eventSource.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (window.location.pathname === '/delivery') {
            updateReadyOrders(data.delivery_orders);
        } else if (window.location.pathname === '/delivery/tour') {
            updateTourOrders(data.tour_orders);
        }
    };

    eventSource.onerror = function (error) {
        console.error('Delivery stream error:', error);
        updateConnectionStatus(false);
        eventSource.close();

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            setTimeout(connectDeliveryStream, 3000 * reconnectAttempts);
        }
    };
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(connected) {
    const statusDiv = document.getElementById('connectionStatus');
    const statusText = document.getElementById('statusText');

    if (statusDiv && statusText) {
        if (connected) {
            statusDiv.className = 'connection-status connected';
            statusText.innerHTML = '<i class="bi bi-wifi"></i> Live Updates Active';
        } else {
            statusDiv.className = 'connection-status disconnected';
            statusText.innerHTML = '<i class="bi bi-wifi-off"></i> Connection Lost';
        }
    }
}

/**
 * Update ready orders display
 */
function updateReadyOrders(orders) {
    const countElement = document.getElementById('readyOrderCount');
    if (countElement) {
        countElement.textContent = orders.length;
    }

    // Check if orders have changed (only compare order IDs)
    const currentOrderElements = Array.from(document.querySelectorAll('[data-order-id]'));
    const currentOrderIds = currentOrderElements
        .map((el) => el.dataset.orderId)
        .filter((id) => id)
        .sort();
    const newOrderIds = orders.map((o) => o.id).sort();

    // Only reload if the SET of order IDs has actually changed
    const ordersChanged =
        currentOrderIds.length !== newOrderIds.length ||
        currentOrderIds.some((id, index) => id !== newOrderIds[index]);

    if (ordersChanged) {
        console.log('Ready orders changed, refreshing display...');
        location.reload();
    }
}

/**
 * Update delivery tour orders
 */
function updateTourOrders(orders) {
    const countElement = document.getElementById('tourOrderCount');
    if (countElement) {
        countElement.textContent = orders.length;
    }

    // Similar logic for tour orders
    const currentOrderElements = Array.from(document.querySelectorAll('[data-order-id]'));
    const currentOrderIds = currentOrderElements
        .map((el) => el.dataset.orderId)
        .filter((id) => id)
        .sort();
    const newOrderIds = orders.map((o) => o.id).sort();

    const ordersChanged =
        currentOrderIds.length !== newOrderIds.length ||
        currentOrderIds.some((id, index) => id !== newOrderIds[index]);

    if (ordersChanged) {
        console.log('Tour orders changed, refreshing display...');
        location.reload();
    }
}

/**
 * Show success modal with message
 */
function showSuccessModal(message) {
    const modal = document.getElementById('successModal');
    const messageElement = document.getElementById('successMessage');

    if (modal && messageElement) {
        messageElement.textContent = message;
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Auto-reload after 2 seconds
        setTimeout(() => {
            location.reload();
        }, 2000);
    }
}

/**
 * Show error modal with message
 */
function showErrorModal(message) {
    const modal = document.getElementById('errorModal');
    const messageElement = document.getElementById('errorMessage');

    if (modal && messageElement) {
        messageElement.textContent = message;
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

/**
 * Assign order to delivery tour
 */
export async function assignOrder(orderId) {
    try {
        const response = await fetch(`/delivery/${orderId}/assign`, {
            method: 'POST',
        });

        const result = await response.json();

        if (result.success) {
            showSuccessModal('Order added to your delivery tour!');
        } else {
            showErrorModal(result.error || 'Failed to add order to tour');
        }
    } catch (error) {
        console.error('Error assigning order:', error);
        showErrorModal('Failed to add order to tour');
    }
}

/**
 * Mark order as delivered
 */
export async function markDelivered(orderId) {
    // Show confirmation modal
    const confirmModal = document.getElementById('confirmModal');
    const confirmBtn = document.getElementById('confirmDeliveryBtn');

    if (!confirmModal || !confirmBtn) {
        // Fallback to native confirm if modal not found
        if (!confirm('Mark this order as delivered?')) {
            return;
        }
        await executeMarkDelivered(orderId);
        return;
    }

    const bsConfirmModal = new bootstrap.Modal(confirmModal);
    bsConfirmModal.show();

    // Handle confirmation
    const handleConfirm = async () => {
        confirmBtn.removeEventListener('click', handleConfirm);
        bsConfirmModal.hide();
        await executeMarkDelivered(orderId);
    };

    confirmBtn.addEventListener('click', handleConfirm);
}

/**
 * Execute mark delivered action
 */
async function executeMarkDelivered(orderId) {
    try {
        const response = await fetch(`/delivery/${orderId}/deliver`, {
            method: 'POST',
        });

        const result = await response.json();

        if (result.success) {
            showSuccessModal('Order marked as delivered!');
        } else {
            showErrorModal(result.error || 'Failed to mark order as delivered');
        }
    } catch (error) {
        console.error('Error marking order delivered:', error);
        showErrorModal('Failed to mark order as delivered');
    }
}

/**
 * Update elapsed times for waiting orders
 */
function updateElapsedTimes() {
    document.querySelectorAll('.waiting-time').forEach((el) => {
        const readyTime = new Date(el.dataset.readyTime);
        const now = new Date();
        const elapsed = Math.floor((now - readyTime) / 1000 / 60); // minutes

        const elapsedSpan = el.querySelector('.elapsed-time');
        if (elapsedSpan) {
            if (elapsed < 1) {
                elapsedSpan.textContent = 'just now';
            } else if (elapsed < 60) {
                elapsedSpan.textContent = `${elapsed} min ago`;
            } else {
                const hours = Math.floor(elapsed / 60);
                const mins = elapsed % 60;
                elapsedSpan.textContent = `${hours}h ${mins}m ago`;
            }

            // Highlight urgent orders (waiting > 15 min)
            if (elapsed > 15) {
                el.classList.add('urgent');
            } else {
                el.classList.remove('urgent');
            }
        }
    });
}

/**
 * Initialize delivery dashboard
 */
export function initDeliveryDashboard() {
    console.log('Initializing delivery dashboard...');

    // Connect to SSE
    connectDeliveryStream();

    // Update elapsed times
    updateElapsedTimes();
    setInterval(updateElapsedTimes, 30000); // Update every 30 seconds

    // Cleanup on page unload
    window.addEventListener('beforeunload', function () {
        if (eventSource) {
            eventSource.close();
        }
    });

    // Make functions available globally for onclick handlers
    window.assignOrder = assignOrder;
    window.markDelivered = markDelivered;
}

// Auto-initialize if on delivery pages
if (
    document.readyState === 'loading'
) {
    document.addEventListener('DOMContentLoaded', function () {
        if (
            window.location.pathname.startsWith('/delivery')
        ) {
            initDeliveryDashboard();
        }
    });
} else {
    if (
        window.location.pathname.startsWith('/delivery')
    ) {
        initDeliveryDashboard();
    }
}
