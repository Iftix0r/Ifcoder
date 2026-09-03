"""
Userbot yordamchi funksiyalari — Telegram kontaktlar va profil rasmlarini olish.

MUHIM: Django ORM chaqiruvlari asyncio.run() TASHQARISIDA sinxron ravishda
       bajariladi, keyin konfiguratsiya ma'lumotlari async funksiyaga uzatiladi.
       Bu Django SynchronousOnlyOperation xatosini oldini oladi.

Session fayli: asosiy userbot bilan bir xil (userbot_{api_id}.session) foydalaniladi.
"""
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Sinxron yordamchi: DB'dan konfiguratsiya ma'lumotlarini olish
# (asyncio.run() dan OLDIN chaqiriladi)
# ──────────────────────────────────────────────────────────────────────
def _get_config_sync() -> Optional[Tuple[int, str, str, str]]:
    """
    UserbotConfig dan (api_id, api_hash, session_str, session_file_path) qaytaradi.
    Xatolik yoki sozlanmagan bo'lsa None qaytaradi.
    """
    try:
        from bots.models import UserbotConfig  # late import — circular import oldini olish
        config = UserbotConfig.get_solo()
        api_id_str = config.api_id.strip()
        api_hash   = config.get_api_hash().strip()
        session_str = config.get_session().strip()

        if not api_id_str or not api_hash:
            logger.warning("Userbot API ID yoki API Hash sozlanmagan.")
            return None

        try:
            api_id = int(api_id_str)
        except ValueError:
            logger.error("Userbot API ID raqam bo'lishi kerak.")
            return None

        # Asosiy userbot bilan bir xil session fayl nomidan foydalanamiz
        session_dir = Path(settings.BASE_DIR) / "vault" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        session_file = str(session_dir / f"userbot_{api_id}.session")

        return api_id, api_hash, session_str, session_file
    except Exception as e:
        logger.error(f"Userbot konfiguratsiyasini o'qishda xatolik: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────
# Async funksiyalar — ORM CHAQIRMAYDI, faqat Telegram bilan ishlaydi
# ──────────────────────────────────────────────────────────────────────
def _build_client(api_id: int, api_hash: str, session_str: str, session_file: str) -> TelegramClient:
    if session_str:
        return TelegramClient(StringSession(session_str), api_id, api_hash)
    return TelegramClient(session_file, api_id, api_hash)


async def _async_get_dialogs(api_id: int, api_hash: str, session_str: str, session_file: str) -> List[Dict[str, Any]]:
    client = _build_client(api_id, api_hash, session_str, session_file)
    media_dir = Path(settings.MEDIA_ROOT) / "clients" / "avatars"
    media_dir.mkdir(parents=True, exist_ok=True)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning("Userbot avtorizatsiya qilinmagan. Oldin run_userbot ni ishga tushiring.")
            await client.disconnect()
            return []

        dialogs_list = []
        async for dialog in client.iter_dialogs(limit=80):
            entity = dialog.entity
            if not isinstance(entity, User) or entity.is_self or entity.bot:
                continue

            first_name = entity.first_name or ""
            last_name  = entity.last_name or ""
            name       = f"{first_name} {last_name}".strip() or "Telegram Foydalanuvchisi"
            username   = entity.username or ""
            phone      = entity.phone or ""
            if phone and not phone.startswith("+"):
                phone = f"+{phone}"

            avatar_rel_path = ""
            avatar_filename = f"tg_{entity.id}.jpg"
            avatar_filepath = media_dir / avatar_filename

            if not avatar_filepath.exists():
                try:
                    photo = await client.download_profile_photo(entity, file=str(avatar_filepath))
                    if photo:
                        avatar_rel_path = f"clients/avatars/{avatar_filename}"
                except Exception as e:
                    logger.debug(f"Avatar yuklab bo'lmadi [ID {entity.id}]: {e}")
            elif avatar_filepath.stat().st_size > 0:
                avatar_rel_path = f"clients/avatars/{avatar_filename}"

            dialogs_list.append({
                "id":         str(entity.id),
                "name":       name,
                "username":   username,
                "phone":      phone,
                "avatar_url": f"{settings.MEDIA_URL}{avatar_rel_path}" if avatar_rel_path else "",
                "avatar_path": avatar_rel_path,
            })

        await client.disconnect()
        return dialogs_list

    except Exception as e:
        logger.error(f"Telegram dialoglarini olishda xatolik: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return []


async def _async_fetch_user(
    target: str,
    api_id: int, api_hash: str, session_str: str, session_file: str
) -> Optional[Dict[str, Any]]:
    client = _build_client(api_id, api_hash, session_str, session_file)
    media_dir = Path(settings.MEDIA_ROOT) / "clients" / "avatars"
    media_dir.mkdir(parents=True, exist_ok=True)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return None

        try:
            target_val: Any = int(target)
        except ValueError:
            target_val = target.lstrip("@")

        entity = await client.get_entity(target_val)
        if not isinstance(entity, User):
            await client.disconnect()
            return None

        first_name = entity.first_name or ""
        last_name  = entity.last_name or ""
        name       = f"{first_name} {last_name}".strip() or "Telegram Foydalanuvchisi"
        username   = entity.username or ""
        phone      = entity.phone or ""
        if phone and not phone.startswith("+"):
            phone = f"+{phone}"

        avatar_rel_path = ""
        avatar_filename = f"tg_{entity.id}.jpg"
        avatar_filepath = media_dir / avatar_filename

        try:
            photo = await client.download_profile_photo(entity, file=str(avatar_filepath))
            if photo:
                avatar_rel_path = f"clients/avatars/{avatar_filename}"
        except Exception as e:
            logger.debug(f"Profil rasmini yuklab bo'lmadi: {e}")

        await client.disconnect()
        return {
            "id":         str(entity.id),
            "name":       name,
            "username":   username,
            "phone":      phone,
            "avatar_url": f"{settings.MEDIA_URL}{avatar_rel_path}" if avatar_rel_path else "",
            "avatar_path": avatar_rel_path,
        }

    except Exception as e:
        logger.error(f"Telegram foydalanuvchisini olishda xatolik [{target}]: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None


# ──────────────────────────────────────────────────────────────────────
# Sinxron umumiy interfeys (Django view lari chaqiradi)
# ──────────────────────────────────────────────────────────────────────
def get_userbot_dialogs() -> List[Dict[str, Any]]:
    """Django view'dan chaqiriladigan sinxron wrapper."""
    cfg = _get_config_sync()  # ORM bu yerda — eventloop YO'Q
    if cfg is None:
        return []
    api_id, api_hash, session_str, session_file = cfg
    try:
        return asyncio.run(_async_get_dialogs(api_id, api_hash, session_str, session_file))
    except Exception as e:
        logger.error(f"get_userbot_dialogs xatolik: {e}")
        return []


def fetch_telegram_user(target: str) -> Optional[Dict[str, Any]]:
    """Django view'dan chaqiriladigan sinxron wrapper."""
    if not target:
        return None
    cfg = _get_config_sync()  # ORM bu yerda — eventloop YO'Q
    if cfg is None:
        return None
    api_id, api_hash, session_str, session_file = cfg
    try:
        return asyncio.run(_async_fetch_user(target, api_id, api_hash, session_str, session_file))
    except Exception as e:
        logger.error(f"fetch_telegram_user xatolik: {e}")
        return None
