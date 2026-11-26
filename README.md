# AKTP PORTAL — AK TUITION COMPLETE EDUCATIONAL MANAGEMENT SYSTEM

**Organization:** AK Tuition  
**Tagline:** Learn • Practise • Achieve  
**Director:** Mr. Akash, B.E.

---

## 1. Architecture Overview

AKTP PORTAL connects four role-isolated portals (**Administrator**, **Teacher**, **Student**, and **Parent**) plus a public-facing website to a single centralized **PostgreSQL** database through a **FastAPI** REST API.

- **Frontend (`/frontend`):** React 18, Vite, Tailwind CSS, React Router v6, Axios, Recharts, Lucide Icons.
- **Backend (`/backend`):** Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic, PyJWT, Argon2 (`argon2-cffi`), ReportLab (PDFs), OpenPyXL (Excel), HTTPX (MSG91 & WhatsApp Cloud).
- **Database:** PostgreSQL 18 (26+ normalized tables with FK constraints, unique constraints, and indexes).

---

## 2. Database Tables (PostgreSQL)

`users`, `roles`, `password_reset_tokens`, `academic_years`, `classes`, `subjects`, `class_subjects`, `teachers`, `teacher_assignments`, `teacher_attendance`, `parents`, `students`, `student_enrollments`, `attendance`, `examinations`, `examination_subjects`, `question_papers`, `questions`, `question_options`, `student_test_attempts`, `student_answers`, `marks`, `result_approvals`, `fees`, `payments`, `fee_receipts`, `notifications`, `announcements`, `audit_logs`, `institution_settings`.

---

## 3. Initial Seeded Credentials

| Portal | Username / ID | Default Password |
|---|---|---|
| **Admin** | `admin` | `Admin@123` |
| **Teacher** | `teacher1` / `teacher2` | `Teacher@123` |
| **Student** | `AK001` / `AK002` / `AK003` / `AK004` | `Student@123` |
| **Parent** | `parent1` / `parent2` / `parent3` / `parent4` | `Parent@123` |

> Change default passwords immediately in production via the **Change Password** menu in each portal.

---

## 4. Local Setup & Running

### 4.1 PostgreSQL
Ensure PostgreSQL is running and create the database `aktp_portal` (or set `DATABASE_URL` in `backend/.env`).
If using the local `.pgdata` cluster created in this workspace:
```powershell
$pgbin = "C:\Program Files\PostgreSQL\18\bin"
$pgdata = ".\.pgdata"
& "$pgbin\pg_ctl.exe" -D $pgdata -l "$pgdata\postgres.log" start
```

### 4.2 Backend (FastAPI)
```powershell
cd backend
copy .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs: `http://127.0.0.1:8000/docs`

### 4.3 Frontend (React + Vite)
```powershell
cd frontend
npm install
npm run dev
```
Open: `http://localhost:5173`

---

## 5. SMS (MSG91) & WhatsApp Business Cloud API

Configure credentials either in `backend/.env` or inside **Admin Portal → Settings & Audit**:
- **MSG91:** `MSG91_AUTH_KEY`, `MSG91_SENDER_ID`, `MSG91_TEMPLATE_ID` + enable Live SMS.
- **WhatsApp Business Cloud API:** `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` + enable Live WhatsApp.

When credentials are not configured, AKTP PORTAL never fakes delivery success — notifications are logged with status **`DEMO_SIMULATED`** and provider **`DEMO`** so admins can verify workflows safely.

---

## 6. Deployment Guide

### Frontend → Netlify
1. Connect your repository to Netlify with **Base directory:** `frontend`, **Build command:** `npm run build`, **Publish directory:** `frontend/dist`.
2. `frontend/netlify.toml` and `frontend/public/_redirects` are pre-configured so all React Router routes (`/login`, `/admin`, `/teacher`, `/student`, `/parent`) work on page refresh.
3. Set Netlify Environment Variable:
   - `VITE_API_BASE_URL=https://your-fastapi-backend-domain.com`

### Backend + PostgreSQL → Cloud Hosting (Render / Railway / Fly.io / AWS)
1. Provision a managed PostgreSQL instance (Neon, Supabase, RDS, or Render PostgreSQL).
2. Deploy `/backend` with start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
3. Set environment variables: `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS` (include your Netlify URL).
