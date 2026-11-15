"""
Pytest Test Fixtures (MongoDB)
AI-Enhanced Reimbursements Management System

Configures isolated test database environment, seeds baseline test users/categories,
cleans up test artifacts, and provides pre-authorized JWT tokens for test cases.
"""

import os
import pytest
from bson import ObjectId
from app import create_app
from app.config import TestConfig
from app.db import get_db, init_db
from app.models.user import UserModel
from app.utils.auth_utils import generate_jwt_token
from scripts.seed_db import seed_database


@pytest.fixture(scope="session", autouse=True)
def clean_test_claims(app):
    """
    Session-wide fixture that tracks existing claims, users, and categories,
    and cleans up only transient records created during the test run.
    """
    with app.app_context():
        db = get_db()
        initial_claim_ids = {str(r["_id"]) for r in db.reimbursement_requests.find({}, {"_id": 1})}
        initial_user_ids = {str(u["_id"]) for u in db.users.find({}, {"_id": 1})}
        initial_cat_ids = {str(c["_id"]) for c in db.expense_categories.find({}, {"_id": 1})}
        yield
        current_claim_ids = {str(r["_id"]) for r in db.reimbursement_requests.find({}, {"_id": 1})}
        created_test_claim_ids = current_claim_ids - initial_claim_ids
        if created_test_claim_ids:
            oids = [ObjectId(cid) for cid in created_test_claim_ids if ObjectId.is_valid(cid)]
            db.reimbursement_requests.delete_many({"_id": {"$in": oids}})
            db.reimbursement_audit_logs.delete_many({
                "$or": [
                    {"reimbursement_id": {"$in": oids}},
                    {"reimbursement_id": {"$in": list(created_test_claim_ids)}}
                ]
            })

        current_user_ids = {str(u["_id"]) for u in db.users.find({}, {"_id": 1})}
        created_test_user_ids = current_user_ids - initial_user_ids
        if created_test_user_ids:
            oids = [ObjectId(uid) for uid in created_test_user_ids if ObjectId.is_valid(uid)]
            db.users.delete_many({"_id": {"$in": oids}})

        current_cat_ids = {str(c["_id"]) for c in db.expense_categories.find({}, {"_id": 1})}
        created_test_cat_ids = current_cat_ids - initial_cat_ids
        if created_test_cat_ids:
            oids = [ObjectId(cid) for cid in created_test_cat_ids if ObjectId.is_valid(cid)]
            db.expense_categories.delete_many({"_id": {"$in": oids}})


@pytest.fixture(scope="session")
def app():
    """Initializes Flask application under TestConfig with seeded MongoDB test database."""
    os.environ["FLASK_ENV"] = "testing"
    application = create_app(TestConfig)
    application.config["TESTING"] = True

    with application.app_context():
        init_db(TestConfig)
        seed_database(TestConfig)

    yield application


@pytest.fixture
def client(app):
    """Provides Flask test HTTP client."""
    return app.test_client()


@pytest.fixture
def employee_token(app):
    """Generates valid JWT bearer token for demo employee John Doe."""
    with app.app_context():
        user = UserModel.get_by_email("john.doe@company.com")
        user_id = user["id"] if user else "2"
        return generate_jwt_token(user_id=user_id, role="EMPLOYEE", email="john.doe@company.com")


@pytest.fixture
def other_employee_token(app):
    """Generates valid JWT bearer token for demo employee Jane Smith."""
    with app.app_context():
        user = UserModel.get_by_email("jane.smith@company.com")
        user_id = user["id"] if user else "3"
        return generate_jwt_token(user_id=user_id, role="EMPLOYEE", email="jane.smith@company.com")


@pytest.fixture
def admin_token(app):
    """Generates valid JWT bearer token for demo Finance Administrator."""
    with app.app_context():
        user = UserModel.get_by_email("admin@company.com")
        user_id = user["id"] if user else "1"
        return generate_jwt_token(user_id=user_id, role="ADMIN", email="admin@company.com")


@pytest.fixture
def employee_headers(employee_token):
    return {"Authorization": f"Bearer {employee_token}"}


@pytest.fixture
def other_employee_headers(other_employee_token):
    return {"Authorization": f"Bearer {other_employee_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
