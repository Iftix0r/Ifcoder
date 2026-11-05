"""Byudjet limitlari, CSV eksport va kalendar."""

import csv
import io
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.dashboard.digest import build_digest
from apps.dashboard.views import calendar_events
from apps.finance.models import Budget, Category, Credit, Kind, Recurring, Transaction
from apps.finance.views import budget_rows
from apps.planner.models import Task

HX = {"HTTP_HX_REQUEST": "true"}


def _expense_category():
    return Category.objects.filter(kind="expense").first()


def _spend(category, amount, **extra):
    return Transaction.objects.create(kind=Kind.EXPENSE, amount=amount, category=category, **extra)


def _month():
    return timezone.localdate().replace(day=1)


def test_budget_tracks_month_currency_and_kind(db):
    category = _expense_category()
    Budget.objects.create(category=category, amount=1000)
    _spend(category, 300)
    _spend(category, 999, currency="USD")  # boshqa valyuta hisobga kirmaydi
    _spend(category, 999, date=_month() - timedelta(days=1))  # o'tgan oy ham
    Transaction.objects.create(kind=Kind.INCOME, amount=999, category=category)
    row = budget_rows(_month())[0]
    assert (row["spent"], row["left"], row["pct"], row["over"]) == (300, 700, 30, False)
    assert row["bar"] == "bg-emerald-500"


def test_budget_warns_then_goes_over(client_in):
    category = _expense_category()
    Budget.objects.create(category=category, amount=1000)
    _spend(category, 800)
    assert budget_rows(_month())[0]["bar"] == "bg-amber-500"
    assert "Limit oshdi" not in build_digest()
    _spend(category, 400)
    row = budget_rows(_month())[0]
    assert row["over"] and row["width"] == 100 and row["pct"] == 120 and row["bar"] == "bg-rose-500"
    assert "Limit oshdi" in build_digest()
    assert any("limiti oshdi" in a["title"] for a in client_in.get(reverse("dashboard")).context["alerts"])
    assert category.name in client_in.get(reverse("finance_overview")).content.decode()


def test_exactly_at_limit_is_not_over(db):
    category = _expense_category()
    Budget.objects.create(category=category, amount=1000)
    _spend(category, 1000)
    assert budget_rows(_month())[0]["over"] is False


def test_budget_form_rejects_income_category_and_duplicate(client_in):
    expense = _expense_category()
    income = Category.objects.filter(kind="income").first()
    url = reverse("budget_create")
    payload = {"category": expense.pk, "amount": "1 000", "currency": "UZS"}
    assert client_in.post(url, payload, **HX).status_code == 204
    assert client_in.post(url, payload, **HX).status_code == 200  # shu toifa+valyuta allaqachon bor
    assert client_in.post(url, {**payload, "category": income.pk, "currency": "USD"}, **HX).status_code == 200
    assert Budget.objects.count() == 1


def _rows(resp):
    text = resp.content.decode("utf-8")
    assert text.startswith("﻿")
    return list(csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";"))


def test_csv_export_matches_filters(client_in):
    category = _expense_category()
    _spend(category, 1500, description="Hosting")
    Transaction.objects.create(kind=Kind.INCOME, amount="99.50", description="Kirim")
    url = reverse("transaction_export")
    resp = client_in.get(url)
    assert "attachment" in resp["Content-Disposition"] and f"{_month():%Y-%m}" in resp["Content-Disposition"]
    assert len(_rows(resp)) == 3
    rows = _rows(client_in.get(url, {"kind": "expense"}))
    assert len(rows) == 2 and rows[1][2] == "1500" and rows[1][8] == "Hosting"
    assert _rows(client_in.get(url, {"kind": "income"}))[1][2] == "99.5"


def test_csv_neutralizes_formulas(client_in):
    _spend(_expense_category(), 100, description='=HYPERLINK("http://x")')
    rows = _rows(client_in.get(reverse("transaction_export")))
    assert rows[1][8].startswith("'=")


def test_csv_requires_login(client, db):
    assert client.get(reverse("transaction_export")).status_code == 302


def test_calendar_collects_all_sources(client_in, data):
    today = timezone.localdate()
    Credit.objects.create(title="Telefon", total_amount=300, months=3, monthly_payment=100, first_payment_date=today)
    Recurring.objects.create(title="Ijara", amount=1, frequency="weekly", next_date=today)
    events = calendar_events(today - timedelta(days=3), today + timedelta(days=8))
    labels = {e["label"] for items in events.values() for e in items}
    assert {"Login sahifasi", "Do'kon sayti", "INV-2026-001 — Ali Valiyev", "Sardor", "Telefon"} <= labels
    assert {"ifcoder.uz", "Ali Valiyev", "Ijara"} <= labels
    assert sum(e["label"] == "Ijara" for items in events.values() for e in items) == 2  # bugun va +7 kun


def test_calendar_shows_planned_day_and_deadline(db):
    today = timezone.localdate()
    Task.objects.create(title="Reliz", planned_for=today, due_date=today + timedelta(days=2))
    events = calendar_events(today, today + timedelta(days=5))
    assert events[today][0]["kind"] == "Vazifa"
    assert events[today + timedelta(days=2)][0]["kind"] == "Vazifa muddati"


def test_calendar_paid_credit_month_is_hidden(db):
    today = timezone.localdate()
    credit = Credit.objects.create(
        title="Telefon", total_amount=200, months=2, monthly_payment=100, first_payment_date=today
    )
    credit.payments.create(period=0, amount=100)
    assert today not in calendar_events(today, today)


def test_calendar_page_navigation(client_in, data):
    url = reverse("calendar")
    assert data["task"].title in client_in.get(url).content.decode()
    assert client_in.get(url, {"m": "2026-02"}).context["month_label"] == "Fevral 2026"
    for bad in ("9999-12", "0001-01", "abc", "2026-13"):
        assert client_in.get(url, {"m": bad}).status_code == 200
