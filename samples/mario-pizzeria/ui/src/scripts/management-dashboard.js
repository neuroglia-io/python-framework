/**
 * Mario's Pizzeria - Management Dashboard Script
 *
 * Handles real-time SSE updates for the management dashboard with
 * improved connection stability tracking (stays green unless 3+
 * consecutive events are missed).
 */

class ManagementDashboard {
    constructor() {
        this.statusIndicator = document.getElementById('connectionStatus');
        this.statusText = document.getElementById('statusText');
        this.eventSource = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        // Connection health tracking
        this.lastEventTime = Date.now();
        this.expectedInterval = 5000; // 5 seconds between events
        this.missedEventsThreshold = 3; // Stay green until 3 consecutive misses
        this.healthCheckInterval = null;
        this.consecutiveMisses = 0;
    }

    /**
     * Initialize the dashboard and start SSE connection
     */
    init() {
        this.connectSSE();
        this.startHealthCheck();

        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    /**
     * Start health check interval to monitor connection
     */
    startHealthCheck() {
        // Check every 2 seconds if we're still receiving events
        this.healthCheckInterval = setInterval(() => {
            this.checkConnectionHealth();
        }, 2000);
    }

    /**
     * Check if we're receiving events regularly
     */
    checkConnectionHealth() {
        const timeSinceLastEvent = Date.now() - this.lastEventTime;
        const expectedMaxDelay = this.expectedInterval + 2000; // Allow 2s buffer

        if (timeSinceLastEvent > expectedMaxDelay) {
            this.consecutiveMisses++;

            // Only show disconnected after 3+ consecutive misses
            if (this.consecutiveMisses >= this.missedEventsThreshold) {
                this.updateConnectionStatus('disconnected', 'Connection Lost');
            }
        } else {
            // Receiving events regularly - reset miss counter
            if (this.consecutiveMisses > 0) {
                this.consecutiveMisses = 0;
                this.updateConnectionStatus('connected', 'Live Updates Active');
            }
        }
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(state, message) {
        if (!this.statusIndicator || !this.statusText) return;

        const icon = state === 'connected' ? 'bi-wifi' :
            state === 'connecting' ? 'bi-arrow-clockwise' :
                'bi-wifi-off';

        this.statusIndicator.className = `connection-status ${state}`;
        this.statusText.innerHTML = `<i class="bi ${icon}"></i> ${message}`;
    }

    /**
     * Establish SSE connection
     */
    connectSSE() {
        try {
            this.updateConnectionStatus('connecting', 'Connecting...');
            this.eventSource = new EventSource('/management/stream');

            this.eventSource.onopen = () => {
                console.log('Management SSE connection opened');
                this.updateConnectionStatus('connected', 'Live Updates Active');
                this.reconnectAttempts = 0;
                this.consecutiveMisses = 0;
                this.lastEventTime = Date.now();
            };

            this.eventSource.onmessage = (event) => {
                try {
                    // Reset health tracking
                    this.lastEventTime = Date.now();
                    this.consecutiveMisses = 0;

                    // Ensure we show connected state
                    if (this.statusIndicator.classList.contains('disconnected')) {
                        this.updateConnectionStatus('connected', 'Live Updates Active');
                    }

                    const data = JSON.parse(event.data);
                    this.updateStatistics(data);
                } catch (error) {
                    console.error('Error parsing SSE data:', error);
                }
            };

            this.eventSource.onerror = (error) => {
                console.error('Management SSE error:', error);
                this.eventSource.close();

                this.updateConnectionStatus('disconnected', 'Connection Lost');

                // Attempt to reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
                    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

                    setTimeout(() => {
                        this.connectSSE();
                    }, delay);
                } else {
                    this.updateConnectionStatus('disconnected', 'Connection Failed');
                    console.error('Max reconnection attempts reached');
                }
            };
        } catch (error) {
            console.error('Failed to establish SSE connection:', error);
            this.updateConnectionStatus('disconnected', 'Connection Error');
        }
    }

    /**
     * Update dashboard statistics from SSE data
     */
    updateStatistics(data) {
        if (data.statistics) {
            const stats = data.statistics;

            // Update main metrics
            this.updateElement('totalOrdersToday', stats.total_orders_today);
            this.updateElement('revenueToday', `$${stats.revenue_today.toFixed(2)}`);
            this.updateElement('activeOrders', stats.active_orders);

            // Update kitchen metrics (removed orders_pending - never used in workflow)
            this.updateElement('ordersConfirmed', stats.orders_confirmed);
            this.updateElement('ordersCooking', stats.orders_cooking);
            this.updateElement('ordersReady', stats.orders_ready);

            // Update delivery metrics
            this.updateElement('ordersDelivering', stats.orders_delivering);

            // Update change percentages if elements exist
            this.updateElement('ordersChange', `${stats.orders_change_percent}%`);
            this.updateElement('revenueChange', `${stats.revenue_change_percent}%`);
        }
    }

    /**
     * Update an element's value with animation
     */
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (!element) return;

        const currentValue = element.textContent.trim();
        const newValue = value.toString();

        // Only animate if value actually changed
        if (currentValue !== newValue) {
            // Add scale animation
            element.style.transition = 'transform 0.2s ease';
            element.style.transform = 'scale(1.1)';
            element.textContent = newValue;

            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 200);
        }
    }

    /**
     * Clean up resources
     */
    cleanup() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }

        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new ManagementDashboard();
    dashboard.init();
});
