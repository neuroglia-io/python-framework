/**
 * Management Analytics Dashboard
 * Handles Chart.js visualization and data fetching for analytics
 */

import Chart from 'chart.js/auto';

class ManagementAnalytics {
    constructor() {
        this.charts = {};
        this.currentDateRange = 'month'; // Default: last 30 days
        this.currentPeriod = 'day'; // Default: daily grouping
        this.customStartDate = null;
        this.customEndDate = null;
        this.isLoading = false;
    }

    /**
     * Initialize analytics dashboard
     */
    async init() {
        console.log('Initializing Management Analytics Dashboard...');

        try {
            this.setupEventListeners();
            this.setupCharts();
            await this.loadData();
            console.log('Analytics dashboard initialized successfully');
        } catch (error) {
            console.error('Failed to initialize analytics dashboard:', error);
            this.showError('Failed to load analytics dashboard');
        }
    }

    /**
     * Setup event listeners for controls
     */
    setupEventListeners() {
        // Date range selector
        const dateRangeSelect = document.getElementById('dateRange');
        if (dateRangeSelect) {
            dateRangeSelect.addEventListener('change', (e) => {
                this.currentDateRange = e.target.value;

                // Show/hide custom date inputs
                const customDateInputs = document.getElementById('customDateInputs');
                if (customDateInputs) {
                    customDateInputs.style.display =
                        this.currentDateRange === 'custom' ? 'block' : 'none';
                }

                if (this.currentDateRange !== 'custom') {
                    this.loadData();
                }
            });
        }

        // Period selector
        const periodSelect = document.getElementById('periodType');
        if (periodSelect) {
            periodSelect.addEventListener('change', (e) => {
                this.currentPeriod = e.target.value;
                this.loadData();
            });
        }

        // Apply custom date range button
        const applyFiltersBtn = document.getElementById('applyFilters');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                const startDate = document.getElementById('startDate')?.value;
                const endDate = document.getElementById('endDate')?.value;

                if (startDate && endDate) {
                    this.customStartDate = startDate;
                    this.customEndDate = endDate;
                    this.loadData();
                } else {
                    alert('Please select both start and end dates');
                }
            });
        }

        // Chart type toggle buttons (if present)
        document.querySelectorAll('[data-chart-type]').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                const chartType = e.target.dataset.chartType;
                const targetChart = e.target.dataset.targetChart;
                this.changeChartType(targetChart, chartType);
            });
        });
    }

    /**
     * Setup Chart.js instances
     */
    setupCharts() {
        // Revenue Timeseries Chart
        const revenueCtx = document.getElementById('revenueChart');
        if (revenueCtx) {
            this.charts.revenue = new Chart(revenueCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Revenue ($)',
                            data: [],
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                        },
                        title: {
                            display: false,
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: (context) => {
                                    return `Revenue: $${context.parsed.y.toFixed(2)}`;
                                },
                            },
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: (value) => `$${value}`,
                            },
                        },
                    },
                },
            });
        }

        // Orders Timeseries Chart
        const ordersCtx = document.getElementById('ordersChart');
        if (ordersCtx) {
            this.charts.orders = new Chart(ordersCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Total Orders',
                            data: [],
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4,
                        },
                        {
                            label: 'Delivered',
                            data: [],
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4,
                        },
                        {
                            label: 'Cancelled',
                            data: [],
                            borderColor: '#dc3545',
                            backgroundColor: 'rgba(220, 53, 69, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1,
                            },
                        },
                    },
                },
            });
        }

        // Pizza Popularity Chart
        const pizzaCtx = document.getElementById('pizzaChart');
        if (pizzaCtx) {
            this.charts.pizza = new Chart(pizzaCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Revenue ($)',
                            data: [],
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.8)',
                                'rgba(54, 162, 235, 0.8)',
                                'rgba(255, 206, 86, 0.8)',
                                'rgba(75, 192, 192, 0.8)',
                                'rgba(153, 102, 255, 0.8)',
                                'rgba(255, 159, 64, 0.8)',
                                'rgba(199, 199, 199, 0.8)',
                                'rgba(83, 102, 255, 0.8)',
                                'rgba(255, 99, 255, 0.8)',
                                'rgba(99, 255, 132, 0.8)',
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(199, 199, 199, 1)',
                                'rgba(83, 102, 255, 1)',
                                'rgba(255, 99, 255, 1)',
                                'rgba(99, 255, 132, 1)',
                            ],
                            borderWidth: 1,
                        },
                    ],
                },
                options: {
                    indexAxis: 'y', // Horizontal bar chart
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false,
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    return `Revenue: $${context.parsed.x.toFixed(2)}`;
                                },
                            },
                        },
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: {
                                callback: (value) => `$${value}`,
                            },
                        },
                    },
                },
            });
        }
    }

    /**
     * Load analytics data from API
     */
    async loadData() {
        if (this.isLoading) {
            console.log('Data load already in progress...');
            return;
        }

        this.isLoading = true;
        this.showLoadingState();

        try {
            // Build query parameters
            const params = new URLSearchParams();

            // Date range
            if (this.currentDateRange === 'custom') {
                if (this.customStartDate && this.customEndDate) {
                    params.append('start_date', this.customStartDate);
                    params.append('end_date', this.customEndDate);
                }
            } else {
                // Calculate date range based on selection
                const { startDate, endDate } = this.getDateRange(this.currentDateRange);
                params.append('start_date', startDate);
                params.append('end_date', endDate);
            }

            // Period type
            params.append('period', this.currentPeriod);

            // Fetch data
            const response = await fetch(`/management/analytics/data?${params.toString()}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            // Update charts with new data
            this.updateCharts(data);

            // Update tables
            this.updateTables(data);

            // Hide loading state
            this.hideLoadingState();
        } catch (error) {
            console.error('Failed to load analytics data:', error);
            this.showError(`Failed to load data: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Get date range based on preset selection
     */
    getDateRange(rangeType) {
        const endDate = new Date();
        const startDate = new Date();

        switch (rangeType) {
            case 'today':
                startDate.setHours(0, 0, 0, 0);
                break;
            case 'week':
                startDate.setDate(startDate.getDate() - 7);
                break;
            case 'month':
                startDate.setDate(startDate.getDate() - 30);
                break;
            case 'quarter':
                startDate.setDate(startDate.getDate() - 90);
                break;
            case 'year':
                startDate.setFullYear(startDate.getFullYear() - 1);
                break;
            default:
                startDate.setDate(startDate.getDate() - 30);
        }

        return {
            startDate: startDate.toISOString(),
            endDate: endDate.toISOString(),
        };
    }

    /**
     * Update charts with new data
     */
    updateCharts(data) {
        // Update revenue chart
        if (this.charts.revenue && data.timeseries) {
            const labels = data.timeseries.map((d) => d.period);
            const revenueData = data.timeseries.map((d) => d.total_revenue);

            this.charts.revenue.data.labels = labels;
            this.charts.revenue.data.datasets[0].data = revenueData;
            this.charts.revenue.update();
        }

        // Update orders chart
        if (this.charts.orders && data.timeseries) {
            const labels = data.timeseries.map((d) => d.period);
            const totalOrders = data.timeseries.map((d) => d.total_orders);
            const delivered = data.timeseries.map((d) => d.orders_delivered);
            const cancelled = data.timeseries.map((d) => d.orders_cancelled || 0);

            this.charts.orders.data.labels = labels;
            this.charts.orders.data.datasets[0].data = totalOrders;
            this.charts.orders.data.datasets[1].data = delivered;
            this.charts.orders.data.datasets[2].data = cancelled;
            this.charts.orders.update();
        }

        // Update pizza chart
        if (this.charts.pizza && data.pizza_analytics) {
            const labels = data.pizza_analytics.map((p) => p.pizza_name);
            const revenueData = data.pizza_analytics.map((p) => p.total_revenue);

            this.charts.pizza.data.labels = labels;
            this.charts.pizza.data.datasets[0].data = revenueData;
            this.charts.pizza.update();
        }
    }

    /**
     * Update data tables
     */
    updateTables(data) {
        // Update summary stats
        if (data.timeseries && data.timeseries.length > 0) {
            const totalOrders = data.timeseries.reduce((sum, d) => sum + d.total_orders, 0);
            const totalRevenue = data.timeseries.reduce((sum, d) => sum + d.total_revenue, 0);
            const totalDelivered = data.timeseries.reduce((sum, d) => sum + d.orders_delivered, 0);
            const avgOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0;
            const deliveryRate = totalOrders > 0 ? (totalDelivered / totalOrders * 100) : 0;

            document.getElementById('summaryTotalOrders').textContent = totalOrders;
            document.getElementById('summaryTotalRevenue').textContent = `$${totalRevenue.toFixed(2)}`;
            document.getElementById('summaryAvgOrderValue').textContent = `$${avgOrderValue.toFixed(2)}`;
            document.getElementById('summaryDelivered').textContent = totalDelivered;
            document.getElementById('summaryDeliveryRate').textContent = `${deliveryRate.toFixed(1)}% delivered`;
        } else {
            // No data in selected range - reset to zero
            document.getElementById('summaryTotalOrders').textContent = '0';
            document.getElementById('summaryTotalRevenue').textContent = '$0.00';
            document.getElementById('summaryAvgOrderValue').textContent = '$0.00';
            document.getElementById('summaryDelivered').textContent = '0';
            document.getElementById('summaryDeliveryRate').textContent = 'No data';
        }

        // Update compact pizza table
        const pizzaTableBody = document.querySelector('#pizzaTable tbody');
        if (pizzaTableBody && data.pizza_analytics) {
            pizzaTableBody.innerHTML = '';

            // Show top 5 in compact view
            const topPizzas = data.pizza_analytics.slice(0, 5);

            if (topPizzas.length === 0) {
                pizzaTableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="text-center text-muted py-4">
                            No data available
                        </td>
                    </tr>
                `;
            } else {
                topPizzas.forEach((pizza, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td class="pizza-name">${pizza.pizza_name}</td>
                        <td class="text-right">${pizza.total_orders}</td>
                        <td class="text-right revenue">$${pizza.total_revenue.toFixed(2)}</td>
                    `;
                    pizzaTableBody.appendChild(row);
                });
            }
        }

        // Update detailed pizza table
        const pizzaTableDetailedBody = document.querySelector('#pizzaTableDetailed tbody');
        if (pizzaTableDetailedBody && data.pizza_analytics) {
            pizzaTableDetailedBody.innerHTML = '';

            if (data.pizza_analytics.length === 0) {
                pizzaTableDetailedBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-muted py-4">
                            No pizza data available for this period
                        </td>
                    </tr>
                `;
            } else {
                data.pizza_analytics.forEach((pizza, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td class="pizza-name">${pizza.pizza_name}</td>
                        <td class="text-right">${pizza.total_orders}</td>
                        <td class="text-right revenue">$${pizza.total_revenue.toFixed(2)}</td>
                        <td class="text-right">$${pizza.average_price.toFixed(2)}</td>
                        <td class="percentage-cell">
                            <span class="percentage-value">${pizza.percentage_of_total.toFixed(1)}%</span>
                            <div class="percentage-bar-container">
                                <div class="percentage-bar" style="width: ${pizza.percentage_of_total}%"></div>
                            </div>
                        </td>
                    `;
                    pizzaTableDetailedBody.appendChild(row);
                });
            }
        }
    }

    /**
     * Change chart type dynamically
     */
    changeChartType(chartName, newType) {
        const chart = this.charts[chartName];
        if (!chart) return;

        chart.config.type = newType;
        chart.update();
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        document.querySelectorAll('.chart-container').forEach((container) => {
            const canvas = container.querySelector('canvas');
            if (canvas) {
                canvas.style.opacity = '0.5';
            }

            // Add loading spinner if not present
            if (!container.querySelector('.chart-loading')) {
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'chart-loading';
                loadingDiv.innerHTML = '<div class="spinner"></div>';
                container.appendChild(loadingDiv);
            }
        });

        // Disable controls
        const applyBtn = document.getElementById('applyFilters');
        if (applyBtn) {
            applyBtn.disabled = true;
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        document.querySelectorAll('.chart-loading').forEach((el) => el.remove());
        document.querySelectorAll('.chart-container canvas').forEach((canvas) => {
            canvas.style.opacity = '1';
        });

        // Enable controls
        const applyBtn = document.getElementById('applyFilters');
        if (applyBtn) {
            applyBtn.disabled = false;
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.hideLoadingState();

        // Create error alert if not present
        let errorAlert = document.getElementById('analyticsError');
        if (!errorAlert) {
            errorAlert = document.createElement('div');
            errorAlert.id = 'analyticsError';
            errorAlert.className = 'alert alert-danger alert-dismissible fade show';
            errorAlert.style.position = 'fixed';
            errorAlert.style.top = '20px';
            errorAlert.style.right = '20px';
            errorAlert.style.zIndex = '9999';
            document.body.appendChild(errorAlert);
        }

        errorAlert.innerHTML = `
            <strong>Error:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            errorAlert.remove();
        }, 5000);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const analytics = new ManagementAnalytics();
    analytics.init();
});

export default ManagementAnalytics;
