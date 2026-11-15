"""
Expense Categories Routes (MongoDB)
AI-Enhanced Reimbursements Management System

Endpoints to list active categories for claim submission
and manage categories for Finance Administrators.
"""

from flask import Blueprint, request, jsonify
from app.models.category import CategoryModel
from app.utils.auth_utils import admin_required

categories_bp = Blueprint("categories", __name__, url_prefix="/api")


@categories_bp.route("/categories", methods=["GET"])
def get_categories():
    """
    Returns active expense categories for claim forms.
    Admins can append ?all=true to inspect inactive categories as well.
    """
    include_all = request.args.get("all", "false").lower() == "true"
    categories = CategoryModel.get_all(include_inactive=include_all)
    return jsonify({"success": True, "categories": categories}), 200


@categories_bp.route("/admin/categories", methods=["POST"])
@admin_required
def create_category():
    """Creates a new expense category (Admin only)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("category_name") or data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    if not name or len(name) < 2:
        return jsonify({"success": False, "error": "Category name must be at least 2 characters."}), 400

    existing = CategoryModel.get_by_name(name)
    if existing:
        return jsonify({"success": False, "error": f"Category '{name}' already exists."}), 409

    created = CategoryModel.create(name=name, description=description, is_active=True)
    return jsonify({
        "success": True,
        "message": "Category created successfully.",
        "category": created
    }), 201


@categories_bp.route("/admin/categories/<cat_id>", methods=["PUT"])
@admin_required
def update_category(cat_id):
    """Updates an existing category's name, description, or active status (Admin only)."""
    data = request.get_json(silent=True) or {}
    cat = CategoryModel.get_by_id(cat_id)
    if not cat:
        return jsonify({"success": False, "error": "Category not found."}), 404

    name = data.get("category_name") or data.get("name")
    description = data.get("description")
    active = data.get("active") if "active" in data else data.get("is_active")

    updated = CategoryModel.update(
        category_id=cat_id,
        name=name,
        description=description,
        is_active=active
    )

    return jsonify({
        "success": True,
        "message": "Category updated successfully.",
        "category": updated
    }), 200
