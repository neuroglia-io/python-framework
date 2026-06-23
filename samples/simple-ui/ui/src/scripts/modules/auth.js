/**
 * Authentication Module
 * Handles user authentication, login, logout, and session management
 */

/**
 * Check current authentication status
 * @returns {Promise<{authenticated: boolean, user: object|null, token: string|null}>}
 */
export async function checkAuth() {
    try {
        // Get token from localStorage
        const token = localStorage.getItem('authToken');

        if (!token) {
            return {
                authenticated: false,
                user: null,
                token: null
            };
        }

        // Send JWT token in Authorization header
        const response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.authenticated) {
                return {
                    authenticated: true,
                    user: data.user,
                    token: token
                };
            }
        }

        // If token is invalid, clear it
        localStorage.removeItem('authToken');
    } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('authToken');
    }

    return {
        authenticated: false,
        user: null,
        token: null
    };
}

/**
 * Login user with credentials
 * @param {string} username - User's username
 * @param {string} password - User's password
 * @returns {Promise<{success: boolean, user: object|null, token: string|null, error: string|null}>}
 */
export async function login(username, password) {
    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/auth/login', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Store token for API calls
            console.log('🔐 Login successful, storing token:', data.token ? 'Token present' : 'NO TOKEN!');
            localStorage.setItem('authToken', data.token);
            console.log('🔐 Token stored in localStorage:', localStorage.getItem('authToken') ? 'Success' : 'FAILED!');
            return {
                success: true,
                user: data.user,
                token: data.token,
                error: null
            };
        } else {
            return {
                success: false,
                user: null,
                token: null,
                error: data.error || 'Login failed. Please try again.'
            };
        }
    } catch (error) {
        console.error('Login error:', error);
        return {
            success: false,
            user: null,
            token: null,
            error: 'Network error. Please try again.'
        };
    }
}

/**
 * Logout current user
 * @returns {Promise<void>}
 */
export async function logout() {
    try {
        await fetch('/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }

    // Clear stored token
    localStorage.removeItem('authToken');
}

/**
 * Get stored authentication token
 * @returns {string|null}
 */
export function getAuthToken() {
    const token = localStorage.getItem('authToken');
    console.log('🔑 Getting auth token from localStorage:', token ? `Token found (${token.substring(0, 20)}...)` : 'NO TOKEN!');
    return token;
}
