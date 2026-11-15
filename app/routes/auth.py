"""
Authentication & User Session Routes (MongoDB)
AI-Enhanced Reimbursements Management System

Provides endpoints for employee registration, corporate login, token verification,
and current user profile retrieval using JWT and MongoDB.
"""

from flask import Blueprint, request, jsonify, g
from app.models.user import UserModel
from app.utils.auth_utils import verify_password, generate_jwt_token, token_required
from app.utils.validators import validate_registration_data

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _serialize_user(user: dict) -> dict:
    """Formats user dictionary for API response, omitting sensitive fields like password hashes."""
    return {
        "id": str(user.get("id") or user.get("_id")),
        "_id": str(user.get("_id") or user.get("id")),
        "full_name": user.get("full_name") or user.get("name"),
        "name": user.get("name") or user.get("full_name"),
        "email": user["email"],
        "role": user["role"],
        "department": user.get("department", "General")
    }


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Registers a new employee account in MongoDB.
    Validates input fields, checks for duplicate emails, and returns a signed JWT.
    """
    data = request.get_json(silent=True) or {}
    is_valid, error_message = validate_registration_data(data)
    if not is_valid:
        return jsonify({"success": False, "error": error_message}), 400

    email = data["email"].strip().lower()
    existing_user = UserModel.get_by_email(email)
    if existing_user:
        return jsonify({
            "success": False,
            "error": f"An account with email '{email}' already exists."
        }), 409

    role = data.get("role", "EMPLOYEE").strip().upper()
    user = UserModel.create(
        full_name=data["full_name"],
        email=email,
        plain_password=data["password"],
        role=role,
        department=data.get("department", "General")
    )

    token = generate_jwt_token(user["id"], user["role"], user["email"])
    return jsonify({
        "success": True,
        "message": "User registered successfully.",
        "token": token,
        "user": _serialize_user(user)
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticates an employee or finance administrator with email and password.
    Returns a signed JWT bearer token on success.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required."}), 400

    user = UserModel.get_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    if not verify_password(password, user["password_hash"]):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    token = generate_jwt_token(user["id"], user["role"], user["email"])

    return jsonify({
        "success": True,
        "message": "Authentication successful.",
        "token": token,
        "user": _serialize_user(user)
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Logs out the user. Client-side clears the stored JWT.
    """
    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    }), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_profile():
    """Returns the authenticated user's profile details."""
    return jsonify({
        "success": True,
        "user": _serialize_user(g.current_user)
    }), 200
