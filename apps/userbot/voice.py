"""Matndan o'zbekcha ovoz (edge-tts: API kalit va ffmpeg kerak emas, MP3 qaytaradi).

Telegram ovozli xabarda MP3 ni qabul qiladi, shuning uchun qayta kodlash yo'q. Xizmat internet orqali ishlaydi.
"""

import asyncio

from django.utils import timezone

DEFAULT_VOICE = "uz-UZ-MadinaNeural"
VOICES = [("uz-UZ-MadinaNeural", "Madina (ayol)"), ("uz-UZ-SardorNeural", "Sardor (erkak)")]
MAX_TEXT = 1000
TIMEOUT = 40
BITRATE = 48_000  # edge-tts standart MP3 oqimi

ONES = ["", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz"]
TENS = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "to'qson"]
ORDINALS = {1: "birinchi", 2: "ikkinchi", 3: "uchinchi", 4: "to'rtinchi", 5: "beshinchi", 6: "oltinchi"}
ORDINALS |= {7: "yettinchi", 8: "sakkizinchi", 9: "to'qqizinchi"}
ROUND_TENS = {10: "o'ninchi", 20: "yigirmanchi", 30: "o'ttizinchi"}
MONTHS = "yanvar fevral mart aprel may iyun iyul avgust sentabr oktabr noyabr dekabr".split()


class VoiceError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato."""


def _below_thousand(number: int) -> list[str]:
    words = []
    if number >= 100:
        words += ([ONES[number // 100]] if number >= 200 else []) + ["yuz"]
        number %= 100
    return words + [w for w in (TENS[number // 10], ONES[number % 10]) if w]


def number_words(number: int) -> str:
    """Raqamni so'z bilan yozadi: ovoz «500 000» ni noto'g'ri o'qimasligi uchun."""
    if number == 0:
        return "nol"
    words = []
    for size, label in ((1_000_000_000, "milliard"), (1_000_000, "million"), (1_000, "ming")):
        if number >= size:
            words += _below_thousand(number // size) + [label]
            number %= size
    return " ".join(words + _below_thousand(number))


def date_words(date) -> str:
    day = date.day
    if day in ROUND_TENS:
        name = ROUND_TENS[day]
    elif day < 10:
        name = ORDINALS[day]
    else:
        name = f"{TENS[day // 10]} {ORDINALS[day % 10]}"
    return f"{MONTHS[date.month - 1]} oyining {name} kuni"


def reminder_text(debt, owner: str = "") -> str:
    """Xushmuomala eslatma. Avtomatik ekani aytiladi: odam jonli odam bilan gaplashyapman deb o'ylamasin."""
    currency = "dollar" if debt.currency == "USD" else "so'm"
    name = debt.contact.name if debt.contact else debt.person
    source = f"{owner}ning avtomatik" if owner else "Avtomatik"
    parts = [f"Assalomu alaykum, {name}.", f"Bu {source} ovozli eslatmasi."]
    reason = f" {debt.reason} bo'yicha" if debt.reason else ""
    parts.append(f"Sizda{reason} {number_words(int(debt.remaining))} {currency} qarz qolgan.")
    if debt.due_date:
        overdue = debt.due_date < timezone.localdate()
        tail = " edi, muddat o'tgan" if overdue else ""
        parts.append(f"Qaytarish muddati {date_words(debt.due_date)}{tail}.")
    parts.append("Savolingiz bo'lsa, shu chatga yozing. Rahmat.")
    return " ".join(parts)


async def synthesize(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    # Bu yerda import: kutubxona muammosi butun saytni emas, faqat ovozni to'xtatsin
    import aiohttp
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)

    async def collect():
        return b"".join([c["data"] async for c in communicate.stream() if c["type"] == "audio"])

    try:
        return await asyncio.wait_for(collect(), TIMEOUT)
    except (edge_tts.exceptions.EdgeTTSException, aiohttp.ClientError, OSError, TimeoutError) as exc:
        raise VoiceError("Ovoz yaratilmadi. Internetni tekshirib, keyinroq urinib ko'ring.") from exc


def duration_seconds(data: bytes) -> int:
    return max(1, round(len(data) * 8 / BITRATE))
