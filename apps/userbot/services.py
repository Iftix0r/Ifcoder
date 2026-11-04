"""Userbot holati va suhbatlar nusxasi ustidagi sinxron amallar (panel ham, runner ham shularni ishlatadi)."""

import re
from dataclasses import dataclass
from datetime import datetime

from django.db import close_old_connections, transaction
from django.utils import timezone

from apps.crm.models import Activity, Contact

from .models import Account, Dialog, Message, Outbox

HEARTBEAT_EVERY = 30  # soniya
PENDING_BATCH = 5


@dataclass
class Peer:
    id: int
    access_hash: int
    name: str = ""
    username: str = ""
    phone: str = ""


@dataclass
class Item:
    tg_id: int
    outgoing: bool
    text: str
    date: datetime


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
class PendingSend:
    id: int
    peer_id: int
    access_hash: int
    text: str


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
    if dialog.contact_id is None:
        dialog.contact = find_contact(peer)

    created = []
    for item in sorted(items, key=lambda i: i.tg_id):
        _, is_new = Message.objects.get_or_create(
            dialog=dialog,
            tg_id=item.tg_id,
            defaults={"outgoing": item.outgoing, "text": item.text, "date": item.date},
        )
        if is_new:
            created.append(item)

    incoming = [i for i in created if not i.outgoing]
    if created:
        dialog.unread = unread if unread is not None else dialog.unread + len(incoming)
        latest = dialog.messages.first()
        dialog.last_text, dialog.last_message_at = latest.text[:200], latest.date
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


def enqueue(dialog: Dialog, text: str) -> Outbox:
    return Outbox.objects.create(dialog=dialog, text=text)


def fail_stale_sends() -> None:
    """Jarayon yuborish paytida o'lgan bo'lsa, xabar ketgan-ketmagani noma'lum — takror yubormaymiz."""
    Outbox.objects.filter(status=Outbox.Status.SENDING).update(
        status=Outbox.Status.FAILED, error="Yuborish uzildi: Telegram'da ketgan-ketmaganini tekshiring."
    )


def claim_pending() -> list[PendingSend]:
    claimed = []
    for row in Outbox.objects.filter(status=Outbox.Status.PENDING).select_related("dialog")[:PENDING_BATCH]:
        taken = Outbox.objects.filter(pk=row.pk, status=Outbox.Status.PENDING).update(status=Outbox.Status.SENDING)
        if taken:
            claimed.append(PendingSend(row.pk, row.dialog.peer_id, row.dialog.access_hash, row.text))
    return claimed


def mark_sent(outbox_id: int, tg_id: int, date: datetime) -> None:
    row = Outbox.objects.select_related("dialog").get(pk=outbox_id)
    dialog = row.dialog
    peer = Peer(dialog.peer_id, dialog.access_hash, dialog.name, dialog.username, dialog.phone)
    record(peer, [Item(tg_id, True, row.text, date)], unread=dialog.unread)
    Outbox.objects.filter(pk=outbox_id).update(status=Outbox.Status.SENT, error="")


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
