"""
MongoDB Database Initializer
AI-Enhanced Reimbursements Management System

Connects to MongoDB Atlas, verifies connectivity via ping command,
creates collections, and establishes required unique and performance indexes.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pymongo import ASCENDING
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
from app.config import Config
from app.db import get_client, get_db, mask_mongo_uri


def init_database(config=Config) -> bool:
    """
    Initializes MongoDB database collections and indexes.
    """
    print("=" * 65)
    print("AI-Enhanced Reimbursements System - MongoDB Initializer")
    print("=" * 65)
    masked_uri = mask_mongo_uri(config.MONGO_URI)
    print(f"Connecting to MongoDB Atlas at: {masked_uri}...")
    print(f"Target Database: {config.MONGO_DB_NAME}")

    try:
        client = get_client(config)
        # Execute ping command to verify connectivity
        client.admin.command("ping")
        print("[OK] MongoDB connection verified successfully via ping.")

        db = get_db(config)
        existing_collections = db.list_collection_names()
        print(f"Existing collections in '{config.MONGO_DB_NAME}': {existing_collections}")

        # Required collections
        required_collections = [
            "users",
            "expense_categories",
            "reimbursement_requests",
            "reimbursement_audit_logs"
        ]

        for coll_name in required_collections:
            if coll_name not in existing_collections:
                db.create_collection(coll_name)
                print(f"  + Created collection: `{coll_name}`")
            else:
                print(f"  * Collection `{coll_name}` is ready.")

        # Create required indexes
        print("\nCreating database indexes...")

        # 1. users: unique email
        db.users.create_index([("email", ASCENDING)], unique=True)
        print("  + Index created: users.email (unique)")

        # 2. expense_categories: unique name
        db.expense_categories.create_index([("name", ASCENDING)], unique=True)
        print("  + Index created: expense_categories.name (unique)")

        # 3. reimbursement_requests: employee_id, status, created_at
        db.reimbursement_requests.create_index([("employee_id", ASCENDING)])
        print("  + Index created: reimbursement_requests.employee_id")

        db.reimbursement_requests.create_index([("status", ASCENDING)])
        print("  + Index created: reimbursement_requests.status")

        db.reimbursement_requests.create_index([("created_at", ASCENDING)])
        print("  + Index created: reimbursement_requests.created_at")

        # 4. reimbursement_audit_logs: reimbursement_id
        db.reimbursement_audit_logs.create_index([("reimbursement_id", ASCENDING)])
        print("  + Index created: reimbursement_audit_logs.reimbursement_id")

        print("-" * 65)
        print(f"MongoDB database '{config.MONGO_DB_NAME}' initialized successfully!")
        print("=" * 65)
        return True

    except (ConnectionFailure, ServerSelectionTimeoutError) as err:
        print(f"\n[ERROR] Could not connect to MongoDB Atlas: {err}", file=sys.stderr)
        print("Please verify your MONGO_URI in .env and check network/IP whitelist settings in MongoDB Atlas.", file=sys.stderr)
        return False
    except PyMongoError as err:
        print(f"\n[ERROR] PyMongo operation error: {err}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)
