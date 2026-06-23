/**
 * Utility Functions Module
 * Common helper functions used across the application
 */

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string}
 */
export function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

/**
 * Debounce function execution
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function}
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format date to locale string
 * @param {string|Date} date - Date to format
 * @returns {string}
 */
export function formatDate(date) {
    try {
        return new Date(date).toLocaleDateString();
    } catch (error) {
        return 'Invalid date';
    }
}

/**
 * Format date to locale date and time string
 * @param {string|Date} date - Date to format
 * @returns {string}
 */
export function formatDateTime(date) {
    try {
        return new Date(date).toLocaleString();
    } catch (error) {
        return 'Invalid date';
    }
}

/**
 * Validate form data
 * @param {HTMLFormElement} form - Form element to validate
 * @returns {boolean}
 */
export function validateForm(form) {
    if (!form) return false;
    return form.checkValidity();
}

/**
 * Get form data as object
 * @param {HTMLFormElement} form - Form element
 * @returns {Object}
 */
export function getFormData(form) {
    const formData = new FormData(form);
    const data = {};
    for (const [key, value] of formData.entries()) {
        data[key] = value;
    }
    return data;
}
