"""
Фабрика приложения, подключение расширений и регистрация blueprints
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_compress import Compress
from flask_talisman import Talisman
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите, чтобы увидеть эту страницу'

cache = Cache()
compress = Compress()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    compress.init_app(app)

    # Политика безопасности контента — разрешен CDN для стилей и скриптов
    csp = {
        'default-src': "'self'",
        'style-src': ["'self'", 'https://cdn.jsdelivr.net', "'unsafe-inline'"],
        'script-src': ["'self'", 'https://cdn.jsdelivr.net', 'https://code.jquery.com', "'unsafe-inline'"],
        'img-src': ["'self'", 'data:'],
    }
    Talisman(app, content_security_policy=csp, force_https=False)

    from app.routes.index import index_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.dispatcher import dispatcher_bp
    from app.routes.worker import worker_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(index_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(dispatcher_bp)
    app.register_blueprint(worker_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()

    return app