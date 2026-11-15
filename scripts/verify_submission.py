import io
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.models.reimbursement import ReimbursementModel

def run_verification():
    app = create_app()
    client = app.test_client()

    print("==================================================")
    print("STEP 1: Authenticate Employee (john.doe@company.com)")
    print("==================================================")
    login_res = client.post("/api/auth/login", json={
        "email": "john.doe@company.com",
        "password": "Password@123"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.data}"
    login_data = login_res.get_json()
    token = login_data["token"]
    user = login_data["user"]
    print(f"[OK] Logged in as: {user['full_name']} (ID: {user['id']}, Role: {user['role']})")
    headers = {"Authorization": f"Bearer {token}"}

    print("\n==================================================")
    print("STEP 2: Verify Categories from API")
    print("==================================================")
    cat_res = client.get("/api/categories")
    assert cat_res.status_code == 200
    categories = cat_res.get_json().get("categories", [])
    assert len(categories) > 0, "No categories returned"
    print(f"[OK] Retrieved {len(categories)} active expense categories.")
    for c in categories[:3]:
        print(f"     - Category #{c['id']}: {c['category_name']}")

    selected_category_id = categories[0]["id"]
    category_name = categories[0]["category_name"]

    print("\n==================================================")
    print("STEP 3: Test Validation & Security Controls")
    print("==================================================")
    # 3a. Negative amount
    neg_res = client.post("/api/reimbursements", headers=headers, json={
        "category_id": selected_category_id,
        "amount": -45.0,
        "expense_date": "2026-11-04",
        "description": "Valid description for testing"
    })
    assert neg_res.status_code == 400
    print("[OK] Negative amount rejected properly (HTTP 400).")

    # 3b. Zero amount
    zero_res = client.post("/api/reimbursements", headers=headers, json={
        "category_id": selected_category_id,
        "amount": 0.0,
        "expense_date": "2026-11-04",
        "description": "Valid description for testing"
    })
    assert zero_res.status_code == 400
    print("[OK] Zero amount rejected properly (HTTP 400).")

    # 3c. Future date
    future_res = client.post("/api/reimbursements", headers=headers, json={
        "category_id": selected_category_id,
        "amount": 100.0,
        "expense_date": "2099-12-31",
        "description": "Future expense claim"
    })
    assert future_res.status_code == 400
    print("[OK] Future expense date rejected properly (HTTP 400).")

    # 3d. Short description
    short_res = client.post("/api/reimbursements", headers=headers, json={
        "category_id": selected_category_id,
        "amount": 100.0,
        "expense_date": "2026-11-04",
        "description": "abc"
    })
    assert short_res.status_code == 400
    print("[OK] Short description (<5 chars) rejected properly (HTTP 400).")

    # 3e. Unauthenticated request
    unauth_res = client.post("/api/reimbursements", json={
        "category_id": selected_category_id,
        "amount": 100.0,
        "expense_date": "2026-11-04",
        "description": "Unauthenticated attempt"
    })
    assert unauth_res.status_code == 401
    print("[OK] Unauthenticated request blocked properly (HTTP 401).")

    print("\n==================================================")
    print("STEP 4: Submit Valid Reimbursement Claim")
    print("==================================================")
    claim_payload = {
        "category_id": selected_category_id,
        "amount": 420.50,
        "expense_date": "2026-11-04",
        "description": "Client site visit travel expenses and metro ticketing"
    }
    submit_res = client.post("/api/reimbursements", headers=headers, json=claim_payload)
    assert submit_res.status_code == 201, f"Claim submission failed: {submit_res.data}"
    submit_data = submit_res.get_json()
    claim = submit_data["claim"]
    claim_id = claim["id"]
    print(f"[OK] Claim created successfully with ID: #{claim_id}")
    print(f"     - Amount: ${claim['amount']}")
    print(f"     - Category: {claim['category_name']}")
    print(f"     - Initial Status: {claim['claim_status']}")
    print(f"     - ML Initial Risk: {claim.get('ml_prediction')}")
    print(f"     - ML Confidence: {claim.get('ml_confidence')}")
    print(f"     - AI Summary: {claim.get('ai_summary')[:80]}...")

    print("\n==================================================")
    print("STEP 5: Upload Receipt File")
    print("==================================================")
    # 5a. Disallowed file extension (.exe)
    bad_upload = client.post(
        f"/api/reimbursements/{claim_id}/upload",
        headers=headers,
        data={"file": (io.BytesIO(b"malicious payload"), "payload.exe")},
        content_type="multipart/form-data"
    )
    assert bad_upload.status_code == 400
    print("[OK] Disallowed file extension (.exe) rejected properly (HTTP 400).")

    # 5b. Valid PDF receipt
    valid_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Metro Ticket Receipt) >>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_res = client.post(
        f"/api/reimbursements/{claim_id}/upload",
        headers=headers,
        data={"file": (io.BytesIO(valid_pdf_bytes), "travel_receipt.pdf")},
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.data}"
    upload_data = upload_res.get_json()
    updated_claim = upload_data["claim"]
    assert updated_claim["bill_available"] == 1
    print(f"[OK] Receipt uploaded: {updated_claim['bill_original_name']}")
    print(f"     - Bill Available: {updated_claim['bill_available']}")
    print(f"     - Bill Path: {updated_claim['bill_path']}")
    print(f"     - Updated ML Risk: {updated_claim.get('ml_prediction')} (Confidence: {updated_claim.get('ml_confidence')})")

    print("\n==================================================")
    print("STEP 6: Direct MongoDB Database Verification")
    print("==================================================")
    db_row = ReimbursementModel.get_by_id(claim_id)
    assert db_row is not None, "Claim record missing from MongoDB database!"
    assert str(db_row["employee_id"]) == str(user["id"]), "Employee ID mismatch!"
    assert float(db_row["amount"]) == 420.50
    assert db_row["claim_status"] == "PENDING"
    assert db_row["bill_available"] == 1
    assert db_row["bill_original_name"] == "travel_receipt.pdf"
    assert db_row.get("ml_prediction") is not None
    assert db_row.get("ai_summary") is not None
    print("[OK] MongoDB record verified:")
    for k, v in db_row.items():
        print(f"     {k}: {v}")

    print("\n==================================================")
    print("STEP 7: Verify Employee Dashboard Integration")
    print("==================================================")
    emp_analytics = client.get("/api/employee/analytics", headers=headers).get_json()
    summary = emp_analytics["summary"]
    print(f"[OK] Employee Summary:")
    print(f"     - Total Claims: {summary['total_claims']}")
    print(f"     - Pending Claims: {summary['pending_claims']}")
    print(f"     - Approved Claims: {summary['approved_claims']}")
    assert summary["total_claims"] >= 1
    assert summary["pending_claims"] >= 1

    emp_claims = client.get("/api/reimbursements/my", headers=headers).get_json()["claims"]
    found_emp = any(c["id"] == claim_id for c in emp_claims)
    assert found_emp, "Submitted claim not found in employee claims list!"
    print(f"[OK] Claim #{claim_id} found in employee claims list ({len(emp_claims)} total claims).")

    print("\n==================================================")
    print("STEP 8: Verify Finance Admin Dashboard Integration")
    print("==================================================")
    admin_login = client.post("/api/auth/login", json={
        "email": "admin@company.com",
        "password": "Password@123"
    }).get_json()
    admin_headers = {"Authorization": f"Bearer {admin_login['token']}"}

    admin_analytics = client.get("/api/admin/analytics", headers=admin_headers).get_json()["summary"]
    print(f"[OK] Finance Admin Summary:")
    print(f"     - Pending Claims: {admin_analytics['pending_claims']}")
    print(f"     - Total Volume Claimed: ${admin_analytics['total_amount_claimed']}")
    assert admin_analytics["pending_claims"] >= 1
    assert admin_analytics["total_amount_claimed"] >= 420.50

    admin_claims = client.get("/api/admin/reimbursements?status=PENDING", headers=admin_headers).get_json()["claims"]
    found_admin = any(c["id"] == claim_id for c in admin_claims)
    assert found_admin, "Submitted claim not found in finance administrator pending claims list!"
    print(f"[OK] Claim #{claim_id} found in Finance Admin review queue.")

    print("\n==================================================")
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY [OK]")
    print("==================================================")

if __name__ == "__main__":
    run_verification()
