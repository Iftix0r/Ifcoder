import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User

from bots.models import UserbotConfig

logger = logging.getLogger(__name__)


async def _get_telegram_dialogs() -> List[Dict[str, Any]]:
    config = UserbotConfig.get_solo()
    api_id_str = config.api_id.strip()
    api_hash = config.get_api_hash().strip()
    session_str = config.get_session().strip()

    if not api_id_str or not api_hash:
        return []

    try:
        api_id = int(api_id_str)
    except ValueError:
        return []

    session_dir = Path(settings.BASE_DIR) / "vault" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"userbot_helper_{api_id}.session"

    if session_str:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
    else:
        client = TelegramClient(str(session_file), api_id, api_hash)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return []

        dialogs_list = []
        media_dir = Path(settings.MEDIA_ROOT) / "clients" / "avatars"
        media_dir.mkdir(parents=True, exist_ok=True)

        async for dialog in client.iter_dialogs(limit=50):
            entity = dialog.entity
            if isinstance(entity, User) and not entity.is_self and not entity.bot:
                first_name = entity.first_name or ""
                last_name = entity.last_name or ""
                name = f"{first_name} {last_name}".strip() or "Telegram Foydalanuvchisi"
                username = entity.username or ""
                phone = entity.phone or ""
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
                        logger.warning(f"Avatar yuklashda xatolik User ID {entity.id}: {e}")
                else:
                    avatar_rel_path = f"clients/avatars/{avatar_filename}"

                dialogs_list.append({
                    "id": str(entity.id),
                    "name": name,
                    "username": username,
                    "phone": phone,
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


async def _fetch_telegram_user(target: str) -> Optional[Dict[str, Any]]:
    config = UserbotConfig.get_solo()
    api_id_str = config.api_id.strip()
    api_hash = config.get_api_hash().strip()
    session_str = config.get_session().strip()

    if not api_id_str or not api_hash or not target:
        return None

    try:
        api_id = int(api_id_str)
    except ValueError:
        return None

    session_dir = Path(settings.BASE_DIR) / "vault" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"userbot_helper_{api_id}.session"

    if session_str:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
    else:
        client = TelegramClient(str(session_file), api_id, api_hash)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return None

        try:
            target_val = int(target)
        except ValueError:
            target_val = target

        entity = await client.get_entity(target_val)
        if isinstance(entity, User):
            first_name = entity.first_name or ""
            last_name = entity.last_name or ""
            name = f"{first_name} {last_name}".strip() or "Telegram Foydalanuvchisi"
            username = entity.username or ""
            phone = entity.phone or ""
            if phone and not phone.startswith("+"):
                phone = f"+{phone}"

            media_dir = Path(settings.MEDIA_ROOT) / "clients" / "avatars"
            media_dir.mkdir(parents=True, exist_ok=True)

            avatar_filename = f"tg_{entity.id}.jpg"
            avatar_filepath = media_dir / avatar_filename
            avatar_rel_path = ""

            try:
                photo = await client.download_profile_photo(entity, file=str(avatar_filepath))
                if photo:
                    avatar_rel_path = f"clients/avatars/{avatar_filename}"
            except Exception as e:
                logger.warning(f"Profil rasmini yuklashda xatolik: {e}")

            res = {
                "id": str(entity.id),
                "name": name,
                "username": username,
                "phone": phone,
                "avatar_url": f"{settings.MEDIA_URL}{avatar_rel_path}" if avatar_rel_path else "",
                "avatar_path": avatar_rel_path,
            }
            await client.disconnect()
            return res

        await client.disconnect()
        return None
    except Exception as e:
        logger.error(f"Telegram foydalanuvchisini olishda xatolik [{target}]: {e}")
        try:
            await client.disconnect()
        except Exception:
            pass
        return None


def get_userbot_dialogs() -> List[Dict[str, Any]]:
    try:
        return asyncio.run(_get_telegram_dialogs())
    except Exception as e:
        logger.error(f"get_userbot_dialogs sync wrapper error: {e}")
        return []


def fetch_telegram_user(target: str) -> Optional[Dict[str, Any]]:
    try:
        return asyncio.run(_fetch_telegram_user(target))
    except Exception as e:
        logger.error(f"fetch_telegram_user sync wrapper error: {e}")
        return None
