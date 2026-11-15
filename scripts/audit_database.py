"""
MongoDB Database Audit Inspector
AI-Enhanced Reimbursements Management System

Inspects MongoDB collections, document counts, indexes, and sample documents.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import get_db, mask_mongo_uri
from app.config import Config


def audit():
    print("=" * 65)
    print("AI-Enhanced Reimbursements System - MongoDB Database Audit")
    print("=" * 65)
    print(f"Connecting to MongoDB at: {mask_mongo_uri(Config.MONGO_URI)}")
    print(f"Database: {Config.MONGO_DB_NAME}\n")

    db = get_db()
    collections = db.list_collection_names()
    print("=== COLLECTIONS IN DATABASE ===")
    for coll_name in sorted(collections):
        count = db[coll_name].count_documents({})
        print(f"Collection: {coll_name:<28} Document count: {count}")

    print("\n=== INDEXES BY COLLECTION ===")
    for coll_name in sorted(collections):
        print(f"Collection: {coll_name}")
        for idx in db[coll_name].list_indexes():
            keys = ", ".join([f"{k}:{v}" for k, v in idx.get("key", {}).items()])
            unique = idx.get("unique", False)
            print(f"  - Index '{idx.get('name')}': ({keys}) [unique={unique}]")

    print("\n=== USERS (SAMPLE) ===")
    for u in db.users.find().limit(5):
        name = u.get("name") or u.get("full_name")
        print(f"User: {name:<18} | Email: {u.get('email'):<24} | Role: {u.get('role')} | Dept: {u.get('department')}")

    print("\n=== EXPENSE CATEGORIES ===")
    for c in db.expense_categories.find().limit(10):
        name = c.get("name") or c.get("category_name")
        active = c.get("is_active") or c.get("active")
        print(f"Category: {name:<28} | Active: {active}")

    print("\n=== REIMBURSEMENTS SUMMARY ===")
    for r in db.reimbursement_requests.find().limit(5):
        status = r.get("status") or r.get("claim_status")
        bill = bool(r.get("receipt_path") or r.get("bill_path"))
        print(f"Claim #{r.get('_id')}: Emp: {r.get('employee_name')} | ${r.get('amount'):.2f} | Status: {status} | Bill: {bill} | ML: {r.get('ml_prediction')}")

    print("\n=== AUDIT LOGS (SAMPLE) ===")
    for l in db.reimbursement_audit_logs.find().limit(5):
        print(f"Log #{l.get('_id')}: Claim #{l.get('reimbursement_id')} | Actor: {l.get('actor_name')} | Action: {l.get('action')} | Time: {l.get('created_at')}")

    print("=" * 65)


if __name__ == "__main__":
    audit()
