import pytest


def test_unauthenticated_request_blocked(client):
    res = client.get("/api/reimbursements/my")
    assert res.status_code == 401
    assert res.get_json()["success"] is False


def test_employee_cannot_access_admin_analytics(client, employee_headers):
    res = client.get("/api/admin/analytics", headers=employee_headers)
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
    assert "Access denied" in data["error"]


def test_employee_cannot_approve_claims(client, employee_headers):
    res = client.post("/api/admin/reimbursements/1/approve", headers=employee_headers, json={"comments": "test"})
    assert res.status_code == 403
    assert res.get_json()["success"] is False


def test_employee_cannot_view_other_employees_claim(client, employee_headers, other_employee_headers):
    # John Doe (ID: 2) submits a claim
    create_res = client.post("/api/reimbursements", headers=employee_headers, json={
        "category_id": 1,
        "amount": 250.00,
        "expense_date": "2026-10-25",
        "description": "Confidential executive travel expense"
    })
    assert create_res.status_code == 201
    claim_id = create_res.get_json()["claim"]["id"]

    # John Doe can access his own claim
    own_res = client.get(f"/api/reimbursements/{claim_id}", headers=employee_headers)
    assert own_res.status_code == 200

    # Jane Smith (different employee) is forbidden from viewing John's claim
    forbidden_res = client.get(f"/api/reimbursements/{claim_id}", headers=other_employee_headers)
    assert forbidden_res.status_code == 403
    assert "you can only view your own claims" in forbidden_res.get_json()["error"]


def test_admin_can_access_all_claims(client, admin_headers):
    res = client.get("/api/admin/reimbursements", headers=admin_headers)
    assert res.status_code == 200
    assert res.get_json()["success"] is True
    assert isinstance(res.get_json()["claims"], list)

