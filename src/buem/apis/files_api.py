from flask import Blueprint, send_from_directory, current_app, jsonify
import os

bp = Blueprint("files_api", __name__, url_prefix="/api/files")

# directory to store/download large results (set via env BUEM_RESULTS_DIR or fallback)
RESULTS_DIR = os.environ.get("BUEM_RESULTS_DIR", r"C:\test\buem\results")

@bp.route("/<path:filename>", methods=["GET"])
def download_file(filename):
    if not os.path.isdir(RESULTS_DIR):
        try:
            os.makedirs(RESULTS_DIR, exist_ok=True)
        except Exception:
            current_app.logger.exception("Failed to create results dir")
            return jsonify({"error": "server_error"}), 500
    # sanitize: prevent path traversal by only serving from RESULTS_DIR
    return send_from_directory(RESULTS_DIR, filename, as_attachment=True)