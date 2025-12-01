from __future__ import annotations

import logging
import os
from logging.config import dictConfig
from pathlib import Path
from typing import Optional

from flask import Flask, got_request_exception

from datetime import datetime, timezone

from .config import get_config
from .extensions import csrf, db, login_manager, migrate
from .models import User
from .routes import register_blueprints
from .seed import register_seed_commands


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return User.query.get(int(user_id))


def create_app(config_name: Optional[str] = None) -> Flask:
    app = Flask("DA", instance_relative_config=True)

    config = get_config(config_name or os.getenv("FLASK_ENV"))
    app.config.from_object(config)

    os.makedirs(app.instance_path, exist_ok=True)
    Path(app.config["LOG_DIR"]).mkdir(parents=True, exist_ok=True)

    setup_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Пожалуйста, войдите в систему для доступа к этой странице."
    login_manager.login_message_category = "info"

    register_blueprints(app)
    register_seed_commands(app)

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        return {
            "current_year": datetime.now(timezone.utc).year,
            "current_user": current_user,
        }

    def log_exception(sender, exception, **extra):
        sender.logger.exception("Unhandled exception", exc_info=exception)

    got_request_exception.connect(log_exception, app)

    return app


def setup_logging(app: Flask) -> None:
    log_level = app.config.get("LOG_LEVEL", "INFO")
    log_file = app.config.get("LOG_FILE")

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": log_level,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "detailed",
                    "level": log_level,
                    "filename": log_file,
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 5,
                },
            },
            "root": {
                "level": log_level,
                "handlers": ["console", "file"],
            },
            "loggers": {
                "sqlalchemy.engine": {"level": "WARNING"},
                "werkzeug": {"level": "WARNING"},
            },
        }
    )
