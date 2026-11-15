import io
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app

def run_receipt_verification():
    app = create_app()
    client = app.test_client()

    print("==================================================")
    print("STEP 1: Log in as Employee and Admin")
    print("==================================================")
    # Employee 1: john.doe@company.com (ID: 2)
    emp1_res = client.post("/api/auth/login", json={"email": "john.doe@company.com", "password": "Password@123"})
    emp1_token = emp1_res.get_json()["token"]
    emp1_headers = {"Authorization": f"Bearer {emp1_token}"}
    print("[OK] Employee 1 (John Doe) authenticated.")

    # Employee 2: jane.smith@company.com (ID: 3)
    emp2_res = client.post("/api/auth/login", json={"email": "jane.smith@company.com", "password": "Password@123"})
    emp2_token = emp2_res.get_json()["token"]
    emp2_headers = {"Authorization": f"Bearer {emp2_token}"}
    print("[OK] Employee 2 (Jane Smith) authenticated.")

    # Admin: admin@company.com (ID: 1)
    admin_res = client.post("/api/auth/login", json={"email": "admin@company.com", "password": "Password@123"})
    admin_token = admin_res.get_json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[OK] Finance Admin authenticated.")

    print("\n==================================================")
    print("STEP 2: Create Test Claims with PDF and PNG Receipts")
    print("==================================================")
    # Create Claim A with PDF
    claim_a_res = client.post("/api/reimbursements", headers=emp1_headers, json={
        "category_id": 1,
        "amount": 150.00,
        "expense_date": "2026-11-04",
        "description": "Taxi fares for client office transit"
    })
    claim_a_id = claim_a_res.get_json()["claim"]["id"]

    pdf_bytes = b"%PDF-1.5\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_pdf_res = client.post(
        f"/api/reimbursements/{claim_a_id}/upload",
        headers=emp1_headers,
        data={"file": (io.BytesIO(pdf_bytes), "taxi_invoice.pdf")},
        content_type="multipart/form-data"
    )
    assert upload_pdf_res.status_code == 200
    print(f"[OK] Claim #{claim_a_id} created with PDF receipt (taxi_invoice.pdf).")

    # Create Claim B with PNG image
    claim_b_res = client.post("/api/reimbursements", headers=emp1_headers, json={
        "category_id": 2,
        "amount": 85.50,
        "expense_date": "2026-11-04",
        "description": "Team lunch meeting receipt"
    })
    claim_b_id = claim_b_res.get_json()["claim"]["id"]

    # Valid PNG header
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    upload_png_res = client.post(
        f"/api/reimbursements/{claim_b_id}/upload",
        headers=emp1_headers,
        data={"file": (io.BytesIO(png_bytes), "lunch_receipt.png")},
        content_type="multipart/form-data"
    )
    assert upload_png_res.status_code == 200
    print(f"[OK] Claim #{claim_b_id} created with PNG receipt (lunch_receipt.png).")

    print("\n==================================================")
    print("STEP 3: Finance Admin Receipt Retrieval")
    print("==================================================")
    # Admin views Claim A (PDF)
    admin_get_pdf = client.get(f"/api/reimbursements/{claim_a_id}/bill", headers=admin_headers)
    assert admin_get_pdf.status_code == 200, f"Failed: {admin_get_pdf.data}"
    assert admin_get_pdf.headers.get("Content-Type") == "application/pdf"
    assert "inline" in admin_get_pdf.headers.get("Content-Disposition", "")
    assert len(admin_get_pdf.data) > 0
    print(f"[OK] Admin successfully fetched PDF receipt for claim #{claim_a_id}.")
    print(f"     - Content-Type: {admin_get_pdf.headers.get('Content-Type')}")
    print(f"     - Content-Disposition: {admin_get_pdf.headers.get('Content-Disposition')}")
    print(f"     - Payload size: {len(admin_get_pdf.data)} bytes")

    # Admin views Claim B (PNG)
    admin_get_png = client.get(f"/api/reimbursements/{claim_b_id}/bill", headers=admin_headers)
    assert admin_get_png.status_code == 200, f"Failed: {admin_get_png.data}"
    assert admin_get_png.headers.get("Content-Type") == "image/png"
    assert "inline" in admin_get_png.headers.get("Content-Disposition", "")
    assert len(admin_get_png.data) > 0
    print(f"[OK] Admin successfully fetched PNG receipt for claim #{claim_b_id}.")
    print(f"     - Content-Type: {admin_get_png.headers.get('Content-Type')}")
    print(f"     - Content-Disposition: {admin_get_png.headers.get('Content-Disposition')}")
    print(f"     - Payload size: {len(admin_get_png.data)} bytes")

    print("\n==================================================")
    print("STEP 4: Employee Self-Service Receipt Retrieval")
    print("==================================================")
    emp1_get_pdf = client.get(f"/api/reimbursements/{claim_a_id}/bill", headers=emp1_headers)
    assert emp1_get_pdf.status_code == 200
    assert emp1_get_pdf.headers.get("Content-Type") == "application/pdf"
    print(f"[OK] Claim owner (Employee 1) successfully retrieved their own receipt.")

    print("\n==================================================")
    print("STEP 5: Security & Access Control Verification")
    print("==================================================")
    # 5a. Unauthorized employee access (Employee 2 trying to view Employee 1's claim)
    emp2_forbidden = client.get(f"/api/reimbursements/{claim_a_id}/bill", headers=emp2_headers)
    assert emp2_forbidden.status_code == 403
    assert "Access denied" in emp2_forbidden.get_json()["error"]
    print("[OK] Access denied (HTTP 403) when another employee tries to view receipt.")

    # 5b. Unauthenticated access without token
    unauth_req = client.get(f"/api/reimbursements/{claim_a_id}/bill")
    assert unauth_req.status_code == 401
    assert "Authentication token is missing" in unauth_req.get_json()["error"]
    print("[OK] Authentication required (HTTP 401) when no Bearer token is provided.")

    # 5c. Non-existent claim
    not_found_req = client.get("/api/reimbursements/999999/bill", headers=admin_headers)
    assert not_found_req.status_code == 404
    assert "not found" in not_found_req.get_json()["error"].lower()
    print("[OK] Receipt not found (HTTP 404) for non-existent claim ID.")

    print("\n==================================================")
    print("ALL RECEIPT VIEWING CHECKS PASSED [OK]")
    print("==================================================")

if __name__ == "__main__":
    run_receipt_verification()

