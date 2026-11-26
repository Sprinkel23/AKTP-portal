from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    identifier: str = Field(..., min_length=2)
    password: str = Field(..., min_length=3)
    portal_role: Optional[str] = None  # admin, teacher, student, parent


class ForgotPasswordRequest(BaseModel):
    identifier: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ClassCreate(BaseModel):
    grade_level: int = Field(..., ge=1, le=10)
    name: str
    section: str = "A"
    capacity: int = 40
    tuition_fee: float = 12000.0


class SubjectCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class ClassSubjectAssign(BaseModel):
    class_id: int
    subject_ids: List[int]


class StudentCreate(BaseModel):
    student_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    class_id: int
    section: str = "A"
    address: Optional[str] = None
    student_phone: Optional[str] = None
    parent_name: str
    parent_phone: str
    parent_email: Optional[str] = None
    admission_date: Optional[date] = None
    total_fees: Optional[float] = None
    assigned_teacher_id: Optional[int] = None
    student_password: Optional[str] = None
    parent_username: Optional[str] = None
    parent_password: Optional[str] = None


class StudentUpdate(BaseModel):
    student_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    class_id: Optional[int] = None
    section: Optional[str] = None
    address: Optional[str] = None
    student_phone: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    assigned_teacher_id: Optional[int] = None
    total_fees: Optional[float] = None
    is_active: Optional[bool] = None


class TeacherCreate(BaseModel):
    teacher_name: str
    username: str
    password: Optional[str] = None
    email: Optional[str] = None
    phone: str
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    address: Optional[str] = None
    joining_date: Optional[date] = None


class TeacherUpdate(BaseModel):
    teacher_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class TeacherAssignmentCreate(BaseModel):
    teacher_id: int
    class_id: int
    subject_id: int
    is_class_teacher: bool = False


class TeacherAttendanceEntry(BaseModel):
    teacher_id: int
    attendance_date: date
    status: str  # PRESENT, ABSENT, LEAVE
    remarks: Optional[str] = None


class AttendanceItem(BaseModel):
    student_id: int
    status: str  # PRESENT or ABSENT
    remarks: Optional[str] = None


class AttendanceBulkCreate(BaseModel):
    class_id: int
    attendance_date: date
    entries: List[AttendanceItem]


class PaymentCreate(BaseModel):
    student_id: int
    amount: float = Field(..., gt=0)
    payment_date: Optional[date] = None
    payment_mode: str  # CASH, UPI, BANK_TRANSFER, OTHER
    reference_number: Optional[str] = None
    idempotency_key: Optional[str] = None
    remarks: Optional[str] = None


class FeeUpdate(BaseModel):
    total_fees: float = Field(..., ge=0)
    due_date: Optional[date] = None
    notes: Optional[str] = None


class ExamSubjectItem(BaseModel):
    subject_id: int
    exam_date: date
    start_time: str = "10:00 AM"
    duration_minutes: int = 90
    max_marks: float = 100
    passing_marks: float = 35


class ExaminationCreate(BaseModel):
    name: str
    class_id: int
    exam_type: str = "UNIT_TEST"
    start_date: date
    end_date: date
    is_timetable_published: bool = True
    instructions: Optional[str] = None
    subjects: List[ExamSubjectItem] = []


class ExaminationUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    is_timetable_published: Optional[bool] = None
    instructions: Optional[str] = None
    subjects: Optional[List[ExamSubjectItem]] = None


class MarkEntryItem(BaseModel):
    student_id: int
    marks_obtained: float = Field(..., ge=0)
    remarks: Optional[str] = None


class MarksBulkEntry(BaseModel):
    examination_id: int
    examination_subject_id: int
    submit_for_approval: bool = True
    notes: Optional[str] = None
    entries: List[MarkEntryItem]


class ResultApprovalAction(BaseModel):
    action: str  # APPROVE or REJECT
    rejection_reason: Optional[str] = None
    send_notifications: bool = True


class QuestionOptionInput(BaseModel):
    option_label: str
    option_text: str
    is_correct: bool = False


class QuestionInput(BaseModel):
    question_type: str
    question_text: str
    marks: float = Field(..., gt=0)
    order_index: int = 1
    correct_answer: Optional[str] = None
    match_pairs: Optional[List[dict]] = None
    explanation: Optional[str] = None
    options: List[QuestionOptionInput] = []


class QuestionPaperCreate(BaseModel):
    title: str
    class_id: int
    subject_id: int
    examination_id: Optional[int] = None
    duration_minutes: int = 60
    total_marks: float = Field(..., gt=0)
    evaluation_scheme: Optional[str] = None
    instructions: Optional[str] = None
    is_online_test: bool = True
    is_published: bool = True
    auto_evaluate_mcq: bool = True
    allow_result_view: bool = True
    questions: List[QuestionInput]


class TestAnswerSubmit(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None
    answer_text: Optional[str] = None


class TestAttemptSubmit(BaseModel):
    answers: List[TestAnswerSubmit]


class SubjectiveEvalItem(BaseModel):
    answer_id: int
    marks_awarded: float = Field(..., ge=0)
    teacher_comment: Optional[str] = None


class AttemptEvaluationInput(BaseModel):
    evaluations: List[SubjectiveEvalItem]
    teacher_feedback: Optional[str] = None


class AnnouncementCreate(BaseModel):
    title: str
    category: str
    content: str
    event_date: Optional[date] = None
    target_audience: str = "PUBLIC"
    is_published: bool = True
    is_featured: bool = False


class NotificationDispatchRequest(BaseModel):
    notification_type: str
    channel: str  # SMS, WHATSAPP, BOTH
    student_ids: Optional[List[int]] = None
    class_id: Optional[int] = None
    message: str


class ParentConsentUpdate(BaseModel):
    sms_consent: bool
    whatsapp_consent: bool


class SettingsUpdate(BaseModel):
    tuition_name: Optional[str] = None
    tagline: Optional[str] = None
    director_name: Optional[str] = None
    director_designation: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    academic_year_label: Optional[str] = None
    grading_rules: Optional[List[dict]] = None
    attendance_min_percentage: Optional[float] = None
    exam_settings: Optional[dict] = None
    sms_provider: Optional[str] = None
    sms_enabled: Optional[bool] = None
    msg91_auth_key: Optional[str] = None
    msg91_sender_id: Optional[str] = None
    msg91_template_id: Optional[str] = None
    whatsapp_enabled: Optional[bool] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    notification_templates: Optional[dict] = None


class ContactInquiryRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    student_class: Optional[str] = None
    message: str


class TeacherOtpRequest(BaseModel):
    phone: str = Field(..., min_length=8)


class TeacherOtpVerify(BaseModel):
    phone: str = Field(..., min_length=8)
    otp_code: str = Field(..., min_length=4, max_length=10)


class ParentPhoneLoginRequest(BaseModel):
    phone: str = Field(..., min_length=8)


class TeacherStudentCreate(BaseModel):
    student_name: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    class_id: int
    section: str = "A"
    address: Optional[str] = None
    student_phone: Optional[str] = None
    parent_name: str
    parent_phone: str
    parent_email: Optional[str] = None
    student_password: Optional[str] = None
    parent_password: Optional[str] = None
