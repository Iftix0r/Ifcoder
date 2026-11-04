import glob
import hashlib
import os
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.utils import timezone

from apps.core import telegram

from .models import Event, ScanState, SessionRecord, TrustedIP

FAIL_ALERT = 5
FAIL_WINDOW = timedelta(minutes=15)
NEW_IP_REPEAT = timedelta(hours=24)
TOUCH_SECONDS = 300
TRAP_SECONDS = 3600
KEEP_DAYS = 90

# Hech qachon so'ralmasligi kerak bo'lgan manzillar: buni faqat skaner yoki hujumchi ochadi
TRAP = re.compile(
    r"(^/\.env|/\.git(/|$)|\.sqlite3?$|wp-login|wp-admin|xmlrpc\.php|phpmyadmin|/backup\.|\.sql$|firebase.*\.json)",
    re.I,
)
SENSITIVE = re.compile(r"^/(\.env|db\.sqlite3|[^/]*firebase[^/]*\.json|backups/|logs/|\.git/|public/media/)", re.I)
LOG_LINE = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "(GET|HEAD|POST) (\S+) [^"]*" (\d{3}) (\S+)')
# Hosting «One moment, please» sahifasi: haqiqiy fayl emas
CHALLENGE_BYTES = range(11_000, 13_000)


def client_ip(request) -> str:
    """X-Forwarded-For ga ishonilmaydi: uni hujumchi o'zi yozadi. Saytdan oldin proksi yo'q."""
    return request.META.get("REMOTE_ADDR", "")


def agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:300]


def key_hash(session_key: str) -> str:
    return hashlib.sha256(session_key.encode()).hexdigest()


def is_trusted(ip: str) -> bool:
    return any(ip.startswith(row) for row in TrustedIP.objects.values_list("ip", flat=True))


def record(kind: str, ip: str = "", *, user_agent: str = "", path: str = "", username: str = "") -> Event:
    return Event.objects.create(kind=kind, ip=ip, user_agent=user_agent, path=path[:300], username=username[:150])


def _alert(text: str) -> None:
    telegram.send_message_async(f"{text}\n\n{settings.SITE_URL}/security/")


def on_login(request, user) -> None:
    ip = client_ip(request)
    seen = Event.objects.filter(kind=Event.Kind.LOGIN_OK, ip=ip).exists()
    record(Event.Kind.LOGIN_OK, ip, user_agent=agent(request), username=user.get_username())
    if not seen and not is_trusted(ip):
        name = telegram.h(user.get_username())
        _alert(
            f"🔐 <b>Yangi IP'dan kirish</b>\n{name} · <code>{telegram.h(ip)}</code>\n{telegram.h(agent(request)[:90])}"
        )


def on_login_failed(request, username: str) -> None:
    if request is None:
        return
    ip = client_ip(request)
    record(Event.Kind.LOGIN_FAIL, ip, user_agent=agent(request), username=username)
    since = timezone.now() - FAIL_WINDOW
    fails = Event.objects.filter(kind=Event.Kind.LOGIN_FAIL, ip=ip, created_at__gte=since).count()
    if fails == FAIL_ALERT and not is_trusted(ip):
        _alert(f"⚠️ <b>Parol terib ko'rilmoqda</b>\n<code>{telegram.h(ip)}</code>: {fails} ta xato urinish")


def note_trap(request) -> None:
    ip = client_ip(request)
    key = f"sec-trap:{ip}"
    if cache.add(key, 1, TRAP_SECONDS):  # skanerlar ko'p: IP'ga soatiga bitta yozuv
        record(Event.Kind.TRAP, ip, user_agent=agent(request), path=request.path)


def touch_session(request) -> None:
    session_key = request.session.session_key
    if not session_key:
        return
    ip, digest = client_ip(request), key_hash(session_key)
    if not cache.add(f"sec-seen:{digest}:{ip}", 1, TOUCH_SECONDS):
        return
    row = SessionRecord.objects.filter(key_hash=digest).first()
    if row is None:
        SessionRecord.objects.create(key_hash=digest, user=request.user, ip=ip, user_agent=agent(request))
        return
    moved = row.ip != ip
    row.ip, row.user_agent = ip, agent(request)
    row.save(update_fields=["ip", "user_agent", "last_seen"])
    if moved and not is_trusted(ip):
        since = timezone.now() - NEW_IP_REPEAT
        if not Event.objects.filter(kind=Event.Kind.NEW_IP, ip=ip, created_at__gte=since).exists():
            record(Event.Kind.NEW_IP, ip, user_agent=agent(request), username=request.user.get_username())
            _alert(
                f"🚨 <b>Sessiya yangi IP'dan ishlatildi</b>\n<code>{telegram.h(ip)}</code>\n"
                f"{telegram.h(agent(request)[:90])}\nSiz bo'lmasangiz, sessiyani yoping."
            )


def active_sessions() -> list[SessionRecord]:
    live = {
        key_hash(key) for key in Session.objects.filter(expire_date__gt=timezone.now()).values_list("pk", flat=True)
    }
    return [row for row in SessionRecord.objects.select_related("user") if row.key_hash in live]


def kill_session(digest: str, ip: str, username: str) -> bool:
    for key in Session.objects.values_list("pk", flat=True):
        if key_hash(key) == digest:
            Session.objects.filter(pk=key).delete()
            SessionRecord.objects.filter(key_hash=digest).delete()
            record(Event.Kind.KILLED, ip, username=username)
            return True
    return False


def parse_leak(line: str) -> tuple[str, str, int] | None:
    """Maxfiy fayl haqiqatan berilganmi: 403/404 va himoya sahifasi hisoblanmaydi."""
    match = LOG_LINE.match(line)
    if not match or match[2] != "GET" or match[4] not in ("200", "206") or not SENSITIVE.match(match[3]):
        return None
    size = int(match[5]) if match[5].isdigit() else 0
    if size == 0 or size in CHALLENGE_BYTES:
        return None
    return match[1], match[3], size


def scan_log() -> list[tuple[str, str, int]]:
    """Faqat yangi qatorlar o'qiladi. Birinchi ishga tushish joriy nuqtani belgilaydi: eski hujum aytilmaydi."""
    state = ScanState.load()
    leaks = []
    for path in glob.glob(os.path.expanduser(settings.SECURITY_ACCESS_LOG)):
        if path.endswith(".gz") or not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        if path not in state.offsets:
            state.offsets[path] = size
            continue
        start = state.offsets[path] if state.offsets[path] <= size else 0  # log aylangan
        with open(path, "rb") as handle:
            handle.seek(start)
            for raw in handle:
                leak = parse_leak(raw.decode("utf-8", "replace"))
                if leak:
                    leaks.append(leak)
                    record(Event.Kind.LEAK, leak[0], path=leak[1])
            state.offsets[path] = handle.tell()
    state.scanned_at = timezone.now()
    state.save()
    Event.objects.filter(created_at__lt=timezone.now() - timedelta(days=KEEP_DAYS)).delete()
    return leaks


def digest_lines() -> list[str]:
    """Ertalabki xulosa uchun: skanerlar har bir urinish bilan bezovta qilmasin."""
    since = timezone.now() - timedelta(days=1)
    today = Event.objects.filter(created_at__gte=since)
    traps = today.filter(kind=Event.Kind.TRAP).count()
    fails = today.filter(kind=Event.Kind.LOGIN_FAIL).count()
    if not traps and not fails:
        return []
    return ["", f"🛡 Xavfsizlik: {traps} ta skaner, {fails} ta xato parol"]
