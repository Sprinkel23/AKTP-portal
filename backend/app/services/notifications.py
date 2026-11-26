import hashlib
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_WEBHOOK_URL,
)
from app.models import Notification, Parent
from app.services.helpers import get_or_create_settings


def format_wa_digits(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 10:
        return "91" + digits
    return digits


def build_direct_links(phone: str, message: str) -> dict:
    wa_digits = format_wa_digits(phone)
    encoded = quote(message or "")
    if not wa_digits:
        return {"whatsapp_url": None, "sms_url": None}
    return {
        "whatsapp_url": f"https://wa.me/{wa_digits}?text={encoded}",
        "sms_url": f"sms:+{wa_digits}?body={encoded}",
    }


def _build_dedup_hash(phone: str, channel: str, notification_type: str, dedup_key: str) -> str:
    raw = f"{phone}|{channel}|{notification_type}|{dedup_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def send_notification(
    db: Session,
    *,
    recipient_phone: str,
    channel: str,  # SMS or WHATSAPP
    notification_type: str,
    message: str,
    dedup_key: str,
    recipient_user_id: Optional[int] = None,
    student_id: Optional[int] = None,
    parent_id: Optional[int] = None,
) -> Notification:
    dedup_hash = _build_dedup_hash(recipient_phone, channel, notification_type, dedup_key)
    existing = db.query(Notification).filter(Notification.dedup_hash == dedup_hash).first()
    if existing:
        return existing

    if parent_id:
        parent = db.query(Parent).filter(Parent.id == parent_id).first()
        if parent:
            if channel == "SMS" and not parent.sms_consent:
                rec = Notification(
                    recipient_user_id=recipient_user_id,
                    student_id=student_id,
                    parent_id=parent_id,
                    recipient_phone=recipient_phone,
                    channel=channel,
                    notification_type=notification_type,
                    message=message,
                    status="SKIPPED_NO_CONSENT",
                    provider="NONE",
                    error_detail="Parent has opted out of SMS notifications.",
                    dedup_hash=dedup_hash,
                )
                db.add(rec)
                db.flush()
                return rec
            if channel == "WHATSAPP" and not parent.whatsapp_consent:
                rec = Notification(
                    recipient_user_id=recipient_user_id,
                    student_id=student_id,
                    parent_id=parent_id,
                    recipient_phone=recipient_phone,
                    channel=channel,
                    notification_type=notification_type,
                    message=message,
                    status="SKIPPED_NO_CONSENT",
                    provider="NONE",
                    error_detail="Parent has opted out of WhatsApp notifications.",
                    dedup_hash=dedup_hash,
                )
                db.add(rec)
                db.flush()
                return rec

    settings = get_or_create_settings(db)
    status_val = "DISPATCH_READY"
    provider_val = "DIRECT_WHATSAPP_SMS"
    provider_msg_id = None
    error_detail = None
    sent_at = None

    if channel == "SMS":
        status_val = "DISPATCH_READY"
        provider_val = "DIRECT_SMS"
        error_detail = None

    elif channel == "WHATSAPP":
        wa_token = settings.whatsapp_access_token or WHATSAPP_ACCESS_TOKEN
        wa_phone_id = settings.whatsapp_phone_number_id or WHATSAPP_PHONE_NUMBER_ID
        if settings.whatsapp_enabled and wa_token and wa_phone_id:
            provider_val = "WHATSAPP_CLOUD"
            try:
                clean_phone = format_wa_digits(recipient_phone)
                url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{wa_phone_id}/messages"
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "text",
                    "text": {"body": message},
                }
                resp = httpx.post(
                    url,
                    headers={"Authorization": f"Bearer {wa_token}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=10.0,
                )
                if 200 <= resp.status_code < 300:
                    data = resp.json() if resp.content else {}
                    msgs = data.get("messages") or []
                    if msgs and msgs[0].get("id"):
                        status_val = "SENT"
                        provider_msg_id = msgs[0]["id"]
                        sent_at = datetime.utcnow()
                    else:
                        status_val = "FAILED"
                        error_detail = f"WhatsApp Cloud response missing message id: {resp.text[:250]}"
                else:
                    status_val = "FAILED"
                    error_detail = f"WhatsApp HTTP {resp.status_code}: {resp.text[:250]}"
            except Exception as exc:
                status_val = "FAILED"
                error_detail = f"WhatsApp Cloud request failed: {exc}"
        else:
            webhook_url = WHATSAPP_WEBHOOK_URL.strip()
            if webhook_url:
                provider_val = "WHATSAPP_WEBHOOK"
                try:
                    clean_phone = format_wa_digits(recipient_phone)
                    resp = httpx.post(
                        webhook_url,
                        json={"phone": clean_phone, "message": message, "type": notification_type},
                        timeout=10.0,
                    )
                    if 200 <= resp.status_code < 300:
                        status_val = "SENT"
                        provider_msg_id = "webhook-ok"
                        sent_at = datetime.utcnow()
                    else:
                        status_val = "FAILED"
                        error_detail = f"Webhook HTTP {resp.status_code}"
                except Exception as exc:
                    status_val = "FAILED"
                    error_detail = f"Webhook error: {exc}"
            else:
                status_val = "DISPATCH_READY"
                provider_val = "DIRECT_WHATSAPP"
                error_detail = None

    rec = Notification(
        recipient_user_id=recipient_user_id,
        student_id=student_id,
        parent_id=parent_id,
        recipient_phone=recipient_phone,
        channel=channel,
        notification_type=notification_type,
        message=message,
        status=status_val,
        provider=provider_val,
        provider_message_id=provider_msg_id,
        error_detail=error_detail,
        dedup_hash=dedup_hash,
        sent_at=sent_at,
    )
    db.add(rec)
    db.flush()
    return rec
