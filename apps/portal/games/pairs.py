"""Kod juftligi: kartalarni ochib, kodni natijasi bilan juftlash.

Juftlikni faqat server biladi: brauzer shu paytgacha ochilgan juftlarni yuboradi, server tekshiradi. To'g'ri
natija yozib qo'yilmaydi, interpretator kodning o'zidan hisoblaydi.
"""

import hashlib
from dataclasses import dataclass
from functools import lru_cache

from .. import engine
from ..levels import Chapter
from . import BadPayload


@dataclass(frozen=True)
class PairLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    codes: tuple[str, ...]
    hint: str = ""
    example: str = ""


def result_of(code: str) -> str:
    return " ".join(engine.printed(engine.capture(engine.Interpreter(), engine.parse(code))))


@lru_cache(maxsize=32)
def deck_of(level: PairLevel) -> tuple[tuple[str, int], ...]:
    """(matn, juftlik raqami). Tartib doimiy: sahifa yangilansa ham kartalar joyidan qimirlamaydi."""
    cards = []
    for index, code in enumerate(level.codes):
        cards += [(code, index), (result_of(code), index)]
    return tuple(sorted(cards, key=lambda card: hashlib.sha256(f"{level.slug}{card}".encode()).hexdigest()))


def stars_for_misses(misses: int, pairs: int) -> int:
    if misses <= pairs // 2:
        return 3
    return 2 if misses <= pairs + 2 else 1


def attempt(level: PairLevel, payload: dict, attempts: int) -> dict:
    deck = deck_of(level)
    picks = payload.get("picks")
    if not isinstance(picks, list) or not 1 <= len(picks) <= 100:
        raise BadPayload
    found: set[int] = set()
    misses = 0
    matched = False
    for pick in picks:
        if not (isinstance(pick, list) and len(pick) == 2 and all(type(n) is int for n in pick)):
            raise BadPayload
        first, second = pick
        if first == second or not (0 <= first < len(deck) and 0 <= second < len(deck)):
            raise BadPayload
        matched = deck[first][1] == deck[second][1]
        if matched:
            found.add(deck[first][1])
        else:
            misses += 1
    finished = len(found) == len(level.codes)
    result = {
        "ok": finished,
        "stars": stars_for_misses(misses, len(level.codes)) if finished else 0,
        "match": matched,
        "misses": misses,
        "partial": not finished,
        "stored": f"{len(picks)} ta urinish, {misses} ta xato",
        "message": "Hammasi topildi!" if finished else "",
    }
    return result


def config(level: PairLevel, row) -> dict:
    return {"cards": [{"text": text, "code": "\n" in text or "(" in text} for text, _ in deck_of(level)]}


CHAPTERS = (
    Chapter(
        "juftlar",
        "Kartalar",
        "Kodni natijasi bilan moslang",
        "tone-violet",
        (),
        (
            PairLevel(
                "juft-sonlar",
                "Hisob kartalari",
                "Har kodni natijasi bilan juftlang.",
                "Kartani bosing, keyin uning juftini toping. Kod chiqaradigan son — uning jufti.",
                (
                    "print(2 + 2)",
                    "print(3 * 3)",
                    "print(10 // 2)",
                    "print(7 - 5)",
                    "print(8 % 3 + 5)",
                    "print(2 * 3 + 2)",
                ),
            ),
            PairLevel(
                "juft-ozgaruvchi",
                "Quti kartalari",
                "O'zgaruvchi oxirida nimaga teng?",
                "Har kodni ko'z bilan yuqoridan pastga bajaring.",
                (
                    "x = 3\nprint(x)",
                    "x = 2\nx = x + 8\nprint(x)",
                    "a = 4\nb = a * 2\nprint(b)",
                    "x = 9\nx = 1\nprint(x)",
                    "a = 3\nprint(a * a)",
                    "x = 7\nx = x - 2\nprint(x)",
                ),
            ),
            PairLevel(
                "juft-shart",
                "Shart kartalari",
                "Qaysi yozuv chiqadi?",
                "True rost, False yolg'on degani.",
                (
                    "print(5 > 2)",
                    "print(2 > 5)",
                    'if 3 == 3:\n    print("ha")',
                    'if 1 > 2:\n    print("ha")\nelse:\n    print("yo\'q")',
                    "print(7 % 2)",
                    "print(4 % 2)",
                ),
            ),
            PairLevel(
                "juft-sikl",
                "Sikl kartalari",
                "Sikl nima chiqaradi?",
                "range oxirgi sonni kiritmaydi. Yig'indilarni diqqat bilan sanang.",
                (
                    "for i in range(3):\n    print(i)",
                    "for i in range(1, 4):\n    print(i)",
                    "s = 0\nfor i in range(4):\n    s = s + 1\nprint(s)",
                    "s = 0\nfor i in range(3):\n    s = s + 3\nprint(s)",
                    "for i in range(0, 6, 3):\n    print(i)",
                    "n = 3\nwhile n > 1:\n    print(n)\n    n = n - 1",
                ),
            ),
            PairLevel(
                "juft-funksiya",
                "Funksiya kartalari",
                "Funksiya nima qaytaradi?",
                "return qaytargan qiymat chaqirilgan joyga tushadi.",
                (
                    "def f():\n    return 6\nprint(f())",
                    "def f(n):\n    return n * 3\nprint(f(4))",
                    "def f(a, b):\n    return a + b\nprint(f(5, 9))",
                    "def f(n):\n    return n - 1\nprint(f(f(9)))",
                    "def f():\n    x = 5\nprint(f())",
                    "def f(n):\n    return n % 2\nprint(f(7))",
                ),
            ),
        ),
    ),
)
