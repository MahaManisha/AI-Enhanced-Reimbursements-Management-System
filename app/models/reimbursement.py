"""
Reimbursement Model (MongoDB)
AI-Enhanced Reimbursements Management System

Manages reimbursement requests and audit logs using MongoDB collections:
- reimbursement_requests
- reimbursement_audit_logs
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.db import get_db, to_object_id, serialize_doc, serialize_docs
from app.models.user import UserModel
from app.models.category import CategoryModel


class ReimbursementModel:
    """Encapsulates MongoDB operations for reimbursement requests and audit trails."""

    @staticmethod
    def get_by_id(reimbursement_id: Any) -> Optional[Dict[str, Any]]:
        """
        Retrieves a reimbursement request by ObjectId or string/integer ID,
        populating employee and category details.
        """
        if not reimbursement_id:
            return None
        db = get_db()
        oid = to_object_id(reimbursement_id)
        doc = db.reimbursement_requests.find_one({"$or": [{"_id": oid}, {"id": reimbursement_id}]})
        if not doc:
            return None

        # Ensure employee and category metadata are fully populated
        emp = UserModel.get_by_id(doc.get("employee_id"))
        if emp:
            doc.setdefault("employee_name", emp.get("name") or emp.get("full_name"))
            doc.setdefault("employee_department", emp.get("department"))
            doc.setdefault("employee_email", emp.get("email"))

        cat = CategoryModel.get_by_id(doc.get("category_id"))
        if cat:
            doc.setdefault("category_name", cat.get("name") or cat.get("category_name"))
            doc.setdefault("category_description", cat.get("description"))

        if doc.get("reviewer_id"):
            rev = UserModel.get_by_id(doc["reviewer_id"])
            if rev:
                doc.setdefault("reviewer_name", rev.get("name") or rev.get("full_name"))
                doc.setdefault("reviewer_email", rev.get("email"))

        return serialize_doc(doc)

    @staticmethod
    def get_all_for_employee(employee_id: Any, status: Optional[str] = None,
                             category_id: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Retrieves all claims submitted by a specific employee."""
        db = get_db()
        emp_oid = to_object_id(employee_id)
        emp_str = str(employee_id)

        # Match either ObjectId or string representation of employee_id
        match_query = {
            "$or": [
                {"employee_id": emp_oid},
                {"employee_id": emp_str},
                {"employee_id": employee_id}
            ]
        }

        if status:
            st = status.strip().upper()
            match_query["$and"] = [{"$or": [{"status": st}, {"claim_status": st}]}]

        if category_id:
            cat_oid = to_object_id(category_id)
            cat_str = str(category_id)
            cat_match = {"$or": [{"category_id": cat_oid}, {"category_id": cat_str}, {"category_id": category_id}]}
            if "$and" in match_query:
                match_query["$and"].append(cat_match)
            else:
                match_query["$and"] = [cat_match]

        docs = list(db.reimbursement_requests.find(match_query).sort("created_at", -1))
        return serialize_docs(docs)

    @staticmethod
    def get_all_filtered(employee_id: Optional[Any] = None,
                         status: Optional[str] = None,
                         category_id: Optional[Any] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         min_amount: Optional[float] = None,
                         max_amount: Optional[float] = None,
                         search: Optional[str] = None,
                         risk: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves reimbursement claims with multi-criteria filtering for Finance Admins.
        Supports searching by employee name, description, category, and date ranges.
        """
        db = get_db()
        query = {}
        and_clauses = []

        if employee_id:
            emp_oid = to_object_id(employee_id)
            emp_str = str(employee_id)
            and_clauses.append({"$or": [{"employee_id": emp_oid}, {"employee_id": emp_str}, {"employee_id": employee_id}]})

        if status:
            st = status.strip().upper()
            and_clauses.append({"$or": [{"status": st}, {"claim_status": st}]})

        if category_id:
            cat_oid = to_object_id(category_id)
            cat_str = str(category_id)
            and_clauses.append({"$or": [{"category_id": cat_oid}, {"category_id": cat_str}, {"category_id": category_id}]})

        if start_date:
            and_clauses.append({"expense_date": {"$gte": start_date}})

        if end_date:
            and_clauses.append({"expense_date": {"$lte": end_date}})

        if min_amount is not None:
            and_clauses.append({"amount": {"$gte": float(min_amount)}})

        if max_amount is not None:
            and_clauses.append({"amount": {"$lte": float(max_amount)}})

        if risk:
            and_clauses.append({"ml_prediction": risk.strip().upper()})

        if search:
            pattern = {"$regex": search.strip(), "$options": "i"}
            and_clauses.append({
                "$or": [
                    {"employee_name": pattern},
                    {"description": pattern},
                    {"category_name": pattern}
                ]
            })

        if and_clauses:
            query["$and"] = and_clauses

        docs = list(db.reimbursement_requests.find(query).sort("created_at", -1))
        return serialize_docs(docs)

    @staticmethod
    def create(employee_id: Any, category_id: Any, amount: float,
               expense_date: str, description: str) -> Optional[Dict[str, Any]]:
        """
        Inserts a new reimbursement claim in PENDING status and records
        the initial CREATED entry in the reimbursement_audit_logs collection.
        """
        db = get_db()
        now = datetime.now(timezone.utc)
        emp_oid = to_object_id(employee_id)
        cat_oid = to_object_id(category_id)

        # Lookup employee and category metadata
        emp = UserModel.get_by_id(employee_id)
        emp_name = (emp.get("name") or emp.get("full_name") or "Employee") if emp else "Employee"
        emp_dept = (emp.get("department") or "General") if emp else "General"
        emp_email = (emp.get("email") or "") if emp else ""

        cat = CategoryModel.get_by_id(category_id)
        cat_name = (cat.get("name") or cat.get("category_name") or "Expense") if cat else "Expense"

        doc = {
            "employee_id": emp_oid,
            "employee_name": emp_name,
            "employee_department": emp_dept,
            "employee_email": emp_email,
            "category_id": cat_oid,
            "category_name": cat_name,
            "amount": float(amount),
            "expense_date": str(expense_date).strip(),
            "description": description.strip(),
            "receipt_filename": None,
            "receipt_path": None,
            "bill_original_name": None,
            "bill_path": None,
            "bill_available": False,
            "status": "PENDING",
            "claim_status": "PENDING",
            "ml_prediction": None,
            "ml_confidence": None,
            "ml_probabilities": None,
            "genai_observations": None,
            "ai_observations": None,
            "ai_summary": None,
            "missing_documents": None,
            "ai_missing_info": None,
            "suggested_actions": None,
            "ai_suggested_actions": None,
            "rejection_reason": None,
            "reviewer_id": None,
            "reviewer_name": None,
            "reviewer_comments": None,
            "created_at": now,
            "submitted_at": now,
            "updated_at": now
        }

        res = db.reimbursement_requests.insert_one(doc)
        claim_id = res.inserted_id

        # Log audit entry
        ReimbursementModel.log_audit(
            reimbursement_id=claim_id,
            actor_id=emp_oid,
            actor_name=emp_name,
            action="CREATED",
            previous_status=None,
            new_status="PENDING",
            comments=f"Claim submitted for ${float(amount):.2f}"
        )

        return ReimbursementModel.get_by_id(claim_id)

    @staticmethod
    def update_bill(reimbursement_id: Any, bill_path: str,
                    bill_original_name: str, actor_id: Any) -> None:
        """
        Attaches an uploaded receipt file to a claim and logs the audit event.
        """
        db = get_db()
        oid = to_object_id(reimbursement_id)
        now = datetime.now(timezone.utc)

        db.reimbursement_requests.update_one(
            {"$or": [{"_id": oid}, {"id": reimbursement_id}]},
            {
                "$set": {
                    "receipt_filename": bill_original_name,
                    "receipt_path": bill_path,
                    "bill_original_name": bill_original_name,
                    "bill_path": bill_path,
                    "bill_available": True,
                    "updated_at": now
                }
            }
        )

        emp = UserModel.get_by_id(actor_id)
        actor_name = (emp.get("name") or emp.get("full_name") or "User") if emp else "User"

        ReimbursementModel.log_audit(
            reimbursement_id=oid,
            actor_id=to_object_id(actor_id),
            actor_name=actor_name,
            action="BILL_UPLOADED",
            previous_status="PENDING",
            new_status="PENDING",
            comments=f"Attached receipt file: {bill_original_name}"
        )

    @staticmethod
    def update_ml_prediction(reimbursement_id: Any, prediction: str,
                             confidence: float, probabilities_json: Optional[Any] = None) -> None:
        """Saves Random Forest classification prediction and class probabilities."""
        db = get_db()
        oid = to_object_id(reimbursement_id)
        now = datetime.now(timezone.utc)

        db.reimbursement_requests.update_one(
            {"$or": [{"_id": oid}, {"id": reimbursement_id}]},
            {
                "$set": {
                    "ml_prediction": prediction,
                    "ml_confidence": float(confidence),
                    "ml_probabilities": probabilities_json,
                    "updated_at": now
                }
            }
        )

    @staticmethod
    def update_ai_insights(reimbursement_id: Any, summary: str,
                           observations: Any, missing_info: Any,
                           suggested_actions: Any,
                           observations_list: Optional[List[str]] = None,
                           missing_info_list: Optional[List[str]] = None,
                           suggested_actions_list: Optional[List[str]] = None,
                           ai_provider: str = "FALLBACK",
                           ai_timestamp: Optional[datetime] = None) -> None:
        """Saves Generative AI audit observations, recommendations, and execution metadata."""
        db = get_db()
        oid = to_object_id(reimbursement_id)
        now = ai_timestamp or datetime.now(timezone.utc)

        # Standardize strings and lists for dual storage
        obs_str = "\n• ".join(observations) if isinstance(observations, list) else str(observations or "")
        missing_str = "\n• ".join(missing_info) if isinstance(missing_info, list) else str(missing_info or "")
        actions_str = "\n• ".join(suggested_actions) if isinstance(suggested_actions, list) else str(suggested_actions or "")

        obs_items = observations_list if observations_list is not None else (
            observations if isinstance(observations, list) else ([obs_str] if obs_str else [])
        )
        missing_items = missing_info_list if missing_info_list is not None else (
            missing_info if isinstance(missing_info, list) else ([missing_str] if missing_str else [])
        )
        action_items = suggested_actions_list if suggested_actions_list is not None else (
            suggested_actions if isinstance(suggested_actions, list) else ([actions_str] if actions_str else [])
        )

        db.reimbursement_requests.update_one(
            {"$or": [{"_id": oid}, {"id": reimbursement_id}]},
            {
                "$set": {
                    "ai_summary": summary,
                    "genai_observations": obs_str,
                    "ai_observations": obs_str,
                    "ai_observations_list": obs_items,
                    "missing_documents": missing_str,
                    "ai_missing_info": missing_str,
                    "ai_missing_info_list": missing_items,
                    "suggested_actions": actions_str,
                    "ai_suggested_actions": actions_str,
                    "ai_suggested_actions_list": action_items,
                    "ai_provider": ai_provider,
                    "ai_source": ai_provider,
                    "ai_timestamp": now,
                    "analysis_timestamp": now,
                    "updated_at": now
                }
            }
        )

    @staticmethod
    def review(reimbursement_id: Any, reviewer_id: Any, status: str,
               comments: Optional[str] = None,
               rejection_reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Executes an approval or rejection review action by an administrator.
        Updates status, timestamps, reviewer notes, and appends an immutable audit log.
        """
        current_claim = ReimbursementModel.get_by_id(reimbursement_id)
        if not current_claim:
            return None

        old_status = current_claim.get("status") or current_claim.get("claim_status")
        now = datetime.now(timezone.utc)
        new_status = status.strip().upper()

        rev = UserModel.get_by_id(reviewer_id)
        reviewer_name = (rev.get("name") or rev.get("full_name") or "Administrator") if rev else "Administrator"

        db = get_db()
        oid = to_object_id(reimbursement_id)

        update_data = {
            "status": new_status,
            "claim_status": new_status,
            "reviewer_id": to_object_id(reviewer_id),
            "reviewer_name": reviewer_name,
            "reviewer_comments": comments,
            "rejection_reason": rejection_reason,
            "reviewed_at": now,
            "updated_at": now
        }

        db.reimbursement_requests.update_one(
            {"$or": [{"_id": oid}, {"id": reimbursement_id}]},
            {"$set": update_data}
        )

        ReimbursementModel.log_audit(
            reimbursement_id=oid,
            actor_id=to_object_id(reviewer_id),
            actor_name=reviewer_name,
            action=new_status,
            previous_status=old_status,
            new_status=new_status,
            comments=comments or rejection_reason or f"Claim marked as {new_status}"
        )

        return ReimbursementModel.get_by_id(reimbursement_id)

    @staticmethod
    def log_audit(reimbursement_id: Any, actor_id: Any, action: str,
                  previous_status: Optional[str] = None, new_status: Optional[str] = None,
                  comments: Optional[str] = None, actor_name: Optional[str] = None) -> None:
        """Appends an immutable audit record to the reimbursement_audit_logs collection."""
        db = get_db()
        now = datetime.now(timezone.utc)

        if not actor_name and actor_id:
            user = UserModel.get_by_id(actor_id)
            if user:
                actor_name = user.get("name") or user.get("full_name")

        doc = {
            "reimbursement_id": to_object_id(reimbursement_id),
            "actor_id": to_object_id(actor_id),
            "actor_name": actor_name or "System",
            "action": action.strip().upper(),
            "previous_status": previous_status,
            "old_status": previous_status,
            "new_status": new_status,
            "comments": comments,
            "created_at": now
        }
        db.reimbursement_audit_logs.insert_one(doc)

    @staticmethod
    def get_audit_logs(reimbursement_id: Any) -> List[Dict[str, Any]]:
        """Retrieves chronological audit history for a given reimbursement request."""
        db = get_db()
        oid = to_object_id(reimbursement_id)
        reimb_str = str(reimbursement_id)

        docs = list(db.reimbursement_audit_logs.find({
            "$or": [
                {"reimbursement_id": oid},
                {"reimbursement_id": reimb_str},
                {"reimbursement_id": reimbursement_id}
            ]
        }).sort("created_at", 1))

        serialized = []
        for d in docs:
            s = serialize_doc(d)
            if s.get("actor_id"):
                user = UserModel.get_by_id(s["actor_id"])
                s["actor_role"] = user.get("role", "USER") if user else "USER"
            else:
                s["actor_role"] = "SYSTEM"
            serialized.append(s)

        return serialized
