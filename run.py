"""
Application Entry Point
AI-Enhanced Reimbursements Management System

Initializes and starts the Flask development server connected to MongoDB.
"""

import os
import sys
from pathlib import Path

# Add project root to Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.config import Config
from app.db import mask_mongo_uri

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "True").lower() == "true"

    print("=" * 65)
    print("AI-Enhanced Reimbursements Management System")
    print(f"Server starting on http://localhost:{port}")
    print("=" * 65)
    print(f"  * Environment     : {os.getenv('FLASK_ENV', 'development')}")
    print(f"  * Database Engine : MongoDB Atlas")
    print(f"  * Database Name   : {Config.MONGO_DB_NAME}")
    print(f"  * MongoDB URI     : {mask_mongo_uri(Config.MONGO_URI)}")
    print(f"  * ML Model Loaded : {Path(Config.ML_MODEL_PATH).exists()}")
    print(f"  * GenAI Provider  : {Config.LLM_PROVIDER}")
    print("=" * 65)

    app.run(host="0.0.0.0", port=port, debug=debug)
