"""
Flask Application Factory (MongoDB)
AI-Enhanced Reimbursements Management System

Initializes the Flask application, registers blueprints, configures CORS,
initializes the MongoDB connection and collections, and pre-loads the Random Forest ML pipeline.
"""

import logging
import os
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

from app.config import Config
from app.db import init_db
from app.services.prediction_service import PredictionService

# Configure application-wide logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config) -> Flask:
    """Creates, configures, and returns a Flask application instance."""
    app = Flask(
        __name__,
        static_folder=str(Config.BASE_DIR / "frontend"),
        static_url_path=""
    )
    app.config.from_object(config_class)

    # Enable CORS for API routes
    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    if frontend_url and frontend_url != "*":
        cors_origins = [orig.strip() for orig in frontend_url.split(",") if orig.strip()]
    else:
        cors_origins = "*"
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize MongoDB connection, collections, and indexes
    if not app.config.get("TESTING", False):
        try:
            init_db(app.config)
        except Exception as e:
            logger.error(f"MongoDB initialization error: {e}")

        try:
            PredictionService.load_model()
        except Exception as e:
            logger.warning(f"ML model preloading error: {e}")

    # Register API blueprints
    from app.routes.auth import auth_bp
    from app.routes.categories import categories_bp
    from app.routes.reimbursements import reimbursements_bp
    from app.routes.admin import admin_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(reimbursements_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analytics_bp)

    # Health check endpoint for deployment monitoring
    @app.route("/api/health", methods=["GET"])
    @app.route("/health", methods=["GET"])
    def health_check():
        """Production health check reporting deployment readiness immediately."""
        from datetime import datetime, timezone
        from app.db import _client

        db_status = "connected" if _client is not None else "initializing"
        model_loaded = (
            PredictionService._pipeline is not None
            and PredictionService._metadata is not None
        )
        genai_configured = bool(getattr(Config, "GEMINI_API_KEY", ""))

        return jsonify({
            "status": "healthy",
            "service": "AI-Enhanced Reimbursements Management System",
            "database": db_status,
            "ml_model_loaded": model_loaded,
            "genai_configured": genai_configured,
            "llm_provider": Config.LLM_PROVIDER,
            "environment": os.getenv("FLASK_ENV", "production"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200

    # Static frontend routing
    frontend_dir = Config.BASE_DIR / "frontend"

    @app.route("/")
    def index():
        """Serves the project landing page."""
        return send_from_directory(str(frontend_dir), "index.html")

    @app.route("/<path:path>")
    def serve_frontend_files(path):
        """Serves frontend static assets or HTML pages."""
        file_path = frontend_dir / path
        if file_path.exists() and file_path.is_file():
            return send_from_directory(str(frontend_dir), path)

        html_file = frontend_dir / f"{path}.html"
        if html_file.exists():
            return send_from_directory(str(frontend_dir), f"{path}.html")

        if not path.startswith("api/"):
            return send_from_directory(str(frontend_dir), "index.html")

        return jsonify({"success": False, "error": f"Endpoint '{path}' not found."}), 404

    # Global HTTP error handlers
    @app.errorhandler(404)
    def not_found_error(err):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Requested API route not found."}), 404
        return send_from_directory(str(frontend_dir), "index.html")

    @app.errorhandler(413)
    def request_entity_too_large(err):
        return jsonify({
            "success": False,
            "error": "Uploaded file is too large. Maximum permissible upload size is 10 MB."
        }), 413

    @app.errorhandler(500)
    def internal_error(err):
        logger.error(f"Internal server error: {err}")
        return jsonify({
            "success": False,
            "error": "An internal server error occurred."
        }), 500

    @app.errorhandler(ConnectionError)
    def database_connection_error(err):
        logger.critical(f"Database connection error: {err}")
        return jsonify({
            "success": False,
            "error": str(err),
            "help": "Please ensure MongoDB Atlas URI or MongoDB service is configured and reachable."
        }), 503

    return app
