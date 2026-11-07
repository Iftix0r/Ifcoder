"""O'yin bosqichlari. ``slug`` o'zgarmasin: o'quvchi natijasi shu nom bilan saqlanadi.

Bir bosqichda bir nechta xarita bo'lsa, kod hammasida o'tishi kerak. Shart va sikl shu tufayli haqiqatan
kerak bo'ladi: bitta xaritani yod olib o'tib bo'lmaydi. Har bir bosqich yechimi ``tests/test_portal.py`` da.
"""

import ast
from dataclasses import dataclass

from . import engine

XP_PER_STAR = 10

REQUIRE_NODES = {
    "for": ast.For,
    "while": ast.While,
    "if": ast.If,
    "def": ast.FunctionDef,
    "return": ast.Return,
    "o'zgaruvchi": ast.Assign,
}


@dataclass(frozen=True)
class Level:
    slug: str
    title: str
    goal: str
    lesson: str
    maps: tuple[tuple[str, ...], ...]
    par: int
    hint: str
    example: str = ""
    starter: str = ""
    require: tuple[str, ...] = ()
    forbid: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chapter:
    slug: str
    title: str
    concept: str
    tone: str
    tools: tuple[str, ...]
    levels: tuple[Level, ...]


BASIC = ("yur()", "chapga()", "ongga()", "ol()")
LOOP = (*BASIC, "for i in range(3):")
FUNC = (*LOOP, "def nom():")
COND = (*FUNC, "if kristall_bor():", "else:", "oldinda_devor()", "chapda_devor()", "ongda_devor()")
WHILE = (*COND, "while not oldinda_devor():", "yetib_keldi()", "elif ")
VARS = (*WHILE, "son = 0", "son = son + 1", "print(son)", "return son")


CHAPTERS: tuple[Chapter, ...] = (
    Chapter(
        "qadamlar",
        "Birinchi qadamlar",
        "Dastur — bu buyruqlar ketma-ketligi",
        "tone-brand",
        BASIC,
        (
            Level(
                "salom-robot",
                "Salom, robot!",
                "Robotni bayroqqacha olib boring.",
                "Kompyuter buyruqlarni yuqoridan pastga, birma-bir bajaradi. yur() robotni bir katak oldinga surad"
                "i. Har bir buyruq alohida qatorga yoziladi.",
                (("#######", "#>...E#", "#######"),),
                4,
                "Bayroqqacha 4 ta katak bor. yur() buyrug'ini 4 marta yozing.",
                example="yur()\nyur()",
                starter="yur()\n",
            ),
            Level(
                "birinchi-kristall",
                "Birinchi kristall",
                "Kristallni oling va bayroqqa boring.",
                "ol() buyrug'i robot turgan katakdagi kristallni oladi. Avval kristall ustiga borish kerak.",
                (("#######", "#>.*.E#", "#######"),),
                5,
                "Ikki qadam, keyin ol(), yana ikki qadam.",
                example="yur()\nol()",
            ),
            Level(
                "burilish",
                "Birinchi burilish",
                "Yo'lak bo'ylab bayroqqa yeting.",
                "ongga() va chapga() robotni joyida 90 gradusga buradi, lekin oldinga surmaydi. Tomonlarni robotning "
                "o'zi qaragan yo'nalishdan hisoblang.",
                (("######", "#>..##", "###.##", "###.E#", "######"),),
                7,
                "yur, yur, ongga, yur, yur, chapga, yur.",
                example="yur()\nongga()\nyur()",
            ),
            Level(
                "ilon-yol",
                "Ilon yo'li",
                "Ikkala kristallni olib, bayroqqa yeting.",
                "Endi hammasini birga ishlating. Avval yo'lni ko'z bilan kuzating, keyin yozing.",
                (("#######", "#>.*###", "###.###", "###*.E#", "#######"),),
                10,
                "Birinchi kristall 2 qadam narida, keyin o'ngga buriling.",
            ),
        ),
    ),
    Chapter(
        "takrorlash",
        "Takrorlash",
        "for sikli bir ishni ko'p marta bajaradi",
        "tone-cyan",
        LOOP,
        (
            Level(
                "uzun-yol",
                "Uzun yo'l",
                "for yordamida bayroqqa yeting.",
                "Bir xil buyruqni qayta-qayta yozish shart emas. for i in range(10): ichidagi qatorlar 10 marta "
                "bajariladi. Ichki qatorlar 4 ta bo'sh joy bilan suriladi — Python blokni shu orqali taniydi.",
                (("#############", "#>.........E#", "#############"),),
                2,
                "Sikl ichida bitta yur() yetarli. Son 10 bo'lsin.",
                example="for i in range(3):\n    yur()",
                require=("for",),
            ),
            Level(
                "kristall-qatori",
                "Kristall qatori",
                "Hamma kristallarni yig'ib, bayroqqa boring.",
                "Sikl ichida bir nechta buyruq bo'lishi mumkin: hammasi bir xil surilgan bo'lsa, ular birga "
                "takrorlanadi. Sikldan keyingi surilmagan qator bir marta bajariladi.",
                (("##########", "#>******E#", "##########"),),
                4,
                "Har aylanishda yur() va ol(). Oxirida yana bitta yur().",
                example="for i in range(2):\n    yur()\n    ol()\nyur()",
                require=("for",),
            ),
            Level(
                "kvadrat",
                "To'rtburchak",
                "Burchakdagi kristallarni yig'ing.",
                "Takrorlanadigan qismni toping: uch qadam, kristall, burilish. Mana shu qism sikl ichiga kiradi.",
                (("######", "#>..*#", "#.##.#", "#E##.#", "#*..*#", "######"),),
                7,
                "3 marta takrorlang: yur x3, ol, ongga. Sikldan keyin bitta yur().",
                require=("for",),
            ),
            Level(
                "zinapoya",
                "Zinapoya",
                "Zinadan tushib bayroqqa yeting.",
                "Zinaning har pog'onasi bir xil: oldinga, o'ngga burilish, oldinga, chapga burilish.",
                (("#######", "#>.####", "##..###", "###..##", "####..#", "#####E#", "#######"),),
                5,
                "Sikl 4 marta aylansin, ichida to'rtta buyruq bo'lsin.",
                require=("for",),
            ),
            Level(
                "ichma-ich",
                "Ichma-ich sikl",
                "Uchta kristallni olib, bayroqqa boring.",
                "Sikl ichida yana sikl yozish mumkin. Ichki sikl ikki marta surilgan bo'ladi. Ikkinchi sikl nomiga "
                "boshqa harf bering: j.",
                (("#########", "#>.....E#", "##.#.#.##", "##*#*#*##", "#########"),),
                12,
                "Bir shoxcha: yur, ongga, 2 qadam, ol, orqaga burilish, 2 qadam, ongga, yur.",
                example="for i in range(2):\n    for j in range(3):\n        yur()\n    ongga()",
                require=("for",),
            ),
        ),
    ),
    Chapter(
        "funksiyalar",
        "Funksiyalar",
        "O'z buyrug'ingizni yarating",
        "tone-violet",
        FUNC,
        (
            Level(
                "orqaga-qayt",
                "Orqaga qayt",
                "Ikki chetdagi kristallarni oling, keyin bayroqqa boring.",
                "Python'da o'z buyrug'ingizni yasash mumkin: def nom(): deb yozasiz, ichiga buyruqlarni joylaysiz, "
                "keyin nom() deb chaqirasiz. Bu yerda orqaga() buyrug'i juda qo'l keladi.",
                (("#########", "#*..>E.*#", "#########"),),
                13,
                "orqaga() ichida ikki marta chapga(). Keyin: 3 qadam, ol, orqaga, 6 qadam, ol, orqaga, 4 qadam.",
                example="def orqaga():\n    chapga()\n    chapga()\n\norqaga()",
                require=("def",),
            ),
            Level(
                "ikki-qator",
                "Ikki qator",
                "Ikkala qatordagi kristallarni yig'ing.",
                "Ikkala qator bir xil: 5 marta yur va ol. Uni bir marta funksiya qilib yozsangiz, ikki marta "
                "chaqirish kifoya.",
                (("########", "#>*****#", "#E####.#", "#*****.#", "########"),),
                12,
                "qator() funksiyasi, keyin: ongga, 2 qadam, ongga, qator(), ongga, yur.",
                example="def qator():\n    for i in range(5):\n        yur()\n        ol()",
                require=("def",),
            ),
            Level(
                "parametr",
                "Parametr",
                "Spiral yo'ldan bayroqqa yeting.",
                "Funksiya qiymat qabul qilishi mumkin. def qadam(n): deb yozsangiz, qadam(6) chaqirilganda n ning "
                "qiymati 6 bo'ladi. Bir funksiya turli uzunlikdagi yo'llarga yaraydi.",
                (
                    (
                        "#########",
                        "#>......#",
                        "#######.#",
                        "#...E##.#",
                        "#.#####.#",
                        "#.......#",
                        "#########",
                    ),
                ),
                12,
                "Yo'l uzunliklari: 6, 4, 6, 2, 3. Har biridan keyin ongga().",
                example="def qadam(n):\n    for i in range(n):\n        yur()\n\nqadam(6)",
                require=("def",),
            ),
            Level(
                "minoralar",
                "Minoralar",
                "Har minora tepasidagi kristallni oling.",
                "Minoralar balandligi har xil, lekin amal bir xil: chiqish, olish, tushish. Balandlikni parametr "
                "qiling.",
                (
                    (
                        "#########",
                        "####*####",
                        "####.#*##",
                        "##*#.#.##",
                        "#>.....E#",
                        "#########",
                    ),
                ),
                19,
                "minora(n): chapga, n qadam, ol, ikki marta chapga, n qadam, chapga. Balandliklar: 1, 3, 2.",
                require=("def",),
            ),
        ),
    ),
    Chapter(
        "shartlar",
        "Shartlar",
        "if — dastur vaziyatga qarab qaror qiladi",
        "tone-amber",
        COND,
        (
            Level(
                "bormi",
                "Kristall bormi?",
                "Uchchala xaritada ham hamma kristallarni oling.",
                "Bu bosqichda kod 3 xil xaritada tekshiriladi. if kristall_bor(): sharti rost bo'lsagina ichidagi "
                "qator bajariladi. Bo'sh katakda ol() xato beradi, shuning uchun avval tekshiring.",
                (
                    ("#########", "#>*..*.E#", "#########"),
                    ("#########", "#>.*.*.E#", "#########"),
                    ("#########", "#>..***E#", "#########"),
                ),
                4,
                "6 marta: yur(), keyin agar kristall bo'lsa ol().",
                example="yur()\nif kristall_bor():\n    ol()",
                require=("if",),
            ),
            Level(
                "devor-oldida",
                "Devor oldida",
                "Burilish joyi har xil bo'lgan 3 xaritadan o'ting.",
                "Robot oldinda devor borligini biladi: oldinda_devor(). Devor ko'rsa o'ngga burilsin, keyin yursin.",
                (
                    ("#######", "#>..###", "###.###", "###.###", "###.###", "###E###", "#######"),
                    ("#######", "#>....#", "#####.#", "#####E#", "#######"),
                    ("########", "#>.....#", "######E#", "########"),
                ),
                4,
                "6 marta: agar oldinda devor bo'lsa ongga(). Sikl ichida oxirida yur().",
                example="if oldinda_devor():\n    ongga()\nyur()",
                require=("if",),
            ),
            Level(
                "chap-yoki-ong",
                "Chapmi, o'ngmi?",
                "Yo'l chapga ham, o'ngga ham ketishi mumkin. Ikkala xaritadan o'ting.",
                "else qismi shart yolg'on bo'lganda bajariladi. Devorga kelganda chap tomonga qarang: u yerda devor "
                "bo'lsa o'ngga, bo'lmasa chapga buriling.",
                (
                    ("#########", "#>...####", "####.####", "####...E#", "#########"),
                    ("#########", "####...E#", "####.####", "#>...####", "#########"),
                ),
                6,
                "8 marta: oldinda devor bo'lsa ichida yana if chapda_devor() ... else ... Oxirida yur().",
                example="if chapda_devor():\n    ongga()\nelse:\n    chapga()",
                require=("if",),
            ),
            Level(
                "aqlli-qadam",
                "Aqlli qadam",
                "Yo'ldagi hamma kristallarni yig'ing.",
                "Tekshirib yuradigan qadamni funksiya qiling: qadam() ichida yur() va if. Keyin u oddiy buyruqdek "
                "ishlaydi.",
                (
                    ("#######", "#>*..*#", "#####.#", "#E.*..#", "#######"),
                    ("#######", "#>.*..#", "#####*#", "#E*.*.#", "#######"),
                    ("#######", "#>...*#", "#####.#", "#E**.*#", "#######"),
                ),
                12,
                "Yo'l: 4 qadam, ongga, 2 qadam, ongga, 4 qadam.",
                require=("if", "def"),
            ),
        ),
    ),
    Chapter(
        "while",
        "Shart bilan sikl",
        "while shart rost ekan aylanaveradi",
        "tone-emerald",
        WHILE,
        (
            Level(
                "devorgacha",
                "Devorgacha",
                "Yo'l uzunligi har xil. Uchchala xaritada bayroqqa yeting.",
                "Necha marta takrorlash noma'lum bo'lsa, while ishlatiladi. while not oldinda_devor(): — «oldinda "
                "devor bo'lmaguncha» degani.",
                (
                    ("######", "#>..E#", "######"),
                    ("#########", "#>.....E#", "#########"),
                    ("############", "#>........E#", "############"),
                ),
                2,
                "Faqat ikki qator kerak.",
                example="while not oldinda_devor():\n    yur()",
                require=("while",),
            ),
            Level(
                "manzilgacha",
                "Manzilgacha",
                "Bayroq yo'lning qayerida ekani noma'lum. U yerda to'xtang.",
                "yetib_keldi() robot bayroqda turganda True beradi. Bayroqdan o'tib ketmaslik uchun shart shu "
                "bo'lishi kerak.",
                (
                    ("##########", "#>..E....#", "##########"),
                    ("##########", "#>.....E.#", "##########"),
                    ("##########", "#>E......#", "##########"),
                ),
                2,
                "while not yetib_keldi():",
                require=("while",),
            ),
            Level(
                "kristall-ovi",
                "Kristall ovi",
                "Yo'lning uzunligi ham, kristallar joyi ham noma'lum.",
                "while ichida if yozish mumkin. Robot har qadamda yerni tekshiradi.",
                (
                    ("########", "#>*.*.E#", "########"),
                    ("###########", "#>..*.**.E#", "###########"),
                    ("#####", "#>*E#", "#####"),
                ),
                4,
                "Devorgacha yuring, har qadamdan keyin kristallni tekshiring.",
                require=("while", "if"),
            ),
            Level(
                "ong-qol",
                "O'ng qo'l qoidasi",
                "Uchta labirintdan bitta kod bilan chiqing.",
                "Labirintdan chiqish usuli: doim o'ng qo'lingiz devorga tegib tursin. O'ngda yo'l bo'lsa o'ngga "
                "buriling va yuring. Oldinda yo'l bo'lsa yuring. Aks holda chapga buriling. elif — «aks holda, "
                "agar» degani.",
                (
                    (
                        "#########",
                        "#>..#...#",
                        "###.#.#.#",
                        "#...#.#.#",
                        "#.###.#.#",
                        "#.....#E#",
                        "#########",
                    ),
                    (
                        "#########",
                        "#>#...#E#",
                        "#.#.#.#.#",
                        "#.#.#.#.#",
                        "#...#...#",
                        "#########",
                    ),
                    (
                        "#########",
                        "#>....#.#",
                        "#.###.#.#",
                        "#.#...#.#",
                        "#.#.###.#",
                        "#.......#",
                        "#######E#",
                        "#########",
                    ),
                ),
                7,
                "while not yetib_keldi(): ichida if not ongda_devor(): ... elif not oldinda_devor(): ... else: ...",
                example="if not ongda_devor():\n    ongga()\n    yur()\nelif not oldinda_devor():\n    yur()\nelse:\n"
                "    chapga()",
                require=("while", "if"),
            ),
        ),
    ),
    Chapter(
        "ozgaruvchilar",
        "O'zgaruvchilar",
        "Dastur eslab qolishni o'rganadi",
        "tone-rose",
        VARS,
        (
            Level(
                "yarim-yol",
                "Yarim yo'l",
                "Yo'l oxiridagi kristallni oling va bayroqqa qayting. yetib_keldi() ishlatilmaydi.",
                "O'zgaruvchi — qiymat saqlaydigan quti: qadam = 0. Har yurganda qadam = qadam + 1. Bayroq doim yo'l "
                "o'rtasida. // butun bo'lish: 7 // 2 = 3. print(qadam) qiymatni pastdagi oynaga chiqaradi.",
                (
                    ("#######", "#>.E.*#", "#######"),
                    ("#########", "#>..E..*#", "#########"),
                    ("###########", "#>...E...*#", "###########"),
                ),
                9,
                "Sanab boring, ol(), orqaga buriling, keyin range(qadam // 2) marta yuring.",
                example="qadam = 0\nwhile not oldinda_devor():\n    yur()\n    qadam = qadam + 1\nprint(qadam)",
                require=("while", "o'zgaruvchi"),
                forbid=("yetib_keldi",),
            ),
            Level(
                "osuvchi-spiral",
                "O'suvchi spiral",
                "Har safar yo'l bir katakka uzayadi. Bayroqqa yeting.",
                "O'zgaruvchi sikl ichida o'sib borishi mumkin. range(n) ga o'zgaruvchi berish ham mumkin.",
                (
                    (
                        "########",
                        "#.....E#",
                        "#.######",
                        "#.#>.###",
                        "#.##.###",
                        "#....###",
                        "########",
                    ),
                ),
                6,
                "n = 1 dan boshlang. 5 marta: n qadam yuring, ongga(), n = n + 1.",
                require=("for", "o'zgaruvchi"),
            ),
            Level(
                "sanab-ber",
                "Sanab ber",
                "Kristallarni yig'ing, nechta bo'lsa o'ngga o'shancha qadam yuring.",
                "Funksiya natija qaytarishi mumkin: return soni. Chaqirgan joyda uni olasiz: k = yigish(). "
                "yetib_keldi() bu bosqichda ishlatilmaydi.",
                (
                    ("########", "#>.*.*.#", "######.#", "######E#", "######.#", "######.#", "########"),
                    ("########", "#>**.*.#", "######.#", "######.#", "######E#", "######.#", "########"),
                    ("########", "#>...*.#", "######E#", "######.#", "######.#", "######.#", "########"),
                ),
                12,
                "yigish() ichida soni = 0, devorgacha yuring va sanang, oxirida return soni.",
                example="def uch():\n    return 3\n\nk = uch()\nprint(k)",
                require=("def", "return"),
                forbid=("yetib_keldi",),
            ),
            Level(
                "katta-sinov",
                "Katta sinov",
                "Labirintdagi hamma kristallarni yig'ib chiqing. Hamma o'rgangan narsangiz kerak bo'ladi.",
                "Oxirgi bosqich: funksiya, sikl va shartlar birga. O'ng qo'l qoidasini aqlli qadam bilan "
                "birlashtiring.",
                (
                    (
                        "#########",
                        "#>*.#.*.#",
                        "###.#.#*#",
                        "#.*.#.#.#",
                        "#.###.#.#",
                        "#..*..#E#",
                        "#########",
                    ),
                    (
                        "#########",
                        "#>#*..#E#",
                        "#*#.#.#.#",
                        "#.#.#*#*#",
                        "#..*#...#",
                        "#########",
                    ),
                ),
                11,
                "qadam() funksiyasini yozing va o'ng qo'l qoidasida yur() o'rniga shuni chaqiring.",
                require=("def", "while", "if"),
            ),
        ),
    ),
)

ALL_LEVELS: tuple[Level, ...] = tuple(level for chapter in CHAPTERS for level in chapter.levels)
LEVELS: dict[str, Level] = {level.slug: level for level in ALL_LEVELS}
CHAPTER_OF: dict[str, Chapter] = {level.slug: chapter for chapter in CHAPTERS for level in chapter.levels}
MAX_XP = len(ALL_LEVELS) * 3 * XP_PER_STAR


def stars_for(statements: int, par: int) -> int:
    if statements <= par:
        return 3
    return 2 if statements <= par + max(2, par // 2) else 1


def _missing(level: Level, tree: ast.Module) -> str:
    nodes = list(ast.walk(tree))
    for name in level.require:
        if not any(isinstance(node, REQUIRE_NODES[name]) for node in nodes):
            return f"Robot yetib keldi, lekin bu bosqichda «{name}» ishlatish kerak."
    names = {node.id for node in nodes if isinstance(node, ast.Name)}
    for name in level.forbid:
        if name in names:
            return f"Bu bosqichda {name}() ishlatilmaydi. Qadamlarni o'zingiz sanang."
    return ""


def attempt(level: Level, code: str) -> dict:
    """Kodni bosqichning hamma xaritalarida sinaydi. Birinchi yiqilgan xarita ko'rsatiladi."""
    result = {"ok": False, "stars": 0, "events": [], "map_index": 0, "maps_total": len(level.maps), "line": None}
    result["world"] = engine.World(level.maps[0]).as_dict()
    try:
        tree = engine.parse(code)
    except engine.CodeError as error:
        return {**result, "message": error.message, "line": error.line}

    first_events = []
    for index, rows in enumerate(level.maps):
        world = engine.World(rows)
        shown = world.as_dict()
        outcome = engine.execute(tree, world)
        if index == 0:
            first_events = outcome.events
        if not outcome.won:
            message = outcome.error or _unfinished(world)
            where = f"{index + 1}-xaritada: " if len(level.maps) > 1 else ""
            return {
                **result,
                "world": shown,
                "events": outcome.events,
                "map_index": index,
                "message": where + message,
                "line": outcome.line,
            }

    problem = _missing(level, tree)
    if problem:
        return {**result, "events": first_events, "message": problem}
    statements = engine.count_statements(tree)
    return {
        **result,
        "ok": True,
        "stars": stars_for(statements, level.par),
        "events": first_events,
        "statements": statements,
        "par": level.par,
        "message": "Barakalla!",
    }


def _unfinished(world: engine.World) -> str:
    left = len(world.crystals)
    if left:
        return f"Dastur tugadi, lekin {left} ta kristall qoldi."
    return "Dastur tugadi, lekin robot bayroqqa yetmadi."
