"""3D o'yinlar: sahna brauzerda, lekin baho serverda. Kutubxona repoda bo'lishi shart: serverda Node yo'q."""

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

from apps.portal.catalog import BY_SLUG, GAME_BY_SLUG
from apps.portal.games import quiz
from apps.portal.models import Student

RACE = GAME_BY_SLUG["poyga"].levels


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


def right_answers(level):
    return [quiz.options_of(q).index(quiz.answer_of(q)) for q in level.questions]


def test_three_is_one_self_contained_file():
    path = Path(settings.BASE_DIR) / "static/vendor/three/three.module.min.js"
    source = path.read_text()
    assert 300_000 < len(source) < 1_500_000
    assert "three.core" not in source, "ikkinchi faylni so'ramasin: u repoda yo'q"


@pytest.mark.parametrize("level", RACE, ids=lambda level: level.slug)
def test_race_questions_are_sound(level):
    assert len(level.questions) == 5
    for question in level.questions:
        answer = quiz.answer_of(question)
        assert answer not in question.wrong, question.code
        assert question.why
        assert len(set(quiz.options_of(question))) == 4
        assert all(len(text) <= 8 for text in quiz.options_of(question)), "darvozada o'qilsin"


def test_race_round_is_graded_on_server(child):
    level = RACE[0]
    data = send(child, level.slug, {"answers": right_answers(level)}).json()
    assert data["ok"] and data["stars"] == 3
    assert child.student.progress.get().stars == 3


def test_race_page_has_no_answers(child):
    response = child.get(reverse("portal_play", args=[RACE[0].slug]))
    assert set(response.context["config"]["questions"][0]) == {"code", "options"}
    assert "portal-race.js" in response.content.decode()


def test_robot_page_loads_3d_before_the_game(child):
    html = child.get(reverse("portal_play", args=["salom-robot"])).content.decode()
    assert html.index("portal-board3d.js") < html.index("portal-game.js")


def test_other_games_do_not_download_3d(child):
    html = child.get(reverse("portal_play", args=[BY_SLUG["pufak-juft"].slug])).content.decode()
    assert "three" not in html and "board3d" not in html
