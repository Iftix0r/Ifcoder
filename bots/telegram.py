import json
import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Union

from django.conf import settings

logger = logging.getLogger(__name__)


def get_telegram_config():
    """Telegram Bot token va Admin Chat ID ni sozlamalar yoki muhit o'zgaruvchilaridan oladi."""
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    admin_chat_id = getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "") or os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
    return token.strip(), admin_chat_id.strip()


def send_telegram_message(
    text: str,
    chat_id: Optional[Union[str, int]] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
    reply_markup: Optional[dict] = None,
) -> bool:
    """
    Telegram Adminga yoki ko'rsatilgan chat_id ga xabar yuboradi.
    """
    token, default_chat_id = get_telegram_config()
    target_chat_id = str(chat_id or default_chat_id).strip()

    if not token or not target_chat_id:
        logger.warning("Telegram Bot Token yoki Admin Chat ID sozlanmagan.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            return res_data.get("ok", False)
    except Exception as e:
        logger.error(f"Telegram xabar yuborishda xatolik: {e}")
        return False


def send_telegram_document(
    file_path: Union[str, Path],
    caption: Optional[str] = None,
    chat_id: Optional[Union[str, int]] = None,
) -> bool:
    """
    Telegram orqali fayl (masalan DB zaxira nusxasi) yuboradi.
    """
    token, default_chat_id = get_telegram_config()
    target_chat_id = str(chat_id or default_chat_id).strip()

    if not token or not target_chat_id:
        logger.warning("Telegram Bot Token yoki Admin Chat ID sozlanmagan.")
        return False

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        logger.error(f"Telegram document yuborish uchun fayl topilmadi: {file_path}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendDocument"

    try:
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = []

        # chat_id field
        body.append(f"--{boundary}".encode("utf-8"))
        body.append('Content-Disposition: form-data; name="chat_id"'.encode("utf-8"))
        body.append(b"")
        body.append(str(target_chat_id).encode("utf-8"))

        # caption field (if exists)
        if caption:
            body.append(f"--{boundary}".encode("utf-8"))
            body.append('Content-Disposition: form-data; name="caption"'.encode("utf-8"))
            body.append(b"")
            body.append(caption.encode("utf-8"))

        # document field
        filename = path.name
        with open(path, "rb") as f:
            file_bytes = f.read()

        body.append(f"--{boundary}".encode("utf-8"))
        body.append(
            f'Content-Disposition: form-data; name="document"; filename="{filename}"'.encode("utf-8")
        )
        body.append("Content-Type: application/octet-stream".encode("utf-8"))
        body.append(b"")
        body.append(file_bytes)

        body.append(f"--{boundary}--".encode("utf-8"))
        body.append(b"")

        payload_bytes = b"\r\n".join(body)

        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode("utf-8")
            res_data = json.loads(res_body)
            return res_data.get("ok", False)
    except Exception as e:
        logger.error(f"Telegram fayl yuborishda xatolik: {e}")
        return False
