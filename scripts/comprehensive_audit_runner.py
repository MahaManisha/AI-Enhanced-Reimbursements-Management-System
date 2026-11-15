import io
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.models.reimbursement import ReimbursementModel

def run_full_system_audit():
    app = create_app()
    client = app.test_client()
    results = {}

    print("==================================================================")
    print("AI-ENHANCED REIMBURSEMENTS MANAGEMENT SYSTEM - FULL SYSTEM AUDIT")
    print("==================================================================")

    # ---------------------------------------------------------
    # TEST 1: Password Hashing with Scrypt
    # ---------------------------------------------------------
    from app.utils.auth_utils import hash_password, verify_password
    pwd = "AuditPassword@2026"
    h = hash_password(pwd)
    assert h.startswith("scrypt:"), f"Password hash is not using scrypt: {h}"
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword", h) is False
    print("[PASS] Password Hashing: Uses Werkzeug scrypt hashing format.")
    results["Password Hashing (scrypt)"] = "PASS"

    # ---------------------------------------------------------
    # TEST 2: User Registration & Duplicate Email Protection
    # ---------------------------------------------------------
    import uuid
    unique_email = f"audit_emp_{uuid.uuid4().hex[:8]}@company.com"
    reg_payload = {
        "full_name": "Audit Test Employee",
        "email": unique_email,
        "password": "Password@123",
        "department": "Quality Assurance",
        "role": "EMPLOYEE"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.data}"
    reg_data = reg_res.get_json()
    assert reg_data["success"] is True
    assert "token" in reg_data
    new_emp_id = reg_data["user"]["id"]
    new_emp_token = reg_data["token"]
    new_emp_headers = {"Authorization": f"Bearer {new_emp_token}"}
    print(f"[PASS] Employee Registration: Created User #{new_emp_id} ({unique_email}).")

    # Duplicate check
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.get_json()["error"]
    print("[PASS] Registration Security: Blocked duplicate email registration (HTTP 409 Conflict).")
    results["User Registration"] = "PASS"

    # ---------------------------------------------------------
    # TEST 3: Authentication & JWT Tokens
    # ---------------------------------------------------------
    # Admin login
    admin_login = client.post("/api/auth/login", json={"email": "admin@company.com", "password": "Password@123"})
    assert admin_login.status_code == 200
    admin_token = admin_login.get_json()["token"]
    admin_id = admin_login.get_json()["user"]["id"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[PASS] Finance Admin Login: Authenticated.")

    # Employee login
    emp_login = client.post("/api/auth/login", json={"email": "john.doe@company.com", "password": "Password@123"})
    assert emp_login.status_code == 200
    emp_token = emp_login.get_json()["token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    print("[PASS] Employee Login: Authenticated.")

    # Invalid password login
    bad_login = client.post("/api/auth/login", json={"email": "admin@company.com", "password": "WrongPassword"})
    assert bad_login.status_code == 401
    print("[PASS] Login Security: Rejected invalid credentials.")
    results["Authentication & JWT"] = "PASS"

    # ---------------------------------------------------------
    # TEST 4: Role-Based Access Control (RBAC)
    # ---------------------------------------------------------
    # Employee attempts admin endpoint
    emp_on_admin = client.get("/api/admin/analytics", headers=emp_headers)
    assert emp_on_admin.status_code == 403
    assert "Access denied" in emp_on_admin.get_json()["error"]
    print("[PASS] RBAC: Employee blocked from accessing Finance Admin analytics (HTTP 403).")

    # Employee attempts to approve claim
    emp_approve = client.post("/api/admin/reimbursements/1/approve", headers=emp_headers, json={"comments": "hack"})
    assert emp_approve.status_code == 403
    print("[PASS] RBAC: Employee blocked from approving claims (HTTP 403).")

    # Unauthenticated request
    unauth = client.get("/api/admin/analytics")
    assert unauth.status_code == 401
    print("[PASS] RBAC: Unauthenticated requests blocked (HTTP 401).")
    results["RBAC & Security"] = "PASS"

    # ---------------------------------------------------------
    # TEST 5: Category Management (Admin & Employee)
    # ---------------------------------------------------------
    cat_res = client.get("/api/categories")
    assert cat_res.status_code == 200
    cats = cat_res.get_json()["categories"]
    assert len(cats) >= 7
    print(f"[PASS] Category Retrieval: Loaded {len(cats)} categories.")

    # Admin creates category
    new_cat_name = f"Audit Category {uuid.uuid4().hex[:6]}"
    cat_create = client.post("/api/admin/categories", headers=admin_headers, json={
        "category_name": new_cat_name,
        "description": "Created during system audit"
    })
    assert cat_create.status_code == 201
    new_cat_id = cat_create.get_json()["category"]["id"]
    print(f"[PASS] Category Management: Admin created category #{new_cat_id} ({new_cat_name}).")
    results["Category Management"] = "PASS"

    # ---------------------------------------------------------
    # TEST 6: Claim Submission, ML Scoring & GenAI Audit
    # ---------------------------------------------------------
    claim_payload = {
        "category_id": new_cat_id,
        "amount": 625.00,
        "expense_date": "2026-11-04",
        "description": "Onsite audit client consultation and workstation supplies"
    }
    submit_res = client.post("/api/reimbursements", headers=new_emp_headers, json=claim_payload)
    assert submit_res.status_code == 201
    claim_data = submit_res.get_json()["claim"]
    claim_id = claim_data["id"]
    print(f"[PASS] Claim Submission: Created Claim #{claim_id} for Employee #{new_emp_id}.")

    # Verify ML output
    ml_pred = claim_data.get("ml_prediction")
    ml_conf = claim_data.get("ml_confidence")
    assert ml_pred in ("LIKELY_APPROVED", "REQUIRES_REVIEW", "HIGH_REJECTION_RISK")
    assert ml_conf is not None and float(ml_conf) > 0.0
    print(f"[PASS] ML Pipeline: Predicted Risk Class '{ml_pred}' with confidence {float(ml_conf)*100:.1f}%.")

    # Verify GenAI output
    ai_summary = claim_data.get("ai_summary")
    ai_obs = claim_data.get("ai_observations")
    assert ai_summary is not None and len(ai_summary) > 10
    assert ai_obs is not None and len(ai_obs) > 5
    print(f"[PASS] GenAI Copilot: Generated summary: {ai_summary[:70]}...")
    results["Claim Submission & AI/ML"] = "PASS"

    # ---------------------------------------------------------
    # TEST 7: Receipt Upload & Content-Type Validation
    # ---------------------------------------------------------
    # Invalid extension blocked
    bad_upload = client.post(
        f"/api/reimbursements/{claim_id}/upload",
        headers=new_emp_headers,
        data={"file": (io.BytesIO(b"binary data"), "virus.exe")},
        content_type="multipart/form-data"
    )
    assert bad_upload.status_code == 400
    print("[PASS] File Upload Security: Blocked disallowed extension .exe.")

    # Valid PNG uploaded
    png_sample = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    good_upload = client.post(
        f"/api/reimbursements/{claim_id}/upload",
        headers=new_emp_headers,
        data={"file": (io.BytesIO(png_sample), "audit_receipt.png")},
        content_type="multipart/form-data"
    )
    assert good_upload.status_code == 200
    upload_claim = good_upload.get_json()["claim"]
    assert upload_claim["bill_available"] == 1
    print(f"[PASS] File Upload: Attached PNG receipt (stored as {upload_claim['bill_path']}).")
    results["File Upload & Validation"] = "PASS"

    # ---------------------------------------------------------
    # TEST 8: Data Privacy & Receipt Access Controls
    # ---------------------------------------------------------
    # Employee 1 attempts to view Employee New's receipt
    emp1_view_other = client.get(f"/api/reimbursements/{claim_id}/bill", headers=emp_headers)
    assert emp1_view_other.status_code == 403
    print("[PASS] Data Privacy: Employee cannot view another employee's receipt (HTTP 403).")

    # Employee 1 attempts to view Employee New's claim details
    emp1_details_other = client.get(f"/api/reimbursements/{claim_id}", headers=emp_headers)
    assert emp1_details_other.status_code == 403
    print("[PASS] Data Privacy: Employee cannot view another employee's claim details (HTTP 403).")

    # Owner views own receipt
    owner_view = client.get(f"/api/reimbursements/{claim_id}/bill", headers=new_emp_headers)
    assert owner_view.status_code == 200
    assert owner_view.headers.get("Content-Type") == "image/png"
    print("[PASS] Receipt Viewing: Claim owner retrieved own receipt.")

    # Admin views receipt
    admin_view = client.get(f"/api/reimbursements/{claim_id}/bill", headers=admin_headers)
    assert admin_view.status_code == 200
    assert admin_view.headers.get("Content-Type") == "image/png"
    print("[PASS] Receipt Viewing: Finance Admin retrieved receipt.")
    results["Data Privacy & Permissions"] = "PASS"

    # ---------------------------------------------------------
    # TEST 9: Finance Admin Decision Lifecycle (Approve & Reject)
    # ---------------------------------------------------------
    # 9a. Approve claim
    approve_res = client.post(
        f"/api/admin/reimbursements/{claim_id}/approve",
        headers=admin_headers,
        json={"comments": "Approved after reviewing consultation agenda and receipt."}
    )
    assert approve_res.status_code == 200
    app_data = approve_res.get_json()["claim"]
    assert app_data["claim_status"] == "APPROVED"
    assert app_data["reviewer_comments"] is not None
    print(f"[PASS] Claim Approval: Admin marked Claim #{claim_id} as APPROVED.")

    # Verify in DB
    db_claim = ReimbursementModel.get_by_id(claim_id)
    assert db_claim["claim_status"] == "APPROVED"
    assert str(db_claim["reviewer_id"]) == str(admin_id)
    print("[PASS] MongoDB Persistence: Approval saved to MongoDB.")

    # Verify audit logs
    audit_logs = ReimbursementModel.get_audit_logs(claim_id)
    actions = [l["action"] for l in audit_logs]
    assert "CREATED" in actions
    assert "BILL_UPLOADED" in actions
    assert "APPROVED" in actions
    print(f"[PASS] Audit Trail: Lifecycle tracked ({', '.join(actions)}).")

    # 9b. Reject claim (test mandatory reason)
    # Submit second claim to reject
    claim2_res = client.post("/api/reimbursements", headers=new_emp_headers, json={
        "category_id": new_cat_id,
        "amount": 950.00,
        "expense_date": "2026-11-04",
        "description": "Weekend entertainment expense"
    })
    claim2_id = claim2_res.get_json()["claim"]["id"]

    # Reject without reason -> must fail
    rej_fail = client.post(
        f"/api/admin/reimbursements/{claim2_id}/reject",
        headers=admin_headers,
        json={"rejection_reason": ""}
    )
    assert rej_fail.status_code == 400
    print("[PASS] Rejection Policy: Mandates rejection reason (HTTP 400).")

    # Reject with reason -> must succeed
    rej_ok = client.post(
        f"/api/admin/reimbursements/{claim2_id}/reject",
        headers=admin_headers,
        json={"rejection_reason": "Weekend entertainment expenses are non-compliant with corporate guidelines."}
    )
    assert rej_ok.status_code == 200
    assert rej_ok.get_json()["claim"]["claim_status"] == "REJECTED"
    print(f"[PASS] Claim Rejection: Admin marked Claim #{claim2_id} as REJECTED with mandatory reason.")
    results["Decision Lifecycle (Approve/Reject)"] = "PASS"

    # ---------------------------------------------------------
    # TEST 10: Dashboards & Analytics
    # ---------------------------------------------------------
    # Employee analytics
    emp_analytics = client.get("/api/employee/analytics", headers=new_emp_headers).get_json()
    emp_summary = emp_analytics["summary"]
    assert emp_summary["total_claims"] >= 2
    assert emp_summary["approved_claims"] >= 1
    assert emp_summary["rejected_claims"] >= 1
    print(f"[PASS] Employee Analytics: Real counts returned (Total: {emp_summary['total_claims']}, Approved: {emp_summary['approved_claims']}, Rejected: {emp_summary['rejected_claims']}).")

    # Admin analytics
    admin_analytics = client.get("/api/admin/analytics", headers=admin_headers).get_json()
    adm_summary = admin_analytics["summary"]
    assert adm_summary["total_claims"] >= 2
    assert adm_summary["approved_claims"] >= 1
    assert adm_summary["rejected_claims"] >= 1
    assert adm_summary["total_amount_approved"] >= 625.0
    print(f"[PASS] Admin Analytics: Real volume returned (Approved: ${adm_summary['total_amount_approved']:.2f}).")
    results["Dashboard Analytics"] = "PASS"

    # ---------------------------------------------------------
    # CLEANUP: Remove audit test records so live database stays clean
    # ---------------------------------------------------------
    from app.db import get_db, to_object_id
    db = get_db()
    test_claim_ids = [to_object_id(claim_id), to_object_id(claim2_id), str(claim_id), str(claim2_id)]
    db.reimbursement_requests.delete_many({"_id": {"$in": test_claim_ids}})
    db.reimbursement_audit_logs.delete_many({"$or": [{"reimbursement_id": {"$in": test_claim_ids}}, {"actor_id": to_object_id(new_emp_id)}]})
    db.expense_categories.delete_many({"_id": {"$in": [to_object_id(new_cat_id), str(new_cat_id)]}})
    db.users.delete_many({"_id": {"$in": [to_object_id(new_emp_id), str(new_emp_id)]}})
    print("[PASS] Cleanup: Temporary audit test artifacts cleanly removed from database.")

    print("\n==================================================================")
    print("AUDIT SUMMARY:")
    for k, v in results.items():
        print(f"  * {k:<35}: {v}")
    print("==================================================================")

if __name__ == "__main__":
    run_full_system_audit()
