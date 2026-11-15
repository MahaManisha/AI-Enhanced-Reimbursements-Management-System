"""
Finance Administrator Routes (MongoDB)
AI-Enhanced Reimbursements Management System

Endpoints for reviewing, approving, and rejecting reimbursement requests,
as well as administrative employee listings.
"""

from flask import Blueprint, request, jsonify, g
from app.models.reimbursement import ReimbursementModel
from app.models.user import UserModel
from app.utils.auth_utils import admin_required
from app.utils.validators import validate_review_action

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/reimbursements", methods=["GET"])
@admin_required
def get_all_reimbursements():
    """
    Returns reimbursement requests with multi-parameter filtering
    (status, category, employee, risk tier, date range, amount range, search).
    """
    employee_id = request.args.get("employee_id")
    status = request.args.get("status")
    category_id = request.args.get("category_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    search = request.args.get("search")
    risk = request.args.get("risk")

    claims = ReimbursementModel.get_all_filtered(
        employee_id=employee_id if employee_id else None,
        status=status,
        category_id=category_id if category_id else None,
        start_date=start_date,
        end_date=end_date,
        min_amount=float(min_amount) if min_amount else None,
        max_amount=float(max_amount) if max_amount else None,
        search=search,
        risk=risk
    )

    return jsonify({"success": True, "claims": claims, "count": len(claims)}), 200


@admin_bp.route("/reimbursements/<reimb_id>", methods=["GET"])
@admin_required
def get_reimbursement_details(reimb_id):
    """Retrieves full claim dossier and chronological audit trail for finance review."""
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement claim not found."}), 404

    audit_logs = ReimbursementModel.get_audit_logs(reimb_id)
    return jsonify({"success": True, "claim": claim, "audit_logs": audit_logs}), 200


@admin_bp.route("/reimbursements/<reimb_id>/approve", methods=["POST"])
@admin_required
def approve_reimbursement(reimb_id):
    """
    Approves a pending reimbursement claim.
    Records the reviewing administrator, approval timestamp, notes, and audit log.
    """
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement claim not found."}), 404

    claim_status = claim.get("status") or claim.get("claim_status")
    if claim_status == "APPROVED":
        return jsonify({"success": False, "error": "Claim has already been approved."}), 400

    data = request.get_json(silent=True) or {}
    comments = data.get("comments", "Approved by finance administrator.").strip()

    updated = ReimbursementModel.review(
        reimbursement_id=reimb_id,
        reviewer_id=user["id"],
        status="APPROVED",
        comments=comments,
        rejection_reason=None
    )

    return jsonify({
        "success": True,
        "message": f"Claim #{reimb_id} has been approved successfully.",
        "claim": updated
    }), 200


@admin_bp.route("/reimbursements/<reimb_id>/reject", methods=["POST"])
@admin_required
def reject_reimbursement(reimb_id):
    """
    Rejects a reimbursement claim with a required explanation reason.
    Records the rejection reason and appends an entry to the audit trail.
    """
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement claim not found."}), 404

    claim_status = claim.get("status") or claim.get("claim_status")
    if claim_status == "REJECTED":
        return jsonify({"success": False, "error": "Claim has already been rejected."}), 400

    data = request.get_json(silent=True) or {}
    rejection_reason = (data.get("rejection_reason") or "").strip()
    comments = (data.get("comments") or "").strip()

    is_valid, err_msg = validate_review_action(status="REJECTED", rejection_reason=rejection_reason)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400

    updated = ReimbursementModel.review(
        reimbursement_id=reimb_id,
        reviewer_id=user["id"],
        status="REJECTED",
        comments=comments or f"Rejected: {rejection_reason}",
        rejection_reason=rejection_reason
    )

    return jsonify({
        "success": True,
        "message": f"Claim #{reimb_id} has been rejected.",
        "claim": updated
    }), 200


@admin_bp.route("/employees", methods=["GET"])
@admin_required
def list_employees():
    """Returns a list of employee profiles for filtering in the finance dashboard."""
    employees = UserModel.get_all(role="EMPLOYEE")
    return jsonify({
        "success": True,
        "employees": [
            {
                "id": str(e["id"]),
                "full_name": e.get("full_name") or e.get("name"),
                "email": e["email"],
                "department": e["department"]
            }
            for e in employees
        ]
    }), 200
