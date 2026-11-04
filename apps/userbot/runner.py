"""Doimiy jarayon: Telegram ulanishini ushlab turadi, xabarlarni bazaga yozadi, panel topshiriqlarini bajaradi.

Bitta sessiyani bir vaqtda ikki joydan ishlatmaslik uchun ulanishni faqat shu jarayon ushlaydi.
"""

import asyncio
import io
import logging
import time
from datetime import timedelta

from asgiref.sync import sync_to_async as db
from django.utils import timezone
from telethon import errors, events
from telethon.tl.types import (
    DocumentAttributeAudio,
    InputPeerUser,
    MessageMediaDocument,
    MessageMediaPhoto,
    UserStatusLastMonth,
    UserStatusLastWeek,
    UserStatusOffline,
    UserStatusOnline,
    UserStatusRecently,
)

from . import commands, services, voice
from .client import build_client
from .models import INLINE_MIMES, Outbox
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
MAX_AUTO_DOWNLOAD = 20 * 1024 * 1024
TYPING_FOR = timedelta(seconds=6)
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
KIND_LABELS = {
    "photo": "[Rasm]",
    "voice": "[Ovozli xabar]",
    "round": "[Video xabar]",
    "video": "[Video]",
    "sticker": "[Stiker]",
    "audio": "[Audio]",
    "document": "[Fayl]",
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
    photo_id = getattr(entity.photo, "photo_id", 0)  # UserProfilePhotoEmpty da yo'q
    return Peer(entity.id, entity.access_hash or 0, name, entity.username or "", entity.phone or "", photo_id)


def seen_fields(status) -> dict:
    if isinstance(status, UserStatusOnline):
        return {"seen_kind": "online", "seen_at": status.expires}
    if isinstance(status, UserStatusOffline):
        return {"seen_kind": "offline", "seen_at": status.was_online}
    if isinstance(status, UserStatusRecently):
        return {"seen_kind": "recently", "seen_at": None}
    if isinstance(status, UserStatusLastWeek):
        return {"seen_kind": "week", "seen_at": None}
    if isinstance(status, UserStatusLastMonth):
        return {"seen_kind": "month", "seen_at": None}
    return {"seen_kind": "", "seen_at": None}


def media_kind(message) -> str:
    """Havola preview'i va geolokatsiya kabilar fayl emas: bo'sh qaytadi."""
    media = message.media
    if isinstance(media, MessageMediaPhoto):
        return "photo" if media.photo else ""
    if not isinstance(media, MessageMediaDocument) or not media.document:
        return ""
    for attr, kind in (
        ("sticker", "sticker"),
        ("voice", "voice"),
        ("video_note", "round"),
        ("gif", "video"),
        ("video", "video"),
        ("audio", "audio"),
    ):
        if getattr(message, attr, None):
            return kind
    return "document"


def to_item(message) -> Item | None:
    """Xizmat xabarlari (qo'ng'iroq, «qo'shildi») va bo'sh xabarlar o'tkazib yuboriladi."""
    if getattr(message, "action", None):
        return None
    media = message.media
    kind = media_kind(message) if media else ""
    text = message.message or ""
    if not text and media:
        text = KIND_LABELS.get(kind, "[Media]")
    if not text:
        return None
    file = getattr(message, "file", None) if kind else None
    mime = "image/jpeg" if kind == "photo" else (getattr(file, "mime_type", "") or "")
    size = getattr(file, "size", 0) or 0
    # Bir marta ko'riladigan fayllar saqlanmaydi; animatsiyali stikerni brauzer ko'rsatolmaydi
    pending = bool(kind) and not getattr(media, "ttl_seconds", None) and size <= MAX_AUTO_DOWNLOAD
    if kind == "sticker" and mime not in INLINE_MIMES:
        pending = False
    return Item(
        message.id,
        bool(message.out),
        text,
        message.date,
        pending,
        kind,
        mime,
        getattr(file, "name", "") or "",
        getattr(message, "reply_to_msg_id", None),
    )


class Runner:
    def __init__(self, client_factory=build_client):
        self.client_factory = client_factory
        self.client = None
        self.me = None
        self.pause_sends_until = 0.0
        self.pause_media_until = 0.0

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
            client.add_event_handler(self.on_edit, events.MessageEdited())
            client.add_event_handler(self.on_delete, events.MessageDeleted())
            client.add_event_handler(self.on_read, events.MessageRead())
            client.add_event_handler(self.on_read, events.MessageRead(inbox=True))
            client.add_event_handler(self.on_user, events.UserUpdate())
            await db(services.tick)()
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
                await self.fetch_media()
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
            await db(services.update_state)(entity.id, typing_until=None)

    async def on_edit(self, event) -> None:
        item = to_item(event.message) if event.is_private else None
        if item:  # bazada yo'q chatlar (xizmat, bot) bu yerda ham yozilmaydi: faqat mavjud qator yangilanadi
            await db(services.apply_edit)(event.chat_id, item.tg_id, item.text)

    async def on_delete(self, event) -> None:
        if not event.chat_id:  # kanal/superguruhda chat_id bor; shaxsiy chatlarda yo'q
            await db(services.mark_deleted)(event.deleted_ids)

    async def on_read(self, event) -> None:
        if event.outbox:
            await db(services.update_state)(event.chat_id, read_outbox_id=event.max_id)
        else:
            await db(services.update_state)(event.chat_id, unread=0)  # telefonda o'qildi

    async def on_user(self, event) -> None:
        if event.status is not None:
            await db(services.update_state)(event.user_id, **seen_fields(event.status))
        elif event.typing:
            await db(services.update_state)(event.user_id, typing_until=timezone.now() + TYPING_FOR)

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
            # Birinchi sinxronlash daqiqalab cho'zilishi mumkin: panel «ishlamayapti» demasligi uchun signal beriladi
            await db(services.tick)()
            if not dialog.is_user or not is_private_person(dialog.entity):
                continue
            entity = dialog.entity
            last_at, last_id = known.get(entity.id, (None, 0))
            if not (last_at and dialog.date and dialog.date <= last_at):
                history = self.client.iter_messages(entity, limit=HISTORY_LIMIT, min_id=last_id)
                items = [item async for message in history if (item := to_item(message))]
                await db(services.record)(to_peer(entity), items, unread=dialog.unread_count)
            await db(services.update_state)(
                entity.id,
                photo_id=to_peer(entity).photo_id,
                pinned=bool(dialog.pinned),
                read_outbox_id=dialog.dialog.read_outbox_max_id,
                **seen_fields(entity.status),
            )
        await self.sync_commands()
        if await db(services.needs_reconcile)():
            await self.reconcile()
        await db(services.sync_finished)()

    async def reconcile(self) -> None:
        """Userbot to'xtagan paytda o'chirilgan/tahrirlangan xabarlarni topadi (hodisa kelmagan bo'ladi)."""
        for target in await db(services.reconcile_targets)():
            await db(services.tick)()
            peer = InputPeerUser(target.peer_id, target.access_hash)
            ids = list(target.messages)
            # Telegram o'chganlarini umuman qaytarmasligi mumkin: tartibga emas, id ga qaraladi
            found = {m.id: m for m in await self.client.get_messages(peer, ids=ids) if m}
            if not found and not await self.history_is_gone(peer, min(ids)):
                continue  # javobga ishonib bo'lmaydi: yolg'on «o'chirildi» belgisi xabarni yo'qotgandan yomon
            gone = [tg_id for tg_id in ids if tg_id not in found]
            if gone:
                await db(services.mark_deleted)(gone, notify=False)
            for tg_id, message in found.items():
                item = to_item(message)
                if item and getattr(message, "edit_date", None) and item.text != target.messages[tg_id]:
                    await db(services.apply_edit)(target.peer_id, tg_id, item.text, notify=False)
        await db(services.reconciled)()

    async def history_is_gone(self, peer, oldest_id: int) -> bool:
        latest = await self.client.get_messages(peer, limit=1)
        return not latest or latest[0].id < oldest_id

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

    async def fetch_media(self) -> None:
        """Fayllar oz-ozdan yuklanadi: xabar qabul qilish va yuborishni ushlab qolmasin."""
        if time.monotonic() < self.pause_media_until:
            return
        try:
            for row in await db(services.pending_avatars)():
                data = None
                if row.photo_id:
                    peer = InputPeerUser(row.peer_id, row.access_hash)
                    data = await self.client.download_profile_photo(peer, file=bytes)
                await db(services.save_avatar)(row.id, row.photo_id, data)
            for row in await db(services.pending_media)():
                await self.fetch_file(row)
        except errors.FloodWaitError as exc:
            self.pause_media_until = time.monotonic() + exc.seconds

    async def fetch_file(self, row) -> None:
        peer = InputPeerUser(row.peer_id, row.access_hash)
        try:
            message = await self.client.get_messages(peer, ids=row.tg_id)
            data = await self.client.download_media(message, file=bytes) if message else None
        except (*REVOKED, errors.FloodWaitError):
            raise
        except errors.RPCError as exc:
            log.warning("Fayl yuklanmadi: %s", exc)
            data = None
        if data:
            await db(services.save_media)(row.id, data)
        else:
            await db(services.skip_media)(row.id)

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
        """True qaytarsa — Telegram cheklov qo'ydi, topshiriqlar vaqtincha to'xtaydi."""
        try:
            await self.perform(row)
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
        except voice.VoiceError as exc:
            await db(services.mark_failed)(row.id, str(exc))
            return False
        except ValueError as exc:  # get_entity: bunday username yo'q
            await db(services.mark_failed)(row.id, str(exc))
            await db(services.set_error)(f"Topilmadi: {row.text}")
            return False
        except (ConnectionError, OSError, TimeoutError):
            await db(services.mark_failed)(row.id, "Ulanish uzildi: Telegram'da ketgan-ketmaganini tekshiring.")
            raise
        return False

    async def perform(self, row) -> None:
        peer = InputPeerUser(row.peer_id, row.access_hash)
        if row.kind == Outbox.Kind.SEND:
            await self.perform_send(row, peer)
        elif row.kind == Outbox.Kind.VOICE:
            await self.perform_voice(row, peer)
        elif row.kind == Outbox.Kind.EDIT:
            await self.client.edit_message(peer, row.target_id, row.text, parse_mode=None)
            await db(services.apply_edit)(row.peer_id, row.target_id, row.text, notify=False)
            await db(services.finish_job)(row.id)
        elif row.kind == Outbox.Kind.DELETE:
            await self.client.delete_messages(peer, [row.target_id], revoke=True)
            await db(services.mark_deleted)([row.target_id], by_me=True)
            await db(services.finish_job)(row.id)
        elif row.kind == Outbox.Kind.READ:
            await self.client.send_read_acknowledge(peer, max_id=row.target_id)
            await db(services.finish_job)(row.id)
        elif row.kind == Outbox.Kind.HISTORY:
            history = self.client.iter_messages(peer, limit=HISTORY_LIMIT, max_id=row.target_id)
            items = [item async for message in history if (item := to_item(message))]
            await db(services.store_history)(row.id, items)
        elif row.kind == Outbox.Kind.OPEN:
            await self.perform_open(row)

    async def perform_send(self, row, peer) -> None:
        if row.has_file:
            buffer = io.BytesIO(await db(services.read_file)(row.id))
            buffer.name = row.file_name  # Telethon nom va turni shundan oladi
            sent = await self.client.send_file(
                peer, buffer, caption=row.text, parse_mode=None, reply_to=row.reply_to_id
            )
        else:
            sent = await self.client.send_message(
                peer, row.text, parse_mode=None, link_preview=False, reply_to=row.reply_to_id
            )
        item = to_item(sent) or Item(sent.id, True, row.text, sent.date)
        item.reply_to_id = item.reply_to_id or row.reply_to_id  # qisqa javobda Telegram buni qaytarmasligi mumkin
        await db(services.mark_sent)(row.id, item)

    async def perform_voice(self, row, peer) -> None:
        speech = await voice.synthesize(row.text, row.voice or voice.DEFAULT_VOICE, row.speed or voice.DEFAULT_SPEED)
        buffer = io.BytesIO(speech.data)
        buffer.name = "voice.mp3"
        attribute = DocumentAttributeAudio(duration=speech.seconds, voice=True)
        sent = await self.client.send_file(peer, buffer, voice_note=True, attributes=[attribute])
        item = to_item(sent) or Item(sent.id, True, "[Ovozli xabar]", sent.date)
        await db(services.mark_sent)(row.id, item)

    async def perform_open(self, row) -> None:
        entity = await self.client.get_entity(row.text)
        if not hasattr(entity, "first_name") or not is_private_person(entity):
            raise ValueError("Faqat oddiy foydalanuvchi bilan suhbat ochiladi.")
        history = self.client.iter_messages(entity, limit=HISTORY_LIMIT)
        items = [item async for message in history if (item := to_item(message))]
        await db(services.record)(to_peer(entity), items, unread=0)
        await db(services.finish_job)(row.id)
