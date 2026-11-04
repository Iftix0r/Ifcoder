"""Telegram userbot: ulanish oqimi, suhbatlar, navbat va buyruqlar (Telegram'ga haqiqiy ulanishsiz)."""

import io
import os
import wave
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pytest
from asgiref.sync import async_to_sync
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from telethon import errors
from telethon.tl.types import (
    MessageMediaDocument,
    MessageMediaPhoto,
    MessageMediaWebPage,
    Photo,
    UserStatusOffline,
    UserStatusOnline,
    WebPageEmpty,
)

from apps.crm.models import Activity, Contact
from apps.finance.models import Debt, Transaction
from apps.notes.models import Note
from apps.planner.models import Task
from apps.userbot import client as tg
from apps.userbot import commands, services, voice
from apps.userbot.models import Account, Dialog, Message, Outbox, QuickReply
from apps.userbot.runner import Runner, restart_stamp, seen_fields, to_item
from apps.userbot.services import Item, Peer

HX = {"HTTP_HX_REQUEST": "true"}
API = {"api_id": "12345", "api_hash": "a" * 32, "phone": "+998901234567"}
ME = tg.Me(id=1, name="Iftixor", username="iftixor")


def connected(**extra):
    account = Account.load()
    account.api_id, account.api_hash, account.session = 12345, "a" * 32, "sess"
    account.status, account.tg_id = Account.Status.CONNECTED, 1
    for key, value in extra.items():
        setattr(account, key, value)
    account.save()
    return account


def item(tg_id=1, text="Salom", outgoing=False, date=None):
    return Item(tg_id, outgoing, text, date or timezone.now())


# --- Ulanish ---------------------------------------------------------------------------


def login_until_code(client_in):
    with mock.patch("apps.userbot.client.request_code", return_value=("sess1", "hash1")) as request:
        client_in.post(reverse("telegram_connect"), API)
    return request


def test_login_flow_with_code(client_in):
    request = login_until_code(client_in)
    request.assert_called_once_with(12345, "a" * 32, "+998901234567")
    account = Account.load()
    assert account.status == "code" and account.session == "sess1" and account.code_hash == "hash1"
    assert "a" * 32 not in account.encrypted_api_hash and "sess1" not in account.encrypted_session

    result = tg.CodeResult(session="sess2", me=ME)
    with mock.patch("apps.userbot.client.submit_code", return_value=result) as submit:
        client_in.post(reverse("telegram_code"), {"code": "12345"})
    submit.assert_called_once_with(12345, "a" * 32, "sess1", "+998901234567", "12345", "hash1")
    account = Account.load()
    assert account.is_connected and account.session == "sess2" and account.tg_name == "Iftixor"
    assert account.code_hash == "" and account.sync_requested


def test_login_flow_with_password(client_in):
    login_until_code(client_in)
    with mock.patch("apps.userbot.client.submit_code", return_value=tg.CodeResult(session="sess2")):
        client_in.post(reverse("telegram_code"), {"code": "12345"})
    assert Account.load().status == "password"
    assert "Telegram 2FA parol" in client_in.get(reverse("telegram_home")).content.decode()

    result = tg.CodeResult(session="sess3", me=ME)
    with mock.patch("apps.userbot.client.submit_password", return_value=result):
        client_in.post(reverse("telegram_password"), {"password": "maxfiy-parol"})
    account = Account.load()
    assert account.is_connected and account.session == "sess3"
    fields = [str(getattr(account, f.name)) for f in Account._meta.fields]
    assert not any("maxfiy-parol" in value for value in fields)


def test_login_error_is_shown_and_state_kept(client_in):
    login_until_code(client_in)
    with mock.patch("apps.userbot.client.submit_code", side_effect=tg.LoginError("Kod noto'g'ri.")):
        resp = client_in.post(reverse("telegram_code"), {"code": "11111"})
    assert "Kod noto&#x27;g&#x27;ri." in resp.content.decode()
    assert Account.load().status == "code"


@pytest.mark.parametrize(
    "data", [{**API, "api_hash": "qisqa"}, {**API, "phone": "998901234567"}, {**API, "api_id": "abc"}]
)
def test_connect_rejects_bad_input(client_in, data):
    with mock.patch("apps.userbot.client.request_code") as request:
        client_in.post(reverse("telegram_connect"), data)
    assert not request.called and Account.load().status == "off"


def test_api_hash_never_rendered(client_in):
    connected()
    assert "a" * 32 not in client_in.get(reverse("telegram_home")).content.decode()


def test_cancel_clears_login(client_in):
    login_until_code(client_in)
    client_in.post(reverse("telegram_cancel"))
    account = Account.load()
    assert account.status == "off" and not account.encrypted_session and not account.encrypted_code_hash


def test_logout_revokes_session(client_in):
    connected()
    with mock.patch("apps.userbot.client.log_out") as log_out:
        client_in.post(reverse("telegram_logout"))
    log_out.assert_called_once_with(12345, "a" * 32, "sess")
    assert Account.load().status == "off" and not Account.load().encrypted_session


def test_logout_clears_panel_even_if_telegram_unreachable(client_in):
    connected()
    with mock.patch("apps.userbot.client.log_out", side_effect=tg.LoginError("x")):
        client_in.post(reverse("telegram_logout"))
    assert not Account.load().encrypted_session


def test_other_account_login_drops_old_chats(db):
    account = connected(last_command_id=50)
    services.record(Peer(10, 5, "Ali"), [item()])
    services.finish_login(account, "new", tg.Me(id=2, name="Boshqa", username=""))
    assert not Dialog.objects.exists() and Account.load().last_command_id == 0


def test_telegram_pages_require_login(client, db):
    assert client.get(reverse("telegram_home")).status_code == 302


def test_friendly_errors():
    assert "noto'g'ri" in tg._message(errors.PhoneCodeInvalidError(request=None))
    assert "60" in tg._message(errors.FloodWaitError(request=None, capture=60))
    assert "ulanib bo'lmadi" in tg._message(ConnectionError())


# --- Suhbatlar -------------------------------------------------------------------------


def test_record_is_idempotent_and_counts_unread(db):
    peer = Peer(10, 5, "Ali")
    services.record(peer, [item(1), item(2, outgoing=True)])
    dialog = services.record(peer, [item(1), item(3, "Oxirgi")])
    assert dialog.messages.count() == 3 and dialog.unread == 2 and dialog.last_text == "Oxirgi"


@pytest.mark.parametrize(
    ("stored", "peer"),
    [
        ({"telegram": "@Ali_V"}, Peer(10, 5, "Ali", username="ali_v")),
        ({"telegram": "ali_v"}, Peer(10, 5, "Ali", username="ali_v")),
        ({"phone": "+998 90 123-45-67"}, Peer(10, 5, "Ali", phone="998901234567")),
    ],
)
def test_dialog_links_crm_contact(db, stored, peer):
    contact = Contact.objects.create(name="Ali", **stored)
    assert services.record(peer, [item()]).contact == contact


def test_contact_message_logged_once_per_day(db):
    connected()
    contact = Contact.objects.create(name="Ali", telegram="@ali")
    peer = Peer(10, 5, "Ali", username="ali")
    services.record(peer, [item(1, "Birinchi")])
    services.record(peer, [item(2, "Ikkinchi")])
    assert list(contact.activities.values_list("text", flat=True)) == ["Telegram: Birinchi"]


def test_old_history_and_disabled_option_not_logged(db):
    connected()
    contact = Contact.objects.create(name="Ali", telegram="@ali")
    peer = Peer(10, 5, "Ali", username="ali")
    services.record(peer, [item(1, date=timezone.now() - timedelta(days=3))])
    Account.objects.update(log_to_crm=False)
    services.record(peer, [item(2)])
    assert not contact.activities.exists()


def test_chat_page_escapes_and_marks_read(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(1, "<script>x</script>")])
    html = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    assert "<script>x</script>" not in html and "&lt;script&gt;" in html
    dialog.refresh_from_db()
    assert dialog.unread == 0


def test_send_enqueues_and_rejects_empty(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    url = reverse("telegram_send", args=[dialog.pk])
    assert client_in.post(url, {"text": "Javob"}, **HX).status_code == 204
    assert client_in.post(url, {"text": "   "}, **HX).status_code == 422
    assert client_in.post(url, {"text": "x" * 4097}, **HX).status_code == 422
    assert list(Outbox.objects.values_list("text", "status")) == [("Javob", "pending")]


def test_make_contact_from_dialog(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali", username="ali", phone="998901234567"), [item()])
    resp = client_in.post(reverse("telegram_contact", args=[dialog.pk]))
    contact = Contact.objects.get()
    assert resp.url == contact.get_absolute_url()
    assert (contact.telegram, contact.phone, contact.status) == ("@ali", "+998901234567", "lead")
    client_in.post(reverse("telegram_contact", args=[dialog.pk]))
    assert Contact.objects.count() == 1
    assert "Suhbat" in client_in.get(contact.get_absolute_url()).content.decode()


def test_options_do_not_overwrite_runner_state(client_in):
    connected(last_command_id=5)
    stale = Account.load()
    Account.objects.update(last_command_id=9)
    with mock.patch("apps.userbot.views.Account.load", return_value=stale):
        client_in.post(
            reverse("telegram_options"),
            {"log_to_crm": "on", "voice": "uz-UZ-SardorNeural", "voice_speed": "slow"},
            **HX,
        )
    account = Account.objects.get()
    assert account.last_command_id == 9 and not account.commands_enabled and account.log_to_crm


# --- Buyruqlar -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "amount", "currency", "rest"),
    [
        ("1 500 000 Mijoz to'lovi", "1500000", "UZS", "Mijoz to'lovi"),
        ("500000", "500000", "UZS", ""),
        ("50k Tushlik", "50000", "UZS", "Tushlik"),
        ("1.5mln Loyiha", "1500000", "UZS", "Loyiha"),
        ("$100 Frilans", "100", "USD", "Frilans"),
        ("100$ Frilans", "100", "USD", "Frilans"),
        ("2 ta kitob", "2", "UZS", "ta kitob"),
    ],
)
def test_parse_amount(text, amount, currency, rest):
    assert commands.parse_amount(text) == (Decimal(amount), currency, rest)


@pytest.mark.parametrize("text", ["", "kitob", "0", "-5 qarz"])
def test_parse_amount_rejects(text):
    assert commands.parse_amount(text) is None


def test_commands_create_records(db):
    assert "Vazifa" in commands.handle(".vazifa Deploy <b>")
    assert Task.objects.get().planned_for == timezone.localdate()
    commands.handle(".eslatma Sarlavha\nDavomi")
    assert Note.objects.get().title == "Sarlavha"
    commands.handle(".chiqim 50k Tushlik")
    tx = Transaction.objects.get()
    assert (tx.kind, tx.amount, tx.description) == ("expense", 50000, "Tushlik")
    commands.handle(".mijoz Ali Valiyev @ali_v +998901234567")
    contact = Contact.objects.get()
    assert (contact.name, contact.telegram, contact.phone) == ("Ali Valiyev", "@ali_v", "+998901234567")


def test_command_reply_escapes_html(db):
    assert "<b>" not in commands.handle(".vazifa <b>x</b>")


@pytest.mark.parametrize("text", ["Salom", ".gitignore", ".", "", None, "vazifa x"])
def test_non_commands_ignored(db, text):
    assert commands.handle(text) is None


def test_bad_amount_and_missing_argument(db):
    assert "tushunmadim" in commands.handle(".kirim ko'p")
    assert "buyruqlari" in commands.handle(".vazifa")
    assert not Transaction.objects.exists() and not Task.objects.exists()


def test_today_command(data):
    assert "Login sahifasi" in commands.handle(".bugun")


# --- Runner ----------------------------------------------------------------------------


def user(id=10, **extra):
    base = {
        "id": id,
        "access_hash": 5,
        "first_name": "Ali",
        "last_name": None,
        "username": "ali",
        "phone": None,
        "bot": False,
        "is_self": False,
        "deleted": False,
        "photo": None,
        "status": None,
    }
    return SimpleNamespace(**{**base, **extra})


def tg_message(id, text="Salom", out=False):
    return SimpleNamespace(id=id, message=text, out=out, date=timezone.now(), media=None, action=None)


def tg_dialog(entity, *, is_user=True, unread=1):
    return SimpleNamespace(
        is_user=is_user,
        entity=entity,
        unread_count=unread,
        date=timezone.now(),
        pinned=False,
        dialog=SimpleNamespace(read_outbox_max_id=0),
    )


async def agen(values):
    for value in values:
        yield value


class FakeClient:
    def __init__(self, dialogs=(), history=None, saved=(), send_error=None):
        self.dialogs, self.history, self.saved = dialogs, history or {}, list(saved)
        self.send_error = send_error
        self.sent = []
        self.remote = {}
        self.download_error = None
        self.avatar_calls = 0
        self.calls = []
        self.entities = {}
        self.latest = []

    async def get_messages(self, peer, ids=None, limit=None):
        if limit:
            return self.latest
        if isinstance(ids, list):
            return [self.remote[i] for i in ids if i in self.remote]  # Telegram o'chganini tashlab yuborishi mumkin
        return self.remote.get(ids)

    async def download_media(self, message, file):
        if self.download_error:
            raise self.download_error
        return b"rasm"

    async def download_profile_photo(self, peer, file):
        if self.download_error:
            raise self.download_error
        self.avatar_calls += 1
        return b"avatar"

    def iter_dialogs(self, limit):
        return agen(self.dialogs)

    def iter_messages(self, entity, limit, min_id=0, max_id=0):
        peer_id = getattr(entity, "id", None) or getattr(entity, "user_id", None)
        messages = self.saved if entity == "me" else self.history.get(peer_id, [])
        rows = (m for m in messages if m.id > min_id and (not max_id or m.id < max_id))
        return agen(sorted(rows, key=lambda m: -m.id)[:limit])

    async def send_message(self, peer, text, **kwargs):
        if self.send_error:
            raise self.send_error
        self.sent.append((peer, text, kwargs))
        return tg_message(900 + len(self.sent), text, out=True)

    async def send_file(self, peer, file, **kwargs):
        self.sent.append((peer, file, kwargs))
        return tg_message(900 + len(self.sent), kwargs.get("caption") or "Fayl", out=True)

    async def edit_message(self, peer, message_id, text, **kwargs):
        self.calls.append(("edit", message_id, text))

    async def delete_messages(self, peer, ids, revoke):
        self.calls.append(("delete", ids, revoke))

    async def send_read_acknowledge(self, peer, max_id):
        self.calls.append(("read", max_id))

    async def get_entity(self, username):
        if username not in self.entities:
            raise ValueError("No user has that username")
        return self.entities[username]


def runner_with(fake):
    runner = Runner()
    runner.client, runner.me = fake, SimpleNamespace(id=1)
    return runner


def test_sync_stores_private_chats_only(db):
    connected()
    code_chat, bot, me = user(777000), user(11, bot=True), user(1, is_self=True)
    channel = SimpleNamespace(id=12)
    history = {
        10: [tg_message(1), tg_message(2, "Javob", out=True)],
        777000: [tg_message(3, "Login code: 12345")],
        11: [tg_message(4)],
        1: [tg_message(5)],
        12: [tg_message(6)],
    }
    dialogs = [tg_dialog(user(10)), tg_dialog(code_chat), tg_dialog(bot), tg_dialog(me)]
    dialogs.append(tg_dialog(channel, is_user=False))
    async_to_sync(runner_with(FakeClient(dialogs, history)).sync)()
    dialog = Dialog.objects.get()
    assert dialog.peer_id == 10 and dialog.access_hash == 5 and dialog.unread == 1
    assert Message.objects.count() == 2 and not Message.objects.filter(text__contains="12345").exists()
    assert Account.load().synced_at


def test_incoming_login_code_event_not_stored(db):
    connected()
    event = SimpleNamespace(is_private=True, chat_id=777000, message=tg_message(1, "Login code: 12345"))

    async def get_chat():
        return user(777000)

    event.get_chat = get_chat
    async_to_sync(runner_with(FakeClient()).on_message)(event)
    assert not Message.objects.exists()


def test_first_sync_does_not_run_old_saved_messages(db):
    connected()
    fake = FakeClient(saved=[tg_message(7, ".vazifa Eski", out=True)])
    async_to_sync(runner_with(fake).sync)()
    assert not Task.objects.exists() and Account.load().last_command_id == 7


def test_missed_commands_run_once_in_order(db):
    connected(last_command_id=7)
    saved = [
        tg_message(7, ".vazifa Eski", out=True),
        tg_message(8, ".vazifa Birinchi", out=True),
        tg_message(9, ".vazifa Ikkinchi", out=True),
    ]
    fake = FakeClient(saved=saved)
    runner = runner_with(fake)
    async_to_sync(runner.sync_commands)()
    async_to_sync(runner.sync_commands)()
    assert list(Task.objects.order_by("id").values_list("title", flat=True)) == ["Birinchi", "Ikkinchi"]
    assert len(fake.sent) == 2 and fake.sent[0][0] == "me"


def test_saved_message_from_other_side_is_not_command(db):
    connected()
    async_to_sync(runner_with(FakeClient()).run_command)(tg_message(5, ".vazifa Begona", out=False))
    assert not Task.objects.exists()


def test_commands_disabled(db):
    connected(commands_enabled=False)
    fake = FakeClient()
    async_to_sync(runner_with(fake).run_command)(tg_message(5, ".vazifa X", out=True))
    assert not Task.objects.exists() and not fake.sent


def test_failing_command_reports_without_crashing(db):
    connected()
    fake = FakeClient()
    with mock.patch("apps.userbot.commands.handle", side_effect=ValueError("x")):
        async_to_sync(runner_with(fake).run_command)(tg_message(5, ".vazifa X", out=True))
    assert "bajarilmadi" in fake.sent[0][1]


def queued(text="Javob"):
    connected()
    return services.enqueue(services.record(Peer(10, 5, "Ali"), [item()]), text)


def test_outbox_sends_and_records(db):
    row = queued()
    fake = FakeClient()
    async_to_sync(runner_with(fake).flush_outbox)()
    peer, text, kwargs = fake.sent[0]
    assert (peer.user_id, peer.access_hash, text, kwargs["parse_mode"]) == (10, 5, "Javob", None)
    row.refresh_from_db()
    assert row.status == "sent" and Message.objects.filter(text="Javob", outgoing=True).exists()
    async_to_sync(runner_with(fake).flush_outbox)()
    assert len(fake.sent) == 1


def test_flood_wait_requeues_and_pauses(db):
    row = queued()
    runner = runner_with(FakeClient(send_error=errors.FloodWaitError(request=None, capture=120)))
    async_to_sync(runner.flush_outbox)()
    row.refresh_from_db()
    assert row.status == "pending" and runner.pause_sends_until > 0
    runner.client.send_error = None
    async_to_sync(runner.flush_outbox)()
    assert not runner.client.sent


def test_peer_flood_stops_sending(db):
    row = queued()
    second = services.enqueue(row.dialog, "Ikkinchi")
    runner = runner_with(FakeClient(send_error=errors.PeerFloodError(request=None)))
    async_to_sync(runner.flush_outbox)()
    row.refresh_from_db()
    second.refresh_from_db()
    assert row.status == "failed" and "spam" in row.error and second.status == "pending"


def test_blocked_user_fails_message(db):
    row = queued()
    async_to_sync(runner_with(FakeClient(send_error=errors.UserIsBlockedError(request=None))).flush_outbox)()
    row.refresh_from_db()
    assert row.status == "failed" and "bloklagan" in row.error


def test_interrupted_send_is_not_repeated(db):
    row = queued()
    Outbox.objects.update(status="sending")
    services.fail_stale_sends()
    row.refresh_from_db()
    assert row.status == "failed"


def test_revoked_session_disconnects(db):
    connected()

    class Revoked:
        def __init__(self, *args):
            pass

        async def connect(self):
            raise errors.AuthKeyUnregisteredError(request=None)

        async def disconnect(self):
            pass

    async_to_sync(Runner(Revoked).run)(once=True)
    account = Account.load()
    assert account.status == "off" and not account.encrypted_session and "Qayta ulang" in account.last_error


def test_runner_stops_when_panel_disconnects(db):
    connected()
    creds = services.load_credentials()
    services.reset_login(Account.load())
    assert services.tick().encrypted_session != creds.encrypted_session
    assert services.load_credentials() is None


def test_changed_fernet_key_asks_to_reconnect(db, settings):
    connected()
    settings.VAULT_FERNET_KEY = "c2Vjb25kLWRldi1mZXJuZXQta2V5LWZvci10ZXN0cyE="
    assert services.load_credentials() is None
    assert Account.objects.get().status == "off"


def test_media_placeholder_and_service_messages():
    photo = with_media(tg_message(1, ""), photo_media(), photo=object())
    assert to_item(photo).text == "[Rasm]" and to_item(photo).media_pending
    assert to_item(SimpleNamespace(**{**vars(tg_message(2)), "action": object()})) is None


def photo_media(ttl=None):
    photo = Photo(id=1, access_hash=1, file_reference=b"", date=timezone.now(), sizes=[], dc_id=2)
    return MessageMediaPhoto(photo=photo, ttl_seconds=ttl)


def with_media(message, media, **extra):
    return SimpleNamespace(**{**vars(message), "media": media, **extra})


def test_view_once_and_link_preview_not_downloaded():
    once = with_media(tg_message(1, ""), photo_media(ttl=10), photo=object())
    assert to_item(once).text == "[Rasm]" and not to_item(once).media_pending
    preview = with_media(tg_message(2, "https://x.uz"), MessageMediaWebPage(webpage=WebPageEmpty(id=1)))
    assert not to_item(preview).media_pending


def test_image_downloaded_and_shown(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True, "photo")])
    fake = FakeClient()
    fake.remote[7] = tg_message(7, "")
    async_to_sync(runner_with(fake).fetch_media)()
    message = Message.objects.get()
    assert message.media.read() == b"rasm"
    html = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    thread = html.split('id="tg-thread"')[1]
    assert reverse("telegram_media", args=[message.pk]) in thread and "[Rasm]" not in thread


def test_image_caption_stays_visible(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [Item(7, False, "Mana chek", timezone.now(), True, "photo")])
    services.save_media(Message.objects.get().pk, b"rasm")
    assert "Mana chek" in client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()


def test_deleted_message_leaves_image_queue(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True, "photo")])
    async_to_sync(runner_with(FakeClient()).fetch_media)()
    assert not services.pending_media()


def test_image_flood_wait_keeps_queue_and_pauses(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True, "photo")])
    fake = FakeClient()
    fake.remote[7] = tg_message(7, "")
    fake.download_error = errors.FloodWaitError(request=None, capture=100)
    runner = runner_with(fake)
    async_to_sync(runner.fetch_media)()
    assert services.pending_media() and runner.pause_media_until > 0


def test_revoked_during_image_download_is_raised(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True, "photo")])
    fake = FakeClient()
    fake.remote[7] = tg_message(7, "")
    fake.download_error = errors.AuthKeyUnregisteredError(request=None)
    with pytest.raises(errors.AuthKeyUnregisteredError):
        async_to_sync(runner_with(fake).fetch_media)()


def test_avatar_downloaded_once_then_replaced_and_removed(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali", photo_id=77), [item()])
    fake = FakeClient()
    runner = runner_with(fake)
    async_to_sync(runner.fetch_media)()
    async_to_sync(runner.fetch_media)()
    dialog.refresh_from_db()
    assert fake.avatar_calls == 1 and dialog.avatar.read() == b"avatar"
    assert dialog.avatar.url in client_in.get(reverse("telegram_home")).content.decode()

    services.update_state(10, photo_id=88)
    async_to_sync(runner.fetch_media)()
    dialog.refresh_from_db()
    assert fake.avatar_calls == 2 and "88" in dialog.avatar.name

    services.update_state(10, photo_id=0)
    async_to_sync(runner.fetch_media)()
    dialog.refresh_from_db()
    assert not dialog.avatar and fake.avatar_calls == 2


def test_sent_message_keeps_photo_id(db):
    row = services.enqueue(services.record(Peer(10, 5, "Ali", photo_id=77), [item()]), "Javob")
    services.mark_sent(row.pk, Item(50, True, "Javob", timezone.now()))
    assert Dialog.objects.get().photo_id == 77


def test_sync_updates_photo_of_unchanged_dialog(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1, date=timezone.now())])
    entity = user(10, photo=SimpleNamespace(photo_id=77))
    dialog = tg_dialog(entity)
    dialog.date = timezone.now() - timedelta(days=1)
    async_to_sync(runner_with(FakeClient([dialog])).sync)()
    assert Dialog.objects.get().photo_id == 77


def test_other_account_login_deletes_files(db):
    account = connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True, "photo")])
    services.save_media(Message.objects.get().pk, b"rasm")
    storage, name = Message.objects.get().media.storage, Message.objects.get().media.name
    services.finish_login(account, "new", tg.Me(id=2, name="Boshqa", username=""))
    assert not storage.exists(name)


def test_media_requires_login(client, db):
    assert client.get("/media/telegram/photos/1-1.jpg").status_code == 302


def doc_media(ttl=None):
    return MessageMediaDocument(document=SimpleNamespace(), ttl_seconds=ttl)


def doc_message(**extra):
    file = SimpleNamespace(mime_type=extra.pop("mime", "application/pdf"), size=extra.pop("size", 10), name="a.pdf")
    return with_media(tg_message(1, ""), doc_media(extra.pop("ttl", None)), file=file, **extra)


@pytest.mark.parametrize(
    ("extra", "kind", "label"),
    [
        ({"voice": 1, "mime": "audio/ogg"}, "voice", "[Ovozli xabar]"),
        ({"video_note": 1, "mime": "video/mp4"}, "round", "[Video xabar]"),
        ({"video": 1, "mime": "video/mp4"}, "video", "[Video]"),
        ({"audio": 1, "mime": "audio/mpeg"}, "audio", "[Audio]"),
        ({"sticker": 1, "mime": "image/webp"}, "sticker", "[Stiker]"),
        ({}, "document", "[Fayl]"),
    ],
)
def test_media_kinds(extra, kind, label):
    result = to_item(doc_message(**extra))
    assert (result.media_kind, result.text, result.media_pending) == (kind, label, True)


def test_large_animated_and_view_once_files_not_downloaded():
    assert not to_item(doc_message(size=21 * 1024 * 1024)).media_pending
    assert not to_item(doc_message(sticker=1, mime="application/x-tgsticker")).media_pending
    assert not to_item(doc_message(ttl=5)).media_pending


def saved_file(mime, name="x"):
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Fayl]", timezone.now(), True, "document", mime, name)])
    message = Message.objects.get()
    services.save_media(message.pk, b"<script>alert(1)</script>")
    return reverse("telegram_media", args=[message.pk])


@pytest.mark.parametrize("mime", ["text/html", "image/svg+xml", "application/pdf", ""])
def test_unsafe_files_are_download_only(client_in, mime):
    resp = client_in.get(saved_file(mime, "evil.html"))
    assert resp["Content-Disposition"].startswith("attachment")
    assert resp["Content-Type"] == "application/octet-stream"
    assert Message.objects.get().media.name.endswith(".bin")


def test_safe_image_opens_inline(client_in):
    resp = client_in.get(saved_file("image/jpeg", "a.jpg"))
    assert resp["Content-Type"] == "image/jpeg" and not resp["Content-Disposition"].startswith("attachment")


def test_media_view_requires_login_and_file(client, client_in):
    connected()
    services.record(Peer(10, 5, "Ali"), [item()])
    assert client_in.get(reverse("telegram_media", args=[Message.objects.get().pk])).status_code == 404
    client_in.logout()
    assert client.get(reverse("telegram_media", args=[1])).status_code == 302


def job_runner():
    fake = FakeClient()
    return fake, runner_with(fake)


def test_reply_is_sent_and_quoted(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4, "Asl xabar")])
    client_in.post(reverse("telegram_send", args=[dialog.pk]), {"text": "Javob", "reply_to": "4"}, **HX)
    fake, runner = job_runner()
    async_to_sync(runner.flush_outbox)()
    assert fake.sent[0][2]["reply_to"] == 4
    message = Message.objects.get(text="Javob")
    assert message.reply_to_id == 4
    assert "tg-quote" in client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()


def test_file_upload_is_sent_with_name_and_removed(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    upload = SimpleUploadedFile("chek.pdf", b"PDF")
    resp = client_in.post(reverse("telegram_send", args=[dialog.pk]), {"text": "Mana", "file": upload}, **HX)
    assert resp.status_code == 204
    row = Outbox.objects.get()
    storage, name = row.file.storage, row.file.name
    assert name.endswith(".bin") and row.file_name == "chek.pdf"
    fake, runner = job_runner()
    async_to_sync(runner.flush_outbox)()
    buffer, kwargs = fake.sent[0][1], fake.sent[0][2]
    assert buffer.name == "chek.pdf" and buffer.read() == b"PDF" and kwargs["caption"] == "Mana"
    row.refresh_from_db()
    assert row.status == "sent" and not storage.exists(name)


def test_multiline_text_uses_unix_newlines(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    client_in.post(reverse("telegram_send", args=[dialog.pk]), {"text": "bir\r\nikki"}, **HX)
    assert Outbox.objects.get().text == "bir\nikki"


def test_last_label_shows_time_today_and_date_before(db):
    today = services.record(Peer(10, 5, "Ali"), [item()])
    old = services.record(Peer(11, 5, "Vali"), [item(date=timezone.now() - timedelta(days=3))])
    assert ":" in today.last_label and "." in old.last_label


def test_too_big_upload_rejected(client_in, settings):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    with mock.patch("apps.userbot.forms.MAX_UPLOAD", 2):
        resp = client_in.post(
            reverse("telegram_send", args=[dialog.pk]), {"file": SimpleUploadedFile("a.bin", b"123")}, **HX
        )
    assert resp.status_code == 422 and not Outbox.objects.exists()


def test_edit_own_message(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4, "Xato", outgoing=True), item(5, "Begona")])
    url = reverse("telegram_send", args=[dialog.pk])
    assert client_in.post(url, {"text": "Yangi", "edit_id": "5"}, **HX).status_code == 404
    assert client_in.post(url, {"text": "Yangi", "edit_id": "4"}, **HX).status_code == 204
    fake, runner = job_runner()
    async_to_sync(runner.flush_outbox)()
    assert fake.calls == [("edit", 4, "Yangi")]
    message = Message.objects.get(tg_id=4)
    assert message.text == "Yangi" and message.edited


def test_delete_message_for_both_sides(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4, "Birinchi"), item(5, "Ikkinchi")])
    url = reverse("telegram_delete", args=[dialog.pk])
    assert client_in.post(url, {"id": "999"}, **HX).status_code == 404
    assert client_in.post(url, {"id": "abc"}, **HX).status_code == 404
    client_in.post(url, {"id": "5"}, **HX)
    fake, runner = job_runner()
    async_to_sync(runner.flush_outbox)()
    assert fake.calls == [("delete", [5], True)]
    dialog.refresh_from_db()
    message = Message.objects.get(tg_id=5)
    assert message.deleted_at and message.deleted_by_me and dialog.last_text == "Birinchi"
    assert client_in.post(url, {"id": "5"}, **HX).status_code == 404


def test_opening_chat_marks_read_on_telegram(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4)])
    client_in.get(reverse("telegram_chat", args=[dialog.pk]))
    client_in.get(reverse("telegram_chat", args=[dialog.pk]))
    assert Outbox.objects.filter(kind="read").count() == 1
    fake, runner = job_runner()
    async_to_sync(runner.flush_outbox)()
    assert fake.calls == [("read", 4)]


def test_load_older_history(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(50, "Yangi")])
    resp = client_in.post(reverse("telegram_older", args=[dialog.pk]) + "?n=100")
    assert resp.url.endswith("?n=200")
    fake, runner = job_runner()
    old = SimpleNamespace(**{**vars(tg_message(49, "Eski")), "date": timezone.now() - timedelta(days=9)})
    fake.history = {10: [old, tg_message(50, "Yangi")]}
    async_to_sync(runner.flush_outbox)()
    dialog.refresh_from_db()
    assert Message.objects.filter(text="Eski").exists() and dialog.last_text == "Yangi" and dialog.unread == 1


def test_open_chat_by_username(client_in):
    connected()
    assert client_in.post(reverse("telegram_open"), {"username": "x y"}, **HX).status_code == 422
    client_in.post(reverse("telegram_open"), {"username": "@ali_valiyev"}, **HX)
    client_in.post(reverse("telegram_open"), {"username": "yoq_odam"}, **HX)
    fake, runner = job_runner()
    fake.entities["ali_valiyev"] = user(10, username="ali_valiyev")
    with mock.patch("apps.userbot.runner.SEND_GAP", 0):
        async_to_sync(runner.flush_outbox)()
    assert Dialog.objects.get().username == "ali_valiyev"
    assert Outbox.objects.get(text="yoq_odam").status == "failed"
    assert "yoq_odam" in Account.load().last_error


def test_open_chat_rejects_bot(db):
    connected()
    services.enqueue(None, "some_bot", kind="open")
    fake, runner = job_runner()
    fake.entities["some_bot"] = user(10, bot=True)
    async_to_sync(runner.flush_outbox)()
    assert not Dialog.objects.exists() and Outbox.objects.get().status == "failed"


def test_failed_message_can_be_dismissed(client_in):
    connected()
    row = services.enqueue(services.record(Peer(10, 5, "Ali"), [item()]), "Javob")
    assert client_in.post(reverse("telegram_dismiss", args=[row.pk]), **HX).status_code == 404
    services.mark_failed(row.pk, "xato")
    assert client_in.post(reverse("telegram_dismiss", args=[row.pk]), **HX).status_code == 204
    assert not Outbox.objects.exists()


def test_edit_event_updates_known_message_only(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(4, "Eski")])
    runner = runner_with(FakeClient())
    async_to_sync(runner.on_edit)(SimpleNamespace(is_private=True, chat_id=10, message=tg_message(4, "Yangi")))
    async_to_sync(runner.on_edit)(SimpleNamespace(is_private=True, chat_id=777000, message=tg_message(9, "Kod 12345")))
    assert list(Message.objects.values_list("text", "edited")) == [("Yangi", True)]


def test_delete_event_ignores_channels(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(4)])
    runner = runner_with(FakeClient())
    async_to_sync(runner.on_delete)(SimpleNamespace(chat_id=-100123, deleted_ids=[4]))
    assert not Message.objects.get().deleted_at
    async_to_sync(runner.on_delete)(SimpleNamespace(chat_id=None, deleted_ids=[4]))
    message = Message.objects.get()
    assert message.deleted_at and not message.deleted_by_me


def test_read_events_show_ticks_and_clear_unread(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4), item(5, "Javob", outgoing=True)])
    runner = runner_with(FakeClient())
    async_to_sync(runner.on_read)(SimpleNamespace(outbox=True, chat_id=10, max_id=5))
    async_to_sync(runner.on_read)(SimpleNamespace(outbox=False, chat_id=10, max_id=4))
    dialog.refresh_from_db()
    assert dialog.read_outbox_id == 5 and dialog.unread == 0
    assert "tg-read" in client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()


def test_online_typing_and_last_seen(db):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    runner = runner_with(FakeClient())
    soon = timezone.now() + timedelta(minutes=5)
    async_to_sync(runner.on_user)(SimpleNamespace(user_id=10, status=UserStatusOnline(expires=soon), typing=None))
    dialog.refresh_from_db()
    assert dialog.is_online and dialog.status_label == "online"
    async_to_sync(runner.on_user)(SimpleNamespace(user_id=10, status=None, typing=True))
    dialog.refresh_from_db()
    assert dialog.status_label == "yozmoqda…"
    services.update_state(10, typing_until=None, **seen_fields(UserStatusOffline(was_online=timezone.now())))
    dialog.refresh_from_db()
    assert not dialog.is_online and "ko'rilgan" in dialog.status_label


def test_chat_keeps_html_out_of_data_attributes(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4, '"><img src=x onerror=alert(1)>')])
    html = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    assert "<img src=x" not in html


def test_pinned_dialog_first(db):
    services.record(Peer(10, 5, "Eski"), [item(1, date=timezone.now() - timedelta(days=5))])
    services.record(Peer(11, 5, "Yangi"), [item(1)])
    services.update_state(10, pinned=True)
    assert Dialog.objects.first().name == "Eski"


@pytest.mark.parametrize(
    ("number", "words"),
    [
        (0, "nol"),
        (15, "o'n besh"),
        (100, "yuz"),
        (250, "ikki yuz ellik"),
        (500_000, "besh yuz ming"),
        (1_500_000, "bir million besh yuz ming"),
        (2_030_007, "ikki million o'ttiz ming yetti"),
    ],
)
def test_number_words(number, words):
    assert voice.number_words(number) == words


@pytest.mark.parametrize(
    ("day", "text"),
    [(1, "birinchi"), (10, "o'ninchi"), (15, "o'n beshinchi"), (20, "yigirmanchi"), (23, "yigirma uchinchi")],
)
def test_date_words(day, text):
    assert voice.date_words(date(2026, 11, day)) == f"{text} noyabr"


def owed(**extra):
    contact = Contact.objects.create(name="Ali Valiyev", telegram="@ali")
    connected(tg_name="Iftixor")
    fields = {"person": "Ali", "contact": contact, "amount": 700000, "paid_amount": 200000, "reason": "sayt"}
    debt = Debt.objects.create(**{**fields, **extra})
    return debt, services.record(Peer(10, 5, "Ali", username="ali"), [item()])


def test_reminder_text_is_polite_and_says_automatic(db):
    debt, _ = owed(due_date=timezone.localdate() - timedelta(days=2))
    text = voice.reminder_text(debt, "Iftixor")
    assert "Ali Valiyev" in text and "avtomatik" in text and "besh yuz ming so'm" in text and " edi." in text


def test_debt_reminder_flow_once_per_day(client_in):
    debt, dialog = owed()
    url = reverse("telegram_debt_remind", args=[debt.pk])
    html = client_in.get(url, **HX).content.decode()
    assert "avtomatik" in html and "Eshitib" in html
    data = {"text": "Eslatma matni", "voice": "uz-UZ-SardorNeural", "speed": "slow"}
    assert client_in.post(url, data, **HX).status_code == 204
    row = Outbox.objects.get()
    assert (row.kind, row.dialog, row.debt, row.voice, row.speed) == (
        "voice",
        dialog,
        debt,
        "uz-UZ-SardorNeural",
        "slow",
    )
    assert client_in.get(url, **HX).status_code == 422
    client_in.post(url, data, **HX)
    assert Outbox.objects.count() == 1


def test_failed_reminder_can_be_retried_same_day(client_in):
    debt, _ = owed()
    url = reverse("telegram_debt_remind", args=[debt.pk])
    client_in.post(url, {"text": "x", "voice": "uz-UZ-MadinaNeural", "speed": "normal"}, **HX)
    services.mark_failed(Outbox.objects.get().pk, "xato")
    assert client_in.get(url, **HX).status_code == 200


@pytest.mark.parametrize("extra", [{"is_closed": True}, {"contact": None}])
def test_reminder_refused_without_open_chat(client_in, extra):
    debt, _ = owed(**extra)
    assert client_in.get(reverse("telegram_debt_remind", args=[debt.pk]), **HX).status_code == 422


def test_reminder_never_for_my_own_debt(client_in):
    debt, _ = owed(direction="i_owe")
    assert client_in.get(reverse("telegram_debt_remind", args=[debt.pk]), **HX).status_code == 404


def test_debt_page_shows_button_only_with_chat(client_in):
    debt, _ = owed()
    assert reverse("telegram_debt_remind", args=[debt.pk]) in client_in.get(reverse("debt_list")).content.decode()
    Dialog.objects.all().delete()
    assert reverse("telegram_debt_remind", args=[debt.pk]) not in client_in.get(reverse("debt_list")).content.decode()


def test_chat_voice_button_enqueues_with_account_voice(client_in):
    connected(voice="uz-UZ-SardorNeural")
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    url = reverse("telegram_send", args=[dialog.pk])
    assert client_in.post(url, {"text": "x" * 1001, "as_voice": "on"}, **HX).status_code == 422
    assert client_in.post(url, {"text": "Salom", "as_voice": "on"}, **HX).status_code == 204
    row = Outbox.objects.get()
    assert (row.kind, row.voice) == ("voice", "uz-UZ-SardorNeural")


def test_voice_is_sent_as_voice_note(db):
    connected()
    row = services.enqueue(
        services.record(Peer(10, 5, "Ali"), [item()]), "Salom", kind="voice", voice="uz-UZ-MadinaNeural"
    )
    fake, runner = job_runner()

    async def speak(text, name, speed):
        return voice.Speech(b"m" * 60_000, 10)

    with mock.patch("apps.userbot.voice.synthesize", speak):
        async_to_sync(runner.flush_outbox)()
    buffer, kwargs = fake.sent[0][1], fake.sent[0][2]
    assert buffer.name == "voice.mp3" and kwargs["voice_note"] and kwargs["attributes"][0].duration == 10
    row.refresh_from_db()
    assert row.status == "sent"


def test_voice_service_failure_marks_message_failed(db):
    connected()
    row = services.enqueue(services.record(Peer(10, 5, "Ali"), [item()]), "Salom", kind="voice")
    fake, runner = job_runner()
    with mock.patch("apps.userbot.voice.synthesize", side_effect=voice.VoiceError("Ovoz yaratilmadi.")):
        async_to_sync(runner.flush_outbox)()
    row.refresh_from_db()
    assert row.status == "failed" and "Ovoz" in row.error and not fake.sent


def test_preview_returns_audio(client_in):
    async def speak(text, name, speed):
        return voice.Speech(b"mp3", 1)

    with mock.patch("apps.userbot.voice.synthesize", speak):
        data = {"text": "Salom", "voice": "uz-UZ-MadinaNeural", "speed": "normal"}
        html = client_in.post(reverse("telegram_voice_preview"), data, **HX).content.decode()
    assert "data:audio/mpeg;base64,bXAz" in html


def test_sentences_get_silent_mp3_frames_between(settings):
    frame = b"\xff\xf3\x64\xc4" + bytes(140)

    class Fake:
        def __init__(self, sentence, name, rate, boundary):
            self.rate = rate

        async def stream(self):
            yield {"type": "audio", "data": frame * 10}

    with mock.patch("edge_tts.Communicate", Fake):
        speech = async_to_sync(voice.synthesize)(
            "Birinchi gap. Ikkinchi gap! Uchinchi?", "uz-UZ-MadinaNeural", "normal"
        )
    assert (
        len(speech.data) == 144 * (30 + 2 * voice.PAUSE_FRAMES)
        and speech.data.count(frame) == 30 + 2 * voice.PAUSE_FRAMES
    )


def test_slow_speed_reaches_edge():
    seen = []

    class Fake:
        def __init__(self, sentence, name, rate, boundary):
            seen.append(rate)

        async def stream(self):
            yield {"type": "audio", "data": b"x"}

    with mock.patch("edge_tts.Communicate", Fake):
        async_to_sync(voice.synthesize)("Gap.", "uz-UZ-SardorNeural", "slow")
    assert seen == ["-20%"]


def test_trim_cuts_edge_silence_on_frame_boundaries():
    data = bytes(range(100)) * 144  # 100 kadr
    ticks = voice.FRAME_TICKS
    kept = voice.trim(data, 20 * ticks, 50 * ticks)
    assert kept == data[17 * 144 : 55 * 144] and len(kept) % 144 == 0
    assert voice.trim(data, 0, 99 * ticks) == data


def test_reminder_sentence_starts_with_capital(db):
    debt, _ = owed(reason="sayt to'lovi")
    assert "Sayt to'lovi bo'yicha" in voice.reminder_text(debt)


def test_aisha_hidden_without_key(settings):
    assert not any(v.startswith("aisha") for v, _ in voice.voice_choices())
    settings.AISHA_API_KEY = "k"
    assert any(v == "aisha:Gulnoza" for v, _ in voice.voice_choices())


def test_aisha_voice_without_key_fails_clearly():
    with pytest.raises(voice.VoiceError):
        async_to_sync(voice.synthesize)("Salom", "aisha:Gulnoza", "normal")


def wav_bytes(seconds=1, rate=22050):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(bytes(2 * rate * seconds))
    return buffer.getvalue()


def test_wav_becomes_mp3():
    speech = voice.wav_to_mp3(wav_bytes(3))
    assert speech.seconds == 3 and speech.data[:2] in (b"\xff\xfb", b"\xff\xf3", b"ID")


def test_bad_wav_is_clear_error():
    with pytest.raises(voice.VoiceError):
        voice.wav_to_mp3(b"not audio")


def edit_of(tg_id, text):
    return SimpleNamespace(**{**vars(tg_message(tg_id, text)), "edit_date": timezone.now()})


def test_deleted_message_stays_with_mark_and_media(client_in):
    connected()
    dialog = services.record(
        Peer(10, 5, "Ali"), [Item(4, False, "[Rasm]", timezone.now(), True, "photo", "image/jpeg")]
    )
    services.save_media(Message.objects.get().pk, b"rasm")
    services.mark_deleted([4])
    html = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    thread = html.split('id="tg-thread"')[1]
    assert "o&#x27;chirilgan" in thread or "o'chirilgan" in thread
    assert "is-deleted" in thread and reverse("telegram_media", args=[Message.objects.get().pk]) in thread
    assert 'aria-label="Javob berish"' not in thread and Message.objects.get().media.read() == b"rasm"


def test_chat_wiped_keeps_dialog_and_all_messages(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1, "Bir"), item(2, "Ikki")])
    services.mark_deleted([1, 2])
    dialog = Dialog.objects.get()
    assert dialog.messages.count() == 2 and dialog.last_text == "Xabarlar o'chirilgan" and dialog.last_message_at


def test_resync_does_not_undelete(db):
    connected()
    peer = Peer(10, 5, "Ali")
    services.record(peer, [item(1, "Bir")])
    services.mark_deleted([1])
    services.record(peer, [item(1, "Bir")])
    assert Message.objects.get().deleted_at


def test_edit_keeps_every_old_text(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4, "Birinchi")])
    services.apply_edit(10, 4, "Ikkinchi")
    services.apply_edit(10, 4, "Ikkinchi")
    services.apply_edit(10, 4, "<b>Uchinchi</b>")
    message = Message.objects.get()
    assert list(message.edits.values_list("text", flat=True)) == ["Birinchi", "Ikkinchi"]
    thread = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode().split('id="tg-thread"')[1]
    assert "Oldingi matn (2)" in thread and "Birinchi" in thread and "<b>Uchinchi" not in thread


def test_deleted_message_cannot_be_edited(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item(4, "Matn", outgoing=True)])
    services.mark_deleted([4], by_me=True)
    url = reverse("telegram_send", args=[dialog.pk])
    assert client_in.post(url, {"text": "x", "edit_id": "4"}, **HX).status_code == 404


def test_reconcile_uses_ids_not_positions(db):
    """Telegram o'chganini tashlab yuborsa, qolganlari siljiydi: yolg'on belgi qo'yilmasligi kerak."""
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1, "Bir"), item(2, "Ikki"), item(3, "Uch")])
    fake = FakeClient()
    fake.remote = {1: tg_message(1, "Bir"), 3: tg_message(3, "Uch")}
    async_to_sync(runner_with(fake).reconcile)()
    assert list(Message.objects.exclude(deleted_at=None).values_list("tg_id", flat=True)) == [2]


def test_reconcile_finds_offline_edit_without_notifying(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1, "Eski")])
    fake = FakeClient()
    fake.remote = {1: edit_of(1, "Yangi")}
    with mock.patch("apps.userbot.services.send_message") as send:
        async_to_sync(runner_with(fake).reconcile)()
    assert Message.objects.get().text == "Yangi" and Message.objects.get().edits.count() == 1 and not send.called


def test_reconcile_same_text_without_edit_date_is_not_edit(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1, "Matn")])
    fake = FakeClient()
    fake.remote = {1: tg_message(1, "Boshqa ko'rinish")}
    async_to_sync(runner_with(fake).reconcile)()
    assert Message.objects.get().text == "Matn"


def test_reconcile_distrusts_empty_answer_when_chat_has_messages(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(5, "Bir"), item(6, "Ikki")])
    fake = FakeClient()
    fake.latest = [tg_message(9, "Yangi")]
    async_to_sync(runner_with(fake).reconcile)()
    assert not Message.objects.exclude(deleted_at=None).exists()


def test_reconcile_marks_wiped_chat(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(5, "Bir"), item(6, "Ikki")])
    async_to_sync(runner_with(FakeClient()).reconcile)()
    assert Message.objects.exclude(deleted_at=None).count() == 2


def test_reconcile_runs_only_every_15_minutes(db):
    connected()
    assert services.needs_reconcile()
    services.reconciled()
    assert not services.needs_reconcile()
    Account.objects.update(reconciled_at=timezone.now() - timedelta(minutes=16))
    assert services.needs_reconcile()


def test_incoming_change_notifies_owner_escaped(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1, "<i>Sir</i>"), item(2, "Mening", outgoing=True)])
    with mock.patch("apps.userbot.services.send_message") as send:
        services.mark_deleted([1, 2])
    text = send.call_args.args[0]
    assert "1 ta xabar" in text and "&lt;i&gt;" in text and "Mening" not in text


def test_own_delete_and_disabled_option_do_not_notify(db):
    connected(notify_changes=False)
    services.record(Peer(10, 5, "Ali"), [item(1, "Bir"), item(2, "Ikki")])
    with mock.patch("apps.userbot.services.send_message") as send:
        services.mark_deleted([1])
        Account.objects.update(notify_changes=True)
        services.mark_deleted([2], by_me=True)
    assert not send.called


def test_peek_shows_unread_without_reading(client_in):
    connected()
    items = [item(1, "Eski"), item(2, "Javobim", outgoing=True), item(3, "Birinchi yangi"), item(4, "<b>Ikkinchi</b>")]
    dialog = services.record(Peer(10, 5, "Ali"), items, unread=2)
    html = client_in.get(reverse("telegram_peek", args=[dialog.pk]), **HX).content.decode()
    assert "Birinchi yangi" in html and "&lt;b&gt;Ikkinchi" in html
    assert "Eski" not in html and "Javobim" not in html
    assert html.index("Birinchi yangi") < html.index("Ikkinchi")
    dialog.refresh_from_db()
    assert dialog.unread == 2 and not Outbox.objects.exists()


def test_peek_button_only_for_unread(client_in):
    connected()
    unread = services.record(Peer(10, 5, "Ali"), [item(1)])
    read = services.record(Peer(11, 5, "Vali"), [item(2)], unread=0)
    html = client_in.get(reverse("telegram_home")).content.decode()
    assert reverse("telegram_peek", args=[unread.pk]) in html
    assert reverse("telegram_peek", args=[read.pk]) not in html


def test_menu_shows_unread_total_on_every_page(client_in):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1), item(2)])
    services.record(Peer(11, 5, "Vali"), [item(3)])
    html = client_in.get(reverse("dashboard")).content.decode()
    assert '<span class="nav-badge">3</span>' in html and "nav-badge-dot" in html


def test_menu_has_no_badge_without_unread_or_account(client_in):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1)], unread=0)
    Dialog.objects.update(unread=0)
    assert 'class="nav-badge"' not in client_in.get(reverse("dashboard")).content.decode()
    Dialog.objects.update(unread=4)
    Account.objects.update(status="off")
    assert 'class="nav-badge"' not in client_in.get(reverse("dashboard")).content.decode()


def test_badge_caps_at_99(client_in):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1)])
    Dialog.objects.update(unread=150)
    assert ">99+<" in client_in.get(reverse("telegram_unread"), **HX).content.decode()


def test_badge_endpoint_keeps_polling_and_dot_variant(client_in):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(1)])
    plain = client_in.get(reverse("telegram_unread"), **HX).content.decode()
    dot = client_in.get(reverse("telegram_unread") + "?dot=1", **HX).content.decode()
    assert "every 10s" in plain and ">1<" in plain
    assert "nav-badge-dot" in dot and "dot=1" in dot


def test_badge_stops_quietly_when_session_ends(client, db):
    resp = client.get(reverse("telegram_unread"), **HX)
    assert resp.status_code == 200 and "hx-get" not in resp.content.decode()
    assert "password" not in resp.content.decode()


def test_heartbeat_is_sent_during_long_first_sync(db):
    connected()
    dialogs = [tg_dialog(user(10)), tg_dialog(user(11)), tg_dialog(user(12))]
    with mock.patch("apps.userbot.services.tick", wraps=services.tick) as tick:
        async_to_sync(runner_with(FakeClient(dialogs)).sync)()
    assert tick.call_count >= 3 and Account.load().runner_alive


def test_runner_exits_when_deploy_touches_restart_file(db, settings, tmp_path):
    connected()
    (tmp_path / "tmp").mkdir()
    stamp = tmp_path / "tmp" / "restart.txt"
    stamp.write_text("")
    settings.BASE_DIR = tmp_path
    calls = []

    class Client:
        def __init__(self, *args):
            calls.append(1)

        async def connect(self):
            os.utime(stamp, (1, 1))  # deploy shu payt bo'ldi

        async def disconnect(self):
            calls.append("disconnected")

        async def is_user_authorized(self):
            return True

        async def get_me(self):
            return SimpleNamespace(id=1)

        def add_event_handler(self, *args):
            pass

        def iter_dialogs(self, limit):
            return agen([])

        def iter_messages(self, entity, limit, min_id=0):
            return agen([])

    async_to_sync(Runner(Client).run)()  # chiqmasa test osilib qoladi
    assert "disconnected" in calls and Account.load().is_connected


def test_missing_restart_file_is_safe(settings, tmp_path):
    settings.BASE_DIR = tmp_path
    assert restart_stamp() == 0.0
    Runner().check_restart()


def test_wide_mode_controls_on_list_and_chat(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    home = client_in.get(reverse("telegram_home")).content.decode()
    chat = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    assert home.count('aria-label="Kengaytirish"') == 1 and chat.count('aria-label="Kengaytirish"') == 1
    assert "tg-resizer" in home


def test_awaiting_reply_tracks_last_message(db):
    connected()
    peer = Peer(10, 5, "Ali")
    dialog = services.record(peer, [item(1, "Salom")])
    assert dialog.awaiting_reply
    dialog = services.record(peer, [item(2, "Javob", outgoing=True)])
    assert not dialog.awaiting_reply
    services.mark_deleted([2])
    dialog.refresh_from_db()
    assert dialog.awaiting_reply
    services.mark_deleted([1])
    dialog.refresh_from_db()
    assert not dialog.awaiting_reply


def test_task_from_message_links_contact(client_in):
    connected()
    contact = Contact.objects.create(name="Ali", telegram="@ali")
    dialog = services.record(Peer(10, 5, "Ali", username="ali"), [item(4, "Logoni o'zgartiring\nKo'kroq bo'lsin")])
    assert client_in.post(reverse("telegram_task", args=[dialog.pk]), {"id": "4"}, **HX).status_code == 204
    task = Task.objects.get()
    assert task.title == "Logoni o'zgartiring" and task.contact == contact and "Ko'kroq" in task.notes
    assert task.planned_for == timezone.localdate()


def test_task_from_media_message_has_title(client_in):
    connected()
    dialog = services.record(
        Peer(10, 5, "Ali"), [Item(4, False, "[Rasm]", timezone.now(), True, "photo", "image/jpeg")]
    )
    services.save_media(Message.objects.get().pk, b"rasm")
    client_in.post(reverse("telegram_task", args=[dialog.pk]), {"id": "4"}, **HX)
    assert Task.objects.get().title == "Telegram: Ali"
    assert client_in.post(reverse("telegram_task", args=[dialog.pk]), {"id": "x"}, **HX).status_code == 404


def test_quick_reply_crud_and_escaped_in_chat(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    data = {"title": "Narx", "text": 'Salom {ism}, <b>"narx"</b>'}
    assert client_in.post(reverse("telegram_reply_create"), data, **HX).status_code == 204
    reply = QuickReply.objects.get()
    html = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    assert "Salom {ism}" in html and '<b>"narx"' not in html
    assert client_in.get(reverse("telegram_reply_edit", args=[reply.pk]), **HX).status_code == 200
    client_in.post(reverse("telegram_reply_delete", args=[reply.pk]), **HX)
    assert not QuickReply.objects.exists()


def local_input(delta):
    return timezone.localtime(timezone.now() + delta).strftime("%Y-%m-%dT%H:%M")


def test_scheduled_message_waits_for_time(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    data = {"text": "Ertaga", "send_at": local_input(timedelta(hours=2))}
    assert client_in.post(reverse("telegram_send", args=[dialog.pk]), data, **HX).status_code == 204
    fake, runner = job_runner()
    async_to_sync(runner.flush_outbox)()
    row = Outbox.objects.get()
    assert not fake.sent and row.status == "pending"
    assert "da yuboriladi" in client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    Outbox.objects.update(send_at=timezone.now() - timedelta(minutes=1))
    async_to_sync(runner.flush_outbox)()
    row.refresh_from_db()
    assert fake.sent and row.status == "sent"


@pytest.mark.parametrize("delta", [timedelta(hours=-1), timedelta(days=400)])
def test_schedule_rejects_past_and_far_future(client_in, delta):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    data = {"text": "x", "send_at": local_input(delta)}
    assert client_in.post(reverse("telegram_send", args=[dialog.pk]), data, **HX).status_code == 422
    assert not Outbox.objects.exists()


def test_scheduled_can_be_cancelled_but_not_immediate(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [item()])
    now_row = services.enqueue(dialog, "Darhol")
    later = services.enqueue(dialog, "Keyin", send_at=timezone.now() + timedelta(hours=1))
    assert client_in.post(reverse("telegram_dismiss", args=[now_row.pk]), **HX).status_code == 404
    assert client_in.post(reverse("telegram_dismiss", args=[later.pk]), **HX).status_code == 204
    assert list(Outbox.objects.values_list("text", flat=True)) == ["Darhol"]


def test_search_finds_messages_including_deleted(client_in):
    connected()
    services.record(Peer(10, 5, "Ali"), [item(4, "Shartnoma tayyor"), item(5, "Boshqa gap")])
    services.mark_deleted([4])
    url = reverse("telegram_search")
    html = client_in.get(url, {"q": "shartnoma"}, **HX).content.decode()
    assert "Shartnoma tayyor" in html and "at=4" in html and "Boshqa" not in html
    assert "Shartnoma" not in client_in.get(url, {"q": "s"}, **HX).content.decode()
    assert "<script" not in client_in.get(url, {"q": "<script>"}, **HX).content.decode()


def test_activity_model_untouched_by_outgoing(db):
    connected()
    Contact.objects.create(name="Ali", telegram="@ali")
    services.record(Peer(10, 5, "Ali", username="ali"), [item(1, outgoing=True)])
    assert not Activity.objects.exists()
