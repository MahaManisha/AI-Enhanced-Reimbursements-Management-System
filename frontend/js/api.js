/**
 * API Client & Network Service
 * AI-Enhanced Reimbursements Management System
 * 
 * Centralizes all REST API communication, attaches JWT Bearer tokens to requests,
 * parses JSON responses, handles session expiration, and supports binary Blob
 * streaming for secure receipt viewing.
 */

/**
 * API Base URL resolution:
 * 1. window.__API_BASE__ if explicitly defined
 * 2. window.__BACKEND_URL__ / window.BACKEND_API_URL + "/api"
 * 3. Default to relative "/api" (works when served by Flask backend or via reverse proxy)
 */
const API_BASE = (function() {
    if (window.__API_BASE__) return window.__API_BASE__;
    if (window.__BACKEND_URL__) return window.__BACKEND_URL__.replace(/\/+$/, "") + "/api";
    if (window.BACKEND_API_URL) return window.BACKEND_API_URL.replace(/\/+$/, "") + "/api";
    // When served from a decoupled Render Static Site (e.g. ai-reimbursements-frontend.onrender.com)
    if (typeof window !== "undefined" && window.location.hostname.includes("onrender.com") && !window.location.hostname.includes("backend")) {
        return "https://ai-reimbursements-backend.onrender.com/api";
    }
    return "/api";
})();

const API = {
    /**
     * Retrieves stored JWT authentication token from LocalStorage.
     */
    getToken() {
        return localStorage.getItem("reimb_auth_token");
    },

    /**
     * Stores JWT token in LocalStorage.
     */
    setToken(token) {
        localStorage.setItem("reimb_auth_token", token);
    },

    /**
     * Clears authentication token and user profile upon logout or session expiration.
     */
    clearAuth() {
        localStorage.removeItem("reimb_auth_token");
        localStorage.removeItem("reimb_user_profile");
    },

    /**
     * Retrieves cached user profile object.
     */
    getUser() {
        const raw = localStorage.getItem("reimb_user_profile");
        try {
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    },

    /**
     * Caches user profile object in LocalStorage.
     */
    setUser(user) {
        localStorage.setItem("reimb_user_profile", JSON.stringify(user));
    },

    /**
     * Core fetch wrapper for JSON REST endpoints.
     */
    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = options.headers || {};

        const token = this.getToken();
        if (token && !headers["Authorization"]) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
            headers["Content-Type"] = "application/json";
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // Automatically handle expired tokens
            if (response.status === 401) {
                this.clearAuth();
                const path = window.location.pathname;
                if (!path.includes("login.html") && !path.includes("register.html") && path !== "/") {
                    window.location.href = "/login.html?expired=true";
                }
            }

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(data.error || `Request failed with status ${response.status}`);
            }

            return data;
        } catch (err) {
            console.error(`API Error on [${options.method || "GET"} ${endpoint}]:`, err);
            throw err;
        }
    },

    /**
     * Performs a GET request with optional query parameters.
     */
    get(endpoint, params = {}) {
        const query = new URLSearchParams(params).toString();
        const fullEndpoint = query ? `${endpoint}?${query}` : endpoint;
        return this.request(fullEndpoint, { method: "GET" });
    },

    /**
     * Performs a POST request with JSON body or FormData.
     */
    post(endpoint, body = {}) {
        return this.request(endpoint, {
            method: "POST",
            body: body instanceof FormData ? body : JSON.stringify(body)
        });
    },

    /**
     * Performs a PUT request with JSON payload.
     */
    put(endpoint, body = {}) {
        return this.request(endpoint, {
            method: "PUT",
            body: JSON.stringify(body)
        });
    },

    /**
     * Uploads a multipart/form-data file to a designated endpoint.
     */
    upload(endpoint, file) {
        const formData = new FormData();
        formData.append("file", file);
        return this.request(endpoint, {
            method: "POST",
            body: formData
        });
    },

    /**
     * Fetches binary file content (PDF or images) with JWT authorization
     * and returns a Blob along with Content-Type metadata for inline viewing.
     */
    async getBlob(endpoint) {
        const url = `${API_BASE}${endpoint}`;
        const headers = {};
        const token = this.getToken();
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            method: "GET",
            headers
        });

        if (response.status === 401) {
            this.clearAuth();
            if (!window.location.pathname.includes("login.html")) {
                window.location.href = "/login.html?expired=true";
            }
            throw new Error("Authentication token is missing or expired. Please log in again.");
        }

        if (!response.ok) {
            let errorMsg = `Request failed with status ${response.status}`;
            try {
                const data = await response.json();
                if (data && data.error) errorMsg = data.error;
            } catch {
                if (response.status === 404) errorMsg = "The requested receipt file was not found.";
                if (response.status === 403) errorMsg = "Access denied: you do not have permission to view this receipt.";
            }
            throw new Error(errorMsg);
        }

        const blob = await response.blob();
        const contentType = response.headers.get("Content-Type") || blob.type || "application/octet-stream";
        return {
            blob: new Blob([blob], { type: contentType }),
            contentType,
            contentDisposition: response.headers.get("Content-Disposition")
        };
    }
};

window.API = API;
