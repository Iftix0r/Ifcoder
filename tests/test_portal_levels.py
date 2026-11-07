"""Har bir bosqich yechiladi, 3 yulduzga yetadi, interpretator esa xavfli kodni bajarmaydi."""

import pytest

from apps.portal import engine
from apps.portal.levels import ALL_LEVELS, LEVELS, REQUIRE_NODES, attempt, stars_for
from apps.portal.solutions import SOLUTIONS


def run(code, rows=("#####", "#>..#", "#####")):
    world = engine.World(rows)
    return engine.execute(engine.parse(code), world), world


def test_every_level_has_a_solution():
    assert set(SOLUTIONS) == set(LEVELS)
    assert len(LEVELS) == len(ALL_LEVELS), "slug takrorlangan"


@pytest.mark.parametrize("slug", SOLUTIONS)
def test_level_is_solvable_with_three_stars(slug):
    result = attempt(LEVELS[slug], SOLUTIONS[slug])
    assert result["ok"], result["message"]
    assert result["stars"] == 3, f"{result['statements']} buyruq, par {result['par']}"
    assert result["statements"] == LEVELS[slug].par


@pytest.mark.parametrize("level", ALL_LEVELS, ids=lambda level: level.slug)
def test_level_data_is_valid(level):
    assert set(level.require) <= set(REQUIRE_NODES)
    for rows in level.maps:
        assert len({len(row) for row in rows}) == 1, "xarita qatorlari teng emas"
        text = "".join(rows)
        assert sum(text.count(mark) for mark in engine.START_MARKS) == 1, "robot bitta bo'lsin"
        assert text.count("E") == 1
        assert set(rows[0]) == {"#"} and set(rows[-1]) == {"#"}


@pytest.mark.parametrize(
    "slug", [level.slug for level in ALL_LEVELS if len(level.maps) > 1 and level.slug != "katta-sinov"]
)
def test_memorized_single_map_fails_on_others(slug):
    """Bir nechta xarita yodlangan kodni ushlaydi: birinchi xaritaning harakatlari boshqasiga yaramaydi."""
    level = LEVELS[slug]
    moves = attempt(level, SOLUTIONS[slug])["events"]
    names = {"move": "yur()", "take": "ol()"}
    code = "\n".join(names.get(e["a"]) or ("ongga()" if e.get("side") == 1 else "chapga()") for e in moves)
    assert not attempt(level, code)["ok"]


def test_required_concept_is_enforced():
    result = attempt(LEVELS["uzun-yol"], "yur()\n" * 10)
    assert not result["ok"]
    assert "for" in result["message"]


def test_forbidden_command_is_enforced():
    code = (
        "while not oldinda_devor():\n    yur()\nol()\nchapga()\nchapga()\nwhile not yetib_keldi():\n    yur()\nx = 1\n"
    )
    result = attempt(LEVELS["yarim-yol"], code)
    assert not result["ok"]
    assert "yetib_keldi" in result["message"]


def test_stars_count_statements_not_lines():
    one_line = attempt(LEVELS["salom-robot"], "yur(); yur(); yur(); yur(); chapga(); chapga(); chapga(); chapga()")
    assert one_line["ok"] and one_line["stars"] == 1
    assert stars_for(4, 4) == 3 and stars_for(6, 4) == 2 and stars_for(7, 4) == 1


def test_failed_map_is_reported_with_its_own_world():
    result = attempt(LEVELS["devorgacha"], "yur()\nyur()\nyur()\n")
    assert not result["ok"]
    assert result["map_index"] == 1
    assert result["world"]["width"] == 9
    assert result["message"].startswith("2-xaritada")


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "from os import system",
        "__import__('os').system('id')",
        "open('/etc/passwd')",
        "eval('1')",
        "exec('x=1')",
        "print.__class__",
        "().__class__",
        "class A:\n    pass",
        "x = [1]",
        "lambda: 1",
        "getattr(print, 'x')",
        "def f():\n    pass\nf.__globals__",
        "f'{1}'",
        "with open('x') as f:\n    pass",
        "x: int = 1",
    ],
)
def test_dangerous_code_is_refused(code):
    outcome, _ = run(code)
    assert outcome.error
    assert not outcome.won


@pytest.mark.parametrize(
    ("code", "fragment"),
    [
        ("while True:\n    pass", "cheksiz"),
        ("while True:\n    chapga()", "charchadi"),
        ("def f():\n    f()\nf()", "juda ko'p"),
        ("x = 2\nwhile True:\n    x = x * x", "juda katta"),
        ("for i in range(10**11):\n    pass", ""),
        ("x = " + "not " * 700 + "1", ""),
        ("x = " + "-" * 900 + "1", ""),
        ("x = 1 // 0", "Nolga"),
        ("x = 1 / 2", "//"),
        ("x = 'a' * 5", "sonlar"),
        ("print(1)\n" * 60, "print"),
        ("return", "funksiya ichida"),
        ("break", "sikl ichida"),
    ],
)
def test_runaway_code_stops_with_an_error(code, fragment):
    try:
        outcome, _ = run(code)
    except engine.CodeError as error:  # parse bosqichida to'xtagan
        assert fragment in error.message
        return
    assert outcome.error
    assert fragment in outcome.error


@pytest.mark.parametrize("code", ["\x00", "(" * 500, "x" * (engine.MAX_CODE + 1), "yur(", "if True\n    yur()"])
def test_broken_source_is_a_clear_error(code):
    with pytest.raises(engine.CodeError):
        engine.parse(code)


@pytest.mark.parametrize(
    ("code", "line", "fragment"),
    [
        ("yur()\nyurr()", 2, "yur"),
        ("yur", 1, "qavs"),
        ("for i in range(2)\n    yur()", 1, "ikki nuqta"),
        ("for i in range(2):\nyur()", 2, "surilishi"),
        ("yur()\n    yur()", 2, "ortiqcha"),
        ("yur = 3", 1, "band nom"),
        ("def ol():\n    pass", 1, "band nom"),
    ],
)
def test_mistakes_are_explained_in_uzbek(code, line, fragment):
    try:
        outcome, _ = run(code)
        message, where = outcome.error, outcome.line
    except engine.CodeError as error:
        message, where = error.message, error.line
    assert fragment in message
    assert where == line


def test_python_semantics():
    code = """
def ikki(n):
    return n * 2

s = 0
for i in range(1, 7, 2):
    if i == 3:
        continue
    s += i
while True:
    s = s + ikki(2)
    break
print(s, 7 % 3, -1, 1 < 2 < 3, not False, True and 5, 0 or 'a')
"""
    outcome, _ = run(code)
    assert not outcome.error
    assert outcome.events[-1]["text"] == "10 1 -1 True True 5 a"


def test_function_scope_is_local():
    outcome, _ = run("def f():\n    y = 1\nf()\nprint(y)")
    assert "nom yo'q" in outcome.error


def test_crash_keeps_events_for_animation():
    outcome, world = run("yur()\nyur()\nyur()")
    assert outcome.error == "Robot devorga urildi!"
    assert outcome.line == 3
    assert [e["a"] for e in outcome.events] == ["move", "move", "crash"]
    assert (world.x, world.y) == (3, 1)
