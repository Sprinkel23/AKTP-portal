from datetime import date
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Announcement, Examination, SchoolClass, Student, Subject, Teacher
from app.schemas import ContactInquiryRequest
from app.security import log_audit
from app.services.helpers import get_or_create_settings

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
