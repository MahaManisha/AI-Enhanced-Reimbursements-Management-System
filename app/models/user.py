"""
User Model (MongoDB)
AI-Enhanced Reimbursements Management System

Manages user authentication records, registration, and role queries
using the MongoDB 'users' collection.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.db import get_db, to_object_id, serialize_doc, serialize_docs
from app.utils.auth_utils import hash_password


class UserModel:
    """Encapsulates MongoDB operations for the users collection."""

    @staticmethod
    def get_by_id(user_id: Any) -> Optional[Dict[str, Any]]:
        """
        Retrieves a user document by ObjectId or string/integer ID.
        """
        if not user_id:
            return None
        db = get_db()
        oid = to_object_id(user_id)
        doc = db.users.find_one({"$or": [{"_id": oid}, {"id": user_id}]})
        return serialize_doc(doc)

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a user document by case-insensitive email, including password_hash.
        """
        if not email:
            return None
        db = get_db()
        clean_email = email.strip().lower()
        doc = db.users.find_one({"email": clean_email})
        return serialize_doc(doc)

    @staticmethod
    def create(full_name: str, email: str, plain_password: str,
               role: str = "EMPLOYEE", department: str = "") -> Optional[Dict[str, Any]]:
        """
        Creates a new user document in MongoDB with a hashed password.
        Returns the newly created user document.
        """
        db = get_db()
        pw_hash = hash_password(plain_password)
        now = datetime.now(timezone.utc)
        clean_name = full_name.strip()
        clean_email = email.strip().lower()

        doc = {
            "name": clean_name,
            "full_name": clean_name,
            "email": clean_email,
            "password_hash": pw_hash,
            "role": role.strip().upper(),
            "department": department.strip(),
            "created_at": now,
            "updated_at": now
        }
        res = db.users.insert_one(doc)
        created_doc = db.users.find_one({"_id": res.inserted_id})
        return serialize_doc(created_doc)

    @staticmethod
    def get_all(role: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all users from MongoDB, optionally filtered by role.
        """
        db = get_db()
        query = {}
        if role:
            query["role"] = role.strip().upper()

        docs = list(db.users.find(query).sort("name", 1))
        return serialize_docs(docs)
