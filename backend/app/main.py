from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import ASSETS_DIR, CORS_ORIGINS, UPLOADS_DIR
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, parent, public, student, teacher
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for stmt in (
            "ALTER TABLE examinations ADD COLUMN IF NOT EXISTS results_declared_at TIMESTAMP",
            "ALTER TABLE question_papers ADD COLUMN IF NOT EXISTS watermark_text VARCHAR(120)",
            "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS image_path TEXT",
            "ALTER TABLE institution_settings ADD COLUMN IF NOT EXISTS whatsapp_webhook_url VARCHAR(512)",
            "ALTER TABLE institution_settings ADD COLUMN IF NOT EXISTS whatsapp_group_id VARCHAR(160)",
            "ALTER TABLE institution_settings ADD COLUMN IF NOT EXISTS sms_webhook_url VARCHAR(512)",
            "ALTER TABLE institution_settings ADD COLUMN IF NOT EXISTS telegram_bot_token VARCHAR(255)",
            "ALTER TABLE institution_settings ADD COLUMN IF NOT EXISTS telegram_chat_id VARCHAR(120)",
            "ALTER TABLE institution_settings ADD COLUMN IF NOT EXISTS auto_notify_group_on_events BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS status VARCHAR(24) NOT NULL DEFAULT 'VERIFIED'",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS verified_by_user_id INTEGER",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP",
        ):
            conn.execute(text(stmt))
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="AKTP PORTAL — AK Tuition Educational Management API",
    version="1.0.0",
    description="Centralized full-stack backend connecting Admin, Teacher, Student, and Parent portals.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)
app.include_router(parent.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AKTP PORTAL API"}
