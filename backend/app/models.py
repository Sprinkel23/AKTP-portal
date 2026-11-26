from datetime import datetime, date
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), unique=True, nullable=False, index=True)  # admin, teacher, student, parent
    description = Column(String(255), nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True, index=True)
    phone = Column(String(24), nullable=True, index=True)
    full_name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="users")
    student_profile = relationship("Student", back_populates="user", uselist=False)
    parent_profile = relationship("Parent", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    phone = Column(String(24), nullable=False, index=True)
    code = Column(String(12), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), unique=True, nullable=False)  # e.g., 2026-2027
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SchoolClass(Base):
    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("name", "section", "academic_year_id", name="uq_class_section_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    grade_level = Column(Integer, nullable=False, index=True)  # 1..10
    name = Column(String(64), nullable=False)  # Class 1 .. Class 10
    section = Column(String(16), nullable=False, default="A")
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False, index=True)
    capacity = Column(Integer, default=40, nullable=False)
    tuition_fee = Column(Numeric(10, 2), default=12000.00, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    academic_year = relationship("AcademicYear")
    students = relationship("Student", back_populates="school_class")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    __table_args__ = (
        UniqueConstraint("class_id", "subject_id", name="uq_class_subject"),
    )

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)

    school_class = relationship("SchoolClass")
    subject = relationship("Subject")


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    teacher_code = Column(String(24), unique=True, nullable=False, index=True)
    teacher_name = Column(String(120), nullable=False, index=True)
    qualification = Column(String(120), nullable=True)
    specialization = Column(String(120), nullable=True)
    phone = Column(String(24), nullable=False)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    joining_date = Column(Date, default=date.today, nullable=False)
    photo_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="teacher_profile")
    assignments = relationship("TeacherAssignment", back_populates="teacher")


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"
    __table_args__ = (
        UniqueConstraint("teacher_id", "class_id", "subject_id", "academic_year_id", name="uq_teacher_class_subj_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False, index=True)
    is_class_teacher = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    teacher = relationship("Teacher", back_populates="assignments")
    school_class = relationship("SchoolClass")
    subject = relationship("Subject")


class TeacherAttendance(Base):
    __tablename__ = "teacher_attendance"
    __table_args__ = (
        UniqueConstraint("teacher_id", "attendance_date", name="uq_teacher_att_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(16), nullable=False)  # PRESENT, ABSENT, LEAVE
    remarks = Column(String(255), nullable=True)
    marked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    teacher = relationship("Teacher")


class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    parent_name = Column(String(120), nullable=False, index=True)
    phone = Column(String(24), nullable=False, index=True)
    email = Column(String(120), nullable=True)
    address = Column(Text, nullable=True)
    occupation = Column(String(100), nullable=True)
    sms_consent = Column(Boolean, default=True, nullable=False)
    whatsapp_consent = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="parent_profile")
    students = relationship("Student", back_populates="parent")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    student_code = Column(String(24), unique=True, nullable=False, index=True)  # AK001, AK002...
    student_name = Column(String(120), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(16), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    section = Column(String(16), nullable=False, default="A")
    address = Column(Text, nullable=True)
    student_phone = Column(String(24), nullable=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False, index=True)
    parent_name = Column(String(120), nullable=False)
    parent_phone = Column(String(24), nullable=False)
    admission_date = Column(Date, default=date.today, nullable=False)
    photo_path = Column(String(255), nullable=True)
    assigned_teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="student_profile")
    school_class = relationship("SchoolClass", back_populates="students")
    parent = relationship("Parent", back_populates="students")
    assigned_teacher = relationship("Teacher")
    enrollments = relationship("StudentEnrollment", back_populates="student", cascade="all, delete-orphan")
    fees = relationship("Fee", back_populates="student", cascade="all, delete-orphan")


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", name="uq_student_enrollment_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False, index=True)
    roll_number = Column(String(24), nullable=True)
    enrolled_date = Column(Date, default=date.today, nullable=False)
    status = Column(String(24), default="ACTIVE", nullable=False)  # ACTIVE, PROMOTED, INACTIVE

    student = relationship("Student", back_populates="enrollments")
    school_class = relationship("SchoolClass")
    academic_year = relationship("AcademicYear")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date", name="uq_attendance_student_date"),
        Index("ix_attendance_class_date", "class_id", "attendance_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    attendance_date = Column(Date, nullable=False, index=True)
    status = Column(String(16), nullable=False)  # PRESENT, ABSENT
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    marked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remarks = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student")
    school_class = relationship("SchoolClass")
    teacher = relationship("Teacher")


class Examination(Base):
    __tablename__ = "examinations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    exam_type = Column(String(32), default="UNIT_TEST", nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(24), default="SCHEDULED", nullable=False)  # SCHEDULED, COMPLETED, CANCELLED
    is_timetable_published = Column(Boolean, default=True, nullable=False)
    instructions = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    school_class = relationship("SchoolClass")
    academic_year = relationship("AcademicYear")
    exam_subjects = relationship("ExaminationSubject", back_populates="examination", cascade="all, delete-orphan")


class ExaminationSubject(Base):
    __tablename__ = "examination_subjects"
    __table_args__ = (
        UniqueConstraint("examination_id", "subject_id", name="uq_exam_subject"),
    )

    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(32), nullable=False, default="10:00 AM")
    duration_minutes = Column(Integer, nullable=False, default=90)
    max_marks = Column(Numeric(6, 2), nullable=False, default=100)
    passing_marks = Column(Numeric(6, 2), nullable=False, default=35)

    examination = relationship("Examination", back_populates="exam_subjects")
    subject = relationship("Subject")


class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id"), nullable=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    total_marks = Column(Numeric(6, 2), nullable=False, default=50)
    evaluation_scheme = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    is_online_test = Column(Boolean, default=True, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    auto_evaluate_mcq = Column(Boolean, default=True, nullable=False)
    allow_result_view = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    school_class = relationship("SchoolClass")
    subject = relationship("Subject")
    examination = relationship("Examination")
    questions = relationship("Question", back_populates="question_paper", cascade="all, delete-orphan", order_by="Question.order_index")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_paper_id = Column(Integer, ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    question_type = Column(String(32), nullable=False)
    # Supported types: MCQ, FILL_IN_BLANK, MATCH_FOLLOWING, ONE_MARK, TWO_MARK, THREE_MARK, FOUR_MARK, FIVE_MARK, SIX_PLUS_MARK
    question_text = Column(Text, nullable=False)
    marks = Column(Numeric(6, 2), nullable=False, default=1)
    order_index = Column(Integer, nullable=False, default=1)
    correct_answer = Column(Text, nullable=True)
    match_pairs = Column(JSON, nullable=True)  # e.g. [{"left": "...", "right": "..."}]
    explanation = Column(Text, nullable=True)

    question_paper = relationship("QuestionPaper", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_label = Column(String(8), nullable=False)  # A, B, C, D
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship("Question", back_populates="options")


class StudentTestAttempt(Base):
    __tablename__ = "student_test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    question_paper_id = Column(Integer, ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    status = Column(String(24), default="IN_PROGRESS", nullable=False)  # IN_PROGRESS, SUBMITTED, EVALUATED
    total_score = Column(Numeric(6, 2), default=0, nullable=False)
    max_score = Column(Numeric(6, 2), default=0, nullable=False)
    evaluated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    teacher_feedback = Column(Text, nullable=True)

    question_paper = relationship("QuestionPaper")
    student = relationship("Student")
    answers = relationship("StudentAnswer", back_populates="attempt", cascade="all, delete-orphan")


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("student_test_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    selected_option_id = Column(Integer, ForeignKey("question_options.id"), nullable=True)
    answer_text = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    marks_awarded = Column(Numeric(6, 2), nullable=True)
    teacher_comment = Column(Text, nullable=True)

    attempt = relationship("StudentTestAttempt", back_populates="answers")
    question = relationship("Question")


class Mark(Base):
    __tablename__ = "marks"
    __table_args__ = (
        UniqueConstraint("examination_subject_id", "student_id", name="uq_mark_exam_subj_student"),
    )

    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    examination_subject_id = Column(Integer, ForeignKey("examination_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    max_marks = Column(Numeric(6, 2), nullable=False)
    marks_obtained = Column(Numeric(6, 2), nullable=False)
    grade = Column(String(16), nullable=False)
    remarks = Column(String(255), nullable=True)
    status = Column(String(24), default="PENDING", nullable=False, index=True)  # DRAFT, PENDING, PUBLISHED, REJECTED
    entered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    examination = relationship("Examination")
    examination_subject = relationship("ExaminationSubject")
    student = relationship("Student")
    subject = relationship("Subject")


class ResultApproval(Base):
    __tablename__ = "result_approvals"

    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    examination_subject_id = Column(Integer, ForeignKey("examination_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submitted_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_date = Column(DateTime, nullable=True)
    status = Column(String(24), default="PENDING", nullable=False, index=True)  # PENDING, PUBLISHED, REJECTED
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    examination = relationship("Examination")
    examination_subject = relationship("ExaminationSubject")
    submitted_by = relationship("User", foreign_keys=[submitted_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])


class Fee(Base):
    __tablename__ = "fees"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", name="uq_fee_student_year"),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"), nullable=False, index=True)
    total_fees = Column(Numeric(10, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(10, 2), nullable=False, default=0)
    pending_amount = Column(Numeric(10, 2), nullable=False, default=0)
    due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = relationship("Student", back_populates="fees")
    academic_year = relationship("AcademicYear")
    payments = relationship("Payment", back_populates="fee")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    fee_id = Column(Integer, ForeignKey("fees.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_date = Column(Date, default=date.today, nullable=False, index=True)
    payment_mode = Column(String(32), nullable=False)  # CASH, UPI, BANK_TRANSFER, OTHER
    reference_number = Column(String(100), unique=True, nullable=True)
    idempotency_key = Column(String(120), unique=True, nullable=True)
    remarks = Column(String(255), nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    fee = relationship("Fee", back_populates="payments")
    student = relationship("Student")
    receipt = relationship("FeeReceipt", back_populates="payment", uselist=False)


class FeeReceipt(Base):
    __tablename__ = "fee_receipts"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    receipt_number = Column(String(48), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    pdf_path = Column(String(255), nullable=True)

    payment = relationship("Payment", back_populates="receipt")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=True, index=True)
    recipient_phone = Column(String(24), nullable=False)
    channel = Column(String(24), nullable=False)  # SMS, WHATSAPP
    notification_type = Column(String(48), nullable=False, index=True)
    message = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True)  # SENT, FAILED, DEMO_SIMULATED, SKIPPED_NO_CONSENT
    provider = Column(String(32), nullable=False)  # MSG91, WHATSAPP_CLOUD, DEMO
    provider_message_id = Column(String(128), nullable=True)
    error_detail = Column(Text, nullable=True)
    dedup_hash = Column(String(64), unique=True, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    category = Column(String(48), nullable=False, index=True)
    # EXAM_DATE, TEST_SCHEDULE, HOLIDAY, PARENT_MEETING, ADMISSION, ACADEMIC_EVENT, NOTICE, NEWS
    content = Column(Text, nullable=False)
    event_date = Column(Date, nullable=True, index=True)
    target_audience = Column(String(32), default="PUBLIC", nullable=False)  # PUBLIC, ALL, STUDENTS, PARENTS, TEACHERS
    is_published = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")


class InstitutionSetting(Base):
    __tablename__ = "institution_settings"

    id = Column(Integer, primary_key=True, index=True)
    tuition_name = Column(String(160), default="AK TUITION", nullable=False)
    tagline = Column(String(160), default="Learn • Practise • Achieve", nullable=False)
    director_name = Column(String(120), default="G. Akash, B.E.", nullable=False)
    director_designation = Column(String(120), default="Director, AK Tuition", nullable=False)
    director_signature_path = Column(String(255), nullable=True)
    logo_path = Column(String(255), nullable=True)
    phone = Column(String(48), default="+91 72042 09785", nullable=False)
    email = Column(String(120), default="akashgakash140@gmail.com", nullable=False)
    address = Column(Text, default="AK Tuition Campus, Bengaluru, Karnataka, India", nullable=False)
    academic_year_label = Column(String(32), default="2026-2027", nullable=False)
    grading_rules = Column(JSON, nullable=False)
    attendance_min_percentage = Column(Numeric(5, 2), default=75.00, nullable=False)
    exam_settings = Column(JSON, nullable=False)
    sms_provider = Column(String(32), default="MSG91", nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    msg91_auth_key = Column(String(255), nullable=True)
    msg91_sender_id = Column(String(32), default="AKTUIT", nullable=True)
    msg91_template_id = Column(String(64), nullable=True)
    whatsapp_enabled = Column(Boolean, default=False, nullable=False)
    whatsapp_phone_number_id = Column(String(64), nullable=True)
    whatsapp_access_token = Column(String(512), nullable=True)
    notification_templates = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
