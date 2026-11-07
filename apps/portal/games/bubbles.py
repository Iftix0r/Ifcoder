"""Pufakcha: qoidaga mos pufaklarni yorish. Faqat bosish kerak, telefonda ham oson.

Qaysi pufak to'g'riligini ``rule`` hisoblaydi va u brauzerga bormaydi.
"""

import hashlib
import keyword
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from .. import engine
from ..levels import Chapter
from . import BadPayload


def _value(expression: str) -> str:
    return " ".join(engine.printed(engine.capture(engine.Interpreter(), engine.parse(f"print({expression})"))))


@dataclass(frozen=True)
class BubbleLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    items: tuple[str, ...]
    rule: Callable[[str], bool]
    hint: str = ""
    example: str = ""


@lru_cache(maxsize=32)
def bubbles_of(level: BubbleLevel) -> tuple[str, ...]:
    return tuple(sorted(level.items, key=lambda text: hashlib.sha256(f"{level.slug}{text}".encode()).hexdigest()))


def stars_for(hits: int, good: int, misses: int) -> int:
    share = hits / good
    if share >= 0.8 and misses <= 1:
        return 3
    return 2 if share >= 0.6 and misses <= 3 else 1


def attempt(level: BubbleLevel, payload: dict, attempts: int) -> dict:
    """Brauzer shu paytgacha yorilganlarning hammasini yuboradi. ``done`` — pufaklar tugadi."""
    items = bubbles_of(level)
    pops = payload.get("pops")
    done = payload.get("done", False)
    if not isinstance(pops, list) or not isinstance(done, bool) or len(pops) > len(items) or not (pops or done):
        raise BadPayload
    if any(type(item) is not int or not 0 <= item < len(items) for item in pops) or len(set(pops)) != len(pops):
        raise BadPayload
    good = sum(level.rule(text) for text in items)
    marks = [level.rule(items[item]) for item in pops]
    hits, misses = marks.count(True), marks.count(False)
    finished = done or hits == good
    enough = hits * 2 >= good  # Yarmini yorgan bola ham o'tadi: bu eng oson o'yin
    ok = finished and enough
    result = {
        "ok": ok,
        "stars": stars_for(hits, good, misses) if ok else 0,
        "hit": marks[-1] if marks else None,
        "hits": hits,
        "misses": misses,
        "good": good,
        "finished": finished,
        "partial": not finished,
        "stored": f"{good} tadan {hits} tasi topildi, {misses} ta xato",
        "message": "",
    }
    if finished:
        result["message"] = "Zo'r!" if ok else f"{good} ta to'g'ri pufakdan {hits} tasini yordingiz. Yana bir bor!"
    return result


def config(level: BubbleLevel, row) -> dict:
    return {"items": bubbles_of(level)}


CHAPTERS = (
    Chapter(
        "pufaklar",
        "Pufaklar",
        "Qoidani o'qing va bosing",
        "tone-cyan",
        (),
        (
            BubbleLevel(
                "pufak-juft",
                "Juft sonlar",
                "Faqat juft sonlarni yoring!",
                "Juft son 2 ga qoldiqsiz bo'linadi: 2, 4, 6, 8...",
                ("2", "7", "4", "11", "6", "3", "8", "15", "10", "9", "12", "5", "14", "1"),
                lambda text: int(text) % 2 == 0,
            ),
            BubbleLevel(
                "pufak-matn",
                "Matnni top",
                "Faqat matnlarni yoring!",
                'Matn qo\'shtirnoq ichida bo\'ladi: "salom". Qo\'shtirnoqsiz 5 — son, "5" esa matn.',
                ('"salom"', "5", '"Ali"', "12", '"5"', "3", '"kod"', "100", '"ha"', "7", "0", '"robot"', "42", '"10"'),
                lambda text: text.startswith('"'),
            ),
            BubbleLevel(
                "pufak-natija",
                "O'n chiqadi",
                "Natijasi 10 bo'lganlarni yoring!",
                "Ko'paytirish qo'shishdan oldin bajariladi. // butun bo'lish.",
                (
                    "5 + 5",
                    "2 * 5",
                    "3 + 3",
                    "20 // 2",
                    "12 - 2",
                    "4 * 3",
                    "1 + 9",
                    "6 + 6",
                    "100 // 10",
                    "7 + 2",
                    "15 - 5",
                    "2 + 2",
                    "5 * 2",
                    "9 - 1",
                ),
                lambda text: _value(text) == "10",
            ),
            BubbleLevel(
                "pufak-nom",
                "To'g'ri nomlar",
                "O'zgaruvchiga qo'yish mumkin bo'lgan nomlarni yoring!",
                "Nom harf bilan boshlanadi, ichida bo'sh joy bo'lmaydi. Python so'zlari (for, if) band.",
                (
                    "ism",
                    "2son",
                    "yosh",
                    "for",
                    "ball_1",
                    "mening nomim",
                    "son2",
                    "if",
                    "jami",
                    "a-b",
                    "narx",
                    "9",
                    "x",
                    "while",
                ),
                lambda text: text.isidentifier() and not keyword.iskeyword(text),
            ),
            BubbleLevel(
                "pufak-kalit",
                "Python so'zlari",
                "Python'ning o'z so'zlarini yoring!",
                "for, while, if, else, def, return — tilning o'z so'zlari.",
                (
                    "for",
                    "olma",
                    "while",
                    "kitob",
                    "if",
                    "robot",
                    "def",
                    "ism",
                    "return",
                    "uy",
                    "else",
                    "son",
                    "True",
                    "yur",
                ),
                keyword.iskeyword,
            ),
        ),
    ),
)
