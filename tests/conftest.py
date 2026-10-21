from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.crm.models import Activity, Contact, Deal
from apps.finance.models import Category, Debt, Invoice, InvoiceLine, Kind, Transaction
from apps.growth.models import Goal, Habit, HabitLog, JournalEntry, LearningItem
from apps.notes.models import Note
from apps.planner.models import Task, TimeEntry
from apps.projects.models import Project
from apps.resources.models import Resource
from apps.vault.models import Secret


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("iftixor", password="Parol-2026!", first_name="Iftixor")


@pytest.fixture
def client_in(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def data(db):
    today = timezone.localdate()
    contact = Contact.objects.create(name="Ali Valiyev", phone="+998901112233", telegram="@ali", next_contact=today)
    project = Project.objects.create(
        name="Do'kon sayti", contact=contact, status="active", deadline=today + timedelta(days=2), stack="Django, HTMX"
    )
    task = Task.objects.create(
        title="Login sahifasi", project=project, planned_for=today, due_date=today - timedelta(days=1), priority=3
    )
    Task.objects.create(title="Bajarilgan", status="done", completed_at=timezone.now())
    deal = Deal.objects.create(title="Bot", contact=contact, value=5_000_000)
    Activity.objects.create(contact=contact, text="Qo'ng'iroq qildim", kind="call")
    inv = Invoice.objects.create(
        number="INV-2026-001", contact=contact, project=project, status="sent", due_date=today - timedelta(days=1)
    )
    InvoiceLine.objects.create(invoice=inv, description="Dizayn", quantity=1, unit_price=2_000_000)
    Transaction.objects.create(
        kind=Kind.INCOME, amount=3_000_000, category=Category.objects.filter(kind="income").first(), project=project
    )
    Transaction.objects.create(kind=Kind.EXPENSE, amount=150_000, currency="USD")
    Debt.objects.create(person="Sardor", amount=500_000, due_date=today)
    goal = Goal.objects.create(title="3 ta SaaS mijoz", target_date=today + timedelta(days=60))
    goal.milestones.create(title="Landing", done=True)
    habit = Habit.objects.create(title="Yugurish", emoji="🏃")
    HabitLog.objects.create(habit=habit, date=today - timedelta(days=1))
    LearningItem.objects.create(title="Clean Code", kind="book", status="active", progress=40)
    JournalEntry.objects.create(date=today, wins="Deploy qildim")
    note = Note.objects.create(
        title="Deploy", kind="snippet", body="git pull && ./deploy.sh", tags="server, deploy", project=project
    )
    res = Resource.objects.create(name="ifcoder.uz", renews_on=today + timedelta(days=5), cost=12, project=project)
    secret = Secret(name="Bot token", project=project)
    secret.value = "123:ABC"
    secret.save()
    entry = TimeEntry.objects.create(
        task=task, project=project, started_at=timezone.now() - timedelta(hours=1), ended_at=timezone.now()
    )
    return locals()
