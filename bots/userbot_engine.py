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

    # Session kodi yaratilgan bo'lsa shifrlab saqlash
    if isinstance(client.session, StringSession):
        curr_str = client.session.save()
        if curr_str != session_str:
            await save_userbot_session(config, curr_str)

    me = await client.get_me()
    print(f"✅ Userbot muvaffaqiyatli ulana oldi: {me.first_name} (@{me.username or 'username_yoq'}) [ID: {me.id}]")
    print(f"🔄 24/7 Avto-javob rejimi: {'FAOL 🟢' if config.is_active else 'NOFAOL 🔴'}")

    @client.on(events.NewMessage(incoming=True, private=True))
    async def incoming_private_handler(event):
        fresh_config = await get_userbot_config()
        if not fresh_config.is_active:
            return

        sender_id = event.sender_id
        # O'zimizga o'zimiz javob qaytarmaslik uchun
        if sender_id == me.id:
            return

        # Bir marta javob berish sozlamasi yoqilgan bo'lsa
        if fresh_config.reply_once_per_user and sender_id in replied_user_ids:
            return

        reply_text = fresh_config.auto_reply_message.strip()
        if not reply_text:
            return

        try:
            await event.reply(reply_text)
            replied_user_ids.add(sender_id)
            logger.info(f"Userbot avto-javob yubordi [User ID: {sender_id}]")
            print(f"💬 Avto-javob yuborildi [User ID: {sender_id}]")
        except Exception as e:
            logger.error(f"Avto-javob yuborishda xatolik: {e}")

    await client.run_until_disconnected()
