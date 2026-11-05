"""Takrorlanish: sana qoidalari, takroriy vazifalar va takroriy to'lovlar."""

import json
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.core.dates import next_occurrence
from apps.dashboard.digest import build_digest
from apps.finance.models import Category, Kind, Recurring, Transaction
from apps.planner.models import Task

HX = {"HTTP_HX_REQUEST": "true"}


@pytest.mark.parametrize(
    "freq,day,expected",
    [
        ("daily", date(2026, 11, 5), date(2026, 11, 6)),
        ("workdays", date(2026, 11, 6), date(2026, 11, 9)),  # juma → dushanba
        ("workdays", date(2026, 11, 7), date(2026, 11, 9)),  # shanba → dushanba
        ("weekly", date(2026, 12, 28), date(2027, 1, 4)),
        ("monthly", date(2026, 12, 15), date(2027, 1, 15)),
        ("yearly", date(2028, 2, 29), date(2029, 2, 28)),
    ],
)
def test_next_occurrence(freq, day, expected):
    assert next_occurrence(freq, day) == expected


def test_month_end_does_not_stick_to_short_month():
    feb = next_occurrence("monthly", date(2026, 1, 31), anchor_day=31)
    assert feb == date(2026, 2, 28)
    assert next_occurrence("monthly", feb, anchor_day=31) == date(2026, 3, 31)


def test_next_occurrence_skips_past_after():
    assert next_occurrence("weekly", date(2026, 1, 1), after=date(2026, 1, 22)) == date(2026, 1, 29)


# --- Takroriy vazifalar -------------------------------------------------------------------


def _task(**extra):
    today = timezone.localdate()
    return Task.objects.create(**{"title": "Hisobot", "repeat": "weekly", "planned_for": today, **extra})


def test_done_task_creates_next(client_in):
    task = _task(priority=4, notes="izoh")
    client_in.post(reverse("task_toggle", args=[task.pk]), **HX)
    nxt = Task.objects.exclude(pk=task.pk).get()
    assert nxt.status == Task.Status.TODO and nxt.repeat == "weekly"
    assert nxt.planned_for == task.planned_for + timedelta(days=7)
    assert (nxt.priority, nxt.notes) == (4, "izoh")


def test_reopen_and_redo_does_not_duplicate(client_in):
    task = _task()
    for _ in range(3):
        client_in.post(reverse("task_toggle", args=[task.pk]), **HX)
    assert Task.objects.count() == 2


def test_overdue_daily_task_lands_after_today(client_in):
    today = timezone.localdate()
    task = _task(repeat="daily", planned_for=today - timedelta(days=10), due_date=today - timedelta(days=8))
    client_in.post(reverse("task_toggle", args=[task.pk]), **HX)
    nxt = Task.objects.exclude(pk=task.pk).get()
    assert nxt.planned_for == today + timedelta(days=1)
    assert nxt.due_date == nxt.planned_for + timedelta(days=2)  # reja va muddat orasidagi farq saqlanadi


def test_due_only_task_stays_due_only(client_in):
    today = timezone.localdate()
    task = _task(planned_for=None, due_date=today)
    client_in.post(reverse("task_toggle", args=[task.pk]), **HX)
    nxt = Task.objects.exclude(pk=task.pk).get()
    assert nxt.planned_for is None and nxt.due_date == today + timedelta(days=7)


def test_kanban_and_edit_also_spawn(client_in):
    moved = _task()
    resp = client_in.post(
        reverse("task_move", args=[moved.pk]),
        json.dumps({"stage": "done", "order": [moved.pk]}),
        content_type="application/json",
    )
    assert resp.status_code == 200 and Task.objects.count() == 2

    edited = _task(title="Tahrir")
    payload = {"title": "Tahrir", "status": "done", "priority": 2, "repeat": "weekly"}
    assert client_in.post(reverse("task_edit", args=[edited.pk]), payload, **HX).status_code == 204
    assert Task.objects.filter(title="Tahrir").count() == 2


def test_plain_task_does_not_repeat(client_in):
    task = _task(repeat="")
    client_in.post(reverse("task_toggle", args=[task.pk]), **HX)
    assert Task.objects.count() == 1


def test_month_end_task_keeps_its_day(db):
    from apps.planner.services import spawn_next

    task = Task.objects.create(title="Soliq", repeat="monthly", status="done", due_date=date(2099, 1, 31))
    nxt = spawn_next(task)
    assert nxt.due_date == date(2099, 2, 28) and nxt.repeat_day == 31
    nxt.status = "done"
    assert spawn_next(nxt).due_date == date(2099, 3, 31)


# --- Takroriy to'lovlar -------------------------------------------------------------------


def _create(client_in, **extra):
    payload = {
        "title": "Ofis ijarasi",
        "kind": "expense",
        "amount": "2 000 000",
        "currency": "UZS",
        "frequency": "monthly",
        "next_date": timezone.localdate().isoformat(),
        "method": "card",
        "is_active": "on",
    }
    payload.update(extra)
    resp = client_in.post(reverse("recurring_create"), payload, **HX)
    assert resp.status_code == 204, resp.content
    return Recurring.objects.get(title=payload["title"])


def _period(item):
    return {"period": item.next_date.isoformat()}


def test_post_writes_transaction_and_advances(client_in):
    item = _create(client_in)
    first = item.next_date
    client_in.post(reverse("recurring_post", args=[item.pk]), _period(item), **HX)
    tx = Transaction.objects.get()
    assert (tx.kind, tx.amount, tx.date, tx.description) == (Kind.EXPENSE, 2_000_000, first, "Ofis ijarasi")
    item.refresh_from_db()
    assert item.next_date > first


def test_double_click_writes_once(client_in):
    item = _create(client_in)
    period = _period(item)
    for _ in range(2):
        assert client_in.post(reverse("recurring_post", args=[item.pk]), period, **HX).status_code == 204
    assert Transaction.objects.count() == 1


def test_missing_period_changes_nothing(client_in):
    item = _create(client_in)
    client_in.post(reverse("recurring_post", args=[item.pk]), **HX)
    assert not Transaction.objects.exists()


def test_late_period_keeps_its_date_and_early_uses_today(client_in):
    today = timezone.localdate()
    late = _create(client_in, title="Kechikkan", next_date=(today - timedelta(days=40)).isoformat())
    period = late.next_date
    client_in.post(reverse("recurring_post", args=[late.pk]), _period(late), **HX)
    assert Transaction.objects.get(description="Kechikkan").date == period
    late.refresh_from_db()
    assert late.is_due  # yana bir davr kutib turibdi: o'tkazib yuborilgan oylar yo'qolmaydi

    early = _create(client_in, title="Oldindan", next_date=(today + timedelta(days=5)).isoformat())
    client_in.post(reverse("recurring_post", args=[early.pk]), _period(early), **HX)
    assert Transaction.objects.get(description="Oldindan").date == today


def test_skip_advances_without_transaction(client_in):
    item = _create(client_in)
    first = item.next_date
    client_in.post(reverse("recurring_skip", args=[item.pk]), _period(item), **HX)
    item.refresh_from_db()
    assert item.next_date > first and not Transaction.objects.exists()


def test_month_end_anchor_saved_from_form(client_in):
    item = _create(client_in, next_date="2099-01-31")
    assert item.anchor_day == 31
    client_in.post(reverse("recurring_post", args=[item.pk]), _period(item), **HX)
    item.refresh_from_db()
    assert item.next_date == date(2099, 2, 28)
    client_in.post(reverse("recurring_post", args=[item.pk]), _period(item), **HX)
    item.refresh_from_db()
    assert item.next_date == date(2099, 3, 31)


def test_without_anchor_keeps_day_of_month(db):
    item = Recurring.objects.create(title="Admin", amount=1, next_date=date(2099, 1, 15))
    assert item.following() == date(2099, 2, 15)


def test_form_rejects_wrong_category_and_zero(client_in):
    income = Category.objects.filter(kind="income").first()
    payload = {
        "title": "X",
        "kind": "expense",
        "amount": "0",
        "currency": "UZS",
        "frequency": "monthly",
        "next_date": timezone.localdate().isoformat(),
        "method": "card",
        "category": income.pk,
    }
    resp = client_in.post(reverse("recurring_create"), payload, **HX)
    assert resp.status_code == 200 and not Recurring.objects.exists()


def test_monthly_equivalent_on_list(client_in):
    _create(client_in, title="Domen", frequency="yearly", amount="1 200 000")
    assert client_in.get(reverse("recurring_list")).context["monthly_expense"]["UZS"] == 100_000


def test_paused_is_not_due_and_alerts_only_when_due(client_in):
    item = _create(client_in)
    assert "Ofis ijarasi" in build_digest()
    assert any("Ofis ijarasi" in a["title"] for a in client_in.get(reverse("dashboard")).context["alerts"])
    Recurring.objects.filter(pk=item.pk).update(is_active=False)
    assert "Ofis ijarasi" not in build_digest()
