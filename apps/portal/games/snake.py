"""Kod iloni: ilon so'zlarni to'g'ri tartibda yeb, kod qatorini yig'adi.

Oson: devorga urilib o'lmaydi, o'zini yesa ham o'lmaydi. Faqat noto'g'ri so'z jonni oladi. Keyingi so'z qaysi
ekanini faqat server biladi, shuning uchun qator tartibini brauzerdan o'qib bo'lmaydi.
"""

import hashlib
import re
from dataclasses import dataclass
from functools import lru_cache

from ..levels import Chapter
from . import BadPayload

LIVES = 5  # Ilon yo'lda tasodifan noto'g'ri so'zga tegishi mumkin: bu jazo bo'lmasin
TOKEN = re.compile(r'"[^"]*"|\w+|==|!=|<=|>=|//|[^\s\w]')


@dataclass(frozen=True)
class Line:
    goal: str
    code: str
    extra: tuple[str, ...] = ()


@dataclass(frozen=True)
class SnakeLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    lines: tuple[Line, ...]
    hint: str = ""
    example: str = ""


@lru_cache(maxsize=64)
def tokens_of(line: Line) -> tuple[str, ...]:
    return tuple(TOKEN.findall(line.code))


@lru_cache(maxsize=64)
def tiles_of(line: Line) -> tuple[str, ...]:
    tiles = [*tokens_of(line), *line.extra]
    numbered = list(enumerate(tiles))
    numbered.sort(key=lambda pair: hashlib.sha256(f"{line.code}{pair[0]}".encode()).hexdigest())
    return tuple(text for _, text in numbered)


def stars_for(mistakes: int) -> int:
    if mistakes <= 1:
        return 3
    return 2 if mistakes <= 3 else 1


def attempt(level: SnakeLevel, payload: dict, attempts: int) -> dict:
    eaten = payload.get("eaten")
    if not isinstance(eaten, list) or not 1 <= len(eaten) <= 100:
        raise BadPayload
    index = position = mistakes = 0
    right = False
    for item in eaten:
        if not (isinstance(item, list) and len(item) == 2 and all(type(n) is int for n in item)):
            raise BadPayload
        line_index, tile = item
        if index >= len(level.lines) or line_index != index or mistakes >= LIVES:
            raise BadPayload
        line = level.lines[index]
        tiles = tiles_of(line)
        if not 0 <= tile < len(tiles):
            raise BadPayload
        right = tiles[tile] == tokens_of(line)[position]
        if right:
            position += 1
            if position == len(tokens_of(line)):
                index, position = index + 1, 0
        else:
            mistakes += 1
    won = index == len(level.lines)
    finished = won or mistakes >= LIVES
    current = level.lines[min(index, len(level.lines) - 1)]
    result = {
        "ok": won,
        "stars": stars_for(mistakes) if won else 0,
        "right": right,
        "line": index,
        "built": [] if won else list(tokens_of(current)[:position]),
        "lives": max(LIVES - mistakes, 0),
        "finished": finished,
        "partial": not finished,
        "stored": "\n".join(line.code for line in level.lines[:index]),
        "message": "",
    }
    if finished:
        result["message"] = "Mazali kod!" if won else "Jonlar tugadi. Yana bir bor!"
    return result


def config(level: SnakeLevel, row) -> dict:
    return {
        "lines": [{"goal": line.goal, "tiles": tiles_of(line), "size": len(tokens_of(line))} for line in level.lines],
        "lives": LIVES,
    }


CHAPTERS = (
    Chapter(
        "ilon",
        "Ilon sayohati",
        "Kod so'zlardan yig'iladi",
        "tone-emerald",
        (),
        (
            SnakeLevel(
                "ilon-print",
                "Birinchi taom",
                "So'zlarni tartib bilan yeng va qatorni yig'ing.",
                "print(...) ekranga yozadi. Avval print, keyin qavs, keyin qiymat, keyin yopuvchi qavs.",
                (
                    Line('Ekranga "Salom" yozing', 'print("Salom")', ("yur",)),
                    Line("Ekranga 5 sonini yozing", "print(5)", ("x",)),
                    Line("2 va 3 yig'indisini chiqaring", "print(2 + 3)", ("*",)),
                ),
            ),
            SnakeLevel(
                "ilon-quti",
                "Quti to'ldiramiz",
                "O'zgaruvchi qatorlarini yig'ing.",
                "Avval nom, keyin =, keyin qiymat.",
                (
                    Line("x ga 5 ni soling", "x = 5", ("==",)),
                    Line("x ni bittaga oshiring", "x = x + 1", ("-",)),
                    Line("x ni ekranga chiqaring", "print(x)", ("=",)),
                ),
            ),
            SnakeLevel(
                "ilon-sikl",
                "Aylanma yo'l",
                "for qatorlarini yig'ing.",
                "for i in range(3): — oxiridagi ikki nuqtani unutmang!",
                (
                    Line("3 marta takrorlang", "for i in range(3):", ("while",)),
                    Line("0 dan 4 gacha sanang", "for i in range(5):", ("if",)),
                ),
            ),
            SnakeLevel(
                "ilon-shart",
                "Ikki yo'l",
                "if qatorlarini yig'ing.",
                "if dan keyin shart, oxirida ikki nuqta. Taqqoslash == bilan yoziladi.",
                (
                    Line("x beshdan kattami?", "if x > 5:", ("<",)),
                    Line("x nolga tengmi?", "if x == 0:", ("=",)),
                    Line("Aks holda", "else:", ("if",)),
                ),
            ),
            SnakeLevel(
                "ilon-funksiya",
                "Sehrli so'z",
                "Funksiya qatorlarini yig'ing.",
                "def nom(): funksiyani yaratadi, return natija qaytaradi, nom() chaqiradi.",
                (
                    Line("salom funksiyasini yarating", "def salom():", ("for",)),
                    Line("5 ni qaytaring", "return 5", ("print",)),
                    Line("salom funksiyasini chaqiring", "salom()", ("def",)),
                ),
            ),
        ),
    ),
)
