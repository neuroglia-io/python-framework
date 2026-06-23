/**
 * UI Module
 * Handles UI state management and DOM manipulations
 */

import { escapeHtml } from './utils.js';

// Store current user for role-based UI decisions
let currentUser = null;

/**
 * Set the current user
 * @param {Object} user - User object
 */
export function setCurrentUser(user) {
    currentUser = user;
}

/**
 * Get the current user
 * @returns {Object|null} - Current user object or null
 */
export function getCurrentUser() {
    return currentUser;
}

/**
 * Show the login section and hide tasks
 */
export function showLoginSection() {
    const loginSection = document.getElementById('loginSection');
    const tasksSection = document.getElementById('tasksSection');
    const userInfo = document.getElementById('userInfo');

    if (loginSection) loginSection.classList.remove('d-none');
    if (tasksSection) tasksSection.classList.add('d-none');
    if (userInfo) userInfo.style.display = 'none';
}

/**
 * Show the tasks section and hide login
 */
export function showTasksSection() {
    const loginSection = document.getElementById('loginSection');
    const tasksSection = document.getElementById('tasksSection');
    const userInfo = document.getElementById('userInfo');
    const createTaskBtn = document.getElementById('createTaskBtn');

    if (loginSection) loginSection.classList.add('d-none');
    if (tasksSection) tasksSection.classList.remove('d-none');
    if (userInfo) userInfo.style.display = 'flex';
    if (createTaskBtn) createTaskBtn.style.display = 'block';
}

/**
 * Update user info display in the navbar
 * @param {Object} user - User object
 * @param {string} user.username - Username
 * @param {string} user.role - User role
 */
export function updateUserInfo(user) {
    if (!user) return;

    // Store current user for later use
    setCurrentUser(user);

    const usernameEl = document.getElementById('username');
    const userRoleEl = document.getElementById('userRole');

    if (usernameEl) usernameEl.textContent = user.username || '';

    // Display the role (use first role if multiple)
    const displayRole = Array.isArray(user.roles) && user.roles.length > 0
        ? user.roles[user.roles.length - 1]  // Use last role (most privileged typically)
        : (user.role || 'user');

    if (userRoleEl) userRoleEl.textContent = displayRole;

    console.log('👤 User info:', { username: user.username, role: user.role, roles: user.roles, displayRole });

    // Show/hide create task button based on roles
    updateRoleBasedUI(user);
}

/**
 * Update UI elements based on user role
 * @param {Object} user - User object with role/roles
 */
function updateRoleBasedUI(user) {
    const createTaskBtn = document.getElementById('createTaskBtn');

    // All authenticated users can create tasks
    console.log('🔐 Role check:', { role: user.role, roles: user.roles, authenticated: true });

    // Show create task button for all authenticated users
    if (createTaskBtn) {
        console.log('✅ Showing create task button for authenticated user');
        createTaskBtn.style.display = '';
        createTaskBtn.disabled = false;
    } else {
        console.warn('⚠️ Create task button element not found');
    }
}

/**
 * Display tasks in the grid
 * @param {Array} tasks - Array of task objects
 */
export function displayTasks(tasks) {
    const grid = document.getElementById('tasksGrid');
    const taskDescription = document.getElementById('taskDescription');
    if (!grid) return;

    if (!tasks || tasks.length === 0) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="empty-state text-center py-5">
                    <i class="bi bi-inbox" style="font-size: 4rem; color: #6c757d;"></i>
                    <h3 class="mt-3">No Tasks Found</h3>
                    <p class="text-muted">There are no tasks to display.</p>
                </div>
            </div>
        `;
        if (taskDescription) {
            taskDescription.textContent = 'No tasks available';
        }
        return;
    }

    // Update task description with count
    if (taskDescription) {
        const taskCount = tasks.length;
        taskDescription.textContent = `${taskCount} task${taskCount !== 1 ? 's' : ''} found`;
    }

    grid.innerHTML = tasks.map(task => `
        <div class="col">
            <div class="card task-card priority-${task.priority || 'medium'} h-100" data-task-id="${task.id}" style="cursor: pointer;">
                <div class="card-body">
                    <h5 class="card-title">${escapeHtml(task.title)}</h5>
                    <p class="card-text">${escapeHtml(task.description || 'No description')}</p>
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <span class="badge ${getStatusBadgeClass(task.status)}">
                            ${escapeHtml(task.status)}
                        </span>
                        ${task.assigned_to ? `<small class="text-muted">@${escapeHtml(task.assigned_to)}</small>` : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    // Add click handlers to task cards
    grid.querySelectorAll('.task-card').forEach(card => {
        card.addEventListener('click', () => {
            const taskId = card.getAttribute('data-task-id');
            const task = tasks.find(t => t.id === taskId);
            if (task) {
                showTaskDetailsModal(task);
            }
        });
    });
}

/**
 * Show loading spinner in tasks grid
 */
export function showTasksLoading() {
    const grid = document.getElementById('tasksGrid');
    const taskDescription = document.getElementById('taskDescription');
    if (!grid) return;

    // Update description to show loading state
    if (taskDescription) {
        taskDescription.textContent = 'Loading...';
    }

    grid.innerHTML = `
        <div class="col-12">
            <div class="spinner-container text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Show error message in tasks grid
 * @param {string} message - Error message
 */
export function showTasksError(message) {
    const grid = document.getElementById('tasksGrid');
    if (!grid) return;

    grid.innerHTML = `
        <div class="col-12">
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i> ${escapeHtml(message)}
            </div>
        </div>
    `;
}

/**
 * Show/hide error message in an element
 * @param {string} elementId - Element ID
 * @param {string|null} message - Error message (null to hide)
 */
export function showError(elementId, message) {
    const errorDiv = document.getElementById(elementId);
    if (!errorDiv) return;

    if (message) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    } else {
        errorDiv.textContent = '';
        errorDiv.classList.add('d-none');
    }
}

/**
 * Show task details in modal with editable fields
 * @param {Object} task - Task object
 */
export function showTaskDetailsModal(task) {
    // Import Modal dynamically to avoid circular dependency
    import('bootstrap').then(({ Modal }) => {
        // Get current user to determine permissions
        const user = getCurrentUser();
        const isAdminOrManager = user && (user.role === 'admin' || user.role === 'manager' ||
            (Array.isArray(user.roles) && (user.roles.includes('admin') || user.roles.includes('manager'))));

        // Populate modal body with editable task details
        const modalBody = document.getElementById('taskDetailsBody');
        modalBody.innerHTML = `
            <form id="editTaskForm">
                <input type="hidden" id="editTaskId" value="${escapeHtml(task.id)}">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Task ID</label>
                        <p class="form-control-plaintext text-muted">${escapeHtml(task.id)}</p>
                    </div>
                    <div class="col-md-6">
                        <label for="editTaskStatus" class="form-label fw-bold">Status</label>
                        <select class="form-select" id="editTaskStatus" name="status" tabindex="2">
                            <option value="pending" ${task.status === 'pending' ? 'selected' : ''}>Pending</option>
                            <option value="in_progress" ${task.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                            <option value="completed" ${task.status === 'completed' ? 'selected' : ''}>Completed</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <label for="editTaskTitle" class="form-label fw-bold">Title</label>
                        <input type="text" class="form-control" id="editTaskTitle" name="title"
                               value="${escapeHtml(task.title)}" required maxlength="100" tabindex="1">
                    </div>
                    <div class="col-12">
                        <label for="editTaskDescription" class="form-label fw-bold">Description</label>
                        <textarea class="form-control" id="editTaskDescription" name="description"
                                  rows="3" tabindex="3">${escapeHtml(task.description || '')}</textarea>
                    </div>
                    <div class="col-md-6">
                        <label for="editTaskAssignedTo" class="form-label fw-bold">Assigned To</label>
                        ${isAdminOrManager ? `
                            <input type="text" class="form-control" id="editTaskAssignedTo" name="assigned_to"
                                   value="${escapeHtml(task.assigned_to || '')}"
                                   placeholder="Enter username"
                                   tabindex="4">
                            <small class="text-muted">Admins/Managers can reassign tasks</small>
                        ` : `
                            <p class="form-control-plaintext">${escapeHtml(task.assigned_to || 'Unassigned')}</p>
                        `}
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Priority</label>
                        <p class="form-control-plaintext">${escapeHtml(task.priority || 'medium')}</p>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Created By</label>
                        <p class="form-control-plaintext">${escapeHtml(task.created_by || 'Unknown')}</p>
                    </div>
                </div>
                <div id="editTaskError" class="alert alert-danger d-none mt-3" role="alert"></div>
            </form>
        `;

        // Update modal footer to include save and delete buttons
        const modalFooter = document.querySelector('#taskDetailsModal .modal-footer');
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-danger" id="deleteTaskBtn" tabindex="6">
                <i class="bi bi-trash"></i> Delete Task
            </button>
            <div class="ms-auto">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" tabindex="7">
                    <i class="bi bi-x-circle"></i> Close
                </button>
                <button type="submit" form="editTaskForm" class="btn btn-primary" tabindex="5">
                    <i class="bi bi-check-circle"></i> Save Changes
                </button>
            </div>
        `;

        // Show the modal
        const modalElement = document.getElementById('taskDetailsModal');
        let modal = Modal.getInstance(modalElement);
        if (!modal) {
            modal = new Modal(modalElement);
        }
        modal.show();

        // Focus on title field after modal is fully shown
        modalElement.addEventListener('shown.bs.modal', function focusTitle() {
            // Use requestAnimationFrame to ensure focus happens after Bootstrap's animation
            requestAnimationFrame(() => {
                const titleInput = document.getElementById('editTaskTitle');
                if (titleInput) {
                    titleInput.focus();
                    titleInput.select();
                }
            });
            // Remove listener after first execution
            modalElement.removeEventListener('shown.bs.modal', focusTitle);
        });

        // Add form submit handler (needs to be done after modal is shown)
        setTimeout(() => {
            const form = document.getElementById('editTaskForm');
            if (form) {
                // Handle Enter key - submit except in textarea
                form.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
                        e.preventDefault();
                        form.requestSubmit();
                    }
                });

                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    await handleEditTask(task.id, modal);
                });
            }

            // Add delete button handler
            const deleteBtn = document.getElementById('deleteTaskBtn');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', async () => {
                    await handleDeleteTask(task.id, modal);
                });
            }
        }, 100);
    });
}

/**
 * Handle edit task form submission
 * @param {string} taskId - Task ID
 * @param {Object} modal - Bootstrap modal instance
 */
async function handleEditTask(taskId, modal) {
    const form = document.getElementById('editTaskForm');
    const errorDiv = document.getElementById('editTaskError');

    // Clear previous errors
    errorDiv.classList.add('d-none');

    try {
        // Import necessary functions dynamically
        const { updateTask } = await import('./tasks.js');
        const { getFormData } = await import('./utils.js');

        const formData = getFormData(form);

        // Update task
        await updateTask(taskId, formData);

        // Close modal properly
        modal.hide();
        document.body.classList.remove('modal-open');
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }

        // Reload tasks to show updated data
        const { loadTasks } = await import('./tasks.js');
        const tasks = await loadTasks();
        displayTasks(tasks);
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('d-none');
    }
}

/**
 * Handle delete task
 * @param {string} taskId - Task ID
 * @param {Object} taskDetailsModal - Bootstrap modal instance for task details
 */
async function handleDeleteTask(taskId, taskDetailsModal) {
    // Import Modal dynamically
    const { Modal } = await import('bootstrap');

    // Get the confirmation modal
    const confirmModalElement = document.getElementById('confirmDeleteModal');
    let confirmModal = Modal.getInstance(confirmModalElement);
    if (!confirmModal) {
        confirmModal = new Modal(confirmModalElement);
    }

    // Show confirmation modal
    confirmModal.show();

    // Handle confirm button click
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const errorDiv = document.getElementById('editTaskError');

    // Remove any existing listeners to prevent duplicates
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.addEventListener('click', async () => {
        // Clear previous errors
        errorDiv.classList.add('d-none');

        try {
            // Import deleteTask function dynamically
            const { deleteTask } = await import('./tasks.js');

            // Delete task
            await deleteTask(taskId);

            // Close confirmation modal
            confirmModal.hide();

            // Close task details modal
            taskDetailsModal.hide();

            // Clean up modal artifacts
            document.body.classList.remove('modal-open');
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Reload tasks to show updated list
            const { loadTasks } = await import('./tasks.js');
            const tasks = await loadTasks();
            displayTasks(tasks);
        } catch (error) {
            // Close confirmation modal
            confirmModal.hide();

            // Show error in task details modal
            errorDiv.textContent = error.message;
            errorDiv.classList.remove('d-none');

            // Clean up any leftover backdrops
            const backdrops = document.querySelectorAll('.modal-backdrop');
            if (backdrops.length > 1) {
                backdrops[backdrops.length - 1].remove();
            }
        }
    });
}

/**
 * Get Bootstrap badge class for task status
 * @param {string} status - Task status
 * @returns {string}
 */
function getStatusBadgeClass(status) {
    const classes = {
        'pending': 'bg-secondary',
        'in_progress': 'bg-primary',
        'completed': 'bg-success',
        'cancelled': 'bg-danger'
    };
    return classes[status] || 'bg-secondary';
}
