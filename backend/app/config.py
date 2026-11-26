import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

_raw_database_url = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:aktp_postgres_pass@127.0.0.1:5433/aktp_portal",
)
if _raw_database_url.startswith("postgres://"):
    _raw_database_url = _raw_database_url.replace("postgres://", "postgresql://", 1)
DATABASE_URL = _raw_database_url
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "aktp-portal-dev-secret-key-change-in-prod-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    ).split(",")
    if origin.strip()
]

ASSETS_DIR = BASE_DIR / "assets"
UPLOADS_DIR = BASE_DIR / "uploads"
STUDENT_PHOTOS_DIR = UPLOADS_DIR / "student_photos"
SIGNATURES_DIR = UPLOADS_DIR / "signatures"
LOGOS_DIR = UPLOADS_DIR / "logos"
RECEIPTS_DIR = UPLOADS_DIR / "receipts"

for d in [ASSETS_DIR, UPLOADS_DIR, STUDENT_PHOTOS_DIR, SIGNATURES_DIR, LOGOS_DIR, RECEIPTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_LOGO_PATH = ASSETS_DIR / "ak-tuition-logo.png"

MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY", "")
MSG91_SENDER_ID = os.getenv("MSG91_SENDER_ID", "AKTUIT")
MSG91_TEMPLATE_ID = os.getenv("MSG91_TEMPLATE_ID", "")

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")
