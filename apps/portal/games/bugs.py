"""Xato ovchisi: buzilgan robot kodini eng kam o'zgartirish bilan tuzatish. Xaritalar robot o'yinidagidek."""

from dataclasses import dataclass

from ..levels import COND, Chapter, Level
from ..levels import attempt as robot_attempt
from . import code_from


@dataclass(frozen=True)
class BugLevel(Level):
    changes: int = 1  # Tuzatish uchun yetarli bo'lgan qatorlar soni


def changed_lines(before: str, after: str) -> int:
    """Eng kam qator tahriri (Levenshtein). difflib yaramaydi: takrorlangan ``yur()`` lar uni adashtiradi."""
    old = [line.rstrip() for line in before.strip().splitlines()]
    new = [line.rstrip() for line in after.strip().splitlines()]
    row = list(range(len(new) + 1))
    for i, line in enumerate(old, 1):
        previous, row = row, [i]
        for j, other in enumerate(new, 1):
            row.append(min(previous[j] + 1, row[j - 1] + 1, previous[j - 1] + (line != other)))
    return row[-1]


def attempt(level: BugLevel, payload: dict, attempts: int) -> dict:
    code = code_from(payload)
    result = {**robot_attempt(level, code), "stored": code}
    if not result["ok"]:
        return result
    changes = changed_lines(level.starter, code)
    if changes == 0:
        return {**result, "ok": False, "stars": 0, "message": "Kod hali o'zgarmadi."}
    extra = changes - level.changes
    stars = 3 if extra <= 0 else 2 if extra == 1 else 1
    return {**result, "stars": stars, "changes": changes, "allowed": level.changes, "message": "Xato tutildi!"}


LINE = ("#######", "#>...E#", "#######")
ROW = ("##########", "#>******E#", "##########")

CHAPTERS = (
    Chapter(
        "ovchi",
        "Xatolarni tuting",
        "Dasturchi vaqtining katta qismi xato qidirish bilan o'tadi",
        "tone-rose",
        COND,
        (
            BugLevel(
                "xato-son",
                "Bitta son",
                "Robot bayroqqa yetmayapti. Bitta qatorni tuzating.",
                "Avval kodni ishga tushiring va robot qayerda to'xtaganini ko'ring. Keyin nima uchun shunday "
                "bo'lganini o'ylang.",
                (LINE,),
                0,
                "Bayroqqacha 4 ta katak bor.",
                starter="for i in range(3):\n    yur()\n",
            ),
            BugLevel(
                "xato-surilish",
                "Surilish xatosi",
                "Kristallar olinmayapti. Bitta qatorni tuzating.",
                "Surilish kodning ma'nosini o'zgartiradi: surilmagan qator sikldan tashqarida.",
                (ROW,),
                0,
                "ol() ham sikl ichida bo'lishi kerak.",
                starter="for i in range(6):\n    yur()\nol()\nyur()\n",
            ),
            BugLevel(
                "xato-tomon",
                "Noto'g'ri tomon",
                "Robot devorga urilyapti. Bitta qatorni tuzating.",
                "Tomonlarni robotning o'zi qaragan yo'nalishdan hisoblang.",
                (("######", "#>..##", "###.##", "###.E#", "######"),),
                0,
                "Birinchi burilish o'ngga bo'lishi kerak.",
                starter="yur()\nyur()\nchapga()\nyur()\nyur()\nchapga()\nyur()\n",
            ),
            BugLevel(
                "xato-shart",
                "Teskari shart",
                "Robot kristall yo'q joyda ol() qilyapti. Bitta qatorni tuzating.",
                "not shartni teskari qiladi. Kerak bo'lmagan joyda u xato keltiradi.",
                (
                    ("#########", "#>*..*.E#", "#########"),
                    ("#########", "#>.*.*.E#", "#########"),
                ),
                0,
                "if qatoridagi not ortiqcha.",
                starter="for i in range(6):\n    yur()\n    if not kristall_bor():\n        ol()\n",
            ),
            BugLevel(
                "xato-chaqiruv",
                "Unutilgan chaqiruv",
                "Funksiya bor, lekin robot joyidan qimirlamayapti. Bitta qator qo'shing.",
                "def funksiyani faqat yaratadi. U ishlashi uchun nomi bilan chaqirilishi kerak.",
                (LINE,),
                0,
                "Oxiriga yetkaz() deb yozing.",
                starter="def yetkaz():\n    for i in range(4):\n        yur()\n",
            ),
            BugLevel(
                "xato-cheksiz",
                "Cheksiz sikl",
                "Robot to'xtamay devorga uriladi. Bitta qator qo'shing.",
                "while sharti o'zgarmasa, sikl hech qachon tugamaydi. Sikl ichida n o'zgarishi kerak.",
                (("######", "#>..E#", "######"),),
                0,
                "yur() ostiga, xuddi shunday surib: n = n + 1",
                starter="n = 0\nwhile n < 3:\n    yur()\n",
            ),
        ),
    ),
)
