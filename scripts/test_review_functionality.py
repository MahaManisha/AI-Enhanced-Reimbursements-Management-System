"""
Verification script for Review Button and Admin Claim Details API
AI-Enhanced Reimbursements Management System
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app

def test_review_details():
    app = create_app()
    client = app.test_client()

    # 1. Login as Admin
    login_res = client.post("/api/auth/login", json={
        "email": "admin@company.com",
        "password": "Password@123"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.data}"
    token = login_res.get_json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get list of claims
    list_res = client.get("/api/admin/reimbursements", headers=headers)
    assert list_res.status_code == 200
    claims = list_res.get_json().get("claims", [])
    print(f"[OK] Admin claims returned: {len(claims)}")
    assert len(claims) > 0, "No claims found in database to review"

    sample_claim = claims[0]
    sample_id = sample_claim["id"]
    print(f"[OK] Testing review detail for Claim #{sample_id}")

    # 3. Fetch single claim detail (the exact endpoint openReviewModal calls)
    detail_res = client.get(f"/api/admin/reimbursements/{sample_id}", headers=headers)
    assert detail_res.status_code == 200, f"Detail fetch failed: {detail_res.data}"
    data = detail_res.get_json()
    assert data["success"] is True

    c = data["claim"]
    print("\nVerified Claim Fields:")
    print(f"  * ID                   : {c.get('id')}")
    print(f"  * Employee Name        : {c.get('employee_name')}")
    print(f"  * Employee Department  : {c.get('employee_department')}")
    print(f"  * Expense Category     : {c.get('category_name')}")
    print(f"  * Amount               : ${c.get('amount')}")
    print(f"  * Expense Date         : {c.get('expense_date')}")
    print(f"  * Description          : {c.get('description')}")
    print(f"  * Receipt Available    : {c.get('bill_available')}")
    print(f"  * Receipt Filename     : {c.get('bill_original_name') or c.get('receipt_filename')}")
    print(f"  * ML Prediction        : {c.get('ml_prediction')}")
    print(f"  * ML Confidence        : {c.get('ml_confidence')}")
    print(f"  * ML Probabilities     : {c.get('ml_probabilities')}")
    print(f"  * GenAI Observations   : {c.get('ai_observations') or c.get('genai_observations')}")
    print(f"  * Missing Documents    : {c.get('ai_missing_info') or c.get('missing_documents')}")
    print(f"  * Suggested Actions    : {c.get('ai_suggested_actions') or c.get('suggested_actions')}")
    print(f"  * Audit Logs           : {len(data.get('audit_logs', []))} entries")

    assert c.get("id") is not None
    assert c.get("employee_name") is not None
    assert c.get("category_name") is not None
    assert c.get("amount") is not None
    print("\n[SUCCESS] Review endpoint and claim payload verified successfully!")

if __name__ == "__main__":
    test_review_details()

