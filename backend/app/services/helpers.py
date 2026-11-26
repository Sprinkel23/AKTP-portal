import secrets
import string
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import InstitutionSetting, Student

DEFAULT_GRADING_RULES = [
    {"min_pct": 90, "grade": "A+", "remark": "Outstanding"},
    {"min_pct": 80, "grade": "A", "remark": "Excellent"},
    {"min_pct": 70, "grade": "B+", "remark": "Very Good"},
    {"min_pct": 60, "grade": "B", "remark": "Good"},
    {"min_pct": 50, "grade": "C", "remark": "Satisfactory"},
    {"min_pct": 35, "grade": "D", "remark": "Pass"},
    {"min_pct": 0, "grade": "F", "remark": "Needs Improvement"},
]

DEFAULT_NOTIFICATION_TEMPLATES = {
    "RESULT": (
        "Dear Parent, your child {student_name} has received {marks_obtained}/{max_marks} "
        "in {exam_name} – {subject_name}. Percentage: {percentage}%. The official result is now "
        "published. Please log in to the AK Tuition Parent Portal to download the marks card. – AK Tuition"
    ),
    "EXAM_TIMETABLE": (
        "Dear Parent, the examination timetable for {exam_name} (Class {class_name}) has been published. "
        "Exams begin on {start_date}. Please check the AK Tuition Parent Portal. – AK Tuition"
    ),
    "ATTENDANCE_ALERT": (
        "Dear Parent, your child {student_name} ({student_code}) was marked ABSENT on {date}. "
        "Current attendance: {percentage}%. – AK Tuition"
    ),
    "FEE_REMINDER": (
        "Dear Parent, a tuition fee balance of Rs. {pending_amount} is pending for {student_name} ({student_code}). "
        "Kindly clear the dues at your earliest convenience. – AK Tuition"
    ),
}


def get_or_create_settings(db: Session) -> InstitutionSetting:
    settings = db.query(InstitutionSetting).first()
    if not settings:
        settings = InstitutionSetting(
            tuition_name="AK TUITION",
            tagline="Learn • Practise • Achieve",
            director_name="G. Akash, B.E.",
            director_designation="Director, AK Tuition",
            logo_path="/assets/ak-tuition-logo.png",
            phone="+91 72042 09785",
            email="akashgakash140@gmail.com",
            address="AK Tuition Campus, Bengaluru, Karnataka, India",
            academic_year_label="2026-2027",
            grading_rules=DEFAULT_GRADING_RULES,
            attendance_min_percentage=75.00,
            exam_settings={"passing_percentage": 35, "allow_practice_auto_eval": True},
            sms_provider="MSG91",
            sms_enabled=False,
            whatsapp_enabled=False,
            notification_templates=DEFAULT_NOTIFICATION_TEMPLATES,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def compute_grade(percentage: float, grading_rules: Optional[list] = None) -> tuple[str, str]:
    rules = grading_rules or DEFAULT_GRADING_RULES
    sorted_rules = sorted(rules, key=lambda r: float(r.get("min_pct", 0)), reverse=True)
    for rule in sorted_rules:
        if percentage >= float(rule.get("min_pct", 0)):
            return rule.get("grade", "D"), rule.get("remark", "Pass")
    return "F", "Needs Improvement"


def generate_next_student_code(db: Session) -> str:
    codes = db.query(Student.student_code).all()
    max_num = 0
    for (code,) in codes:
        if code and code.upper().startswith("AK"):
            suffix = code[2:]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"AK{max_num + 1:03d}"


def generate_unique_password(prefix: str = "AK") -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    digits = "".join(secrets.choice(string.digits) for _ in range(4))
    suffix = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{prefix}@{digits}{suffix}"


def compute_class_rank(db: Session, examination_id: int, class_id: int, student_id: int) -> tuple[Optional[int], int]:
    from app.models import Mark, Student

    rows = (
        db.query(Mark.student_id, func.sum(Mark.marks_obtained).label("total_marks"))
        .join(Student, Student.id == Mark.student_id)
        .filter(
            Mark.examination_id == examination_id,
            Mark.status == "PUBLISHED",
            Student.class_id == class_id,
        )
        .group_by(Mark.student_id)
        .order_by(func.sum(Mark.marks_obtained).desc())
        .all()
    )
    if not rows:
        return None, 0
    total_students = len(rows)
    rank = 0
    prev_score = None
    for idx, (sid, score) in enumerate(rows, start=1):
        val = float(score or 0)
        if prev_score is None or val < prev_score:
            rank = idx
            prev_score = val
        if sid == student_id:
            return rank, total_students
    return None, total_students
