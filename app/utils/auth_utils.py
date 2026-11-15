"""
Authentication Utilities & Decorators (MongoDB)
AI-Enhanced Reimbursements Management System

Provides password hashing via scrypt, JWT token creation and validation,
and Flask route protection decorators (@token_required, @admin_required).
"""

import datetime
from functools import wraps
from typing import Tuple, Dict, Any, List
import jwt
from flask import request, jsonify, g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from app.config import Config
from app.db import get_db, to_object_id, serialize_doc


def hash_password(password: str) -> str:
    """Hashes a plaintext password using the scrypt key derivation function."""
    return generate_password_hash(password, method="scrypt")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored scrypt password hash."""
    return check_password_hash(hashed_password, plain_password)


def _get_jwt_settings() -> Tuple[str, int]:
    """Retrieves JWT secret key and token lifetime in hours from Flask app config."""
    try:
        secret = current_app.config.get("JWT_SECRET_KEY", Config.JWT_SECRET_KEY)
        expires_hours = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES_HOURS", Config.JWT_ACCESS_TOKEN_EXPIRES_HOURS)
    except RuntimeError:
        secret = Config.JWT_SECRET_KEY
        expires_hours = Config.JWT_ACCESS_TOKEN_EXPIRES_HOURS
    return secret, expires_hours


def generate_jwt_token(user_id: Any, role: str, email: str) -> str:
    """Creates a cryptographically signed HS256 JWT access token with an expiration timestamp."""
    secret, expires_hours = _get_jwt_settings()
    uid = str(user_id) if isinstance(user_id, ObjectId) else user_id
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "user_id": uid,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + datetime.timedelta(hours=expires_hours)
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token signature and expiration."""
    secret, _ = _get_jwt_settings()
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Authentication token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid authentication token. Please log in again.")


def token_required(f):
    """
    Decorator to protect API endpoints.
    Extracts Bearer token from the Authorization header, validates it,
    loads the authenticated user from MongoDB, and attaches it to Flask's `g.current_user`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        elif "token" in request.args:
            token = request.args.get("token")

        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication token is missing. Please provide Bearer token in Authorization header."
            }), 401

        try:
            payload = decode_jwt_token(token)
            user_id = payload.get("user_id")
            email = payload.get("email")

            db = get_db()
            user_oid = to_object_id(user_id)
            user_doc = db.users.find_one({"$or": [{"_id": user_oid}, {"id": user_id}]})
            if not user_doc and email:
                user_doc = db.users.find_one({"email": email.strip().lower()})

            if not user_doc:
                return jsonify({"success": False, "error": "User account no longer exists."}), 401

            g.current_user = serialize_doc(user_doc)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 401
        except Exception as e:
            return jsonify({"success": False, "error": f"Authentication failure: {str(e)}"}), 401

        return f(*args, **kwargs)
    return decorated


def role_required(allowed_roles: List[str]):
    """
    Decorator to restrict access to users belonging to specific roles (e.g. ['ADMIN']).
    Must be applied to authenticated routes.
    """
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            user = g.current_user
            if user["role"] not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": f"Access denied. Required role: {', '.join(allowed_roles)}. Your role: {user['role']}."
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    """Convenience decorator ensuring only users with the ADMIN role can execute the endpoint."""
    return role_required(["ADMIN"])(f)
