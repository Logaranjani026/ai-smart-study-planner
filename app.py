import os
import sys
from flask import Flask, jsonify, request
from sqlalchemy import text
from config import Config
from models import db
from routes import auth_bp, pages_bp, api_bp


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    if os.getenv("VERCEL") == "1" and not app.config.get("TESTING"):
        with app.app_context():
            db.create_all()
            from database.init_db import seed_sample_data
            seed_sample_data()

    @app.errorhandler(404)
    def handle_404(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Endpoint not found"}), 404
        return "Page not found", 404

    @app.errorhandler(500)
    def handle_500(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Internal server error"}), 500
        return "Internal server error", 500

    return app


app = create_app()


if __name__ == "__main__":
    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:
            print(
                f"\n[Database Error] Could not connect to configured database:\n  {exc}\n"
                "Make sure MySQL is running, update .env from .env.example, and run:\n"
                "  python database/init_db.py\n"
                "(Or set ALLOW_SQLITE_FALLBACK=1 in .env for local offline SQLite preview.)\n"
            )
            sys.exit(1)

    app.run(host="127.0.0.1", port=5000, debug=True)
