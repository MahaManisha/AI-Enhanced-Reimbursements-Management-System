"""
MongoDB Database Seeder
AI-Enhanced Reimbursements Management System

Seeds baseline expense categories and verified corporate demo accounts
into MongoDB Atlas without overwriting or duplicating existing records.
"""

from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from werkzeug.security import generate_password_hash
from app.config import Config
from app.db import get_client, get_db, mask_mongo_uri

CATEGORIES = [
    ("Travel & Conveyance", "Flights, trains, cabs, and transit expenses for business trips", True),
    ("Meals & Entertainment", "Client dinners, team meals, and official business food expenses", True),
    ("Office Supplies & Software", "Hardware peripherals, software subscriptions, office supplies", True),
    ("Accommodation & Lodging", "Hotel accommodations and temporary stays during official travel", True),
    ("Training & Certification", "Courses, technical certifications, books, and conference passes", True),
    ("Health & Wellness", "Workplace wellness, health checks, and ergonomic items", True),
    ("Miscellaneous Expenses", "Ad-hoc operational expenses with required receipts", True),
]

USERS = [
    ("Finance Admin", "admin@company.com", "Password@123", "ADMIN", "Finance & Accounts"),
    ("John Doe", "john.doe@company.com", "Password@123", "EMPLOYEE", "Engineering"),
    ("Jane Smith", "jane.smith@company.com", "Password@123", "EMPLOYEE", "Marketing"),
    ("Alex Kumar", "alex.kumar@company.com", "Password@123", "EMPLOYEE", "Sales & BD"),
    ("Sarah Jenkins", "sarah.jenkins@company.com", "Password@123", "EMPLOYEE", "Human Resources"),
]


def seed_database(config=Config) -> bool:
    """
    Seeds baseline expense categories and demo users into MongoDB.
    """
    print("=" * 65)
    print("AI-Enhanced Reimbursements System - MongoDB Database Seeder")
    print("=" * 65)
    masked_uri = mask_mongo_uri(config.MONGO_URI)
    print(f"Connecting to MongoDB at: {masked_uri}...")

    try:
        client = get_client(config)
        client.admin.command("ping")
        db = get_db(config)
        now = datetime.now(timezone.utc)

        # 1. Seed Expense Categories
        print("\nSeeding Expense Categories...")
        cat_count = 0
        for name, desc, is_active in CATEGORIES:
            existing = db.expense_categories.find_one({
                "$or": [{"name": name}, {"category_name": name}]
            })
            if not existing:
                cat_count += 1
                doc = {
                    "id": cat_count,
                    "name": name,
                    "category_name": name,
                    "description": desc,
                    "is_active": is_active,
                    "active": is_active,
                    "created_at": now
                }
                res = db.expense_categories.insert_one(doc)
                print(f"  + Added Category: '{name}' (ID: {res.inserted_id})")
            else:
                print(f"  * Category '{name}' already exists.")

        # 2. Seed Corporate Demo Users
        print("\nSeeding Corporate Demo Users...")
        user_count = 0
        for full_name, email, plain_pw, role, dept in USERS:
            clean_email = email.strip().lower()
            existing = db.users.find_one({"email": clean_email})
            user_count += 1
            if not existing:
                pw_hash = generate_password_hash(plain_pw, method="scrypt")
                doc = {
                    "id": user_count,
                    "name": full_name,
                    "full_name": full_name,
                    "email": clean_email,
                    "password_hash": pw_hash,
                    "role": role,
                    "department": dept,
                    "created_at": now,
                    "updated_at": now
                }
                res = db.users.insert_one(doc)
                print(f"  + Created User: {full_name} ({clean_email}) [Role: {role}] (ID: {res.inserted_id})")
            else:
                print(f"  * User '{clean_email}' already exists.")

        print("-" * 65)
        print("Database seeding completed successfully.")
        print("=" * 65)
        return True

    except Exception as err:
        print(f"\n[ERROR] Database seeding failed: {err}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = seed_database()
    if not success:
        sys.exit(1)
