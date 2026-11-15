"""
Reimbursement Routes (MongoDB)
AI-Enhanced Reimbursements Management System

Endpoints for submitting claims, uploading receipts, viewing receipts securely,
and retrieving real-time ML risk predictions and Generative AI audit summaries.
"""

import json
from flask import Blueprint, request, jsonify, g
from app.models.reimbursement import ReimbursementModel
from app.models.category import CategoryModel
from app.utils.auth_utils import token_required
from app.utils.file_utils import validate_file_content, save_uploaded_file, serve_secure_file
from app.utils.validators import validate_reimbursement_data
from app.services.prediction_service import PredictionService
from app.services.genai_service import GenAIService

reimbursements_bp = Blueprint("reimbursements", __name__, url_prefix="/api/reimbursements")


def _compute_ml_and_ai(claim: dict) -> tuple[dict, dict, str]:
    """
    Executes the dual-intelligence audit pipeline:
    1. Evaluates claim via Random Forest ML model (predicts approval/review/rejection risk score).
    2. Passes features & ML score to Generative AI for contextual auditing and compliance checks.
    3. Persists both results into MongoDB for instant dashboard display.
    """
    pred_result = PredictionService.predict(claim)
    if pred_result.get("available"):
        prob_json = json.dumps(pred_result.get("probabilities", {}))
        ReimbursementModel.update_ml_prediction(
            reimbursement_id=claim["id"],
            prediction=pred_result["prediction"],
            confidence=pred_result["confidence"],
            probabilities_json=prob_json
        )
        claim["ml_prediction"] = pred_result["prediction"]
        claim["ml_confidence"] = pred_result["confidence"]
        claim["ml_probabilities"] = prob_json

    _, insights, provider_info = GenAIService.generate_reimbursement_insights(claim, pred_result)
    ReimbursementModel.update_ai_insights(
        reimbursement_id=claim["id"],
        summary=insights.get("summary", ""),
        observations=insights.get("observations_text") or insights.get("observations", ""),
        missing_info=insights.get("missing_info_text") or insights.get("missing_info", ""),
        suggested_actions=insights.get("suggested_actions_text") or insights.get("suggested_actions", ""),
        observations_list=insights.get("observations_list") or (insights.get("observations") if isinstance(insights.get("observations"), list) else None),
        missing_info_list=insights.get("missing_info_list") or (insights.get("missing_info") if isinstance(insights.get("missing_info"), list) else None),
        suggested_actions_list=insights.get("suggested_actions_list") or (insights.get("suggested_actions") if isinstance(insights.get("suggested_actions"), list) else None),
        ai_provider=insights.get("ai_source") or insights.get("ai_provider") or provider_info
    )
    return pred_result, insights, provider_info


@reimbursements_bp.route("", methods=["POST"])
@token_required
def create_reimbursement():
    """
    Submits a new reimbursement request.
    Validates expense fields, verifies active category, saves record to MongoDB,
    and runs the ML + GenAI analysis pipeline.
    """
    user = g.current_user
    data = request.get_json(silent=True) or {}

    is_valid, err_msg = validate_reimbursement_data(data)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400

    category = CategoryModel.get_by_id(data["category_id"])
    if not category or not (category.get("is_active") or category.get("active")):
        return jsonify({"success": False, "error": "Selected expense category is invalid or inactive."}), 400

    claim = ReimbursementModel.create(
        employee_id=user["id"],
        category_id=category["id"],
        amount=float(data["amount"]),
        expense_date=data["expense_date"],
        description=data["description"]
    )

    pred_result, insights, provider_info = _compute_ml_and_ai(claim)
    refreshed_claim = ReimbursementModel.get_by_id(claim["id"])

    return jsonify({
        "success": True,
        "message": "Reimbursement claim submitted successfully.",
        "claim": refreshed_claim,
        "ml_prediction": pred_result,
        "ai_insights": insights,
        "ai_engine": provider_info
    }), 201


@reimbursements_bp.route("/my", methods=["GET"])
@token_required
def get_my_reimbursements():
    """Returns all reimbursement claims submitted by the currently logged-in employee."""
    user = g.current_user
    status = request.args.get("status")
    category_id = request.args.get("category_id")

    claims = ReimbursementModel.get_all_for_employee(
        employee_id=user["id"],
        status=status,
        category_id=category_id
    )
    return jsonify({"success": True, "claims": claims, "count": len(claims)}), 200


@reimbursements_bp.route("/<reimb_id>", methods=["GET"])
@token_required
def get_reimbursement(reimb_id):
    """
    Returns full claim details including audit trail, ML predictions, and AI observations.
    Employees can only view their own claims; Admins can view any claim.
    """
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement request not found."}), 404

    # Enforce data privacy between employees
    if user["role"] != "ADMIN" and str(claim.get("employee_id")) != str(user["id"]):
        return jsonify({"success": False, "error": "Access denied: you can only view your own claims."}), 403

    audit_logs = ReimbursementModel.get_audit_logs(reimb_id)

    if claim.get("ml_probabilities") and isinstance(claim["ml_probabilities"], str):
        try:
            claim["ml_probabilities"] = json.loads(claim["ml_probabilities"])
        except (ValueError, TypeError):
            pass

    return jsonify({
        "success": True,
        "claim": claim,
        "audit_logs": audit_logs
    }), 200


@reimbursements_bp.route("/<reimb_id>/upload", methods=["POST"])
@token_required
def upload_bill(reimb_id):
    """
    Uploads and attaches a receipt document (PDF, PNG, JPG) to an existing pending claim.
    Automatically re-triggers ML and GenAI evaluation to reflect the attached proof.
    """
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement request not found."}), 404

    if user["role"] != "ADMIN" and str(claim.get("employee_id")) != str(user["id"]):
        return jsonify({"success": False, "error": "Access denied: you cannot modify another employee's claim."}), 403

    claim_status = claim.get("status") or claim.get("claim_status")
    if claim_status in ("APPROVED", "REJECTED"):
        return jsonify({"success": False, "error": f"Cannot upload receipt. Claim is already {claim_status}."}), 400

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in upload request."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No file selected."}), 400

    is_valid, err_msg = validate_file_content(file)
    if not is_valid:
        return jsonify({"success": False, "error": err_msg}), 400

    stored_name, original_name = save_uploaded_file(file)
    ReimbursementModel.update_bill(
        reimbursement_id=reimb_id,
        bill_path=stored_name,
        bill_original_name=original_name,
        actor_id=user["id"]
    )

    updated_claim = ReimbursementModel.get_by_id(reimb_id)
    pred_result, insights, _ = _compute_ml_and_ai(updated_claim)
    refreshed_claim = ReimbursementModel.get_by_id(reimb_id)

    return jsonify({
        "success": True,
        "message": "Bill uploaded successfully. ML risk prediction and AI insights updated.",
        "claim": refreshed_claim,
        "ml_prediction": pred_result,
        "ai_insights": insights
    }), 200


@reimbursements_bp.route("/<reimb_id>/bill", methods=["GET"])
@token_required
def get_bill_file(reimb_id):
    """
    Serves the attached receipt document directly to authenticated users.
    Enforces authorization check and verifies file integrity.
    """
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement request not found."}), 404

    if user["role"] != "ADMIN" and str(claim.get("employee_id")) != str(user["id"]):
        return jsonify({"success": False, "error": "Access denied: you cannot view receipts for other employees."}), 403

    bill_path = claim.get("receipt_path") or claim.get("bill_path")
    if not bill_path:
        return jsonify({"success": False, "error": "No bill has been uploaded for this reimbursement."}), 404

    return serve_secure_file(
        stored_filename=bill_path,
        original_filename=claim.get("receipt_filename") or claim.get("bill_original_name")
    )


@reimbursements_bp.route("/<reimb_id>/prediction", methods=["GET"])
@token_required
def get_prediction(reimb_id):
    """Re-runs and returns the Random Forest ML prediction for a given claim."""
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement request not found."}), 404

    if user["role"] != "ADMIN" and str(claim.get("employee_id")) != str(user["id"]):
        return jsonify({"success": False, "error": "Access denied."}), 403

    pred_result = PredictionService.predict(claim)
    if pred_result.get("available"):
        prob_json = json.dumps(pred_result.get("probabilities", {}))
        ReimbursementModel.update_ml_prediction(
            reimbursement_id=reimb_id,
            prediction=pred_result["prediction"],
            confidence=pred_result["confidence"],
            probabilities_json=prob_json
        )

    return jsonify({"success": True, "prediction": pred_result}), 200


@reimbursements_bp.route("/<reimb_id>/summary", methods=["POST"])
@token_required
def generate_summary(reimb_id):
    """Regenerates Generative AI financial insights for a given claim."""
    user = g.current_user
    claim = ReimbursementModel.get_by_id(reimb_id)
    if not claim:
        return jsonify({"success": False, "error": "Reimbursement request not found."}), 404

    if user["role"] != "ADMIN" and str(claim.get("employee_id")) != str(user["id"]):
        return jsonify({"success": False, "error": "Access denied."}), 403

    _, insights, provider_info = _compute_ml_and_ai(claim)

    return jsonify({
        "success": True,
        "insights": insights,
        "engine": provider_info
    }), 200
