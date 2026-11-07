"""O'quvchi portali: panelga kira olmaslik, ro'yxatdan o'tish, o'yin va o'qituvchi bo'limi."""

import json
from datetime import date
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client
from django.urls import get_resolver, reverse
from django.utils import timezone

from apps.finance.models import Transaction
from apps.portal.catalog import BY_SLUG, EVERY_LEVEL, GAME_OF, MAX_XP
from apps.portal.levels import ALL_LEVELS
from apps.portal.models import Attendance, Group, Lesson, LevelProgress, Payment, Post, Student, Submission
from apps.portal.services import (
    PAYMENT_ALERT_DAY,
    RANKS,
    achievements,
    attendance_stats,
    leaderboard,
    parse_month,
    payment_rows,
    pending_homework,
    progress_of,
    rank_for,
    teacher_alerts,
)
from apps.portal.solutions import SOLUTIONS
from apps.security.models import Event, SessionRecord
from tests.test_pages import MODALS, PAGES

User = get_user_model()
HX = {"HTTP_HX_REQUEST": "true"}
PASSWORD = "Robot-2026!"


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def make_student(username="ali", first="Ali", last="Valiyev"):
    user = User.objects.create_user(username, password=PASSWORD, first_name=first, last_name=last)
    return Student.objects.create(user=user)


@pytest.fixture
def student(db):
    return make_student()


@pytest.fixture
def student_client(client, student):
    client.force_login(student.user)
    return client


def run_code(client, slug, code):
    return client.post(reverse("portal_run", args=[slug]), json.dumps({"code": code}), content_type="application/json")


def solve_up_to(student, count):
    for level in EVERY_LEVEL[:count]:
        LevelProgress.objects.create(student=student, level=level.slug, stars=3)


# --- Darvoza: o'quvchi panelni ko'rmasligi kerak ---


def panel_paths():
    """URL ro'yxatidan: yangi sahifa qo'shilsa ham test uni o'zi oladi."""
    paths = []
    for pattern in get_resolver().url_patterns:
        route = str(pattern.pattern)
        if route.startswith(("portal/", "static/")):
            continue
        for sub in getattr(pattern, "url_patterns", [None]):
            full = route + (str(sub.pattern) if sub else "")
            if full.startswith("portal/") or "<" in full or "^" in full:
                continue
            paths.append("/" + full)
    return sorted(set(paths))


@pytest.mark.parametrize("name", PAGES + MODALS)
def test_student_is_kept_out_of_every_panel_page(student_client, data, name):
    response = student_client.get(reverse(name), **HX)
    assert response.status_code == 302
    assert response.url == reverse("portal_home")


@pytest.mark.parametrize("path", panel_paths())
def test_student_is_kept_out_of_every_route(student_client, path):
    response = student_client.get(path)
    assert response.status_code == 302
    assert response.url == reverse("portal_home")


@pytest.mark.parametrize(
    "path", ["/vault/", "/contacts/1/", "/admin/", "/search/?q=a", "/media/x.png", "/students/", "/nonexistent/"]
)
def test_student_is_kept_out_of_sensitive_paths(student_client, path):
    assert student_client.get(path).status_code == 302


def test_student_post_to_panel_changes_nothing(student_client):
    response = student_client.post(reverse("post_create"), {"title": "Buzildi", "kind": "news"})
    assert response.status_code == 302
    assert not Post.objects.exists()


def test_portal_pages_do_not_leak_panel_data(student_client, data):
    for name in ("portal_home", "portal_map", "portal_materials", "portal_rating", "portal_profile"):
        html = student_client.get(reverse(name)).content.decode()
        assert "Login sahifasi" not in html  # vazifa nomi
        assert "Bot token" not in html
        assert "/vault/" not in html


def test_owner_still_reaches_the_panel(client_in, data):
    assert client_in.get(reverse("dashboard")).status_code == 200


# --- Ro'yxatdan o'tish va kirish ---

FORM = {
    "first_name": "Vali",
    "last_name": "Aliyev",
    "username": "vali2012",
    "phone": "+998901234567",
    "password1": PASSWORD,
    "password2": PASSWORD,
}


def test_register_creates_student_and_logs_in(client, db):
    response = client.post(reverse("portal_register"), FORM)
    assert response.status_code == 302
    assert response.url == reverse("portal_home")
    student = Student.objects.get(user__username="vali2012")
    assert student.phone == FORM["phone"]
    assert not student.user.is_staff and not student.user.is_superuser
    assert client.get(reverse("portal_home")).status_code == 200


def test_register_cannot_set_privileges(client, db):
    client.post(reverse("portal_register"), {**FORM, "is_staff": "on", "is_superuser": "on"})
    user = User.objects.get(username="vali2012")
    assert not user.is_staff and not user.is_superuser


def test_register_rejects_weak_password_and_taken_username(client, student):
    response = client.post(
        reverse("portal_register"), {**FORM, "username": "ALI", "password1": "123", "password2": "123"}
    )
    assert response.status_code == 200
    assert Student.objects.count() == 1


def test_honeypot_creates_nothing(client, db):
    response = client.post(reverse("portal_register"), {**FORM, "website": "http://spam"})
    assert response.status_code == 302
    assert not User.objects.exists()


def test_register_is_rate_limited(client, db):
    with mock.patch("apps.portal.views.REGISTER_LIMIT", 1):
        client.post(reverse("portal_register"), FORM)
        client.post(reverse("portal_logout"))
        response = client.post(reverse("portal_register"), {**FORM, "username": "boshqa"})
    assert response.status_code == 200
    assert Student.objects.count() == 1


def test_register_tells_the_teacher(client, db):
    with mock.patch("apps.portal.views.telegram.send_message_async") as send:
        client.post(reverse("portal_register"), {**FORM, "first_name": "<b>Vali"})
    assert "&lt;b&gt;Vali" in send.call_args.args[0]


def test_student_logs_in_through_portal(client, student):
    response = client.post(reverse("portal_login"), {"username": "ali", "password": PASSWORD})
    assert response.status_code == 302
    assert response.url == reverse("portal_home")


def test_owner_cannot_log_in_through_portal(client, user):
    response = client.post(reverse("portal_login"), {"username": user.username, "password": "Parol-2026!"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_portal_error_does_not_reveal_owner_password(client, user):
    right = client.post(reverse("portal_login"), {"username": user.username, "password": "Parol-2026!"})
    wrong = client.post(reverse("portal_login"), {"username": user.username, "password": "xato"})
    assert right.context["form"].non_field_errors() == wrong.context["form"].non_field_errors()


def test_one_child_does_not_lock_the_class(client, student):
    other = make_student("vali")
    for _ in range(6):
        client.post(reverse("portal_login"), {"username": student.user.username, "password": "xato"})
    locked = client.post(reverse("portal_login"), {"username": student.user.username, "password": PASSWORD})
    assert locked.status_code == 200
    response = client.post(reverse("portal_login"), {"username": other.user.username, "password": PASSWORD})
    assert response.status_code == 302


def test_anonymous_goes_to_portal_login(client, db):
    response = client.get(reverse("portal_home"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("portal_login"))


def test_logout_returns_to_portal_login(student_client):
    response = student_client.post(reverse("portal_logout"))
    assert response.url == reverse("portal_login")


def test_blocked_student_is_thrown_out_at_once(student_client, student):
    assert student_client.get(reverse("portal_home")).status_code == 200
    student.user.is_active = False
    student.user.save()
    assert student_client.get(reverse("portal_home")).status_code == 302


# --- Egasining xavfsizlik ogohlantirishlari buzilmasligi ---


def test_student_login_does_not_mark_ip_as_known(client, student):
    """Aks holda o'quvchi IP'sidan panelga kirilganda «yangi IP» ogohlantirishi kelmaydi."""
    with mock.patch("apps.security.services.telegram.send_message_async") as send:
        client.post(reverse("portal_login"), {"username": "ali", "password": PASSWORD})
    send.assert_not_called()
    assert not Event.objects.exists()


def test_owner_login_from_student_ip_still_alerts(client, student, user):
    client.post(reverse("portal_login"), {"username": "ali", "password": PASSWORD})
    client.post(reverse("portal_logout"))
    with mock.patch("apps.security.services.telegram.send_message_async") as send:
        client.post(reverse("login"), {"username": user.username, "password": "Parol-2026!"})
    assert "Yangi IP" in send.call_args.args[0]


def test_failed_student_logins_do_not_raise_alarm(client, student):
    with mock.patch("apps.security.services.telegram.send_message_async") as send:
        for _ in range(6):
            client.post(reverse("portal_login"), {"username": "ali", "password": "xato"})
    send.assert_not_called()
    assert not Event.objects.exists()


def test_failed_panel_logins_are_still_recorded(client, user):
    client.post(reverse("login"), {"username": user.username, "password": "xato"})
    assert Event.objects.filter(kind=Event.Kind.LOGIN_FAIL).count() == 1


def test_student_sessions_stay_out_of_security_page(student_client):
    student_client.get(reverse("portal_home"))
    assert not SessionRecord.objects.exists()


# --- O'yin ---


def test_solving_saves_stars_and_unlocks_next(student_client, student):
    second = ALL_LEVELS[1].slug
    assert student_client.get(reverse("portal_play", args=[second])).status_code == 302

    response = run_code(student_client, "salom-robot", SOLUTIONS["salom-robot"])
    data = response.json()
    assert data["ok"] and data["stars"] == 3 and data["gained"] == 30

    row = student.progress.get(level="salom-robot")
    assert row.stars == 3 and row.attempts == 1 and row.solved_at
    assert row.best_code == SOLUTIONS["salom-robot"]
    assert student_client.get(reverse("portal_play", args=[second])).status_code == 200


def test_locked_level_cannot_be_run(student_client, student):
    response = run_code(student_client, ALL_LEVELS[5].slug, "yur()")
    assert response.status_code == 403
    assert not student.progress.exists()


def test_failed_run_keeps_code_but_gives_no_stars(student_client, student):
    data = run_code(student_client, "salom-robot", "yur()").json()
    assert not data["ok"]
    row = student.progress.get()
    assert row.stars == 0 and row.code == "yur()" and row.attempts == 1 and row.solved_at is None
    assert "yur()" in student_client.get(reverse("portal_play", args=["salom-robot"])).content.decode()


def test_worse_solution_does_not_lower_stars(student_client, student):
    run_code(student_client, "salom-robot", SOLUTIONS["salom-robot"])
    long_code = "chapga()\n" * 8 + SOLUTIONS["salom-robot"]
    data = run_code(student_client, "salom-robot", long_code).json()
    assert data["ok"] and data["stars"] == 1
    assert data["best_stars"] == 3 and data["gained"] == 0
    row = student.progress.get()
    assert row.stars == 3 and row.best_code == SOLUTIONS["salom-robot"] and row.code == long_code


def test_client_cannot_claim_stars(student_client, student):
    body = json.dumps({"code": "yur()", "stars": 3, "ok": True})
    student_client.post(reverse("portal_run", args=["salom-robot"]), body, content_type="application/json")
    assert student.progress.get().stars == 0


@pytest.mark.parametrize("body", ["", "{", "[]", '{"code": 5}', '{"x": 1}', "null"])
def test_bad_run_request(student_client, body):
    response = student_client.post(reverse("portal_run", args=["salom-robot"]), body, content_type="application/json")
    assert response.status_code == 400


def test_huge_code_is_refused_and_not_stored_whole(student_client, student):
    data = run_code(student_client, "salom-robot", "yur()\n" * 5000).json()
    assert not data["ok"]
    assert len(student.progress.get().code) <= 3000


def test_run_is_rate_limited(student_client):
    with mock.patch("apps.portal.views.RUNS_PER_MINUTE", 1):
        assert run_code(student_client, "salom-robot", "yur()").status_code == 200
        assert run_code(student_client, "salom-robot", "yur()").status_code == 429


def test_run_needs_post(student_client):
    assert student_client.get(reverse("portal_run", args=["salom-robot"])).status_code == 405


def test_unknown_level_is_404(student_client):
    assert student_client.get(reverse("portal_play", args=["yoq"])).status_code == 404
    assert run_code(student_client, "yoq", "yur()").status_code == 404


def test_csrf_is_enforced_on_run(student):
    client = Client(enforce_csrf_checks=True)
    client.force_login(student.user)
    assert run_code(client, "salom-robot", "yur()").status_code == 403


def test_teacher_preview_opens_everything_and_saves_nothing(client_in):
    last = ALL_LEVELS[-1].slug
    assert GAME_OF[last].slug == "robot"
    assert client_in.get(reverse("portal_play", args=[last])).status_code == 200
    data = run_code(client_in, last, SOLUTIONS[last]).json()
    assert data["ok"] and data["preview"]
    assert not LevelProgress.objects.exists()


@pytest.mark.parametrize("slug", BY_SLUG)
def test_every_level_page_renders(client_in, slug):
    response = client_in.get(reverse("portal_play", args=[slug]))
    assert response.status_code == 200
    assert 'id="game-data"' in response.content.decode()


def test_solution_is_not_sent_to_the_browser(student_client):
    html = student_client.get(reverse("portal_play", args=["salom-robot"])).content.decode()
    assert "yur()\\nyur()\\nyur()\\nyur()" not in html


# --- Portal sahifalari ---


@pytest.mark.parametrize("name", ["portal_home", "portal_map", "portal_materials", "portal_rating", "portal_profile"])
def test_portal_pages_open(student_client, name):
    assert student_client.get(reverse(name)).status_code == 200


def test_finished_student_home(student_client, student):
    solve_up_to(student, len(EVERY_LEVEL))
    html = student_client.get(reverse("portal_home")).content.decode()
    assert "Hamma bosqichni yechdingiz" in html


def test_rating_hides_surnames_and_blocked_students(student_client, student):
    blocked = make_student("blok", "Bloklangan", "Bola")
    classmate = make_student("sardor", "Sardor", "Karimov")
    LevelProgress.objects.create(student=classmate, level="salom-robot", stars=2)
    LevelProgress.objects.create(student=blocked, level="salom-robot", stars=3)
    blocked.user.is_active = False
    blocked.user.save()
    html = student_client.get(reverse("portal_rating")).content.decode()
    assert "Sardor K." in html
    assert "Karimov" not in html
    assert "Bloklangan" not in html


def test_leaderboard_sorts_by_stars(db):
    first, second = make_student("a"), make_student("b")
    solve_up_to(first, 1)
    solve_up_to(second, 2)
    assert [s.pk for s in leaderboard()] == [second.pk, first.pk]
    assert leaderboard()[0].xp == 60


def test_ranks_cover_the_whole_scale():
    assert rank_for(0)["title"] == RANKS[0][1]
    assert rank_for(MAX_XP)["title"] == RANKS[-1][1]
    assert rank_for(MAX_XP)["percent"] == 100
    assert RANKS[-1][0] <= MAX_XP


def test_materials_show_only_published(student_client):
    Post.objects.create(title="Ochiq dars", kind="material")
    Post.objects.create(title="Qoralama", kind="material", is_published=False)
    html = student_client.get(reverse("portal_materials")).content.decode()
    assert "Ochiq dars" in html and "Qoralama" not in html


def test_post_text_is_escaped(student_client):
    Post.objects.create(title="<script>alert(1)</script>", body="<img src=x onerror=alert(1)>")
    html = student_client.get(reverse("portal_materials")).content.decode()
    assert "<script>alert(1)" not in html and "<img src=x" not in html


def test_student_edits_profile_and_password(student_client, student):
    form = {"p-first_name": "Yangi", "p-last_name": "Ism", "p-phone": "123", "profile": "1"}
    assert student_client.post(reverse("portal_profile"), form).status_code == 302
    student.refresh_from_db()
    student.user.refresh_from_db()
    assert student.user.first_name == "Yangi" and student.phone == "123"

    new = "Boshqa-Parol-1"
    form = {"pw-old_password": PASSWORD, "pw-new_password1": new, "pw-new_password2": new, "password": "1"}
    assert student_client.post(reverse("portal_profile"), form).status_code == 302
    student.user.refresh_from_db()
    assert student.user.check_password(new)
    assert student_client.get(reverse("portal_home")).status_code == 200


def test_student_cannot_change_own_note(student_client, student):
    form = {"p-first_name": "A", "p-last_name": "B", "p-phone": "", "p-note": "hack", "profile": "1"}
    student_client.post(reverse("portal_profile"), form)
    student.refresh_from_db()
    assert student.note == ""


# --- O'qituvchi bo'limi ---


def test_teacher_sees_student_and_code(client_in, student):
    LevelProgress.objects.create(
        student=student, level="salom-robot", stars=2, attempts=3, code="yur()", best_code="yur()"
    )
    assert "Ali Valiyev" in client_in.get(reverse("student_list")).content.decode()
    assert "Salom, robot!" in client_in.get(reverse("student_detail", args=[student.pk])).content.decode()
    html = client_in.get(reverse("student_code", args=[student.pk, "salom-robot"]), **HX).content.decode()
    assert "yur()" in html


def test_teacher_search(client_in, student):
    make_student("boshqa", "Sardor", "Karimov")
    html = client_in.get(reverse("student_list"), {"q": "sardor"}).content.decode()
    assert "Karimov" in html and "Valiyev" not in html


def test_teacher_blocks_student(client_in, student):
    form = {"first_name": "Ali", "last_name": "Valiyev", "phone": "", "note": "Qiynalyapti"}
    response = client_in.post(reverse("student_edit", args=[student.pk]), form, **HX)
    assert response.status_code == 204
    student.refresh_from_db()
    student.user.refresh_from_db()
    assert not student.user.is_active and student.note == "Qiynalyapti"


def test_teacher_form_keeps_active_student_active(client_in, student):
    html = client_in.get(reverse("student_edit", args=[student.pk]), **HX).content.decode()
    assert 'name="is_active"' in html and "checked" in html


def test_teacher_resets_password(client_in, student):
    html = client_in.get(reverse("student_password", args=[student.pk]), **HX).content.decode()
    assert 'name="password"' in html
    response = client_in.post(reverse("student_password", args=[student.pk]), {"password": "yangi-parol-77"}, **HX)
    assert response.status_code == 204
    student.user.refresh_from_db()
    assert student.user.check_password("yangi-parol-77")


def test_password_reset_ends_student_sessions(client, client_in, student):
    child = Client()
    child.force_login(student.user)
    assert child.get(reverse("portal_home")).status_code == 200
    client_in.post(reverse("student_password", args=[student.pk]), {"password": "yangi-parol-77"}, **HX)
    assert child.get(reverse("portal_home")).status_code == 302


def test_teacher_cannot_set_weak_password(client_in, student):
    client_in.post(reverse("student_password", args=[student.pk]), {"password": "123"}, **HX)
    student.user.refresh_from_db()
    assert student.user.check_password(PASSWORD)


def test_teacher_deletes_student_with_account(client_in, student):
    LevelProgress.objects.create(student=student, level="salom-robot", stars=1)
    response = client_in.post(reverse("student_delete", args=[student.pk]), **HX)
    assert response.headers["HX-Redirect"] == reverse("student_list")
    assert not Student.objects.exists()
    assert not User.objects.filter(username="ali").exists()
    assert not LevelProgress.objects.exists()


def test_delete_needs_post(client_in, student):
    assert client_in.get(reverse("student_delete", args=[student.pk])).status_code == 405
    assert Student.objects.exists()


def test_post_crud(client_in):
    form = {"title": "Dars", "kind": "homework", "is_published": "on"}
    assert client_in.post(reverse("post_create"), form, **HX).status_code == 204
    post = Post.objects.get()
    assert "Dars" in client_in.get(reverse("post_list")).content.decode()
    assert client_in.post(reverse("post_edit", args=[post.pk]), {**form, "title": "Yangi"}, **HX).status_code == 204
    post.refresh_from_db()
    assert post.title == "Yangi"
    assert client_in.post(reverse("post_delete", args=[post.pk]), **HX).status_code == 204
    assert not Post.objects.exists()


def test_post_link_must_be_web_address(client_in):
    form = {"title": "Dars", "kind": "news", "url": "javascript:alert(1)"}
    assert client_in.post(reverse("post_create"), form, **HX).status_code == 200
    assert not Post.objects.exists()


def test_teacher_nav_has_students(client_in):
    html = client_in.get(reverse("dashboard")).content.decode()
    assert reverse("student_list") in html and reverse("post_list") in html


# --- Guruhlar ---


@pytest.fixture
def group(db):
    return Group.objects.create(name="Python 1", schedule="Du, Cho 16:00", monthly_fee=300_000)


@pytest.fixture
def member(student, group):
    student.group = group
    student.save()
    return student


def test_group_crud(client_in):
    form = {"name": "Boshlovchilar", "schedule": "Sesh", "monthly_fee": "250 000", "is_active": "on"}
    assert client_in.post(reverse("group_create"), form, **HX).status_code == 204
    group = Group.objects.get()
    assert group.monthly_fee == 250_000
    assert client_in.get(reverse("group_detail", args=[group.pk])).status_code == 200
    assert client_in.get(reverse("group_edit", args=[group.pk]), **HX).status_code == 200
    assert client_in.post(reverse("group_delete", args=[group.pk]), **HX).status_code == 204
    assert not Group.objects.exists()


def test_deleting_group_keeps_students(client_in, member, group):
    client_in.post(reverse("group_delete", args=[group.pk]), **HX)
    member.refresh_from_db()
    assert member.group is None


def test_deleting_group_never_opens_its_posts_to_everyone(client_in, group):
    Post.objects.create(title="Maxsus", group=group)
    client_in.post(reverse("group_delete", args=[group.pk]), **HX)
    assert not Post.objects.exists()


def test_teacher_assigns_group_and_filters(client_in, student, group):
    form = {"first_name": "Ali", "last_name": "Valiyev", "group": group.pk, "phone": "", "note": "", "is_active": "on"}
    assert client_in.post(reverse("student_edit", args=[student.pk]), form, **HX).status_code == 204
    student.refresh_from_db()
    assert student.group == group
    make_student("boshqa", "Sardor", "Karimov")
    html = client_in.get(reverse("student_list"), {"group": group.pk}).content.decode()
    assert "Valiyev" in html and "Karimov" not in html


def test_group_post_is_visible_only_inside_group(student_client, member, group):
    other = Group.objects.create(name="Boshqa")
    Post.objects.create(title="Hammaga")
    Post.objects.create(title="Bizning guruh", group=group)
    Post.objects.create(title="Begona guruh", group=other)
    for name in ("portal_materials", "portal_home"):
        html = student_client.get(reverse(name)).content.decode()
        assert "Hammaga" in html and "Bizning guruh" in html and "Begona guruh" not in html


def test_student_without_group_sees_only_common_posts(student_client, group):
    Post.objects.create(title="Hammaga")
    Post.objects.create(title="Guruhniki", group=group)
    html = student_client.get(reverse("portal_materials")).content.decode()
    assert "Hammaga" in html and "Guruhniki" not in html


# --- Davomat ---


def test_attendance_is_saved_and_shown_to_student(client_in, member, group):
    url = reverse("lesson_edit", args=[group.pk, "2026-11-02"])
    assert f'name="s{member.pk}"' in client_in.get(url).content.decode()
    response = client_in.post(url, {"topic": "Sikllar", f"s{member.pk}": "absent"})
    assert response.status_code == 302
    mark = Attendance.objects.get()
    assert mark.status == "absent" and mark.lesson.topic == "Sikllar"
    assert client_in.post(url, {"topic": "Sikllar", f"s{member.pk}": "late"}).status_code == 302
    assert Attendance.objects.get().status == "late"
    assert attendance_stats(member) == {"total": 1, "came": 1, "absent": 0, "percent": 100}


def test_attendance_bad_input(client_in, member, group):
    assert client_in.get(reverse("lesson_edit", args=[group.pk, "emas"])).status_code == 404
    client_in.post(reverse("lesson_edit", args=[group.pk, "2026-11-02"]), {f"s{member.pk}": "hack"})
    assert not Attendance.objects.exists()


def test_attendance_cannot_touch_other_groups(client_in, member, group):
    outsider = make_student("tashqi")
    client_in.post(reverse("lesson_edit", args=[group.pk, "2026-11-02"]), {f"s{outsider.pk}": "present"})
    assert not Attendance.objects.filter(student=outsider).exists()


def test_attendance_stats_without_lessons(student):
    assert attendance_stats(student)["percent"] is None


# --- Uy vazifalari ---


@pytest.fixture
def homework(db):
    return Post.objects.create(title="Sikl mashqi", kind="homework")


def submit(client, post, **form):
    return client.post(reverse("portal_homework", args=[post.pk]), form)


def test_student_submits_and_teacher_accepts(student_client, user, student, homework):
    client_in = Client()
    client_in.force_login(user)
    assert student_client.get(reverse("portal_homework", args=[homework.pk])).status_code == 200
    assert submit(student_client, homework, text="for i in range(3)").status_code == 302
    row = student.submissions.get()
    assert row.status == "submitted"
    assert "Sikl mashqi" in client_in.get(reverse("review_list")).content.decode()
    assert "for i in range(3)" in client_in.get(reverse("review_edit", args=[row.pk]), **HX).content.decode()

    form = {"status": "accepted", "grade": "5", "feedback": "Zo'r"}
    assert client_in.post(reverse("review_edit", args=[row.pk]), form, **HX).status_code == 204
    row.refresh_from_db()
    assert row.grade == 5 and row.reviewed_at
    assert "Zo&#x27;r" in student_client.get(reverse("portal_homework", args=[homework.pk])).content.decode()


def test_accepted_answer_is_locked(student_client, student, homework):
    Submission.objects.create(post=homework, student=student, text="eski", status="accepted", grade=5)
    submit(student_client, homework, text="yangi")
    row = student.submissions.get()
    assert row.text == "eski" and row.grade == 5


def test_returned_answer_can_be_resubmitted(student_client, student, homework):
    Submission.objects.create(post=homework, student=student, text="eski", status="returned", feedback="Qayta")
    assert pending_homework(student) == 1
    submit(student_client, homework, text="yangi")
    row = student.submissions.get()
    assert row.text == "yangi" and row.status == "submitted"
    assert pending_homework(student) == 0


def test_empty_answer_is_refused(student_client, student, homework):
    assert submit(student_client, homework, text="  ").status_code == 200
    assert not student.submissions.exists()


def test_answer_link_must_be_web_address(student_client, student, homework):
    assert submit(student_client, homework, url="javascript:alert(1)").status_code == 200
    assert not student.submissions.exists()


def test_accept_needs_grade_and_return_clears_it(client_in, student, homework):
    row = Submission.objects.create(post=homework, student=student, text="a", grade=4)
    url = reverse("review_edit", args=[row.pk])
    assert client_in.post(url, {"status": "accepted", "grade": ""}, **HX).status_code == 200
    assert client_in.post(url, {"status": "returned", "feedback": "Qayta"}, **HX).status_code == 204
    row.refresh_from_db()
    assert row.status == "returned" and row.grade is None


@pytest.mark.parametrize("grade", ["0", "6", "x"])
def test_bad_grade_is_refused(client_in, student, homework, grade):
    row = Submission.objects.create(post=homework, student=student, text="a")
    form = {"status": "accepted", "grade": grade}
    assert client_in.post(reverse("review_edit", args=[row.pk]), form, **HX).status_code == 200


def test_other_groups_homework_is_404(student_client, group):
    post = Post.objects.create(title="Begona", kind="homework", group=group)
    assert student_client.get(reverse("portal_homework", args=[post.pk])).status_code == 404
    assert submit(student_client, post, text="x").status_code == 404
    assert not Submission.objects.exists()


@pytest.mark.parametrize("field", [{"kind": "news"}, {"kind": "homework", "is_published": False}])
def test_only_published_homework_accepts_answers(student_client, field):
    post = Post.objects.create(title="X", **field)
    assert student_client.get(reverse("portal_homework", args=[post.pk])).status_code == 404


def test_student_answer_is_escaped_for_teacher(client_in, student, homework):
    row = Submission.objects.create(post=homework, student=student, text="<script>alert(1)</script>")
    html = client_in.get(reverse("review_edit", args=[row.pk]), **HX).content.decode()
    assert "<script>alert(1)" not in html


# --- To'lovlar ---

NOV = date(2026, 11, 1)


def pay(client, student, amount="300 000", month="2026-11"):
    form = {"amount": amount, "method": "cash", "date": "2026-11-05"}
    return client.post(reverse("payment_create", args=[student.pk]) + f"?month={month}", form, **HX)


def test_payment_goes_to_finance(client_in, member):
    assert pay(client_in, member).status_code == 204
    entry = Transaction.objects.get()
    assert entry.kind == "income" and entry.amount == 300_000
    assert entry.category.name == "O'quv to'lovi"
    assert "Ali Valiyev" in entry.description
    assert member.payments.get().month == NOV


def test_partial_payments_add_up(client_in, member):
    pay(client_in, member, "100 000")
    assert payment_rows(NOV)[0].left == 200_000
    pay(client_in, member, "200 000")
    row = payment_rows(NOV)[0]
    assert row.paid == 300_000 and row.left == 0


def test_payment_page_totals(client_in, member):
    pay(client_in, member, "100 000")
    response = client_in.get(reverse("payment_list"), {"month": "2026-11"})
    assert response.context["expected"] == 300_000
    assert response.context["collected"] == 100_000
    assert response.context["left"] == 200_000


def test_finance_edit_changes_tuition(client_in, member):
    """Summa bitta joyda: moliyada tuzatilsa, o'quv to'lovi ham o'zgaradi."""
    pay(client_in, member)
    Transaction.objects.update(amount=150_000)
    assert payment_rows(NOV)[0].paid == 150_000


def test_deleting_finance_entry_removes_payment(client_in, member):
    pay(client_in, member)
    Transaction.objects.get().delete()
    assert not Payment.objects.exists()


def test_deleting_payment_removes_finance_entry(client_in, member):
    pay(client_in, member)
    response = client_in.post(reverse("payment_delete", args=[Payment.objects.get().pk]), **HX)
    assert response.status_code == 204
    assert not Transaction.objects.exists()


def test_deleting_student_keeps_income(client_in, member):
    pay(client_in, member)
    client_in.post(reverse("student_delete", args=[member.pk]), **HX)
    assert Transaction.objects.count() == 1
    assert not Payment.objects.exists()


def test_who_owes(member, group):
    blocked = make_student("blok")
    Student.objects.filter(pk=blocked.pk).update(group=group)
    User.objects.filter(pk=blocked.user_id).update(is_active=False)
    free = Group.objects.create(name="Bepul")
    Student.objects.filter(pk=make_student("bepul").pk).update(group=free)
    make_student("guruhsiz")
    assert [row.student.pk for row in payment_rows(services_month())] == [member.pk]


def services_month():
    return timezone.localdate().replace(day=1)


def test_student_who_joined_later_owes_nothing_for_old_months(member):
    assert payment_rows(date(2020, 1, 1)) == []


def test_former_member_payment_stays_visible(client_in, member):
    pay(client_in, member)
    Student.objects.filter(pk=member.pk).update(group=None)
    row = payment_rows(NOV)[0]
    assert row.paid == 300_000 and row.left == 0


@pytest.mark.parametrize("amount", ["0", "-5", "abc", ""])
def test_bad_payment_amount(client_in, member, amount):
    assert pay(client_in, member, amount).status_code == 200
    assert not Transaction.objects.exists()


@pytest.mark.parametrize("value", ["2026-13", "x", "", None, "2026-11-05"])
def test_bad_month_falls_back_to_current(value):
    assert parse_month(value) == services_month()


def test_money_is_invisible_to_student(student_client, member):
    assert student_client.get(reverse("payment_list")).status_code == 302
    assert student_client.get(reverse("payment_create", args=[member.pk])).status_code == 302
    assert "so'm" not in student_client.get(reverse("portal_home")).content.decode()


# --- Yutuqlar va ogohlantirishlar ---


def earned(student):
    return {a["title"] for a in achievements(student, progress_of(student)) if a["earned"]}


def test_achievements(student):
    assert earned(student) == set()
    solve_up_to(student, 4)
    assert earned(student) == {"Birinchi qadam", "Birinchi qadamlar"}
    LevelProgress.objects.all().delete()
    solve_up_to(student, len(EVERY_LEVEL))
    assert {"Uch yulduz", "Mukammal", "O'zgaruvchilar", "Kod rassomi", "Xato ovchisi"} <= earned(student)


def test_attendance_and_grade_achievements(student, group):
    for day in range(1, 11):
        lesson = Lesson.objects.create(group=group, date=date(2026, 11, day))
        Attendance.objects.create(lesson=lesson, student=student)
    for n in range(3):
        post = Post.objects.create(title=str(n), kind="homework")
        Submission.objects.create(post=post, student=student, status="accepted", grade=5)
    assert {"Intizomli", "A'lochi"} <= earned(student)


def test_achievements_show_on_profile(student_client):
    assert "Yutuqlar" in student_client.get(reverse("portal_profile")).content.decode()


def test_run_returns_new_xp_total(student_client):
    assert run_code(student_client, "salom-robot", SOLUTIONS["salom-robot"]).json()["xp"] == 30


def test_teacher_alerts(member, homework):
    Submission.objects.create(post=homework, student=member, text="a")
    assert "uy vazifasi" in teacher_alerts(date(2026, 11, 2))[0]["title"]
    assert len(teacher_alerts(date(2026, 11, 2))) == 1, "oy boshida to'lov haqida gapirilmaydi"
    late = timezone.localdate().replace(day=PAYMENT_ALERT_DAY)
    assert "to'lamagan" in teacher_alerts(late)[1]["title"]


def test_dashboard_shows_portal_alerts(client_in, member, homework):
    Submission.objects.create(post=homework, student=member, text="a")
    assert "uy vazifasi tekshirilmagan" in client_in.get(reverse("dashboard")).content.decode()


# --- O'zbekcha xabarlar ---


@pytest.mark.parametrize(
    ("change", "field", "fragment"),
    [
        ({"username": "ali 2012!"}, "username", "Loginda faqat"),
        ({"username": "ALI"}, "username", "band"),
        ({"password1": "123", "password2": "123"}, "password2", "juda qisqa"),
        ({"password1": "password", "password2": "password"}, "password2", "juda oddiy"),
    ],
)
def test_register_errors_are_in_uzbek(client, student, change, field, fragment):
    response = client.post(reverse("portal_register"), {**FORM, **change})
    errors = response.context["form"].errors[field]
    assert any(fragment in error for error in errors)
    assert not any("password" in error.lower() or "username" in error.lower() for error in errors)


def test_profile_password_help_is_short_and_uzbek(student_client):
    html = student_client.get(reverse("portal_profile")).content.decode()
    assert "Your password" not in html
    assert "Kamida 8 ta belgi" in html
