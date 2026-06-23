/**
 * Tasks Module
 * Handles task management operations (CRUD)
 */

import { getAuthToken } from './auth.js';

/**
 * Load all tasks for the current user
 * @returns {Promise<Array>}
 */
export async function loadTasks() {
    try {
        const token = getAuthToken();
        console.log('📋 Loading tasks with token:', token ? `Token present (${token.substring(0, 20)}...)` : 'NO TOKEN!');
        if (!token) {
            throw new Error('No authentication token available');
        }

        const response = await fetch('/api/tasks/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            console.error('📋 Tasks load failed:', response.status, response.statusText);
            if (response.status === 401) {
                throw new Error('Authentication required');
            }
            throw new Error('Failed to load tasks');
        }

        const tasks = await response.json();
        return tasks || [];
    } catch (error) {
        console.error('Failed to load tasks:', error);
        throw error;
    }
}

/**
 * Create a new task
 * @param {Object} taskData - Task data
 * @param {string} taskData.title - Task title
 * @param {string} taskData.description - Task description
 * @param {string} taskData.status - Task status
 * @returns {Promise<Object>}
 */
export async function createTask(taskData) {
    try {
        const token = getAuthToken();
        if (!token) {
            throw new Error('No authentication token available');
        }

        const response = await fetch('/api/tasks/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create task');
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to create task:', error);
        throw error;
    }
}

/**
 * Get a single task by ID
 * @param {string} taskId - Task ID
 * @returns {Promise<Object>}
 */
export async function getTask(taskId) {
    try {
        const token = getAuthToken();
        if (!token) {
            throw new Error('No authentication token available');
        }

        const response = await fetch(`/api/tasks/${taskId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load task');
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to load task:', error);
        throw error;
    }
}

/**
 * Update an existing task
 * @param {string} taskId - Task ID
 * @param {Object} taskData - Updated task data
 * @returns {Promise<Object>}
 */
export async function updateTask(taskId, taskData) {
    try {
        const token = getAuthToken();
        if (!token) {
            throw new Error('No authentication token available');
        }

        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(taskData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update task');
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to update task:', error);
        throw error;
    }
}

/**
 * Delete a task
 * @param {string} taskId - Task ID
 * @returns {Promise<void>}
 */
export async function deleteTask(taskId) {
    try {
        const token = getAuthToken();
        if (!token) {
            throw new Error('No authentication token available');
        }

        const response = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to delete task');
        }
    } catch (error) {
        console.error('Failed to delete task:', error);
        throw error;
    }
}
