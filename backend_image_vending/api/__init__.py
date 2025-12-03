import os
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache

jwt = JWTManager()
cache = Cache()


def create_app():
    app = Flask(__name__)

    register_blueprints(app)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token"
    app.config["JWT_ACCESS_CSRF_COOKIE_NAME"] = "csrf_access_token"
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    CORS(app)
    jwt.init_app(app)
    cache.init_app(app)
    return app


def register_blueprints(app):
    from .tile.routes import tile

    app.register_blueprint(tile)
