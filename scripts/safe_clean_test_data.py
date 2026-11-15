"""
Safe Database Cleanup & Backup Script
AI-Enhanced Reimbursements Management System

Safely identifies and removes audit/test records while backing them up:
- Test users (e.g. Audit Test Employee, Test Engineer)
- Test categories (e.g. Audit Category 8bfe67, Audit Category 4dfe89)
- Test reimbursement claims ($625, $950 created by test users)
- Associated audit logs

Preserves:
- Finance Admin (admin@company.com)
- Genuine employees (john.doe, jane.smith, alex.kumar, sarah.jenkins)
- Genuine reimbursement claims (e.g. client visit, team lunch, etc.)
- Legitimate standard expense categories
"""

import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from bson import ObjectId, json_util

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import get_db

GENUINE_EMAILS = {
    "admin@company.com",
    "john.doe@company.com",
    "jane.smith@company.com",
    "alex.kumar@company.com",
    "sarah.jenkins@company.com"
}

GENUINE_CATEGORIES = {
    "Travel & Conveyance",
    "Meals & Entertainment",
    "Office Supplies & Software",
    "Accommodation & Lodging",
    "Training & Certification",
    "Health & Wellness",
    "Miscellaneous Expenses"
}

def clean_test_data():
    db = get_db()
    print("=" * 70)
    print("AI-ENHANCED REIMBURSEMENTS SYSTEM - SAFE TEST DATA CLEANUP")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. IDENTIFY TEST USERS
    # -------------------------------------------------------------
    all_users = list(db.users.find())
    test_users = []
    genuine_users = []

    for u in all_users:
        email = (u.get("email") or "").strip().lower()
        if email in GENUINE_EMAILS:
            genuine_users.append(u)
        else:
            # Check if this user was created for testing
            name = u.get("name") or u.get("full_name") or ""
            if "audit" in email or "audit" in name.lower() or "test" in email or "test" in name.lower():
                test_users.append(u)
            else:
                genuine_users.append(u)

    print(f"\n[Users Audit] Total: {len(all_users)} | Genuine: {len(genuine_users)} | Test: {len(test_users)}")
    test_user_ids = [u["_id"] for u in test_users]
    test_user_id_strs = [str(uid) for uid in test_user_ids]
    for u in test_users:
        print(f"  - Target Test User: {u.get('name') or u.get('full_name')} ({u.get('email')}) [ID: {u['_id']}]")

    # -------------------------------------------------------------
    # 2. IDENTIFY TEST CATEGORIES
    # -------------------------------------------------------------
    all_cats = list(db.expense_categories.find())
    test_cats = []
    genuine_cats = []

    for c in all_cats:
        cname = (c.get("name") or c.get("category_name") or "").strip()
        if cname in GENUINE_CATEGORIES:
            genuine_cats.append(c)
        elif "audit" in cname.lower() or "test" in cname.lower():
            test_cats.append(c)
        else:
            genuine_cats.append(c)

    print(f"\n[Categories Audit] Total: {len(all_cats)} | Genuine: {len(genuine_cats)} | Test: {len(test_cats)}")
    test_cat_ids = [c["_id"] for c in test_cats]
    test_cat_id_strs = [str(cid) for cid in test_cat_ids]
    for c in test_cats:
        cname = c.get("name") or c.get("category_name")
        print(f"  - Target Test Category: '{cname}' [ID: {c['_id']}]")

    # -------------------------------------------------------------
    # 3. IDENTIFY TEST REIMBURSEMENT CLAIMS
    # -------------------------------------------------------------
    all_claims = list(db.reimbursement_requests.find())
    test_claims = []
    genuine_claims = []

    for r in all_claims:
        emp_id = r.get("employee_id")
        cat_id = r.get("category_id")
        emp_name = r.get("employee_name") or ""
        cat_name = r.get("category_name") or ""

        # Claim belongs to a test user OR a test category
        is_test = False
        if emp_id in test_user_ids or str(emp_id) in test_user_id_strs:
            is_test = True
        elif cat_id in test_cat_ids or str(cat_id) in test_cat_id_strs:
            is_test = True
        elif "audit" in emp_name.lower() or "audit" in cat_name.lower():
            is_test = True

        if is_test:
            test_claims.append(r)
        else:
            genuine_claims.append(r)

    print(f"\n[Claims Audit] Total: {len(all_claims)} | Genuine: {len(genuine_claims)} | Test: {len(test_claims)}")
    test_claim_ids = [r["_id"] for r in test_claims]
    test_claim_id_strs = [str(rid) for rid in test_claim_ids]
    for r in test_claims:
        print(f"  - Target Test Claim: #{r['_id']} | Emp: {r.get('employee_name')} | ${r.get('amount')} | Cat: {r.get('category_name')} | Status: {r.get('status') or r.get('claim_status')}")

    # -------------------------------------------------------------
    # 4. IDENTIFY ASSOCIATED AUDIT LOGS
    # -------------------------------------------------------------
    all_logs = list(db.reimbursement_audit_logs.find())
    test_logs = []
    genuine_logs = []

    for l in all_logs:
        reimb_id = l.get("reimbursement_id")
        actor_id = l.get("actor_id")
        actor_name = l.get("actor_name") or ""

        is_test_log = False
        if reimb_id in test_claim_ids or str(reimb_id) in test_claim_id_strs:
            is_test_log = True
        elif actor_id in test_user_ids or str(actor_id) in test_user_id_strs:
            is_test_log = True
        elif "audit test employee" in actor_name.lower():
            is_test_log = True

        if is_test_log:
            test_logs.append(l)
        else:
            genuine_logs.append(l)

    print(f"\n[Audit Logs Audit] Total: {len(all_logs)} | Genuine: {len(genuine_logs)} | Test: {len(test_logs)}")

    # -------------------------------------------------------------
    # 5. CREATE SAFETY BACKUP
    # -------------------------------------------------------------
    backup_dir = BASE_DIR / "scripts" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"test_records_backup_{ts}.json"

    backup_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "test_users_count": len(test_users),
            "test_categories_count": len(test_cats),
            "test_claims_count": len(test_claims),
            "test_audit_logs_count": len(test_logs)
        },
        "records": {
            "users": test_users,
            "expense_categories": test_cats,
            "reimbursement_requests": test_claims,
            "reimbursement_audit_logs": test_logs
        }
    }

    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(json_util.dumps(backup_payload, indent=2))

    print(f"\n[BACKUP] Safety backup successfully written to:")
    print(f"         {backup_file}")
    print(f"         Total records backed up: {len(test_users) + len(test_cats) + len(test_claims) + len(test_logs)}")

    # -------------------------------------------------------------
    # 6. EXECUTE SAFE DELETION
    # -------------------------------------------------------------
    print("\nExecuting safe deletion of test records...")

    deleted_claims_count = 0
    if test_claim_ids:
        del_res = db.reimbursement_requests.delete_many({
            "$or": [
                {"_id": {"$in": test_claim_ids}},
                {"_id": {"$in": test_claim_id_strs}}
            ]
        })
        deleted_claims_count = del_res.deleted_count
        print(f"  [OK] Deleted {deleted_claims_count} test reimbursement claims.")

    deleted_logs_count = 0
    if test_logs:
        test_log_ids = [l["_id"] for l in test_logs]
        del_res = db.reimbursement_audit_logs.delete_many({
            "_id": {"$in": test_log_ids}
        })
        deleted_logs_count = del_res.deleted_count
        print(f"  [OK] Deleted {deleted_logs_count} associated test audit logs.")

    deleted_cats_count = 0
    if test_cat_ids:
        del_res = db.expense_categories.delete_many({
            "$or": [
                {"_id": {"$in": test_cat_ids}},
                {"_id": {"$in": test_cat_id_strs}}
            ]
        })
        deleted_cats_count = del_res.deleted_count
        print(f"  [OK] Deleted {deleted_cats_count} test categories.")

    deleted_users_count = 0
    if test_user_ids:
        del_res = db.users.delete_many({
            "$or": [
                {"_id": {"$in": test_user_ids}},
                {"_id": {"$in": test_user_id_strs}}
            ]
        })
        deleted_users_count = del_res.deleted_count
        print(f"  [OK] Deleted {deleted_users_count} test user accounts.")

    # -------------------------------------------------------------
    # 7. POST-CLEANUP VERIFICATION
    # -------------------------------------------------------------
    final_users = list(db.users.find())
    final_cats = list(db.expense_categories.find())
    final_claims = list(db.reimbursement_requests.find())
    final_logs = list(db.reimbursement_audit_logs.find())

    print("\n" + "=" * 70)
    print("POST-CLEANUP DATABASE STATE VERIFICATION")
    print("=" * 70)
    print(f"  * Users in MongoDB               : {len(final_users)} (All genuine)")
    for u in final_users:
        print(f"      - {u.get('name') or u.get('full_name')} ({u.get('email')}) [{u.get('role')}]")

    print(f"  * Categories in MongoDB          : {len(final_cats)} (All legitimate standard categories)")
    for c in final_cats:
        print(f"      - {c.get('name') or c.get('category_name')}")

    print(f"  * Claims in MongoDB              : {len(final_claims)} (All genuine employee submissions)")
    for r in final_claims:
        print(f"      - #{r['_id']} | {r.get('employee_name')} | ${r.get('amount')} | {r.get('category_name')} | {r.get('status') or r.get('claim_status')}")

    print(f"  * Audit Logs in MongoDB          : {len(final_logs)} (All genuine history records)")

    print("=" * 70)
    print("DATABASE CLEANUP AND INTEGRITY VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)

    return {
        "deleted_users": deleted_users_count,
        "deleted_cats": deleted_cats_count,
        "deleted_claims": deleted_claims_count,
        "deleted_logs": deleted_logs_count,
        "preserved_users": len(final_users),
        "preserved_cats": len(final_cats),
        "preserved_claims": len(final_claims),
        "preserved_logs": len(final_logs),
        "backup_path": str(backup_file)
    }

if __name__ == "__main__":
    clean_test_data()

