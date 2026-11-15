/**
 * Authentication & Session Management
 * AI-Enhanced Reimbursements Management System
 * 
 * Handles user login, registration, logout, route protection, and dynamic
 * sidebar user badge rendering based on the active JWT session.
 */

const Auth = {
    /**
     * Checks if a valid auth token is stored in the browser.
     */
    isAuthenticated() {
        return !!API.getToken();
    },

    /**
     * Returns the currently logged-in user profile from storage.
     */
    getCurrentUser() {
        return API.getUser();
    },

    /**
     * Authenticates user against /api/auth/login and saves session token.
     */
    async login(email, password) {
        const res = await API.post("/auth/login", { email, password });
        if (res.success && res.token) {
            API.setToken(res.token);
            API.setUser(res.user);
            return res.user;
        }
        throw new Error(res.error || "Login failed");
    },

    /**
     * Registers a new employee via /api/auth/register and logs them in immediately.
     */
    async register(userData) {
        const res = await API.post("/auth/register", userData);
        if (res.success && res.token) {
            API.setToken(res.token);
            API.setUser(res.user);
            return res.user;
        }
        throw new Error(res.error || "Registration failed");
    },

    /**
     * Ends user session, calls backend logout endpoint, clears storage, and redirects to login.
     */
    async logout() {
        try {
            await API.post("/auth/logout");
        } catch {
            // Ignore network errors during logout
        } finally {
            API.clearAuth();
            window.location.href = "/login.html";
        }
    },

    /**
     * Route guard: validates authentication and role permissions.
     * Redirects unauthorized users to their designated dashboard or login page.
     */
    requireAuth(allowedRoles = []) {
        const token = API.getToken();
        const user = API.getUser();

        if (!token || !user) {
            API.clearAuth();
            window.location.href = `/login.html?redirect=${encodeURIComponent(window.location.pathname)}`;
            return false;
        }

        if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
            if (user.role === "ADMIN") {
                window.location.href = "/finance-dashboard.html";
            } else {
                window.location.href = "/employee-dashboard.html";
            }
            return false;
        }

        this.renderUserBadge(user);
        return true;
    },

    /**
     * Populates user details (initials avatar, name, department) in UI elements.
     */
    renderUserBadge(user) {
        const nameEls = document.querySelectorAll(".user-name");
        const roleEls = document.querySelectorAll(".user-role");
        const avatarEls = document.querySelectorAll(".user-avatar");

        const initials = (user.full_name || "User")
            .split(" ")
            .filter(Boolean)
            .map(n => n[0])
            .join("")
            .substring(0, 2)
            .toUpperCase();

        nameEls.forEach(el => el.textContent = user.full_name || user.email);
        roleEls.forEach(el => {
            el.textContent = user.role === "ADMIN" ? "Finance Admin" : `Employee (${user.department || "Staff"})`;
        });
        avatarEls.forEach(el => el.textContent = initials);
    }
};

window.Auth = Auth;
