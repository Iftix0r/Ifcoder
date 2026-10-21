from unittest import mock

from django.core.management import call_command
from django.test import override_settings

from apps.dashboard.digest import build_digest


def test_digest_renders(data):
    text = build_digest()
    assert "Bugungi reja" in text and "Login sahifasi" in text
    assert "Ali Valiyev" in text  # bugun bog'lanish kerak
    assert "<script" not in text


def test_digest_escapes_html(db):
    from django.utils import timezone

    from apps.planner.models import Task

    Task.objects.create(title="<b>x</b> & y", planned_for=timezone.localdate())
    assert "&lt;b&gt;x&lt;/b&gt; &amp; y" in build_digest()


@override_settings(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="1")
def test_lead_notifies_telegram(client, db):
    with mock.patch("apps.core.telegram.send_message") as send, mock.patch("threading.Thread") as thread:
        thread.side_effect = lambda target, args, daemon: mock.Mock(start=lambda: target(*args))
        client.post("/", {"name": "Bekzod", "phone": "@bekzod", "service": "bot", "message": "Bot kerak"})
    text = send.call_args.args[0]
    assert "Bekzod" in text and "@bekzod" in text


def test_lead_without_telegram_config_still_works(client, db):
    resp = client.post("/", {"name": "Ali", "phone": "+998901234567", "service": "web"})
    assert resp.status_code == 200


@override_settings(TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="1")
def test_daily_digest_command(data):
    with mock.patch("apps.core.telegram.send_message", return_value=True) as send:
        call_command("daily_digest")
    assert send.called
