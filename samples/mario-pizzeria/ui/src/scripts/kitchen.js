/**
 * Mario's Pizzeria - Kitchen Dashboard JavaScript
 *
 * Handles SSE connections, order updates, and kitchen staff interactions
 */

// SSE Connection Management
let eventSource = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

/**
 * Connect to kitchen SSE stream
 */
export function connectKitchenStream() {
    console.log('Connecting to kitchen stream...');
    eventSource = new EventSource('/kitchen/stream');

    eventSource.onopen = function () {
        console.log('Kitchen stream connected');
        updateConnectionStatus(true);
        reconnectAttempts = 0;
    };

    eventSource.onmessage = function (event) {
        const data = JSON.parse(event.data);
        updateKitchenOrders(data.orders);
    };

    eventSource.onerror = function (error) {
        console.error('Kitchen stream error:', error);
        updateConnectionStatus(false);
        eventSource.close();

        // Attempt reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            setTimeout(connectKitchenStream, 3000 * reconnectAttempts);
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
 * Update kitchen orders display
 */
function updateKitchenOrders(orders) {
    // Update count badges for each status
    updateStatusCounts(orders);

    // Check if orders have changed
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
        console.log('Kitchen orders changed, refreshing display...');
        location.reload();
    }
}

/**
 * Update status count badges
 */
function updateStatusCounts(orders) {
    const counts = {
        pending: 0,
        confirmed: 0,
        cooking: 0,
        ready: 0,
    };

    orders.forEach((order) => {
        const status = order.status.toLowerCase();
        if (counts.hasOwnProperty(status)) {
            counts[status]++;
        }
    });

    // Update badge elements
    Object.keys(counts).forEach((status) => {
        const badgeElement = document.getElementById(`${status}Count`);
        if (badgeElement) {
            badgeElement.textContent = counts[status];
        }
    });
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
 * Confirm order (start preparation)
 */
export async function confirmOrder(orderId) {
    try {
        const formData = new FormData();
        formData.append('status', 'confirmed');

        const response = await fetch(`/kitchen/${orderId}/status`, {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            showSuccessModal('Order confirmed!');
        } else {
            showErrorModal(result.error || 'Failed to confirm order');
        }
    } catch (error) {
        console.error('Error confirming order:', error);
        showErrorModal('Failed to confirm order');
    }
}

/**
 * Start cooking order
 */
export async function startCooking(orderId) {
    try {
        const formData = new FormData();
        formData.append('status', 'cooking');

        const response = await fetch(`/kitchen/${orderId}/status`, {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            showSuccessModal('Cooking started!');
        } else {
            showErrorModal(result.error || 'Failed to start cooking');
        }
    } catch (error) {
        console.error('Error starting cooking:', error);
        showErrorModal('Failed to start cooking');
    }
}

/**
 * Mark order as ready
 */
export async function markReady(orderId) {
    try {
        const formData = new FormData();
        formData.append('status', 'ready');

        const response = await fetch(`/kitchen/${orderId}/status`, {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (result.success) {
            showSuccessModal('Order marked as ready!');
        } else {
            showErrorModal(result.error || 'Failed to mark order as ready');
        }
    } catch (error) {
        console.error('Error marking order ready:', error);
        showErrorModal('Failed to mark order as ready');
    }
}

/**
 * Cancel order
 */
export async function cancelOrder(orderId) {
    // Show confirmation modal
    const modal = document.getElementById('confirmCancelModal');
    const confirmBtn = document.getElementById('confirmCancelBtn');

    if (!modal || !confirmBtn) {
        showErrorModal('Modal not found');
        return;
    }

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    // Handle confirmation
    const handleConfirm = async function () {
        confirmBtn.removeEventListener('click', handleConfirm);
        bsModal.hide();

        try {
            const formData = new FormData();
            formData.append('status', 'cancelled');

            const response = await fetch(`/kitchen/${orderId}/status`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();

            if (result.success) {
                showSuccessModal('Order cancelled!');
            } else {
                showErrorModal(result.error || 'Failed to cancel order');
            }
        } catch (error) {
            console.error('Error cancelling order:', error);
            showErrorModal('Failed to cancel order');
        }
    };

    confirmBtn.addEventListener('click', handleConfirm);
}

/**
 * Initialize kitchen dashboard
 */
export function initKitchenDashboard() {
    console.log('Initializing kitchen dashboard...');

    // Connect to SSE
    connectKitchenStream();

    // Cleanup on page unload
    window.addEventListener('beforeunload', function () {
        if (eventSource) {
            eventSource.close();
        }
    });

    // Make functions available globally for onclick handlers
    window.confirmOrder = confirmOrder;
    window.startCooking = startCooking;
    window.markReady = markReady;
    window.cancelOrder = cancelOrder;
}

// Auto-initialize if on kitchen page
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
        if (window.location.pathname.startsWith('/kitchen')) {
            initKitchenDashboard();
        }
    });
} else {
    if (window.location.pathname.startsWith('/kitchen')) {
        initKitchenDashboard();
    }
}
