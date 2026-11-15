"""
MongoDB Database Connection and Helpers
AI-Enhanced Reimbursements Management System

Manages MongoDB Atlas connection pooling via pymongo.MongoClient,
provides index initialization, connection health checks ('ping'),
and document serialization utilities for Flask routes and JSON responses.
"""

from datetime import datetime, date
import logging
import os
import re
from typing import Optional, Dict, Any, List
from bson import ObjectId
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, PyMongoError
from app.config import Config

try:
    import certifi
    CERTIFI_CA_FILE = certifi.where()
except ImportError:
    CERTIFI_CA_FILE = None

logger = logging.getLogger(__name__)

# Cached MongoDB client and database singletons
_client: Optional[MongoClient] = None
_db = None


def mask_mongo_uri(uri: str) -> str:
    """Masks credentials in MongoDB connection string for safe logging."""
    if not uri:
        return ""
    # Mask password in mongodb:// or mongodb+srv://
    return re.sub(r":([^@]+)@", r":****@", uri)


def _get_config_attr(config, key: str, default=None):
    """Safely retrieves configuration property from class or dict."""
    if hasattr(config, key):
        return getattr(config, key)
    elif isinstance(config, dict):
        return config.get(key, default)
    return default


def get_client(config=Config) -> MongoClient:
    """
    Returns the cached MongoClient instance, or establishes a new connection
    if not already initialized.
    """
    global _client
    if _client is not None:
        return _client

    uri = _get_config_attr(config, "MONGO_URI", os.getenv("MONGO_URI", ""))
    timeout = int(_get_config_attr(config, "MONGO_TIMEOUT_MS", 5000))
    is_testing = bool(_get_config_attr(config, "TESTING", False)) or os.getenv("FLASK_ENV") == "testing"

    # If in testing mode or URI contains placeholder credentials, fall back to local MongoDB if available
    target_uri = uri
    if is_testing or ("<PASSWORD>" in uri or "<USERNAME>" in uri):
        local_uri = os.getenv("MONGO_LOCAL_URI", "mongodb://localhost:27017")
        try:
            test_client = MongoClient(local_uri, serverSelectionTimeoutMS=2000)
            test_client.admin.command("ping")
            target_uri = local_uri
            logger.info("Using local MongoDB instance for isolated testing environment.")
        except Exception:
            target_uri = uri

    try:
        masked = mask_mongo_uri(target_uri)
        logger.info(f"Connecting to MongoDB at: {masked}")
        client_kwargs = {
            "serverSelectionTimeoutMS": timeout,
            "connectTimeoutMS": timeout,
            "maxPoolSize": 50,
            "retryWrites": True
        }
        if CERTIFI_CA_FILE and ("mongodb+srv://" in target_uri or "ssl=true" in target_uri.lower() or "tls=true" in target_uri.lower()):
            client_kwargs["tlsCAFile"] = CERTIFI_CA_FILE

        _client = MongoClient(target_uri, **client_kwargs)
        # Verify connection using ping command
        _client.admin.command("ping")
        logger.info("MongoDB connection verified successfully via ping.")
        return _client
    except (ConnectionFailure, ServerSelectionTimeoutError, PyMongoError) as err:
        logger.error(f"MongoDB connection failed: {err}")
        # If Atlas failed and local instance is available, fallback gracefully
        if target_uri != "mongodb://localhost:27017":
            try:
                logger.warning("Attempting local MongoDB connection fallback (localhost:27017)...")
                _client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
                _client.admin.command("ping")
                logger.info("Connected to local MongoDB instance as fallback.")
                return _client
            except Exception as fallback_err:
                logger.critical(f"Local fallback also failed: {fallback_err}")

        _client = None
        raise ConnectionError(f"Failed to connect to MongoDB: {err}")


def get_db(config=Config):
    """
    Returns the active MongoDB database object for the application.
    """
    global _db
    if _db is not None:
        return _db

    client = get_client(config)
    db_name = _get_config_attr(config, "MONGO_DB_NAME", os.getenv("MONGO_DB_NAME", "reimbursement_db"))
    _db = client[db_name]
    return _db


def init_db(config=Config):
    """
    Initializes the database connection, ensures required collections exist,
    and creates required performance and uniqueness indexes.
    """
    db = get_db(config)

    # 1. users: unique index on email
    db.users.create_index([("email", ASCENDING)], unique=True)

    # 2. expense_categories: unique index on name
    db.expense_categories.create_index([("name", ASCENDING)], unique=True)

    # 3. reimbursement_requests indexes
    db.reimbursement_requests.create_index([("employee_id", ASCENDING)])
    db.reimbursement_requests.create_index([("status", ASCENDING)])
    db.reimbursement_requests.create_index([("created_at", ASCENDING)])

    # 4. reimbursement_audit_logs index
    db.reimbursement_audit_logs.create_index([("reimbursement_id", ASCENDING)])

    logger.info("MongoDB collections and indexes initialized successfully.")
    return db


def close_mongodb():
    """Closes the cached MongoDB client."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB client connection closed.")


def to_object_id(val: Any) -> Any:
    """
    Safely converts a string to a BSON ObjectId if valid hex format,
    or returns the value untouched if already an ObjectId or invalid.
    """
    if isinstance(val, ObjectId):
        return val
    if isinstance(val, str) and ObjectId.is_valid(val):
        return ObjectId(val)
    return val


def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Converts a MongoDB document into a JSON-serializable dictionary.
    Guarantees compatibility with both the MongoDB collection schema and
    frontend expectations:
    - _id is serialized to string 'id' and '_id'
    - Datetimes are formatted as ISO strings
    - Field aliases (name/full_name, is_active/active, status/claim_status,
      receipt_path/bill_path, receipt_filename/bill_original_name) are populated.
    """
    if not doc or not isinstance(doc, dict):
        return doc

    d = dict(doc)

    # Serialize ObjectId
    if "_id" in d:
        oid_str = str(d["_id"])
        d["id"] = oid_str
        d["_id"] = oid_str

    # User field aliases
    if "name" in d and "full_name" not in d:
        d["full_name"] = d["name"]
    elif "full_name" in d and "name" not in d:
        d["name"] = d["full_name"]

    # Category field aliases
    if "name" in d and "category_name" not in d:
        d["category_name"] = d["name"]
    elif "category_name" in d and "name" not in d:
        d["name"] = d["category_name"]

    if "is_active" in d and "active" not in d:
        d["active"] = bool(d["is_active"])
    elif "active" in d and "is_active" not in d:
        d["is_active"] = bool(d["active"])

    # Reimbursement field aliases
    if "status" in d and "claim_status" not in d:
        d["claim_status"] = d["status"]
    elif "claim_status" in d and "status" not in d:
        d["status"] = d["claim_status"]

    if "receipt_filename" in d and "bill_original_name" not in d:
        d["bill_original_name"] = d["receipt_filename"]
    elif "bill_original_name" in d and "receipt_filename" not in d:
        d["receipt_filename"] = d["bill_original_name"]

    if "receipt_path" in d and "bill_path" not in d:
        d["bill_path"] = d["receipt_path"]
    elif "bill_path" in d and "receipt_path" not in d:
        d["receipt_path"] = d["bill_path"]

    d["bill_available"] = bool(d.get("receipt_path") or d.get("bill_path"))

    if "genai_observations" in d and "ai_observations" not in d:
        d["ai_observations"] = d["genai_observations"]
    elif "ai_observations" in d and "genai_observations" not in d:
        d["genai_observations"] = d["ai_observations"]

    if "missing_documents" in d and "ai_missing_info" not in d:
        d["ai_missing_info"] = d["missing_documents"]
    elif "ai_missing_info" in d and "missing_documents" not in d:
        d["missing_documents"] = d["ai_missing_info"]

    if "suggested_actions" in d and "ai_suggested_actions" not in d:
        d["ai_suggested_actions"] = d["suggested_actions"]
    elif "ai_suggested_actions" in d and "suggested_actions" not in d:
        d["suggested_actions"] = d["ai_suggested_actions"]

    if "created_at" in d and "submitted_at" not in d:
        d["submitted_at"] = d["created_at"]
    if "updated_at" in d and "reviewed_at" not in d:
        d["reviewed_at"] = d["updated_at"]

    # Recursively convert ObjectId and datetime objects to strings
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
        elif isinstance(v, (datetime, date)):
            d[k] = v.isoformat()

    return d


def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serializes a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs if doc]
