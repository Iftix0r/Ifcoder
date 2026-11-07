"""Kod detektivi: kodni bajarmasdan, nima chiqishini topish. 3 ta jon, har raundda 5 ta savol.

To'g'ri javob yozib qo'yilmaydi: uni interpretator kodning o'zidan hisoblaydi. Variantlar brauzerga javobsiz boradi.
"""

import hashlib
from dataclasses import dataclass
from functools import lru_cache

from .. import engine
from ..levels import Chapter
from . import BadPayload

LIVES = 3


@dataclass(frozen=True)
class Question:
    code: str
    wrong: tuple[str, str, str]


@dataclass(frozen=True)
class QuizLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    questions: tuple[Question, ...]
    hint: str = ""
    example: str = ""


@lru_cache(maxsize=128)
def answer_of(question: Question) -> str:
    return " ".join(engine.printed(engine.capture(engine.Interpreter(), engine.parse(question.code))))


@lru_cache(maxsize=128)
def options_of(question: Question) -> tuple[str, ...]:
    choices = [answer_of(question), *question.wrong]
    return tuple(sorted(choices, key=lambda text: hashlib.sha256((question.code + text).encode()).hexdigest()))


def attempt(level: QuizLevel, payload: dict, attempts: int) -> dict:
    """Javoblar birma-bir keladi: brauzer shu paytgacha berilganlarning hammasini yuboradi."""
    answers = payload.get("answers")
    total = len(level.questions)
    if not isinstance(answers, list) or not 1 <= len(answers) <= total:
        raise BadPayload
    if any(type(item) is not int or not 0 <= item < 4 for item in answers):
        raise BadPayload
    marks = [options_of(q)[item] == answer_of(q) for q, item in zip(level.questions, answers, strict=False)]
    mistakes = marks.count(False)
    finished = len(answers) == total or mistakes >= LIVES
    last = level.questions[len(answers) - 1]
    result = {
        "ok": False,
        "stars": 0,
        "correct": marks[-1],
        "right": options_of(last).index(answer_of(last)),
        "lives": max(LIVES - mistakes, 0),
        "finished": finished,
        "partial": not finished,
        "stored": f"{total} ta savoldan {marks.count(True)} tasi to'g'ri",
        "message": "",
    }
    if not finished:
        return result
    if mistakes >= LIVES:
        return {**result, "message": "Jonlar tugadi. Kodni sekinroq o'qib, qayta urinib ko'ring."}
    return {**result, "ok": True, "stars": 3 - mistakes, "mistakes": mistakes, "message": "Ish ochildi!"}


def config(level: QuizLevel, row) -> dict:
    return {
        "questions": [{"code": q.code, "options": options_of(q)} for q in level.questions],
        "lives": LIVES,
    }


def q(code: str, *wrong: str) -> Question:
    return Question(code, wrong)


CHAPTERS = (
    Chapter(
        "ishlar",
        "Detektiv ishlari",
        "Kodni ko'z bilan bajaring",
        "tone-amber",
        (),
        (
            QuizLevel(
                "detektiv-sonlar",
                "Sonlar sirri",
                "Kod nima chiqarishini toping.",
                "Amallar tartibi matematikadagidek: avval * va //, keyin + va -. % qoldiqni beradi.",
                (
                    q("print(2 + 3 * 4)", "20", "24", "9"),
                    q("print(7 // 2)", "3.5", "4", "1"),
                    q("print(7 % 2)", "3", "0", "2"),
                    q("print((2 + 3) * 4)", "14", "24", "9"),
                    q("print(10 - 2 - 3)", "11", "9", "7"),
                ),
            ),
            QuizLevel(
                "detektiv-ozgaruvchi",
                "Yo'qolgan qiymat",
                "O'zgaruvchilar oxirida nimaga teng?",
                "= belgisi o'ng tomonni hisoblab, chapdagi o'zgaruvchiga yozadi. Eski qiymat yo'qoladi.",
                (
                    q("a = 5\na = 3\nprint(a)", "5", "8", "2"),
                    q("a = 2\nb = a\na = 9\nprint(b)", "9", "11", "7"),
                    q("x = 4\nx = x + x\nprint(x)", "4", "6", "16"),
                    q("a = 1\nb = 2\na = b\nb = a\nprint(a, b)", "2 1", "1 2", "1 1"),
                    q("n = 10\nn = n // 3\nn = n * 2\nprint(n)", "20", "7", "8"),
                ),
            ),
            QuizLevel(
                "detektiv-shart",
                "Qaysi yo'l?",
                "Dastur qaysi tarmoqqa kiradi?",
                "if rost bo'lsa uning ichi, aks holda else ishlaydi. elif birinchi rost shartda to'xtaydi.",
                (
                    q('x = 5\nif x > 3:\n    print("A")\nelse:\n    print("B")', "B", "A B", "Hech narsa"),
                    q('x = 3\nif x > 3:\n    print("A")\nelse:\n    print("B")', "A", "A B", "Hech narsa"),
                    q('x = 9\nif x > 5:\n    print("A")\nelif x > 2:\n    print("B")', "B", "A B", "Hech narsa"),
                    q('x = 4\nif x % 2 == 0 and x > 5:\n    print("A")\nelse:\n    print("B")', "A", "A B", "4"),
                    q('x = 1\nif x > 5 or x == 1:\n    print("A")\nprint("B")', "B", "A", "1 B"),
                ),
            ),
            QuizLevel(
                "detektiv-sikl",
                "Necha marta?",
                "Sikl necha marta aylanadi?",
                "range(3) — 0, 1, 2. Oxirgi son kirmaydi! range(1, 4) — 1, 2, 3.",
                (
                    q("for i in range(3):\n    print(i)", "1 2 3", "0 1 2 3", "3"),
                    q("for i in range(1, 4):\n    print(i)", "0 1 2 3", "1 2 3 4", "4"),
                    q("s = 0\nfor i in range(4):\n    s = s + i\nprint(s)", "10", "4", "3"),
                    q("for i in range(0, 6, 2):\n    print(i)", "0 2 4 6", "2 4 6", "0 1 2"),
                    q("n = 0\nfor i in range(2):\n    for j in range(3):\n        n = n + 1\nprint(n)", "5", "3", "2"),
                ),
            ),
            QuizLevel(
                "detektiv-while",
                "To'xtash nuqtasi",
                "while qachon to'xtaydi?",
                "Shart har aylanish boshida tekshiriladi. break siklni to'xtatadi, continue keyingi aylanishga o'tadi.",
                (
                    q("n = 3\nwhile n > 0:\n    n = n - 1\nprint(n)", "1", "3", "-1"),
                    q("n = 1\nwhile n < 10:\n    n = n * 2\nprint(n)", "8", "10", "32"),
                    q("for i in range(5):\n    if i == 2:\n        break\n    print(i)", "0 1 2", "0 1 3 4", "2"),
                    q("for i in range(4):\n    if i == 1:\n        continue\n    print(i)", "0", "1", "0 1 2 3"),
                    q("n = 0\nwhile n < 3:\n    print(n)\n    n = n + 2", "0 1 2", "0 2 4", "2 4"),
                ),
            ),
            QuizLevel(
                "detektiv-funksiya",
                "Maxfiy funksiya",
                "Funksiya nima qaytaradi?",
                "return funksiyani darhol tugatadi. Ichidagi o'zgaruvchi tashqariga chiqmaydi.",
                (
                    q("def f(n):\n    return n + 1\nprint(f(2))", "2", "1", "None"),
                    q("def f(n):\n    return n * 2\nprint(f(f(2)))", "4", "6", "16"),
                    q("def f():\n    return 1\n    return 2\nprint(f())", "2", "1 2", "None"),
                    q("def f(n):\n    n = n + 1\nprint(f(1))", "2", "1", "0"),
                    q("def f(a, b):\n    return a - b\nprint(f(2, 5))", "3", "7", "-7"),
                ),
            ),
        ),
    ),
)
