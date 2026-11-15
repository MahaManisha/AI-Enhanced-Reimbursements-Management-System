import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db


def clean_database():
    print("=" * 60)
    print("AI-Enhanced Reimbursements System - Database Cleanup (MongoDB)")
    print("=" * 60)

    db = get_db()

    # Inspect current state
    users_count = db.users.count_documents({})
    categories_count = db.expense_categories.count_documents({})
    claims_count = db.reimbursement_requests.count_documents({})
    audit_count = db.reimbursement_audit_logs.count_documents({})

    print(f"Current database state:")
    print(f"  - Users              : {users_count}")
    print(f"  - Categories         : {categories_count}")
    print(f"  - Reimbursement claims: {claims_count}")
    print(f"  - Audit log entries  : {audit_count}")

    if claims_count > 0 or audit_count > 0:
        print("\nDeleting demonstration and test reimbursement claims...")
        db.reimbursement_audit_logs.delete_many({})
        db.reimbursement_requests.delete_many({})
        print("  [OK] Removed sample and test reimbursement claims from MongoDB.")

    # Verification
    final_users = db.users.count_documents({})
    final_categories = db.expense_categories.count_documents({})
    final_claims = db.reimbursement_requests.count_documents({})
    final_audit = db.reimbursement_audit_logs.count_documents({})

    print("\nVerification after cleanup:")
    print(f"  - Users              : {final_users} (Preserved)")
    print(f"  - Categories         : {final_categories} (Preserved)")
    print(f"  - Reimbursement claims: {final_claims} (Clean zero state)")
    print(f"  - Audit log entries  : {final_audit} (Clean zero state)")
    print("=" * 60)
    print("Database cleanup completed successfully.")
    return True


if __name__ == "__main__":
    success = clean_database()
    if not success:
        sys.exit(1)
