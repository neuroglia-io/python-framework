/**
 * Common JavaScript functionality for the Exam Record Manager UI
 */

// Import Bootstrap JavaScript components from our custom bootstrap.js file
import bootstrap from './bootstrap.js';

// Format date to a more readable format
export function formatDateTime(isoDateString) {
  if (!isoDateString) return '';
  const date = new Date(isoDateString);
  return date.toLocaleString();
}

// Truncate long text with ellipsis
export function truncateText(text, maxLength = 100) {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// Show toast notification
export function showToast(message, type = 'success') {
  const toastContainer = document.getElementById('toast-container') || createToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-bg-${type} border-0`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');

  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        ${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  toastContainer.appendChild(toast);

  const bsToast = new bootstrap.Toast(toast);
  bsToast.show();

  // Remove the toast after it's hidden
  toast.addEventListener('hidden.bs.toast', () => {
    toast.remove();
  });
}

// Create toast container if it doesn't exist
function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
  document.body.appendChild(container);
  return container;
}

// Handle notification dismissal
export function initializeNotifications() {
  // Add smooth animation when dismissing notifications
  document.querySelectorAll('.notification-item form').forEach(form => {
    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const notificationItem = this.closest('.notification-item');

      // Add dismissing animation
      notificationItem.style.opacity = '0.5';
      notificationItem.style.transform = 'translateX(100%)';

      // Submit form after animation
      setTimeout(() => {
        this.submit();
      }, 300);
    });
  });

  // Mark notifications as read when viewed
  markNotificationsAsRead();
}

// Mark unread notifications as read when the page is viewed
function markNotificationsAsRead() {
  const unreadNotifications = document.querySelectorAll('.notification-item.bg-light');

  // Simple visual feedback - remove the "new" styling after a delay
  setTimeout(() => {
    unreadNotifications.forEach(notification => {
      notification.classList.remove('bg-light');
      const newBadge = notification.querySelector('.badge.bg-primary');
      if (newBadge) {
        newBadge.remove();
      }
    });
  }, 3000); // After 3 seconds viewing
}

// Initialize common functionalities
document.addEventListener('DOMContentLoaded', () => {
  console.log('Common JS loaded');
  initializeNotifications();
});

// Make functions available globally
window.appUtils = {
  formatDateTime,
  truncateText,
  showToast,
  initializeNotifications
};
