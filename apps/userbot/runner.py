"""Doimiy jarayon: Telegram ulanishini ushlab turadi, xabarlarni bazaga yozadi, navbatni yuboradi.

Bitta sessiyani bir vaqtda ikki joydan ishlatmaslik uchun ulanishni faqat shu jarayon ushlaydi.
"""

import asyncio
import logging
import time

from asgiref.sync import sync_to_async as db
from telethon import errors, events
from telethon.tl.types import InputPeerUser

from . import commands, services
from .client import build_client
from .services import Item, Peer

log = logging.getLogger(__name__)

TICK = 2  # soniya: navbat va holatni tekshirish
IDLE = 5  # akkaunt ulanmagan bo'lsa
RETRY = 30  # tarmoq xatosidan keyin
RESYNC_EVERY = 15 * 60
SEND_GAP = 1.5  # ketma-ket xabarlar orasidagi pauza
PEER_FLOOD_PAUSE = 3600
DIALOG_LIMIT = 100
HISTORY_LIMIT = 50
COMMAND_LIMIT = 20
# Telegram xizmat chatlari: kirish kodlari shu yerdan keladi, ular bazaga tushmasligi shart
SERVICE_PEERS = {777000, 42777}

REVOKED = (
    errors.AuthKeyUnregisteredError,
    errors.AuthKeyDuplicatedError,
    errors.SessionRevokedError,
    errors.UserDeactivatedError,
    errors.UserDeactivatedBanError,
)
PERMANENT_SEND_ERRORS = {
    errors.UserIsBlockedError: "Foydalanuvchi sizni bloklagan.",
    errors.InputUserDeactivatedError: "Akkaunt o'chirilgan.",
}


def is_private_person(entity) -> bool:
    return not (
        getattr(entity, "bot", False)
        or getattr(entity, "is_self", False)
        or getattr(entity, "deleted", False)
        or entity.id in SERVICE_PEERS
    )


def to_peer(entity) -> Peer:
    name = " ".join(filter(None, [entity.first_name, entity.last_name]))
    return Peer(entity.id, entity.access_hash or 0, name, entity.username or "", entity.phone or "")


def to_item(message) -> Item | None:
    """Xizmat xabarlari (qo'ng'iroq, «qo'shildi») va bo'sh xabarlar o'tkazib yuboriladi."""
    if getattr(message, "action", None):
        return None
    text = message.message or ""
    if not text and message.media:
        for attr, label in (
            ("photo", "[Rasm]"),
            ("voice", "[Ovozli xabar]"),
            ("video_note", "[Video xabar]"),
            ("video", "[Video]"),
            ("sticker", "[Stiker]"),
            ("document", "[Fayl]"),
        ):
            if getattr(message, attr, None):
                text = label
                break
        else:
            text = "[Media]"
    return Item(message.id, bool(message.out), text, message.date) if text else None


class Runner:
    def __init__(self, client_factory=build_client):
        self.client_factory = client_factory
        self.client = None
        self.me = None
        self.pause_sends_until = 0.0

    async def run(self, *, once: bool = False) -> None:
        await db(services.fail_stale_sends)()
        while True:
            creds = await db(services.load_credentials)()
            delay = IDLE
            if creds is not None:
                try:
                    await self.serve(creds, once=once)
                except REVOKED as exc:
                    log.warning("Telegram sessiyasi bekor qilindi: %s", exc)
                    await db(services.mark_revoked)("Sessiya bekor qilindi. Qayta ulang.")
                except errors.FloodWaitError as exc:
                    log.warning("Telegram FloodWait: %s soniya", exc.seconds)
                    await db(services.set_error)(f"Telegram cheklovi: {exc.seconds} soniya kutilmoqda.")
                    delay = exc.seconds
                except (errors.RPCError, ConnectionError, OSError, TimeoutError) as exc:
                    log.warning("Userbot xatosi: %s", exc)
                    await db(services.set_error)(str(exc))
                    delay = RETRY
            if once:
                return
            await asyncio.sleep(delay)

    async def serve(self, creds, *, once: bool) -> None:
        client = self.client_factory(creds.api_id, creds.api_hash, creds.session)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                await db(services.mark_revoked)("Sessiya yaroqsiz. Qayta ulang.")
                return
            self.client = client
            self.me = await client.get_me()
            client.add_event_handler(self.on_message, events.NewMessage())
            await self.sync()
            next_sync = time.monotonic() + RESYNC_EVERY
            while True:
                state = await db(services.tick)()
                if state.encrypted_session != creds.encrypted_session:
                    return  # panelda uzildi yoki boshqa akkaunt ulandi
                if state.sync_requested or time.monotonic() >= next_sync:
                    await self.sync()
                    next_sync = time.monotonic() + RESYNC_EVERY
                await self.flush_outbox()
                if once:
                    return
                await asyncio.sleep(TICK)
        finally:
            self.client = None
            await client.disconnect()

    async def on_message(self, event) -> None:
        if not event.is_private:
            return
        message = event.message
        if event.chat_id == self.me.id:
            await self.run_command(message)
            return
        entity = await event.get_chat()
        item = to_item(message)
        if item and is_private_person(entity):
            await db(services.record)(to_peer(entity), [item])

    async def run_command(self, message) -> None:
        if not message.out or not message.message:
            return
        if not await db(services.claim_command)(message.id):
            return
        _, enabled = await db(services.command_state)()
        if not enabled:
            return
        try:
            reply = await db(commands.handle)(message.message)
        except Exception:  # noqa: BLE001 — buyruqdagi xato ulanishni uzmasligi kerak
            log.exception("Buyruq bajarilmadi")
            reply = "⚠ Buyruq bajarilmadi, logni tekshiring."
        if reply:
            await self.client.send_message("me", reply, parse_mode="html", reply_to=message.id)

    async def sync(self) -> None:
        """Ulanish uzilgan vaqtda kelgan xabarlar va buyruqlarni yetkazib oladi."""
        known = await db(services.known_dialogs)()
        async for dialog in self.client.iter_dialogs(limit=DIALOG_LIMIT):
            if not dialog.is_user or not is_private_person(dialog.entity):
                continue
            last_at, last_id = known.get(dialog.entity.id, (None, 0))
            if last_at and dialog.date and dialog.date <= last_at:
                continue
            history = self.client.iter_messages(dialog.entity, limit=HISTORY_LIMIT, min_id=last_id)
            items = [item async for message in history if (item := to_item(message))]
            await db(services.record)(to_peer(dialog.entity), items, unread=dialog.unread_count)
        await self.sync_commands()
        await db(services.sync_finished)()

    async def sync_commands(self) -> None:
        last_id, _ = await db(services.command_state)()
        if not last_id:
            # Birinchi ulanish: eski xabarlarni buyruq deb bajarmaymiz, faqat joriy nuqtani belgilaymiz
            async for message in self.client.iter_messages("me", limit=1):
                await db(services.claim_command)(message.id)
            return
        missed = [m async for m in self.client.iter_messages("me", limit=COMMAND_LIMIT, min_id=last_id)]
        for message in reversed(missed):
            await self.run_command(message)

    async def flush_outbox(self) -> None:
        if time.monotonic() < self.pause_sends_until:
            return
        batch = await db(services.claim_pending)()
        for index, row in enumerate(batch):
            stop = await self.send(row)
            if stop:
                for rest in batch[index + 1 :]:
                    await db(services.requeue)(rest.id)
                return
            if index + 1 < len(batch):
                await asyncio.sleep(SEND_GAP)

    async def send(self, row) -> bool:
        """True qaytarsa — Telegram cheklov qo'ydi, yuborish vaqtincha to'xtaydi."""
        peer = InputPeerUser(row.peer_id, row.access_hash)
        try:
            sent = await self.client.send_message(peer, row.text, parse_mode=None, link_preview=False)
        except errors.FloodWaitError as exc:
            self.pause_sends_until = time.monotonic() + exc.seconds
            await db(services.requeue)(row.id)
            return True
        except errors.PeerFloodError:
            # Telegram akkauntni spam deb gumon qilmoqda: bosim berish bloklanishga olib keladi
            self.pause_sends_until = time.monotonic() + PEER_FLOOD_PAUSE
            await db(services.mark_failed)(row.id, "Telegram spam cheklovi. 1 soatga yuborish to'xtatildi.")
            return True
        except REVOKED:
            await db(services.requeue)(row.id)
            raise
        except errors.RPCError as exc:
            text = next((v for k, v in PERMANENT_SEND_ERRORS.items() if isinstance(exc, k)), str(exc))
            await db(services.mark_failed)(row.id, text)
            return False
        except (ConnectionError, OSError, TimeoutError):
            await db(services.mark_failed)(row.id, "Ulanish uzildi: Telegram'da ketgan-ketmaganini tekshiring.")
            raise
        await db(services.mark_sent)(row.id, sent.id, sent.date)
        return False
