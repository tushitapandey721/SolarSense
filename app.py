import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from routes.main import main_bp
from routes.chat import chat_bp
from routes.admin import admin_bp

load_dotenv()  # reads .env into os.environ if present (no-op if missing)


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "solarsense-dev-secret-2024")

    CORS(app)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False)
