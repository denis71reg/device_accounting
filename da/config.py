import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'devices.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_SESSION_OPTIONS = {"expire_on_commit": False}
    WTF_CSRF_TIME_LIMIT = None
    DEFAULT_LOCATIONS = (
        "Склад Основной",
        "Офис (Астана)",
        "Офис (Алматы)",
    )
    DEFAULT_DEVICE_TYPES = ("Mobile", "Laptop", "Monitor", "Tablet")
    LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "instance" / "logs"))
    LOG_FILE = str(LOG_DIR / "app.log")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Email/SMTP settings
    # Письма отправляются с da@ittest-team.ru на email супер-админа
    SMTP_HOST = os.getenv("SMTP_HOST", "mail.ittest-team.ru")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER", "da@ittest-team.ru")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # Security settings
    # SESSION_COOKIE_SECURE будет установлен динамически в зависимости от протокола
    # Используем переменную окружения или определяем по заголовкам
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    # Database connection pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }


class TestingConfig(Config):
    TESTING = True
    # Используем файл для тестов, чтобы данные сохранялись между запросами
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'test.db'}"
    WTF_CSRF_ENABLED = False
    LOG_LEVEL = "CRITICAL"


def get_config(env: str | None) -> type[Config]:
    mapping = {
        "production": ProductionConfig,
        "prod": ProductionConfig,
        "development": DevelopmentConfig,
        "dev": DevelopmentConfig,
        "testing": TestingConfig,
        "test": TestingConfig,
    }
    return mapping.get(env, Config)





