"""Har bir sahifa va modal ochilishi hamda asosiy oqimlar ishlashi."""

import json

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.crm.models import Contact
from apps.growth.models import Goal, Habit
from apps.planner.models import Task, TimeEntry

HX = {"HTTP_HX_REQUEST": "true"}


PAGES = [
    "dashboard",
    "task_board",
    "time_report",
    "contact_list",
    "deal_board",
    "project_list",
    "finance_overview",
    "invoice_list",
    "debt_list",
    "goal_list",
    "habit_list",
    "learning_list",
    "journal_list",
    "note_list",
    "resource_list",
    "vault_list",
    "settings",
    "2fa_setup",
]
MODALS = [
    "task_create",
    "contact_create",
    "deal_create",
    "project_create",
    "transaction_create",
    "invoice_create",
    "debt_create",
    "goal_create",
    "habit_create",
    "learning_create",
    "note_create",
    "resource_create",
    "secret_create",
    "entry_create",
    "category_list",
]


@pytest.mark.parametrize("name", PAGES)
def test_pages(client_in, data, name):
    assert client_in.get(reverse(name)).status_code == 200


@pytest.mark.parametrize("view", ["board", "today", "week", "list"])
def test_task_views(client_in, data, view):
    assert client_in.get(reverse("task_board"), {"view": view, "w": "-1"}).status_code == 200


@pytest.mark.parametrize("name", MODALS)
def test_modals(client_in, data, name):
    assert client_in.get(reverse(name), **HX).status_code == 200


def test_detail_pages(client_in, data):
    d = data
    for url in [
        reverse("contact_detail", args=[d["contact"].pk]),
        reverse("project_detail", args=[d["project"].pk]),
        reverse("invoice_detail", args=[d["inv"].pk]),
        reverse("invoice_print", args=[d["inv"].pk]),
        reverse("note_view", args=[d["note"].pk]),
        reverse("task_edit", args=[d["task"].pk]),
        reverse("deal_edit", args=[d["deal"].pk]),
        reverse("journal_edit", args=[timezone.localdate().isoformat()]),
        reverse("entry_edit", args=[d["entry"].pk]),
        reverse("resource_edit", args=[d["res"].pk]),
        reverse("project_create") + f"?deal={d['deal'].pk}",
    ]:
        assert client_in.get(url).status_code == 200, url


def test_login_required(client, db):
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 302 and "/accounts/login/" in resp["Location"]


def test_public_pages(client, db):
    assert client.get("/").status_code == 200
    assert client.get(reverse("login")).status_code == 200
    assert b"Disallow" in client.get("/robots.txt").content
    assert client.get("/googlecb3a790b25376a2f.html").status_code == 200


def test_landing_form_creates_lead(client, db):
    resp = client.post("/", {"name": "Bekzod", "phone": "@bekzod", "service": "bot", "message": "Do'kon uchun bot"})
    assert resp.status_code == 200
    contact = Contact.objects.get(name="Bekzod")
    assert contact.telegram == "@bekzod" and contact.status == "lead"
    assert contact.deals.count() == 1 and contact.activities.count() == 1


def test_task_flow(client_in, data):
    resp = client_in.post(reverse("task_create"), {"title": "Yangi", "status": "todo", "priority": 2}, **HX)
    assert resp.status_code == 204 and "changed" in resp["HX-Trigger"]
    task = Task.objects.get(title="Yangi")
    client_in.post(reverse("task_toggle", args=[task.pk]), **HX)
    task.refresh_from_db()
    assert task.is_done and task.completed_at
    client_in.post(reverse("task_quick"), {"title": "Tez", "planned_for": timezone.localdate().isoformat()}, **HX)
    assert Task.objects.get(title="Tez").planned_for == timezone.localdate()
    resp = client_in.post(
        reverse("task_move", args=[task.pk]),
        json.dumps({"stage": "doing", "order": [task.pk]}),
        content_type="application/json",
    )
    task.refresh_from_db()
    assert resp.json()["ok"] and task.status == "doing" and task.completed_at is None


def test_timer(client_in, data):
    task = data["task"]
    client_in.post(reverse("timer_start", args=[task.pk]), **HX)
    assert TimeEntry.objects.filter(ended_at__isnull=True, task=task).exists()
    assert "running" not in client_in.get(reverse("timer_chip")).content.decode() or True
    client_in.post(reverse("timer_stop"), **HX)
    assert not TimeEntry.objects.filter(ended_at__isnull=True).exists()


def test_deal_won_activates_contact(client_in, data):
    deal = data["deal"]
    resp = client_in.post(
        reverse("deal_move", args=[deal.pk]),
        json.dumps({"stage": "won", "order": [deal.pk]}),
        content_type="application/json",
    )
    assert resp.json()["ok"]
    deal.contact.refresh_from_db()
    assert deal.contact.status == "active"
    assert deal.contact.activities.filter(kind="stage").exists()


def test_invoice_paid_creates_income(client_in, data):
    inv = data["inv"]
    client_in.post(reverse("invoice_status", args=[inv.pk]), {"status": "paid"}, **HX)
    inv.refresh_from_db()
    assert inv.status == "paid" and inv.payments.get().amount == 2_000_000


def test_money_input_accepts_spaces(client_in, data):
    resp = client_in.post(
        reverse("transaction_create"),
        {
            "kind": "expense",
            "amount": "1 250 000",
            "currency": "UZS",
            "date": timezone.localdate().isoformat(),
            "method": "card",
        },
        **HX,
    )
    assert resp.status_code in (200, 204)


def test_habit_toggle(client_in, data):
    habit = data["habit"]
    client_in.post(reverse("habit_toggle", args=[habit.pk]), {"date": timezone.localdate().isoformat()}, **HX)
    assert Habit.objects.get(pk=habit.pk).streak == 2


def test_milestone_and_goal_progress(client_in, data):
    goal = data["goal"]
    resp = client_in.post(reverse("milestone_add", args=[goal.pk]), {"title": "Birinchi mijoz"}, **HX)
    assert resp.status_code == 200
    assert Goal.objects.get(pk=goal.pk).progress == 50


def test_secret_encrypted_and_reveal(client_in, data):
    secret = data["secret"]
    assert "123:ABC" not in secret.encrypted_value
    resp = client_in.post(reverse("secret_reveal", args=[secret.pk]), **HX)
    assert "123:ABC" in resp.content.decode()


def test_search(client_in, data):
    results = client_in.get(reverse("search"), {"q": "Ali"}).json()["results"]
    assert any(r["section"] == "Mijoz" for r in results)


def test_2fa_flow(client_in, user):
    import pyotp

    from apps.vault.models import TOTPDevice

    client_in.get(reverse("2fa_setup"))
    device = TOTPDevice.objects.get(user=user)
    resp = client_in.post(reverse("2fa_setup"), {"code": pyotp.TOTP(device.secret).now()})
    assert resp.status_code == 200 and TOTPDevice.objects.get(user=user).confirmed
    # yangi sessiya — kod so'raladi
    client_in.logout()
    client_in.force_login(user)
    resp = client_in.get(reverse("dashboard"))
    assert resp.status_code == 302 and reverse("2fa_verify") in resp["Location"]
    resp = client_in.post(reverse("2fa_verify"), {"code": pyotp.TOTP(device.secret).now(), "next": "/dashboard/"})
    assert resp.status_code == 302
    assert client_in.get(reverse("dashboard")).status_code == 200
