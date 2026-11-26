from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from app.models import (
    AcademicYear,
    Announcement,
    Attendance,
    ClassSubject,
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
    StudentEnrollment,
    Subject,
    Teacher,
    TeacherAssignment,
    User,
)
from app.security import hash_password
from app.services.helpers import compute_grade, get_or_create_settings


def seed_database(db: Session):
    get_or_create_settings(db)

    if db.query(Role).count() > 0:
        return

    roles = {
        "admin": Role(name="admin", description="Administrator with full AKTP Portal control"),
        "teacher": Role(name="teacher", description="Teacher managing assigned classes, attendance, marks & tests"),
        "student": Role(name="student", description="Student accessing exams, practice tests, marks & attendance"),
        "parent": Role(name="parent", description="Parent monitoring child progress, attendance, fees & results"),
    }
    db.add_all(roles.values())
    db.flush()

    year = AcademicYear(
        name="2026-2027",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db.add(year)
    db.flush()

    # Classes 1 to 10
    classes_map = {}
    for g in range(1, 11):
        c = SchoolClass(
            grade_level=g,
            name=f"Class {g}",
            section="A",
            academic_year_id=year.id,
            capacity=40,
            tuition_fee=10000 + g * 1000,
            is_active=True,
        )
        db.add(c)
        classes_map[g] = c
    db.flush()

    # Core Subjects
    subjects_data = [
        ("Mathematics", "MATH", "Core algebra, geometry, arithmetic & problem solving"),
        ("Science", "SCI", "Integrated physics, chemistry & biology concepts"),
        ("English", "ENG", "Grammar, comprehension, literature & writing skills"),
        ("Social Studies", "SST", "History, geography, civics & economics"),
        ("Computer Science", "CS", "Coding, logical thinking & digital literacy"),
        ("Hindi", "HIN", "Language fluency, grammar & literature"),
    ]
    subjects_map = {}
    for name, code, desc in subjects_data:
        s = Subject(name=name, code=code, description=desc, is_active=True)
        db.add(s)
        subjects_map[code] = s
    db.flush()

    # Assign subjects to classes 1-10
    for g, cls_obj in classes_map.items():
        for subj in subjects_map.values():
            db.add(ClassSubject(class_id=cls_obj.id, subject_id=subj.id))
    db.flush()

    # Admin User
    admin_user = User(
        username="admin",
        email="akashgakash140@gmail.com",
        phone="+917204209785",
        full_name="G. Akash, B.E.",
        password_hash=hash_password("Admin@123"),
        role_id=roles["admin"].id,
        is_active=True,
    )
    db.add(admin_user)
    db.flush()

    # Teachers
    t1_user = User(
        username="teacher1",
        email="priya.sharma@aktuition.edu.in",
        phone="+919876500001",
        full_name="Mrs. Priya Sharma",
        password_hash=hash_password("Teacher@123"),
        role_id=roles["teacher"].id,
        is_active=True,
    )
    t2_user = User(
        username="teacher2",
        email="rahul.verma@aktuition.edu.in",
        phone="+919876500002",
        full_name="Mr. Rahul Verma",
        password_hash=hash_password("Teacher@123"),
        role_id=roles["teacher"].id,
        is_active=True,
    )
    db.add_all([t1_user, t2_user])
    db.flush()

    t1 = Teacher(
        user_id=t1_user.id,
        teacher_code="TCH001",
        teacher_name="Mrs. Priya Sharma",
        qualification="M.Sc., B.Ed.",
        specialization="Mathematics & Science",
        phone="+919876500001",
        email="priya.sharma@aktuition.edu.in",
        address="Bengaluru",
        joining_date=date(2024, 6, 1),
    )
    t2 = Teacher(
        user_id=t2_user.id,
        teacher_code="TCH002",
        teacher_name="Mr. Rahul Verma",
        qualification="M.A., MCA",
        specialization="English & Computer Science",
        phone="+919876500002",
        email="rahul.verma@aktuition.edu.in",
        address="Bengaluru",
        joining_date=date(2025, 1, 15),
    )
    db.add_all([t1, t2])
    db.flush()

    # Assign teacher1 to Class 10 & Class 9 (Math, Science) and teacher2 to Class 10 & Class 8 (English, CS)
    assignments = [
        TeacherAssignment(teacher_id=t1.id, class_id=classes_map[10].id, subject_id=subjects_map["MATH"].id, academic_year_id=year.id, is_class_teacher=True),
        TeacherAssignment(teacher_id=t1.id, class_id=classes_map[10].id, subject_id=subjects_map["SCI"].id, academic_year_id=year.id),
        TeacherAssignment(teacher_id=t1.id, class_id=classes_map[9].id, subject_id=subjects_map["MATH"].id, academic_year_id=year.id, is_class_teacher=True),
        TeacherAssignment(teacher_id=t2.id, class_id=classes_map[10].id, subject_id=subjects_map["ENG"].id, academic_year_id=year.id),
        TeacherAssignment(teacher_id=t2.id, class_id=classes_map[10].id, subject_id=subjects_map["CS"].id, academic_year_id=year.id),
        TeacherAssignment(teacher_id=t2.id, class_id=classes_map[8].id, subject_id=subjects_map["ENG"].id, academic_year_id=year.id, is_class_teacher=True),
    ]
    db.add_all(assignments)
    db.flush()

    # Parents & Students
    sample_families = [
        ("parent1", "Mr. Ramesh Kumar", "+919811111001", "ramesh.kumar@example.com", "AK001", "Aarav Kumar", date(2011, 5, 14), "Male", 10, t1.id, 15000),
        ("parent2", "Mrs. Sunita Devi", "+919811111002", "sunita.devi@example.com", "AK002", "Ananya Sharma", date(2011, 8, 22), "Female", 10, t1.id, 20000),
        ("parent3", "Mr. Vikram Rao", "+919811111003", "vikram.rao@example.com", "AK003", "Rohan Rao", date(2012, 3, 10), "Male", 9, t1.id, 10000),
        ("parent4", "Mrs. Meena Patel", "+919811111004", "meena.patel@example.com", "AK004", "Diya Patel", date(2013, 11, 4), "Female", 8, t2.id, 18000),
    ]

    students_created = []
    for p_uname, p_name, p_phone, p_email, s_code, s_name, dob, gender, grade, t_id, paid in sample_families:
        p_user = User(
            username=p_uname,
            email=p_email,
            phone=p_phone,
            full_name=p_name,
            password_hash=hash_password("Parent@123"),
            role_id=roles["parent"].id,
            is_active=True,
        )
        db.add(p_user)
        db.flush()
        parent_obj = Parent(
            user_id=p_user.id,
            parent_name=p_name,
            phone=p_phone,
            email=p_email,
            address="Bengaluru, Karnataka",
            sms_consent=True,
            whatsapp_consent=True,
        )
        db.add(parent_obj)
        db.flush()

        s_user = User(
            username=s_code,
            email=f"{s_code.lower()}@student.aktuition.edu.in",
            phone=p_phone,
            full_name=s_name,
            password_hash=hash_password("Student@123"),
            role_id=roles["student"].id,
            is_active=True,
        )
        db.add(s_user)
        db.flush()

        cls_obj = classes_map[grade]
        student_obj = Student(
            user_id=s_user.id,
            student_code=s_code,
            student_name=s_name,
            date_of_birth=dob,
            gender=gender,
            class_id=cls_obj.id,
            section="A",
            address="Bengaluru, Karnataka",
            student_phone=p_phone,
            parent_id=parent_obj.id,
            parent_name=p_name,
            parent_phone=p_phone,
            admission_date=date(2026, 4, 5),
            assigned_teacher_id=t_id,
            is_active=True,
        )
        db.add(student_obj)
        db.flush()
        students_created.append((student_obj, cls_obj, paid))

        db.add(StudentEnrollment(
            student_id=student_obj.id,
            class_id=cls_obj.id,
            academic_year_id=year.id,
            roll_number=s_code,
            enrolled_date=date(2026, 4, 5),
            status="ACTIVE",
        ))

        total_fee = float(cls_obj.tuition_fee)
        pending = max(0.0, total_fee - paid)
        fee_obj = Fee(
            student_id=student_obj.id,
            academic_year_id=year.id,
            total_fees=total_fee,
            paid_amount=paid,
            pending_amount=pending,
            due_date=date(2026, 12, 31),
        )
        db.add(fee_obj)
        db.flush()

        if paid > 0:
            pay = Payment(
                fee_id=fee_obj.id,
                student_id=student_obj.id,
                amount=paid,
                payment_date=date(2026, 6, 15),
                payment_mode="UPI",
                reference_number=f"UPI-{s_code}-2026",
                remarks="First Term Tuition Fee",
                recorded_by_user_id=admin_user.id,
            )
            db.add(pay)
            db.flush()
            db.add(FeeReceipt(payment_id=pay.id, receipt_number=f"AKR-2026-{pay.id:04d}"))

    # Sample Attendance (last 10 working days)
    today = date.today()
    for offset in range(1, 11):
        d = today - timedelta(days=offset)
        if d.weekday() == 6:
            continue
        for idx, (st, cls_obj, _) in enumerate(students_created):
            status_val = "ABSENT" if (offset in (2, 6) and idx == 0) or (offset == 4 and idx == 1) else "PRESENT"
            db.add(Attendance(
                student_id=st.id,
                class_id=cls_obj.id,
                attendance_date=d,
                status=status_val,
                teacher_id=t1.id,
                marked_by_user_id=t1_user.id,
            ))

    # Sample Examination for Class 10
    exam10 = Examination(
        name="Mid-Term Assessment 2026",
        academic_year_id=year.id,
        class_id=classes_map[10].id,
        exam_type="MIDTERM",
        start_date=today - timedelta(days=12),
        end_date=today - timedelta(days=8),
        status="COMPLETED",
        is_timetable_published=True,
        instructions="Arrive 15 minutes prior. Scientific calculators are not allowed.",
        created_by_user_id=admin_user.id,
    )
    exam10_upcoming = Examination(
        name="Pre-Board Examination 2026",
        academic_year_id=year.id,
        class_id=classes_map[10].id,
        exam_type="FINAL",
        start_date=today + timedelta(days=10),
        end_date=today + timedelta(days=16),
        status="SCHEDULED",
        is_timetable_published=True,
        instructions="Carry AK Tuition ID card and blue/black ballpoint pens.",
        created_by_user_id=admin_user.id,
    )
    db.add_all([exam10, exam10_upcoming])
    db.flush()

    ex_math = ExaminationSubject(
        examination_id=exam10.id,
        subject_id=subjects_map["MATH"].id,
        exam_date=today - timedelta(days=12),
        start_time="10:00 AM",
        duration_minutes=120,
        max_marks=100,
        passing_marks=35,
    )
    ex_sci = ExaminationSubject(
        examination_id=exam10.id,
        subject_id=subjects_map["SCI"].id,
        exam_date=today - timedelta(days=10),
        start_time="10:00 AM",
        duration_minutes=120,
        max_marks=100,
        passing_marks=35,
    )
    ex_eng = ExaminationSubject(
        examination_id=exam10.id,
        subject_id=subjects_map["ENG"].id,
        exam_date=today - timedelta(days=8),
        start_time="10:00 AM",
        duration_minutes=90,
        max_marks=100,
        passing_marks=35,
    )
    ex_up_math = ExaminationSubject(
        examination_id=exam10_upcoming.id,
        subject_id=subjects_map["MATH"].id,
        exam_date=today + timedelta(days=10),
        start_time="09:30 AM",
        duration_minutes=180,
        max_marks=100,
        passing_marks=35,
    )
    ex_up_sci = ExaminationSubject(
        examination_id=exam10_upcoming.id,
        subject_id=subjects_map["SCI"].id,
        exam_date=today + timedelta(days=12),
        start_time="09:30 AM",
        duration_minutes=180,
        max_marks=100,
        passing_marks=35,
    )
    db.add_all([ex_math, ex_sci, ex_eng, ex_up_math, ex_up_sci])
    db.flush()

    # Published Marks for Math & English (Class 10), Pending Marks for Science (to test Admin Approval!)
    class10_students = [st for st, cls_obj, _ in students_created if cls_obj.grade_level == 10]
    for st, score_math, score_eng, score_sci in zip(class10_students, [94, 88], [89, 92], [91, 85]):
        g_m, rem_m = compute_grade(score_math)
        db.add(Mark(
            examination_id=exam10.id,
            examination_subject_id=ex_math.id,
            student_id=st.id,
            subject_id=subjects_map["MATH"].id,
            max_marks=100,
            marks_obtained=score_math,
            grade=g_m,
            remarks=rem_m,
            status="PUBLISHED",
            entered_by_user_id=t1_user.id,
            submitted_at=datetime.utcnow() - timedelta(days=5),
        ))
        g_e, rem_e = compute_grade(score_eng)
        db.add(Mark(
            examination_id=exam10.id,
            examination_subject_id=ex_eng.id,
            student_id=st.id,
            subject_id=subjects_map["ENG"].id,
            max_marks=100,
            marks_obtained=score_eng,
            grade=g_e,
            remarks=rem_e,
            status="PUBLISHED",
            entered_by_user_id=t2_user.id,
            submitted_at=datetime.utcnow() - timedelta(days=4),
        ))
        g_s, rem_s = compute_grade(score_sci)
        db.add(Mark(
            examination_id=exam10.id,
            examination_subject_id=ex_sci.id,
            student_id=st.id,
            subject_id=subjects_map["SCI"].id,
            max_marks=100,
            marks_obtained=score_sci,
            grade=g_s,
            remarks=rem_s,
            status="PENDING",
            entered_by_user_id=t1_user.id,
            submitted_at=datetime.utcnow() - timedelta(hours=6),
        ))

    db.add_all([
        ResultApproval(
            examination_id=exam10.id,
            examination_subject_id=ex_math.id,
            submitted_by_user_id=t1_user.id,
            submitted_date=datetime.utcnow() - timedelta(days=5),
            approved_by_user_id=admin_user.id,
            approval_date=datetime.utcnow() - timedelta(days=4),
            status="PUBLISHED",
            notes="Verified and approved by Director",
        ),
        ResultApproval(
            examination_id=exam10.id,
            examination_subject_id=ex_eng.id,
            submitted_by_user_id=t2_user.id,
            submitted_date=datetime.utcnow() - timedelta(days=4),
            approved_by_user_id=admin_user.id,
            approval_date=datetime.utcnow() - timedelta(days=3),
            status="PUBLISHED",
            notes="Approved for release",
        ),
        ResultApproval(
            examination_id=exam10.id,
            examination_subject_id=ex_sci.id,
            submitted_by_user_id=t1_user.id,
            submitted_date=datetime.utcnow() - timedelta(hours=6),
            status="PENDING",
            notes="Science mid-term marks submitted for Director review",
        ),
    ])

    # Sample Online Practice Test (Class 10 Mathematics)
    qp = QuestionPaper(
        title="Class 10 Quadratic Equations & Trigonometry Practice Test",
        class_id=classes_map[10].id,
        subject_id=subjects_map["MATH"].id,
        teacher_id=t1.id,
        created_by_user_id=t1_user.id,
        duration_minutes=30,
        total_marks=10,
        evaluation_scheme="MCQs auto-graded (2 marks each); 4-mark descriptive evaluated by teacher.",
        instructions="Read every question carefully. Do not refresh the browser during the test.",
        is_online_test=True,
        is_published=True,
        auto_evaluate_mcq=True,
        allow_result_view=True,
    )
    db.add(qp)
    db.flush()

    q1 = Question(
        question_paper_id=qp.id,
        question_type="MCQ",
        question_text="What is the discriminant of the quadratic equation 2x^2 - 4x + 3 = 0?",
        marks=2,
        order_index=1,
        correct_answer="B",
        explanation="D = b^2 - 4ac = (-4)^2 - 4(2)(3) = 16 - 24 = -8",
    )
    q2 = Question(
        question_paper_id=qp.id,
        question_type="MCQ",
        question_text="If sin(A) = 1/2, where A is an acute angle, what is the value of cos(A)?",
        marks=2,
        order_index=2,
        correct_answer="C",
        explanation="A = 30 degrees, so cos(30) = sqrt(3)/2",
    )
    q3 = Question(
        question_paper_id=qp.id,
        question_type="FILL_IN_BLANK",
        question_text="The sum of the roots of x^2 - 7x + 10 = 0 is ____.",
        marks=2,
        order_index=3,
        correct_answer="7",
    )
    q4 = Question(
        question_paper_id=qp.id,
        question_type="FOUR_MARK",
        question_text="Solve the quadratic equation x^2 - 5x + 6 = 0 by factorization and verify the roots.",
        marks=4,
        order_index=4,
    )
    db.add_all([q1, q2, q3, q4])
    db.flush()

    db.add_all([
        QuestionOption(question_id=q1.id, option_label="A", option_text="8", is_correct=False),
        QuestionOption(question_id=q1.id, option_label="B", option_text="-8", is_correct=True),
        QuestionOption(question_id=q1.id, option_label="C", option_text="16", is_correct=False),
        QuestionOption(question_id=q1.id, option_label="D", option_text="0", is_correct=False),
        QuestionOption(question_id=q2.id, option_label="A", option_text="1/2", is_correct=False),
        QuestionOption(question_id=q2.id, option_label="B", option_text="1", is_correct=False),
        QuestionOption(question_id=q2.id, option_label="C", option_text="sqrt(3)/2", is_correct=True),
        QuestionOption(question_id=q2.id, option_label="D", option_text="0", is_correct=False),
    ])

    # Public Announcements, News & Events
    announcements = [
        Announcement(
            title="Pre-Board Examination 2026 Timetable Released",
            category="EXAM_DATE",
            content="Class 10 Pre-Board Examinations will commence next month. Students and parents can download the official timetable PDF from their portals.",
            event_date=today + timedelta(days=10),
            target_audience="PUBLIC",
            is_published=True,
            is_featured=True,
            created_by_user_id=admin_user.id,
        ),
        Announcement(
            title="Parent–Teacher Academic Review Meeting",
            category="PARENT_MEETING",
            content="Parents of Classes 1 to 10 are invited to meet subject faculty and Director Mr. Akash, B.E. between 10:00 AM and 1:30 PM this Saturday.",
            event_date=today + timedelta(days=5),
            target_audience="PUBLIC",
            is_published=True,
            is_featured=True,
            created_by_user_id=admin_user.id,
        ),
        Announcement(
            title="Admissions Open for New Academic Batch (Classes 1–10)",
            category="ADMISSION",
            content="Registrations are open for Mathematics, Science, English, and Computer Science foundation batches with personalized mentorship.",
            event_date=today + timedelta(days=14),
            target_audience="PUBLIC",
            is_published=True,
            is_featured=True,
            created_by_user_id=admin_user.id,
        ),
        Announcement(
            title="Weekly Mathematics & Science Olympiad Workshop",
            category="ACADEMIC_EVENT",
            content="Special problem-solving clinic for Classes 8–10 focusing on Olympiad and Board excellence.",
            event_date=today + timedelta(days=7),
            target_audience="PUBLIC",
            is_published=True,
            is_featured=False,
            created_by_user_id=admin_user.id,
        ),
        Announcement(
            title="98% Distinction Rate in Annual Assessment",
            category="NEWS",
            content="AK Tuition celebrates outstanding academic results across Classes 1–10 under dedicated conceptual coaching.",
            event_date=today - timedelta(days=3),
            target_audience="PUBLIC",
            is_published=True,
            is_featured=False,
            created_by_user_id=admin_user.id,
        ),
    ]
    db.add_all(announcements)
    db.commit()
