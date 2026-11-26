import csv
import io
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import LOGOS_DIR, SIGNATURES_DIR, STUDENT_PHOTOS_DIR
from app.database import get_db
from app.models import (
    AcademicYear,
    Announcement,
    Attendance,
    AuditLog,
    ClassSubject,
    Examination,
    ExaminationSubject,
    Fee,
    FeeReceipt,
    Mark,
    Notification,
    Parent,
    Payment,
    QuestionPaper,
    ResultApproval,
    Role,
    SchoolClass,
    Student,
    StudentEnrollment,
    Subject,
    Teacher,
    TeacherAssignment,
    TeacherAttendance,
    User,
)
from app.schemas import (
    AnnouncementCreate,
    ClassCreate,
    ClassSubjectAssign,
    ExaminationCreate,
    ExaminationUpdate,
    FeeUpdate,
    NotificationDispatchRequest,
    ParentConsentUpdate,
    PaymentCreate,
    ResultApprovalAction,
    SettingsUpdate,
    StudentCreate,
    StudentUpdate,
    SubjectCreate,
    TeacherAssignmentCreate,
    TeacherAttendanceEntry,
    TeacherCreate,
    TeacherUpdate,
)
from app.security import hash_password, log_audit, require_roles
from app.services.excel_generator import generate_excel_report
from app.services.helpers import (
    compute_class_rank,
    compute_grade,
    generate_next_student_code,
    generate_unique_password,
    get_or_create_settings,
)
from app.services.notifications import send_notification
from app.services.pdf_generator import (
    generate_branded_table_pdf,
    generate_fee_receipt_pdf,
    generate_marks_card_pdf,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["Administrator"],
    dependencies=[Depends(require_roles(["admin"]))],
)


def _get_current_year(db: Session) -> AcademicYear:
    yr = db.query(AcademicYear).filter(AcademicYear.is_current == True).first()
    if not yr:
        yr = db.query(AcademicYear).first()
    if not yr:
        yr = AcademicYear(name="2026-2027", start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_current=True)
        db.add(yr)
        db.flush()
    return yr


@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db)):
    total_students = db.query(Student).filter(Student.is_active == True).count()
    total_teachers = db.query(Teacher).filter(Teacher.is_active == True).count()
    total_classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).count()

    fee_totals = db.query(
        func.coalesce(func.sum(Fee.paid_amount), 0),
        func.coalesce(func.sum(Fee.pending_amount), 0),
    ).first()
    total_fees_collected = float(fee_totals[0] or 0)
    pending_fees = float(fee_totals[1] or 0)

    today = date.today()
    today_total = db.query(Attendance).filter(Attendance.attendance_date == today).count()
    today_present = db.query(Attendance).filter(Attendance.attendance_date == today, Attendance.status == "PRESENT").count()
    today_attendance_pct = round((today_present / today_total) * 100, 1) if today_total else 0.0

    all_att_total = db.query(Attendance).count()
    all_att_present = db.query(Attendance).filter(Attendance.status == "PRESENT").count()
    overall_attendance_pct = round((all_att_present / all_att_total) * 100, 1) if all_att_total else 0.0

    upcoming_exams = db.query(Examination).filter(Examination.status == "SCHEDULED", Examination.end_date >= today).count()
    published_results = db.query(ResultApproval).filter(ResultApproval.status == "PUBLISHED").count()
    pending_result_approvals = db.query(ResultApproval).filter(ResultApproval.status == "PENDING").count()
    active_practice_tests = db.query(QuestionPaper).filter(QuestionPaper.is_online_test == True, QuestionPaper.is_published == True).count()

    # Chart 1: Monthly fee collection
    payments = db.query(Payment).order_by(Payment.payment_date.asc()).all()
    monthly_fee_map = {}
    for p in payments:
        key = p.payment_date.strftime("%b %Y")
        monthly_fee_map[key] = monthly_fee_map.get(key, 0.0) + float(p.amount)
    monthly_fee_collection = [{"month": k, "amount": round(v, 2)} for k, v in monthly_fee_map.items()]

    # Chart 2: Student enrollment growth by admission month
    students = db.query(Student).order_by(Student.admission_date.asc()).all()
    enroll_map = {}
    running = 0
    for st in students:
        key = st.admission_date.strftime("%b %Y")
        running += 1
        enroll_map[key] = running
    enrollment_growth = [{"month": k, "students": v} for k, v in enroll_map.items()]

    # Chart 3: Attendance statistics (by recent dates)
    att_rows = (
        db.query(Attendance.attendance_date, Attendance.status, func.count(Attendance.id))
        .group_by(Attendance.attendance_date, Attendance.status)
        .order_by(Attendance.attendance_date.desc())
        .limit(20)
        .all()
    )
    att_date_map = {}
    for d, st_val, cnt in att_rows:
        ds = d.isoformat()
        if ds not in att_date_map:
            att_date_map[ds] = {"date": ds, "present": 0, "absent": 0}
        if st_val == "PRESENT":
            att_date_map[ds]["present"] += cnt
        else:
            att_date_map[ds]["absent"] += cnt
    attendance_stats = sorted(att_date_map.values(), key=lambda x: x["date"])

    # Chart 4: Examination performance (avg % per exam)
    published_marks = db.query(Mark).filter(Mark.status == "PUBLISHED").all()
    exam_perf_map = {}
    for m in published_marks:
        ename = m.examination.name if m.examination else f"Exam {m.examination_id}"
        if ename not in exam_perf_map:
            exam_perf_map[ename] = {"obtained": 0.0, "max": 0.0}
        exam_perf_map[ename]["obtained"] += float(m.marks_obtained)
        exam_perf_map[ename]["max"] += float(m.max_marks)
    exam_performance = [
        {"exam": k, "average_pct": round((v["obtained"] / v["max"]) * 100, 1) if v["max"] else 0}
        for k, v in exam_perf_map.items()
    ]

    # Chart 5: Class-wise results
    class_perf_map = {}
    for m in published_marks:
        cname = m.student.school_class.name if m.student and m.student.school_class else "Unknown"
        if cname not in class_perf_map:
            class_perf_map[cname] = {"obtained": 0.0, "max": 0.0}
        class_perf_map[cname]["obtained"] += float(m.marks_obtained)
        class_perf_map[cname]["max"] += float(m.max_marks)
    class_wise_results = [
        {"class_name": k, "average_pct": round((v["obtained"] / v["max"]) * 100, 1) if v["max"] else 0}
        for k, v in class_perf_map.items()
    ]

    # Chart 6: Subject-wise performance
    subj_perf_map = {}
    for m in published_marks:
        sname = m.subject.name if m.subject else f"Sub {m.subject_id}"
        if sname not in subj_perf_map:
            subj_perf_map[sname] = {"obtained": 0.0, "max": 0.0}
        subj_perf_map[sname]["obtained"] += float(m.marks_obtained)
        subj_perf_map[sname]["max"] += float(m.max_marks)
    subject_wise_performance = [
        {"subject": k, "average_pct": round((v["obtained"] / v["max"]) * 100, 1) if v["max"] else 0}
        for k, v in subj_perf_map.items()
    ]

    return {
        "cards": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "total_fees_collected": total_fees_collected,
            "pending_fees": pending_fees,
            "today_attendance_present": today_present,
            "today_attendance_total": today_total,
            "today_attendance_pct": today_attendance_pct,
            "overall_attendance_pct": overall_attendance_pct,
            "upcoming_examinations": upcoming_exams,
            "published_results": published_results,
            "pending_result_approvals": pending_result_approvals,
            "active_practice_tests": active_practice_tests,
        },
        "charts": {
            "monthly_fee_collection": monthly_fee_collection,
            "enrollment_growth": enrollment_growth,
            "attendance_stats": attendance_stats,
            "exam_performance": exam_performance,
            "class_wise_results": class_wise_results,
            "subject_wise_performance": subject_wise_performance,
        },
    }


# ---------------- STUDENT MANAGEMENT ----------------

def _serialize_student(st: Student, db: Session) -> dict:
    fee = db.query(Fee).filter(Fee.student_id == st.id).order_by(Fee.id.desc()).first()
    return {
        "id": st.id,
        "student_code": st.student_code,
        "student_name": st.student_name,
        "date_of_birth": st.date_of_birth.isoformat() if st.date_of_birth else None,
        "gender": st.gender,
        "class_id": st.class_id,
        "class_name": st.school_class.name if st.school_class else "",
        "section": st.section,
        "address": st.address,
        "student_phone": st.student_phone,
        "parent_id": st.parent_id,
        "parent_name": st.parent_name,
        "parent_phone": st.parent_phone,
        "parent_username": st.parent.user.username if st.parent and st.parent.user else None,
        "admission_date": st.admission_date.isoformat() if st.admission_date else None,
        "photo_path": st.photo_path,
        "assigned_teacher_id": st.assigned_teacher_id,
        "assigned_teacher_name": st.assigned_teacher.teacher_name if st.assigned_teacher else None,
        "total_fees": float(fee.total_fees) if fee else 0.0,
        "paid_fees": float(fee.paid_amount) if fee else 0.0,
        "pending_fees": float(fee.pending_amount) if fee else 0.0,
        "is_active": st.is_active,
        "username": st.user.username if st.user else st.student_code,
    }


@router.get("/students")
def list_students(
    search: Optional[str] = None,
    class_id: Optional[int] = None,
    active_only: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    if active_only is not None:
        q = q.filter(Student.is_active == active_only)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(
            (Student.student_name.ilike(like))
            | (Student.student_code.ilike(like))
            | (Student.parent_name.ilike(like))
            | (Student.parent_phone.ilike(like))
        )
    students = q.order_by(Student.student_code.asc()).all()
    return [_serialize_student(s, db) for s in students]


@router.post("/students")
def create_student(payload: StudentCreate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    cls_obj = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
    if not cls_obj:
        raise HTTPException(status_code=404, detail="Selected class does not exist.")

    student_role = db.query(Role).filter(Role.name == "student").first()
    parent_role = db.query(Role).filter(Role.name == "parent").first()
    year = _get_current_year(db)

    student_code = generate_next_student_code(db)
    s_pwd = (payload.student_password or "").strip() or generate_unique_password("AK")
    s_user = User(
        username=student_code,
        email=f"{student_code.lower()}@student.aktuition.edu.in",
        phone=payload.student_phone or payload.parent_phone,
        full_name=payload.student_name.strip(),
        password_hash=hash_password(s_pwd),
        role_id=student_role.id,
        is_active=True,
    )
    db.add(s_user)
    db.flush()

    # Reuse parent if phone matches or create new parent account
    parent_obj = db.query(Parent).filter(Parent.phone == payload.parent_phone.strip()).first()
    created_parent_username = None
    parent_pwd_out = None
    parent_is_new = False
    if not parent_obj:
        parent_is_new = True
        p_uname = (payload.parent_username or f"parent_{student_code.lower()}").strip()
        if db.query(User).filter(User.username == p_uname).first():
            p_uname = f"parent_{student_code.lower()}_{uuid.uuid4().hex[:4]}"
        p_pwd = (payload.parent_password or "").strip() or generate_unique_password("PR")
        parent_pwd_out = p_pwd
        p_user = User(
            username=p_uname,
            email=payload.parent_email,
            phone=payload.parent_phone.strip(),
            full_name=payload.parent_name.strip(),
            password_hash=hash_password(p_pwd),
            role_id=parent_role.id,
            is_active=True,
        )
        db.add(p_user)
        db.flush()
        parent_obj = Parent(
            user_id=p_user.id,
            parent_name=payload.parent_name.strip(),
            phone=payload.parent_phone.strip(),
            email=payload.parent_email,
            address=payload.address,
        )
        db.add(parent_obj)
        db.flush()
        created_parent_username = p_uname
    else:
        created_parent_username = parent_obj.user.username if parent_obj.user else None

    student = Student(
        user_id=s_user.id,
        student_code=student_code,
        student_name=payload.student_name.strip(),
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        class_id=payload.class_id,
        section=payload.section or cls_obj.section,
        address=payload.address,
        student_phone=payload.student_phone,
        parent_id=parent_obj.id,
        parent_name=payload.parent_name.strip(),
        parent_phone=payload.parent_phone.strip(),
        admission_date=payload.admission_date or date.today(),
        assigned_teacher_id=payload.assigned_teacher_id,
        is_active=True,
    )
    db.add(student)
    db.flush()

    db.add(StudentEnrollment(
        student_id=student.id,
        class_id=cls_obj.id,
        academic_year_id=year.id,
        roll_number=student_code,
        enrolled_date=student.admission_date,
        status="ACTIVE",
    ))

    total_fee = float(payload.total_fees if payload.total_fees is not None else cls_obj.tuition_fee)
    db.add(Fee(
        student_id=student.id,
        academic_year_id=year.id,
        total_fees=total_fee,
        paid_amount=0,
        pending_amount=total_fee,
    ))

    log_audit(db, current_user.id, "CREATE_STUDENT", "student", student_code, {"name": student.student_name}, request)
    db.commit()
    db.refresh(student)

    res = _serialize_student(student, db)
    res["generated_credentials"] = {
        "student_name": student.student_name,
        "student_code": student_code,
        "student_username": student_code,
        "student_password": s_pwd,
        "parent_name": parent_obj.parent_name,
        "parent_username": created_parent_username,
        "parent_phone": parent_obj.phone,
        "parent_password": parent_pwd_out if parent_is_new else None,
        "parent_is_new": parent_is_new,
    }
    return res


@router.post("/students/{student_id}/reset-credentials")
def reset_student_and_parent_credentials(
    student_id: int,
    reset_parent: bool = True,
    request: Request = None,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    st = db.query(Student).filter(Student.id == student_id).first()
    if not st or not st.user:
        raise HTTPException(status_code=404, detail="Student not found.")

    new_student_pwd = generate_unique_password("AK")
    st.user.password_hash = hash_password(new_student_pwd)

    new_parent_pwd = None
    if reset_parent and st.parent and st.parent.user:
        new_parent_pwd = generate_unique_password("PR")
        st.parent.user.password_hash = hash_password(new_parent_pwd)

    log_audit(db, current_user.id, "RESET_STUDENT_CREDENTIALS", "student", st.student_code, {"reset_parent": reset_parent}, request)
    db.commit()
    return {
        "student_name": st.student_name,
        "student_code": st.student_code,
        "student_username": st.user.username,
        "student_password": new_student_pwd,
        "parent_name": st.parent_name,
        "parent_username": st.parent.user.username if st.parent and st.parent.user else None,
        "parent_phone": st.parent_phone,
        "parent_password": new_parent_pwd,
        "parent_is_new": bool(new_parent_pwd),
    }


@router.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    st = db.query(Student).filter(Student.id == student_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found.")

    data = payload.model_dump(exclude_unset=True)
    total_fees = data.pop("total_fees", None)
    for k, v in data.items():
        setattr(st, k, v)

    if "student_name" in data and st.user:
        st.user.full_name = data["student_name"]
    if "is_active" in data and st.user:
        st.user.is_active = data["is_active"]

    if total_fees is not None:
        fee = db.query(Fee).filter(Fee.student_id == st.id).order_by(Fee.id.desc()).first()
        if fee:
            fee.total_fees = total_fees
            fee.pending_amount = max(0.0, float(total_fees) - float(fee.paid_amount))

    log_audit(db, current_user.id, "UPDATE_STUDENT", "student", st.student_code, data, request)
    db.commit()
    db.refresh(st)
    return _serialize_student(st, db)


@router.delete("/students/{student_id}")
def deactivate_or_delete_student(student_id: int, hard_delete: bool = False, request: Request = None, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    st = db.query(Student).filter(Student.id == student_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found.")
    if hard_delete:
        code = st.student_code
        user = st.user
        db.query(Notification).filter(Notification.student_id == st.id).delete()
        db.query(Attendance).filter(Attendance.student_id == st.id).delete()
        db.query(Mark).filter(Mark.student_id == st.id).delete()
        db.query(Payment).filter(Payment.student_id == st.id).delete()
        db.delete(st)
        if user:
            db.query(AuditLog).filter(AuditLog.user_id == user.id).update({"user_id": None})
            db.delete(user)
        log_audit(db, current_user.id, "DELETE_STUDENT", "student", code, None, request)
        db.commit()
        return {"message": f"Student {code} permanently deleted."}
    st.is_active = False
    if st.user:
        st.user.is_active = False
    log_audit(db, current_user.id, "DEACTIVATE_STUDENT", "student", st.student_code, None, request)
    db.commit()
    return {"message": f"Student {st.student_code} deactivated."}


@router.post("/students/{student_id}/photo")
async def upload_student_photo(student_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    st = db.query(Student).filter(Student.id == student_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found.")
    ext = Path(file.filename or "photo.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, JPEG, or WEBP images are allowed.")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit.")
    fname = f"{st.student_code}_{uuid.uuid4().hex[:8]}{ext}"
    dest = STUDENT_PHOTOS_DIR / fname
    dest.write_bytes(content)
    st.photo_path = f"/uploads/student_photos/{fname}"
    db.commit()
    return {"photo_path": st.photo_path}


@router.get("/students/{student_id}/history")
def get_student_academic_history(student_id: int, db: Session = Depends(get_db)):
    st = db.query(Student).filter(Student.id == student_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student not found.")

    marks = db.query(Mark).filter(Mark.student_id == st.id).order_by(Mark.created_at.desc()).all()
    total_att = db.query(Attendance).filter(Attendance.student_id == st.id).count()
    present_att = db.query(Attendance).filter(Attendance.student_id == st.id, Attendance.status == "PRESENT").count()
    payments = db.query(Payment).filter(Payment.student_id == st.id).order_by(Payment.payment_date.desc()).all()

    return {
        "student": _serialize_student(st, db),
        "attendance": {
            "total_working_days": total_att,
            "present_days": present_att,
            "absent_days": total_att - present_att,
            "percentage": round((present_att / total_att) * 100, 2) if total_att else 0.0,
        },
        "marks": [
            {
                "id": m.id,
                "examination": m.examination.name if m.examination else "",
                "subject": m.subject.name if m.subject else "",
                "max_marks": float(m.max_marks),
                "marks_obtained": float(m.marks_obtained),
                "grade": m.grade,
                "status": m.status,
            }
            for m in marks
        ],
        "payments": [
            {
                "id": p.id,
                "amount": float(p.amount),
                "payment_date": p.payment_date.isoformat(),
                "payment_mode": p.payment_mode,
                "receipt_number": p.receipt.receipt_number if p.receipt else None,
            }
            for p in payments
        ],
    }


# ---------------- TEACHER MANAGEMENT ----------------

@router.get("/teachers")
def list_teachers(db: Session = Depends(get_db)):
    teachers = db.query(Teacher).order_by(Teacher.teacher_code.asc()).all()
    result = []
    for t in teachers:
        assigns = [
            {
                "id": a.id,
                "class_id": a.class_id,
                "class_name": f"{a.school_class.name} ({a.school_class.section})" if a.school_class else "",
                "subject_id": a.subject_id,
                "subject_name": a.subject.name if a.subject else "",
                "is_class_teacher": a.is_class_teacher,
            }
            for a in t.assignments
        ]
        result.append({
            "id": t.id,
            "teacher_code": t.teacher_code,
            "teacher_name": t.teacher_name,
            "username": t.user.username if t.user else "",
            "qualification": t.qualification,
            "specialization": t.specialization,
            "phone": t.phone,
            "email": t.email,
            "address": t.address,
            "joining_date": t.joining_date.isoformat() if t.joining_date else None,
            "is_active": t.is_active,
            "assignments": assigns,
        })
    return result


@router.post("/teachers")
def create_teacher(payload: TeacherCreate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    if db.query(User).filter(func.lower(User.username) == payload.username.strip().lower()).first():
        raise HTTPException(status_code=400, detail="Username already exists.")
    t_role = db.query(Role).filter(Role.name == "teacher").first()
    pwd = (payload.password or "").strip() or generate_unique_password("TC")
    t_user = User(
        username=payload.username.strip(),
        email=payload.email,
        phone=payload.phone,
        full_name=payload.teacher_name.strip(),
        password_hash=hash_password(pwd),
        role_id=t_role.id,
        is_active=True,
    )
    db.add(t_user)
    db.flush()

    cnt = db.query(Teacher).count() + 1
    code = f"TCH{cnt:03d}"
    while db.query(Teacher).filter(Teacher.teacher_code == code).first():
        cnt += 1
        code = f"TCH{cnt:03d}"

    t = Teacher(
        user_id=t_user.id,
        teacher_code=code,
        teacher_name=payload.teacher_name.strip(),
        qualification=payload.qualification,
        specialization=payload.specialization,
        phone=payload.phone,
        email=payload.email,
        address=payload.address,
        joining_date=payload.joining_date or date.today(),
    )
    db.add(t)
    log_audit(db, current_user.id, "CREATE_TEACHER", "teacher", code, {"name": t.teacher_name}, request)
    db.commit()
    db.refresh(t)
    return {
        "id": t.id,
        "teacher_code": t.teacher_code,
        "teacher_name": t.teacher_name,
        "username": t_user.username,
        "teacher_password": pwd,
    }


@router.post("/teachers/{teacher_id}/reset-credentials")
def reset_teacher_credentials(
    teacher_id: int,
    request: Request = None,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t or not t.user:
        raise HTTPException(status_code=404, detail="Teacher not found.")
    new_pwd = generate_unique_password("TC")
    t.user.password_hash = hash_password(new_pwd)
    log_audit(db, current_user.id, "RESET_TEACHER_CREDENTIALS", "teacher", t.teacher_code, None, request)
    db.commit()
    return {
        "teacher_code": t.teacher_code,
        "teacher_name": t.teacher_name,
        "username": t.user.username,
        "teacher_password": new_pwd,
    }


@router.put("/teachers/{teacher_id}")
def update_teacher(teacher_id: int, payload: TeacherUpdate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    t = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Teacher not found.")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(t, k, v)
    if "teacher_name" in data and t.user:
        t.user.full_name = data["teacher_name"]
    if "is_active" in data and t.user:
        t.user.is_active = data["is_active"]
    log_audit(db, current_user.id, "UPDATE_TEACHER", "teacher", t.teacher_code, data, request)
    db.commit()
    return {"message": "Teacher updated successfully."}


@router.post("/teacher-assignments")
def assign_teacher(payload: TeacherAssignmentCreate, db: Session = Depends(get_db)):
    year = _get_current_year(db)
    existing = (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.teacher_id == payload.teacher_id,
            TeacherAssignment.class_id == payload.class_id,
            TeacherAssignment.subject_id == payload.subject_id,
            TeacherAssignment.academic_year_id == year.id,
        )
        .first()
    )
    if existing:
        existing.is_class_teacher = payload.is_class_teacher
        db.commit()
        return {"id": existing.id, "message": "Assignment updated."}
    ta = TeacherAssignment(
        teacher_id=payload.teacher_id,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
        academic_year_id=year.id,
        is_class_teacher=payload.is_class_teacher,
    )
    db.add(ta)
    db.commit()
    db.refresh(ta)
    return {"id": ta.id, "message": "Teacher assigned successfully."}


@router.delete("/teacher-assignments/{assignment_id}")
def delete_teacher_assignment(assignment_id: int, db: Session = Depends(get_db)):
    ta = db.query(TeacherAssignment).filter(TeacherAssignment.id == assignment_id).first()
    if not ta:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    db.delete(ta)
    db.commit()
    return {"message": "Assignment removed."}


@router.get("/teacher-attendance")
def list_teacher_attendance(attendance_date: Optional[date] = None, db: Session = Depends(get_db)):
    q = db.query(TeacherAttendance)
    if attendance_date:
        q = q.filter(TeacherAttendance.attendance_date == attendance_date)
    rows = q.order_by(TeacherAttendance.attendance_date.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "teacher_id": r.teacher_id,
            "teacher_code": r.teacher.teacher_code if r.teacher else "",
            "teacher_name": r.teacher.teacher_name if r.teacher else "",
            "attendance_date": r.attendance_date.isoformat(),
            "status": r.status,
            "remarks": r.remarks,
        }
        for r in rows
    ]


@router.post("/teacher-attendance")
def mark_teacher_attendance(payload: TeacherAttendanceEntry, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    existing = (
        db.query(TeacherAttendance)
        .filter(TeacherAttendance.teacher_id == payload.teacher_id, TeacherAttendance.attendance_date == payload.attendance_date)
        .first()
    )
    if existing:
        existing.status = payload.status.upper()
        existing.remarks = payload.remarks
    else:
        db.add(TeacherAttendance(
            teacher_id=payload.teacher_id,
            attendance_date=payload.attendance_date,
            status=payload.status.upper(),
            remarks=payload.remarks,
            marked_by_user_id=current_user.id,
        ))
    db.commit()
    return {"message": "Teacher attendance recorded."}


# ---------------- CLASS & SUBJECT MANAGEMENT ----------------

@router.get("/classes")
def list_classes(db: Session = Depends(get_db)):
    classes = db.query(SchoolClass).order_by(SchoolClass.grade_level.asc(), SchoolClass.section.asc()).all()
    out = []
    for c in classes:
        strength = db.query(Student).filter(Student.class_id == c.id, Student.is_active == True).count()
        class_subjs = db.query(ClassSubject).filter(ClassSubject.class_id == c.id).all()
        out.append({
            "id": c.id,
            "grade_level": c.grade_level,
            "name": c.name,
            "section": c.section,
            "capacity": c.capacity,
            "tuition_fee": float(c.tuition_fee),
            "student_strength": strength,
            "is_active": c.is_active,
            "subjects": [{"id": cs.subject.id, "name": cs.subject.name, "code": cs.subject.code} for cs in class_subjs if cs.subject],
        })
    return out


@router.post("/classes")
def create_class(payload: ClassCreate, db: Session = Depends(get_db)):
    year = _get_current_year(db)
    exists = (
        db.query(SchoolClass)
        .filter(SchoolClass.name == payload.name.strip(), SchoolClass.section == payload.section.strip(), SchoolClass.academic_year_id == year.id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Class with this section already exists for the current academic year.")
    c = SchoolClass(
        grade_level=payload.grade_level,
        name=payload.name.strip(),
        section=payload.section.strip().upper(),
        academic_year_id=year.id,
        capacity=payload.capacity,
        tuition_fee=payload.tuition_fee,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "name": c.name, "section": c.section}


@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db)):
    return [
        {"id": s.id, "name": s.name, "code": s.code, "description": s.description, "is_active": s.is_active}
        for s in db.query(Subject).order_by(Subject.name.asc()).all()
    ]


@router.post("/subjects")
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    if db.query(Subject).filter(func.upper(Subject.code) == payload.code.strip().upper()).first():
        raise HTTPException(status_code=400, detail="Subject code already exists.")
    s = Subject(name=payload.name.strip(), code=payload.code.strip().upper(), description=payload.description)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id, "name": s.name, "code": s.code}


@router.post("/class-subjects")
def assign_subjects_to_class(payload: ClassSubjectAssign, db: Session = Depends(get_db)):
    db.query(ClassSubject).filter(ClassSubject.class_id == payload.class_id).delete()
    for sid in set(payload.subject_ids):
        db.add(ClassSubject(class_id=payload.class_id, subject_id=sid))
    db.commit()
    return {"message": "Subjects updated for class."}


# ---------------- FEE & PAYMENT MANAGEMENT ----------------

@router.get("/fees")
def list_fees(class_id: Optional[int] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Fee).join(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter((Student.student_name.ilike(like)) | (Student.student_code.ilike(like)))
    fees = q.order_by(Student.student_code.asc()).all()

    payments = db.query(Payment).order_by(Payment.payment_date.desc(), Payment.id.desc()).limit(100).all()

    return {
        "student_fees": [
            {
                "fee_id": f.id,
                "student_id": f.student_id,
                "student_code": f.student.student_code,
                "student_name": f.student.student_name,
                "class_name": f"{f.student.school_class.name} ({f.student.section})" if f.student.school_class else "",
                "parent_name": f.student.parent_name,
                "parent_phone": f.student.parent_phone,
                "total_fees": float(f.total_fees),
                "paid_amount": float(f.paid_amount),
                "pending_amount": float(f.pending_amount),
                "due_date": f.due_date.isoformat() if f.due_date else None,
            }
            for f in fees
        ],
        "payments": [
            {
                "id": p.id,
                "student_id": p.student_id,
                "student_code": p.student.student_code if p.student else "",
                "student_name": p.student.student_name if p.student else "",
                "amount": float(p.amount),
                "payment_date": p.payment_date.isoformat(),
                "payment_mode": p.payment_mode,
                "reference_number": p.reference_number,
                "remarks": p.remarks,
                "receipt_number": p.receipt.receipt_number if p.receipt else None,
            }
            for p in payments
        ],
    }


@router.put("/fees/{student_id}")
def update_student_fee(student_id: int, payload: FeeUpdate, db: Session = Depends(get_db)):
    fee = db.query(Fee).filter(Fee.student_id == student_id).order_by(Fee.id.desc()).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee record not found for student.")
    fee.total_fees = payload.total_fees
    fee.pending_amount = max(0.0, float(payload.total_fees) - float(fee.paid_amount))
    fee.due_date = payload.due_date
    fee.notes = payload.notes
    db.commit()
    return {"message": "Fee structure updated."}


@router.post("/payments")
def record_payment(payload: PaymentCreate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    valid_modes = {"CASH", "UPI", "BANK_TRANSFER", "OTHER"}
    mode = payload.payment_mode.strip().upper().replace(" ", "_")
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Payment mode must be one of: {', '.join(sorted(valid_modes))}.")

    if payload.idempotency_key:
        dup_key = db.query(Payment).filter(Payment.idempotency_key == payload.idempotency_key).first()
        if dup_key:
            raise HTTPException(status_code=409, detail="Duplicate payment submission blocked.")

    if payload.reference_number:
        dup_ref = db.query(Payment).filter(Payment.reference_number == payload.reference_number.strip()).first()
        if dup_ref:
            raise HTTPException(status_code=409, detail="A payment with this reference number already exists.")

    fee = db.query(Fee).filter(Fee.student_id == payload.student_id).order_by(Fee.id.desc()).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee record not found for this student.")

    if payload.amount > float(fee.pending_amount) and float(fee.pending_amount) > 0:
        raise HTTPException(status_code=400, detail=f"Payment amount exceeds pending balance (Rs. {float(fee.pending_amount):,.2f}).")

    pay = Payment(
        fee_id=fee.id,
        student_id=payload.student_id,
        amount=payload.amount,
        payment_date=payload.payment_date or date.today(),
        payment_mode=mode,
        reference_number=payload.reference_number.strip() if payload.reference_number else None,
        idempotency_key=payload.idempotency_key,
        remarks=payload.remarks,
        recorded_by_user_id=current_user.id,
    )
    db.add(pay)
    db.flush()

    fee.paid_amount = float(fee.paid_amount) + payload.amount
    fee.pending_amount = max(0.0, float(fee.total_fees) - float(fee.paid_amount))

    receipt_no = f"AKR-{datetime.now().year}-{pay.id:04d}"
    receipt = FeeReceipt(payment_id=pay.id, receipt_number=receipt_no)
    db.add(receipt)
    log_audit(db, current_user.id, "RECORD_PAYMENT", "payment", str(pay.id), {"amount": payload.amount, "mode": mode}, request)
    db.commit()

    return {"id": pay.id, "receipt_number": receipt_no, "pending_amount": float(fee.pending_amount)}


@router.get("/payments/{payment_id}/receipt-pdf")
def download_fee_receipt_pdf(payment_id: int, db: Session = Depends(get_db)):
    pay = db.query(Payment).filter(Payment.id == payment_id).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Payment record not found.")
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
        headers={"Content-Disposition": f'attachment; filename="AK_Receipt_{st.student_code}_{pay.id}.pdf"'},
    )


# ---------------- EXAMINATION MANAGEMENT ----------------

@router.get("/examinations")
def list_examinations(class_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Examination)
    if class_id:
        q = q.filter(Examination.class_id == class_id)
    exams = q.order_by(Examination.start_date.desc()).all()
    return [
        {
            "id": ex.id,
            "name": ex.name,
            "class_id": ex.class_id,
            "class_name": f"{ex.school_class.name} ({ex.school_class.section})" if ex.school_class else "",
            "exam_type": ex.exam_type,
            "start_date": ex.start_date.isoformat(),
            "end_date": ex.end_date.isoformat(),
            "status": ex.status,
            "is_timetable_published": ex.is_timetable_published,
            "instructions": ex.instructions,
            "subjects": [
                {
                    "id": es.id,
                    "subject_id": es.subject_id,
                    "subject_name": es.subject.name if es.subject else "",
                    "exam_date": es.exam_date.isoformat(),
                    "start_time": es.start_time,
                    "duration_minutes": es.duration_minutes,
                    "max_marks": float(es.max_marks),
                    "passing_marks": float(es.passing_marks),
                }
                for es in sorted(ex.exam_subjects, key=lambda x: x.exam_date)
            ],
        }
        for ex in exams
    ]


@router.post("/examinations")
def create_examination(payload: ExaminationCreate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    year = _get_current_year(db)
    ex = Examination(
        name=payload.name.strip(),
        academic_year_id=year.id,
        class_id=payload.class_id,
        exam_type=payload.exam_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="SCHEDULED",
        is_timetable_published=payload.is_timetable_published,
        instructions=payload.instructions,
        created_by_user_id=current_user.id,
    )
    db.add(ex)
    db.flush()

    for sub in payload.subjects:
        db.add(ExaminationSubject(
            examination_id=ex.id,
            subject_id=sub.subject_id,
            exam_date=sub.exam_date,
            start_time=sub.start_time,
            duration_minutes=sub.duration_minutes,
            max_marks=sub.max_marks,
            passing_marks=sub.passing_marks,
        ))
    log_audit(db, current_user.id, "CREATE_EXAMINATION", "examination", str(ex.id), {"name": ex.name}, request)
    db.commit()
    db.refresh(ex)
    return {"id": ex.id, "name": ex.name}


@router.put("/examinations/{exam_id}")
def update_examination(exam_id: int, payload: ExaminationUpdate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    ex = db.query(Examination).filter(Examination.id == exam_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Examination not found.")
    data = payload.model_dump(exclude_unset=True)
    subjects_data = data.pop("subjects", None)
    for k, v in data.items():
        setattr(ex, k, v)
    if subjects_data is not None:
        db.query(ExaminationSubject).filter(ExaminationSubject.examination_id == ex.id).delete()
        for sub in subjects_data:
            db.add(ExaminationSubject(examination_id=ex.id, **sub))
    log_audit(db, current_user.id, "UPDATE_EXAMINATION", "examination", str(ex.id), data, request)
    db.commit()
    return {"message": "Examination updated."}


@router.get("/examinations/{exam_id}/timetable-pdf")
def download_exam_timetable_pdf(exam_id: int, db: Session = Depends(get_db)):
    ex = db.query(Examination).filter(Examination.id == exam_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Examination not found.")
    settings = get_or_create_settings(db)
    rows = [
        [
            idx,
            es.subject.name if es.subject else "",
            es.exam_date.strftime("%d %b %Y (%a)"),
            es.start_time,
            f"{es.duration_minutes} mins",
            f"{float(es.max_marks):.0f}",
        ]
        for idx, es in enumerate(sorted(ex.exam_subjects, key=lambda x: x.exam_date), start=1)
    ]
    cls_label = f"{ex.school_class.name} ({ex.school_class.section})" if ex.school_class else ""
    pdf_bytes = generate_branded_table_pdf(
        title=f"OFFICIAL EXAMINATION TIMETABLE — {ex.name}",
        subtitle=f"Class: {cls_label} | Academic Year: {settings.academic_year_label} | Schedule: {ex.start_date.strftime('%d %b %Y')} to {ex.end_date.strftime('%d %b %Y')}",
        headers=["Sl.", "Subject", "Exam Date", "Start Time", "Duration", "Max Marks"],
        rows=rows,
        logo_path=settings.logo_path,
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
        footer_note=f"Instructions: {ex.instructions or 'Arrive 15 minutes before the scheduled start time.'}",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AK_Timetable_{ex.id}.pdf"'},
    )


# ---------------- RESULT APPROVAL MANAGEMENT (CRITICAL WORKFLOW) ----------------

@router.get("/result-approvals")
def list_result_approvals(status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(ResultApproval)
    if status_filter:
        q = q.filter(ResultApproval.status == status_filter.upper())
    approvals = q.order_by(ResultApproval.submitted_date.desc()).all()

    out = []
    for ap in approvals:
        marks_rows = (
            db.query(Mark)
            .filter(Mark.examination_subject_id == ap.examination_subject_id)
            .order_by(Mark.student_id.asc())
            .all()
        )
        out.append({
            "id": ap.id,
            "examination_id": ap.examination_id,
            "examination_name": ap.examination.name if ap.examination else "",
            "class_name": f"{ap.examination.school_class.name} ({ap.examination.school_class.section})" if ap.examination and ap.examination.school_class else "",
            "examination_subject_id": ap.examination_subject_id,
            "subject_name": ap.examination_subject.subject.name if ap.examination_subject and ap.examination_subject.subject else "",
            "submitted_by": ap.submitted_by.full_name if ap.submitted_by else "",
            "submitted_date": ap.submitted_date.isoformat(),
            "approved_by": ap.approved_by.full_name if ap.approved_by else None,
            "approval_date": ap.approval_date.isoformat() if ap.approval_date else None,
            "status": ap.status,
            "rejection_reason": ap.rejection_reason,
            "notes": ap.notes,
            "marks": [
                {
                    "id": m.id,
                    "student_id": m.student_id,
                    "student_code": m.student.student_code if m.student else "",
                    "student_name": m.student.student_name if m.student else "",
                    "marks_obtained": float(m.marks_obtained),
                    "max_marks": float(m.max_marks),
                    "grade": m.grade,
                    "remarks": m.remarks,
                    "status": m.status,
                }
                for m in marks_rows
            ],
        })
    return out


@router.post("/result-approvals/{approval_id}/review")
def review_result_approval(
    approval_id: int,
    payload: ResultApprovalAction,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    ap = db.query(ResultApproval).filter(ResultApproval.id == approval_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="Result approval submission not found.")

    action = payload.action.strip().upper()
    marks_rows = db.query(Mark).filter(Mark.examination_subject_id == ap.examination_subject_id).all()
    settings = get_or_create_settings(db)

    if action == "APPROVE":
        ap.status = "PUBLISHED"
        ap.approved_by_user_id = current_user.id
        ap.approval_date = datetime.utcnow()
        ap.rejection_reason = None
        for m in marks_rows:
            m.status = "PUBLISHED"

        notified = []
        if payload.send_notifications:
            template = (settings.notification_templates or {}).get(
                "RESULT",
                "Dear Parent, your child {student_name} has received {marks_obtained}/{max_marks} in {exam_name} – {subject_name}. Percentage: {percentage}%. The official result is now published. Please log in to the AK Tuition Parent Portal to download the marks card. – AK Tuition",
            )
            exam_name = ap.examination.name if ap.examination else "Examination"
            subj_name = ap.examination_subject.subject.name if ap.examination_subject and ap.examination_subject.subject else "Subject"
            for m in marks_rows:
                st = m.student
                if not st:
                    continue
                pct = round((float(m.marks_obtained) / float(m.max_marks)) * 100, 1) if float(m.max_marks) else 0.0
                msg = template.format(
                    student_name=st.student_name,
                    marks_obtained=f"{float(m.marks_obtained):g}",
                    max_marks=f"{float(m.max_marks):g}",
                    exam_name=exam_name,
                    subject_name=subj_name,
                    percentage=pct,
                )
                for ch in ("SMS", "WHATSAPP"):
                    n = send_notification(
                        db,
                        recipient_phone=st.parent_phone,
                        channel=ch,
                        notification_type="RESULT",
                        message=msg,
                        dedup_key=f"RESULT_{ap.id}_{m.id}_{ch}",
                        recipient_user_id=st.parent.user_id if st.parent else None,
                        student_id=st.id,
                        parent_id=st.parent_id,
                    )
                    notified.append({"student": st.student_code, "target": "parent", "channel": ch, "status": n.status})
                if st.student_phone and st.student_phone.strip() != st.parent_phone.strip():
                    ns = send_notification(
                        db,
                        recipient_phone=st.student_phone.strip(),
                        channel="SMS",
                        notification_type="RESULT",
                        message=msg,
                        dedup_key=f"RESULT_{ap.id}_{m.id}_STUDENT_SMS",
                        recipient_user_id=st.user_id,
                        student_id=st.id,
                    )
                    notified.append({"student": st.student_code, "target": "student", "channel": "SMS", "status": ns.status})

        log_audit(db, current_user.id, "APPROVE_PUBLISH_RESULT", "result_approval", str(ap.id), {"exam_subject_id": ap.examination_subject_id}, request)
        db.commit()
        return {"status": "PUBLISHED", "message": "Results approved and published.", "notifications": notified}

    elif action == "REJECT":
        if not payload.rejection_reason or not payload.rejection_reason.strip():
            raise HTTPException(status_code=400, detail="A rejection reason is required when rejecting marks.")
        ap.status = "REJECTED"
        ap.approved_by_user_id = current_user.id
        ap.approval_date = datetime.utcnow()
        ap.rejection_reason = payload.rejection_reason.strip()
        for m in marks_rows:
            m.status = "REJECTED"

        log_audit(db, current_user.id, "REJECT_RESULT", "result_approval", str(ap.id), {"reason": ap.rejection_reason}, request)
        db.commit()
        return {"status": "REJECTED", "message": "Marks submission rejected and returned to teacher."}

    raise HTTPException(status_code=400, detail="Action must be APPROVE or REJECT.")


# ---------------- ANNOUNCEMENTS ----------------

@router.get("/announcements")
def list_announcements(db: Session = Depends(get_db)):
    items = db.query(Announcement).order_by(Announcement.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "category": a.category,
            "content": a.content,
            "event_date": a.event_date.isoformat() if a.event_date else None,
            "target_audience": a.target_audience,
            "is_published": a.is_published,
            "is_featured": a.is_featured,
            "created_at": a.created_at.isoformat(),
        }
        for a in items
    ]


@router.post("/announcements")
def create_announcement(payload: AnnouncementCreate, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    a = Announcement(
        title=payload.title.strip(),
        category=payload.category.strip().upper(),
        content=payload.content.strip(),
        event_date=payload.event_date,
        target_audience=payload.target_audience.strip().upper(),
        is_published=payload.is_published,
        is_featured=payload.is_featured,
        created_by_user_id=current_user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "title": a.title}


@router.delete("/announcements/{ann_id}")
def delete_announcement(ann_id: int, db: Session = Depends(get_db)):
    a = db.query(Announcement).filter(Announcement.id == ann_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Announcement not found.")
    db.delete(a)
    db.commit()
    return {"message": "Announcement deleted."}


# ---------------- NOTIFICATIONS (SMS & WHATSAPP) ----------------

@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db)):
    items = db.query(Notification).order_by(Notification.created_at.desc()).limit(200).all()
    settings = get_or_create_settings(db)
    return {
        "mode": {
            "sms_live": bool(settings.sms_enabled and settings.msg91_auth_key),
            "whatsapp_live": bool(settings.whatsapp_enabled and settings.whatsapp_access_token and settings.whatsapp_phone_number_id),
        },
        "notifications": [
            {
                "id": n.id,
                "recipient_phone": n.recipient_phone,
                "channel": n.channel,
                "notification_type": n.notification_type,
                "message": n.message,
                "status": n.status,
                "provider": n.provider,
                "provider_message_id": n.provider_message_id,
                "error_detail": n.error_detail,
                "created_at": n.created_at.isoformat(),
            }
            for n in items
        ],
    }


@router.post("/notifications/dispatch")
def dispatch_notifications(payload: NotificationDispatchRequest, db: Session = Depends(get_db)):
    q = db.query(Student).filter(Student.is_active == True)
    if payload.student_ids:
        q = q.filter(Student.id.in_(payload.student_ids))
    elif payload.class_id:
        q = q.filter(Student.class_id == payload.class_id)
    students = q.all()
    if not students:
        raise HTTPException(status_code=400, detail="No matching active students found.")

    channels = ["SMS", "WHATSAPP"] if payload.channel.upper() == "BOTH" else [payload.channel.upper()]
    dispatched = []
    batch_tag = datetime.utcnow().strftime("%Y%m%d%H%M")
    for st in students:
        msg = payload.message.replace("{student_name}", st.student_name).replace("{student_code}", st.student_code)
        for ch in channels:
            n = send_notification(
                db,
                recipient_phone=st.parent_phone,
                channel=ch,
                notification_type=payload.notification_type.upper(),
                message=msg,
                dedup_key=f"MANUAL_{batch_tag}_{st.id}_{ch}",
                recipient_user_id=st.parent.user_id if st.parent else None,
                student_id=st.id,
                parent_id=st.parent_id,
            )
            dispatched.append({"student": st.student_code, "channel": ch, "status": n.status, "provider": n.provider})
    db.commit()
    return {"dispatched_count": len(dispatched), "results": dispatched}


@router.put("/parents/{parent_id}/consent")
def update_parent_consent(parent_id: int, payload: ParentConsentUpdate, db: Session = Depends(get_db)):
    p = db.query(Parent).filter(Parent.id == parent_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parent not found.")
    p.sms_consent = payload.sms_consent
    p.whatsapp_consent = payload.whatsapp_consent
    db.commit()
    return {"message": "Notification consent updated."}


# ---------------- 13 ADMIN REPORTS (PDF + EXCEL) ----------------

@router.get("/reports/{report_type}")
def generate_report(
    report_type: str,
    format: str = Query("pdf", pattern="^(pdf|xlsx)$"),
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
    examination_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    settings = get_or_create_settings(db)
    rt = report_type.lower()

    if rt == "individual_marks_card":
        if not student_id or not examination_id:
            raise HTTPException(status_code=400, detail="student_id and examination_id are required for individual_marks_card.")
        st = db.query(Student).filter(Student.id == student_id).first()
        ex = db.query(Examination).filter(Examination.id == examination_id).first()
        if not st or not ex:
            raise HTTPException(status_code=404, detail="Student or examination not found.")
        marks = (
            db.query(Mark)
            .filter(Mark.student_id == st.id, Mark.examination_id == ex.id, Mark.status == "PUBLISHED")
            .all()
        )
        if not marks:
            raise HTTPException(status_code=400, detail="No published marks found for this student in the selected examination.")
        total_max = sum(float(m.max_marks) for m in marks)
        total_obt = sum(float(m.marks_obtained) for m in marks)
        pct = round((total_obt / total_max) * 100, 2) if total_max else 0.0
        overall_grade, remark = compute_grade(pct, settings.grading_rules)
        res_status = "PASS" if pct >= 35 else "FAIL"
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
                {
                    "subject": m.subject.name if m.subject else "",
                    "max_marks": float(m.max_marks),
                    "marks_obtained": float(m.marks_obtained),
                    "grade": m.grade,
                    "remarks": m.remarks or "-",
                }
                for m in marks
            ],
            total_max=total_max,
            total_obtained=total_obt,
            percentage=pct,
            overall_grade=overall_grade,
            result_status=res_status,
            teacher_remarks=remark,
            class_rank=rank,
            class_total_students=class_tot,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="MarksCard_{st.student_code}_Exam{ex.id}.pdf"'},
        )

    title = rt.replace("_", " ").title()
    subtitle = f"Academic Year {settings.academic_year_label}"
    headers = []
    rows = []

    if rt in ("overall_students", "class_wise_students"):
        q = db.query(Student)
        if class_id:
            q = q.filter(Student.class_id == class_id)
        students = q.order_by(Student.class_id.asc(), Student.student_code.asc()).all()
        title = "Class-Wise Student Report" if rt == "class_wise_students" else "Overall Student Directory Report"
        headers = ["Student ID", "Student Name", "Class", "Section", "Parent Name", "Parent Phone", "Admission Date", "Status"]
        rows = [
            [
                s.student_code,
                s.student_name,
                s.school_class.name if s.school_class else "",
                s.section,
                s.parent_name,
                s.parent_phone,
                s.admission_date.isoformat(),
                "Active" if s.is_active else "Inactive",
            ]
            for s in students
        ]

    elif rt in ("student_attendance", "absent_students"):
        q = db.query(Attendance).join(Student)
        if class_id:
            q = q.filter(Attendance.class_id == class_id)
        if student_id:
            q = q.filter(Attendance.student_id == student_id)
        if start_date:
            q = q.filter(Attendance.attendance_date >= start_date)
        if end_date:
            q = q.filter(Attendance.attendance_date <= end_date)
        if rt == "absent_students":
            q = q.filter(Attendance.status == "ABSENT")
            title = "Absent Student Report"
        else:
            title = "Student Attendance Register Report"
        recs = q.order_by(Attendance.attendance_date.desc()).limit(500).all()
        headers = ["Date", "Student ID", "Student Name", "Class", "Status", "Remarks"]
        rows = [
            [
                r.attendance_date.isoformat(),
                r.student.student_code if r.student else "",
                r.student.student_name if r.student else "",
                r.school_class.name if r.school_class else "",
                r.status,
                r.remarks or "-",
            ]
            for r in recs
        ]

    elif rt == "overall_attendance_percentage":
        title = "Overall Attendance Percentage Report"
        q = db.query(Student)
        if class_id:
            q = q.filter(Student.class_id == class_id)
        if student_id:
            q = q.filter(Student.id == student_id)
        students = q.order_by(Student.student_code.asc()).all()
        headers = ["Student ID", "Student Name", "Class", "Working Days", "Present Days", "Absent Days", "Attendance %"]
        for s in students:
            aq = db.query(Attendance).filter(Attendance.student_id == s.id)
            if start_date:
                aq = aq.filter(Attendance.attendance_date >= start_date)
            if end_date:
                aq = aq.filter(Attendance.attendance_date <= end_date)
            tot = aq.count()
            pres = aq.filter(Attendance.status == "PRESENT").count()
            pct = round((pres / tot) * 100, 2) if tot else 0.0
            rows.append([s.student_code, s.student_name, s.school_class.name if s.school_class else "", tot, pres, tot - pres, f"{pct}%"])

    elif rt == "examination_timetable":
        title = "Examination Timetable Report"
        q = db.query(ExaminationSubject).join(Examination)
        if class_id:
            q = q.filter(Examination.class_id == class_id)
        if examination_id:
            q = q.filter(ExaminationSubject.examination_id == examination_id)
        items = q.order_by(ExaminationSubject.exam_date.asc()).all()
        headers = ["Examination", "Class", "Subject", "Exam Date", "Start Time", "Duration (min)", "Max Marks"]
        rows = [
            [
                es.examination.name if es.examination else "",
                es.examination.school_class.name if es.examination and es.examination.school_class else "",
                es.subject.name if es.subject else "",
                es.exam_date.isoformat(),
                es.start_time,
                es.duration_minutes,
                float(es.max_marks),
            ]
            for es in items
        ]

    elif rt == "examination_results":
        title = "Examination Results Report (Published)"
        q = db.query(Mark).join(Student).filter(Mark.status == "PUBLISHED")
        if class_id:
            q = q.filter(Student.class_id == class_id)
        if student_id:
            q = q.filter(Mark.student_id == student_id)
        if examination_id:
            q = q.filter(Mark.examination_id == examination_id)
        if subject_id:
            q = q.filter(Mark.subject_id == subject_id)
        marks = q.order_by(Mark.examination_id.desc(), Student.student_code.asc()).all()
        headers = ["Student ID", "Student Name", "Class", "Examination", "Subject", "Max Marks", "Obtained", "Grade"]
        rows = [
            [
                m.student.student_code,
                m.student.student_name,
                m.student.school_class.name if m.student.school_class else "",
                m.examination.name if m.examination else "",
                m.subject.name if m.subject else "",
                float(m.max_marks),
                float(m.marks_obtained),
                m.grade,
            ]
            for m in marks
        ]

    elif rt == "class_wise_performance":
        title = "Class-Wise Academic Performance Report"
        classes = db.query(SchoolClass).order_by(SchoolClass.grade_level.asc()).all()
        headers = ["Class", "Students", "Evaluated Entries", "Total Max", "Total Obtained", "Average %"]
        for c in classes:
            if class_id and c.id != class_id:
                continue
            q = db.query(Mark).join(Student).filter(Student.class_id == c.id, Mark.status == "PUBLISHED")
            if examination_id:
                q = q.filter(Mark.examination_id == examination_id)
            m_list = q.all()
            tot_max = sum(float(m.max_marks) for m in m_list)
            tot_obt = sum(float(m.marks_obtained) for m in m_list)
            avg = round((tot_obt / tot_max) * 100, 2) if tot_max else 0.0
            st_cnt = db.query(Student).filter(Student.class_id == c.id, Student.is_active == True).count()
            rows.append([f"{c.name} ({c.section})", st_cnt, len(m_list), tot_max, tot_obt, f"{avg}%"])

    elif rt in ("fee_collection", "student_payment_history"):
        title = "Student Payment History Report" if rt == "student_payment_history" else "Fee Collection Report"
        q = db.query(Payment).join(Student)
        if class_id:
            q = q.filter(Student.class_id == class_id)
        if student_id:
            q = q.filter(Payment.student_id == student_id)
        if start_date:
            q = q.filter(Payment.payment_date >= start_date)
        if end_date:
            q = q.filter(Payment.payment_date <= end_date)
        pays = q.order_by(Payment.payment_date.desc()).all()
        headers = ["Receipt No", "Date", "Student ID", "Student Name", "Class", "Mode", "Reference", "Amount (Rs.)"]
        rows = [
            [
                p.receipt.receipt_number if p.receipt else f"AKR-{p.id}",
                p.payment_date.isoformat(),
                p.student.student_code,
                p.student.student_name,
                p.student.school_class.name if p.student.school_class else "",
                p.payment_mode,
                p.reference_number or "-",
                f"{float(p.amount):,.2f}",
            ]
            for p in pays
        ]

    elif rt == "pending_fees":
        title = "Pending Tuition Fee Report"
        q = db.query(Fee).join(Student).filter(Fee.pending_amount > 0)
        if class_id:
            q = q.filter(Student.class_id == class_id)
        if student_id:
            q = q.filter(Fee.student_id == student_id)
        fees = q.order_by(Fee.pending_amount.desc()).all()
        headers = ["Student ID", "Student Name", "Class", "Parent Phone", "Total Fee", "Paid", "Pending"]
        rows = [
            [
                f.student.student_code,
                f.student.student_name,
                f.student.school_class.name if f.student.school_class else "",
                f.student.parent_phone,
                f"{float(f.total_fees):,.2f}",
                f"{float(f.paid_amount):,.2f}",
                f"{float(f.pending_amount):,.2f}",
            ]
            for f in fees
        ]

    elif rt == "teacher_report":
        title = "Faculty & Teaching Assignments Report"
        teachers = db.query(Teacher).order_by(Teacher.teacher_code.asc()).all()
        headers = ["Teacher ID", "Name", "Qualification", "Specialization", "Phone", "Assigned Subjects", "Status"]
        for t in teachers:
            assigns = ", ".join(
                f"{a.school_class.name} {a.subject.code}" for a in t.assignments if a.school_class and a.subject
            ) or "None"
            rows.append([t.teacher_code, t.teacher_name, t.qualification or "-", t.specialization or "-", t.phone, assigns, "Active" if t.is_active else "Inactive"])

    else:
        raise HTTPException(status_code=404, detail=f"Unknown report type '{report_type}'.")

    if format == "xlsx":
        xls_bytes = generate_excel_report(title=title, headers=headers, rows=rows)
        return Response(
            content=xls_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="AKTP_{rt}.xlsx"'},
        )

    pdf_bytes = generate_branded_table_pdf(
        title=title,
        subtitle=subtitle,
        headers=headers,
        rows=rows,
        logo_path=settings.logo_path,
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
        landscape_mode=len(headers) > 6,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AKTP_{rt}.pdf"'},
    )


# ---------------- ADMIN SETTINGS & AUDIT LOGS ----------------

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    s = get_or_create_settings(db)
    return {
        "tuition_name": s.tuition_name,
        "tagline": s.tagline,
        "director_name": s.director_name,
        "director_designation": s.director_designation,
        "director_signature_path": s.director_signature_path,
        "logo_path": s.logo_path or "/assets/ak-tuition-logo.png",
        "phone": s.phone,
        "email": s.email,
        "address": s.address,
        "academic_year_label": s.academic_year_label,
        "grading_rules": s.grading_rules,
        "attendance_min_percentage": float(s.attendance_min_percentage),
        "exam_settings": s.exam_settings,
        "sms_provider": s.sms_provider,
        "sms_enabled": s.sms_enabled,
        "msg91_sender_id": s.msg91_sender_id,
        "msg91_template_id": s.msg91_template_id,
        "has_msg91_auth_key": bool(s.msg91_auth_key),
        "whatsapp_enabled": s.whatsapp_enabled,
        "whatsapp_phone_number_id": s.whatsapp_phone_number_id,
        "has_whatsapp_access_token": bool(s.whatsapp_access_token),
        "notification_templates": s.notification_templates,
    }


@router.put("/settings")
def update_settings(payload: SettingsUpdate, request: Request, current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    s = get_or_create_settings(db)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k in ("msg91_auth_key", "whatsapp_access_token") and (v is None or v == ""):
            continue
        setattr(s, k, v)
    log_audit(db, current_user.id, "UPDATE_SETTINGS", "institution_settings", str(s.id), {"keys": list(data.keys())}, request)
    db.commit()
    return {"message": "Settings updated successfully."}


@router.post("/settings/signature")
async def upload_director_signature(file: UploadFile = File(...), current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    ext = Path(file.filename or "sig.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Only PNG or JPG signature images are allowed.")
    content = await file.read()
    fname = f"director_sig_{uuid.uuid4().hex[:8]}{ext}"
    (SIGNATURES_DIR / fname).write_bytes(content)
    s = get_or_create_settings(db)
    s.director_signature_path = f"/uploads/signatures/{fname}"
    log_audit(db, current_user.id, "UPLOAD_DIRECTOR_SIGNATURE", "institution_settings", str(s.id))
    db.commit()
    return {"director_signature_path": s.director_signature_path}


@router.post("/settings/logo")
async def upload_official_logo(file: UploadFile = File(...), current_user: User = Depends(require_roles(["admin"])), db: Session = Depends(get_db)):
    ext = Path(file.filename or "logo.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="Only PNG or JPG logo images are allowed.")
    content = await file.read()
    fname = f"ak_logo_{uuid.uuid4().hex[:8]}{ext}"
    (LOGOS_DIR / fname).write_bytes(content)
    s = get_or_create_settings(db)
    s.logo_path = f"/uploads/logos/{fname}"
    log_audit(db, current_user.id, "UPLOAD_LOGO", "institution_settings", str(s.id))
    db.commit()
    return {"logo_path": s.logo_path}


@router.get("/audit-logs")
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "user": l.user.username if l.user else "Public/System",
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
