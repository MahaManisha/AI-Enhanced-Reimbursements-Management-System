"""
Model Evaluator and Diagnostic Inspector
AI-Enhanced Reimbursements Management System

Loads the saved Random Forest pipeline and metadata from disk,
computes metrics against the test set, prints the confusion matrix,
and outputs sample prediction checks.
"""

from pathlib import Path
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "ml" / "dataset" / "reimbursement_data.csv"
MODEL_PATH = PROJECT_ROOT / "ml" / "saved_models" / "random_forest_reimbursement.joblib"
METADATA_PATH = PROJECT_ROOT / "ml" / "saved_models" / "pipeline_metadata.joblib"


def evaluate():
    """Evaluates the serialized model pipeline on test data."""
    print("=" * 60)
    print("AI-Enhanced Reimbursements System - ML Model Evaluator")
    print("=" * 60)

    if not MODEL_PATH.exists():
        print(f"Model not found at {MODEL_PATH}. Please run train_model.py first.")
        return

    pipeline = joblib.load(MODEL_PATH)
    metadata = joblib.load(METADATA_PATH)

    df = pd.read_csv(DATASET_PATH)
    categorical_features = metadata["categorical_features"]
    numerical_features = metadata["numerical_features"]
    target_column = "risk_label"

    X = df[categorical_features + numerical_features]
    y = df[target_column]

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    y_pred = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"Model Algorithm : {metadata.get('algorithm', 'RandomForestClassifier')}")
    print(f"Overall Accuracy: {acc * 100:.2f}%\n")

    print("Detailed Classification Report:")
    print(classification_report(y_test, y_pred))

    classes = pipeline.classes_.tolist()
    cm = confusion_matrix(y_test, y_pred, labels=classes)
    cm_df = pd.DataFrame(cm, index=[f"Actual {c}" for c in classes], columns=[f"Pred {c}" for c in classes])

    print("Confusion Matrix:")
    print(cm_df)
    print("\nInference Sample Check:")
    for i in range(min(5, len(X_test))):
        sample = X_test.iloc[[i]]
        true_label = y_test.iloc[i]
        pred_label = y_pred[i]
        max_prob = probs[i].max()
        amount_val = sample['amount'].values[0]
        cat_val = sample['category_name'].values[0]
        print(f"Sample #{i+1} | Amount: ${amount_val:.2f} | Category: {cat_val} | True: {true_label} | Pred: {pred_label} (Confidence: {max_prob*100:.1f}%)")

    print("=" * 60)


if __name__ == "__main__":
    evaluate()
