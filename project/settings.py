import os
from pathlib import Path

from corsheaders.defaults import default_headers
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "#v!*!fq6=x4ufwjtk9p18^*pzt4ex363h4ql!*zt3=cw^6=%s%")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "rest_framework",
    "corsheaders",
    "database",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "utils.request_log.RequestLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = (*default_headers, "x-tenant")

ROOT_URLCONF = "project.urls"
WSGI_APPLICATION = "project.wsgi.application"
ASGI_APPLICATION = "project.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
        "NAME": os.environ.get("MONGODB_DB", "care_companion"),
    }
}


CENTRAL_MONGODB_URI = os.environ.get("CENTRAL_MONGODB_URI", "")
CENTRAL_MONGODB_DB = os.environ.get(
    "CENTRAL_MONGODB_DB", "synaptix_central_admin_portal_demo"
)

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
    "EXCEPTION_HANDLER": "utils.common.exception_handler",
}


# --- OpenAI (Chat + Embeddings) ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS = int(os.environ.get("OPENAI_MAX_TOKENS", "1000"))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))

CARE_COMPANION_PHONE = os.environ.get("CARE_COMPANION_PHONE", "")

FRONTEND_PATH = os.environ.get("FRONTEND_PATH", "/chat")

ASSETS_URL = os.environ.get("ASSETS_URL", "http://localhost:8000/api/assets").rstrip("/")

MS_GRAPH_TENANT_ID = os.environ.get("MS_GRAPH_TENANT_ID", "")
MS_GRAPH_CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID", "")
MS_GRAPH_CLIENT_SECRET = os.environ.get("MS_GRAPH_CLIENT_SECRET", "")
MS_GRAPH_SENDER_EMAIL = os.environ.get("MS_GRAPH_SENDER_EMAIL", "")
MS_GRAPH_TIMEOUT = int(os.environ.get("MS_GRAPH_TIMEOUT", "15"))
MS_GRAPH_SAVE_TO_SENT_ITEMS = (
    os.environ.get("MS_GRAPH_SAVE_TO_SENT_ITEMS", "false").lower() == "true"
)

MS_GRAPH_CONFIGURED = all(
    (
        MS_GRAPH_TENANT_ID,
        MS_GRAPH_CLIENT_ID,
        MS_GRAPH_CLIENT_SECRET,
        MS_GRAPH_SENDER_EMAIL,
    )
)

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", MS_GRAPH_SENDER_EMAIL or "care-companion@example.com"
)

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "utils.graph_mail.GraphEmailBackend"
    if MS_GRAPH_CONFIGURED
    else "django.core.mail.backends.console.EmailBackend",
)

# --- Logging ---
# One file, one record per API call. FileHandler flushes on every record, so
# `tail -f logs/api.log` follows calls as they happen.
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "api": {
            "format": "%(asctime)s  %(levelname)-7s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "api_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "api.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "api",
        },
    },
    "loggers": {
        # The request/response record.
        "api": {"handlers": ["api_file"], "level": "INFO", "propagate": False},
        # Whatever the chat itself reports - a crisis or emergency alert - in
        # the same file, next to the call that caused it.
        "api.controllers": {
            "handlers": ["api_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"