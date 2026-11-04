"""Userbot holati va suhbatlar nusxasi ustidagi sinxron amallar (panel ham, runner ham shularni ishlatadi)."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from django.db import close_old_connections, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.core.telegram import h, send_message
from apps.crm.models import Activity, Contact

from .models import Account, Dialog, Message, MessageEdit, Outbox

HEARTBEAT_EVERY = 30  # soniya
PENDING_BATCH = 5
MEDIA_BATCH = 3
NOTIFY_LINES = 5
RECONCILE_EVERY = 15 * 60  # soniya
RECONCILE_DAYS = 7
RECONCILE_DIALOGS = 20
RECONCILE_MESSAGES = 50


@dataclass
class Peer:
    id: int
    access_hash: int
    name: str = ""
    username: str = ""
    phone: str = ""
    photo_id: int = 0


@dataclass
class Item:
    tg_id: int
    outgoing: bool
    text: str
    date: datetime
    media_pending: bool = False
    media_kind: str = ""
    mime: str = ""
    file_name: str = ""
    reply_to_id: int | None = None


@dataclass
class Credentials:
    api_id: int
    api_hash: str
    session: str
    encrypted_session: str


@dataclass
class Tick:
    encrypted_session: str
    sync_requested: bool


@dataclass
class Job:
    id: int
    kind: str
    peer_id: int
    access_hash: int
    text: str
    target_id: int | None
    reply_to_id: int | None
    file_name: str
    has_file: bool
    voice: str = ""
    speed: str = ""


@dataclass
class ReconcileTarget:
    peer_id: int
    access_hash: int
    messages: dict[int, str]


@dataclass
class PendingAvatar:
    id: int
    peer_id: int
    access_hash: int
    photo_id: int


@dataclass
class PendingMedia:
    id: int
    peer_id: int
    access_hash: int
    tg_id: int


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def find_contact(peer: Peer) -> Contact | None:
    """CRM'dagi mijozni @username yoki telefonning oxirgi 9 raqami bo'yicha topadi."""
    if peer.username:
        handle = peer.username.lower()
        for contact in Contact.objects.exclude(telegram=""):
            if contact.telegram.strip().lstrip("@").lower() == handle:
                return contact
    phone = _digits(peer.phone)[-9:]
    if len(phone) == 9:
        for contact in Contact.objects.exclude(phone=""):
            if _digits(contact.phone)[-9:] == phone:
                return contact
    return None


def _log_activity(contact: Contact, item: Item) -> None:
    """Bugungi birinchi kelgan xabar tarixga yoziladi — har bir xabar bilan tarixni to'ldirib yubormaymiz."""
    today = timezone.localdate()
    if timezone.localdate(item.date) != today:
        return
    already = contact.activities.filter(
        kind=Activity.Kind.MESSAGE, text__startswith="Telegram:", created_at__date=today
    ).exists()
    if not already:
        Activity.objects.create(contact=contact, kind=Activity.Kind.MESSAGE, text=f"Telegram: {item.text[:200]}")


@transaction.atomic
def record(peer: Peer, items: list[Item], *, unread: int | None = None) -> Dialog:
    """Suhbatni yangilaydi va yangi xabarlarni yozadi (takroriy chaqiruv xavfsiz).

    ``unread`` — Telegram bergan son (sinxronlashda); ``None`` bo'lsa yangi kelganlar qo'shib boriladi.
    """
    dialog, _ = Dialog.objects.get_or_create(peer_id=peer.id)
    dialog.access_hash = peer.access_hash or dialog.access_hash
    dialog.name, dialog.username, dialog.phone = peer.name[:200], peer.username[:100], peer.phone[:20]
    dialog.photo_id = peer.photo_id
    if dialog.contact_id is None:
        dialog.contact = find_contact(peer)

    created = []
    for item in sorted(items, key=lambda i: i.tg_id):
        _, is_new = Message.objects.get_or_create(
            dialog=dialog,
            tg_id=item.tg_id,
            defaults={
                "outgoing": item.outgoing,
                "text": item.text,
                "date": item.date,
                "media_pending": item.media_pending,
                "media_kind": item.media_kind,
                "mime": item.mime[:100],
                "file_name": item.file_name[:200],
                "reply_to_id": item.reply_to_id,
            },
        )
        if is_new:
            created.append(item)

    incoming = [i for i in created if not i.outgoing]
    if created:
        dialog.unread = unread if unread is not None else dialog.unread + len(incoming)
        latest = dialog.messages.filter(deleted_at=None).first()
        if latest:
            _apply_latest(dialog, latest)
    dialog.save()

    if incoming and dialog.contact_id and Account.load().log_to_crm:
        _log_activity(dialog.contact, incoming[-1])
    return dialog


def known_dialogs() -> dict[int, tuple[datetime | None, int]]:
    """{peer_id: (oxirgi xabar vaqti, oxirgi xabar id)} — o'zgarmagan suhbatlarni qayta yuklamaslik uchun."""
    result = {}
    for dialog in Dialog.objects.all():
        latest = dialog.messages.first()
        result[dialog.peer_id] = (dialog.last_message_at, latest.tg_id if latest else 0)
    return result


# --- Rasmlar --------------------------------------------------------------------------


def update_state(peer_id: int, **fields) -> None:
    """Xabardan tashqari holat: profil rasmi, o'qilganlik, online, qadalgan."""
    Dialog.objects.filter(peer_id=peer_id).update(**fields)


def pending_avatars() -> list[PendingAvatar]:
    rows = Dialog.objects.exclude(photo_id=F("avatar_photo_id"))[:MEDIA_BATCH]
    return [PendingAvatar(d.pk, d.peer_id, d.access_hash, d.photo_id) for d in rows]


def save_avatar(dialog_id: int, photo_id: int, data: bytes | None) -> None:
    dialog = Dialog.objects.get(pk=dialog_id)
    if dialog.avatar:
        dialog.avatar.delete(save=False)
    if data:
        dialog.avatar.save(f"{dialog.peer_id}-{photo_id}.jpg", ContentFile(data), save=False)
    dialog.avatar_photo_id = photo_id
    dialog.save(update_fields=["avatar", "avatar_photo_id"])


def pending_media() -> list[PendingMedia]:
    rows = Message.objects.filter(media_pending=True, media="").select_related("dialog")[:MEDIA_BATCH]
    return [PendingMedia(m.pk, m.dialog.peer_id, m.dialog.access_hash, m.tg_id) for m in rows]


def save_media(message_id: int, data: bytes) -> None:
    # .bin: /media/ orqali to'g'ridan-to'g'ri ochilsa ham brauzer html/svg sifatida ishga tushirmaydi
    message = Message.objects.get(pk=message_id)
    message.media.save(f"{message.dialog_id}-{message.tg_id}.bin", ContentFile(data), save=False)
    message.media_pending = False
    message.save(update_fields=["media", "media_pending"])


def skip_media(message_id: int) -> None:
    """Fayl endi yo'q (xabar o'chirilgan): qayta-qayta urinmaslik uchun navbatdan chiqariladi."""
    Message.objects.filter(pk=message_id).update(media_pending=False)


def apply_edit(peer_id: int, tg_id: int, text: str, *, notify: bool = True) -> None:
    """Yangi matn qo'yiladi, eskisi tarixda qoladi."""
    message = Message.objects.select_related("dialog").filter(dialog__peer_id=peer_id, tg_id=tg_id).first()
    if message is None or message.text == text:
        return
    old = message.text
    with transaction.atomic():
        MessageEdit.objects.create(message=message, text=old)
        message.text, message.edited = text, True
        message.save(update_fields=["text", "edited"])
        _refresh_preview(message.dialog)
    if notify and not message.outgoing:
        _notify(
            f"✏️ <b>{h(message.dialog.title)}</b> xabarni tahrirladi\n\nOldin: {h(old[:300])}\nHozir: {h(text[:300])}"
        )


def mark_deleted(tg_ids: list[int], *, by_me: bool = False, notify: bool = True) -> None:
    """Shaxsiy chatlarda xabar id'lari akkaunt bo'yicha yagona, shuning uchun suhbatsiz ham topiladi."""
    rows = list(Message.objects.filter(tg_id__in=tg_ids, deleted_at=None).select_related("dialog"))
    if not rows:
        return
    Message.objects.filter(pk__in=[m.pk for m in rows]).update(deleted_at=timezone.now(), deleted_by_me=by_me)
    for dialog in {m.dialog_id: m.dialog for m in rows}.values():
        _refresh_preview(dialog)
    incoming = [m for m in rows if not m.outgoing]
    if notify and not by_me and incoming:
        title = h(incoming[0].dialog.title)
        lines = "\n".join(f"• {h(m.text[:200])}" for m in incoming[:NOTIFY_LINES])
        more = f"\n…yana {len(incoming) - NOTIFY_LINES} ta" if len(incoming) > NOTIFY_LINES else ""
        _notify(f"🗑 <b>{title}</b>: {len(incoming)} ta xabar o'chirildi\n\n{lines}{more}")


def _notify(text: str) -> None:
    if Account.load().notify_changes:
        send_message(text)


def _refresh_preview(dialog: Dialog) -> None:
    latest = dialog.messages.filter(deleted_at=None).first()
    if latest:
        _apply_latest(dialog, latest)
    else:
        dialog.last_text = "Xabarlar o'chirilgan"  # vaqt qoladi: suhbat ro'yxatdan yo'qolmaydi
        dialog.awaiting_reply = False
    dialog.save(update_fields=["last_text", "last_message_at", "awaiting_reply"])


def _apply_latest(dialog: Dialog, latest: Message) -> None:
    dialog.last_text, dialog.last_message_at = latest.text[:200], latest.date
    dialog.awaiting_reply = not latest.outgoing


def unread_total() -> int:
    """Menyudagi raqam. Akkaunt uzilgan bo'lsa, eski son ko'rsatilmaydi."""
    if not Account.objects.filter(status=Account.Status.CONNECTED).exists():
        return 0
    return Dialog.objects.aggregate(total=Sum("unread"))["total"] or 0


def needs_reconcile() -> bool:
    account = Account.load()
    return not account.reconciled_at or (timezone.now() - account.reconciled_at).total_seconds() >= RECONCILE_EVERY


def reconcile_targets() -> list[ReconcileTarget]:
    """Yaqinda faol suhbatlardagi xabarlar: userbot to'xtagan paytdagi o'zgarishlarni topish uchun."""
    since = timezone.now() - timedelta(days=RECONCILE_DAYS)
    targets = []
    for dialog in Dialog.objects.filter(last_message_at__gte=since).order_by("-last_message_at")[:RECONCILE_DIALOGS]:
        rows = dialog.messages.filter(deleted_at=None).values_list("tg_id", "text")[:RECONCILE_MESSAGES]
        if rows:
            targets.append(ReconcileTarget(dialog.peer_id, dialog.access_hash, dict(rows)))
    return targets


def reconciled() -> None:
    Account.objects.filter(pk=1).update(reconciled_at=timezone.now())


def delete_media() -> None:
    for dialog in Dialog.objects.exclude(avatar=""):
        dialog.avatar.delete(save=False)
    for message in Message.objects.exclude(media=""):
        message.media.delete(save=False)
    for row in Outbox.objects.exclude(file=""):
        row.file.delete(save=False)


# --- Holat -----------------------------------------------------------------------------


def load_credentials() -> Credentials | None:
    close_old_connections()
    account = Account.load()
    if not account.is_connected or not account.encrypted_session:
        return None
    session = account.session
    if session.startswith("⚠"):  # IFCODER_FERNET_KEY almashgan
        mark_revoked("Sessiyani ochib bo'lmadi: IFCODER_FERNET_KEY o'zgargan. Qayta ulang.")
        return None
    return Credentials(account.api_id, account.api_hash, session, account.encrypted_session)


def tick() -> Tick:
    close_old_connections()
    account = Account.load()
    now = timezone.now()
    if not account.heartbeat_at or (now - account.heartbeat_at).total_seconds() >= HEARTBEAT_EVERY:
        Account.objects.filter(pk=account.pk).update(heartbeat_at=now, last_error="")
    return Tick(account.encrypted_session, account.sync_requested)


def sync_finished() -> None:
    Account.objects.filter(pk=1).update(sync_requested=False, synced_at=timezone.now())


def set_error(text: str) -> None:
    Account.objects.filter(pk=1).update(last_error=text[:300])


def mark_revoked(reason: str) -> None:
    """Sessiya endi yaroqsiz — qayta ulanish kerak."""
    Account.objects.filter(pk=1).update(
        status=Account.Status.DISCONNECTED, encrypted_session="", encrypted_code_hash="", last_error=reason[:300]
    )


def begin_login(api_id: int, api_hash: str, phone: str, session: str, code_hash: str) -> Account:
    account = Account.load()
    account.api_id, account.api_hash, account.phone = api_id, api_hash, phone
    account.session, account.code_hash = session, code_hash
    account.status = Account.Status.CODE_SENT
    account.last_error = ""
    account.save()
    return account


def finish_login(account: Account, session: str, me) -> None:
    if account.tg_id and account.tg_id != me.id:
        delete_media()
        Dialog.objects.all().delete()  # boshqa akkaunt — eski suhbatlar aralashmasin
        account.last_command_id = 0
    account.session, account.code_hash = session, ""
    account.tg_id, account.tg_name, account.tg_username = me.id, me.name, me.username
    account.status = Account.Status.CONNECTED
    account.sync_requested = True
    account.last_error = ""
    account.save()


def reset_login(account: Account) -> None:
    account.session, account.code_hash = "", ""
    account.status = Account.Status.DISCONNECTED
    account.heartbeat_at = None
    account.save()


def claim_command(message_id: int) -> bool:
    """Buyruq ikki marta bajarilmasligi uchun: faqat yangi id uchun True qaytaradi."""
    return bool(Account.objects.filter(pk=1, last_command_id__lt=message_id).update(last_command_id=message_id))


def command_state() -> tuple[int, bool]:
    account = Account.load()
    return account.last_command_id, account.commands_enabled


# --- Navbat ----------------------------------------------------------------------------


def enqueue(dialog: Dialog | None, text: str = "", **fields) -> Outbox:
    return Outbox.objects.create(dialog=dialog, text=text, **fields)


def voice_dialog(debt) -> Dialog | None:
    return debt.contact.telegram_dialogs.first() if debt.contact else None


def reminded_today(debt) -> bool:
    """Bir qarz bo'yicha kuniga bittadan ortiq eslatma yo'q: bezovta qilish va spam bloklanishi xavfi."""
    return (
        debt.voice_reminders.filter(created_at__date=timezone.localdate()).exclude(status=Outbox.Status.FAILED).exists()
    )


def fail_stale_sends() -> None:
    """Jarayon yuborish paytida o'lgan bo'lsa, xabar ketgan-ketmagani noma'lum — takror yubormaymiz."""
    Outbox.objects.filter(status=Outbox.Status.SENDING).update(
        status=Outbox.Status.FAILED, error="Yuborish uzildi: Telegram'da ketgan-ketmaganini tekshiring."
    )


def claim_pending() -> list[Job]:
    claimed = []
    due = Q(send_at=None) | Q(send_at__lte=timezone.now())
    for row in Outbox.objects.filter(due, status=Outbox.Status.PENDING).select_related("dialog")[:PENDING_BATCH]:
        taken = Outbox.objects.filter(pk=row.pk, status=Outbox.Status.PENDING).update(status=Outbox.Status.SENDING)
        if taken:
            dialog = row.dialog
            claimed.append(
                Job(
                    row.pk,
                    row.kind,
                    dialog.peer_id if dialog else 0,
                    dialog.access_hash if dialog else 0,
                    row.text,
                    row.target_id,
                    row.reply_to_id,
                    row.file_name,
                    bool(row.file),
                    row.voice,
                    row.speed,
                )
            )
    return claimed


def peer_of(dialog: Dialog) -> Peer:
    return Peer(dialog.peer_id, dialog.access_hash, dialog.name, dialog.username, dialog.phone, dialog.photo_id)


def read_file(outbox_id: int) -> bytes:
    row = Outbox.objects.get(pk=outbox_id)
    with row.file.open("rb") as handle:
        return handle.read()


def finish_job(outbox_id: int) -> None:
    row = Outbox.objects.get(pk=outbox_id)
    if row.file:
        row.file.delete(save=False)  # Telegram'ga ketdi; nusxa xabar sifatida qaytib yuklanadi
    Outbox.objects.filter(pk=outbox_id).update(status=Outbox.Status.SENT, error="", file="")


def mark_sent(outbox_id: int, item: Item) -> None:
    dialog = Outbox.objects.select_related("dialog").get(pk=outbox_id).dialog
    record(peer_of(dialog), [item], unread=dialog.unread)
    finish_job(outbox_id)


def store_history(outbox_id: int, items: list[Item]) -> None:
    dialog = Outbox.objects.select_related("dialog").get(pk=outbox_id).dialog
    record(peer_of(dialog), items, unread=dialog.unread)
    finish_job(outbox_id)


def mark_failed(outbox_id: int, error: str) -> None:
    Outbox.objects.filter(pk=outbox_id).update(status=Outbox.Status.FAILED, error=error[:300])


def requeue(outbox_id: int) -> None:
    Outbox.objects.filter(pk=outbox_id).update(status=Outbox.Status.PENDING)


# --- CRM -------------------------------------------------------------------------------


def create_contact(dialog: Dialog) -> Contact:
    contact = Contact.objects.create(
        name=dialog.title,
        telegram=f"@{dialog.username}" if dialog.username else "",
        phone=f"+{_digits(dialog.phone)}" if dialog.phone else "",
        source=Contact.Source.TELEGRAM,
        status=Contact.Status.LEAD,
    )
    dialog.contact = contact
    dialog.save(update_fields=["contact", "updated_at"])
    return contact
