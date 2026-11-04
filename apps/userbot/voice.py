"""Matndan o'zbekcha ovoz. Ikki manba:

- edge-tts: bepul, API kalit kerak emas. Tabiiyroq chiqishi uchun sekinroq o'qiladi, gap orasiga pauza qo'yiladi.
- Aisha (AISHA_API_KEY bo'lsa): o'zbek tiliga moslangan, tabiiyroq ovoz. WAV qaytaradi, u MP3 ga aylantiriladi.

Telegram ovozli xabarda MP3 ni qabul qiladi. Serverda ffmpeg kerak emas.
"""

import asyncio
import io
import re
import wave
from dataclasses import dataclass
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone

DEFAULT_VOICE = "uz-UZ-MadinaNeural"
AISHA_PREFIX = "aisha:"
VOICES = [
    ("uz-UZ-MadinaNeural", "Madina (ayol, bepul)"),
    ("uz-UZ-SardorNeural", "Sardor (erkak, bepul)"),
    ("aisha:Gulnoza", "Gulnoza (ayol, tabiiy, Aisha)"),
]
SPEEDS = [("slow", "Sekin"), ("normal", "O'rtacha"), ("fast", "Tez")]
DEFAULT_SPEED = "normal"
EDGE_RATE = {"slow": "-20%", "normal": "-12%", "fast": "+0%"}
AISHA_SPEED = {"slow": 0.85, "normal": 0.95, "fast": 1.05}
AISHA_URL = "https://back.aisha.group/api/v1/tts/post/"
MAX_TEXT = 1000
TIMEOUT = 60

# edge-tts oqimi: MPEG-2 Layer III, 24 kHz, 48 kbit/s, mono. Bitta kadr 144 bayt, 24 ms
EDGE_HEADER = b"\xff\xf3\x64"
EDGE_BYTES_PER_SECOND = 6000
FRAME_SIZE = 144
FRAME_TICKS = 240_000  # 24 ms, edge-tts vaqtlari 100 ns birlikda
PAUSE_FRAMES = 16  # gaplar orasida ~0,4 soniya (odam nutqi kabi)
LEAD_FRAMES = 3  # kesilganda so'z boshi yo'qolmasin
TAIL_FRAMES = 5
MP3_BITRATE = 64


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


@dataclass
class Speech:
    data: bytes
    seconds: int


def voice_choices() -> list[tuple[str, str]]:
    """Aisha faqat kalit bo'lsa tanlovda ko'rinadi."""
    return [c for c in VOICES if settings.AISHA_API_KEY or not c[0].startswith(AISHA_PREFIX)]


def date_words(date) -> str:
    day = date.day
    if day in ROUND_TENS:
        name = ROUND_TENS[day]
    elif day < 10:
        name = ORDINALS[day]
    else:
        name = f"{TENS[day // 10]} {ORDINALS[day % 10]}"
    return f"{name} {MONTHS[date.month - 1]}"


def reminder_text(debt, owner: str = "") -> str:
    """Odam gapirgandek qisqa gaplar. Avtomatik ekani aytiladi: tinglovchi aldanmasin."""
    currency = "dollar" if debt.currency == "USD" else "so'm"
    name = debt.contact.name if debt.contact else debt.person
    parts = [f"Assalomu alaykum, {name}."]
    parts.append(f"{owner}dan eslatma, bu avtomatik xabar." if owner else "Bu avtomatik eslatma.")
    subject = f"{debt.reason[:1].upper()}{debt.reason[1:]} bo'yicha" if debt.reason else "Qarzingizdan"
    parts.append(f"{subject} {number_words(int(debt.remaining))} {currency} qolgan ekan.")
    if debt.due_date:
        past = " edi" if debt.due_date < timezone.localdate() else ""
        parts.append(f"Muddati {date_words(debt.due_date)}{past}.")
    parts.append("Imkoningiz bo'lsa, to'lab qo'ysangiz yaxshi bo'lardi.")
    parts.append("Savolingiz bo'lsa, shu yerga yozing. Rahmat.")
    return " ".join(parts)


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def trim(data: bytes, start: int, end: int) -> bytes:
    """Edge har gap atrofiga ~1 soniya jimlik qo'yadi. So'z vaqtlari bo'yicha kesiladi (kadr chegarasida)."""
    first = max(0, start // FRAME_TICKS - LEAD_FRAMES)
    last = end // FRAME_TICKS + TAIL_FRAMES
    return data[first * FRAME_SIZE : last * FRAME_SIZE]


def silence(header: bytes) -> bytes:
    """Bo'sh MP3 kadrlar: ffmpeg'siz pauza. Sarlavha shu oqimdan olinadi."""
    return (header[:4] + bytes(FRAME_SIZE - 4)) * PAUSE_FRAMES


async def _edge(text: str, voice: str, speed: str) -> Speech:
    # Bu yerda import: kutubxona muammosi butun saytni emas, faqat ovozni to'xtatsin
    import aiohttp
    import edge_tts

    async def one(sentence):
        communicate = edge_tts.Communicate(sentence, voice, rate=EDGE_RATE[speed], boundary="WordBoundary")
        chunks = [chunk async for chunk in communicate.stream()]
        audio = b"".join(c["data"] for c in chunks if c["type"] == "audio")
        words = [c for c in chunks if c["type"] == "WordBoundary"]
        if not words or not audio.startswith(EDGE_HEADER):
            return audio
        return trim(audio, words[0]["offset"], words[-1]["offset"] + words[-1]["duration"])

    try:
        parts = await asyncio.gather(*(one(s) for s in split_sentences(text)))
    except (edge_tts.exceptions.EdgeTTSException, aiohttp.ClientError, OSError) as exc:
        raise VoiceError("Ovoz yaratilmadi. Internetni tekshirib, keyinroq urinib ko'ring.") from exc
    parts = [p for p in parts if p]
    if not parts:
        raise VoiceError("Ovoz yaratilmadi: matnni tekshiring.")
    # Boshqa formatda kelsa, pauza qo'shib oqimni buzmaymiz
    glue = silence(parts[0]) if all(p.startswith(EDGE_HEADER) for p in parts) else b""
    data = glue.join(parts)
    return Speech(data, max(1, round(len(data) / EDGE_BYTES_PER_SECOND)))


def wav_to_mp3(data: bytes) -> Speech:
    import lameenc

    try:
        with wave.open(io.BytesIO(data)) as source:
            channels, width, rate = source.getnchannels(), source.getsampwidth(), source.getframerate()
            frames = source.getnframes()
            pcm = source.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise VoiceError("Ovoz xizmati noto'g'ri fayl qaytardi.") from exc
    if width != 2:
        raise VoiceError("Ovoz xizmati noma'lum formatda fayl qaytardi.")
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(MP3_BITRATE)
    encoder.set_in_sample_rate(rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)
    mp3 = bytes(encoder.encode(pcm)) + bytes(encoder.flush())
    return Speech(mp3, max(1, round(frames / rate)))


async def _aisha(text: str, model: str, speed: str) -> Speech:
    import aiohttp

    form = aiohttp.FormData()
    fields = {"transcript": text, "language": "uz", "model": model, "mood": "Neutral", "speed": AISHA_SPEED[speed]}
    for name, value in fields.items():
        form.add_field(name, str(value))
    headers = {"X-Api-Key": settings.AISHA_API_KEY}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as session:
            async with session.post(AISHA_URL, data=form, headers=headers) as response:
                if response.status in (401, 403):
                    raise VoiceError("Aisha kaliti noto'g'ri yoki limit tugagan.")
                if response.status == 402 or response.status == 429:
                    raise VoiceError("Aisha limiti tugagan. Bepul ovozni tanlang yoki keyinroq urinib ko'ring.")
                if response.status >= 400:
                    raise VoiceError(f"Aisha xatosi: {response.status}.")
                path = (await response.json()).get("audio_path")
            if not path:
                raise VoiceError("Aisha audio qaytarmadi.")
            async with session.get(urljoin(AISHA_URL, path)) as audio:
                data = await audio.read()
    except (aiohttp.ClientError, OSError, ValueError) as exc:
        raise VoiceError("Aisha xizmatiga ulanib bo'lmadi.") from exc
    return wav_to_mp3(data)


async def synthesize(text: str, voice: str = DEFAULT_VOICE, speed: str = DEFAULT_SPEED) -> Speech:
    speed = speed if speed in EDGE_RATE else DEFAULT_SPEED
    if voice.startswith(AISHA_PREFIX):
        if not settings.AISHA_API_KEY:
            raise VoiceError("Aisha kaliti sozlanmagan.")
        work = _aisha(text, voice.removeprefix(AISHA_PREFIX), speed)
    else:
        work = _edge(text, voice, speed)
    try:
        return await asyncio.wait_for(work, TIMEOUT)
    except TimeoutError as exc:
        raise VoiceError("Ovoz yaratish juda uzoq davom etdi. Keyinroq urinib ko'ring.") from exc
