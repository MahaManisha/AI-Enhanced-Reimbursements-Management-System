"""
Application Configuration
AI-Enhanced Reimbursements Management System

Loads environment variables and defines settings for Flask, MongoDB Atlas,
JWT authentication, file uploads, and ML / GenAI services.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration loaded from environment variables."""
    BASE_DIR = BASE_DIR

    # Flask & Security
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24))

    # MongoDB Atlas Configuration
    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb+srv://<USERNAME>:<PASSWORD>@cluster0.gse3wum.mongodb.net/reimbursement_db?retryWrites=true&w=majority"
    )
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "reimbursement_db")
    MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", 15000))

    # File Uploads
    UPLOAD_FOLDER = str(BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/pjpeg"
    }

    # Machine Learning Pipeline
    ML_MODEL_PATH = str(BASE_DIR / os.getenv("ML_MODEL_PATH", "ml/saved_models/random_forest_reimbursement.joblib"))
    ML_METADATA_PATH = str(BASE_DIR / os.getenv("ML_METADATA_PATH", "ml/saved_models/pipeline_metadata.joblib"))

    # Generative AI Audit Copilot
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", 15))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class TestConfig(Config):
    """Configuration used during automated testing."""
    TESTING = True
    DEBUG = False
    MONGO_DB_NAME = "test_reimbursement_db"
