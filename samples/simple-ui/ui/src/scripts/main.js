/**
 * Main Application Entry Point
 * Initializes the application and sets up event handlers
 */

// Import Bootstrap
import 'bootstrap/dist/js/bootstrap.bundle';
import { Modal } from 'bootstrap';

// Import modules
import { checkAuth, login, logout } from './modules/auth.js';
import { loadTasks, createTask } from './modules/tasks.js';
import {
  showLoginSection,
  showTasksSection,
  updateUserInfo,
  displayTasks,
  showTasksLoading,
  showTasksError,
  showError
} from './modules/ui.js';
import { validateForm, getFormData } from './modules/utils.js';

// Application state
let currentUser = null;
let authToken = null;

/**
 * Initialize application on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
  console.log('🚀 Simple Task Manager initialized');

  // Check authentication status
  await initializeAuth();

  // Setup event listeners
  setupEventListeners();
});

/**
 * Initialize authentication
 */
async function initializeAuth() {
  const authResult = await checkAuth();

  if (authResult.authenticated) {
    currentUser = authResult.user;
    authToken = authResult.token;

    showTasksSection();
    updateUserInfo(currentUser);
    await loadAndDisplayTasks();
  } else {
    showLoginSection();
  }
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // Login form submission
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }

  // Logout button
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }

  // Create task form submission
  const createTaskForm = document.getElementById('createTaskForm');
  if (createTaskForm) {
    createTaskForm.addEventListener('submit', handleCreateTask);

    // Handle Enter key - submit except in textarea
    createTaskForm.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        createTaskForm.requestSubmit();
      }
    });
  }

  // Add focus handling for create task modal
  const createTaskModal = document.getElementById('createTaskModal');
  if (createTaskModal) {
    createTaskModal.addEventListener('shown.bs.modal', () => {
      // Use requestAnimationFrame to ensure focus happens after Bootstrap's animation
      requestAnimationFrame(() => {
        const titleInput = document.getElementById('taskTitle');
        if (titleInput) {
          titleInput.focus();
        }
      });
    });
  }
}

/**
 * Handle login form submission
 * @param {Event} event - Form submit event
 */
async function handleLogin(event) {
  event.preventDefault();

  const form = event.target;
  const formData = getFormData(form);

  showError('loginError', null);

  const result = await login(formData.username, formData.password);

  if (result.success) {
    currentUser = result.user;
    authToken = result.token;

    showTasksSection();
    updateUserInfo(currentUser);
    await loadAndDisplayTasks();

    // Clear form
    form.reset();
  } else {
    showError('loginError', result.error);
  }
}

/**
 * Handle logout button click
 */
async function handleLogout() {
  await logout();

  currentUser = null;
  authToken = null;

  showLoginSection();

  // Clear login form
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.reset();
  }
}

/**
 * Handle create task form submission
 * @param {Event} event - Form submit event
 */
async function handleCreateTask(event) {
  event.preventDefault();

  const form = event.target;

  if (!validateForm(form)) {
    form.reportValidity();
    return;
  }

  const formData = getFormData(form);
  showError('createTaskError', null);

  try {
    await createTask(formData);

    // Close modal properly
    const modalElement = document.getElementById('createTaskModal');
    let modal = Modal.getInstance(modalElement);

    if (!modal) {
      // If no instance exists, create one
      modal = new Modal(modalElement);
    }

    // Hide the modal
    modal.hide();

    // Remove backdrop and restore body scroll
    document.body.classList.remove('modal-open');
    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) {
      backdrop.remove();
    }

    // Clear form
    form.reset();

    // Reload tasks
    await loadAndDisplayTasks();
  } catch (error) {
    showError('createTaskError', error.message);
  }
}

/**
 * Load and display tasks
 */
export async function loadAndDisplayTasks() {
  showTasksLoading();

  try {
    const tasks = await loadTasks();
    displayTasks(tasks);
  } catch (error) {
    if (error.message === 'Authentication required') {
      // Session expired, show login
      await handleLogout();
    } else {
      showTasksError(error.message);
    }
  }
}
