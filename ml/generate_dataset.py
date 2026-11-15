"""
Synthetic Dataset Generator for Reimbursement Risk Classification
AI-Enhanced Reimbursements Management System

Generates a realistic corporate reimbursement dataset with 2,500 records.
Simulates real-world expense distributions, receipt compliance, weekend anomalies,
and historical employee approval rates to produce balanced risk labels:
- LIKELY_APPROVED: Routine amounts with receipts and clean compliance history.
- REQUIRES_REVIEW: Moderately elevated amounts, weekend expenses, or policy variances.
- HIGH_REJECTION_RISK: Missing receipts, excessive amounts, or high historical rejection rates.
"""

import os
from pathlib import Path
import random
import numpy as np
import pandas as pd

# Fix random seed for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = PROJECT_ROOT / "ml" / "dataset" / "reimbursement_data.csv"

CATEGORIES = [
    "Travel & Conveyance",
    "Meals & Entertainment",
    "Office Supplies & Software",
    "Accommodation & Lodging",
    "Training & Certification",
    "Health & Wellness",
    "Miscellaneous Expenses"
]

# Category profiles: (minimum, median, standard policy threshold)
CATEGORY_PROFILES = {
    "Travel & Conveyance": (200, 1500, 5000),
    "Meals & Entertainment": (300, 1200, 4000),
    "Office Supplies & Software": (500, 2500, 8000),
    "Accommodation & Lodging": (1500, 6000, 15000),
    "Training & Certification": (1000, 5000, 20000),
    "Health & Wellness": (500, 1500, 5000),
    "Miscellaneous Expenses": (100, 800, 2500)
}


def generate_dataset(num_records: int = 2500, output_path: str = None) -> pd.DataFrame:
    """
    Generates synthetic corporate expense records and writes them to a CSV file.
    """
    output_path = output_path or str(DEFAULT_DATASET_PATH)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    records = []

    for _ in range(num_records):
        category = random.choice(CATEGORIES)
        min_val, median_val, threshold_val = CATEGORY_PROFILES[category]

        # Generate realistic right-skewed expense amount using log-normal distribution
        amount = round(float(np.random.lognormal(mean=np.log(median_val), sigma=0.65)), 2)
        amount = max(min_val * 0.5, min(amount, threshold_val * 2.5))
        amount = round(amount, 2)

        # Day of week: 0=Mon, 6=Sun (Weekdays are 94% probable, weekends 6%)
        day_of_week = int(np.random.choice(
            [0, 1, 2, 3, 4, 5, 6],
            p=[0.20, 0.22, 0.22, 0.18, 0.12, 0.03, 0.03]
        ))

        # Receipt availability probability decreases as expense becomes higher / non-standard
        if amount > threshold_val:
            bill_available = int(np.random.choice([1, 0], p=[0.75, 0.25]))
        elif amount > median_val:
            bill_available = int(np.random.choice([1, 0], p=[0.88, 0.12]))
        else:
            bill_available = int(np.random.choice([1, 0], p=[0.93, 0.07]))

        # Employee historical profile (geometric distribution for prior claims)
        total_past_claims = int(np.random.geometric(p=0.08)) - 1
        if total_past_claims > 0:
            past_approval_rate = round(float(np.random.beta(a=8, b=2)), 3)
            past_approval_rate = min(1.0, max(0.0, past_approval_rate))
            past_rejection_count = int(round(total_past_claims * (1.0 - past_approval_rate)))
        else:
            past_approval_rate = 1.0
            past_rejection_count = 0

        # Ratio of claimed amount to category median benchmark
        amount_ratio = round(amount / median_val, 3)

        # Deterministic risk scoring with Gaussian noise
        risk_score = 0.0

        # Missing receipt penalties
        if bill_available == 0:
            risk_score += 45.0
            if amount > threshold_val * 0.8:
                risk_score += 25.0

        # Amount threshold penalties
        if amount > threshold_val * 1.5:
            risk_score += 40.0
        elif amount > threshold_val:
            risk_score += 25.0
        elif amount > median_val * 1.3:
            risk_score += 12.0

        # Weekend expense anomalies for work equipment / software
        if day_of_week in (5, 6):
            if category in ("Office Supplies & Software", "Training & Certification"):
                risk_score += 15.0

        # Employee track record penalties
        if past_rejection_count >= 3:
            risk_score += 20.0
        elif past_approval_rate < 0.60:
            risk_score += 15.0

        # Add Gaussian noise (mean=0, std=5) to simulate real-world variability
        noise = np.random.normal(0, 5.0)
        final_score = max(0.0, min(100.0, risk_score + noise))

        if final_score < 30.0:
            label = "LIKELY_APPROVED"
        elif final_score < 60.0:
            label = "REQUIRES_REVIEW"
        else:
            label = "HIGH_REJECTION_RISK"

        records.append({
            "amount": amount,
            "category_name": category,
            "day_of_week": day_of_week,
            "bill_available": bill_available,
            "employee_total_past_claims": total_past_claims,
            "employee_past_approval_rate": past_approval_rate,
            "employee_past_rejection_count": past_rejection_count,
            "amount_to_category_median_ratio": amount_ratio,
            "risk_label": label
        })

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"[OK] Generated dataset with {len(df)} records saved to '{output_path}'.")
    print("\nClass distribution:")
    print(df["risk_label"].value_counts(normalize=True).round(3))
    print("\nSample records:")
    print(df.head(3))
    return df


if __name__ == "__main__":
    generate_dataset()
