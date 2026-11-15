"""
Input Validation Utilities
AI-Enhanced Reimbursements Management System

Validates incoming JSON payloads for registration, reimbursement submission,
and admin review decisions to ensure data integrity before database operations.
"""

from datetime import datetime, date
import re
from typing import Tuple, Dict, Any

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_registration_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates user registration input fields."""
    if not data or not isinstance(data, dict):
        return False, "Payload must be a valid JSON object."

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    department = data.get("department", "").strip()
    role = data.get("role", "EMPLOYEE").strip().upper()

    if not full_name or len(full_name) < 2 or len(full_name) > 100:
        return False, "Full name must be between 2 and 100 characters."

    if not email or not EMAIL_REGEX.match(email):
        return False, "A valid email address is required."

    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."

    if not department or len(department) < 2:
        return False, "Department is required."

    if role not in ("EMPLOYEE", "ADMIN"):
        return False, "Role must be either 'EMPLOYEE' or 'ADMIN'."

    return True, "Valid"


def validate_reimbursement_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates employee reimbursement submission inputs."""
    if not data or not isinstance(data, dict):
        return False, "Payload must be a valid JSON object."

    category_id = data.get("category_id")
    if not category_id and category_id != 0:
        return False, "Expense category is required."

    is_valid_cat = False
    try:
        if int(category_id) > 0:
            is_valid_cat = True
    except (ValueError, TypeError):
        pass

    try:
        from bson import ObjectId
        if not is_valid_cat and isinstance(category_id, (str, ObjectId)) and ObjectId.is_valid(str(category_id)):
            is_valid_cat = True
    except Exception:
        pass

    if not is_valid_cat:
        return False, "Category ID must be an integer or valid ObjectId."

    amount = data.get("amount")
    if amount is None or amount == "":
        return False, "Expense amount is required."
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return False, "Expense amount must be greater than 0."
        if amount_float > 1000000:
            return False, "Expense amount exceeds permissible limit (1,000,000)."
    except (ValueError, TypeError):
        return False, "Amount must be a numeric value."

    expense_date_str = data.get("expense_date")
    if not expense_date_str:
        return False, "Expense date is required."
    try:
        exp_date = datetime.strptime(str(expense_date_str).strip(), "%Y-%m-%d").date()
        if exp_date > date.today():
            return False, "Expense date cannot be in the future."
        if (date.today() - exp_date).days > 365:
            return False, "Expense claims older than 365 days cannot be processed."
    except ValueError:
        return False, "Expense date must follow the YYYY-MM-DD format."

    description = data.get("description", "").strip()
    if not description or len(description) < 5:
        return False, "Please provide a detailed expense description (minimum 5 characters)."

    return True, "Valid"


def validate_review_action(status: str, rejection_reason: str = None) -> Tuple[bool, str]:
    """Validates administrative review decisions (APPROVED or REJECTED)."""
    status_upper = (status or "").strip().upper()
    if status_upper not in ("APPROVED", "REJECTED"):
        return False, "Status decision must be either 'APPROVED' or 'REJECTED'."

    if status_upper == "REJECTED":
        reason = (rejection_reason or "").strip()
        if not reason or len(reason) < 5:
            return False, "A clear rejection reason is mandatory when rejecting a reimbursement claim (min 5 characters)."

    return True, "Valid"
