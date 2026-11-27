import hashlib
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.config import (
    MSG91_AUTH_KEY,
    MSG91_SENDER_ID,
    MSG91_TEMPLATE_ID,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_WEBHOOK_URL,
)
from app.models import Notification, Parent
from app.services.helpers import get_or_create_settings


def gateway_status_summary(settings) -> dict:
    sms_live = bool(
        getattr(settings, "sms_enabled", False)
        and (
            (getattr(settings, "msg91_auth_key", None) or MSG91_AUTH_KEY)
            or (getattr(settings, "sms_webhook_url", None) or "").strip()
        )
    )
    wa_token = getattr(settings, "whatsapp_access_token", None) or WHATSAPP_ACCESS_TOKEN
    wa_phone_id = getattr(settings, "whatsapp_phone_number_id", None) or WHATSAPP_PHONE_NUMBER_ID
    wa_webhook = (getattr(settings, "whatsapp_webhook_url", None) or WHATSAPP_WEBHOOK_URL or "").strip()
    whatsapp_live = bool(
        (getattr(settings, "whatsapp_enabled", False) and wa_token and wa_phone_id)
        or wa_webhook
    )
    group_live = bool(
        (wa_webhook and (getattr(settings, "whatsapp_group_id", None) or "").strip())
        or (
            (getattr(settings, "telegram_bot_token", None) or "").strip()
            and (getattr(settings, "telegram_chat_id", None) or "").strip()
        )
    )
    return {
        "sms_live": sms_live,
        "whatsapp_live": whatsapp_live,
        "group_live": group_live,
        "auto_notify_group_on_events": bool(getattr(settings, "auto_notify_group_on_events", True)),
    }


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


def _post_json(client: Optional[httpx.Client], url: str, *, json_body: dict, headers: Optional[dict] = None) -> httpx.Response:
    if client is not None:
        return client.post(url, json=json_body, headers=headers or {}, timeout=10.0)
    return httpx.post(url, json=json_body, headers=headers or {}, timeout=10.0)


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
    http_client: Optional[httpx.Client] = None,
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
        sms_webhook = (getattr(settings, "sms_webhook_url", None) or "").strip()
        msg91_key = (getattr(settings, "msg91_auth_key", None) or MSG91_AUTH_KEY or "").strip()
        if getattr(settings, "sms_enabled", False) and sms_webhook:
            provider_val = "SMS_WEBHOOK"
            try:
                clean_phone = format_wa_digits(recipient_phone)
                resp = _post_json(
                    http_client,
                    sms_webhook,
                    json_body={
                        "phone": clean_phone,
                        "to": clean_phone,
                        "message": message,
                        "sender_id": settings.msg91_sender_id or MSG91_SENDER_ID,
                        "type": notification_type,
                    },
                )
                if 200 <= resp.status_code < 300:
                    status_val = "SENT"
                    provider_msg_id = "sms-webhook-ok"
                    sent_at = datetime.utcnow()
                else:
                    status_val = "FAILED"
                    error_detail = f"SMS Webhook HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                status_val = "FAILED"
                error_detail = f"SMS Webhook error: {exc}"
        elif getattr(settings, "sms_enabled", False) and msg91_key:
            provider_val = "MSG91"
            try:
                clean_phone = format_wa_digits(recipient_phone)
                payload = {
                    "sender": settings.msg91_sender_id or MSG91_SENDER_ID,
                    "route": "4",
                    "country": "91",
                    "sms": [{"message": message, "to": [clean_phone[-10:]]}],
                }
                tpl_id = (getattr(settings, "msg91_template_id", None) or MSG91_TEMPLATE_ID or "").strip()
                if tpl_id:
                    payload["DLT_TE_ID"] = tpl_id
                resp = _post_json(
                    http_client,
                    "https://api.msg91.com/api/v2/sendsms",
                    json_body=payload,
                    headers={"authkey": msg91_key, "Content-Type": "application/json"},
                )
                if 200 <= resp.status_code < 300:
                    status_val = "SENT"
                    provider_msg_id = "msg91-ok"
                    sent_at = datetime.utcnow()
                else:
                    status_val = "FAILED"
                    error_detail = f"MSG91 HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as exc:
                status_val = "FAILED"
                error_detail = f"MSG91 error: {exc}"
        else:
            status_val = "DISPATCH_READY"
            provider_val = "DIRECT_SMS"
            error_detail = None

    elif channel == "WHATSAPP":
        wa_token = settings.whatsapp_access_token or WHATSAPP_ACCESS_TOKEN
        wa_phone_id = settings.whatsapp_phone_number_id or WHATSAPP_PHONE_NUMBER_ID
        webhook_url = (getattr(settings, "whatsapp_webhook_url", None) or WHATSAPP_WEBHOOK_URL or "").strip()
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
                resp = _post_json(
                    http_client,
                    url,
                    headers={"Authorization": f"Bearer {wa_token}", "Content-Type": "application/json"},
                    json_body=payload,
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
        elif webhook_url:
            provider_val = "WHATSAPP_WEBHOOK"
            try:
                clean_phone = format_wa_digits(recipient_phone)
                resp = _post_json(
                    http_client,
                    webhook_url,
                    json_body={
                        "to": clean_phone,
                        "phone": clean_phone,
                        "chatId": f"{clean_phone}@c.us",
                        "body": message,
                        "message": message,
                        "type": notification_type,
                    },
                )
                if 200 <= resp.status_code < 300:
                    status_val = "SENT"
                    provider_msg_id = "webhook-ok"
                    sent_at = datetime.utcnow()
                else:
                    status_val = "FAILED"
                    error_detail = f"Webhook HTTP {resp.status_code}: {resp.text[:200]}"
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


def dispatch_group_workflow_event(
    db: Session,
    *,
    event_type: str,
    title: str,
    message: str,
    entity_id: str = "",
) -> Notification:
    """Broadcasts every automated portal workflow milestone to the configured Group & logs it in the live feed."""
    settings = get_or_create_settings(db)
    full_text = f"[{title}]\n{message}\n- {settings.tuition_name}"
    dedup_key = f"GRP_{event_type}_{entity_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    dedup_hash = _build_dedup_hash("GROUP", "GROUP", event_type, dedup_key)

    wa_webhook = (getattr(settings, "whatsapp_webhook_url", None) or WHATSAPP_WEBHOOK_URL or "").strip()
    wa_group_id = (getattr(settings, "whatsapp_group_id", None) or "").strip()
    tg_token = (getattr(settings, "telegram_bot_token", None) or "").strip()
    tg_chat_id = (getattr(settings, "telegram_chat_id", None) or "").strip()

    status_val = "LOGGED"
    provider_val = "AUTO_WORKFLOW_FEED"
    error_detail = None
    sent_at = None
    target_label = wa_group_id or tg_chat_id or "CLASS_GROUP_FEED"

    if getattr(settings, "auto_notify_group_on_events", True):
        delivered_any = False
        errors = []
        if wa_webhook and wa_group_id:
            try:
                r = httpx.post(
                    wa_webhook,
                    json={
                        "to": wa_group_id,
                        "chatId": wa_group_id,
                        "group_id": wa_group_id,
                        "body": full_text,
                        "message": full_text,
                        "event": event_type,
                        "title": title,
                    },
                    timeout=8.0,
                )
                if 200 <= r.status_code < 300:
                    delivered_any = True
                    provider_val = "WHATSAPP_GROUP_WEBHOOK"
                else:
                    errors.append(f"WA Group HTTP {r.status_code}")
            except Exception as exc:
                errors.append(f"WA Group err: {exc}")

        if tg_token and tg_chat_id:
            try:
                r = httpx.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={"chat_id": tg_chat_id, "text": full_text},
                    timeout=8.0,
                )
                if 200 <= r.status_code < 300:
                    delivered_any = True
                    provider_val = (
                        "WA_AND_TELEGRAM_GROUP"
                        if provider_val == "WHATSAPP_GROUP_WEBHOOK"
                        else "TELEGRAM_GROUP_BOT"
                    )
                else:
                    errors.append(f"Telegram HTTP {r.status_code}")
            except Exception as exc:
                errors.append(f"Telegram err: {exc}")

        if delivered_any:
            status_val = "SENT"
            sent_at = datetime.utcnow()
        elif errors:
            status_val = "FAILED"
            error_detail = "; ".join(errors)

    rec = Notification(
        recipient_phone=target_label,
        channel="GROUP",
        notification_type=event_type,
        message=full_text,
        status=status_val,
        provider=provider_val,
        error_detail=error_detail,
        dedup_hash=dedup_hash,
        sent_at=sent_at,
    )
    db.add(rec)
    db.flush()
    return rec
