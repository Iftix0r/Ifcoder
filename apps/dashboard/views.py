import calendar
from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from apps.crm.models import Contact, Deal
from apps.finance.models import Credit, Debt, Invoice, Kind, Recurring, Transaction, totals_by_currency
from apps.finance.views import MONTHS, _month, _shift, budget_rows, month_series
from apps.growth.models import Goal, Habit, JournalEntry, LearningItem
from apps.planner.models import Task, TimeEntry
from apps.projects.models import Project
from apps.resources.models import Resource
from apps.resources.views import expiring


def _greeting(hour):
    if 5 <= hour < 11:
        return "Xayrli tong"
    if 11 <= hour < 17:
        return "Xayrli kun"
    if 17 <= hour < 22:
        return "Xayrli kech"
    return "Xayrli tun"


def due_credits(today, days=3):
    """Keyingi to'lovi kechikkan yoki `days` kun ichida bo'lgan ochiq kreditlar."""
    credits = Credit.objects.filter(is_closed=False).prefetch_related("payments")
    return sorted(
        (c for c in credits if c.next_due and c.next_due <= today + timedelta(days=days)), key=lambda c: c.next_due
    )


def _alerts(today):
    """«E'tibor talab qiladi»: muddati o'tgan yoki yaqinlashgan hamma narsa bitta ro'yxatda."""
    items = []
    overdue = Task.objects.exclude(status=Task.Status.DONE).filter(due_date__lt=today).count()
    if overdue:
        items.append(
            {
                "icon": "list-todo",
                "tone": "tone-rose",
                "title": f"{overdue} ta vazifa muddati o'tgan",
                "url": "/tasks/?view=list",
            }
        )
    for c in Contact.objects.filter(next_contact__lte=today).order_by("next_contact")[:5]:
        items.append(
            {
                "icon": "phone-outgoing",
                "tone": "tone-cyan",
                "title": f"{c.name} bilan bog'lanish",
                "hint": c.next_contact,
                "url": c.get_absolute_url(),
            }
        )
    for inv in Invoice.objects.filter(status=Invoice.Status.SENT, due_date__lt=today).select_related("contact")[:5]:
        items.append(
            {
                "icon": "receipt-text",
                "tone": "tone-amber",
                "title": f"{inv.number} to'lanmagan — {inv.contact}",
                "hint": inv.due_date,
                "url": inv.get_absolute_url(),
            }
        )
    for r in expiring(14)[:5]:
        items.append(
            {
                "icon": r.icon,
                "tone": "tone-violet",
                "title": f"{r.name} tugaydi",
                "hint": r.renews_on,
                "url": "/resources/",
            }
        )
    for d in Debt.objects.filter(is_closed=False, due_date__lte=today + timedelta(days=3))[:5]:
        verb = "qarzini qaytarishi kerak" if d.direction == Debt.Direction.THEY_OWE else "ga qarzni qaytarish"
        items.append(
            {
                "icon": "hand-coins",
                "tone": "tone-amber",
                "title": f"{d.person} {verb}",
                "hint": d.due_date,
                "url": "/debts/",
            }
        )
    for c in due_credits(today):
        items.append(
            {
                "icon": "credit-card",
                "tone": "tone-rose",
                "title": f"{c.title}: {c.paid_count + 1}-oy to'lovi",
                "hint": c.next_due,
                "url": "/credits/",
            }
        )
    for r in Recurring.objects.filter(is_active=True, next_date__lte=today)[:5]:
        items.append(
            {
                "icon": "calendar-clock",
                "tone": "tone-emerald" if r.kind == Kind.INCOME else "tone-rose",
                "title": f"{r.title}: {'kirimni' if r.kind == Kind.INCOME else 'chiqimni'} yozish",
                "hint": r.next_date,
                "url": reverse("recurring_list"),
            }
        )
    for row in budget_rows(today.replace(day=1)):
        if row["over"]:
            items.append(
                {
                    "icon": "gauge",
                    "tone": "tone-rose",
                    "title": f"«{row['budget'].category}» limiti oshdi ({row['pct']}%)",
                    "url": reverse("finance_overview"),
                }
            )
    for deal in Deal.objects.filter(stage__in=Deal.OPEN_STAGES, expected_close__lt=today).select_related("contact")[:5]:
        items.append(
            {
                "icon": "target",
                "tone": "tone-brand",
                "title": f"«{deal.title}» bitimi kechikmoqda",
                "hint": deal.expected_close,
                "url": "/deals/",
            }
        )
    return items


def home(request):
    now = timezone.localtime()
    today = now.date()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    open_tasks = Task.objects.exclude(status=Task.Status.DONE).select_related("project", "contact")
    today_tasks = open_tasks.filter(
        Q(planned_for__lte=today) | Q(due_date__lte=today) | Q(status=Task.Status.DOING)
    ).order_by("-priority", "due_date")
    done_today = Task.objects.filter(completed_at__date=today).count()

    habits = list(Habit.objects.filter(is_active=True).prefetch_related("logs"))
    week_minutes = sum(e.minutes for e in TimeEntry.objects.filter(started_at__date__gte=week_start))
    month_tx = Transaction.objects.filter(date__gte=month_start)
    pipeline = totals_by_currency(Deal.objects.filter(stage__in=Deal.OPEN_STAGES), "value")

    plan_total = done_today + today_tasks.count()
    kpis = [
        {
            "label": "Bugungi reja",
            "value": done_today,
            "suffix": f" / {plan_total}",
            "icon": "list-checks",
            "tone": "brand",
            "hint": "bajarildi",
            "url": "/tasks/?view=today",
        },
        {
            "label": "Bu oy kirim",
            "text": totals_by_currency(month_tx.filter(kind=Kind.INCOME)),
            "icon": "trending-up",
            "tone": "emerald",
            "hint": f"chiqim: {_short(totals_by_currency(month_tx.filter(kind=Kind.EXPENSE)))}",
            "url": "/finance/",
        },
        {
            "label": "Ochiq bitimlar",
            "value": Deal.objects.filter(stage__in=Deal.OPEN_STAGES).count(),
            "icon": "target",
            "tone": "violet",
            "hint": _short(pipeline) or "voronka bo'sh",
            "url": "/deals/",
        },
        {
            "label": "Bu hafta fokus",
            "value": round(week_minutes / 60, 1),
            "unit": "soat",
            "icon": "timer",
            "tone": "amber",
            "hint": "taymer bo'yicha",
            "url": "/time/",
        },
    ]

    projects = (
        Project.objects.filter(status=Project.Status.ACTIVE)
        .annotate(
            task_total=Count("tasks", distinct=True),
            task_done=Count("tasks", filter=Q(tasks__status=Task.Status.DONE), distinct=True),
        )
        .select_related("contact")[:5]
    )
    return render(
        request,
        "dashboard/home.html",
        {
            "nav_active": "dashboard",
            "greeting": _greeting(now.hour),
            "today": today,
            "kpis": kpis,
            "today_tasks": today_tasks[:12],
            "done_today": done_today,
            "plan_total": plan_total,
            "habits": habits,
            "habits_done": sum(1 for h in habits if h.done_today),
            "alerts": _alerts(today),
            "series": month_series(6),
            "goals": Goal.objects.filter(status=Goal.Status.ACTIVE).prefetch_related("milestones")[:4],
            "projects": projects,
            "learning": LearningItem.objects.filter(status=LearningItem.Status.ACTIVE)[:4],
            "journal_today": JournalEntry.objects.filter(date=today).first(),
            "is_empty": not (Task.objects.exists() or Project.objects.exists() or Contact.objects.exists()),
        },
    )


WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]


def calendar_events(start, end):
    """[start, end] dagi barcha muddatlar: {sana: [hodisa, ...]}.

    Hodisada ``url`` (sahifaga o'tish) yoki ``modal`` (tahrir oynasi) bo'ladi; ``tone`` — nuqta rangi.
    """
    events = {}

    def add(day, label, tone, kind, url="", modal="", done=False):
        if day and start <= day <= end:
            events.setdefault(day, []).append(
                {"label": label, "tone": tone, "kind": kind, "url": url, "modal": modal, "done": done}
            )

    tasks = Task.objects.filter(Q(planned_for__range=(start, end)) | Q(due_date__range=(start, end)))
    for t in tasks:
        modal = reverse("task_edit", args=[t.pk])
        add(t.planned_for or t.due_date, t.title, "brand", "Vazifa", modal=modal, done=t.is_done)
        if t.planned_for and t.due_date and t.planned_for != t.due_date and not t.is_done:
            add(t.due_date, t.title, "rose", "Vazifa muddati", modal=modal)
    for p in Project.objects.exclude(status=Project.Status.DONE).filter(deadline__range=(start, end)):
        add(p.deadline, p.name, "violet", "Loyiha muddati", url=p.get_absolute_url())
    for inv in Invoice.objects.filter(status=Invoice.Status.SENT, due_date__range=(start, end)).select_related(
        "contact"
    ):
        add(inv.due_date, f"{inv.number} — {inv.contact}", "amber", "Hisob-faktura", url=inv.get_absolute_url())
    for d in Debt.objects.filter(is_closed=False, due_date__range=(start, end)):
        add(d.due_date, d.person, "amber", d.get_direction_display(), url=reverse("debt_list"))
    for c in Credit.objects.filter(is_closed=False).prefetch_related("payments"):
        for row in c.schedule():
            if not row["payment"]:
                add(row["date"], c.title, "rose", "Kredit to'lovi", url=reverse("credit_list"))
    for r in Recurring.objects.filter(is_active=True, next_date__lte=end):
        tone = "emerald" if r.kind == Kind.INCOME else "rose"
        for day in r.occurrences(start, end):
            add(day, r.title, tone, "Takroriy to'lov", url=reverse("recurring_list"))
    for res in Resource.objects.filter(is_active=True, renews_on__range=(start, end)):
        add(res.renews_on, res.name, "violet", "Resurs tugaydi", url=reverse("resource_list"))
    for c in Contact.objects.filter(next_contact__range=(start, end)):
        add(c.next_contact, c.name, "cyan", "Bog'lanish", url=c.get_absolute_url())
    for deal in Deal.objects.filter(stage__in=Deal.OPEN_STAGES, expected_close__range=(start, end)):
        add(deal.expected_close, deal.title, "cyan", "Bitim", url=reverse("deal_board"))
    for g in Goal.objects.filter(status=Goal.Status.ACTIVE, target_date__range=(start, end)):
        add(g.target_date, g.title, "emerald", "Maqsad", url=reverse("goal_list"))
    return events


def calendar_view(request):
    today = timezone.localdate()
    month = _month(request)
    if abs(month.year - today.year) > 10:
        month = today.replace(day=1)
    weeks = calendar.Calendar().monthdatescalendar(month.year, month.month)
    events = calendar_events(weeks[0][0], weeks[-1][-1])
    in_month = month.year == today.year and month.month == today.month
    return render(
        request,
        "dashboard/calendar.html",
        {
            "nav_active": "calendar",
            "weekdays": WEEKDAYS,
            "month_label": f"{MONTHS[month.month]} {month.year}",
            "prev": _shift(month, -1),
            "next": _shift(month, 1),
            "is_current": in_month,
            "selected": today if in_month else month,
            "weeks": [
                [
                    {
                        "date": d,
                        "events": events.get(d, []),
                        "is_today": d == today,
                        "other": d.month != month.month,
                    }
                    for d in week
                ]
                for week in weeks
            ],
        },
    )


def _short(totals):
    from apps.core.templatetags.ui import totals as fmt

    return fmt(totals) if totals else ""
