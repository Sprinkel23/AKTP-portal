import hashlib
import secrets
from datetime import date, datetime, timedelta
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import GEMINI_API_KEY
from app.database import get_db
from app.models import Announcement, Attendance, Examination, Mark, OtpCode, Parent, ResultApproval, SchoolClass, Student, Subject, Teacher, User
from app.schemas import (
    AiAssistantRequest,
    ContactInquiryRequest,
    PublicResultLookupRequest,
    PublicResultOtpRequest,
)
from app.security import create_signed_payload, decode_signed_payload, get_optional_user, log_audit
from app.services.helpers import compute_class_rank, compute_grade, get_or_create_settings
from app.services.notifications import build_direct_links, send_notification
from app.services.pdf_generator import generate_marks_card_pdf, number_to_words, result_division

router = APIRouter(prefix="/api/public", tags=["Public"])


@router.get("/home")
def get_public_home(db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(SchoolClass.grade_level).all()
    subjects = db.query(Subject).filter(Subject.is_active == True).order_by(Subject.name).all()
    teachers = db.query(Teacher).filter(Teacher.is_active == True).all()
    announcements = (
        db.query(Announcement)
        .filter(Announcement.is_published == True, Announcement.target_audience.in_(["PUBLIC", "ALL"]))
        .order_by(Announcement.created_at.desc())
        .limit(20)
        .all()
    )
    upcoming_exams = (
        db.query(Examination)
        .filter(
            Examination.is_timetable_published == True,
            Examination.status != "CANCELLED",
            Examination.end_date >= date.today(),
        )
        .order_by(Examination.start_date.asc())
        .limit(6)
        .all()
    )

    student_count = db.query(Student).filter(Student.is_active == True).count()

    return {
        "institution": {
            "tuition_name": settings.tuition_name,
            "tagline": settings.tagline,
            "director_name": settings.director_name,
            "director_designation": settings.director_designation,
            "phone": settings.phone,
            "email": settings.email,
            "address": settings.address,
            "academic_year": settings.academic_year_label,
            "logo_url": settings.logo_path or "/assets/ak-tuition-logo.png",
        },
        "stats": {
            "total_students": student_count,
            "total_teachers": len(teachers),
            "total_classes": len(classes),
            "total_subjects": len(subjects),
        },
        "classes": [
            {
                "id": c.id,
                "grade_level": c.grade_level,
                "name": c.name,
                "section": c.section,
            }
            for c in classes
        ],
        "subjects": [
            {"id": s.id, "name": s.name, "code": s.code, "description": s.description}
            for s in subjects
        ],
        "teachers": [
            {
                "id": t.id,
                "name": t.teacher_name,
                "qualification": t.qualification,
                "specialization": t.specialization,
            }
            for t in teachers
        ],
        "announcements": [
            {
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "content": a.content,
                "event_date": a.event_date.isoformat() if a.event_date else None,
                "is_featured": a.is_featured,
                "image_path": a.image_path,
                "created_at": a.created_at.isoformat(),
            }
            for a in announcements
        ],
        "upcoming_examinations": [
            {
                "id": ex.id,
                "name": ex.name,
                "class_name": f"{ex.school_class.name} - {ex.school_class.section}" if ex.school_class else "",
                "exam_type": ex.exam_type,
                "start_date": ex.start_date.isoformat(),
                "end_date": ex.end_date.isoformat(),
            }
            for ex in upcoming_exams
        ],
    }


@router.post("/contact")
def submit_contact_inquiry(payload: ContactInquiryRequest, request: Request, db: Session = Depends(get_db)):
    log_audit(
        db,
        user_id=None,
        action="PUBLIC_CONTACT_INQUIRY",
        entity_type="contact_inquiry",
        details=payload.model_dump(),
        request=request,
    )
    db.commit()
    return {
        "status": "received",
        "message": "Thank you for contacting AK Tuition! Our admissions coordinator will reach out shortly.",
    }


@router.get("/classes")
def get_public_classes(db: Session = Depends(get_db)):
    classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(SchoolClass.grade_level.asc(), SchoolClass.section.asc()).all()
    return [
        {"id": c.id, "grade_level": c.grade_level, "name": c.name, "section": c.section}
        for c in classes
    ]


def _get_result_expiry_info(db: Session, ex: Examination) -> tuple[bool, datetime, datetime, int]:
    declared_at = getattr(ex, "results_declared_at", None)
    if not declared_at:
        ap = (
            db.query(ResultApproval)
            .filter(ResultApproval.examination_id == ex.id, ResultApproval.status == "PUBLISHED")
            .order_by(ResultApproval.approval_date.desc())
            .first()
        )
        declared_at = (ap.approval_date if ap and ap.approval_date else ex.created_at) or datetime.utcnow()
    expires_at = declared_at + timedelta(days=15)
    now = datetime.utcnow()
    is_expired = now > expires_at
    if is_expired:
        days_remaining = 0
    else:
        delta = expires_at - now
        days_remaining = max(1, delta.days + (1 if delta.seconds > 0 else 0))
    return is_expired, declared_at, expires_at, days_remaining


@router.get("/verify-markscard")
def verify_markscard(code: str, exam: Optional[int] = None, db: Session = Depends(get_db)):
    st = db.query(Student).filter(func.lower(Student.student_code) == code.strip().lower()).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student record not found for verification.")
    q = db.query(Mark).filter(Mark.student_id == st.id, Mark.status == "PUBLISHED")
    if exam:
        q = q.filter(Mark.examination_id == exam)
    marks = q.order_by(Mark.examination_id.desc(), Mark.id.asc()).all()
    if not marks:
        raise HTTPException(status_code=404, detail="No published examination marks found for this QR code.")
    target_exam_id = exam or marks[0].examination_id
    marks = [m for m in marks if m.examination_id == target_exam_id]
    ex = db.query(Examination).filter(Examination.id == target_exam_id).first()
    if ex:
        is_expired, declared_at, expires_at, days_remaining = _get_result_expiry_info(db, ex)
        if is_expired:
            raise HTTPException(
                status_code=410,
                detail="This public result link has expired after the 15-day declaration window. Please log in to the Student or Parent Portal for permanent records.",
            )
    else:
        declared_at = datetime.utcnow()
        expires_at = declared_at + timedelta(days=15)
        days_remaining = 15
    settings = get_or_create_settings(db)
    total_max = sum(float(m.max_marks) for m in marks)
    total_obt = sum(float(m.marks_obtained) for m in marks)
    pct = round((total_obt / total_max) * 100, 2) if total_max else 0.0
    grade, remark = compute_grade(pct, settings.grading_rules)
    rank, class_tot = compute_class_rank(db, target_exam_id, st.class_id, st.id)
    return {
        "verified": True,
        "tuition_name": settings.tuition_name,
        "director_name": settings.director_name,
        "student_code": st.student_code,
        "student_name": st.student_name,
        "class_name": st.school_class.name if st.school_class else "",
        "section": st.section,
        "examination_id": target_exam_id,
        "examination_name": ex.name if ex else "",
        "declared_at": declared_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "days_remaining": days_remaining,
        "total_max": total_max,
        "total_obtained": total_obt,
        "percentage": pct,
        "overall_grade": grade,
        "result_status": result_division(pct, any(float(m.marks_obtained) < round(float(m.max_marks) * 0.35) for m in marks)),
        "class_rank": rank,
        "class_total_students": class_tot,
        "teacher_remarks": remark,
        "subjects": [
            {
                "subject": m.subject.name if m.subject else "",
                "max_marks": float(m.max_marks),
                "min_marks": round(float(m.max_marks) * 0.35),
                "marks_obtained": float(m.marks_obtained),
                "marks_in_words": number_to_words(float(m.marks_obtained)),
                "subject_result": "PASS" if float(m.marks_obtained) >= round(float(m.max_marks) * 0.35) else "FAIL",
                "grade": m.grade,
            }
            for m in marks
        ],
    }


def _captcha_hash(code: str) -> str:
    return hashlib.sha256(code.upper().encode("utf-8")).hexdigest()


def _build_captcha_svg(code: str) -> str:
    rng = secrets.SystemRandom()
    chars_svg = []
    x = 18
    palette = ["#0A2463", "#7C1D24", "#1E40AF", "#0F172A", "#15803D"]
    for ch in code:
        y = rng.randint(28, 37)
        rot = rng.randint(-18, 18)
        col = rng.choice(palette)
        chars_svg.append(
            f'<text x="{x}" y="{y}" fill="{col}" font-size="25" font-weight="800" '
            f'font-family="monospace, sans-serif" transform="rotate({rot} {x} {y - 8})">{ch}</text>'
        )
        x += 26
    lines_svg = []
    for _ in range(5):
        x1, y1 = rng.randint(2, 150), rng.randint(4, 44)
        x2, y2 = rng.randint(2, 150), rng.randint(4, 44)
        lines_svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#94A3B8" stroke-width="1.2" opacity="0.65" />')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="48" viewBox="0 0 160 48">'
        '<rect width="160" height="48" rx="6" fill="#EFF6FF" stroke="#0A2463" stroke-width="1.2"/>'
        + "".join(lines_svg)
        + "".join(chars_svg)
        + "</svg>"
    )


@router.get("/result-captcha")
def get_result_captcha():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(secrets.choice(alphabet) for _ in range(5))
    token = create_signed_payload({"cap": _captcha_hash(code)}, expire_minutes=15)
    return {"captcha_token": token, "svg": _build_captcha_svg(code)}


def _find_student_by_register_no(db: Session, raw_reg: str) -> Optional[Student]:
    cleaned = "".join(ch for ch in (raw_reg or "").strip() if ch.isalnum()).upper()
    if not cleaned:
        return None
    st = db.query(Student).filter(func.upper(Student.student_code) == cleaned, Student.is_active == True).first()
    if st:
        return st
    # Support Register No. with section suffix such as AK001A
    for candidate in db.query(Student).filter(Student.is_active == True).all():
        full_reg = f"{candidate.student_code}{candidate.section or ''}".upper()
        if full_reg == cleaned:
            return candidate
    return None


@router.post("/results/request-otp")
def request_public_result_otp(payload: PublicResultOtpRequest, request: Request, db: Session = Depends(get_db)):
    digits = "".join(ch for ch in payload.phone if ch.isdigit())
    if len(digits) < 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit registered mobile number.")
    tail10 = digits[-10:]
    st = (
        db.query(Student)
        .filter(
            ((Student.student_phone.endswith(tail10)) | (Student.parent_phone.endswith(tail10))),
            Student.is_active == True,
        )
        .first()
    )
    if not st:
        raise HTTPException(status_code=404, detail="No active student found for this registered mobile number.")
    otp = f"{secrets.randbelow(900000) + 100000}"
    db.query(OtpCode).filter(OtpCode.user_id == st.user_id, OtpCode.used == False).update({"used": True})
    db.add(OtpCode(
        user_id=st.user_id,
        phone=tail10,
        code=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    msg = f"AK Tuition Examination Result OTP: {otp}. Valid for 10 minutes."
    notif = send_notification(
        db,
        recipient_phone=st.student_phone or st.parent_phone,
        channel="WHATSAPP",
        notification_type="RESULT_OTP",
        message=msg,
        dedup_key=f"RESOTP_{st.id}_{datetime.utcnow().isoformat()}",
        recipient_user_id=st.user_id,
        student_id=st.id,
    )
    log_audit(db, st.user_id, "PUBLIC_RESULT_OTP", "student", st.student_code, None, request)
    db.commit()
    resp = {"message": "Verification OTP generated for your registered mobile number.", "delivery_status": notif.status}
    if notif.status != "SENT":
        resp["otp_preview"] = otp
    return resp


def _format_official_result_payload(db: Session, st: Student, target_exam_id: int) -> dict:
    ex = db.query(Examination).filter(Examination.id == target_exam_id).first()
    marks = (
        db.query(Mark)
        .filter(Mark.student_id == st.id, Mark.examination_id == target_exam_id, Mark.status == "PUBLISHED")
        .order_by(Mark.id.asc())
        .all()
    )
    if not ex or not marks:
        raise HTTPException(status_code=404, detail="No published marks found for this examination.")
    settings = get_or_create_settings(db)
    total_max = sum(float(m.max_marks) for m in marks)
    total_obt = sum(float(m.marks_obtained) for m in marks)
    pct = round((total_obt / total_max) * 100, 2) if total_max else 0.0
    grade, remark = compute_grade(pct, settings.grading_rules)
    any_fail = any(float(m.marks_obtained) < round(float(m.max_marks) * 0.35) for m in marks)
    div_res = result_division(pct, any_fail)
    rank, class_tot = compute_class_rank(db, ex.id, st.class_id, st.id)
    is_expired, declared_at, expires_at, days_remaining = _get_result_expiry_info(db, ex)
    if is_expired:
        raise HTTPException(
            status_code=410,
            detail="This declared result link has expired (15-day public access window ended). Please log in to the Student or Parent Portal for archive access.",
        )
    dl_token = create_signed_payload({"sid": st.id, "exid": ex.id}, expire_minutes=30)
    return {
        "examination_id": ex.id,
        "examination_name": ex.name,
        "declared_at": declared_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "days_remaining": days_remaining,
        "exam_date": f"{ex.start_date.strftime('%d %b %Y')} - {ex.end_date.strftime('%d %b %Y')}",
        "academic_year": settings.academic_year_label,
        "student_code": st.student_code,
        "register_number": f"{st.student_code}{st.section or ''}",
        "student_name": st.student_name,
        "class_name": st.school_class.name if st.school_class else "",
        "section": st.section,
        "total_max": total_max,
        "total_obtained": total_obt,
        "total_in_words": number_to_words(total_obt),
        "percentage": pct,
        "overall_grade": grade,
        "result_status": div_res,
        "teacher_remarks": remark,
        "class_rank": rank,
        "class_total_students": class_tot,
        "director_name": settings.director_name,
        "director_designation": settings.director_designation,
        "director_signature_path": settings.director_signature_path,
        "certificate_id": f"AKTP-DSIG-{hashlib.sha256(f'{st.student_code}|{ex.id}|{total_obt}|{pct}'.encode()).hexdigest()[:10].upper()}",
        "download_token": dl_token,
        "subjects": [
            {
                "subject": m.subject.name if m.subject else "",
                "max_marks": float(m.max_marks),
                "min_marks": round(float(m.max_marks) * 0.35),
                "marks_obtained": float(m.marks_obtained),
                "marks_in_words": number_to_words(float(m.marks_obtained)),
                "subject_result": "PASS" if float(m.marks_obtained) >= round(float(m.max_marks) * 0.35) else "FAIL",
                "grade": m.grade,
                "remarks": m.remarks or "-",
            }
            for m in marks
        ],
    }


@router.get("/results/announcements")
def get_announced_results_status(db: Session = Depends(get_db)):
    published_exam_ids = {m[0] for m in db.query(Mark.examination_id).filter(Mark.status == "PUBLISHED").distinct().all()}
    exams = (
        db.query(Examination)
        .filter(Examination.id.in_(published_exam_ids))
        .order_by(Examination.start_date.desc())
        .all()
        if published_exam_ids
        else []
    )
    result_notices = (
        db.query(Announcement)
        .filter(Announcement.is_published == True, Announcement.category == "RESULT")
        .order_by(Announcement.created_at.desc())
        .limit(10)
        .all()
    )
    return {
        "declared_exams": [
            {
                "id": ex.id,
                "name": ex.name,
                "class_name": f"{ex.school_class.name} ({ex.school_class.section})" if ex.school_class else "",
                "exam_date": f"{ex.start_date.strftime('%d %b %Y')}",
                "is_expired": exp_info[0],
                "declared_at": exp_info[1].isoformat(),
                "expires_at": exp_info[2].isoformat(),
                "days_remaining": exp_info[3],
            }
            for ex in exams
            for exp_info in [_get_result_expiry_info(db, ex)]
        ],
        "announcements": [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "image_path": a.image_path,
                "created_at": a.created_at.isoformat(),
            }
            for a in result_notices
        ],
    }


@router.post("/results/lookup")
def public_result_lookup(payload: PublicResultLookupRequest, db: Session = Depends(get_db)):
    cap_data = decode_signed_payload(payload.captcha_token)
    ans_hash = _captcha_hash((payload.captcha_answer or "").strip())
    if cap_data.get("cap") != ans_hash:
        raise HTTPException(status_code=400, detail="Invalid CAPTCHA code. Please try again.")

    st = None
    mode = (payload.mode or "register_no").lower()
    if mode == "otp":
        digits = "".join(ch for ch in (payload.phone or "") if ch.isdigit())
        if len(digits) < 10:
            raise HTTPException(status_code=400, detail="Enter a valid 10-digit registered mobile number.")
        tail10 = digits[-10:]
        st = (
            db.query(Student)
            .filter(
                ((Student.student_phone.endswith(tail10)) | (Student.parent_phone.endswith(tail10))),
                Student.is_active == True,
            )
            .first()
        )
        if not st:
            raise HTTPException(status_code=404, detail="No active student found for this mobile number.")
        otp_row = (
            db.query(OtpCode)
            .filter(OtpCode.user_id == st.user_id, OtpCode.code == (payload.otp_code or "").strip(), OtpCode.used == False)
            .order_by(OtpCode.id.desc())
            .first()
        )
        if not otp_row or otp_row.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired OTP code.")
        otp_row.used = True
        db.commit()
    else:
        st = _find_student_by_register_no(db, payload.register_no or "")
        if not st:
            raise HTTPException(status_code=404, detail="Student Register Number not found (e.g. AK001 or AK001A).")

    pub_marks = (
        db.query(Mark)
        .filter(Mark.student_id == st.id, Mark.status == "PUBLISHED")
        .order_by(Mark.examination_id.desc())
        .all()
    )
    if not pub_marks:
        raise HTTPException(status_code=404, detail="Results for this student are not published yet.")

    exam_ids = []
    for m in pub_marks:
        if m.examination_id not in exam_ids:
            exam_ids.append(m.examination_id)

    active_exam_ids = []
    available_exams = []
    for eid in exam_ids:
        ex_obj = db.query(Examination).filter(Examination.id == eid).first()
        if ex_obj:
            exp, _, _, rem = _get_result_expiry_info(db, ex_obj)
            available_exams.append({"id": ex_obj.id, "name": ex_obj.name, "is_expired": exp, "days_remaining": rem})
            if not exp:
                active_exam_ids.append(eid)

    if payload.examination_id and payload.examination_id in exam_ids:
        target_ex_id = payload.examination_id
    elif active_exam_ids:
        target_ex_id = active_exam_ids[0]
    else:
        raise HTTPException(
            status_code=410,
            detail="Declared public result links for this student have expired after 15 days. Please log in to the Student or Parent Portal for archive access.",
        )

    return {
        "available_examinations": available_exams,
        "result": _format_official_result_payload(db, st, target_ex_id),
    }


@router.get("/results/pdf")
def download_public_marks_card_pdf(token: str = Query(...), db: Session = Depends(get_db)):
    data = decode_signed_payload(token)
    sid = data.get("sid")
    exid = data.get("exid")
    st = db.query(Student).filter(Student.id == sid).first()
    ex = db.query(Examination).filter(Examination.id == exid).first()
    if not st or not ex:
        raise HTTPException(status_code=404, detail="Marks card record not found.")
    is_expired, _, _, _ = _get_result_expiry_info(db, ex)
    if is_expired:
        raise HTTPException(
            status_code=410,
            detail="This public result download link has expired after 15 days. Log in to Student/Parent Portal to download.",
        )
    marks = (
        db.query(Mark)
        .filter(Mark.student_id == st.id, Mark.examination_id == ex.id, Mark.status == "PUBLISHED")
        .order_by(Mark.id.asc())
        .all()
    )
    if not marks:
        raise HTTPException(status_code=404, detail="No published marks found.")
    settings = get_or_create_settings(db)
    total_max = sum(float(m.max_marks) for m in marks)
    total_obt = sum(float(m.marks_obtained) for m in marks)
    pct = round((total_obt / total_max) * 100, 2) if total_max else 0.0
    grade, remark = compute_grade(pct, settings.grading_rules)
    rank, class_tot = compute_class_rank(db, ex.id, st.class_id, st.id)
    pdf_bytes = generate_marks_card_pdf(
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
        director_name=settings.director_name,
        director_designation=settings.director_designation,
        logo_path=settings.logo_path,
        signature_path=settings.director_signature_path,
        academic_year=settings.academic_year_label,
        exam_name=ex.name,
        exam_date=f"{ex.start_date.strftime('%d %b %Y')} - {ex.end_date.strftime('%d %b %Y')}",
        student_name=st.student_name,
        student_code=st.student_code,
        class_name=st.school_class.name if st.school_class else "",
        section=st.section,
        subjects=[
            {"subject": m.subject.name if m.subject else "", "max_marks": float(m.max_marks), "marks_obtained": float(m.marks_obtained), "grade": m.grade, "remarks": m.remarks or "-"}
            for m in marks
        ],
        total_max=total_max,
        total_obtained=total_obt,
        percentage=pct,
        overall_grade=grade,
        result_status="PASS" if pct >= 35 else "FAIL",
        teacher_remarks=remark,
        class_rank=rank,
        class_total_students=class_tot,
        examination_id=ex.id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AK_MarksCard_{st.student_code}_Exam{ex.id}.pdf"'},
    )


@router.post("/ai-assistant")
def ak_ai_assistant(
    payload: AiAssistantRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    settings = get_or_create_settings(db)
    q_text = payload.message.strip()
    q_lower = q_text.lower()

    context_lines = [
        f"Institution: {settings.tuition_name} ({settings.tagline}), Director: {settings.director_name}, Phone: {settings.phone}, Email: {settings.email}, Academic Year: {settings.academic_year_label}.",
        "Portal URL: https://aktp-portal.netlify.app | Public Result Lookup (Register No./OTP + Captcha): https://aktp-portal.netlify.app/results",
    ]
    user_summary = ""
    if current_user and current_user.role:
        role = current_user.role.name
        context_lines.append(f"Signed-in user: {current_user.full_name} (role={role}, username={current_user.username}).")
        if role == "student" and current_user.student_profile:
            st = current_user.student_profile
            tot_att = db.query(Attendance).filter(Attendance.student_id == st.id).count()
            pres_att = db.query(Attendance).filter(Attendance.student_id == st.id, Attendance.status == "PRESENT").count()
            pct_att = round((pres_att / tot_att) * 100, 1) if tot_att else 0.0
            abs_rows = db.query(Attendance).filter(Attendance.student_id == st.id, Attendance.status == "ABSENT").order_by(Attendance.attendance_date.desc()).limit(5).all()
            abs_dates = ", ".join(a.attendance_date.isoformat() for a in abs_rows) or "None"
            pub_marks = db.query(Mark).filter(Mark.student_id == st.id, Mark.status == "PUBLISHED").order_by(Mark.examination_id.desc()).all()
            marks_str = "; ".join(
                f"{m.examination.name if m.examination else ''} - {m.subject.name if m.subject else ''}: {float(m.marks_obtained):g}/{float(m.max_marks):g} ({m.grade})"
                for m in pub_marks[:8]
            ) or "No published marks yet"
            user_summary = (
                f"Student {st.student_name} ({st.student_code}, {st.school_class.name if st.school_class else ''}): "
                f"Attendance {pct_att}% ({pres_att}/{tot_att} days), Absent dates: {abs_dates}. Published Marks: {marks_str}."
            )
            context_lines.append(user_summary)

    upcoming = (
        db.query(Examination)
        .filter(Examination.is_timetable_published == True, Examination.status != "CANCELLED", Examination.end_date >= date.today())
        .order_by(Examination.start_date.asc())
        .limit(4)
        .all()
    )
    if upcoming:
        ex_list = "; ".join(f"{e.name} ({e.school_class.name if e.school_class else ''}: {e.start_date} to {e.end_date})" for e in upcoming)
        context_lines.append(f"Upcoming published examinations: {ex_list}.")

    if GEMINI_API_KEY:
        try:
            sys_prompt = (
                "You are AKTP AI Academic Assistant for AK Tuition (Director: G. Akash, B.E.). "
                "Answer concisely, accurately, and politely using ONLY the provided institutional/database context for AK Tuition data, "
                "plus clear academic explanations for school subjects (Maths, Science, English, Social Studies, CS, Hindi Classes 1-10).\n\n"
                + "\n".join(context_lines)
            )
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"role": "user", "parts": [{"text": f"{sys_prompt}\n\nUser question: {q_text}"}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 450},
                },
                timeout=12.0,
            )
            if r.status_code == 200:
                cands = r.json().get("candidates") or []
                parts = cands[0].get("content", {}).get("parts", []) if cands else []
                txt = "".join(p.get("text", "") for p in parts).strip()
                if txt:
                    return {"reply": txt, "mode": "GEMINI_LIVE"}
        except Exception:
            pass

    # Deterministic grounded fallback assistant (zero external key required)
    if any(w in q_lower for w in ["result", "mark", "marks card", "rank", "download", "score"]):
        base = "You can view & download your digitally signed AK Tuition Statement of Marks anytime at **/results** (enter your Register No. like `AK001` or `AK001A` + Captcha, OR verify via Registered Mobile OTP + Captcha)."
        if user_summary:
            base = f"Here is your live academic summary:\n{user_summary}\n\n{base}"
        return {"reply": base, "mode": "AKTP_GROUNDED"}

    if any(w in q_lower for w in ["attend", "absent", "present"]):
        if user_summary:
            return {"reply": user_summary, "mode": "AKTP_GROUNDED"}
        return {
            "reply": "Students and Parents can view overall Attendance % and exact **Absent-only dates** inside the Student Portal or Parent Portal (Parent login uses registered phone number only). Whenever a teacher marks a student absent, an instant WhatsApp/SMS alert is prepared for the registered number.",
            "mode": "AKTP_GROUNDED",
        }

    if any(w in q_lower for w in ["exam", "timetable", "schedule", "date"]):
        if upcoming:
            lines = "\n".join(f"- **{e.name}** ({e.school_class.name if e.school_class else ''}): {e.start_date} to {e.end_date}" for e in upcoming)
            return {"reply": f"Upcoming published examinations:\n{lines}", "mode": "AKTP_GROUNDED"}
        return {"reply": "No upcoming examination timetables are currently published. Check back in the Exam Timetables section or Notices.", "mode": "AKTP_GROUNDED"}

    if any(w in q_lower for w in ["contact", "phone", "director", "akash", "email", "address"]):
        return {
            "reply": f"**{settings.tuition_name}** is directed by **{settings.director_name}** ({settings.director_designation}). Phone: **{settings.phone}** • Email: **{settings.email}** • Address: {settings.address}.",
            "mode": "AKTP_GROUNDED",
        }

    if any(w in q_lower for w in ["signup", "sign up", "register", "login", "password", "otp"]):
        return {
            "reply": "**How AKTP Portal Access Works:**\n- **Results Without Login:** Open **/results** with your AK Register No. (e.g. `AK001A`) + Captcha or Mobile + OTP.\n- **New Student Sign Up:** Use the *New Student Sign Up* tab on the home page with your Name, Class & Mobile Number to auto-create your ID & Password.\n- **Parents:** Enter your registered phone number only on the Parent tab.\n- **Teachers:** Sign in with your access key or Registered Mobile + OTP.",
            "mode": "AKTP_GROUNDED",
        }

    return {
        "reply": (
            f"Hello! I'm the **AKTP AI Academic Assistant** for {settings.tuition_name}.\n"
            "Ask me about:\n"
            "• Checking/downloading your **Official Marks Card** (`/results`)\n"
            "• Your **attendance %, absent dates, or class rank**\n"
            "• **Upcoming exam timetables** & **student sign-up / OTP help**\n"
            f"• Contacting Director **{settings.director_name}** (`{settings.phone}`)"
        ),
        "mode": "AKTP_GROUNDED",
    }
