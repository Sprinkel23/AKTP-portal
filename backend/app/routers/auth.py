import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OtpCode, Parent, PasswordResetToken, Student, Teacher, User
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ParentPhoneLoginRequest,
    ResetPasswordRequest,
    TeacherOtpRequest,
    TeacherOtpVerify,
)
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    log_audit,
    verify_password,
)
from app.services.notifications import send_notification

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ident = payload.identifier.strip()
    user = (
        db.query(User)
        .filter(
            (func.lower(User.username) == ident.lower())
            | (func.lower(User.email) == ident.lower())
        )
        .first()
    )
    if not user:
        student = db.query(Student).filter(func.lower(Student.student_code) == ident.lower()).first()
        if student:
            user = student.user
    if not user:
        digits = "".join(ch for ch in ident if ch.isdigit())
        if len(digits) >= 10:
            tail10 = digits[-10:]
            parent = db.query(Parent).filter(Parent.phone.endswith(tail10)).first()
            if parent:
                user = parent.user
            else:
                user = db.query(User).filter(User.phone.endswith(tail10)).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Please contact the administrator.")

    role_name = user.role.name if user.role else ""
    if payload.portal_role and payload.portal_role.lower() != role_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This account belongs to the '{role_name}' portal. Please use the {role_name.title()} Login tab.",
        )

    user.last_login_at = datetime.utcnow()
    token = create_access_token(user.id, role_name, user.username)
    log_audit(db, user.id, "LOGIN", "user", str(user.id), {"role": role_name}, request)
    db.commit()

    profile_extra = {}
    if role_name == "student" and user.student_profile:
        st = user.student_profile
        profile_extra = {
            "student_id": st.id,
            "student_code": st.student_code,
            "class_name": f"{st.school_class.name} ({st.section})" if st.school_class else "",
        }
    elif role_name == "teacher" and user.teacher_profile:
        tc = user.teacher_profile
        profile_extra = {"teacher_id": tc.id, "teacher_code": tc.teacher_code}
    elif role_name == "parent" and user.parent_profile:
        pr = user.parent_profile
        profile_extra = {
            "parent_id": pr.id,
            "children_count": len(pr.students),
        }

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": role_name,
            **profile_extra,
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    role_name = current_user.role.name if current_user.role else ""
    extra = {}
    if role_name == "student" and current_user.student_profile:
        st = current_user.student_profile
        extra = {"student_id": st.id, "student_code": st.student_code, "photo_path": st.photo_path}
    elif role_name == "teacher" and current_user.teacher_profile:
        extra = {"teacher_id": current_user.teacher_profile.id, "teacher_code": current_user.teacher_profile.teacher_code}
    elif role_name == "parent" and current_user.parent_profile:
        extra = {"parent_id": current_user.parent_profile.id}
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": role_name,
        "is_active": current_user.is_active,
        **extra,
    }


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    ident = payload.identifier.strip().lower()
    user = (
        db.query(User)
        .filter((func.lower(User.username) == ident) | (func.lower(User.email) == ident))
        .first()
    )
    if not user:
        st = db.query(Student).filter(func.lower(Student.student_code) == ident).first()
        if st:
            user = st.user
    if not user:
        raise HTTPException(status_code=404, detail="No matching account found.")

    token = secrets.token_urlsafe(24)
    reset_entry = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db.add(reset_entry)
    log_audit(db, user.id, "FORGOT_PASSWORD_REQUEST", "user", str(user.id))
    db.commit()

    return {
        "message": "Password reset token generated (valid for 30 minutes). Enter this token on the Reset Password form.",
        "reset_token": token,
        "username": user.username,
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == payload.token.strip(), PasswordResetToken.used == False)
        .first()
    )
    if not token_row or token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired.")

    user = db.query(User).filter(User.id == token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = hash_password(payload.new_password)
    token_row.used = True
    log_audit(db, user.id, "PASSWORD_RESET", "user", str(user.id))
    db.commit()
    return {"message": "Password has been reset successfully. You can now log in."}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current_user.password_hash = hash_password(payload.new_password)
    log_audit(db, current_user.id, "PASSWORD_CHANGE", "user", str(current_user.id))
    db.commit()
    return {"message": "Password updated successfully."}


@router.post("/teacher/request-otp")
def teacher_request_otp(payload: TeacherOtpRequest, request: Request, db: Session = Depends(get_db)):
    digits = "".join(ch for ch in payload.phone if ch.isdigit())
    if len(digits) < 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit registered mobile number.")
    tail10 = digits[-10:]
    teacher = db.query(Teacher).filter(Teacher.phone.endswith(tail10)).first()
    if not teacher or not teacher.user:
        raise HTTPException(status_code=404, detail="No teacher account registered with this mobile number.")
    if not teacher.is_active or not teacher.user.is_active:
        raise HTTPException(status_code=403, detail="Teacher account is deactivated. Contact the administrator.")

    otp = f"{secrets.randbelow(900000) + 100000}"
    db.query(OtpCode).filter(OtpCode.user_id == teacher.user_id, OtpCode.used == False).update({"used": True})
    db.add(OtpCode(
        user_id=teacher.user_id,
        phone=teacher.phone,
        code=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    ))
    notif = send_notification(
        db,
        recipient_phone=teacher.phone,
        channel="SMS",
        notification_type="TEACHER_OTP",
        message=f"Your AK Tuition Teacher Portal OTP is {otp}. Valid for 10 minutes. – AK Tuition",
        dedup_key=f"OTP_{teacher.user_id}_{datetime.utcnow().isoformat()}",
        recipient_user_id=teacher.user_id,
    )
    log_audit(db, teacher.user_id, "TEACHER_OTP_REQUEST", "teacher", teacher.teacher_code, {"delivery": notif.status}, request)
    db.commit()

    resp = {
        "message": "OTP sent to your registered mobile number." if notif.status == "SENT" else "DEMONSTRATION MODE: SMS gateway not configured — use the OTP displayed below to verify.",
        "delivery_status": notif.status,
        "teacher_name": teacher.teacher_name,
    }
    if notif.status != "SENT":
        resp["demo_otp"] = otp
    return resp


@router.post("/teacher/verify-otp")
def teacher_verify_otp(payload: TeacherOtpVerify, request: Request, db: Session = Depends(get_db)):
    digits = "".join(ch for ch in payload.phone if ch.isdigit())
    if len(digits) < 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number.")
    tail10 = digits[-10:]
    teacher = db.query(Teacher).filter(Teacher.phone.endswith(tail10)).first()
    if not teacher or not teacher.user:
        raise HTTPException(status_code=404, detail="Teacher account not found.")
    if not teacher.is_active or not teacher.user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    otp_row = (
        db.query(OtpCode)
        .filter(OtpCode.user_id == teacher.user_id, OtpCode.code == payload.otp_code.strip(), OtpCode.used == False)
        .order_by(OtpCode.id.desc())
        .first()
    )
    if not otp_row or otp_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired OTP code.")

    otp_row.used = True
    teacher.user.last_login_at = datetime.utcnow()
    token = create_access_token(teacher.user.id, "teacher", teacher.user.username)
    log_audit(db, teacher.user_id, "LOGIN_OTP", "teacher", teacher.teacher_code, None, request)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": teacher.user.id,
            "username": teacher.user.username,
            "full_name": teacher.user.full_name,
            "email": teacher.user.email,
            "phone": teacher.user.phone,
            "role": "teacher",
            "teacher_id": teacher.id,
            "teacher_code": teacher.teacher_code,
        },
    }


@router.post("/parent/phone-login")
def parent_phone_only_login(payload: ParentPhoneLoginRequest, request: Request, db: Session = Depends(get_db)):
    digits = "".join(ch for ch in payload.phone if ch.isdigit())
    if len(digits) < 10:
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit registered parent phone number.")
    tail10 = digits[-10:]
    parent = db.query(Parent).filter(Parent.phone.endswith(tail10)).first()
    if not parent or not parent.user:
        raise HTTPException(status_code=404, detail="No parent account found for this registered phone number.")
    if not parent.is_active or not parent.user.is_active:
        raise HTTPException(status_code=403, detail="Parent account is deactivated. Contact the administrator.")

    parent.user.last_login_at = datetime.utcnow()
    token = create_access_token(parent.user.id, "parent", parent.user.username)
    log_audit(db, parent.user.id, "LOGIN_PARENT_PHONE", "parent", str(parent.id), {"phone_tail": tail10}, request)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": parent.user.id,
            "username": parent.user.username,
            "full_name": parent.user.full_name,
            "email": parent.user.email,
            "phone": parent.user.phone,
            "role": "parent",
            "parent_id": parent.id,
            "children_count": len(parent.students),
        },
    }
