"""Telegram'ga kirish bosqichlari (Telethon). Veb so'rov ichida qisqa ulanish bilan ishlaydi.

Doimiy ulanish bu yerda emas — ``runner.py`` da. Kirish kodi va 2FA parol hech qayerga yozilmaydi.
"""

import asyncio
from dataclasses import dataclass

from telethon import TelegramClient, errors
from telethon.sessions import StringSession

TIMEOUT = 25  # veb so'rovni osib qo'ymaslik uchun


class LoginError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


@dataclass
class Me:
    id: int
    name: str
    username: str


@dataclass
class CodeResult:
    session: str
    me: Me | None = None  # None — 2FA parol ham kerak


def build_client(api_id: int, api_hash: str, session: str = "", **kwargs) -> TelegramClient:
    """Faqat ishlayotgan event loop ichida chaqiring."""
    return TelegramClient(
        StringSession(session or None),
        api_id,
        api_hash,
        device_model="Ifcoder",
        system_version="Linux",
        app_version="1.0",
        **kwargs,
    )


def _to_me(user) -> Me:
    name = " ".join(filter(None, [user.first_name, user.last_name]))
    return Me(id=user.id, name=name, username=user.username or "")


def _message(exc: Exception) -> str:
    if isinstance(exc, errors.FloodWaitError):
        return f"Telegram cheklov qo'ydi: {exc.seconds} soniyadan keyin urinib ko'ring."
    known = {
        errors.ApiIdInvalidError: "API ID yoki API Hash noto'g'ri. my.telegram.org dan qayta tekshiring.",
        errors.PhoneNumberInvalidError: "Telefon raqam noto'g'ri. Xalqaro formatda yozing: +998901234567.",
        errors.PhoneNumberBannedError: "Bu raqam Telegram tomonidan bloklangan.",
        errors.PhoneNumberUnoccupiedError: "Bu raqamda Telegram akkaunt yo'q.",
        errors.PhoneCodeInvalidError: "Kod noto'g'ri.",
        errors.PhoneCodeExpiredError: "Kod muddati o'tgan. Bekor qilib, qaytadan boshlang.",
        errors.PasswordHashInvalidError: "2FA parol noto'g'ri.",
    }
    for kind, text in known.items():
        if isinstance(exc, kind):
            return text
    if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
        return "Telegram serveriga ulanib bo'lmadi. Internet yoki hosting cheklovini tekshiring."
    return f"Telegram xatosi: {exc}"


async def _with_client(api_id, api_hash, session, work):
    # flood_sleep_threshold=0: Telegram kutishni so'rasa, veb so'rov uxlab qolmasin — xato bo'lib qaytsin
    client = build_client(api_id, api_hash, session, flood_sleep_threshold=0, connection_retries=2)
    await client.connect()
    try:
        return await work(client)
    finally:
        await client.disconnect()


def _run(api_id, api_hash, session, work):
    async def bounded():
        return await asyncio.wait_for(_with_client(api_id, api_hash, session, work), TIMEOUT)

    try:
        return asyncio.run(bounded())
    except (errors.RPCError, ConnectionError, OSError, TimeoutError) as exc:
        raise LoginError(_message(exc)) from exc


def request_code(api_id: int, api_hash: str, phone: str) -> tuple[str, str]:
    """Kod yuboradi. (session, phone_code_hash) qaytaradi — keyingi qadam shu sessiyada davom etishi shart."""

    async def work(client):
        sent = await client.send_code_request(phone)
        return client.session.save(), sent.phone_code_hash

    return _run(api_id, api_hash, "", work)


def submit_code(api_id: int, api_hash: str, session: str, phone: str, code: str, code_hash: str) -> CodeResult:
    async def work(client):
        try:
            user = await client.sign_in(phone, code, phone_code_hash=code_hash)
        except errors.SessionPasswordNeededError:
            return CodeResult(session=client.session.save())
        return CodeResult(session=client.session.save(), me=_to_me(user))

    return _run(api_id, api_hash, session, work)


def submit_password(api_id: int, api_hash: str, session: str, password: str) -> CodeResult:
    async def work(client):
        user = await client.sign_in(password=password)
        return CodeResult(session=client.session.save(), me=_to_me(user))

    return _run(api_id, api_hash, session, work)


def log_out(api_id: int, api_hash: str, session: str) -> None:
    """Sessiyani Telegram tomonida ham bekor qiladi."""

    async def work(client):
        await client.log_out()

    _run(api_id, api_hash, session, work)
