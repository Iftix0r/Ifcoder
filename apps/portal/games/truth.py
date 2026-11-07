"""Rostmi? Kartani suradi: rost yoki yolg'on. Eng oson o'yin: ikkitagina tanlov, tez sur'at.

Javob yozib qo'yilmaydi: interpretator ifodaning o'zidan hisoblaydi, brauzerga bormaydi.
"""

from dataclasses import dataclass
from functools import lru_cache

from .. import engine
from ..levels import Chapter
from . import BadPayload

LIVES = 3


@dataclass(frozen=True)
class Card:
    code: str  # Oxirgi qator tekshiriladigan ifoda
    why: str


@dataclass(frozen=True)
class TruthLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    cards: tuple[Card, ...]
    hint: str = ""
    example: str = ""


@lru_cache(maxsize=128)
def truth_of(card: Card) -> bool:
    *setup, last = card.code.splitlines()
    source = "\n".join([*setup, f"print({last})"])
    return engine.printed(engine.capture(engine.Interpreter(), engine.parse(source))) == ["True"]


def attempt(level: TruthLevel, payload: dict, attempts: int) -> dict:
    answers = payload.get("answers")
    total = len(level.cards)
    if not isinstance(answers, list) or not 1 <= len(answers) <= total:
        raise BadPayload
    if any(type(item) is not bool for item in answers):
        raise BadPayload
    marks = [item == truth_of(card) for card, item in zip(level.cards, answers, strict=False)]
    mistakes = marks.count(False)
    finished = len(answers) == total or mistakes >= LIVES
    result = {
        "ok": False,
        "stars": 0,
        "correct": marks[-1],
        "why": level.cards[len(answers) - 1].why,
        "lives": max(LIVES - mistakes, 0),
        "finished": finished,
        "partial": not finished,
        "stored": f"{len(answers)} ta kartadan {marks.count(True)} tasi to'g'ri",
        "message": "",
    }
    if not finished:
        return result
    if mistakes >= LIVES:
        return {**result, "message": "Jonlar tugadi. Yana bir bor!"}
    return {**result, "ok": True, "stars": 3 - mistakes, "mistakes": mistakes, "message": "Zo'r!"}


def config(level: TruthLevel, row) -> dict:
    return {"cards": [card.code for card in level.cards], "lives": LIVES}


def c(code: str, why: str) -> Card:
    return Card(code, why)


CHAPTERS = (
    Chapter(
        "kartalar",
        "Rost yoki yolg'on",
        "Kompyuter hamma narsani rost yoki yolg'onga ajratadi",
        "tone-emerald",
        (),
        (
            TruthLevel(
                "rost-taqqoslash",
                "Katta va kichik",
                "Rost bo'lsa o'ngga, yolg'on bo'lsa chapga suring.",
                "> katta, < kichik, == teng, != teng emas, >= katta yoki teng.",
                (
                    c("5 > 3", "5 uchdan katta."),
                    c("2 > 7", "2 yettidan kichik."),
                    c("4 == 4", "To'rt to'rtga teng."),
                    c("3 != 3", "!= teng emas degani, 3 esa uchga teng."),
                    c("10 < 20", "10 yigirmadan kichik."),
                    c("6 >= 6", ">= katta yoki teng. 6 oltiga teng."),
                    c("1 <= 0", "1 noldan katta."),
                    c("7 == 8", "7 va 8 har xil."),
                ),
            ),
            TruthLevel(
                "rost-hisob",
                "Hisobchi",
                "Tenglik to'g'rimi?",
                "// butun bo'lish, % qoldiq: 7 % 2 = 1, chunki 7 ni 2 ga bo'lsa 1 qoladi.",
                (
                    c("2 + 2 == 4", "2 + 2 haqiqatan 4."),
                    c("3 * 3 == 6", "3 * 3 = 9."),
                    c("10 // 2 == 5", "10 ni 2 ga bo'lsa 5."),
                    c("7 % 2 == 0", "Qoldiq 1, demak 7 toq."),
                    c("9 - 4 == 5", "9 - 4 = 5."),
                    c("2 * 5 > 9", "2 * 5 = 10, u 9 dan katta."),
                    c("8 // 3 == 3", "8 ichida 3 ikki marta bor: 8 // 3 = 2."),
                    c("6 % 3 == 0", "6 uchga qoldiqsiz bo'linadi."),
                ),
            ),
            TruthLevel(
                "rost-quti",
                "Quti ichida nima?",
                "O'zgaruvchini o'qing, keyin oxirgi qatorga javob bering.",
                "Yuqoridan pastga o'qing. Eng oxirgi berilgan qiymat qutida qoladi.",
                (
                    c("x = 5\nx > 3", "x beshga teng, 5 > 3."),
                    c("x = 2\nx == 3", "x ikkiga teng."),
                    c("a = 4\nb = 4\na == b", "Ikkalasida ham 4 bor."),
                    c("x = 1\nx = x + 1\nx == 2", "1 + 1 = 2."),
                    c("n = 10\nn % 2 == 0", "10 juft son."),
                    c("x = 3\nx = 7\nx == 3", "Yangi qiymat 7, eskisi o'chdi."),
                    c("a = 2\nb = a * 2\nb == 4", "2 * 2 = 4."),
                    c("s = 5\ns != 5", "s beshga teng, != esa yolg'on."),
                ),
            ),
            TruthLevel(
                "rost-mantiq",
                "Va, yoki, emas",
                "Mantiqni toping.",
                "and: ikkalasi rost bo'lsin. or: bittasi yetadi. not: teskarisi.",
                (
                    c("True and True", "Ikkalasi ham rost."),
                    c("True and False", "and uchun ikkalasi rost bo'lishi kerak."),
                    c("False or True", "or uchun bittasi yetadi."),
                    c("not False", "Yolg'onning teskarisi rost."),
                    c("not True", "Rostning teskarisi yolg'on."),
                    c("5 > 1 and 2 > 1", "Ikkala taqqoslash ham rost."),
                    c("5 > 9 or 1 > 9", "Ikkalasi ham yolg'on."),
                    c("not 3 > 5", "3 > 5 yolg'on, not uni rost qiladi."),
                ),
            ),
        ),
    ),
)
