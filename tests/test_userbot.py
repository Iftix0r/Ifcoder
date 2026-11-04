"""Telegram userbot: ulanish oqimi, suhbatlar, navbat va buyruqlar (Telegram'ga haqiqiy ulanishsiz)."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse
from django.utils import timezone
from telethon import errors
from telethon.tl.types import MessageMediaPhoto, MessageMediaWebPage, Photo, WebPageEmpty

from apps.crm.models import Activity, Contact
from apps.finance.models import Transaction
from apps.notes.models import Note
from apps.planner.models import Task
from apps.userbot import client as tg
from apps.userbot import commands, services
from apps.userbot.models import Account, Dialog, Message, Outbox
from apps.userbot.runner import Runner, to_item
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
    assert client_in.post(url, {"text": "   "}, **HX).status_code == 204
    assert client_in.post(url, {"text": "x" * 4097}, **HX).status_code == 204
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
        client_in.post(reverse("telegram_options"), {"log_to_crm": "on"}, **HX)
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
    }
    return SimpleNamespace(**{**base, **extra})


def tg_message(id, text="Salom", out=False):
    return SimpleNamespace(id=id, message=text, out=out, date=timezone.now(), media=None, action=None)


def tg_dialog(entity, *, is_user=True, unread=1):
    return SimpleNamespace(is_user=is_user, entity=entity, unread_count=unread, date=timezone.now())


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

    async def get_messages(self, peer, ids):
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

    def iter_messages(self, entity, limit, min_id=0):
        messages = self.saved if entity == "me" else self.history.get(entity.id, [])
        return agen(sorted((m for m in messages if m.id > min_id), key=lambda m: -m.id)[:limit])

    async def send_message(self, peer, text, **kwargs):
        if self.send_error:
            raise self.send_error
        self.sent.append((peer, text, kwargs))
        return SimpleNamespace(id=900 + len(self.sent), date=timezone.now())


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
    assert to_item(photo).text == "[Rasm]" and to_item(photo).has_photo
    assert to_item(SimpleNamespace(**{**vars(tg_message(2)), "action": object()})) is None


def photo_media(ttl=None):
    photo = Photo(id=1, access_hash=1, file_reference=b"", date=timezone.now(), sizes=[], dc_id=2)
    return MessageMediaPhoto(photo=photo, ttl_seconds=ttl)


def with_media(message, media, **extra):
    return SimpleNamespace(**{**vars(message), "media": media, **extra})


def test_view_once_and_link_preview_not_downloaded():
    once = with_media(tg_message(1, ""), photo_media(ttl=10), photo=object())
    assert to_item(once).text == "[Rasm]" and not to_item(once).has_photo
    preview = with_media(tg_message(2, "https://x.uz"), MessageMediaWebPage(webpage=WebPageEmpty(id=1)))
    assert not to_item(preview).has_photo


def test_image_downloaded_and_shown(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True)])
    fake = FakeClient()
    fake.remote[7] = tg_message(7, "")
    async_to_sync(runner_with(fake).fetch_media)()
    message = Message.objects.get()
    assert message.image.read() == b"rasm"
    html = client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()
    assert message.image.url in html and "[Rasm]" not in html


def test_image_caption_stays_visible(client_in):
    connected()
    dialog = services.record(Peer(10, 5, "Ali"), [Item(7, False, "Mana chek", timezone.now(), True)])
    services.save_image(Message.objects.get().pk, b"rasm")
    assert "Mana chek" in client_in.get(reverse("telegram_chat", args=[dialog.pk])).content.decode()


def test_deleted_message_leaves_image_queue(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True)])
    async_to_sync(runner_with(FakeClient()).fetch_media)()
    assert not services.pending_images()


def test_image_flood_wait_keeps_queue_and_pauses(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True)])
    fake = FakeClient()
    fake.remote[7] = tg_message(7, "")
    fake.download_error = errors.FloodWaitError(request=None, capture=100)
    runner = runner_with(fake)
    async_to_sync(runner.fetch_media)()
    assert services.pending_images() and runner.pause_media_until > 0


def test_revoked_during_image_download_is_raised(db):
    connected()
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True)])
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

    services.set_photo_id(10, 88)
    async_to_sync(runner.fetch_media)()
    dialog.refresh_from_db()
    assert fake.avatar_calls == 2 and "88" in dialog.avatar.name

    services.set_photo_id(10, 0)
    async_to_sync(runner.fetch_media)()
    dialog.refresh_from_db()
    assert not dialog.avatar and fake.avatar_calls == 2


def test_sent_message_keeps_photo_id(db):
    row = services.enqueue(services.record(Peer(10, 5, "Ali", photo_id=77), [item()]), "Javob")
    services.mark_sent(row.pk, 50, timezone.now())
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
    services.record(Peer(10, 5, "Ali"), [Item(7, False, "[Rasm]", timezone.now(), True)])
    services.save_image(Message.objects.get().pk, b"rasm")
    storage, name = Message.objects.get().image.storage, Message.objects.get().image.name
    services.finish_login(account, "new", tg.Me(id=2, name="Boshqa", username=""))
    assert not storage.exists(name)


def test_media_requires_login(client, db):
    assert client.get("/media/telegram/photos/1-1.jpg").status_code == 302


def test_activity_model_untouched_by_outgoing(db):
    connected()
    Contact.objects.create(name="Ali", telegram="@ali")
    services.record(Peer(10, 5, "Ali", username="ali"), [item(1, outgoing=True)])
    assert not Activity.objects.exists()
