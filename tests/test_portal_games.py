"""Robotdan boshqa o'yinlar: yechiladi, baho serverda va soxtalashtirib bo'lmaydi."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils.html import escape

from apps.portal import catalog, engine
from apps.portal.catalog import BY_SLUG, EVERY_LEVEL, GAME_BY_SLUG, GAMES
from apps.portal.games import BadPayload, bugs, draw, machine, puzzle, quiz
from apps.portal.levels import ALL_LEVELS
from apps.portal.models import LevelProgress, Student

DRAW = GAME_BY_SLUG["rassom"].levels
MACHINE = GAME_BY_SLUG["mashina"].levels
PUZZLE = GAME_BY_SLUG["jumboq"].levels
QUIZ = GAME_BY_SLUG["detektiv"].levels
BUGS = GAME_BY_SLUG["xato"].levels

FIXES = {
    "xato-son": "for i in range(4):\n    yur()\n",
    "xato-surilish": "for i in range(6):\n    yur()\n    ol()\nyur()\n",
    "xato-tomon": "yur()\nyur()\nongga()\nyur()\nyur()\nchapga()\nyur()\n",
    "xato-shart": "for i in range(6):\n    yur()\n    if kristall_bor():\n        ol()\n",
    "xato-chaqiruv": "def yetkaz():\n    for i in range(4):\n        yur()\nyetkaz()\n",
    "xato-cheksiz": "n = 0\nwhile n < 3:\n    yur()\n    n = n + 1\n",
}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def child(client, db):
    user = get_user_model().objects.create_user("ali", password="Robot-2026!", first_name="Ali")
    student = Student.objects.create(user=user)
    client.force_login(user)
    client.student = student
    return client


def send(client, slug, body):
    return client.post(reverse("portal_run", args=[slug]), json.dumps(body), content_type="application/json")


def picks(level, code=None):
    """To'g'ri kodni brauzer yuboradigan ko'rinishga o'tkazadi."""
    tiles = list(puzzle.tiles_of(level))
    rows = []
    for line in (code or level.answer).strip().splitlines():
        rows.append([tiles.index(line.strip()), (len(line) - len(line.lstrip())) // 4])
    return {"lines": rows}


def right_answers(level):
    return [quiz.options_of(q).index(quiz.answer_of(q)) for q in level.questions]


def wrong_index(question):
    return next(i for i, text in enumerate(quiz.options_of(question)) if text != quiz.answer_of(question))


# --- Katalog ---


def test_there_are_six_different_games():
    assert len(GAMES) == 6
    assert len({game.template for game in GAMES}) == 5  # Xato ovchisi robot taxtasidan foydalanadi


def test_slugs_are_unique_across_games():
    assert len(BY_SLUG) == len(EVERY_LEVEL)


def test_robot_slugs_are_kept_so_old_results_survive():
    assert [level.slug for level in GAME_BY_SLUG["robot"].levels] == [level.slug for level in ALL_LEVELS]
    assert ALL_LEVELS[0].slug == "salom-robot"


def test_every_game_has_stars_scale():
    assert catalog.MAX_XP == len(EVERY_LEVEL) * 30


def test_hub_and_maps_open(child):
    html = child.get(reverse("portal_map")).content.decode()
    for game in GAMES:
        assert escape(game.title) in html
        assert child.get(reverse("portal_game", args=[game.slug])).status_code == 200


def test_unknown_game_is_404(child):
    assert child.get(reverse("portal_game", args=["yoq"])).status_code == 404


def test_each_game_has_its_own_path(child):
    for game in GAMES:
        first, second = game.levels[0].slug, game.levels[1].slug
        assert child.get(reverse("portal_play", args=[first])).status_code == 200
        assert child.get(reverse("portal_play", args=[second])).status_code == 302


def test_solving_one_game_does_not_unlock_another(child):
    LevelProgress.objects.create(student=child.student, level=ALL_LEVELS[0].slug, stars=3)
    assert child.get(reverse("portal_play", args=[ALL_LEVELS[1].slug])).status_code == 200
    assert child.get(reverse("portal_play", args=[DRAW[1].slug])).status_code == 302


def test_last_level_returns_to_game_map(child):
    last = BUGS[-1]
    for level in BUGS[:-1]:
        LevelProgress.objects.create(student=child.student, level=level.slug, stars=1)
    response = child.get(reverse("portal_play", args=[last.slug]))
    assert response.context["config"]["isLast"] is True
    assert response.context["config"]["nextUrl"] == reverse("portal_game", args=["xato"])


@pytest.mark.parametrize("game", GAMES, ids=lambda game: game.slug)
@pytest.mark.parametrize("body", [{}, {"code": 5}, {"lines": "x"}, {"answers": "x"}, {"code": None, "answers": None}])
def test_malformed_payload_is_400_in_every_game(child, game, body):
    assert send(child, game.levels[0].slug, body).status_code == 400
    assert not LevelProgress.objects.exists()


# --- Kod rassomi ---


def draw_code(level, code):
    return draw.attempt(level, {"code": code}, 0)


SQUARE = BY_SLUG["rassom-kvadrat"]


@pytest.mark.parametrize("level", DRAW, ids=lambda level: level.slug)
def test_draw_solution_earns_three_stars(level):
    result = draw_code(level, level.solution)
    assert result["ok"] and result["stars"] == 3 and result["percent"] >= 99


@pytest.mark.parametrize("level", DRAW, ids=lambda level: level.slug)
def test_draw_target_stays_on_paper(level):
    for x1, y1, x2, y2, _ in draw.target_of(level):
        assert all(0 <= value <= draw.SIZE for value in (x1, y1, x2, y2))


def test_draw_split_line_counts_as_same_drawing():
    line = BY_SLUG["rassom-chiziq"]
    assert draw_code(line, "oldinga(120)\noldinga(120)")["ok"]


def test_draw_reversed_direction_counts():
    line = BY_SLUG["rassom-chiziq"]
    assert draw_code(line, "qalam_ol()\noldinga(240)\nqalam_qoy()\norqaga(240)")["ok"]


@pytest.mark.parametrize(
    "code",
    [
        "oldinga(160)\nongga(90)\noldinga(160)\nongga(90)\noldinga(160)",  # bir tomoni yo'q
        "for i in range(4):\n    oldinga(120)\n    ongga(90)",  # kichik
        "for i in range(4):\n    oldinga(160)\n    ongga(90)\nchapga(45)\noldinga(100)",  # ortiqcha chiziq
        'rang("qizil")\nfor i in range(4):\n    oldinga(160)\n    ongga(90)',  # boshqa rang
        "ongga(45)",  # hech narsa chizilmagan
        "",
    ],
)
def test_draw_wrong_picture_fails(code):
    result = draw_code(SQUARE, code)
    assert not result["ok"]
    assert result["stars"] == 0


def test_draw_requires_concept():
    level = BY_SLUG["rassom-uchburchak"]
    code = "oldinga(180)\nongga(120)\noldinga(180)\nongga(120)\noldinga(180)"
    result = draw_code(level, code)
    assert not result["ok"] and "for" in result["message"]


@pytest.mark.parametrize(
    ("code", "fragment"),
    [
        ("oldinga(1000)", "chiqib ketdi"),
        ('rang("pushti")', "Bunday rang"),
        ('oldinga("a")', "butun son"),
        ("oldinga()", "1 ta qiymat"),
        ("qalam_ol(1)", "hech narsa olmaydi"),
        ("while True:\n    ongga(1)", "charchadi"),
        ("yur()", "nom yo'q"),
        ("import os", "import"),
    ],
)
def test_draw_mistakes_are_explained(code, fragment):
    assert fragment in draw_code(SQUARE, code)["message"]


def test_draw_page_shows_target_but_not_solution(child):
    html = child.get(reverse("portal_play", args=[DRAW[0].slug])).content.decode()
    assert "target" in html
    assert "oldinga(240)" not in html


def test_draw_run_saves_stars(child):
    data = send(child, DRAW[0].slug, {"code": DRAW[0].solution}).json()
    assert data["ok"] and data["gained"] == 30
    assert child.student.progress.get().stars == 3


# --- Sehrli mashina ---


def machine_code(level, code):
    return machine.attempt(level, {"code": code}, 0)


@pytest.mark.parametrize("level", MACHINE, ids=lambda level: level.slug)
def test_machine_solution_earns_three_stars(level):
    result = machine_code(level, level.solution)
    assert result["ok"] and result["stars"] == 3
    assert all(row["ok"] for row in result["rows"])


@pytest.mark.parametrize("level", MACHINE, ids=lambda level: level.slug)
def test_machine_starter_is_not_already_right(level):
    assert not machine_code(level, level.starter)["ok"]


@pytest.mark.parametrize("level", MACHINE, ids=lambda level: level.slug)
def test_memorized_samples_are_caught_by_hidden_tests(level):
    lines = []
    params = ", ".join(f"p{i}" for i in range(len(level.samples[0])))
    for args in level.samples:
        test = " and ".join(f"p{i} == {arg}" for i, arg in enumerate(args))
        expected = machine.show(level.reference(*args))
        lines.append(f"    if {test}:\n        return {expected}")
    code = f"def mashina({params}):\n" + "\n".join(lines) + "\n    return 0\n"
    result = machine_code(level, code)
    assert not result["ok"]


def test_machine_type_must_match():
    level = BY_SLUG["mashina-juft"]
    assert not machine_code(level, "def mashina(son):\n    return True\n")["ok"]
    number = BY_SLUG["mashina-qoshuvchi"]
    assert not machine_code(number, 'def mashina(son):\n    return "2"\n')["ok"]


@pytest.mark.parametrize(
    ("code", "fragment"),
    [
        ("x = 1", "funksiya yozing"),
        ("def boshqa(son):\n    return son", "funksiya yozing"),
        ("def mashina(son):\n    son + 1", "return"),
        ("def mashina():\n    return 1", "qiymat kutadi"),
        ("def mashina(son):\n    while True:\n        pass", "cheksiz"),
        ("def mashina(son):\n    return mashina(son)", "juda ko'p"),
        ("def mashina(son):\n    break", "sikl ichida"),
        ("def mashina(son)\n    return 1", "ikki nuqta"),
    ],
)
def test_machine_mistakes_are_explained(code, fragment):
    result = machine_code(BY_SLUG["mashina-qoshuvchi"], code)
    assert not result["ok"]
    assert fragment in result["message"]


def test_machine_hidden_inputs_stay_secret_until_they_fail():
    level = BY_SLUG["mashina-qoshuvchi"]
    config = machine.config(level, None)
    assert len(config["rows"]) == len(level.samples)
    assert config["hidden"] == len(level.hidden)
    assert "99" not in json.dumps(config)
    passed = machine_code(level, level.solution)
    assert len(passed["rows"]) == len(level.samples)


def test_machine_failed_hidden_test_is_shown():
    level = BY_SLUG["mashina-musbat"]
    result = machine_code(
        level, "def mashina(son):\n    if son == -5 or son == -1:\n        return -son\n    return son\n"
    )
    assert "Yashirin" in result["message"]
    assert result["rows"][-1]["input"] == "-100"


def test_machine_each_test_has_its_own_step_budget():
    level = BY_SLUG["mashina-jami"]
    assert machine_code(level, level.solution)["ok"]


def test_machine_page_hides_solution(child):
    html = child.get(reverse("portal_play", args=[MACHINE[0].slug])).content.decode()
    assert "son + 1" not in html.replace("return son + 2", "").replace(MACHINE[0].hint, "")


# --- Kod jumboq ---


@pytest.mark.parametrize("level", PUZZLE, ids=lambda level: level.slug)
def test_puzzle_answer_solves(level):
    result = puzzle.attempt(level, picks(level), 0)
    assert result["ok"] and result["stars"] == 3


@pytest.mark.parametrize("level", [lvl for lvl in PUZZLE if len(puzzle.tiles_of(lvl)) > 2], ids=lambda lvl: lvl.slug)
def test_puzzle_tiles_are_shuffled_or_unindented(level):
    assert all(tile == tile.strip() for tile in puzzle.tiles_of(level))


def test_puzzle_wrong_indent_fails():
    level = BY_SLUG["jumboq-yigindi"]
    code = "s = 0\nfor i in range(1, 4):\n    s = s + i\n    print(s)\n"
    result = puzzle.attempt(level, picks(level, code), 0)
    assert not result["ok"]
    assert result["output"] == ["1", "3", "6"]


def test_puzzle_syntax_error_is_explained():
    level = BY_SLUG["jumboq-sikl"]
    assert "surilishi" in puzzle.attempt(level, picks(level, "for i in range(3):\nprint(i)"), 0)["message"]


def test_puzzle_other_valid_order_is_accepted():
    level = BY_SLUG["jumboq-ayirma"]
    assert puzzle.attempt(level, picks(level, "b = 4\na = 10\nprint(a - b)"), 0)["ok"]


def test_puzzle_stars_depend_on_tries():
    level = PUZZLE[0]
    assert [puzzle.attempt(level, picks(level), n)["stars"] for n in (0, 1, 2, 3, 9)] == [3, 2, 2, 1, 1]


def test_puzzle_empty_program_is_not_a_win():
    assert not puzzle.attempt(PUZZLE[0], {"lines": []}, 0)["ok"]


@pytest.mark.parametrize(
    "lines",
    [
        [[99, 0]],
        [[-1, 0]],
        [[0, 9]],
        [[0, -1]],
        [[0, 0], [0, 0]],
        [["print(1)", 0]],
        [[0]],
        [[0, 0, 0]],
        [[True, 0]],
        [[0.5, 0]],
        "print(1)",
        [[0, 0]] * 50,
    ],
)
def test_puzzle_rejects_forged_requests(lines):
    with pytest.raises(BadPayload):
        puzzle.attempt(PUZZLE[0], {"lines": lines}, 0)


def test_puzzle_cannot_inject_code(child):
    response = send(child, PUZZLE[0].slug, {"code": 'print("Salom")', "lines": [['print("Salom")', 0]]})
    assert response.status_code == 400


def test_puzzle_run_saves_assembled_code(child):
    level = PUZZLE[0]
    send(child, level.slug, picks(level))
    row = child.student.progress.get()
    assert row.stars == 3 and row.code == level.answer.strip()


def test_puzzle_second_try_cannot_reach_three_stars(child):
    level = PUZZLE[0]
    send(child, level.slug, {"lines": []})
    data = send(child, level.slug, picks(level)).json()
    assert data["ok"] and data["stars"] == 2


# --- Kod detektivi ---


@pytest.mark.parametrize("level", QUIZ, ids=lambda level: level.slug)
def test_quiz_questions_are_sound(level):
    assert len(level.questions) == 5
    for question in level.questions:
        answer = quiz.answer_of(question)
        assert answer not in question.wrong, question.code
        assert len(set(quiz.options_of(question))) == 4


def test_quiz_config_has_no_answers():
    config = quiz.config(QUIZ[0], None)
    assert set(config["questions"][0]) == {"code", "options"}


def test_quiz_correct_answer_is_not_always_first():
    positions = {index for level in QUIZ for index in right_answers(level)}
    assert len(positions) >= 3


def test_quiz_perfect_round():
    level = QUIZ[0]
    result = quiz.attempt(level, {"answers": right_answers(level)}, 0)
    assert result["ok"] and result["stars"] == 3 and result["finished"]


def test_quiz_mistakes_cost_stars():
    level = QUIZ[0]
    answers = right_answers(level)
    answers[0] = wrong_index(level.questions[0])
    assert quiz.attempt(level, {"answers": answers}, 0)["stars"] == 2
    answers[1] = wrong_index(level.questions[1])
    assert quiz.attempt(level, {"answers": answers}, 0)["stars"] == 1


def test_quiz_three_mistakes_end_the_round():
    level = QUIZ[0]
    answers = [wrong_index(q) for q in level.questions[:3]]
    result = quiz.attempt(level, {"answers": answers}, 0)
    assert result["finished"] and not result["ok"] and result["lives"] == 0 and result["stars"] == 0


def test_quiz_partial_answer_is_not_saved(child):
    level = QUIZ[0]
    data = send(child, level.slug, {"answers": right_answers(level)[:1]}).json()
    assert data["correct"] and not data["finished"]
    assert not child.student.progress.exists()


def test_quiz_finished_round_is_saved(child):
    level = QUIZ[0]
    data = send(child, level.slug, {"answers": right_answers(level)}).json()
    assert data["ok"] and data["gained"] == 30
    assert child.student.progress.get().stars == 3


@pytest.mark.parametrize("answers", [[], [9], [-1], ["0"], [True], [0, 0, 0, 0, 0, 0], "x", None])
def test_quiz_rejects_forged_requests(answers):
    with pytest.raises(BadPayload):
        quiz.attempt(QUIZ[0], {"answers": answers}, 0)


# --- Xato ovchisi ---


def test_every_bug_level_has_a_fix():
    assert set(FIXES) == {level.slug for level in BUGS}


@pytest.mark.parametrize("level", BUGS, ids=lambda level: level.slug)
def test_buggy_code_really_fails(level):
    assert not bugs.attempt(level, {"code": level.starter}, 0)["ok"]


@pytest.mark.parametrize("level", BUGS, ids=lambda level: level.slug)
def test_small_fix_earns_three_stars(level):
    result = bugs.attempt(level, {"code": FIXES[level.slug]}, 0)
    assert result["ok"], result["message"]
    assert result["stars"] == 3 and result["changes"] == level.changes == 1


def test_rewriting_everything_earns_less():
    level = BY_SLUG["xato-tomon"]
    rewrite = "for i in range(2):\n    yur()\nongga()\nfor i in range(2):\n    yur()\nchapga()\nyur()\n"
    result = bugs.attempt(level, {"code": rewrite}, 0)
    assert result["ok"] and result["stars"] < 3


def test_changed_lines_is_not_fooled_by_repeated_lines():
    before = "yur()\nyur()\nchapga()\nyur()\nyur()\nchapga()\nyur()"
    assert bugs.changed_lines(before, before.replace("chapga", "ongga", 1)) == 1


def test_changed_lines_counts_replacement_once():
    assert bugs.changed_lines("a\nb\nc", "a\nx\nc") == 1
    assert bugs.changed_lines("a\nb", "a\nb\nc") == 1
    assert bugs.changed_lines("a\nb\n", "a\nb") == 0


def test_bug_page_starts_with_broken_code(child):
    html = child.get(reverse("portal_play", args=[BUGS[0].slug])).content.decode()
    assert "range(3)" in html
    assert "Buzilgan kodni qaytarish" in html


def test_robot_page_has_no_restore_button(child):
    assert "Buzilgan kodni" not in child.get(reverse("portal_play", args=[ALL_LEVELS[0].slug])).content.decode()


# --- Interpretator umumiyligi ---


def test_plain_interpreter_has_no_robot_commands():
    outcome = engine.capture(engine.Interpreter(), engine.parse("yur()"))
    assert "nom yo'q" in outcome.error


def test_break_cannot_escape_a_function():
    outcome = engine.capture(engine.Interpreter(), engine.parse("def f():\n    break\nfor i in range(3):\n    f()"))
    assert "sikl ichida" in outcome.error
