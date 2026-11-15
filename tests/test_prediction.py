import pytest
from app.services.prediction_service import PredictionService


def test_model_loading():
    pipeline, metadata = PredictionService.load_model()
    assert pipeline is not None
    assert metadata is not None
    assert "classes" in metadata
    assert "accuracy" in metadata
    assert metadata["accuracy"] > 0.85


def test_prediction_low_risk_claim():
    claim = {
        "amount": 250.00,
        "category_name": "Travel & Conveyance",
        "bill_available": 1,
        "bill_path": "receipt.pdf",
        "expense_date": "2026-10-20",
        "employee_id": 2
    }
    result = PredictionService.predict(claim)
    assert result["available"] is True
    assert result["prediction"] in ("LIKELY_APPROVED", "REQUIRES_REVIEW", "HIGH_REJECTION_RISK")
    assert 0.0 <= result["confidence"] <= 1.0
    assert "probabilities" in result
    assert "features_used" in result


def test_prediction_high_risk_claim():
    # Extreme amount with no bill attached
    claim = {
        "amount": 45000.00,
        "category_name": "Meals & Entertainment",
        "bill_available": 0,
        "bill_path": None,
        "expense_date": "2026-10-25",
        "employee_id": 2
    }
    result = PredictionService.predict(claim)
    assert result["available"] is True
    assert result["prediction"] in ("HIGH_REJECTION_RISK", "REQUIRES_REVIEW")


def test_prediction_output_classes_and_probabilities():
    claim = {
        "amount": 1500.00,
        "category_name": "Office Supplies & Software",
        "bill_available": 1,
        "expense_date": "2026-10-21",
        "employee_id": 2
    }
    res = PredictionService.predict(claim)
    assert res["available"] is True
    probs = res["probabilities"]
    assert "LIKELY_APPROVED" in probs
    assert "REQUIRES_REVIEW" in probs
    assert "HIGH_REJECTION_RISK" in probs
    # Sum of probabilities approximately 1
    total_prob = sum(probs.values())
    assert 0.99 <= total_prob <= 1.01

