"""Kod rassomi: qalamni kod bilan boshqarib, namunadagi rasmni chizish.

Namuna bosqichning ``solution`` kodidan chiqadi, shuning uchun rasm va yechim hech qachon ajralib ketmaydi.
Taqqoslash chiziqlar emas, qog'ozdagi izlar bo'yicha: 100 ni 50+50 qilib chizish yoki teskari yo'nalishdan
yurish ham to'g'ri hisoblanadi.
"""

import math
from dataclasses import dataclass
from functools import lru_cache

from .. import engine
from ..levels import Chapter, _missing, stars_for
from . import code_from

SIZE = 400
CELL = 4  # Taqqoslash katagi: bir necha piksel farq yechimni buzmasin
MATCH = 0.97

COLORS = {
    "qora": "#1e293b",
    "qizil": "#ef4444",
    "kok": "#3b82f6",
    "yashil": "#22c55e",
    "sariq": "#eab308",
    "binafsha": "#8b5cf6",
}


class Pen(engine.Interpreter):
    tired = "Qalam charchadi: chiziqlar juda ko'p. Sikl to'xtayaptimi?"

    def __init__(self, start: tuple[int, int]):
        super().__init__()
        self.x, self.y = start
        self.heading = 0
        self.down = True
        self.color = "qora"
        self.segments: list[tuple[float, float, float, float, str]] = []
        self.commands = {
            "oldinga": (lambda n: self._go(n), 1),
            "orqaga": (lambda n: self._go(-self._number(n)), 1),
            "ongga": (lambda n: self._turn(n), 1),
            "chapga": (lambda n: self._turn(-self._number(n)), 1),
            "rang": (self._color, 1),
            "qalam_ol": (lambda: self._pen(False), 0),
            "qalam_qoy": (lambda: self._pen(True), 0),
        }

    def _number(self, value) -> int:
        if type(value) is not int:
            raise engine.CodeError("Bu buyruq butun son kutadi, masalan: oldinga(100)", self.line)
        return value

    def _go(self, distance) -> None:
        self._action()
        distance = self._number(distance)
        angle = math.radians(self.heading)
        x = round(self.x + math.sin(angle) * distance, 2)
        y = round(self.y - math.cos(angle) * distance, 2)
        if not (0 <= x <= SIZE and 0 <= y <= SIZE):
            raise engine.CodeError("Qalam qog'ozdan chiqib ketdi.", self.line)
        if self.down:
            self.segments.append((self.x, self.y, x, y, self.color))
        self.events.append(
            {"a": "go", "x": x, "y": y, "draw": self.down, "color": COLORS[self.color], "line": self.line}
        )
        self.x, self.y = x, y

    def _turn(self, degrees) -> None:
        self._action()
        self.heading = (self.heading + self._number(degrees)) % 360
        self.events.append({"a": "turn", "h": self.heading, "line": self.line})

    def _color(self, name) -> None:
        if name not in COLORS:
            raise engine.CodeError(f"Bunday rang yo'q. Ranglar: {', '.join(COLORS)}", self.line)
        self.color = name

    def _pen(self, down: bool) -> None:
        self.down = down


def cells(segments) -> set[tuple[int, int, str]]:
    found = set()
    for x1, y1, x2, y2, color in segments:
        steps = max(int(math.hypot(x2 - x1, y2 - y1) / 2), 1)
        for step in range(steps + 1):
            part = step / steps
            found.add((round((x1 + (x2 - x1) * part) / CELL), round((y1 + (y2 - y1) * part) / CELL), color))
    return found


def _near(cell, others) -> bool:
    x, y, color = cell
    return any((x + dx, y + dy, color) in others for dx in (-1, 0, 1) for dy in (-1, 0, 1))


def likeness(drawn: set, target: set) -> float:
    """Eng yomon tomon olinadi: chizilmagan joy ham, ortiqcha chiziq ham foizni tushiradi."""
    if not drawn or not target:
        return 0.0
    covered = sum(_near(cell, drawn) for cell in target) / len(target)
    clean = sum(_near(cell, target) for cell in drawn) / len(drawn)
    return min(covered, clean)


@dataclass(frozen=True)
class DrawLevel:
    slug: str
    title: str
    goal: str
    lesson: str
    solution: str
    hint: str
    start: tuple[int, int] = (200, 200)
    example: str = ""
    starter: str = ""
    require: tuple[str, ...] = ()
    forbid: tuple[str, ...] = ()


@lru_cache(maxsize=64)
def target_of(level: DrawLevel) -> tuple:
    pen = Pen(level.start)
    outcome = engine.capture(pen, engine.parse(level.solution))
    if outcome.error:
        raise ValueError(f"{level.slug}: {outcome.error}")
    return tuple(pen.segments)


@lru_cache(maxsize=64)
def par_of(level: DrawLevel) -> int:
    return engine.count_statements(engine.parse(level.solution))


def attempt(level: DrawLevel, payload: dict, attempts: int) -> dict:
    code = code_from(payload)
    result = {"ok": False, "stars": 0, "events": [], "line": None, "stored": code, "percent": 0}
    try:
        tree = engine.parse(code)
    except engine.CodeError as error:
        return {**result, "message": error.message, "line": error.line}
    pen = Pen(level.start)
    outcome = engine.capture(pen, tree)
    result["events"] = outcome.events
    if outcome.error:
        return {**result, "message": outcome.error, "line": outcome.line}
    score = likeness(cells(pen.segments), cells(target_of(level)))
    result["percent"] = round(score * 100)
    if score < MATCH:
        return {**result, "message": f"Rasm namunaga {result['percent']}% o'xshadi. Yana bir urinib ko'ring!"}
    problem = _missing(level, tree)
    if problem:
        return {**result, "message": problem.replace("Robot yetib keldi", "Rasm to'g'ri")}
    statements = engine.count_statements(tree)
    par = par_of(level)
    return {
        **result,
        "ok": True,
        "stars": stars_for(statements, par),
        "statements": statements,
        "par": par,
        "message": "Ajoyib rasm!",
    }


def config(level: DrawLevel, row) -> dict:
    return {
        "size": SIZE,
        "start": level.start,
        "target": [[x1, y1, x2, y2, COLORS[color]] for x1, y1, x2, y2, color in target_of(level)],
        "code": row.code if row and row.code else level.starter,
    }


PEN = ("oldinga(100)", "ongga(90)", "chapga(90)")
LOOP = (*PEN, "for i in range(4):")
FULL = (*LOOP, "def nom():", 'rang("qizil")', "qalam_ol()", "qalam_qoy()", "n = 20", "n = n + 20")

CHAPTERS = (
    Chapter(
        "chiziqlar",
        "Birinchi chiziqlar",
        "Qalam yuradi, iz qoldiradi",
        "tone-brand",
        (*PEN, "qalam_ol()", "qalam_qoy()"),
        (
            DrawLevel(
                "rassom-chiziq",
                "Birinchi chiziq",
                "Kulrang namuna ustidan yuring.",
                "Qalam yuqoriga qarab turibdi. oldinga(100) uni 100 qadam suradi va chiziq qoldiradi.",
                "oldinga(240)\n",
                "Namuna uzunligi 240 qadam.",
                start=(200, 320),
                example="oldinga(100)",
                starter="oldinga(100)\n",
            ),
            DrawLevel(
                "rassom-burchak",
                "Burchak",
                "To'g'ri burchak chizing.",
                "ongga(90) qalamni 90 gradusga buradi: bu to'g'ri burchak. Qavs ichidagi son burilish kattaligi.",
                "oldinga(120)\nongga(90)\noldinga(120)\n",
                "Oldinga 120, ongga 90, yana oldinga 120.",
                start=(140, 260),
                example="oldinga(50)\nongga(90)\noldinga(50)",
            ),
            DrawLevel(
                "rassom-kvadrat",
                "Kvadrat",
                "Kvadrat chizing.",
                "Kvadratning 4 tomoni teng va hamma burchagi 90 gradus. Qalam boshlagan joyiga qaytib keladi.",
                "oldinga(160)\nongga(90)\noldinga(160)\nongga(90)\noldinga(160)\nongga(90)\noldinga(160)\n",
                "Tomoni 160 qadam.",
                start=(120, 280),
            ),
            DrawLevel(
                "rassom-uzuq",
                "Uzuq chiziq",
                "Uzuq-uzuq chiziq chizing.",
                "qalam_ol() qalamni qog'ozdan ko'taradi: u yuradi, lekin iz qoldirmaydi. qalam_qoy() yana tushiradi.",
                "for i in range(6):\n    oldinga(20)\n    qalam_ol()\n    oldinga(20)\n    qalam_qoy()\n",
                "6 marta: 20 chiz, ko'tar, 20 yur, tushir.",
                start=(200, 320),
                example="oldinga(20)\nqalam_ol()\noldinga(20)\nqalam_qoy()",
                require=("for",),
            ),
        ),
    ),
    Chapter(
        "naqshlar",
        "Sikl bilan naqsh",
        "Takrorlash chiroyli shakl yaratadi",
        "tone-cyan",
        LOOP,
        (
            DrawLevel(
                "rassom-uchburchak",
                "Uchburchak",
                "Teng tomonli uchburchak chizing.",
                "Shakl yopilishi uchun qalam jami 360 gradus burilishi kerak. Uch burchak bo'lsa: 360 / 3 = 120.",
                "for i in range(3):\n    oldinga(180)\n    ongga(120)\n",
                "3 marta: oldinga(180), ongga(120).",
                start=(110, 290),
                require=("for",),
            ),
            DrawLevel(
                "rassom-olti",
                "Asalari uyasi",
                "Olti burchakli shakl chizing.",
                "Oltita tomon: har burchakda 360 / 6 gradus buriling.",
                "for i in range(6):\n    oldinga(90)\n    ongga(60)\n",
                "6 marta: oldinga(90), ongga(60).",
                start=(120, 250),
                require=("for",),
            ),
            DrawLevel(
                "rassom-yulduz",
                "Yulduz",
                "Besh qirrali yulduz chizing.",
                "Yulduzda qalam ikki marta aylanadi: 720 / 5 = 144 gradus. Sonni o'zgartirib, boshqa shakl yasang!",
                "for i in range(5):\n    oldinga(220)\n    ongga(144)\n",
                "5 marta: oldinga(220), ongga(144).",
                start=(110, 250),
                require=("for",),
            ),
            DrawLevel(
                "rassom-zina",
                "Zinapoya",
                "Yuqoriga ko'tarilayotgan zina chizing.",
                "Har pog'ona bir xil: yuqoriga, o'ngga, keyin yana yuqoriga qarab buriling.",
                "for i in range(5):\n    oldinga(40)\n    ongga(90)\n    oldinga(40)\n    chapga(90)\n",
                "5 marta: oldinga(40), ongga(90), oldinga(40), chapga(90).",
                start=(60, 340),
                require=("for",),
            ),
        ),
    ),
    Chapter(
        "sanat",
        "Rang va funksiya",
        "Katta rasm kichik qismlardan yig'iladi",
        "tone-violet",
        FULL,
        (
            DrawLevel(
                "rassom-rangli",
                "Rangli kvadratlar",
                "Katta qizil va kichik ko'k kvadrat chizing.",
                'rang("qizil") qalam rangini o\'zgartiradi. Ranglar: qora, qizil, kok, yashil, sariq, binafsha. '
                "kvadrat(n) funksiyasi har qanday o'lchamga yaraydi.",
                "def kvadrat(n):\n    for i in range(4):\n        oldinga(n)\n        ongga(90)\n\n"
                'rang("qizil")\nkvadrat(160)\nrang("kok")\nkvadrat(80)\n',
                "kvadrat(n) yozing. Avval qizil 160, keyin ko'k 80.",
                start=(120, 280),
                example='rang("yashil")\noldinga(50)',
                require=("def",),
            ),
            DrawLevel(
                "rassom-uycha",
                "Uycha",
                "Ko'k devorli, qizil tomli uy chizing.",
                "Uy ikki qismdan iborat: kvadrat devor va uchburchak tom. Kvadrat tugagach qalam yuqoriga qarab "
                "turadi, tomni shu yerdan boshlang.",
                'rang("kok")\nfor i in range(4):\n    oldinga(160)\n    ongga(90)\n'
                'oldinga(160)\nrang("qizil")\nongga(30)\noldinga(160)\nongga(120)\noldinga(160)\n',
                "Devordan keyin: oldinga(160), rang, ongga(30), oldinga(160), ongga(120), oldinga(160).",
                start=(120, 320),
                require=("for",),
            ),
            DrawLevel(
                "rassom-gul",
                "Gul",
                "12 ta kvadratni aylantirib gul chizing.",
                "Bir shaklni qayta-qayta oz-ozdan burib chizsangiz, chiroyli naqsh chiqadi. Sikl ichida funksiyani "
                "chaqiring.",
                'def kvadrat():\n    for i in range(4):\n        oldinga(70)\n        ongga(90)\n\nrang("binafsha")\n'
                "for j in range(12):\n    kvadrat()\n    ongga(30)\n",
                "kvadrat() tomoni 70, rangi binafsha. 12 marta: kvadrat(), ongga(30).",
                require=("def", "for"),
            ),
            DrawLevel(
                "rassom-spiral",
                "Spiral",
                "Har safar uzayib boradigan spiral chizing.",
                "O'zgaruvchi har aylanishda o'sadi: n = n + 20. Shu tufayli har chiziq oldingisidan uzun bo'ladi.",
                "n = 20\nfor i in range(16):\n    oldinga(n)\n    ongga(90)\n    n = n + 20\n",
                "n = 20 dan boshlang. 16 marta: oldinga(n), ongga(90), n = n + 20.",
                example="n = 20\noldinga(n)\nn = n + 20\noldinga(n)",
                require=("for", "o'zgaruvchi"),
            ),
        ),
    ),
)
