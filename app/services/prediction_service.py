"""
Machine Learning Prediction Service (MongoDB)
AI-Enhanced Reimbursements Management System

Loads the trained Random Forest Classifier pipeline and computes risk predictions
(LIKELY_APPROVED, REQUIRES_REVIEW, HIGH_REJECTION_RISK) along with class probabilities.
Queries employee historical claims directly from MongoDB.
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import joblib
import pandas as pd
from app.config import Config
from app.db import get_db, to_object_id

logger = logging.getLogger(__name__)

# Standard corporate category medians used for ratio calculation
CATEGORY_MEDIANS = {
    "Travel & Conveyance": 1500.0,
    "Meals & Entertainment": 1200.0,
    "Office Supplies & Software": 2500.0,
    "Accommodation & Lodging": 6000.0,
    "Training & Certification": 5000.0,
    "Health & Wellness": 1500.0,
    "Miscellaneous Expenses": 800.0
}


class PredictionService:
    """Manages the lifecycle and inference of the Random Forest ML model."""

    _pipeline = None
    _metadata = None

    @classmethod
    def load_model(cls) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """Loads and caches the trained scikit-learn pipeline and its metadata from disk."""
        if cls._pipeline is not None and cls._metadata is not None:
            return cls._pipeline, cls._metadata

        model_path = Path(Config.ML_MODEL_PATH)
        meta_path = Path(Config.ML_METADATA_PATH)

        if not model_path.exists() or not meta_path.exists():
            logger.warning(f"ML model files not found at {model_path}.")
            return None, None

        try:
            cls._pipeline = joblib.load(model_path)
            cls._metadata = joblib.load(meta_path)
            logger.info("Random Forest ML model and metadata successfully loaded.")
            return cls._pipeline, cls._metadata
        except Exception as e:
            logger.error(f"Error loading ML model from disk: {e}")
            return None, None

    @classmethod
    def get_employee_history(cls, employee_id: Any) -> Dict[str, Any]:
        """
        Calculates employee historical compliance metrics from MongoDB:
        - Total historical claims processed
        - Past approval rate (0.0 to 1.0)
        - Count of past rejected claims
        """
        if not employee_id:
            return {
                "total_past_claims": 0,
                "past_approval_rate": 1.0,
                "past_rejection_count": 0
            }

        db = get_db()
        emp_oid = to_object_id(employee_id)
        emp_str = str(employee_id)

        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"employee_id": emp_oid},
                        {"employee_id": emp_str},
                        {"employee_id": employee_id}
                    ],
                    "$and": [
                        {
                            "$or": [
                                {"status": {"$in": ["APPROVED", "REJECTED"]}},
                                {"claim_status": {"$in": ["APPROVED", "REJECTED"]}}
                            ]
                        }
                    ]
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_past_claims": {"$sum": 1},
                    "approved_count": {
                        "$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, 1, 0]}
                    },
                    "rejected_count": {
                        "$sum": {"$cond": [{"$in": ["$status", ["REJECTED", "rejected"]]}, 1, 0]}
                    }
                }
            }
        ]

        try:
            res = list(db.reimbursement_requests.aggregate(pipeline))
            if not res or not res[0].get("total_past_claims"):
                return {
                    "total_past_claims": 0,
                    "past_approval_rate": 1.0,
                    "past_rejection_count": 0
                }

            row = res[0]
            total = int(row["total_past_claims"])
            approved = int(row.get("approved_count") or 0)
            rejected = int(row.get("rejected_count") or 0)
            approval_rate = round(float(approved) / float(total), 3) if total > 0 else 1.0

            return {
                "total_past_claims": total,
                "past_approval_rate": approval_rate,
                "past_rejection_count": rejected
            }
        except Exception as e:
            logger.warning(f"Could not retrieve employee history from MongoDB: {e}")
            return {
                "total_past_claims": 0,
                "past_approval_rate": 1.0,
                "past_rejection_count": 0
            }

    @classmethod
    def predict(cls, claim: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts engineered features from a claim, constructs the input DataFrame,
        and generates an advisory risk classification via the Random Forest pipeline.
        """
        pipeline, metadata = cls.load_model()
        if pipeline is None:
            return {
                "available": False,
                "error": "ML model is not trained or loaded. Run 'python ml/train_model.py' to initialize the model."
            }

        category_name = claim.get("category_name") or claim.get("name") or "Miscellaneous Expenses"
        amount = float(claim.get("amount", 0.0))
        bill_available = 1 if claim.get("bill_available") or claim.get("receipt_path") or claim.get("bill_path") else 0

        # Extract day of week (0=Mon, 6=Sun)
        expense_date = claim.get("expense_date")
        if isinstance(expense_date, str):
            try:
                day_of_week = datetime.strptime(expense_date, "%Y-%m-%d").weekday()
            except ValueError:
                day_of_week = 2
        elif hasattr(expense_date, "weekday"):
            day_of_week = expense_date.weekday()
        else:
            day_of_week = 2

        # Fetch employee compliance profile
        employee_id = claim.get("employee_id")
        history = cls.get_employee_history(employee_id) if employee_id else {
            "total_past_claims": 0,
            "past_approval_rate": 1.0,
            "past_rejection_count": 0
        }

        # Calculate deviation ratio relative to category benchmark median
        median = CATEGORY_MEDIANS.get(category_name, 1500.0)
        amount_ratio = round(amount / median, 3)

        # Build single-sample DataFrame with exact column names expected by ColumnTransformer
        input_data = pd.DataFrame([{
            "category_name": category_name,
            "amount": amount,
            "day_of_week": day_of_week,
            "bill_available": bill_available,
            "employee_total_past_claims": history["total_past_claims"],
            "employee_past_approval_rate": history["past_approval_rate"],
            "employee_past_rejection_count": history["past_rejection_count"],
            "amount_to_category_median_ratio": amount_ratio
        }])

        try:
            prediction = pipeline.predict(input_data)[0]
            probabilities = pipeline.predict_proba(input_data)[0]
            classes = pipeline.classes_.tolist()

            prob_map = {classes[i]: round(float(probabilities[i]), 4) for i in range(len(classes))}
            confidence = round(float(max(probabilities)), 4)

            return {
                "available": True,
                "prediction": prediction,
                "confidence": confidence,
                "probabilities": prob_map,
                "features_used": {
                    "category": category_name,
                    "amount": amount,
                    "day_of_week": day_of_week,
                    "bill_attached": bool(bill_available),
                    "employee_total_past_claims": history["total_past_claims"],
                    "employee_past_approval_rate": history["past_approval_rate"],
                    "employee_past_rejections": history["past_rejection_count"],
                    "amount_to_median_ratio": amount_ratio
                },
                "disclaimer": (
                    "This ML prediction is an advisory risk score generated by a Random Forest Classifier "
                    "and does not constitute a final financial decision."
                )
            }
        except Exception as e:
            logger.error(f"Inference computation error: {e}")
            return {
                "available": False,
                "error": f"ML prediction computation error: {str(e)}"
            }
