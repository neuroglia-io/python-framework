/**
 * Main entry point for Mario's Pizzeria UI
 *
 * This file is the single entry point for Parcel bundler.
 * It imports all necessary dependencies and makes them available globally.
 */

// Import Bootstrap JavaScript components from our custom bootstrap.js file
import bootstrap from './bootstrap.js';

// Import utilities
import * as utils from './common.js';

// Import feature modules
import * as kitchen from './kitchen.js';
import * as delivery from './delivery.js';

// Import styles (Parcel will process SCSS and inject into page)
import '../styles/main.scss';

// Make utilities available globally for inline scripts and templates
window.pizzeriaUtils = utils;
window.bootstrap = bootstrap;
window.kitchenModule = kitchen;
window.deliveryModule = delivery;

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    console.log('🍕 Mario\'s Pizzeria UI loaded');

    // Initialize any global UI components here
    initializeToastContainer();
});

/**
 * Create toast container if it doesn't exist
 */
function initializeToastContainer() {
    if (!document.getElementById('toast-container')) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.setAttribute('style', 'z-index: 11');
        document.body.appendChild(container);
    }
}

// Export for potential module usage
export { bootstrap, utils };
