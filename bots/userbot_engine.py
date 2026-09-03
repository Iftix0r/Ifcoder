import asyncio
import logging
from pathlib import Path
from typing import Set

from asgiref.sync import sync_to_async
from django.conf import settings
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from bots.models import UserbotConfig

logger = logging.getLogger(__name__)

# Bir marta yuborilgan foydalanuvchilar ID to'plami
replied_user_ids: Set[int] = set()


@sync_to_async
def get_userbot_config():
    return UserbotConfig.get_solo()


@sync_to_async
def save_userbot_session(config: UserbotConfig, session_str: str):
    config.set_session(session_str)
    config.save(update_fields=["encrypted_session"])


from django.db import models
from django.utils import timezone
from bots.models import TelegramMessage
from clients.models import Client


@sync_to_async
def db_save_telegram_message(
    message_id: int,
    chat_id: int,
    sender_id: int,
    sender_name: str,
    is_outgoing: bool,
    text: str,
    media_type: str = "text",
    rel_media_path: str = "",
):
    try:
        clean_sender = (sender_name or "").strip().lstrip("@")
        client_obj = Client.objects.filter(
            models.Q(telegram_id=str(chat_id)) |
            models.Q(telegram_id=str(sender_id)) |
            (models.Q(telegram__iexact=sender_name) if sender_name else models.Q(pk=0)) |
            (models.Q(telegram__iexact=f"@{clean_sender}") if clean_sender else models.Q(pk=0)) |
            (models.Q(telegram__iexact=clean_sender) if clean_sender else models.Q(pk=0))
        ).first()

        msg, created = TelegramMessage.objects.get_or_create(
            chat_id=chat_id,
            message_id=message_id,
            defaults={
                "sender_id": sender_id,
                "sender_name": sender_name,
                "is_outgoing": is_outgoing,
                "is_read": is_outgoing,
                "text": text or "",
                "media_type": media_type,
                "media_file": rel_media_path,
                "client": client_obj,
            },
        )
        if not created:
            if text and not msg.text:
                msg.text = text
            if rel_media_path and not msg.media_file:
                msg.media_file = rel_media_path
            if client_obj and not msg.client:
                msg.client = client_obj
            msg.save()
        return msg
    except Exception as e:
        logger.error(f"Xabar saqlashda DB xatolik: {e}")
        return None


@sync_to_async
def db_handle_edited_message(chat_id: int, message_id: int, new_text: str):
    try:
        msg = TelegramMessage.objects.filter(chat_id=chat_id, message_id=message_id).first()
        if msg:
            if not msg.original_text and msg.text != new_text:
                msg.original_text = msg.text
            msg.text = new_text
            msg.is_edited = True
            msg.save(update_fields=["text", "original_text", "is_edited"])
    except Exception as e:
        logger.error(f"Tahrir saqlashda DB xatolik: {e}")


@sync_to_async
def db_handle_deleted_messages(chat_id: int, message_ids: list):
    try:
        now = timezone.now()
        qs = TelegramMessage.objects.filter(message_id__in=message_ids)
        if chat_id:
            qs = qs.filter(chat_id=chat_id)
        qs.update(is_deleted=True, deleted_at=now)
    except Exception as e:
        logger.error(f"O'chirilgan xabarlarni belgilashda DB xatolik: {e}")


async def start_userbot_service():
    """
    Shaxsiy Telegram akkaunt Userbot xizmatini ishga tushiradi.
    """
    config = await get_userbot_config()

    api_id_str = config.api_id.strip()
    api_hash = config.get_api_hash().strip()
    phone_number = config.phone_number.strip()
    session_str = config.get_session().strip()

    if not api_id_str or not api_hash:
        logger.error("Userbot API ID va API Hash sozlanmagan! Admin paneldan kiriting: /panel/bots/userbot/")
        print("❌ XATOLIK: API ID va API Hash sozlanmagan. Admin paneldan kiritishingiz kerak (/panel/bots/userbot/)")
        return

    try:
        api_id = int(api_id_str)
    except ValueError:
        logger.error("API ID raqam bo'lishi kerak!")
        print("❌ XATOLIK: API ID noto'g'ri kiritilgan.")
        return

    session_dir = Path(settings.BASE_DIR) / "vault" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"userbot_{api_id}.session"

    if session_str:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
    else:
        client = TelegramClient(str(session_file), api_id, api_hash)

    print(f"🚀 Telegram Userbot ulanmoqda... ({phone_number or 'Akkaunt'})")
    await client.start(phone=phone_number if phone_number else None)

    from telethon.sessions import StringSession as _SS
    exported = _SS.save(client.session)
    if exported and exported != session_str:
        await save_userbot_session(config, exported)
        session_str = exported
        print("💾 Session ma'lumotlari DB ga saqlandi (helpers uchun).")

    me = await client.get_me()
    print(f"✅ Userbot muvaffaqiyatli ulana oldi: {me.first_name} (@{me.username or 'username_yoq'}) [ID: {me.id}]")
    print(f"🔄 24/7 Avto-javob rejimi: {'FAOL 🟢' if config.is_active else 'NOFAOL 🔴'}")

    # ── 1) YANGI XABARLAR LOGI ──────────────────────────────────────────
    @client.on(events.NewMessage)
    async def message_logger_handler(event):
        if not event.is_private:
            return

        chat_id = event.chat_id
        sender_id = event.sender_id
        sender = await event.get_sender()

        sender_name = ""
        if sender:
            first = getattr(sender, "first_name", "") or ""
            last = getattr(sender, "last_name", "") or ""
            sender_name = f"{first} {last}".strip() or getattr(sender, "username", "") or str(sender_id)

        is_outgoing = event.out or (sender_id == me.id)

        media_type = "text"
        rel_media_path = ""
        if event.photo:
            media_type = "photo"
            ext = ".jpg"
        elif event.voice:
            media_type = "voice"
            ext = ".ogg"
        elif event.video:
            media_type = "video"
            ext = ".mp4"
        elif event.document:
            media_type = "document"
            ext = ".bin"

        if media_type != "text":
            media_dir = Path(settings.MEDIA_ROOT) / "telegram_chat_media"
            media_dir.mkdir(parents=True, exist_ok=True)
            filename = f"media_{chat_id}_{event.id}{ext}"
            file_path = media_dir / filename

            if not file_path.exists():
                try:
                    downloaded = await event.download_media(file=str(file_path))
                    if downloaded:
                        rel_media_path = f"telegram_chat_media/{filename}"
                except Exception as ex:
                    logger.debug(f"Media yuklashda xatolik: {ex}")
            else:
                rel_media_path = f"telegram_chat_media/{filename}"

        await db_save_telegram_message(
            message_id=event.id,
            chat_id=chat_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_outgoing=is_outgoing,
            text=event.raw_text or "",
            media_type=media_type,
            rel_media_path=rel_media_path,
        )

        # Avto-javob rejimi
        if not is_outgoing and sender_id != me.id:
            fresh_config = await get_userbot_config()
            if fresh_config.is_active:
                if not (fresh_config.reply_once_per_user and sender_id in replied_user_ids):
                    reply_text = fresh_config.auto_reply_message.strip()
                    if reply_text:
                        try:
                            await event.reply(reply_text)
                            replied_user_ids.add(sender_id)
                            logger.info(f"Userbot avto-javob yubordi [User ID: {sender_id}]")
                        except Exception as e:
                            logger.error(f"Avto-javob yuborishda xatolik: {e}")

    # ── 2) TAHRIRLANGAN XABARLAR LOGI ────────────────────────────────────
    @client.on(events.MessageEdited)
    async def message_edit_handler(event):
        if not event.is_private:
            return
        await db_handle_edited_message(event.chat_id, event.id, event.raw_text or "")

    # ── 3) O'CHIRILGAN XABARLAR LOGI ─────────────────────────────────────
    @client.on(events.MessageDeleted)
    async def message_delete_handler(event):
        chat_id = getattr(event, "chat_id", None)
        await db_handle_deleted_messages(chat_id, event.deleted_ids or [])

    await client.run_until_disconnected()

