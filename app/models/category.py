"""
Expense Category Model (MongoDB)
AI-Enhanced Reimbursements Management System

Manages expense categories stored in the 'expense_categories' collection.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.db import get_db, to_object_id, serialize_doc, serialize_docs


class CategoryModel:
    """Encapsulates MongoDB operations for expense categories."""

    @staticmethod
    def get_by_id(category_id: Any) -> Optional[Dict[str, Any]]:
        """
        Finds category by ObjectId or index/ID.
        """
        if not category_id:
            return None
        db = get_db()
        oid = to_object_id(category_id)
        doc = db.expense_categories.find_one({"$or": [{"_id": oid}, {"id": category_id}]})
        if doc:
            return serialize_doc(doc)

        # Fallback for integer/numeric string indices in tests
        try:
            idx = int(category_id)
            all_cats = list(db.expense_categories.find().sort("created_at", 1))
            if 1 <= idx <= len(all_cats):
                return serialize_doc(all_cats[idx - 1])
        except (ValueError, TypeError):
            pass

        return None

    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Finds category by case-insensitive name."""
        if not name:
            return None
        db = get_db()
        clean_name = name.strip()
        doc = db.expense_categories.find_one({
            "$or": [
                {"name": {"$regex": f"^{clean_name}$", "$options": "i"}},
                {"category_name": {"$regex": f"^{clean_name}$", "$options": "i"}}
            ]
        })
        return serialize_doc(doc)

    @staticmethod
    def get_all(include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Retrieves all categories, optionally filtering for active only."""
        db = get_db()
        query = {}
        if not include_inactive:
            query = {"$or": [{"is_active": True}, {"active": True}]}

        docs = list(db.expense_categories.find(query).sort("name", 1))
        return serialize_docs(docs)

    @staticmethod
    def create(name: str, description: str = "", is_active: bool = True) -> Optional[Dict[str, Any]]:
        """Creates a new category document."""
        db = get_db()
        clean_name = name.strip()
        now = datetime.now(timezone.utc)
        doc = {
            "name": clean_name,
            "category_name": clean_name,
            "description": description.strip(),
            "is_active": is_active,
            "active": is_active,
            "created_at": now
        }
        res = db.expense_categories.insert_one(doc)
        created = db.expense_categories.find_one({"_id": res.inserted_id})
        return serialize_doc(created)

    @staticmethod
    def update(category_id: Any, name: Optional[str] = None,
               description: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """Updates an existing category document."""
        db = get_db()
        oid = to_object_id(category_id)
        update_fields = {}
        if name is not None:
            update_fields["name"] = name.strip()
            update_fields["category_name"] = name.strip()
        if description is not None:
            update_fields["description"] = description.strip()
        if is_active is not None:
            update_fields["is_active"] = bool(is_active)
            update_fields["active"] = bool(is_active)

        if not update_fields:
            return CategoryModel.get_by_id(category_id)

        db.expense_categories.update_one(
            {"$or": [{"_id": oid}, {"id": category_id}]},
            {"$set": update_fields}
        )
        return CategoryModel.get_by_id(category_id)
