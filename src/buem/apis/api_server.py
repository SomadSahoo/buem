from flask import Flask, jsonify
import logging
import os
from logging.handlers import RotatingFileHandler

from buem.apis.model_api import bp as model_bp

LOG_FILE = "/app/logs/buem_api.log"

def create_app():
    app = Flask(__name__)
    app.register_blueprint(model_bp)

    # centralized logging - rotates to limit disk usage
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # also configure root logger to propagate to handlers (optional)
    logging.getLogger().addHandler(handler)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    app.logger.info(f"BUEM API starting, log: {LOG_FILE}")
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)