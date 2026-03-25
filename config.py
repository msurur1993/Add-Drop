import os
from pathlib import Path


def load_local_env(filename=".env"):
    env_path = Path(__file__).resolve().parent / filename
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def env_flag(name, default="false"):
    value = os.environ.get(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = str(os.environ.get(name, default)).strip()
    try:
        return int(value)
    except ValueError:
        return default


def infer_email_provider():
    explicit = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
    if explicit:
        return explicit

    if os.environ.get("RESEND_API_KEY", "").strip():
        return "resend"
    if os.environ.get("SMTP_HOST", "").strip():
        return "smtp"
    if (
        os.environ.get("GMAIL_SENDER", "").strip()
        or os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
    ):
        return "gmail_api"
    return ""


load_local_env()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
    # Use DB_DIR env var for persistent storage on Railway (mount a volume there)
    _db_dir = os.environ.get("DB_DIR", "")
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
        _default_db = f"sqlite:///{_db_dir}/addrop.db"
    else:
        _default_db = "sqlite:///addrop.db"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _default_db)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PeopleSoft class search
    PEOPLESOFT_URL = os.environ.get(
        "PEOPLESOFT_URL",
        "https://coursesearch92.ais.uchicago.edu/",
    )
    CURRENT_TERM = os.environ.get("CURRENT_TERM", "2264")  # Spring 2026

    # Scraper settings
    CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL", "50"))
    PLAYWRIGHT_HEADLESS = env_flag("PLAYWRIGHT_HEADLESS", "true")

    # Google OAuth (Sign in with Google)
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    GOOGLE_DISCOVERY_URL = os.environ.get(
        "GOOGLE_DISCOVERY_URL",
        "https://accounts.google.com/.well-known/openid-configuration",
    ).strip()
    GOOGLE_OAUTH_REDIRECT_URI = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()

    # Email notifications
    EMAIL_PROVIDER = infer_email_provider()
    EMAIL_FROM = os.environ.get("EMAIL_FROM", os.environ.get("GMAIL_SENDER", "")).strip()
    EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO", "").strip()
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
    SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
    SMTP_PORT = env_int("SMTP_PORT", 587)
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS = env_flag("SMTP_USE_TLS", "true")
    SMTP_USE_SSL = env_flag("SMTP_USE_SSL", "false")

    # Legacy Gmail API fallback
    GMAIL_SENDER = os.environ.get("GMAIL_SENDER", "").strip()
    GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", GOOGLE_CLIENT_ID).strip()
    GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", GOOGLE_CLIENT_SECRET).strip()
    GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
    GMAIL_TOKEN_URI = os.environ.get(
        "GMAIL_TOKEN_URI",
        "https://oauth2.googleapis.com/token",
    ).strip()

    # Local development fallback for Gmail OAuth
    GMAIL_CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json").strip()
    GMAIL_TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "token.json").strip()
    GMAIL_ENABLE_INTERACTIVE_AUTH = env_flag("GMAIL_ENABLE_INTERACTIVE_AUTH", "false")
