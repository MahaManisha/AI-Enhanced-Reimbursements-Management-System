"""
Analytics & Aggregation Routes (MongoDB)
AI-Enhanced Reimbursements Management System

Provides live aggregation pipelines for executive dashboards:
- Admin Analytics: Status distribution, expenditure by category, monthly audit trends,
  risk class distribution, and high-rejection-risk alerts.
- Employee Analytics: Personal expense volume, status counts, monthly breakdown,
  and recent submission dossiers.
All metrics are computed directly from real MongoDB records.
"""

from flask import Blueprint, jsonify, g
from app.db import get_db, to_object_id, serialize_docs
from app.utils.auth_utils import token_required, admin_required

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api")


@analytics_bp.route("/admin/analytics", methods=["GET"])
@admin_required
def get_admin_analytics():
    """
    Computes financial analytics from MongoDB records for the Finance Admin Dashboard
    using native MongoDB aggregation pipelines.
    """
    db = get_db()

    # 1. Executive Summary KPIs
    summary_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_claims": {"$sum": 1},
                "pending_claims": {"$sum": {"$cond": [{"$in": ["$status", ["PENDING", "pending"]]}, 1, 0]}},
                "approved_claims": {"$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, 1, 0]}},
                "rejected_claims": {"$sum": {"$cond": [{"$in": ["$status", ["REJECTED", "rejected"]]}, 1, 0]}},
                "total_amount_claimed": {"$sum": "$amount"},
                "total_amount_approved": {"$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, "$amount", 0]}},
                "total_amount_pending": {"$sum": {"$cond": [{"$in": ["$status", ["PENDING", "pending"]]}, "$amount", 0]}},
                "total_amount_rejected": {"$sum": {"$cond": [{"$in": ["$status", ["REJECTED", "rejected"]]}, "$amount", 0]}},
            }
        }
    ]
    summary_res = list(db.reimbursement_requests.aggregate(summary_pipeline))
    summary = summary_res[0] if summary_res else {}

    for key in ["total_amount_claimed", "total_amount_approved", "total_amount_pending", "total_amount_rejected"]:
        summary[key] = float(summary.get(key) or 0.0)
    for key in ["total_claims", "pending_claims", "approved_claims", "rejected_claims"]:
        summary[key] = int(summary.get(key) or 0)

    # 2. Status distribution
    status_pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }
        }
    ]
    status_distribution = [
        {
            "status": r["_id"] or "PENDING",
            "count": int(r["count"]),
            "amount": float(r["total_amount"])
        }
        for r in db.reimbursement_requests.aggregate(status_pipeline)
        if r.get("_id")
    ]

    # 3. Expenditure by category
    category_pipeline = [
        {
            "$group": {
                "_id": "$category_name",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }
        },
        {"$match": {"total_amount": {"$gt": 0}}},
        {"$sort": {"total_amount": -1}}
    ]
    category_distribution = [
        {
            "category": r["_id"] or "General",
            "count": int(r["count"]),
            "amount": float(r["total_amount"])
        }
        for r in db.reimbursement_requests.aggregate(category_pipeline)
        if r.get("_id")
    ]

    # 4. Monthly audit trends (last 12 months)
    monthly_pipeline = [
        {
            "$project": {
                "month": {
                    "$cond": [
                        {"$eq": [{"$type": "$expense_date"}, "date"]},
                        {"$dateToString": {"format": "%Y-%m", "date": "$expense_date"}},
                        {"$substrCP": [{"$ifNull": ["$expense_date", "2026-01-01"]}, 0, 7]}
                    ]
                },
                "amount": "$amount",
                "status": "$status"
            }
        },
        {
            "$group": {
                "_id": "$month",
                "total_claims": {"$sum": 1},
                "claimed_amount": {"$sum": "$amount"},
                "approved_amount": {"$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, "$amount", 0]}}
            }
        },
        {"$sort": {"_id": 1}},
        {"$limit": 12}
    ]
    monthly_trends = [
        {
            "month": r["_id"],
            "total_claims": int(r["total_claims"]),
            "claimed_amount": float(r["claimed_amount"]),
            "approved_amount": float(r["approved_amount"])
        }
        for r in db.reimbursement_requests.aggregate(monthly_pipeline)
        if r.get("_id")
    ]

    # 5. ML Risk distribution
    risk_pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$ml_prediction", "UNPREDICTED"]},
                "count": {"$sum": 1}
            }
        }
    ]
    risk_distribution = [
        {"risk": r["_id"], "count": int(r["count"])}
        for r in db.reimbursement_requests.aggregate(risk_pipeline)
    ]

    # 6. High-Risk Pending Claims
    high_risk_query = {
        "$or": [{"status": "PENDING"}, {"claim_status": "PENDING"}],
        "ml_prediction": "HIGH_REJECTION_RISK"
    }
    high_risk_claims = serialize_docs(
        list(db.reimbursement_requests.find(high_risk_query).sort("amount", -1))
    )

    # 7. Department Distribution
    dept_pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": ["$employee_department", "General"]},
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }
        },
        {"$sort": {"total_amount": -1}}
    ]
    department_distribution = [
        {
            "department": r["_id"],
            "count": int(r["count"]),
            "amount": float(r["total_amount"])
        }
        for r in db.reimbursement_requests.aggregate(dept_pipeline)
    ]

    return jsonify({
        "success": True,
        "summary": summary,
        "status_distribution": status_distribution,
        "category_distribution": category_distribution,
        "monthly_trends": monthly_trends,
        "risk_distribution": risk_distribution,
        "high_risk_claims": high_risk_claims,
        "department_distribution": department_distribution
    }), 200


@analytics_bp.route("/employee/analytics", methods=["GET"])
@token_required
def get_employee_analytics():
    """
    Computes personal reimbursement analytics for the authenticated employee
    using MongoDB aggregation pipelines.
    """
    user = g.current_user
    employee_id = user["id"]
    db = get_db()

    emp_oid = to_object_id(employee_id)
    emp_str = str(employee_id)
    match_emp = {
        "$match": {
            "$or": [
                {"employee_id": emp_oid},
                {"employee_id": emp_str},
                {"employee_id": employee_id}
            ]
        }
    }

    # 1. Summary KPIs
    summary_pipeline = [
        match_emp,
        {
            "$group": {
                "_id": None,
                "total_claims": {"$sum": 1},
                "pending_claims": {"$sum": {"$cond": [{"$in": ["$status", ["PENDING", "pending"]]}, 1, 0]}},
                "approved_claims": {"$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, 1, 0]}},
                "rejected_claims": {"$sum": {"$cond": [{"$in": ["$status", ["REJECTED", "rejected"]]}, 1, 0]}},
                "total_claimed": {"$sum": "$amount"},
                "total_approved": {"$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, "$amount", 0]}}
            }
        }
    ]
    summary_res = list(db.reimbursement_requests.aggregate(summary_pipeline))
    summary = summary_res[0] if summary_res else {}

    for key in ["total_claimed", "total_approved"]:
        summary[key] = float(summary.get(key) or 0.0)
    for key in ["total_claims", "pending_claims", "approved_claims", "rejected_claims"]:
        summary[key] = int(summary.get(key) or 0)

    # 2. Category breakdown for employee
    cat_pipeline = [
        match_emp,
        {
            "$group": {
                "_id": "$category_name",
                "count": {"$sum": 1},
                "total_amount": {"$sum": "$amount"}
            }
        },
        {"$sort": {"total_amount": -1}}
    ]
    category_breakdown = [
        {
            "category": r["_id"] or "General",
            "count": int(r["count"]),
            "amount": float(r["total_amount"])
        }
        for r in db.reimbursement_requests.aggregate(cat_pipeline)
        if r.get("_id")
    ]

    # 3. Monthly trends (last 6 months)
    month_pipeline = [
        match_emp,
        {
            "$project": {
                "month": {
                    "$cond": [
                        {"$eq": [{"$type": "$expense_date"}, "date"]},
                        {"$dateToString": {"format": "%Y-%m", "date": "$expense_date"}},
                        {"$substrCP": [{"$ifNull": ["$expense_date", "2026-01-01"]}, 0, 7]}
                    ]
                },
                "amount": "$amount",
                "status": "$status"
            }
        },
        {
            "$group": {
                "_id": "$month",
                "total_claims": {"$sum": 1},
                "claimed_amount": {"$sum": "$amount"},
                "approved_amount": {"$sum": {"$cond": [{"$in": ["$status", ["APPROVED", "approved"]]}, "$amount", 0]}}
            }
        },
        {"$sort": {"_id": 1}},
        {"$limit": 6}
    ]
    monthly_trends = [
        {
            "month": r["_id"],
            "total_claims": int(r["total_claims"]),
            "claimed_amount": float(r["claimed_amount"]),
            "approved_amount": float(r["approved_amount"])
        }
        for r in db.reimbursement_requests.aggregate(month_pipeline)
        if r.get("_id")
    ]

    # 4. Recent claims
    recent_docs = list(db.reimbursement_requests.find({
        "$or": [
            {"employee_id": emp_oid},
            {"employee_id": emp_str},
            {"employee_id": employee_id}
        ]
    }).sort("created_at", -1).limit(5))
    recent_claims = serialize_docs(recent_docs)

    return jsonify({
        "success": True,
        "summary": summary,
        "category_breakdown": category_breakdown,
        "monthly_trends": monthly_trends,
        "recent_claims": recent_claims
    }), 200
