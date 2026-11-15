"""
Comprehensive MongoDB Data Inspector
AI-Enhanced Reimbursements Management System
"""

import sys
from pathlib import Path
from bson import json_util

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import get_db

def inspect_all():
    db = get_db()

    print("==================================================================")
    print("MONGODB DATABASE CONTENT INSPECTION")
    print("==================================================================")

    # 1. Users
    users = list(db.users.find())
    print(f"\n--- USERS ({len(users)} total) ---")
    for u in users:
        uid = str(u["_id"])
        name = u.get("name") or u.get("full_name")
        email = u.get("email")
        role = u.get("role")
        dept = u.get("department")
        print(f"[{uid}] {name:<25} | {email:<35} | Role: {role:<8} | Dept: {dept}")

    # 2. Categories
    cats = list(db.expense_categories.find())
    print(f"\n--- EXPENSE CATEGORIES ({len(cats)} total) ---")
    for c in cats:
        cid = str(c["_id"])
        cname = c.get("name") or c.get("category_name")
        active = c.get("is_active", c.get("active"))
        desc = c.get("description", "")
        print(f"[{cid}] {cname:<30} | Active: {active} | {desc}")

    # 3. Claims
    claims = list(db.reimbursement_requests.find())
    print(f"\n--- REIMBURSEMENT REQUESTS ({len(claims)} total) ---")
    for r in claims:
        rid = str(r["_id"])
        ename = r.get("employee_name")
        cname = r.get("category_name")
        amt = r.get("amount")
        dt = r.get("expense_date")
        desc = (r.get("description") or "")[:40]
        status = r.get("status") or r.get("claim_status")
        bill = r.get("receipt_filename") or r.get("bill_original_name")
        ml = r.get("ml_prediction")
        print(f"[{rid}] {ename:<20} | ${amt:<8} | {dt} | {cname:<25} | Status: {status:<8} | Bill: {bill} | Desc: {desc}")

    # 4. Audit Logs
    logs = list(db.reimbursement_audit_logs.find())
    print(f"\n--- AUDIT LOGS ({len(logs)} total) ---")
    for l in logs:
        lid = str(l["_id"])
        claim_ref = str(l.get("reimbursement_id"))
        actor = l.get("actor_name")
        action = l.get("action")
        comments = (l.get("comments") or "")[:35]
        print(f"[{lid}] Claim: {claim_ref} | Actor: {actor:<20} | Action: {action:<14} | Comments: {comments}")

    print("==================================================================")

if __name__ == "__main__":
    inspect_all()

