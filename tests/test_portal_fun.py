"""Oson o'yinlar (Rostmi?, Pufakcha, Kod iloni), kiyim va kunlik seriya."""

import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.portal import catalog, engine
from apps.portal.catalog import BY_SLUG, GAME_BY_SLUG
from apps.portal.games import BadPayload, bubbles, snake, truth
from apps.portal.levels import ALL_LEVELS
from apps.portal.models import LevelProgress, Student

TRUTH = GAME_BY_SLUG["rostmi"].levels
BUBBLES = GAME_BY_SLUG["pufak"].levels
SNAKE = GAME_BY_SLUG["ilon"].levels


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def child(client, db):
    user = get_user_model().objects.create_user("ali", password="Robot-2026!", first_name="Ali")
    client.student = Student.objects.create(user=user)
    client.force_login(user)
    return client


def send(client, slug, body):
    return client.post(reverse("portal_run", args=[slug]), json.dumps(body), content_type="application/json")


# --- Rostmi? ---


def truths(level):
    return [truth.truth_of(card) for card in level.cards]


@pytest.mark.parametrize("level", TRUTH, ids=lambda level: level.slug)
def test_truth_cards_are_balanced_and_explained(level):
    values = truths(level)
    assert 2 <= sum(values) <= len(values) - 2, "faqat bitta tugmani bosib o'tib bo'lmasin"
    assert all(card.why for card in level.cards)


def test_truth_hand_checked_values():
    assert truths(TRUTH[0]) == [True, False, True, False, True, True, False, False]


def test_truth_multiline_card():
    assert truth.truth_of(truth.Card("x = 3\nx = 7\nx == 3", "")) is False


def test_truth_config_has_no_answers():
    config = truth.config(TRUTH[0], None)
    assert set(config) == {"cards", "lives"}
    assert all(isinstance(card, str) for card in config["cards"])


def test_truth_perfect_round(child):
    level = TRUTH[0]
    data = send(child, level.slug, {"answers": truths(level)}).json()
    assert data["ok"] and data["stars"] == 3
    assert child.student.progress.get().stars == 3


def test_truth_partial_not_saved_and_explained(child):
    data = send(child, TRUTH[0].slug, {"answers": [False]}).json()
    assert not data["correct"] and data["lives"] == 2 and data["why"]
    assert not child.student.progress.exists()


def test_truth_three_mistakes_end_round():
    level = TRUTH[0]
    wrong = [not value for value in truths(level)][:3]
    result = truth.attempt(level, {"answers": wrong}, 0)
    assert result["finished"] and not result["ok"]


@pytest.mark.parametrize("answers", [[], [1], ["x"], [None], [True] * 9, "x", None])
def test_truth_rejects_forged_requests(answers):
    with pytest.raises(BadPayload):
        truth.attempt(TRUTH[0], {"answers": answers}, 0)


# --- Pufakcha ---


def good_ids(level):
    return [i for i, text in enumerate(bubbles.bubbles_of(level)) if level.rule(text)]


@pytest.mark.parametrize("level", BUBBLES, ids=lambda level: level.slug)
def test_bubble_level_is_fair(level):
    assert len(set(level.items)) == len(level.items)
    assert 4 <= len(good_ids(level)) <= len(level.items) - 4


def test_bubble_rules_hand_checked():
    numbers = BY_SLUG["pufak-natija"]
    assert numbers.rule("2 * 5") and numbers.rule("100 // 10") and not numbers.rule("4 * 3")
    names = BY_SLUG["pufak-nom"]
    assert names.rule("ball_1") and not names.rule("2son") and not names.rule("for") and not names.rule("a-b")


@pytest.mark.parametrize("level", BUBBLES, ids=lambda level: level.slug)
def test_bubble_perfect_round_ends_early(level):
    result = bubbles.attempt(level, {"pops": good_ids(level)}, 0)
    assert result["ok"] and result["stars"] == 3 and result["finished"]


def test_bubble_config_has_no_answers():
    assert set(bubbles.config(BUBBLES[0], None)) == {"items"}


def test_bubble_half_is_enough_to_pass():
    level = BUBBLES[0]
    half = good_ids(level)[: (len(good_ids(level)) + 1) // 2]
    result = bubbles.attempt(level, {"pops": half, "done": True}, 0)
    assert result["ok"] and result["stars"] == 1


def test_bubble_too_few_fails_kindly():
    level = BUBBLES[0]
    result = bubbles.attempt(level, {"pops": good_ids(level)[:1], "done": True}, 0)
    assert not result["ok"] and result["finished"] and result["message"]


def test_bubble_no_pops_at_all_is_a_valid_end():
    assert not bubbles.attempt(BUBBLES[0], {"pops": [], "done": True}, 0)["ok"]


def test_bubble_popping_everything_is_not_three_stars():
    level = BUBBLES[0]
    result = bubbles.attempt(level, {"pops": list(range(len(level.items))), "done": True}, 0)
    assert result["stars"] < 3


def test_bubble_partial_not_saved(child):
    level = BUBBLES[0]
    data = send(child, level.slug, {"pops": good_ids(level)[:1]}).json()
    assert data["hit"] is True
    assert not child.student.progress.exists()


@pytest.mark.parametrize(
    "body",
    [
        {"pops": []},
        {"pops": [99]},
        {"pops": [0, 0]},
        {"pops": ["a"]},
        {"pops": [True]},
        {"pops": "x"},
        {"pops": [0], "done": 1},
    ],
)
def test_bubble_rejects_forged_requests(body):
    with pytest.raises(BadPayload):
        bubbles.attempt(BUBBLES[0], body, 0)


# --- Kod iloni ---


def perfect_meal(level):
    meal = []
    for number, line in enumerate(level.lines):
        tiles = list(snake.tiles_of(line))
        for token in snake.tokens_of(line):
            index = tiles.index(token)
            tiles[index] = None
            meal.append([number, index])
    return meal


def wrong_bite(level):
    line = level.lines[0]
    first = snake.tokens_of(line)[0]
    return [0, next(i for i, text in enumerate(snake.tiles_of(line)) if text != first)]


@pytest.mark.parametrize("level", SNAKE, ids=lambda level: level.slug)
def test_snake_level_can_be_finished(level):
    result = snake.attempt(level, {"eaten": perfect_meal(level)}, 0)
    assert result["ok"] and result["stars"] == 3


@pytest.mark.parametrize("level", SNAKE, ids=lambda level: level.slug)
def test_snake_lines_are_real_python(level):
    for line in level.lines:
        if line.code != "else:":
            engine.parse(line.code + "\n    pass" if line.code.endswith(":") else line.code)
        assert set(line.extra).isdisjoint(snake.tokens_of(line)), "chalg'ituvchi so'z qatorda bo'lmasin"


def test_snake_tokens():
    assert snake.tokens_of(snake.Line("", 'print("Salom bola")')) == ("print", "(", '"Salom bola"', ")")


def test_snake_double_equals_is_one_word():
    assert "==" in snake.tokens_of(snake.Line("", "if x == 0:"))


def test_snake_config_does_not_reveal_order():
    line = SNAKE[0].lines[0]
    config = snake.config(SNAKE[0], None)["lines"][0]
    assert set(config) == {"goal", "tiles", "size"}
    assert sorted(config["tiles"]) == sorted([*snake.tokens_of(line), *line.extra])


def test_snake_same_word_twice_works():
    level = BY_SLUG["ilon-quti"]
    assert snake.tokens_of(level.lines[1]).count("x") == 2
    assert snake.attempt(level, {"eaten": perfect_meal(level)}, 0)["ok"]


def test_snake_wrong_word_costs_a_heart_not_the_game():
    level = SNAKE[0]
    result = snake.attempt(level, {"eaten": [wrong_bite(level)]}, 0)
    assert not result["right"] and result["lives"] == snake.LIVES - 1 and not result["finished"]


def test_snake_forgives_one_accidental_bite():
    level = SNAKE[0]
    result = snake.attempt(level, {"eaten": [wrong_bite(level), *perfect_meal(level)]}, 0)
    assert result["ok"] and result["stars"] == 3


def test_snake_more_mistakes_cost_stars():
    assert [snake.stars_for(n) for n in (0, 1, 2, 3, 4)] == [3, 3, 2, 2, 1]


def test_snake_running_out_of_hearts_ends_game():
    level = SNAKE[0]
    result = snake.attempt(level, {"eaten": [wrong_bite(level)] * snake.LIVES}, 0)
    assert result["finished"] and not result["ok"]


def test_snake_partial_not_saved(child):
    level = SNAKE[0]
    data = send(child, level.slug, {"eaten": perfect_meal(level)[:1]}).json()
    assert data["right"] and data["built"]
    assert not child.student.progress.exists()


def test_snake_run_saves_stars(child):
    level = SNAKE[0]
    assert send(child, level.slug, {"eaten": perfect_meal(level)}).json()["ok"]
    assert child.student.progress.get().stars == 3


@pytest.mark.parametrize(
    "eaten", [[], [[0, 99]], [[5, 0]], [[1, 0]], [[0]], [["a", 0]], [[True, 0]], "x", [[0, 0]] * 101]
)
def test_snake_rejects_forged_requests(eaten):
    with pytest.raises(BadPayload):
        snake.attempt(SNAKE[0], {"eaten": eaten}, 0)


def test_snake_cannot_keep_playing_after_game_over():
    level = SNAKE[0]
    with pytest.raises(BadPayload):
        snake.attempt(level, {"eaten": [wrong_bite(level)] * (snake.LIVES + 1)}, 0)


# --- Kiyim va seriya ---


def play_once(client):
    send(client, ALL_LEVELS[0].slug, {"code": "yur()"})
    client.student.refresh_from_db()


def test_first_game_of_the_day_starts_streak(child):
    play_once(child)
    assert child.student.streak == 1 and child.student.last_played == timezone.localdate()


def test_same_day_does_not_grow_streak(child):
    play_once(child)
    play_once(child)
    assert child.student.streak == 1


def test_next_day_grows_streak_and_gap_resets_it(child):
    today = timezone.localdate()
    Student.objects.filter(pk=child.student.pk).update(streak=4, last_played=today - timedelta(days=1))
    play_once(child)
    assert child.student.streak == 5 and child.student.best_streak == 5
    Student.objects.filter(pk=child.student.pk).update(last_played=today - timedelta(days=3))
    play_once(child)
    assert child.student.streak == 1 and child.student.best_streak == 5


def test_broken_streak_is_not_shown(child):
    last = timezone.localdate() - timedelta(days=2)
    Student.objects.filter(pk=child.student.pk).update(streak=9, last_played=last)
    child.student.refresh_from_db()
    assert child.student.live_streak == 0


def test_locked_skin_cannot_be_worn(child):
    assert child.post(reverse("portal_skin"), {"skin": "fuchsia"}).status_code == 302
    child.student.refresh_from_db()
    assert child.student.skin == "indigo"


def test_unknown_skin_is_refused(child):
    child.post(reverse("portal_skin"), {"skin": "<script>"})
    child.student.refresh_from_db()
    assert child.student.skin == "indigo"


def test_earned_skin_is_worn_and_coloured(child):
    for level in ALL_LEVELS[:4]:
        LevelProgress.objects.create(student=child.student, level=level.slug, stars=3)
    child.post(reverse("portal_skin"), {"skin": "cyan"})
    child.student.refresh_from_db()
    assert child.student.skin == "cyan"
    assert "#06b6d4" in child.get(reverse("portal_home")).content.decode()


def test_skin_needs_post(child):
    assert child.get(reverse("portal_skin")).status_code == 405


def test_skin_list_shows_on_profile(child):
    assert "Robot kiyimi" in child.get(reverse("portal_profile")).content.decode()


# --- Osonlashtirish ---


def test_one_extra_command_still_earns_three_stars():
    level = BY_SLUG["salom-robot"]
    result = catalog._robot_attempt(level, {"code": "yur()\n" * 4 + "chapga()\n"}, 0)
    assert result["ok"] and result["stars"] == 3


def test_new_games_are_listed_first(child):
    assert [game.slug for game in catalog.GAMES[:3]] == ["pufak", "rostmi", "ilon"]
    html = child.get(reverse("portal_map")).content.decode()
    assert html.index("Pufakcha") < html.index("Sehrli mashina")


def test_profile_password_form_is_in_uzbek(child):
    html = child.get(reverse("portal_profile")).content.decode()
    assert "Old password" not in html and "Hozirgi parol" in html
