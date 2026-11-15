"""
Random Forest Model Trainer
AI-Enhanced Reimbursements Management System

Trains a scikit-learn Pipeline with:
1. ColumnTransformer:
   - StandardScaler for numerical features (amount, day_of_week, historical stats, median ratio)
   - OneHotEncoder for categorical features (category_name)
2. RandomForestClassifier:
   - 150 decision trees, max_depth=10, balanced class weights
3. Evaluates model accuracy, precision, recall, and F1-score on a stratified 20% test holdout.
4. Serializes the trained pipeline and metadata to disk using joblib.
"""

import os
from pathlib import Path
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = PROJECT_ROOT / "ml" / "dataset" / "reimbursement_data.csv"
MODEL_PATH = PROJECT_ROOT / "ml" / "saved_models" / "random_forest_reimbursement.joblib"
METADATA_PATH = PROJECT_ROOT / "ml" / "saved_models" / "pipeline_metadata.joblib"


def train_reimbursement_model():
    """
    Trains the Random Forest classifier and persists the model pipeline.
    """
    print("=" * 60)
    print("AI-Enhanced Reimbursements System - ML Model Trainer")
    print("=" * 60)

    # Ensure dataset exists; generate if missing
    if not DATASET_PATH.exists():
        print(f"Dataset not found at {DATASET_PATH}. Generating synthetic dataset...")
        from ml.generate_dataset import generate_dataset
        generate_dataset(output_path=str(DATASET_PATH))

    df = pd.read_csv(DATASET_PATH)
    print(f"Loaded dataset: {df.shape[0]} records, {df.shape[1]} columns.")

    categorical_features = ["category_name"]
    numerical_features = [
        "amount",
        "day_of_week",
        "bill_available",
        "employee_total_past_claims",
        "employee_past_approval_rate",
        "employee_past_rejection_count",
        "amount_to_category_median_ratio"
    ]
    target_column = "risk_label"

    X = df[categorical_features + numerical_features]
    y = df[target_column]

    missing = X.isnull().sum().sum()
    print(f"Total missing values in features: {missing}")

    # Stratified train/test split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Training set: {X_train.shape[0]} samples | Test set: {X_test.shape[0]} samples")

    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numerical_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    # Random Forest classifier
    rf_classifier = RandomForestClassifier(
        n_estimators=150,
        max_depth=10,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", rf_classifier)
    ])

    print("Training Random Forest Classifier pipeline...")
    pipeline.fit(X_train, y_train)

    # Evaluate on holdout test set
    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    conf_matrix = confusion_matrix(y_test, y_pred, labels=pipeline.classes_).tolist()

    print(f"\nModel Performance on Test Set:")
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Persist trained pipeline
    os.makedirs(MODEL_PATH.parent, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved trained pipeline to: {MODEL_PATH}")

    # Persist metadata for inference service verification
    metadata = {
        "classes": pipeline.classes_.tolist(),
        "categorical_features": categorical_features,
        "numerical_features": numerical_features,
        "accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": conf_matrix,
        "model_version": "1.0.0",
        "algorithm": "RandomForestClassifier (scikit-learn)"
    }
    joblib.dump(metadata, METADATA_PATH)
    print(f"Saved pipeline metadata to: {METADATA_PATH}")
    print("=" * 60)
    return pipeline, metadata


if __name__ == "__main__":
    train_reimbursement_model()
