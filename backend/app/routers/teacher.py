import uuid
from datetime import date, datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AcademicYear,
    Attendance,
    Examination,
    ExaminationSubject,
    Fee,
    FeeReceipt,
    Mark,
    Parent,
    Payment,
    Question,
    QuestionOption,
    QuestionPaper,
    ResultApproval,
    Role,
    SchoolClass,
    Student,
    StudentAnswer,
    StudentEnrollment,
    StudentTestAttempt,
    Subject,
    Teacher,
    TeacherAssignment,
    User,
)
from app.schemas import (
    AttemptEvaluationInput,
    AttendanceBulkCreate,
    MarksBulkEntry,
    QuestionPaperCreate,
    TeacherAllSubjectsMarksEntry,
    TeacherDirectMarksEntry,
    TeacherFeeCollectRequest,
    TeacherStudentCreate,
)
from app.security import create_signed_payload, hash_password, log_audit, require_roles
from app.services.helpers import (
    compute_class_rank,
    compute_grade,
    generate_next_student_code,
    generate_unique_password,
    get_or_create_settings,
)
from app.services.notifications import (
    build_direct_links,
    dispatch_group_workflow_event,
    gateway_status_summary,
    send_notification,
)
from app.services.pdf_generator import generate_branded_table_pdf, generate_fee_receipt_pdf, generate_question_paper_pdf

router = APIRouter(
    prefix="/api/teacher",
    tags=["Teacher"],
    dependencies=[Depends(require_roles(["teacher"]))],
)

SUPPORTED_QUESTION_TYPES = {
    "MCQ",
    "FILL_IN_BLANK",
    "MATCH_FOLLOWING",
    "ONE_MARK",
    "TWO_MARK",
    "THREE_MARK",
    "FOUR_MARK",
    "FIVE_MARK",
    "SIX_PLUS_MARK",
}


def _get_teacher(current_user: User, db: Session) -> Teacher:
    t = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Teacher profile not found.")
    return t


def _assigned_class_ids(t: Teacher) -> set[int]:
    return {a.class_id for a in t.assignments}


def _assigned_pairs(t: Teacher) -> set[tuple[int, int]]:
    return {(a.class_id, a.subject_id) for a in t.assignments}


def _all_active_class_ids(db: Session) -> list[int]:
    return [c.id for c in db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(SchoolClass.grade_level.asc()).all()]


@router.get("/classes")
def list_all_classes_for_teacher(db: Session = Depends(get_db)):
    classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(SchoolClass.grade_level.asc(), SchoolClass.section.asc()).all()
    subjects = db.query(Subject).filter(Subject.is_active == True).order_by(Subject.name.asc()).all()
    return {
        "classes": [
            {"id": c.id, "grade_level": c.grade_level, "name": c.name, "section": c.section}
            for c in classes
        ],
        "subjects": [
            {"id": s.id, "name": s.name, "code": s.code}
            for s in subjects
        ],
    }


@router.get("/dashboard")
def teacher_dashboard(current_user: User = Depends(require_roles(["teacher"])), db: Session = Depends(get_db)):
    t = _get_teacher(current_user, db)
    all_classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).all()
    class_ids = {c.id for c in all_classes}
    students = db.query(Student).filter(Student.is_active == True).all()

    today = date.today()
    today_att = db.query(Attendance).filter(Attendance.attendance_date == today).all()
    today_present = sum(1 for a in today_att if a.status == "PRESENT")

    upcoming_exams = (
        db.query(Examination)
        .filter(Examination.status == "SCHEDULED", Examination.end_date >= today)
        .order_by(Examination.start_date.asc())
        .all()
    )
    pending_subs = db.query(ResultApproval).filter(ResultApproval.submitted_by_user_id == current_user.id, ResultApproval.status == "PENDING").count()
    practice_tests = db.query(QuestionPaper).filter(QuestionPaper.teacher_id == t.id).count()

    return {
        "teacher": {
            "id": t.id,
            "teacher_code": t.teacher_code,
            "teacher_name": t.teacher_name,
            "qualification": t.qualification,
            "specialization": t.specialization,
        },
        "cards": {
            "assigned_classes": len(class_ids),
            "assigned_students": len(students),
            "assigned_subjects": db.query(Subject).filter(Subject.is_active == True).count(),
            "today_attendance_present": today_present,
            "today_attendance_total": len(today_att),
            "upcoming_examinations": len(upcoming_exams),
            "pending_mark_submissions": pending_subs,
            "practice_tests": practice_tests,
        },
        "assignments": [
            {
                "id": a.id,
                "class_id": a.class_id,
                "class_name": f"{a.school_class.name} ({a.school_class.section})" if a.school_class else "",
                "subject_id": a.subject_id,
                "subject_name": a.subject.name if a.subject else "",
                "is_class_teacher": a.is_class_teacher,
            }
            for a in t.assignments
        ],
        "upcoming_examinations": [
            {
                "id": ex.id,
                "name": ex.name,
                "class_name": f"{ex.school_class.name} ({ex.school_class.section})" if ex.school_class else "",
                "start_date": ex.start_date.isoformat(),
                "end_date": ex.end_date.isoformat(),
            }
            for ex in upcoming_exams
        ],
    }


@router.get("/students")
def list_assigned_students(
    class_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    q = db.query(Student).filter(Student.is_active == True)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    students = q.order_by(Student.class_id.asc(), Student.student_code.asc()).all()

    out = []
    for st in students:
        tot_att = db.query(Attendance).filter(Attendance.student_id == st.id).count()
        pres_att = db.query(Attendance).filter(Attendance.student_id == st.id, Attendance.status == "PRESENT").count()
        pct = round((pres_att / tot_att) * 100, 2) if tot_att else 0.0
        marks = db.query(Mark).filter(Mark.student_id == st.id).order_by(Mark.created_at.desc()).all()
        out.append({
            "id": st.id,
            "student_code": st.student_code,
            "student_name": st.student_name,
            "class_id": st.class_id,
            "class_name": st.school_class.name if st.school_class else "",
            "section": st.section,
            "gender": st.gender,
            "student_phone": st.student_phone,
            "parent_name": st.parent_name,
            "parent_phone": st.parent_phone,
            "photo_path": st.photo_path,
            "attendance_percentage": pct,
            "working_days": tot_att,
            "present_days": pres_att,
            "recent_marks": [
                {
                    "exam": m.examination.name if m.examination else "",
                    "subject": m.subject.name if m.subject else "",
                    "marks_obtained": float(m.marks_obtained),
                    "max_marks": float(m.max_marks),
                    "grade": m.grade,
                    "status": m.status,
                }
                for m in marks[:6]
            ],
        })
    return out


@router.post("/students")
def teacher_add_student(
    payload: TeacherStudentCreate,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    cls_obj = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
    if not cls_obj:
        raise HTTPException(status_code=404, detail="Class not found.")

    raw_parent_phone = (payload.parent_phone or payload.student_phone or "").strip()
    if not raw_parent_phone:
        raise HTTPException(status_code=400, detail="Student or parent mobile number is required.")
    raw_student_phone = (payload.student_phone or raw_parent_phone).strip()
    raw_parent_name = (payload.parent_name or "").strip() or f"Parent of {payload.student_name.strip()}"

    year = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()
    student_role = db.query(Role).filter(Role.name == "student").first()
    parent_role = db.query(Role).filter(Role.name == "parent").first()

    student_code = generate_next_student_code(db)
    s_pwd = (payload.student_password or "").strip() or generate_unique_password("AK")
    s_user = User(
        username=student_code,
        email=f"{student_code.lower()}@student.aktuition.edu.in",
        phone=raw_student_phone,
        full_name=payload.student_name.strip(),
        password_hash=hash_password(s_pwd),
        role_id=student_role.id,
        is_active=True,
    )
    db.add(s_user)
    db.flush()

    parent_obj = db.query(Parent).filter(Parent.phone == raw_parent_phone).first()
    parent_is_new = False
    p_pwd_out = None
    if not parent_obj:
        parent_is_new = True
        p_uname = f"parent_{student_code.lower()}"
        if db.query(User).filter(User.username == p_uname).first():
            p_uname = f"parent_{student_code.lower()}_{uuid.uuid4().hex[:4]}"
        p_pwd = (payload.parent_password or "").strip() or generate_unique_password("PR")
        p_pwd_out = p_pwd
        p_user = User(
            username=p_uname,
            email=payload.parent_email,
            phone=raw_parent_phone,
            full_name=raw_parent_name,
            password_hash=hash_password(p_pwd),
            role_id=parent_role.id,
            is_active=True,
        )
        db.add(p_user)
        db.flush()
        parent_obj = Parent(
            user_id=p_user.id,
            parent_name=raw_parent_name,
            phone=raw_parent_phone,
            email=payload.parent_email,
            address=payload.address,
        )
        db.add(parent_obj)
        db.flush()
    else:
        p_uname = parent_obj.user.username if parent_obj.user else None

    student = Student(
        user_id=s_user.id,
        student_code=student_code,
        student_name=payload.student_name.strip(),
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        class_id=payload.class_id,
        section=payload.section or cls_obj.section,
        address=payload.address,
        student_phone=raw_student_phone,
        parent_id=parent_obj.id,
        parent_name=parent_obj.parent_name,
        parent_phone=parent_obj.phone,
        admission_date=date.today(),
        assigned_teacher_id=t.id,
        is_active=True,
    )
    db.add(student)
    db.flush()

    if year:
        db.add(StudentEnrollment(
            student_id=student.id,
            class_id=cls_obj.id,
            academic_year_id=year.id,
            roll_number=student_code,
            enrolled_date=student.admission_date,
            status="ACTIVE",
        ))
        db.add(Fee(
            student_id=student.id,
            academic_year_id=year.id,
            total_fees=float(cls_obj.tuition_fee),
            paid_amount=0,
            pending_amount=float(cls_obj.tuition_fee),
        ))

    send_notification(
        db,
        recipient_phone=parent_obj.phone,
        channel="WHATSAPP",
        notification_type="WELCOME_CREDENTIAL",
        message=f"Welcome to AK Tuition! {student.student_name} ({student_code}) enrolled in {cls_obj.name} ({student.section}). Login ID: {student_code}, Password: {s_pwd}.",
        dedup_key=f"TEACHER_ADD_{student_code}",
        recipient_user_id=parent_obj.user_id,
        student_id=student.id,
        parent_id=parent_obj.id,
    )
    dispatch_group_workflow_event(
        db,
        event_type="STUDENT_REGISTERED",
        title="New Student Added by Teacher",
        message=f"{t.teacher_name} enrolled {student.student_name} ({student_code}) in {cls_obj.name} ({student.section}).",
        entity_id=student_code,
    )
    log_audit(db, current_user.id, "TEACHER_CREATE_STUDENT", "student", student_code, {"teacher": t.teacher_code}, request)
    db.commit()
    return {
        "id": student.id,
        "student_code": student_code,
        "student_name": student.student_name,
        "generated_credentials": {
            "student_name": student.student_name,
            "student_code": student_code,
            "student_username": student_code,
            "student_password": s_pwd,
            "parent_name": parent_obj.parent_name,
            "parent_username": p_uname,
            "parent_phone": parent_obj.phone,
            "parent_password": p_pwd_out if parent_is_new else None,
            "parent_is_new": parent_is_new,
        },
    }


@router.get("/results-pdf")
def teacher_overall_results_pdf(
    examination_id: Optional[int] = None,
    class_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    settings = get_or_create_settings(db)
    q = db.query(Mark).join(Student).filter(Mark.status == "PUBLISHED")
    if class_id:
        q = q.filter(Student.class_id == class_id)
    if examination_id:
        q = q.filter(Mark.examination_id == examination_id)
    marks = q.order_by(Mark.examination_id.desc(), Student.class_id.asc(), Student.student_code.asc()).all()

    grouped = {}
    for m in marks:
        key = (m.examination_id, m.student_id)
        if key not in grouped:
            grouped[key] = {
                "exam_id": m.examination_id,
                "exam_name": m.examination.name if m.examination else "",
                "student": m.student,
                "obtained": 0.0,
                "max": 0.0,
                "subjects": [],
            }
        grouped[key]["obtained"] += float(m.marks_obtained)
        grouped[key]["max"] += float(m.max_marks)
        grouped[key]["subjects"].append(f"{m.subject.code if m.subject else ''}: {float(m.marks_obtained):g}/{float(m.max_marks):g}")

    rows = []
    for (_, _), g in grouped.items():
        st = g["student"]
        pct = round((g["obtained"] / g["max"]) * 100, 2) if g["max"] else 0.0
        grade, _ = compute_grade(pct, settings.grading_rules)
        rank, tot_in_cls = compute_class_rank(db, g["exam_id"], st.class_id, st.id)
        rows.append([
            st.student_code,
            st.student_name,
            f"{st.school_class.name if st.school_class else ''} ({st.section})",
            g["exam_name"],
            ", ".join(g["subjects"]),
            f"{g['obtained']:g} / {g['max']:g}",
            f"{pct}% ({grade})",
            f"#{rank}/{tot_in_cls}" if rank else "-",
        ])

    pdf_bytes = generate_branded_table_pdf(
        title="OVERALL STUDENT EXAMINATION RESULT REPORT",
        subtitle=f"Prepared by {t.teacher_name} ({t.teacher_code}) • Published Results Only",
        headers=["ID", "Student Name", "Class", "Examination", "Subject Marks", "Total", "% (Grade)", "Class Rank"],
        rows=rows,
        logo_path=settings.logo_path,
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
        landscape_mode=True,
        director_name=settings.director_name,
        director_designation=settings.director_designation,
        signature_path=settings.director_signature_path,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="AK_Teacher_Overall_Results.pdf"'},
    )


# ---------------- ATTENDANCE MANAGEMENT ----------------

@router.get("/attendance")
def get_class_attendance(
    attendance_date: date,
    class_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    q = db.query(Student).filter(Student.is_active == True)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    students = q.order_by(Student.class_id.asc(), Student.student_code.asc()).all()

    att_q = db.query(Attendance).filter(Attendance.attendance_date == attendance_date)
    if class_id:
        att_q = att_q.filter(Attendance.class_id == class_id)
    existing = {a.student_id: a for a in att_q.all()}
    return {
        "class_id": class_id,
        "attendance_date": attendance_date.isoformat(),
        "students": [
            {
                "student_id": s.id,
                "student_code": s.student_code,
                "student_name": s.student_name,
                "class_id": s.class_id,
                "class_name": s.school_class.name if s.school_class else "",
                "section": s.section,
                "student_phone": s.student_phone,
                "parent_phone": s.parent_phone,
                "status": existing[s.id].status if s.id in existing else "PRESENT",
                "remarks": existing[s.id].remarks if s.id in existing else "",
                "already_marked": s.id in existing,
            }
            for s in students
        ],
    }


@router.post("/attendance")
def save_class_attendance(
    payload: AttendanceBulkCreate,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    q = db.query(Student).filter(Student.is_active == True)
    if payload.class_id:
        q = q.filter(Student.class_id == payload.class_id)
    students_map = {s.id: s for s in q.all()}

    saved = 0
    absent_alerts = []
    absent_names = []
    settings = get_or_create_settings(db)
    gw_mode = gateway_status_summary(settings)
    with httpx.Client(timeout=10.0) as http_cli:
        for item in payload.entries:
            st = students_map.get(item.student_id)
            if not st:
                continue
            st_val = item.status.strip().upper()
            if st_val not in {"PRESENT", "ABSENT"}:
                raise HTTPException(status_code=400, detail="Attendance status must be PRESENT or ABSENT.")
            existing = (
                db.query(Attendance)
                .filter(Attendance.student_id == item.student_id, Attendance.attendance_date == payload.attendance_date)
                .first()
            )
            if existing:
                existing.status = st_val
                existing.remarks = item.remarks
                existing.class_id = st.class_id
                existing.teacher_id = t.id
                existing.marked_by_user_id = current_user.id
            else:
                db.add(Attendance(
                    student_id=item.student_id,
                    class_id=st.class_id,
                    attendance_date=payload.attendance_date,
                    status=st_val,
                    teacher_id=t.id,
                    marked_by_user_id=current_user.id,
                    remarks=item.remarks,
                ))
            saved += 1

            if st_val == "ABSENT":
                cls_label = f"{st.school_class.name} ({st.section})" if st.school_class else ""
                absent_names.append(f"{st.student_name} ({st.student_code})")
                note_txt = f" Note: {item.remarks}." if item.remarks else ""
                msg = (
                    f"AK Tuition Absence Alert: {st.student_name} ({st.student_code}, {cls_label}) "
                    f"was marked ABSENT on {payload.attendance_date.isoformat()}.{note_txt} – AK Tuition"
                )
                seen_phones = set()
                targets = [("parent", st.parent_phone, st.parent.user_id if st.parent else None, st.parent_id)]
                if st.student_phone:
                    targets.append(("student", st.student_phone, st.user_id, None))
                for tgt_role, raw_phone, uid, pid in targets:
                    clean_p = (raw_phone or "").strip()
                    tail = "".join(c for c in clean_p if c.isdigit())[-10:]
                    if not clean_p or tail in seen_phones:
                        continue
                    seen_phones.add(tail)
                    notif = send_notification(
                        db,
                        recipient_phone=clean_p,
                        channel="WHATSAPP",
                        notification_type="ABSENT",
                        message=msg,
                        dedup_key=f"ABSENT_{st.id}_{payload.attendance_date.isoformat()}_{tail}",
                        recipient_user_id=uid,
                        student_id=st.id,
                        parent_id=pid,
                        http_client=http_cli,
                    )
                    if gw_mode["sms_live"]:
                        send_notification(
                            db,
                            recipient_phone=clean_p,
                            channel="SMS",
                            notification_type="ABSENT",
                            message=msg,
                            dedup_key=f"ABSENT_SMS_{st.id}_{payload.attendance_date.isoformat()}_{tail}",
                            recipient_user_id=uid,
                            student_id=st.id,
                            parent_id=pid,
                            http_client=http_cli,
                        )
                    links = build_direct_links(clean_p, msg)
                    absent_alerts.append({
                        "student_id": st.id,
                        "student_code": st.student_code,
                        "student_name": st.student_name,
                        "class_name": cls_label,
                        "target": tgt_role,
                        "phone": clean_p,
                        "status": notif.status,
                        "provider": notif.provider,
                        "message": msg,
                        "whatsapp_url": links["whatsapp_url"],
                        "sms_url": links["sms_url"],
                    })

    present_cnt = max(0, saved - len(absent_names))
    abs_summary = f"Absentees: {', '.join(absent_names[:15])}" if absent_names else "All students PRESENT!"
    dispatch_group_workflow_event(
        db,
        event_type="ATTENDANCE_MARKED",
        title=f"Attendance Saved ({payload.attendance_date.isoformat()})",
        message=f"Marked by {t.teacher_name}: {present_cnt} Present, {len(absent_names)} Absent (Total {saved}). {abs_summary}",
        entity_id=f"{payload.class_id or 'ALL'}:{payload.attendance_date.isoformat()}",
    )
    log_audit(
        db,
        current_user.id,
        "SAVE_ATTENDANCE",
        "attendance",
        f"{payload.class_id or 'ALL'}:{payload.attendance_date}",
        {"count": saved, "absent_alerts": len(absent_alerts)},
        request,
    )
    db.commit()
    return {
        "message": (
            f"Attendance saved for {saved} student(s). {len(absent_alerts)} absence alert(s) triggered for registered numbers."
            if absent_alerts
            else f"Attendance saved for {saved} student(s)."
        ),
        "saved_count": saved,
        "absent_alerts": absent_alerts,
    }


@router.get("/attendance/history")
def attendance_history(
    class_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    q = db.query(Attendance)
    if class_id:
        q = q.filter(Attendance.class_id == class_id)
    rows = (
        q.order_by(Attendance.attendance_date.desc(), Attendance.student_id.asc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": r.id,
            "attendance_date": r.attendance_date.isoformat(),
            "student_code": r.student.student_code if r.student else "",
            "student_name": r.student.student_name if r.student else "",
            "class_name": r.school_class.name if r.school_class else "",
            "status": r.status,
            "remarks": r.remarks,
        }
        for r in rows
    ]


# ---------------- EXAMINATION MARKS ENTRY (ALWAYS PENDING FOR ADMIN APPROVAL) ----------------

@router.get("/examinations")
def list_teacher_examinations(current_user: User = Depends(require_roles(["teacher"])), db: Session = Depends(get_db)):
    exams = db.query(Examination).filter(Examination.status != "CANCELLED").order_by(Examination.start_date.desc()).all()
    out = []
    for ex in exams:
        subjects = []
        for es in ex.exam_subjects:
            ap = db.query(ResultApproval).filter(ResultApproval.examination_subject_id == es.id).order_by(ResultApproval.id.desc()).first()
            subjects.append({
                "examination_subject_id": es.id,
                "subject_id": es.subject_id,
                "subject_name": es.subject.name if es.subject else "",
                "exam_date": es.exam_date.isoformat(),
                "max_marks": float(es.max_marks),
                "approval_status": ap.status if ap else "NOT_SUBMITTED",
                "rejection_reason": ap.rejection_reason if ap else None,
            })
        if subjects:
            out.append({
                "id": ex.id,
                "name": ex.name,
                "class_id": ex.class_id,
                "class_name": f"{ex.school_class.name} ({ex.school_class.section})" if ex.school_class else "",
                "start_date": ex.start_date.isoformat(),
                "end_date": ex.end_date.isoformat(),
                "subjects": subjects,
            })
    return out


@router.get("/marks/matrix")
def get_all_subjects_marks_matrix(
    class_id: int,
    examination_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    students = (
        db.query(Student)
        .filter(Student.class_id == class_id, Student.is_active == True)
        .order_by(Student.student_code.asc())
        .all()
    )
    subjects = db.query(Subject).filter(Subject.is_active == True).order_by(Subject.name.asc()).all()
    existing_scores: dict[int, dict[int, float]] = {}
    existing_remarks: dict[int, str] = {}
    subject_max_marks: dict[int, float] = {s.id: 100.0 for s in subjects}
    published_subject_ids: list[int] = []

    if examination_id:
        es_rows = db.query(ExaminationSubject).filter(ExaminationSubject.examination_id == examination_id).all()
        for es in es_rows:
            subject_max_marks[es.subject_id] = float(es.max_marks)
            ap = (
                db.query(ResultApproval)
                .filter(ResultApproval.examination_subject_id == es.id)
                .order_by(ResultApproval.id.desc())
                .first()
            )
            if ap and ap.status == "PUBLISHED":
                published_subject_ids.append(es.subject_id)
        mark_rows = (
            db.query(Mark)
            .filter(Mark.examination_id == examination_id)
            .all()
        )
        for m in mark_rows:
            existing_scores.setdefault(m.student_id, {})[m.subject_id] = float(m.marks_obtained)
            if m.remarks and m.student_id not in existing_remarks:
                existing_remarks[m.student_id] = m.remarks

    return {
        "class_id": class_id,
        "examination_id": examination_id,
        "subjects": [
            {
                "subject_id": s.id,
                "name": s.name,
                "code": s.code,
                "max_marks": subject_max_marks.get(s.id, 100.0),
                "is_published": s.id in published_subject_ids,
            }
            for s in subjects
        ],
        "students": [
            {
                "student_id": st.id,
                "student_code": st.student_code,
                "student_name": st.student_name,
                "scores": existing_scores.get(st.id, {}),
                "remarks": existing_remarks.get(st.id, ""),
            }
            for st in students
        ],
    }


@router.get("/marks/{examination_subject_id}")
def get_marks_entry_sheet(
    examination_subject_id: int,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    es = db.query(ExaminationSubject).filter(ExaminationSubject.id == examination_subject_id).first()
    if not es:
        raise HTTPException(status_code=404, detail="Examination subject not found.")
    ex = es.examination

    students = db.query(Student).filter(Student.class_id == ex.class_id, Student.is_active == True).order_by(Student.student_code.asc()).all()
    existing = {m.student_id: m for m in db.query(Mark).filter(Mark.examination_subject_id == es.id).all()}
    ap = db.query(ResultApproval).filter(ResultApproval.examination_subject_id == es.id).order_by(ResultApproval.id.desc()).first()

    return {
        "examination_id": ex.id,
        "examination_name": ex.name,
        "examination_subject_id": es.id,
        "subject_name": es.subject.name if es.subject else "",
        "max_marks": float(es.max_marks),
        "approval_status": ap.status if ap else "NOT_SUBMITTED",
        "rejection_reason": ap.rejection_reason if ap else None,
        "students": [
            {
                "student_id": s.id,
                "student_code": s.student_code,
                "student_name": s.student_name,
                "marks_obtained": float(existing[s.id].marks_obtained) if s.id in existing else "",
                "grade": existing[s.id].grade if s.id in existing else "",
                "remarks": existing[s.id].remarks if s.id in existing else "",
                "status": existing[s.id].status if s.id in existing else "DRAFT",
            }
            for s in students
        ],
    }


@router.post("/marks")
def save_and_submit_marks(
    payload: MarksBulkEntry,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    es = db.query(ExaminationSubject).filter(ExaminationSubject.id == payload.examination_subject_id).first()
    if not es or es.examination_id != payload.examination_id:
        raise HTTPException(status_code=404, detail="Examination subject not found.")
    ex = es.examination

    ap = db.query(ResultApproval).filter(ResultApproval.examination_subject_id == es.id).order_by(ResultApproval.id.desc()).first()
    if ap and ap.status == "PUBLISHED":
        raise HTTPException(status_code=400, detail="Official results are already PUBLISHED by Administrator and cannot be altered by teacher.")

    settings = get_or_create_settings(db)
    max_m = float(es.max_marks)
    target_status = "PENDING" if payload.submit_for_approval else "DRAFT"

    valid_students = {s.id for s in db.query(Student).filter(Student.class_id == ex.class_id, Student.is_active == True).all()}

    for entry in payload.entries:
        if entry.student_id not in valid_students:
            raise HTTPException(status_code=400, detail=f"Student {entry.student_id} is not in this class.")
        if entry.marks_obtained > max_m:
            raise HTTPException(status_code=400, detail=f"Marks obtained ({entry.marks_obtained}) cannot exceed maximum marks ({max_m}).")

        pct = (entry.marks_obtained / max_m) * 100 if max_m else 0.0
        grade, auto_rem = compute_grade(pct, settings.grading_rules)
        existing = (
            db.query(Mark)
            .filter(Mark.examination_subject_id == es.id, Mark.student_id == entry.student_id)
            .first()
        )
        if existing:
            existing.marks_obtained = entry.marks_obtained
            existing.max_marks = max_m
            existing.grade = grade
            existing.remarks = entry.remarks or auto_rem
            existing.status = target_status
            existing.entered_by_user_id = current_user.id
            if payload.submit_for_approval:
                existing.submitted_at = datetime.utcnow()
        else:
            db.add(Mark(
                examination_id=ex.id,
                examination_subject_id=es.id,
                student_id=entry.student_id,
                subject_id=es.subject_id,
                max_marks=max_m,
                marks_obtained=entry.marks_obtained,
                grade=grade,
                remarks=entry.remarks or auto_rem,
                status=target_status,
                entered_by_user_id=current_user.id,
                submitted_at=datetime.utcnow() if payload.submit_for_approval else None,
            ))

    if payload.submit_for_approval:
        if ap:
            ap.status = "PENDING"
            ap.submitted_by_user_id = current_user.id
            ap.submitted_date = datetime.utcnow()
            ap.rejection_reason = None
            ap.notes = payload.notes
        else:
            db.add(ResultApproval(
                examination_id=ex.id,
                examination_subject_id=es.id,
                submitted_by_user_id=current_user.id,
                submitted_date=datetime.utcnow(),
                status="PENDING",
                notes=payload.notes,
            ))

    if payload.submit_for_approval:
        dispatch_group_workflow_event(
            db,
            event_type="MARKS_SUBMITTED",
            title="Marks Submitted for Approval",
            message=f"{t.teacher_name} submitted {len(payload.entries)} mark(s) for {ex.name} ({es.subject.name if es.subject else 'Subject'}). Ready for Admin Publish.",
            entity_id=str(es.id),
        )
    log_audit(db, current_user.id, "SUBMIT_MARKS" if payload.submit_for_approval else "SAVE_MARKS_DRAFT", "marks", str(es.id), {"count": len(payload.entries)}, request)
    db.commit()
    return {
        "status": target_status,
        "message": "Marks submitted for Administrator approval (status: PENDING)." if payload.submit_for_approval else "Marks saved as draft.",
    }


@router.post("/marks/direct")
def direct_save_and_submit_marks(
    payload: TeacherDirectMarksEntry,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    _get_teacher(current_user, db)
    clean_name = (payload.exam_name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Examination or Re-Examination name is required.")

    cls = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Selected class not found.")
    subj = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Selected subject not found.")
    if not payload.entries:
        raise HTTPException(status_code=400, detail="Enter marks for at least one student.")

    ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()
    if not ay:
        raise HTTPException(status_code=400, detail="No active academic year configured.")

    ex = (
        db.query(Examination)
        .filter(
            Examination.class_id == payload.class_id,
            func.lower(Examination.name) == clean_name.lower(),
        )
        .first()
    )
    if not ex:
        ex_date = payload.exam_date or date.today()
        ex = Examination(
            name=clean_name,
            academic_year_id=ay.id,
            class_id=payload.class_id,
            exam_type=(payload.exam_type or "RE_EXAMINATION").strip().upper(),
            start_date=ex_date,
            end_date=ex_date,
            status="SCHEDULED",
            created_by_user_id=current_user.id,
        )
        db.add(ex)
        db.flush()

    es = (
        db.query(ExaminationSubject)
        .filter(
            ExaminationSubject.examination_id == ex.id,
            ExaminationSubject.subject_id == payload.subject_id,
        )
        .first()
    )
    if not es:
        es = ExaminationSubject(
            examination_id=ex.id,
            subject_id=payload.subject_id,
            exam_date=payload.exam_date or date.today(),
            max_marks=payload.max_marks,
        )
        db.add(es)
        db.flush()
    else:
        es.max_marks = payload.max_marks

    ap = db.query(ResultApproval).filter(ResultApproval.examination_subject_id == es.id).order_by(ResultApproval.id.desc()).first()
    if ap and ap.status == "PUBLISHED":
        raise HTTPException(status_code=400, detail="Official results are already PUBLISHED by Administrator and cannot be altered by teacher.")

    settings = get_or_create_settings(db)
    max_m = float(es.max_marks)
    target_status = "PENDING" if payload.submit_for_approval else "DRAFT"
    valid_students = {s.id for s in db.query(Student).filter(Student.class_id == ex.class_id, Student.is_active == True).all()}

    for entry in payload.entries:
        if entry.student_id not in valid_students:
            raise HTTPException(status_code=400, detail=f"Student {entry.student_id} is not in this class.")
        if entry.marks_obtained > max_m:
            raise HTTPException(status_code=400, detail=f"Marks obtained ({entry.marks_obtained}) cannot exceed maximum marks ({max_m}).")

        pct = (entry.marks_obtained / max_m) * 100 if max_m else 0.0
        grade, auto_rem = compute_grade(pct, settings.grading_rules)
        existing = (
            db.query(Mark)
            .filter(Mark.examination_subject_id == es.id, Mark.student_id == entry.student_id)
            .first()
        )
        if existing:
            existing.marks_obtained = entry.marks_obtained
            existing.max_marks = max_m
            existing.grade = grade
            existing.remarks = entry.remarks or auto_rem
            existing.status = target_status
            existing.entered_by_user_id = current_user.id
            if payload.submit_for_approval:
                existing.submitted_at = datetime.utcnow()
        else:
            db.add(Mark(
                examination_id=ex.id,
                examination_subject_id=es.id,
                student_id=entry.student_id,
                subject_id=es.subject_id,
                max_marks=max_m,
                marks_obtained=entry.marks_obtained,
                grade=grade,
                remarks=entry.remarks or auto_rem,
                status=target_status,
                entered_by_user_id=current_user.id,
                submitted_at=datetime.utcnow() if payload.submit_for_approval else None,
            ))

    if payload.submit_for_approval:
        if ap:
            ap.status = "PENDING"
            ap.submitted_by_user_id = current_user.id
            ap.submitted_date = datetime.utcnow()
            ap.rejection_reason = None
            ap.notes = payload.notes
        else:
            db.add(ResultApproval(
                examination_id=ex.id,
                examination_subject_id=es.id,
                submitted_by_user_id=current_user.id,
                submitted_date=datetime.utcnow(),
                status="PENDING",
                notes=payload.notes,
            ))

    if payload.submit_for_approval:
        dispatch_group_workflow_event(
            db,
            event_type="MARKS_SUBMITTED",
            title="Exam / Re-Exam Marks Submitted",
            message=f"{ex.name} ({subj.name}) marks for {len(payload.entries)} student(s) submitted by {current_user.full_name} for Admin approval.",
            entity_id=str(es.id),
        )
    log_audit(db, current_user.id, "DIRECT_SUBMIT_MARKS", "marks", str(es.id), {"exam_name": ex.name, "count": len(payload.entries)}, request)
    db.commit()
    return {
        "status": target_status,
        "examination_id": ex.id,
        "examination_subject_id": es.id,
        "message": f"Marks for '{ex.name}' submitted for Administrator approval (status: PENDING)." if payload.submit_for_approval else f"Marks for '{ex.name}' saved as draft.",
    }


@router.post("/marks/bulk-all-subjects")
def save_all_subjects_marks_at_once(
    payload: TeacherAllSubjectsMarksEntry,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    cls = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Selected class not found.")
    if not payload.subjects:
        raise HTTPException(status_code=400, detail="Select at least one subject column.")
    if not payload.entries:
        raise HTTPException(status_code=400, detail="Enter marks for at least one student.")

    ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()
    if not ay:
        raise HTTPException(status_code=400, detail="No active academic year configured.")

    if payload.examination_id:
        ex = db.query(Examination).filter(Examination.id == payload.examination_id).first()
        if not ex:
            raise HTTPException(status_code=404, detail="Selected examination not found.")
        if ex.class_id != payload.class_id:
            raise HTTPException(status_code=400, detail="Selected examination belongs to a different class.")
    else:
        clean_name = (payload.exam_name or "").strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Enter an Examination / Re-Examination name or select an existing examination.")
        ex = (
            db.query(Examination)
            .filter(Examination.class_id == payload.class_id, func.lower(Examination.name) == clean_name.lower())
            .first()
        )
        if not ex:
            ex_date = payload.exam_date or date.today()
            ex = Examination(
                name=clean_name,
                academic_year_id=ay.id,
                class_id=payload.class_id,
                exam_type=(payload.exam_type or "UNIT_TEST").strip().upper(),
                start_date=ex_date,
                end_date=ex_date,
                status="SCHEDULED",
                created_by_user_id=current_user.id,
            )
            db.add(ex)
            db.flush()

    settings = get_or_create_settings(db)
    target_status = "PENDING" if payload.submit_for_approval else "DRAFT"
    valid_students = {s.id for s in db.query(Student).filter(Student.class_id == payload.class_id, Student.is_active == True).all()}
    subj_map = {s.id: s for s in db.query(Subject).filter(Subject.id.in_([c.subject_id for c in payload.subjects])).all()}

    es_by_subj: dict[int, ExaminationSubject] = {}
    max_by_subj: dict[int, float] = {}
    for col in payload.subjects:
        if col.subject_id not in subj_map:
            raise HTTPException(status_code=404, detail=f"Subject {col.subject_id} not found.")
        es = (
            db.query(ExaminationSubject)
            .filter(ExaminationSubject.examination_id == ex.id, ExaminationSubject.subject_id == col.subject_id)
            .first()
        )
        if not es:
            es = ExaminationSubject(
                examination_id=ex.id,
                subject_id=col.subject_id,
                exam_date=payload.exam_date or ex.start_date or date.today(),
                max_marks=col.max_marks,
            )
            db.add(es)
            db.flush()
        else:
            es.max_marks = col.max_marks
        ap = db.query(ResultApproval).filter(ResultApproval.examination_subject_id == es.id).order_by(ResultApproval.id.desc()).first()
        if ap and ap.status == "PUBLISHED":
            raise HTTPException(
                status_code=400,
                detail=f"{subj_map[col.subject_id].name} is already PUBLISHED by Admin and cannot be overwritten.",
            )
        es_by_subj[col.subject_id] = es
        max_by_subj[col.subject_id] = float(col.max_marks)

    marks_saved = 0
    touched_es_ids = set()
    for row in payload.entries:
        if row.student_id not in valid_students:
            raise HTTPException(status_code=400, detail=f"Student {row.student_id} is not in this class.")
        for sid_key, score_val in row.scores.items():
            sid = int(sid_key)
            if sid not in es_by_subj:
                continue
            es = es_by_subj[sid]
            max_m = max_by_subj[sid]
            if score_val < 0 or score_val > max_m:
                raise HTTPException(
                    status_code=400,
                    detail=f"Score ({score_val}) for {subj_map[sid].name} must be between 0 and {max_m}.",
                )
            pct = (score_val / max_m) * 100 if max_m else 0.0
            grade, auto_rem = compute_grade(pct, settings.grading_rules)
            existing = (
                db.query(Mark)
                .filter(Mark.examination_subject_id == es.id, Mark.student_id == row.student_id)
                .first()
            )
            if existing:
                existing.marks_obtained = score_val
                existing.max_marks = max_m
                existing.grade = grade
                existing.remarks = row.remarks or auto_rem
                existing.status = target_status
                existing.entered_by_user_id = current_user.id
                if payload.submit_for_approval:
                    existing.submitted_at = datetime.utcnow()
            else:
                db.add(Mark(
                    examination_id=ex.id,
                    examination_subject_id=es.id,
                    student_id=row.student_id,
                    subject_id=sid,
                    max_marks=max_m,
                    marks_obtained=score_val,
                    grade=grade,
                    remarks=row.remarks or auto_rem,
                    status=target_status,
                    entered_by_user_id=current_user.id,
                    submitted_at=datetime.utcnow() if payload.submit_for_approval else None,
                ))
            marks_saved += 1
            touched_es_ids.add(es.id)

    if marks_saved == 0:
        raise HTTPException(status_code=400, detail="Enter at least one student mark before saving.")

    if payload.submit_for_approval:
        for es_id in touched_es_ids:
            ap = db.query(ResultApproval).filter(ResultApproval.examination_subject_id == es_id).order_by(ResultApproval.id.desc()).first()
            if ap:
                ap.status = "PENDING"
                ap.submitted_by_user_id = current_user.id
                ap.submitted_date = datetime.utcnow()
                ap.rejection_reason = None
                ap.notes = payload.notes
            else:
                db.add(ResultApproval(
                    examination_id=ex.id,
                    examination_subject_id=es_id,
                    submitted_by_user_id=current_user.id,
                    submitted_date=datetime.utcnow(),
                    status="PENDING",
                    notes=payload.notes,
                ))
        dispatch_group_workflow_event(
            db,
            event_type="ALL_SUBJECT_MARKS_SUBMITTED",
            title=f"All Subject Marks Submitted ({ex.name})",
            message=f"{t.teacher_name} entered {marks_saved} mark entries across {len(touched_es_ids)} subject(s) for {cls.name} ({cls.section}). Ready for Admin Declare All!",
            entity_id=str(ex.id),
        )

    log_audit(
        db,
        current_user.id,
        "BULK_ALL_SUBJECTS_MARKS",
        "examination",
        str(ex.id),
        {"subjects_count": len(touched_es_ids), "marks_saved": marks_saved},
        request,
    )
    db.commit()
    return {
        "status": target_status,
        "examination_id": ex.id,
        "exam_name": ex.name,
        "subjects_count": len(touched_es_ids),
        "marks_saved": marks_saved,
        "message": f"Saved {marks_saved} marks across {len(touched_es_ids)} subject(s) for '{ex.name}' (status: {target_status}).",
    }


# ---------------- QUESTION PAPERS & ONLINE PRACTICE TESTS ----------------

@router.get("/question-papers")
def list_question_papers(current_user: User = Depends(require_roles(["teacher"])), db: Session = Depends(get_db)):
    t = _get_teacher(current_user, db)
    papers = db.query(QuestionPaper).filter(QuestionPaper.teacher_id == t.id).order_by(QuestionPaper.created_at.desc()).all()
    return [
        {
            "id": qp.id,
            "title": qp.title,
            "class_id": qp.class_id,
            "class_name": f"{qp.school_class.name} ({qp.school_class.section})" if qp.school_class else "",
            "subject_id": qp.subject_id,
            "subject_name": qp.subject.name if qp.subject else "",
            "examination_id": qp.examination_id,
            "duration_minutes": qp.duration_minutes,
            "total_marks": float(qp.total_marks),
            "watermark_text": qp.watermark_text,
            "question_count": len(qp.questions),
            "is_online_test": qp.is_online_test,
            "is_published": qp.is_published,
            "created_at": qp.created_at.isoformat(),
        }
        for qp in papers
    ]


@router.post("/question-papers")
def create_question_paper(
    payload: QuestionPaperCreate,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    if not payload.questions:
        raise HTTPException(status_code=400, detail="Add at least one question.")

    sum_marks = sum(q.marks for q in payload.questions)
    if abs(sum_marks - payload.total_marks) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"Sum of question marks ({sum_marks}) must match configured total marks ({payload.total_marks}).",
        )

    if payload.examination_id:
        es = (
            db.query(ExaminationSubject)
            .filter(
                ExaminationSubject.examination_id == payload.examination_id,
                ExaminationSubject.subject_id == payload.subject_id,
            )
            .first()
        )
        if es and abs(float(es.max_marks) - payload.total_marks) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Question paper total marks ({payload.total_marks}) must match the examination maximum marks ({float(es.max_marks)}).",
            )

    qp = QuestionPaper(
        title=payload.title.strip(),
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        examination_id=payload.examination_id,
        teacher_id=t.id,
        created_by_user_id=current_user.id,
        duration_minutes=payload.duration_minutes,
        total_marks=payload.total_marks,
        evaluation_scheme=payload.evaluation_scheme,
        instructions=payload.instructions,
        watermark_text=(payload.watermark_text or "").strip() or None,
        is_online_test=payload.is_online_test,
        is_published=payload.is_published,
        auto_evaluate_mcq=payload.auto_evaluate_mcq,
        allow_result_view=payload.allow_result_view,
    )
    db.add(qp)
    db.flush()

    for idx, q_in in enumerate(payload.questions, start=1):
        qt = q_in.question_type.strip().upper()
        if qt not in SUPPORTED_QUESTION_TYPES:
            raise HTTPException(status_code=400, detail=f"Unsupported question type: {qt}")
        q_obj = Question(
            question_paper_id=qp.id,
            question_type=qt,
            question_text=q_in.question_text.strip(),
            marks=q_in.marks,
            order_index=q_in.order_index or idx,
            correct_answer=q_in.correct_answer,
            match_pairs=q_in.match_pairs,
            explanation=q_in.explanation,
        )
        db.add(q_obj)
        db.flush()
        for opt in q_in.options:
            db.add(QuestionOption(
                question_id=q_obj.id,
                option_label=opt.option_label.strip().upper(),
                option_text=opt.option_text.strip(),
                is_correct=opt.is_correct,
            ))

    if qp.is_published:
        dispatch_group_workflow_event(
            db,
            event_type="QUESTION_PAPER_CREATED",
            title="New Question Paper / Online Test",
            message=f"{t.teacher_name} published '{qp.title}' ({qp.total_marks} Marks, {qp.duration_minutes} mins).",
            entity_id=str(qp.id),
        )
    log_audit(db, current_user.id, "CREATE_QUESTION_PAPER", "question_paper", str(qp.id), {"title": qp.title}, request)
    db.commit()
    db.refresh(qp)
    return {"id": qp.id, "title": qp.title}


# ---------------- TEACHER FEE COLLECTION (PENDING ADMIN VERIFICATION) ----------------

@router.get("/fees/collections")
def list_teacher_fee_collections(
    class_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    st_q = db.query(Student).filter(Student.is_active == True)
    if class_id:
        st_q = st_q.filter(Student.class_id == class_id)
    students = st_q.order_by(Student.class_id.asc(), Student.student_code.asc()).all()

    student_rows = []
    for st in students:
        fee = db.query(Fee).filter(Fee.student_id == st.id).order_by(Fee.id.desc()).first()
        tot_f = float(fee.total_fees) if fee else float(st.school_class.tuition_fee if st.school_class else 0)
        paid_f = float(fee.paid_amount) if fee else 0.0
        pend_f = float(fee.pending_amount) if fee else tot_f
        student_rows.append({
            "student_id": st.id,
            "student_code": st.student_code,
            "student_name": st.student_name,
            "class_id": st.class_id,
            "class_name": f"{st.school_class.name} ({st.section})" if st.school_class else "",
            "parent_name": st.parent_name,
            "parent_phone": st.parent_phone,
            "total_fees": tot_f,
            "paid_amount": paid_f,
            "pending_amount": pend_f,
        })

    payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .limit(120)
        .all()
    )
    collections = []
    for p in payments:
        st = p.student
        rec_no = p.receipt.receipt_number if p.receipt else None
        pdf_tok = create_signed_payload({"pid": p.id}, expire_minutes=60 * 24 * 30) if p.status == "VERIFIED" else None
        pdf_url = f"https://aktp-backend-production.up.railway.app/api/public/fee-receipt/pdf?token={pdf_tok}" if pdf_tok else None
        msg = (
            f"AK TUITION - FEE RECEIPT VERIFIED\n"
            f"Receipt: {rec_no or f'AKR-{p.id}'}\n"
            f"Student: {st.student_name if st else ''} ({st.student_code if st else ''})\n"
            f"Paid: Rs. {float(p.amount):,.2f} ({p.payment_mode})\n"
            f"Download PDF Receipt: {pdf_url}"
            if pdf_url
            else ""
        )
        links = build_direct_links(st.parent_phone if st else "", msg) if pdf_url and st else {"whatsapp_url": None, "sms_url": None}
        collections.append({
            "id": p.id,
            "student_id": p.student_id,
            "student_code": st.student_code if st else "",
            "student_name": st.student_name if st else "",
            "class_name": f"{st.school_class.name} ({st.section})" if st and st.school_class else "",
            "parent_phone": st.parent_phone if st else "",
            "amount": float(p.amount),
            "payment_date": p.payment_date.isoformat(),
            "payment_mode": p.payment_mode,
            "reference_number": p.reference_number,
            "remarks": p.remarks,
            "status": p.status,
            "receipt_number": rec_no,
            "receipt_pdf_url": pdf_url,
            "whatsapp_url": links["whatsapp_url"],
            "sms_url": links["sms_url"],
            "created_at": p.created_at.isoformat(),
        })

    return {"students": student_rows, "collections": collections}


@router.post("/fees/collect")
def teacher_collect_student_fee(
    payload: TeacherFeeCollectRequest,
    request: Request,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    st = db.query(Student).filter(Student.id == payload.student_id, Student.is_active == True).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found.")

    valid_modes = {"CASH", "UPI", "BANK_TRANSFER", "OTHER"}
    mode = payload.payment_mode.strip().upper().replace(" ", "_")
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Payment mode must be one of: {', '.join(sorted(valid_modes))}.")

    if payload.idempotency_key and db.query(Payment).filter(Payment.idempotency_key == payload.idempotency_key).first():
        raise HTTPException(status_code=409, detail="Duplicate fee collection blocked.")

    if payload.reference_number and db.query(Payment).filter(Payment.reference_number == payload.reference_number.strip()).first():
        raise HTTPException(status_code=409, detail="A fee collection with this reference number already exists.")

    fee = db.query(Fee).filter(Fee.student_id == st.id).order_by(Fee.id.desc()).first()
    if not fee:
        ay = db.query(AcademicYear).filter(AcademicYear.is_current == True).first() or db.query(AcademicYear).first()
        base_fee = float(st.school_class.tuition_fee if st.school_class else 0)
        fee = Fee(
            student_id=st.id,
            academic_year_id=ay.id,
            total_fees=base_fee,
            paid_amount=0,
            pending_amount=base_fee,
        )
        db.add(fee)
        db.flush()

    pay = Payment(
        fee_id=fee.id,
        student_id=st.id,
        amount=payload.amount,
        payment_date=payload.payment_date or date.today(),
        payment_mode=mode,
        reference_number=payload.reference_number.strip() if payload.reference_number else None,
        idempotency_key=payload.idempotency_key,
        remarks=payload.remarks or f"Collected by {t.teacher_name}",
        status="PENDING",
        recorded_by_user_id=current_user.id,
    )
    db.add(pay)
    db.flush()

    dispatch_group_workflow_event(
        db,
        event_type="FEE_COLLECTED_PENDING",
        title="Fee Collected — Pending Admin Verification",
        message=f"{t.teacher_name} collected Rs. {payload.amount:,.2f} ({mode}) from {st.student_name} ({st.student_code}). Sent to Admin for verification.",
        entity_id=str(pay.id),
    )
    log_audit(db, current_user.id, "TEACHER_COLLECT_FEE", "payment", str(pay.id), {"student": st.student_code, "amount": payload.amount}, request)
    db.commit()
    return {
        "id": pay.id,
        "status": pay.status,
        "message": f"Collected Rs. {payload.amount:,.2f} from {st.student_name} ({st.student_code}). Sent to Admin for verification.",
    }


@router.get("/fees/{payment_id}/receipt-pdf")
def teacher_download_fee_receipt_pdf(
    payment_id: int,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    pay = db.query(Payment).filter(Payment.id == payment_id).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Fee payment record not found.")
    if pay.status != "VERIFIED":
        raise HTTPException(status_code=400, detail="Official PDF receipt is generated only after Admin verifies the payment.")
    settings = get_or_create_settings(db)
    st = pay.student
    fee = pay.fee
    pdf_bytes = generate_fee_receipt_pdf(
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
        address=settings.address,
        phone=settings.phone,
        logo_path=settings.logo_path,
        receipt_number=pay.receipt.receipt_number if pay.receipt else f"AKR-{pay.id:04d}",
        payment_date=pay.payment_date.strftime("%d %b %Y"),
        student_name=st.student_name,
        student_code=st.student_code,
        class_name=f"{st.school_class.name} ({st.section})" if st.school_class else "",
        parent_name=st.parent_name,
        payment_mode=pay.payment_mode,
        reference_number=pay.reference_number or "",
        amount_paid=float(pay.amount),
        total_fees=float(fee.total_fees),
        total_paid_to_date=float(fee.paid_amount),
        pending_amount=float(fee.pending_amount),
        remarks=pay.remarks or "",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AK_FeeReceipt_{st.student_code}_{pay.id}.pdf"'},
    )


@router.get("/question-papers/{paper_id}/pdf")
def download_question_paper_pdf(
    paper_id: int,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    qp = db.query(QuestionPaper).filter(QuestionPaper.id == paper_id, QuestionPaper.teacher_id == t.id).first()
    if not qp:
        raise HTTPException(status_code=404, detail="Question paper not found.")
    settings = get_or_create_settings(db)
    pdf_bytes = generate_question_paper_pdf(
        tuition_name=settings.tuition_name,
        logo_path=settings.logo_path,
        title=qp.title,
        class_name=f"{qp.school_class.name} ({qp.school_class.section})" if qp.school_class else "",
        subject_name=qp.subject.name if qp.subject else "",
        duration_minutes=qp.duration_minutes,
        total_marks=float(qp.total_marks),
        instructions=qp.instructions or "",
        evaluation_scheme=qp.evaluation_scheme or "",
        director_name=settings.director_name,
        director_designation=settings.director_designation,
        signature_path=settings.director_signature_path,
        watermark_text=qp.watermark_text,
        questions=[
            {
                "question_type": q.question_type,
                "question_text": q.question_text,
                "marks": float(q.marks),
                "match_pairs": q.match_pairs,
                "options": [{"option_label": o.option_label, "option_text": o.option_text} for o in q.options],
            }
            for q in qp.questions
        ],
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AK_QuestionPaper_{qp.id}.pdf"'},
    )


@router.get("/test-attempts")
def list_student_test_attempts(
    paper_id: Optional[int] = None,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    q = db.query(StudentTestAttempt).join(QuestionPaper).filter(QuestionPaper.teacher_id == t.id)
    if paper_id:
        q = q.filter(StudentTestAttempt.question_paper_id == paper_id)
    attempts = q.order_by(StudentTestAttempt.started_at.desc()).all()
    return [
        {
            "id": a.id,
            "question_paper_id": a.question_paper_id,
            "paper_title": a.question_paper.title if a.question_paper else "",
            "student_code": a.student.student_code if a.student else "",
            "student_name": a.student.student_name if a.student else "",
            "status": a.status,
            "total_score": float(a.total_score),
            "max_score": float(a.max_score),
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
            "answers": [
                {
                    "answer_id": ans.id,
                    "question_id": ans.question_id,
                    "question_type": ans.question.question_type if ans.question else "",
                    "question_text": ans.question.question_text if ans.question else "",
                    "max_marks": float(ans.question.marks) if ans.question else 0,
                    "answer_text": ans.answer_text,
                    "selected_option_id": ans.selected_option_id,
                    "marks_awarded": float(ans.marks_awarded) if ans.marks_awarded is not None else None,
                    "teacher_comment": ans.teacher_comment,
                }
                for ans in a.answers
            ],
        }
        for a in attempts
    ]


@router.post("/test-attempts/{attempt_id}/evaluate")
def evaluate_test_attempt(
    attempt_id: int,
    payload: AttemptEvaluationInput,
    current_user: User = Depends(require_roles(["teacher"])),
    db: Session = Depends(get_db),
):
    t = _get_teacher(current_user, db)
    attempt = db.query(StudentTestAttempt).filter(StudentTestAttempt.id == attempt_id).first()
    if not attempt or not attempt.question_paper or attempt.question_paper.teacher_id != t.id:
        raise HTTPException(status_code=404, detail="Test attempt not found or unauthorized.")

    ans_map = {a.id: a for a in attempt.answers}
    for ev in payload.evaluations:
        ans = ans_map.get(ev.answer_id)
        if not ans:
            continue
        max_q = float(ans.question.marks) if ans.question else 0
        if ev.marks_awarded > max_q:
            raise HTTPException(status_code=400, detail=f"Awarded marks ({ev.marks_awarded}) cannot exceed question marks ({max_q}).")
        ans.marks_awarded = ev.marks_awarded
        ans.teacher_comment = ev.teacher_comment

    attempt.total_score = sum(float(a.marks_awarded or 0) for a in attempt.answers)
    attempt.status = "EVALUATED"
    attempt.evaluated_by_user_id = current_user.id
    attempt.teacher_feedback = payload.teacher_feedback
    db.commit()
    return {"message": "Evaluation saved.", "total_score": float(attempt.total_score)}
