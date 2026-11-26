from datetime import date, datetime
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
    Payment,
    QuestionOption,
    QuestionPaper,
    Student,
    StudentAnswer,
    StudentTestAttempt,
    User,
)
from app.schemas import TestAttemptSubmit
from app.security import require_roles
from app.services.helpers import compute_class_rank, compute_grade, get_or_create_settings
from app.services.pdf_generator import (
    generate_branded_table_pdf,
    generate_fee_receipt_pdf,
    generate_marks_card_pdf,
)

router = APIRouter(
    prefix="/api/student",
    tags=["Student"],
    dependencies=[Depends(require_roles(["student"]))],
)


def _get_student(current_user: User, db: Session) -> Student:
    st = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return st


@router.get("/dashboard")
def student_dashboard(current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    tot_att = db.query(Attendance).filter(Attendance.student_id == st.id).count()
    pres_att = db.query(Attendance).filter(Attendance.student_id == st.id, Attendance.status == "PRESENT").count()
    att_pct = round((pres_att / tot_att) * 100, 2) if tot_att else 0.0

    today = date.today()
    upcoming_exams = (
        db.query(Examination)
        .filter(
            Examination.class_id == st.class_id,
            Examination.is_timetable_published == True,
            Examination.status != "CANCELLED",
            Examination.end_date >= today,
        )
        .order_by(Examination.start_date.asc())
        .all()
    )

    published_marks = (
        db.query(Mark)
        .filter(Mark.student_id == st.id, Mark.status == "PUBLISHED")
        .order_by(Mark.created_at.desc())
        .limit(8)
        .all()
    )

    fee = db.query(Fee).filter(Fee.student_id == st.id).order_by(Fee.id.desc()).first()
    announcements = (
        db.query(Announcement)
        .filter(Announcement.is_published == True, Announcement.target_audience.in_(["PUBLIC", "ALL", "STUDENTS"]))
        .order_by(Announcement.created_at.desc())
        .limit(8)
        .all()
    )

    return {
        "profile": {
            "id": st.id,
            "student_code": st.student_code,
            "student_name": st.student_name,
            "class_id": st.class_id,
            "class_name": st.school_class.name if st.school_class else "",
            "section": st.section,
            "date_of_birth": st.date_of_birth.isoformat() if st.date_of_birth else None,
            "gender": st.gender,
            "address": st.address,
            "student_phone": st.student_phone,
            "parent_name": st.parent_name,
            "parent_phone": st.parent_phone,
            "admission_date": st.admission_date.isoformat() if st.admission_date else None,
            "photo_path": st.photo_path,
        },
        "attendance_summary": {
            "total_working_days": tot_att,
            "present_days": pres_att,
            "absent_days": tot_att - pres_att,
            "attendance_percentage": att_pct,
        },
        "fee_summary": {
            "total_fees": float(fee.total_fees) if fee else 0.0,
            "paid_amount": float(fee.paid_amount) if fee else 0.0,
            "pending_amount": float(fee.pending_amount) if fee else 0.0,
        },
        "upcoming_examinations": [
            {
                "id": ex.id,
                "name": ex.name,
                "start_date": ex.start_date.isoformat(),
                "end_date": ex.end_date.isoformat(),
                "exam_type": ex.exam_type,
            }
            for ex in upcoming_exams
        ],
        "recent_published_results": [
            {
                "id": m.id,
                "examination_id": m.examination_id,
                "examination_name": m.examination.name if m.examination else "",
                "subject_name": m.subject.name if m.subject else "",
                "marks_obtained": float(m.marks_obtained),
                "max_marks": float(m.max_marks),
                "grade": m.grade,
            }
            for m in published_marks
        ],
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
    }


@router.get("/attendance")
def student_attendance(current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    tot_att = db.query(Attendance).filter(Attendance.student_id == st.id).count()
    pres_att = db.query(Attendance).filter(Attendance.student_id == st.id, Attendance.status == "PRESENT").count()
    absent_rows = (
        db.query(Attendance)
        .filter(Attendance.student_id == st.id, Attendance.status == "ABSENT")
        .order_by(Attendance.attendance_date.desc())
        .all()
    )
    return {
        "total_working_days": tot_att,
        "present_days": pres_att,
        "absent_days": tot_att - pres_att,
        "attendance_percentage": round((pres_att / tot_att) * 100, 2) if tot_att else 0.0,
        # Dedicated absent-details section: ONLY Absent Date & Attendance Status
        "absent_details": [
            {
                "absent_date": a.attendance_date.isoformat(),
                "attendance_status": a.status,
            }
            for a in absent_rows
        ],
    }


@router.get("/examinations")
def student_examinations(current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    exams = (
        db.query(Examination)
        .filter(Examination.class_id == st.class_id, Examination.is_timetable_published == True, Examination.status != "CANCELLED")
        .order_by(Examination.start_date.desc())
        .all()
    )
    return [
        {
            "id": ex.id,
            "name": ex.name,
            "exam_type": ex.exam_type,
            "start_date": ex.start_date.isoformat(),
            "end_date": ex.end_date.isoformat(),
            "instructions": ex.instructions,
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
        for ex in exams
    ]


@router.get("/examinations/{exam_id}/timetable-pdf")
def download_student_timetable_pdf(exam_id: int, current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    ex = db.query(Examination).filter(Examination.id == exam_id, Examination.class_id == st.class_id, Examination.is_timetable_published == True).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Examination timetable not found.")
    settings = get_or_create_settings(db)
    rows = [
        [idx, es.subject.name if es.subject else "", es.exam_date.strftime("%d %b %Y"), es.start_time, f"{es.duration_minutes} mins", f"{float(es.max_marks):.0f}"]
        for idx, es in enumerate(sorted(ex.exam_subjects, key=lambda x: x.exam_date), start=1)
    ]
    pdf_bytes = generate_branded_table_pdf(
        title=f"EXAMINATION TIMETABLE — {ex.name}",
        subtitle=f"Class: {st.school_class.name if st.school_class else ''} ({st.section}) | Student: {st.student_name} ({st.student_code})",
        headers=["Sl.", "Subject", "Date", "Time", "Duration", "Max Marks"],
        rows=rows,
        logo_path=settings.logo_path,
        tuition_name=settings.tuition_name,
        tagline=settings.tagline,
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="AK_Timetable_{ex.id}.pdf"'})


@router.get("/results")
def student_published_results(current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    settings = get_or_create_settings(db)
    marks = (
        db.query(Mark)
        .filter(Mark.student_id == st.id, Mark.status == "PUBLISHED")
        .order_by(Mark.examination_id.desc(), Mark.id.asc())
        .all()
    )
    grouped = {}
    for m in marks:
        eid = m.examination_id
        if eid not in grouped:
            ex = m.examination
            grouped[eid] = {
                "examination_id": eid,
                "examination_name": ex.name if ex else "",
                "exam_date": f"{ex.start_date.strftime('%d %b %Y')} - {ex.end_date.strftime('%d %b %Y')}" if ex else "",
                "subjects": [],
                "total_max": 0.0,
                "total_obtained": 0.0,
            }
        grouped[eid]["subjects"].append({
            "subject": m.subject.name if m.subject else "",
            "max_marks": float(m.max_marks),
            "marks_obtained": float(m.marks_obtained),
            "grade": m.grade,
            "remarks": m.remarks or "-",
        })
        grouped[eid]["total_max"] += float(m.max_marks)
        grouped[eid]["total_obtained"] += float(m.marks_obtained)

    results = []
    for eid, g in grouped.items():
        pct = round((g["total_obtained"] / g["total_max"]) * 100, 2) if g["total_max"] else 0.0
        grade, remark = compute_grade(pct, settings.grading_rules)
        rank, class_tot = compute_class_rank(db, eid, st.class_id, st.id)
        g["percentage"] = pct
        g["overall_grade"] = grade
        g["class_rank"] = rank
        g["class_total_students"] = class_tot
        g["result_status"] = "PASS" if pct >= 35 else "FAIL"
        g["teacher_remarks"] = remark
        g["student_name"] = st.student_name
        g["student_code"] = st.student_code
        g["class_name"] = st.school_class.name if st.school_class else ""
        g["section"] = st.section
        g["academic_year"] = settings.academic_year_label
        g["director_name"] = settings.director_name
        g["director_designation"] = settings.director_designation
        g["director_signature_path"] = settings.director_signature_path
        g["logo_path"] = settings.logo_path or "/assets/ak-tuition-logo.png"
        results.append(g)
    return results


@router.get("/results/{exam_id}/marks-card-pdf")
def download_student_marks_card_pdf(exam_id: int, current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    ex = db.query(Examination).filter(Examination.id == exam_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Examination not found.")
    marks = db.query(Mark).filter(Mark.student_id == st.id, Mark.examination_id == exam_id, Mark.status == "PUBLISHED").all()
    if not marks:
        raise HTTPException(status_code=403, detail="Official marks card is only available after administrator approval and publication.")
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
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="AK_MarksCard_{st.student_code}_Exam{ex.id}.pdf"'})


@router.get("/fees")
def student_fees(current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    fee = db.query(Fee).filter(Fee.student_id == st.id).order_by(Fee.id.desc()).first()
    payments = db.query(Payment).filter(Payment.student_id == st.id).order_by(Payment.payment_date.desc()).all()
    return {
        "total_fees": float(fee.total_fees) if fee else 0.0,
        "paid_amount": float(fee.paid_amount) if fee else 0.0,
        "pending_amount": float(fee.pending_amount) if fee else 0.0,
        "due_date": fee.due_date.isoformat() if fee and fee.due_date else None,
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
    }


@router.get("/payments/{payment_id}/receipt-pdf")
def student_receipt_pdf(payment_id: int, current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    pay = db.query(Payment).filter(Payment.id == payment_id, Payment.student_id == st.id).first()
    if not pay:
        raise HTTPException(status_code=404, detail="Receipt not found.")
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
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="AK_Receipt_{pay.id}.pdf"'})


# ---------------- ONLINE PRACTICE TESTS ----------------

@router.get("/tests")
def list_available_tests(current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    papers = (
        db.query(QuestionPaper)
        .filter(QuestionPaper.class_id == st.class_id, QuestionPaper.is_online_test == True, QuestionPaper.is_published == True)
        .order_by(QuestionPaper.created_at.desc())
        .all()
    )
    attempts = {
        a.question_paper_id: a
        for a in db.query(StudentTestAttempt).filter(StudentTestAttempt.student_id == st.id).order_by(StudentTestAttempt.id.desc()).all()
    }
    return [
        {
            "id": qp.id,
            "title": qp.title,
            "subject_name": qp.subject.name if qp.subject else "",
            "duration_minutes": qp.duration_minutes,
            "total_marks": float(qp.total_marks),
            "question_count": len(qp.questions),
            "instructions": qp.instructions,
            "allow_result_view": qp.allow_result_view,
            "latest_attempt": {
                "id": attempts[qp.id].id,
                "status": attempts[qp.id].status,
                "total_score": float(attempts[qp.id].total_score) if qp.allow_result_view else None,
                "max_score": float(attempts[qp.id].max_score),
                "submitted_at": attempts[qp.id].submitted_at.isoformat() if attempts[qp.id].submitted_at else None,
            }
            if qp.id in attempts
            else None,
        }
        for qp in papers
    ]


@router.post("/tests/{paper_id}/start")
def start_online_test(paper_id: int, current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    qp = db.query(QuestionPaper).filter(
        QuestionPaper.id == paper_id,
        QuestionPaper.class_id == st.class_id,
        QuestionPaper.is_online_test == True,
        QuestionPaper.is_published == True,
    ).first()
    if not qp:
        raise HTTPException(status_code=404, detail="Practice test not available for your class.")

    attempt = (
        db.query(StudentTestAttempt)
        .filter(StudentTestAttempt.question_paper_id == qp.id, StudentTestAttempt.student_id == st.id, StudentTestAttempt.status == "IN_PROGRESS")
        .first()
    )
    if not attempt:
        attempt = StudentTestAttempt(
            question_paper_id=qp.id,
            student_id=st.id,
            status="IN_PROGRESS",
            max_score=qp.total_marks,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

    # IMPORTANT: Do NOT include correct_answer, is_correct, or explanation before submission!
    return {
        "attempt_id": attempt.id,
        "paper_id": qp.id,
        "title": qp.title,
        "duration_minutes": qp.duration_minutes,
        "total_marks": float(qp.total_marks),
        "instructions": qp.instructions,
        "started_at": attempt.started_at.isoformat(),
        "questions": [
            {
                "id": q.id,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "marks": float(q.marks),
                "match_pairs": [{"left": p.get("left", "")} for p in q.match_pairs] if q.match_pairs else None,
                "match_choices": [p.get("right", "") for p in q.match_pairs] if q.match_pairs else None,
                "options": [
                    {
                        "id": opt.id,
                        "option_label": opt.option_label,
                        "option_text": opt.option_text,
                    }
                    for opt in q.options
                ],
            }
            for q in qp.questions
        ],
    }


@router.post("/tests/attempts/{attempt_id}/submit")
def submit_online_test(
    attempt_id: int,
    payload: TestAttemptSubmit,
    current_user: User = Depends(require_roles(["student"])),
    db: Session = Depends(get_db),
):
    st = _get_student(current_user, db)
    attempt = db.query(StudentTestAttempt).filter(StudentTestAttempt.id == attempt_id, StudentTestAttempt.student_id == st.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Test attempt not found.")
    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="This test attempt has already been submitted.")

    qp = attempt.question_paper
    q_map = {q.id: q for q in qp.questions}
    total_score = 0.0
    needs_teacher_eval = False

    db.query(StudentAnswer).filter(StudentAnswer.attempt_id == attempt.id).delete()
    for ans_in in payload.answers:
        q = q_map.get(ans_in.question_id)
        if not q:
            continue
        is_corr = None
        awarded = None
        if q.question_type == "MCQ" and qp.auto_evaluate_mcq:
            if ans_in.selected_option_id:
                opt = db.query(QuestionOption).filter(QuestionOption.id == ans_in.selected_option_id, QuestionOption.question_id == q.id).first()
                is_corr = bool(opt and opt.is_correct)
                awarded = float(q.marks) if is_corr else 0.0
            else:
                is_corr = False
                awarded = 0.0
            total_score += awarded
        elif q.question_type == "FILL_IN_BLANK" and q.correct_answer and qp.auto_evaluate_mcq:
            given = (ans_in.answer_text or "").strip().lower()
            expected = q.correct_answer.strip().lower()
            is_corr = given == expected
            awarded = float(q.marks) if is_corr else 0.0
            total_score += awarded
        else:
            needs_teacher_eval = True

        db.add(StudentAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            selected_option_id=ans_in.selected_option_id,
            answer_text=ans_in.answer_text,
            is_correct=is_corr,
            marks_awarded=awarded,
        ))

    attempt.submitted_at = datetime.utcnow()
    attempt.total_score = total_score
    attempt.status = "SUBMITTED" if needs_teacher_eval else "EVALUATED"
    db.commit()

    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "message": "Test submitted successfully!" + (" Subjective questions await teacher evaluation." if needs_teacher_eval else ""),
        "total_score": float(attempt.total_score) if qp.allow_result_view else None,
        "max_score": float(attempt.max_score),
    }


@router.get("/tests/attempts/{attempt_id}/result")
def view_attempt_result(attempt_id: int, current_user: User = Depends(require_roles(["student"])), db: Session = Depends(get_db)):
    st = _get_student(current_user, db)
    attempt = db.query(StudentTestAttempt).filter(StudentTestAttempt.id == attempt_id, StudentTestAttempt.student_id == st.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")
    if attempt.status == "IN_PROGRESS":
        raise HTTPException(status_code=403, detail="Cannot view results before submitting the test.")
    if attempt.status != "EVALUATED":
        raise HTTPException(status_code=403, detail="Your quiz has been submitted and is awaiting teacher review.")
    qp = attempt.question_paper
    if not qp.allow_result_view:
        raise HTTPException(status_code=403, detail="Result viewing is disabled for this test by the teacher.")

    return {
        "attempt_id": attempt.id,
        "title": qp.title,
        "status": attempt.status,
        "total_score": float(attempt.total_score),
        "max_score": float(attempt.max_score),
        "teacher_feedback": attempt.teacher_feedback,
        "answers": [
            {
                "question_text": a.question.question_text if a.question else "",
                "question_type": a.question.question_type if a.question else "",
                "max_marks": float(a.question.marks) if a.question else 0,
                "marks_awarded": float(a.marks_awarded) if a.marks_awarded is not None else None,
                "is_correct": a.is_correct,
                "answer_text": a.answer_text,
                "correct_answer": a.question.correct_answer if a.question else None,
                "explanation": a.question.explanation if a.question else None,
                "teacher_comment": a.teacher_comment,
            }
            for a in attempt.answers
        ],
    }
