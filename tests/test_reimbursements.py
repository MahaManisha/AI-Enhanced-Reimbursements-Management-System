import io


def test_claim_creation_success(client, employee_headers):
    payload = {
        "category_id": 1,
        "amount": 750.50,
        "expense_date": "2026-10-24",
        "description": "Transit and fuel reimbursement for on-site client audit."
    }
    res = client.post("/api/reimbursements", headers=employee_headers, json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert float(data["claim"]["amount"]) == 750.50
    assert data["claim"]["claim_status"] == "PENDING"
    assert "ml_prediction" in data


def test_claim_validation_negative_amount(client, employee_headers):
    payload = {
        "category_id": 1,
        "amount": -50.00,
        "expense_date": "2026-10-24",
        "description": "Invalid negative amount expense"
    }
    res = client.post("/api/reimbursements", headers=employee_headers, json=payload)
    assert res.status_code == 400
    assert "greater than 0" in res.get_json()["error"]


def test_claim_validation_future_date(client, employee_headers):
    payload = {
        "category_id": 1,
        "amount": 100.00,
        "expense_date": "2099-01-01",
        "description": "Future date attempt"
    }
    res = client.post("/api/reimbursements", headers=employee_headers, json=payload)
    assert res.status_code == 400
    assert "cannot be in the future" in res.get_json()["error"]


def test_claim_validation_short_description(client, employee_headers):
    payload = {
        "category_id": 1,
        "amount": 100.00,
        "expense_date": "2026-10-20",
        "description": "hi"
    }
    res = client.post("/api/reimbursements", headers=employee_headers, json=payload)
    assert res.status_code == 400
    assert "minimum 5 characters" in res.get_json()["error"]


def test_upload_receipt_valid_pdf(client, employee_headers):
    create_res = client.post("/api/reimbursements", headers=employee_headers, json={
        "category_id": 2,
        "amount": 120.00,
        "expense_date": "2026-10-22",
        "description": "Team lunch meeting with vendor"
    })
    claim_id = create_res.get_json()["claim"]["id"]

    pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    data = {
        "file": (io.BytesIO(pdf_content), "team_lunch_receipt.pdf")
    }
    upload_res = client.post(
        f"/api/reimbursements/{claim_id}/upload",
        headers=employee_headers,
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 200
    assert upload_res.get_json()["success"] is True
    assert upload_res.get_json()["claim"]["bill_available"] == 1


def test_upload_receipt_invalid_extension_blocked(client, employee_headers):
    create_res = client.post("/api/reimbursements", headers=employee_headers, json={
        "category_id": 2,
        "amount": 120.00,
        "expense_date": "2026-10-22",
        "description": "Team lunch meeting with vendor"
    })
    claim_id = create_res.get_json()["claim"]["id"]

    exe_content = b"MZ\x90\x00\x03\x00\x00\x00"
    data = {
        "file": (io.BytesIO(exe_content), "malware.exe")
    }
    upload_res = client.post(
        f"/api/reimbursements/{claim_id}/upload",
        headers=employee_headers,
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 400
    assert "Unsupported file extension" in upload_res.get_json()["error"]


def test_admin_approve_and_audit_log(client, employee_headers, admin_headers):
    create_res = client.post("/api/reimbursements", headers=employee_headers, json={
        "category_id": 3,
        "amount": 450.00,
        "expense_date": "2026-10-21",
        "description": "Monitor stand and ergonomic accessories"
    })
    claim_id = create_res.get_json()["claim"]["id"]

    approve_res = client.post(
        f"/api/admin/reimbursements/{claim_id}/approve",
        headers=admin_headers,
        json={"comments": "Approved per workplace ergonomics allowance."}
    )
    assert approve_res.status_code == 200
    assert approve_res.get_json()["claim"]["claim_status"] == "APPROVED"

    detail_res = client.get(f"/api/reimbursements/{claim_id}", headers=employee_headers)
    logs = detail_res.get_json()["audit_logs"]
    actions = [l["action"] for l in logs]
    assert "CREATED" in actions
    assert "APPROVED" in actions


def test_admin_reject_requires_reason(client, employee_headers, admin_headers):
    create_res = client.post("/api/reimbursements", headers=employee_headers, json={
        "category_id": 7,
        "amount": 350.00,
        "expense_date": "2026-10-21",
        "description": "Personal items claim"
    })
    claim_id = create_res.get_json()["claim"]["id"]

    fail_res = client.post(
        f"/api/admin/reimbursements/{claim_id}/reject",
        headers=admin_headers,
        json={"rejection_reason": ""}
    )
    assert fail_res.status_code == 400
    assert "rejection reason is mandatory" in fail_res.get_json()["error"]

    success_res = client.post(
        f"/api/admin/reimbursements/{claim_id}/reject",
        headers=admin_headers,
        json={"rejection_reason": "Personal items are strictly non-reimbursable under corporate expense guidelines."}
    )
    assert success_res.status_code == 200
    assert success_res.get_json()["claim"]["claim_status"] == "REJECTED"
