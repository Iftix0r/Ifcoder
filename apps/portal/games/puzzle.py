"""Kod jumboq: aralashgan qatorlarni tartiblab, to'g'ri surish.

Brauzerdan matn emas, qator raqami va surilishi keladi: o'quvchi o'zidan kod qo'sha olmaydi. To'g'rilik tartib
bilan emas, natija bilan tekshiriladi, shuning uchun bir xil natija beradigan boshqa tartib ham qabul qilinadi.
"""

import hashlib
from dataclasses import dataclass
from functools import lru_cache

from .. import engine
from ..levels import Chapter
from . import BadPayload

MAX_INDENT = 4


@dataclass(frozen=True)
class PuzzleLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    answer: str  # To'g'ri kod: chiqishi kerak bo'lgan natija shundan olinadi
    hint: str
    extra: tuple[str, ...] = ()  # Keraksiz, chalg'ituvchi qatorlar
    example: str = ""


def run(code: str) -> engine.Outcome:
    return engine.capture(engine.Interpreter(), engine.parse(code))


@lru_cache(maxsize=32)
def expected_of(level: PuzzleLevel) -> tuple[str, ...]:
    return tuple(engine.printed(run(level.answer)))


@lru_cache(maxsize=32)
def tiles_of(level: PuzzleLevel) -> tuple[str, ...]:
    """Aralashtirish doimiy: sahifa yangilansa ham raqamlar o'zgarmaydi."""
    lines = [line.strip() for line in level.answer.splitlines() if line.strip()]
    return tuple(sorted([*lines, *level.extra], key=lambda text: hashlib.sha256(text.encode()).hexdigest()))


def assemble(level: PuzzleLevel, payload: dict) -> str:
    tiles = tiles_of(level)
    picked = payload.get("lines")
    if not isinstance(picked, list) or len(picked) > len(tiles):
        raise BadPayload
    seen, rows = set(), []
    for item in picked:
        if not (isinstance(item, list) and len(item) == 2 and all(type(n) is int for n in item)):
            raise BadPayload
        index, indent = item
        if not (0 <= index < len(tiles) and 0 <= indent <= MAX_INDENT) or index in seen:
            raise BadPayload
        seen.add(index)
        rows.append("    " * indent + tiles[index])
    return "\n".join(rows)


def stars_for_tries(attempts: int) -> int:
    if attempts == 0:
        return 3
    return 2 if attempts <= 2 else 1


def attempt(level: PuzzleLevel, payload: dict, attempts: int) -> dict:
    code = assemble(level, payload)
    expected = list(expected_of(level))
    result = {"ok": False, "stars": 0, "line": None, "stored": code, "output": [], "expected": expected}
    if not code.strip():
        return {**result, "message": "Avval qatorlarni dasturga qo'shing."}
    try:
        outcome = run(code)
    except engine.CodeError as error:
        return {**result, "message": error.message, "line": error.line}
    output = engine.printed(outcome)
    result["output"] = output
    if outcome.error:
        return {**result, "message": outcome.error, "line": outcome.line}
    if output != expected:
        return {**result, "message": "Dastur ishladi, lekin natija boshqacha chiqdi."}
    return {**result, "ok": True, "stars": stars_for_tries(attempts), "tries": attempts + 1, "message": "Yechildi!"}


def config(level: PuzzleLevel, row) -> dict:
    return {
        "tiles": tiles_of(level),
        "expected": expected_of(level),
        "maxIndent": MAX_INDENT,
    }


CHAPTERS = (
    Chapter(
        "tartib",
        "Tartib muhim",
        "Qatorlar yuqoridan pastga bajariladi",
        "tone-brand",
        (),
        (
            PuzzleLevel(
                "jumboq-salom",
                "Salomlashish",
                "Natija ko'rsatilgan tartibda chiqsin.",
                "print() ekranga yozadi. Kompyuter qatorlarni yuqoridan pastga bajaradi.",
                'print("Salom")\nprint("Dunyo")\nprint("Xayr")\n',
                "Natijadagi tartibga qarang.",
            ),
            PuzzleLevel(
                "jumboq-ozgaruvchi",
                "Quti",
                "Natija 7 chiqsin.",
                "O'zgaruvchi ishlatilishidan oldin qiymat olishi kerak.",
                "x = 5\nx = x + 2\nprint(x)\n",
                "Avval x yaratiladi, keyin o'zgaradi, keyin chiqariladi.",
            ),
            PuzzleLevel(
                "jumboq-ayirma",
                "Keraksiz qator",
                "Natija 6 chiqsin. Bitta qator ortiqcha!",
                "Ba'zi qatorlar kerak emas. Ularni shunchaki dasturga qo'shmang.",
                "a = 10\nb = 4\nprint(a - b)\n",
                "print(a + b) natijasi 14 bo'lardi.",
                extra=("print(a + b)",),
            ),
        ),
    ),
    Chapter(
        "bloklar",
        "Bloklar va surilish",
        "Surilish qaysi qator kimga tegishliligini aytadi",
        "tone-cyan",
        (),
        (
            PuzzleLevel(
                "jumboq-sikl",
                "Sanash",
                "0, 1, 2 chiqsin. Sikl ichidagi qatorni o'ngga suring.",
                "for dan keyingi qator surilgan bo'lishi kerak. → tugmasi qatorni suradi.",
                "for i in range(3):\n    print(i)\n",
                "print(i) qatorini bir marta o'ngga suring.",
            ),
            PuzzleLevel(
                "jumboq-shart",
                "Katta yoki kichik",
                "Natija «katta» chiqsin.",
                "else if bilan bir xil surilishda turadi, ichidagi qatorlar esa suriladi.",
                'son = 8\nif son > 5:\n    print("katta")\nelse:\n    print("kichik")\n',
                "son, if, surilgan print, else, surilgan print.",
            ),
            PuzzleLevel(
                "jumboq-yigindi",
                "Yig'indi",
                "Natija 6 chiqsin: 1 + 2 + 3.",
                "Sikl tugagach chiqarish uchun print surilmaydi. Surilsa, u har aylanishda ishlaydi.",
                "s = 0\nfor i in range(1, 4):\n    s = s + i\nprint(s)\n",
                "print(s) sikldan tashqarida.",
                extra=("s = s - i",),
            ),
        ),
    ),
    Chapter(
        "murakkab",
        "Murakkab jumboqlar",
        "Blok ichida yana blok",
        "tone-violet",
        (),
        (
            PuzzleLevel(
                "jumboq-funksiya",
                "Funksiya",
                "Natija 10 chiqsin.",
                "def ichidagi qator funksiya chaqirilgandagina ishlaydi. Funksiya chaqirilishdan oldin yoziladi.",
                "def ikki(n):\n    return n * 2\nprint(ikki(5))\n",
                "def, surilgan return, keyin print.",
            ),
            PuzzleLevel(
                "jumboq-orqaga",
                "Orqaga sanash",
                "3, 2, 1 chiqsin.",
                "while ichida o'zgaruvchi o'zgarmasa, sikl hech qachon to'xtamaydi.",
                "n = 3\nwhile n > 0:\n    print(n)\n    n = n - 1\n",
                "Sikl ichida ikki qator bor.",
                extra=("n = n + 1",),
            ),
            PuzzleLevel(
                "jumboq-juftlar",
                "Juft sonlar",
                "0, 2, 4 chiqsin.",
                "Blok ichidagi blok yana bir pog'ona suriladi: for ichida if, if ichida print.",
                "for i in range(5):\n    if i % 2 == 0:\n        print(i)\n",
                "for, bir surilgan if, ikki surilgan print.",
                extra=("if i % 2 == 1:",),
            ),
        ),
    ),
)
