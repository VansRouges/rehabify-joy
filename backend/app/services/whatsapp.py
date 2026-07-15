import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services.chat_service import process_message
from app.services.gemini import GeminiError
from app.services.patient_service import get_or_create_patient_by_phone
from app.services.session import get_redis
from app.services.storage import upload_audio
from app.services.transcription import transcribe_audio
from app.utils import normalize_phone

logger = logging.getLogger(__name__)
settings = get_settings()

DEDUP_TTL_SECONDS = 7 * 24 * 60 * 60
ACTIVE_SESSION_TTL_SECONDS = settings.session_ttl_seconds


class WhatsAppError(Exception):
    pass


def verify_signature(body: bytes, signature_header: str | None) -> bool:
    secret = settings.whatsapp_app_secret
    if not secret:
        logger.warning("WHATSAPP_APP_SECRET not set; skipping webhook signature verification")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


async def send_text_message(to_phone: str, body: str) -> None:
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise WhatsAppError("WhatsApp is not configured")

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_graph_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": normalize_phone(to_phone),
        "type": "text",
        "text": {"body": body},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json=payload,
        )

    if response.status_code != 200:
        logger.error("WhatsApp send failed %s: %s", response.status_code, response.text)
        raise WhatsAppError(f"WhatsApp API returned {response.status_code}")


async def download_media(media_id: str) -> tuple[bytes, str]:
    if not settings.whatsapp_access_token:
        raise WhatsAppError("WhatsApp is not configured")

    meta_url = (
        f"https://graph.facebook.com/{settings.whatsapp_graph_api_version}/{media_id}"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        meta_response = await client.get(meta_url, headers=headers)
        if meta_response.status_code != 200:
            raise WhatsAppError(f"Failed to fetch media metadata: {meta_response.status_code}")

        meta = meta_response.json()
        media_url = meta.get("url")
        mime_type = meta.get("mime_type", "audio/ogg")
        if not media_url:
            raise WhatsAppError("Media URL missing from Meta response")

        media_response = await client.get(media_url, headers=headers)
        if media_response.status_code != 200:
            raise WhatsAppError(f"Failed to download media: {media_response.status_code}")

        return media_response.content, mime_type


async def _is_duplicate(message_id: str) -> bool:
    client = await get_redis()
    key = f"joy:whatsapp:dedup:{message_id}"
    created = await client.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)
    return created is None


async def _get_active_session_id(patient_id: str) -> str | None:
    client = await get_redis()
    return await client.get(f"joy:whatsapp:active_session:{patient_id}")


async def _set_active_session_id(patient_id: str, session_id: str) -> None:
    client = await get_redis()
    await client.set(
        f"joy:whatsapp:active_session:{patient_id}",
        session_id,
        ex=ACTIVE_SESSION_TTL_SECONDS,
    )


def _profile_name_for_sender(contacts: list[dict[str, Any]] | None, sender: str) -> str | None:
    if not contacts:
        return None
    for contact in contacts:
        if contact.get("wa_id") == sender:
            profile = contact.get("profile") or {}
            name = profile.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


async def _handle_user_message(
    *,
    sender: str,
    message_id: str,
    message_type: str,
    text: str | None,
    media_id: str | None,
    profile_name: str | None,
) -> None:
    if await _is_duplicate(message_id):
        logger.info("Skipping duplicate WhatsApp message %s", message_id)
        return

    async with AsyncSessionLocal() as db:
        patient = await get_or_create_patient_by_phone(db, sender, profile_name)
        patient_id = str(patient.id)
        session_id = await _get_active_session_id(patient_id)

        user_text = text
        audio_url: str | None = None
        msg_type = "text"

        if message_type == "audio":
            if not media_id:
                await send_text_message(sender, "I couldn't read that voice note. Please try again.")
                return
            try:
                audio_bytes, mime_type = await download_media(media_id)
                if settings.bucket_configured:
                    try:
                        audio_url = upload_audio(audio_bytes, mime_type, patient_id)
                    except Exception:
                        logger.exception("WhatsApp voice upload failed for patient %s", patient_id)
                user_text = await transcribe_audio(audio_bytes, mime_type)
                msg_type = "voice"
            except (GeminiError, WhatsAppError) as exc:
                logger.exception("WhatsApp voice processing failed: %s", exc)
                await send_text_message(
                    sender,
                    "I couldn't process your voice note. Try again or type your message instead.",
                )
                return

        if message_type not in {"text", "audio"}:
            await send_text_message(
                sender,
                "I can help with text and voice messages about physiotherapy and recovery. What can I help you with?",
            )
            return

        if not user_text or not user_text.strip():
            await send_text_message(sender, "I didn't catch that. Please send your message again.")
            return

        try:
            result = await process_message(
                db,
                patient,
                user_text,
                session_id,
                message_type=msg_type,
                audio_url=audio_url,
                channel="whatsapp",
            )
        except Exception as exc:
            logger.exception("Joy processing failed for WhatsApp user %s: %s", sender, exc)
            await send_text_message(
                sender,
                "I'm having trouble responding right now. Please try again in a moment.",
            )
            return

        await _set_active_session_id(patient_id, result.session_id)
        await send_text_message(sender, result.reply)


async def process_webhook_payload(payload: dict[str, Any]) -> None:
    if payload.get("object") != "whatsapp_business_account":
        return

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") != "messages":
                continue

            value = change.get("value") or {}
            contacts = value.get("contacts")
            messages = value.get("messages") or []

            for message in messages:
                sender = message.get("from")
                message_id = message.get("id")
                message_type = message.get("type")
                if not sender or not message_id or not message_type:
                    continue

                profile_name = _profile_name_for_sender(contacts, sender)
                text = (message.get("text") or {}).get("body")
                media_id = (message.get("audio") or {}).get("id")

                await _handle_user_message(
                    sender=sender,
                    message_id=message_id,
                    message_type=message_type,
                    text=text,
                    media_id=media_id,
                    profile_name=profile_name,
                )

            statuses = value.get("statuses") or []
            for status in statuses:
                logger.debug("WhatsApp status update: %s", status.get("id"))
