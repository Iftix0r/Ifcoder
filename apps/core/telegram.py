"""Telegram Bot API orqali egaga bildirishnoma yuborish (tashqi kutubxonasiz).

Sozlamalar: TELEGRAM_BOT_TOKEN va TELEGRAM_CHAT_ID (.env). Bo'sh bo'lsa — hech narsa yuborilmaydi.
Xatolar logga yoziladi, lekin hech qachon so'rovni buzmaydi.
"""

import json
import logging
import threading
import uuid
from html import escape
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

log = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"
LIMIT = 4096


def is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)


def call(method: str, payload: dict | None = None, *, timeout: float = 10) -> dict:
    """Bot API'ga JSON so'rov. Xato bo'lsa {"ok": False, "description": ...} qaytaradi."""
    url = API.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    data = json.dumps(payload or {}).encode()
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        body = getattr(exc, "read", lambda: b"")()
        try:
            return json.loads(body)
        except ValueError:
            return {"ok": False, "description": str(exc)}


def send_message(text: str) -> bool:
    if not is_configured():
        return False
    result = call(
        "sendMessage",
        {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text[:LIMIT],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )
    if not result.get("ok"):
        log.warning("Telegram sendMessage xatosi: %s", result.get("description"))
    return bool(result.get("ok"))


def send_message_async(text: str) -> None:
    """Foydalanuvchi so'rovini kutdirmaslik uchun fonda yuboradi."""
    if is_configured():
        threading.Thread(target=send_message, args=(text,), daemon=True).start()


def send_document(path: Path, caption: str = "") -> bool:
    """Faylni (masalan, DB backup) multipart/form-data bilan yuboradi. Bot API limiti — 50 MB."""
    if not is_configured():
        return False
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in (
        ("chat_id", str(settings.TELEGRAM_CHAT_ID)),
        ("caption", caption[:1024]),
        ("parse_mode", "HTML"),
    ):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    body = b"".join(parts) + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    url = API.format(token=settings.TELEGRAM_BOT_TOKEN, method="sendDocument")
    request = Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urlopen(request, timeout=60) as resp:
            ok = json.loads(resp.read()).get("ok", False)
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        log.warning("Telegram sendDocument xatosi: %s", exc)
        return False
    return bool(ok)


def h(value) -> str:
    """HTML parse_mode uchun xavfsiz matn."""
    return escape(str(value or ""), quote=False)
