"""Xavfsizlik jurnali: kirish, sessiya, skaner va log tekshiruvi."""

from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.security import services
from apps.security.models import Event, ScanState, SessionRecord, TrustedIP

PASSWORD = "Parol-2026!"
LOGIN = {"username": "iftixor", "password": PASSWORD}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()


@pytest.fixture
def alerts():
    with mock.patch("apps.core.telegram.send_message_async") as send:
        yield send


def login(client, ip="1.2.3.4", data=None, **extra):
    return client.post(reverse("login"), data or LOGIN, REMOTE_ADDR=ip, **extra)


def test_new_ip_login_alerts_once(client, user, alerts):
    login(client)
    client.logout()
    login(client)
    assert Event.objects.filter(kind="login_ok", ip="1.2.3.4").count() == 2
    assert alerts.call_count == 1 and "1.2.3.4" in alerts.call_args.args[0]


def test_trusted_prefix_is_quiet(client, user, alerts):
    TrustedIP.objects.create(ip="1.2.")
    login(client)
    assert not alerts.called


def test_failed_login_recorded_and_alerts_at_threshold(client, user, alerts):
    for _ in range(5):
        login(client, data={"username": "iftixor", "password": "xato"})
    assert Event.objects.filter(kind="login_fail").count() == 5
    assert alerts.call_count == 1 and "5 ta" in alerts.call_args.args[0]


def test_forged_forwarded_header_cannot_bypass_lock(client, user):
    for number in range(6):
        login(client, data={"username": "iftixor", "password": "xato"}, HTTP_X_FORWARDED_FOR=f"9.9.9.{number}")
    resp = login(client, HTTP_X_FORWARDED_FOR="9.9.9.99")
    assert "Juda ko" in resp.content.decode() and not Event.objects.filter(kind="login_ok").exists()
    assert not Event.objects.filter(ip__startswith="9.9.9").exists()


def test_session_hash_only_never_raw_key(client_in, db):
    client_in.get(reverse("dashboard"))
    key = client_in.session.session_key
    row = SessionRecord.objects.get()
    assert row.key_hash == services.key_hash(key) and key not in row.key_hash


def test_session_used_from_new_ip_alerts(client_in, alerts):
    client_in.get(reverse("dashboard"), REMOTE_ADDR="1.1.1.1")
    client_in.get(reverse("dashboard"), REMOTE_ADDR="6.6.6.6")
    assert Event.objects.filter(kind="new_ip", ip="6.6.6.6").exists()
    assert alerts.call_count == 1 and "6.6.6.6" in alerts.call_args.args[0]
    cache.clear()
    client_in.get(reverse("dashboard"), REMOTE_ADDR="1.1.1.1")
    cache.clear()
    client_in.get(reverse("dashboard"), REMOTE_ADDR="6.6.6.6")
    assert Event.objects.filter(kind="new_ip", ip="6.6.6.6").count() == 1


def test_trap_paths_logged_once_per_hour_without_alert(client, db, alerts):
    for path in ("/.env.backup", "/wp-login.php", "/.git/HEAD"):
        client.get(path, REMOTE_ADDR="5.5.5.5")
    assert Event.objects.filter(kind="trap", ip="5.5.5.5").count() == 1 and not alerts.called


def test_normal_pages_are_not_traps(client, db):
    client.get("/", REMOTE_ADDR="5.5.5.5")
    client.get("/accounts/login/", REMOTE_ADDR="5.5.5.5")
    assert not Event.objects.exists()


def test_panel_page_and_kill_other_session(client_in, user):
    other = Client()
    other.force_login(user)
    other.get(reverse("dashboard"), REMOTE_ADDR="7.7.7.7")
    client_in.get(reverse("security_home"), REMOTE_ADDR="1.1.1.1")
    html = client_in.get(reverse("security_home"), REMOTE_ADDR="1.1.1.1").content.decode()
    assert "7.7.7.7" in html and "Joriy" in html
    digest = services.key_hash(other.session.session_key)
    client_in.post(reverse("security_kill"), {"key": digest})
    assert other.get(reverse("dashboard")).status_code == 302
    assert Event.objects.filter(kind="killed").exists()


def test_current_session_cannot_be_killed_here(client_in):
    client_in.get(reverse("dashboard"))
    key = client_in.session.session_key
    client_in.post(reverse("security_kill"), {"key": services.key_hash(key)})
    assert Session.objects.filter(pk=key).exists()


def test_trust_validation_and_remove(client_in):
    client_in.post(reverse("security_trust"), {"ip": "<script>", "note": ""})
    assert not TrustedIP.objects.exists()
    client_in.post(reverse("security_trust"), {"ip": "84.54.", "note": "Uy"})
    row = TrustedIP.objects.get()
    client_in.post(reverse("security_untrust", args=[row.pk]))
    assert not TrustedIP.objects.exists()


def test_security_requires_login(client, db):
    assert client.get(reverse("security_home")).status_code == 302


LINE = '{ip} - - [04/Nov/2026:18:00:00 +0500] "{method} {path} HTTP/1.1" {status} {size} "-" "curl"\n'


def line(path, status=200, size=5000, method="GET", ip="8.8.8.8"):
    return LINE.format(ip=ip, path=path, status=status, size=size, method=method)


@pytest.mark.parametrize("path", ["/db.sqlite3", "/.env", "/.git/config", "/backups/a.sqlite3", "/x-firebase-y.json"])
def test_real_download_is_a_leak(path):
    assert services.parse_leak(line(path)) == ("8.8.8.8", path, 5000)


@pytest.mark.parametrize(
    "text",
    [
        line("/db.sqlite3", status=403),
        line("/db.sqlite3", status=404),
        line("/db.sqlite3", size=11866),  # himoya sahifasi
        line("/db.sqlite3", method="HEAD", size=0),
        line("/db.sqlite3", size="-"),
        line("/dashboard/"),
        line("/static/app.css"),
        "buzilgan qator\n",
    ],
)
def test_not_a_leak(text):
    assert services.parse_leak(text) is None


def scan_setup(settings, tmp_path, text=""):
    log = tmp_path / "site-ssl_log"
    log.write_text(text)
    settings.SECURITY_ACCESS_LOG = str(tmp_path / "site*")
    return log


def test_first_scan_sets_baseline_without_old_alerts(db, settings, tmp_path):
    scan_setup(settings, tmp_path, line("/db.sqlite3"))
    assert services.scan_log() == []
    assert ScanState.load().scanned_at


def test_scan_reads_only_new_lines_and_alerts(db, settings, tmp_path):
    log = scan_setup(settings, tmp_path, line("/db.sqlite3"))
    services.scan_log()
    with log.open("a") as handle:
        handle.write(line("/.env", size=439, ip="9.9.9.9"))
    with mock.patch("apps.core.telegram.send_message") as send:
        call_command("security_scan")
        call_command("security_scan")
    assert send.call_count == 1 and "9.9.9.9" in send.call_args.args[0]
    assert Event.objects.filter(kind="leak").count() == 1


def test_scan_handles_rotated_log_and_gz(db, settings, tmp_path):
    log = scan_setup(settings, tmp_path, line("/dashboard/") * 20)
    (tmp_path / "site-Oct.gz").write_bytes(b"x")
    services.scan_log()
    log.write_text(line("/.env"))
    assert len(services.scan_log()) == 1
    assert not any(path.endswith(".gz") for path in ScanState.load().offsets)


def test_scan_prunes_old_events(db, settings, tmp_path):
    scan_setup(settings, tmp_path)
    old = services.record("trap", "1.1.1.1")
    Event.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=100))
    services.scan_log()
    assert not Event.objects.exists()


def test_digest_mentions_only_when_something_happened(db):
    assert services.digest_lines() == []
    services.record("trap", "1.1.1.1")
    services.record("login_fail", "1.1.1.1")
    assert "1 ta skaner, 1 ta xato parol" in services.digest_lines()[1]
