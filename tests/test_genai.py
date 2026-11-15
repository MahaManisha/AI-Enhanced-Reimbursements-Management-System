import json
from unittest.mock import patch
import pytest
from app.services.genai_service import GenAIService


def test_genai_prompt_building():
    claim = {
        "employee_name": "John Doe",
        "employee_department": "Engineering",
        "category_name": "Travel & Conveyance",
        "amount": 420.00,
        "expense_date": "2026-10-22",
        "description": "Roundtrip taxi fare for client demonstration",
        "bill_available": 1,
        "bill_original_name": "taxi_bill.pdf"
    }
    ml_data = {
        "prediction": "LIKELY_APPROVED",
        "confidence": 0.92
    }
    prompt = GenAIService._build_prompt(claim, ml_data)
    assert "John Doe" in prompt
    assert "$420.00" in prompt
    assert "Travel & Conveyance" in prompt
    assert "LIKELY_APPROVED" in prompt


def test_genai_json_parsing_and_validation():
    mock_json = """
    ```json
    {
      "summary": "Employee requested local travel reimbursement.",
      "observations": "Expense aligns with standard urban cab allowance.",
      "missing_info": "None identified.",
      "suggested_actions": "Proceed with standard review."
    }
    ```
    """
    parsed = GenAIService._parse_and_validate_json(mock_json)
    assert parsed["summary"] == "Employee requested local travel reimbursement."
    assert parsed["observations"] == "Expense aligns with standard urban cab allowance."
    assert "missing_info" in parsed
    assert "suggested_actions" in parsed


def test_genai_heuristic_fallback_when_unconfigured():
    claim = {
        "employee_name": "Alex Kumar",
        "employee_department": "Sales",
        "category_name": "Meals & Entertainment",
        "amount": 9500.00,
        "expense_date": "2026-10-25",
        "description": "Dinner with clients",
        "bill_available": 0,
        "bill_path": None,
        "ml_prediction": "HIGH_REJECTION_RISK"
    }
    # When no external key is available, should generate high quality fallback without crashing
    success, insights, engine = GenAIService.generate_reimbursement_insights(claim)
    assert "summary" in insights
    assert "observations" in insights
    assert "missing_info" in insights
    assert "suggested_actions" in insights
    assert "Alex Kumar" in insights["summary"]
    assert "receipt" in insights["observations"].lower() or "missing" in insights["missing_info"].lower()


def test_genai_mocked_llm_call():
    mock_llm_response = {
        "summary": "Mocked LLM reimbursement summary.",
        "observations": "All policies satisfied.",
        "missing_info": "None.",
        "suggested_actions": "Authorize payment."
    }

    with patch.object(GenAIService, "_call_gemini", return_value=mock_llm_response):
        with patch("app.config.Config.GEMINI_API_KEY", "dummy-key-for-test"):
            with patch("app.config.Config.LLM_PROVIDER", "gemini"):
                claim = {
                    "employee_name": "Sarah",
                    "amount": 100,
                    "category_name": "General"
                }
                success, insights, provider = GenAIService.generate_reimbursement_insights(claim)
                assert success is True
                assert insights["summary"] == "Mocked LLM reimbursement summary."
                assert "Gemini" in provider

