import os

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='template')
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key and os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError('SECRET_KEY must be set in production')
    app.config['SECRET_KEY'] = secret_key or 'local-development-only-change-me'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 'sqlite:///site.db'
    )
    db.init_app(app)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    )

    from app import model  # noqa: F401
    from app.routes.auth import auth_bp
    from app.routes.incidents import incidents_bp, weather_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(weather_bp)

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app