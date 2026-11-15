"""
File Storage & Receipt Utilities
AI-Enhanced Reimbursements Management System

Handles secure receipt uploads, MIME type and magic-number validation,
unique filename generation to avoid collisions, directory traversal defense,
and inline browser rendering for PDF and image formats.
"""

import mimetypes
import os
from pathlib import Path
from typing import Tuple
import uuid
from flask import send_from_directory, jsonify
from werkzeug.utils import secure_filename
from app.config import Config

# Standard magic numbers (file headers) to verify actual file content
MAGIC_BYTES = {
    b"%PDF": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


def allowed_file(filename: str) -> bool:
    """Checks whether the file extension is included in ALLOWED_EXTENSIONS."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def validate_file_content(file_storage) -> Tuple[bool, str]:
    """
    Validates both the filename extension and binary magic bytes to prevent
    executable or malicious files disguised with valid extensions.
    """
    filename = secure_filename(file_storage.filename)
    if not allowed_file(filename):
        return False, f"Unsupported file extension. Allowed extensions: {', '.join(Config.ALLOWED_EXTENSIONS)}"

    # Read the first 16 bytes to check file signature
    header = file_storage.read(16)
    file_storage.seek(0)

    detected_mime = None
    for magic, mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            detected_mime = mime
            break

    if detected_mime and detected_mime not in Config.ALLOWED_MIME_TYPES:
        return False, f"File content identified as {detected_mime}, which is not permitted."

    return True, "Valid"


def save_uploaded_file(file_storage, upload_folder: str = None) -> Tuple[str, str]:
    """
    Saves an uploaded file storage object to the uploads directory using a UUID filename.
    Returns (stored_filename, original_filename).
    """
    upload_folder = upload_folder or Config.UPLOAD_FOLDER
    os.makedirs(upload_folder, exist_ok=True)

    original_name = secure_filename(file_storage.filename) or "receipt"
    extension = original_name.rsplit(".", 1)[1].lower() if "." in original_name else "dat"

    unique_filename = f"{uuid.uuid4().hex}.{extension}"
    destination_path = os.path.join(upload_folder, unique_filename)

    file_storage.save(destination_path)
    return unique_filename, original_name


def serve_secure_file(stored_filename: str, original_filename: str = None, download_name: str = None):
    """
    Serves a stored receipt file securely:
    - Protects against directory traversal attacks via relative_to() verification.
    - Guesses accurate MIME type so images and PDFs open directly in the browser.
    """
    upload_folder = Path(Config.UPLOAD_FOLDER).resolve()
    target_path = (upload_folder / stored_filename).resolve()

    # Prevent directory traversal attacks
    try:
        target_path.relative_to(upload_folder)
    except ValueError:
        return jsonify({"success": False, "error": "Access denied: invalid file path."}), 403

    if not target_path.exists() or not target_path.is_file():
        return jsonify({"success": False, "error": "Requested receipt file does not exist on server."}), 404

    mime_type, _ = mimetypes.guess_type(str(target_path))
    if not mime_type and original_filename:
        mime_type, _ = mimetypes.guess_type(original_filename)
    if mime_type == "image/pjpeg":
        mime_type = "image/jpeg"
    mime_type = mime_type or "application/octet-stream"

    # Serve PDFs and images inline; force download for other types
    as_attachment = mime_type not in ("application/pdf", "image/png", "image/jpeg")

    return send_from_directory(
        directory=str(upload_folder),
        path=stored_filename,
        mimetype=mime_type,
        as_attachment=as_attachment,
        download_name=download_name or original_filename or stored_filename
    )
