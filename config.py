import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def build_database_uri() -> str:
    """Resolve SQLAlchemy database URI with MySQL as the primary target."""
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    is_vercel = os.getenv("VERCEL") == "1"
    if os.getenv("ALLOW_SQLITE_FALLBACK", "0") == "1" or (is_vercel and not os.getenv("MYSQL_HOST")):
        if is_vercel:
            return "sqlite:////tmp/smart_study_planner_local.db"
        sqlite_path = os.path.join(BASE_DIR, "smart_study_planner_local.db")
        return f"sqlite:///{sqlite_path}"

    user = os.getenv("MYSQL_USER", "root")
    password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "smart_study_planner")

    auth = f"{user}:{password}" if password else user
    return f"mysql+pymysql://{auth}@{host}:{port}/{database}?charset=utf8mb4"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-smart-study-planner-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    JSON_SORT_KEYS = False

