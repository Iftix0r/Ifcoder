"""Sehrli mashina: o'quvchi ``mashina`` funksiyasini yozadi, u kirgan sonni to'g'ri javobga aylantirishi kerak.

To'g'ri javob ``reference`` dan olinadi. Yashirin sinovlar yodlangan javoblarni ushlaydi.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from types import SimpleNamespace

from .. import engine
from ..levels import Chapter, _missing, stars_for
from . import code_from

NAME = "mashina"


def _factorial(n):
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result


@dataclass(frozen=True)
class MachineLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    solution: str
    reference: Callable
    samples: tuple[tuple, ...]
    hidden: tuple[tuple, ...]
    hint: str
    starter: str = "def mashina(son):\n    return son\n"
    example: str = ""
    require: tuple[str, ...] = ()
    forbid: tuple[str, ...] = ()


def show(value) -> str:
    return f'"{value}"' if isinstance(value, str) else str(value)


def _same(got, expected) -> bool:
    return type(got) is type(expected) and got == expected


@lru_cache(maxsize=32)
def par_of(level: MachineLevel) -> int:
    return engine.count_statements(engine.parse(level.solution))


def _row(args, expected, got="", ok=None) -> dict:
    return {"input": ", ".join(show(arg) for arg in args), "expected": show(expected), "got": got, "ok": ok}


def _call(machine: engine.Interpreter, function, args):
    machine.steps = 0  # Har sinov uchun alohida chegara
    node = SimpleNamespace(lineno=function.node.lineno)
    try:
        return machine._invoke(function, list(args), node), ""
    except engine.CodeError as error:
        return None, error.message
    except RecursionError:
        return None, "Funksiya juda chuqur ketdi."


def attempt(level: MachineLevel, payload: dict, attempts: int) -> dict:
    code = code_from(payload)
    rows = [_row(args, level.reference(*args)) for args in level.samples]
    result = {"ok": False, "stars": 0, "rows": rows, "line": None, "stored": code, "events": []}
    try:
        tree = engine.parse(code)
    except engine.CodeError as error:
        return {**result, "message": error.message, "line": error.line}
    machine = engine.Interpreter()
    outcome = engine.capture(machine, tree)
    result["events"] = outcome.events
    if outcome.error:
        return {**result, "message": outcome.error, "line": outcome.line}
    function = machine.globals.get(NAME)
    if not isinstance(function, engine._Function):
        return {**result, "message": f"{NAME} degan funksiya yozing: def {NAME}(son):"}

    shown = []
    for args in (*level.samples, *level.hidden):
        expected = level.reference(*args)
        got, error = _call(machine, function, args)
        if error:
            return {**result, "rows": shown or rows, "message": error, "line": machine.line}
        passed = _same(got, expected)
        secret = args not in level.samples
        if not secret or not passed:
            shown.append(_row(args, expected, show(got), passed))
        if not passed:
            shown += [_row(a, level.reference(*a)) for a in level.samples[len(shown) :]]
            hint = " Funksiya javob qaytarmadi: return yozing." if got is None else ""
            where = "Yashirin sinovda xato chiqdi." if secret else "Mashina noto'g'ri javob berdi."
            return {**result, "rows": shown, "message": where + hint}

    problem = _missing(level, tree)
    if problem:
        return {**result, "rows": shown, "message": problem.replace("Robot yetib keldi", "Mashina ishladi")}
    statements = engine.count_statements(tree)
    par = par_of(level)
    return {
        **result,
        "ok": True,
        "stars": stars_for(statements, par),
        "rows": shown,
        "hidden": len(level.hidden),
        "statements": statements,
        "par": par,
        "message": "Mashina ishladi!",
    }


def config(level: MachineLevel, row) -> dict:
    return {
        "rows": [_row(args, level.reference(*args)) for args in level.samples],
        "hidden": len(level.hidden),
        "code": row.code if row and row.code else level.starter,
    }


BASE = ("def mashina(son):", "return son")
COND = (*BASE, "if son > 0:", "else:", "son % 2 == 0")
LOOPS = (*COND, "for i in range(1, son + 1):", "jami = 0", "jami = jami + i", "while son > 0:", "son = son // 10")

TWO_ARGS = "def mashina(a, b):\n    return a\n"

CHAPTERS = (
    Chapter(
        "hisob",
        "Oddiy mashinalar",
        "return natijani qaytaradi",
        "tone-brand",
        BASE,
        (
            MachineLevel(
                "mashina-qoshuvchi",
                "Bittaga ko'p",
                "Kirgan sondan bittaga katta son chiqsin.",
                "Funksiya son qabul qiladi va return orqali javob qaytaradi. Mashinaga son tushadi, yozgan "
                "kodingiz uni o'zgartiradi.",
                "def mashina(son):\n    return son + 1\n",
                lambda son: son + 1,
                ((1,), (5,), (10,)),
                ((0,), (-1,), (99,)),
                "return son + 1",
                example="def mashina(son):\n    return son + 2",
            ),
            MachineLevel(
                "mashina-ikki",
                "Ikki baravar",
                "Kirgan son ikki baravar ko'paysin.",
                "Ko'paytirish belgisi: * (yulduzcha).",
                "def mashina(son):\n    return son * 2\n",
                lambda son: son * 2,
                ((2,), (5,), (7,)),
                ((0,), (-3,), (50,)),
                "return son * 2",
            ),
            MachineLevel(
                "mashina-kvadrat",
                "Kvadrat",
                "Sonning kvadratini hisoblang.",
                "Sonning kvadrati — son o'ziga ko'paytirilgani: 4 ning kvadrati 16.",
                "def mashina(son):\n    return son * son\n",
                lambda son: son * son,
                ((2,), (3,), (4,)),
                ((0,), (-5,), (11,)),
                "son * son",
            ),
            MachineLevel(
                "mashina-yigindi",
                "Ikki kirish",
                "Ikki sonning yig'indisini chiqaring.",
                "Funksiya bir nechta qiymat olishi mumkin: def mashina(a, b):",
                "def mashina(a, b):\n    return a + b\n",
                lambda a, b: a + b,
                ((1, 2), (5, 5), (10, 3)),
                ((0, 0), (-1, 1), (7, -9)),
                "return a + b",
                starter=TWO_ARGS,
            ),
        ),
    ),
    Chapter(
        "qaror",
        "Qaror qiluvchi mashinalar",
        "if bilan har xil javob",
        "tone-amber",
        COND,
        (
            MachineLevel(
                "mashina-kattasi",
                "Kattasini top",
                "Ikki sondan kattasini chiqaring.",
                "if a > b: sharti rost bo'lsa bitta javob, aks holda boshqasi qaytariladi.",
                "def mashina(a, b):\n    if a > b:\n        return a\n    return b\n",
                max,
                ((3, 7), (9, 2), (5, 5)),
                ((-1, -5), (0, 1), (100, 99)),
                "if a > b: return a. Aks holda return b.",
                starter=TWO_ARGS,
                example="if a > b:\n    return a",
                require=("if",),
            ),
            MachineLevel(
                "mashina-juft",
                "Juftmi, toqmi?",
                'Juft son uchun "juft", toq son uchun "toq" chiqaring.',
                "% — bo'linganda qoladigan qoldiq. son % 2 == 0 bo'lsa, son juft. Mashina matn ham qaytara oladi.",
                'def mashina(son):\n    if son % 2 == 0:\n        return "juft"\n    return "toq"\n',
                lambda son: "juft" if son % 2 == 0 else "toq",
                ((2,), (7,), (10,)),
                ((0,), (1,), (-3,), (100,)),
                'if son % 2 == 0: return "juft"',
                example='if son % 2 == 0:\n    return "juft"',
                require=("if",),
            ),
            MachineLevel(
                "mashina-musbat",
                "Minusni olib tashla",
                "Manfiy son musbat bo'lsin, qolgani o'zgarmasin.",
                "Manfiy sonning oldiga minus qo'ysangiz musbat bo'ladi: -son.",
                "def mashina(son):\n    if son < 0:\n        return -son\n    return son\n",
                abs,
                ((-5,), (3,), (-1,)),
                ((0,), (-100,), (42,)),
                "if son < 0: return -son",
                require=("if",),
            ),
        ),
    ),
    Chapter(
        "sikl",
        "Sanovchi mashinalar",
        "Sikl va o'zgaruvchi birga ishlaydi",
        "tone-emerald",
        LOOPS,
        (
            MachineLevel(
                "mashina-jami",
                "Hammasini qo'sh",
                "1 dan kirgan songacha bo'lgan sonlar yig'indisi.",
                "Yig'indi uchun o'zgaruvchi kerak: jami = 0. Sikl har aylanishda unga qo'shib boradi.",
                "def mashina(son):\n    jami = 0\n    for i in range(1, son + 1):\n        jami = jami + i\n"
                "    return jami\n",
                lambda son: son * (son + 1) // 2,
                ((3,), (4,), (10,)),
                ((1,), (0,), (100,)),
                "jami = 0, keyin for i in range(1, son + 1): jami = jami + i",
                example="jami = 0\nfor i in range(1, 4):\n    jami = jami + i",
                require=("for",),
            ),
            MachineLevel(
                "mashina-faktorial",
                "Faktorial",
                "1 dan kirgan songacha bo'lgan sonlar ko'paytmasi.",
                "Faktorial: 4! = 1 * 2 * 3 * 4 = 24. Yig'indiga o'xshaydi, lekin 1 dan boshlanadi va ko'paytiriladi.",
                "def mashina(son):\n    natija = 1\n    for i in range(1, son + 1):\n        natija = natija * i\n"
                "    return natija\n",
                _factorial,
                ((3,), (4,), (5,)),
                ((0,), (1,), (10,)),
                "natija = 1 dan boshlang.",
                require=("for",),
            ),
            MachineLevel(
                "mashina-raqamlar",
                "Raqamlarni sana",
                "Sonda nechta raqam borligini toping.",
                "Sonni 10 ga butun bo'lsangiz, oxirgi raqami tushib qoladi: 123 // 10 = 12. Son 0 bo'lguncha "
                "sanang. Kirgan son doim 0 dan katta.",
                "def mashina(son):\n    soni = 0\n    while son > 0:\n        son = son // 10\n"
                "        soni = soni + 1\n    return soni\n",
                lambda son: len(str(son)),
                ((7,), (42,), (123,)),
                ((1,), (10,), (9999,), (100000,)),
                "while son > 0: son = son // 10, soni = soni + 1",
                require=("while",),
            ),
        ),
    ),
)
