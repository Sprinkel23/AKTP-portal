from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Announcement,
    Attendance,
    Examination,
    Fee,
    Mark,
    Notification,
    Parent,
    Payment,
    Student,
    User,
)
from app.schemas import ParentConsentUpdate
from app.security import require_roles
from app.services.helpers import compute_class_rank, compute_grade, get_or_create_settings
from app.services.pdf_generator import (
    generate_branded_table_pdf,
    generate_fee_receipt_pdf,
    generate_marks_card_pdf,
)

router = APIRouter(
    prefix="/api/parent",
    tags=["Parent"],
    dependencies=[Depends(require_roles(["parent"]))],
)


def _get_parent_and_child(current_user: User, db: Session, student_id: Optional[int] = None) -> tuple[Parent, list[Student], Student]:
    parent = db.query(Parent).filter(Parent.user_id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent profile not found.")
    children = db.query(Student).filter(Student.parent_id == parent.id).order_by(Student.student_code.asc()).all()
    if not children:
        raise HTTPException(status_code=404, detail="No students linked to this parent account.")
    if student_id:
        match = next((c for c in children if c.id == student_id), None)
        if not match:
            raise HTTPException(status_code=403, detail="Access denied: You can only view your own child's records.")
        return parent, children, match
    return parent, children, children[0]


@router.get("/dashboard")
def parent_dashboard(student_id: Optional[int] = None, current_user: User = Depends(require_roles(["parent"])), db: Session = Depends(get_db)):
    parent, children, child = _get_parent_and_child(current_user, db, student_id)
    settings = get_or_create_settings(db)

    tot_att = db.query(Attendance).filter(Attendance.student_id == child.id).count()
    pres_att = db.query(Attendance).filter(Attendance.student_id == child.id, Attendance.status == "PRESENT").count()
    absent_rows = (
        db.query(Attendance)
        .filter(Attendance.student_id == child.id, Attendance.status == "ABSENT")
        .order_by(Attendance.attendance_date.desc())
        .all()
    )

    today = date.today()
    upcoming_exams = (
        db.query(Examination)
        .filter(Examination.class_id == child.class_id, Examination.is_timetable_published == True, Examination.status != "CANCELLED", Examination.end_date >= today)
        .order_by(Examination.start_date.asc())
        .all()
    )

    published_marks = (
        db.query(Mark)
        .filter(Mark.student_id == child.id, Mark.status == "PUBLISHED")
        .order_by(Mark.examination_id.desc())
        .all()
    )

    # Subject-wise performance chart data
    subj_map = {}
    for m in published_marks:
        sname = m.subject.name if m.subject else "Subject"
        if sname not in subj_map:
            subj_map[sname] = {"obtained": 0.0, "max": 0.0}
        subj_map[sname]["obtained"] += float(m.marks_obtained)
        subj_map[sname]["max"] += float(m.max_marks)
    subject_performance = [
        {"subject": k, "percentage": round((v["obtained"] / v["max"]) * 100, 1) if v["max"] else 0}
        for k, v in subj_map.items()
    ]

    fee = db.query(Fee).filter(Fee.student_id == child.id).order_by(Fee.id.desc()).first()
    payments = db.query(Payment).filter(Payment.student_id == child.id).order_by(Payment.payment_date.desc()).all()
    announcements = (
        db.query(Announcement)
        .filter(Announcement.is_published == True, Announcement.target_audience.in_(["PUBLIC", "ALL", "PARENTS"]))
        .order_by(Announcement.created_at.desc())
        .limit(10)
        .all()
    )
    notifications = (
        db.query(Notification)
        .filter(Notification.parent_id == parent.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )

    # Group published results by examination for marks card rendering
    grouped_results = {}
    for m in published_marks:
        eid = m.examination_id
        if eid not in grouped_results:
            ex = m.examination
            grouped_results[eid] = {
                "examination_id": eid,
                "examination_name": ex.name if ex else "",
                "exam_date": f"{ex.start_date.strftime('%d %b %Y')} - {ex.end_date.strftime('%d %b %Y')}" if ex else "",
                "subjects": [],
                "total_max": 0.0,
                "total_obtained": 0.0,
            }
        grouped_results[eid]["subjects"].append({
            "subject": m.subject.name if m.subject else "",
            "max_marks": float(m.max_marks),
            "marks_obtained": float(m.marks_obtained),
            "grade": m.grade,
            "remarks": m.remarks or "-",
        })
        grouped_results[eid]["total_max"] += float(m.max_marks)
        grouped_results[eid]["total_obtained"] += float(m.marks_obtained)

    results_list = []
    for eid, g in grouped_results.items():
        pct = round((g["total_obtained"] / g["total_max"]) * 100, 2) if g["total_max"] else 0.0
        grade, remark = compute_grade(pct, settings.grading_rules)
        rank, class_tot = compute_class_rank(db, eid, child.class_id, child.id)
        g["percentage"] = pct
        g["overall_grade"] = grade
        g["class_rank"] = rank
        g["class_total_students"] = class_tot
        g["result_status"] = "PASS" if pct >= 35 else "FAIL"
        g["teacher_remarks"] = remark
        g["director_name"] = settings.director_name
        g["director_designation"] = settings.director_designation
        g["director_signature_path"] = settings.director_signature_path
        results_list.append(g)

    return {
        "parent": {
            "id": parent.id,
            "parent_name": parent.parent_name,
            "phone": parent.phone,
            "sms_consent": parent.sms_consent,
            "whatsapp_consent": parent.whatsapp_consent,
        },
        "children": [
            {
                "id": c.id,
                "student_code": c.student_code,
                "student_name": c.student_name,
                "class_name": f"{c.school_class.name} ({c.section})" if c.school_class else "",
            }
            for c in children
        ],
        "selected_child": {
            "id": child.id,
            "student_code": child.student_code,
            "student_name": child.student_name,
            "class_name": child.school_class.name if child.school_class else "",
            "section": child.section,
            "photo_path": child.photo_path,
            "admission_date": child.admission_date.isoformat() if child.admission_date else None,
        },
        "attendance": {
            "total_working_days": tot_att,
            "present_days": pres_att,
            "absent_days": tot_att - pres_att,
            "attendance_percentage": round((pres_att / tot_att) * 100, 2) if tot_att else 0.0,
            "absent_details": [
                {"absent_date": a.attendance_date.isoformat(), "attendance_status": a.status}
                for a in absent_rows
            ],
        },
        "upcoming_examinations": [
            {
                "id": ex.id,
                "name": ex.name,
                "start_date": ex.start_date.isoformat(),
                "end_date": ex.end_date.isoformat(),
                "subjects": [
                    {
                        "subject_name": es.subject.name if es.subject else "",
                        "exam_date": es.exam_date.isoformat(),
                        "start_time": es.start_time,
                        "duration_minutes": es.duration_minutes,
                        "max_marks": float(es.max_marks),
                    }
                    for es in sorted(ex.exam_subjects, key=lambda x: x.exam_date)
                ],
            }
            for ex in upcoming_exams
        ],
        "published_results": results_list,
        "subject_performance": subject_performance,
        "fees": {
            "total_fees": float(fee.total_fees) if fee else 0.0,
            "paid_amount": float(fee.paid_amount) if fee else 0.0,
            "pending_amount": float(fee.pending_amount) if fee else 0.0,
            "payments": [
                {
                    "id": p.id,
                    "amount": float(p.amount),
                    "payment_date": p.payment_date.isoformat(),
                    "payment_mode": p.payment_mode,
                    "reference_number": p.reference_number,
                    "receipt_number": p.receipt.receipt_number if p.receipt else None,
                }
                for p in payments
            ],
        },
        "announcements": [
            {
                "id": a.id,
                "title": a.title,
                "category": a.category,
                "content": a.content,
                "event_date": a.event_date.isoformat() if a.event_date else None,
            }
            for a in announcements
        ],
        "notifications": [
            {
                "id": n.id,
                "channel": n.channel,
                "notification_type": n.notification_type,
                "message": n.message,
                "status": n.status,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifications
        ],
    }


@router.put("/consent")
def update_my_consent(payload: ParentConsentUpdate, current_user: User = Depends(require_roles(["parent"])), db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.user_id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent profile not found.")
    parent.sms_consent = payload.sms_consent
    parent.whatsapp_consent = payload.whatsapp_consent
    db.commit()
    return {"message": "Notification preferences saved."}


@router.get("/children/{student_id}/examinations/{exam_id}/timetable-pdf")
def parent_timetable_pdf(student_id: int, exam_id: int, current_user: User = Depends(require_roles(["parent"])), db: Session = Depends(get_db)):
    _, _, child = _get_parent_and_child(current_user, db, student_id)
    ex = db.query(Examination).filter(Examination.id == exam_id, Examination.class_id == child.class_id, Examination.is_timetable_published == True).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Examination timetable not found.")
    settings = get_or_create_settings(db)
    rows = [
        [idx, es.subject.name if es.subject else "", es.exam_date.strftime("%d %b %Y"), es.start_time, f"{es.duration_minutes} mins", f"{float(es.max_marks):.0f}"]
        for idx, es in enumerate(sorted(ex.exam_subjects, key=lambda x: x.exam_date), start=1)
    ]
    pdf_bytes = generate_branded_table_pdf(
        title=f"EXAMINATION TIMETABLE — {ex.name}",
        subtitle=f"Student: {child.student_name} ({child.student_code}) | Class: {child.school_class.name if child.school_class else ''}",
        headers=["Sl.", "Subject", "Date", "Time", "Duration", "Max Marks"],
        rows=rows,
        logo_path=settings.logo_path,
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="AK_Timetable_{child.student_code}.pdf"'})


@router.get("/children/{student_id}/results/{exam_id}/marks-card-pdf")
def parent_marks_card_pdf(student_id: int, exam_id: int, current_user: User = Depends(require_roles(["parent"])), db: Session = Depends(get_db)):
    _, _, child = _get_parent_and_child(current_user, db, student_id)
    ex = db.query(Examination).filter(Examination.id == exam_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Examination not found.")
    marks = db.query(Mark).filter(Mark.student_id == child.id, Mark.examination_id == exam_id, Mark.status == "PUBLISHED").all()
    if not marks:
        raise HTTPException(status_code=403, detail="Official marks card is only available after administrator approval and publication.")
    settings = get_or_create_settings(db)
    total_max = sum(float(m.max_marks) for m in marks)
    total_obt = sum(float(m.marks_obtained) for m in marks)
    pct = round((total_obt / total_max) * 100, 2) if total_max else 0.0
    grade, remark = compute_grade(pct, settings.grading_rules)
    rank, class_tot = compute_class_rank(db, ex.id, child.class_id, child.id)
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
        student_name=child.student_name,
        student_code=child.student_code,
        class_name=child.school_class.name if child.school_class else "",
        section=child.section,
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
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="AK_MarksCard_{child.student_code}_Exam{ex.id}.pdf"'})


@router.get("/children/{student_id}/payments/{payment_id}/receipt-pdf")
def parent_receipt_pdf(student_id: int, payment_id: int, current_user: User = Depends(require_roles(["parent"])), db: Session = Depends(get_db)):
    _, _, child = _get_parent_and_child(current_user, db, student_id)
    pay = db.query(Payment).filter(Payment.id == payment_id, Payment.student_id == child.id).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Payment receipt not found.")
    settings = get_or_create_settings(db)
    fee = pay.fee
    pdf_bytes = generate_fee_receipt_pdf(
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
        address=settings.address,
        phone=settings.phone,
        logo_path=settings.logo_path,
        receipt_number=pay.receipt.receipt_number if pay.receipt else f"AKR-{pay.id:04d}",
        payment_date=pay.payment_date.strftime("%d %b %Y"),
        student_name=child.student_name,
        student_code=child.student_code,
        class_name=f"{child.school_class.name} ({child.section})" if child.school_class else "",
        parent_name=child.parent_name,
        payment_mode=pay.payment_mode,
        reference_number=pay.reference_number or "",
        amount_paid=float(pay.amount),
        total_fees=float(fee.total_fees),
        total_paid_to_date=float(fee.paid_amount),
        pending_amount=float(fee.pending_amount),
        remarks=pay.remarks or "",
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="AK_Receipt_{child.student_code}_{pay.id}.pdf"'})
