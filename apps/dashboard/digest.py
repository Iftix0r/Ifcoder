"""Telegram'ga yuboriladigan ertalabki xulosa matni."""

from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.telegram import h
from apps.crm.models import Contact, Deal
from apps.finance.models import Debt, Invoice, Kind, Transaction, totals_by_currency
from apps.growth.models import Habit
from apps.planner.models import Task
from apps.resources.views import expiring

GREETINGS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


def _money(totals):
    from apps.core.templatetags.ui import totals as fmt

    return fmt(totals)


def build_digest(today=None) -> str:
    today = today or timezone.localdate()
    site = settings.SITE_URL
    open_tasks = Task.objects.exclude(status=Task.Status.DONE).select_related("project")
    plan = list(
        open_tasks.filter(Q(planned_for__lte=today) | Q(due_date__lte=today) | Q(status=Task.Status.DOING)).order_by(
            "-priority", "due_date"
        )[:10]
    )
    overdue = open_tasks.filter(due_date__lt=today).count()

    lines = [f"☀️ <b>Xayrli tong!</b> {GREETINGS[today.weekday()]}, {today:%d.%m.%Y}", ""]

    if plan:
        lines.append(f"📋 <b>Bugungi reja</b> ({len(plan)})")
        for t in plan:
            flag = "🔴 " if t.priority >= 4 else "🟠 " if t.priority == 3 else ""
            late = " — <i>kechikkan</i>" if t.due_date and t.due_date < today else ""
            project = f" · {h(t.project.name)}" if t.project else ""
            lines.append(f"• {flag}{h(t.title)}{project}{late}")
    else:
        lines.append("📋 Bugunga reja yo'q — 3 ta asosiy ishni yozing.")
    if overdue:
        lines.append(f"⚠️ Muddati o'tgan vazifalar: <b>{overdue}</b>")

    calls = list(Contact.objects.filter(next_contact__lte=today).order_by("next_contact")[:5])
    if calls:
        lines += ["", "📞 <b>Bog'lanish kerak</b>"]
        lines += [f"• {h(c.name)}" + (f" — {h(c.phone)}" if c.phone else "") for c in calls]

    unpaid = list(Invoice.objects.filter(status=Invoice.Status.SENT, due_date__lt=today).select_related("contact")[:5])
    if unpaid:
        lines += ["", "🧾 <b>To'lanmagan hisob-fakturalar</b>"]
        lines += [f"• {h(i.number)} — {h(i.contact)}" for i in unpaid]

    renewals = list(expiring(14)[:5])
    if renewals:
        lines += ["", "🌐 <b>Tez orada tugaydi</b>"]
        lines += [f"• {h(r.name)} — {r.renews_on:%d.%m}" for r in renewals]

    debts = list(Debt.objects.filter(is_closed=False, due_date__lte=today + timedelta(days=3))[:5])
    if debts:
        lines += ["", "💸 <b>Qarz muddatlari</b>"]
        for d in debts:
            arrow = "←" if d.direction == Debt.Direction.THEY_OWE else "→"
            lines.append(f"• {arrow} {h(d.person)} — {d.due_date:%d.%m}")

    from apps.core.templatetags.ui import money
    from apps.dashboard.views import due_credits

    credits = due_credits(today)
    if credits:
        lines += ["", "💳 <b>Kredit to'lovlari</b>"]
        for c in credits:
            late = " — <i>kechikkan</i>" if c.next_due < today else ""
            lines.append(f"• {h(c.title)}: {money(c.next_amount, c.currency)} — {c.next_due:%d.%m}{late}")

    stale = Deal.objects.filter(stage__in=Deal.OPEN_STAGES, expected_close__lt=today).count()
    if stale:
        lines.append(f"\n🎯 Kechikayotgan bitimlar: <b>{stale}</b>")

    habits = [hb for hb in Habit.objects.filter(is_active=True).prefetch_related("logs")]
    if habits:
        lines += ["", "🔁 <b>Odatlar</b>: " + ", ".join(f"{hb.emoji} {h(hb.title)} (🔥{hb.streak})" for hb in habits)]

    month = Transaction.objects.filter(date__gte=today.replace(day=1))
    income = totals_by_currency(month.filter(kind=Kind.INCOME))
    expense = totals_by_currency(month.filter(kind=Kind.EXPENSE))
    lines += ["", f"💰 Bu oy: +{_money(income)} / −{_money(expense)}"]

    lines += ["", f'<a href="{site}/dashboard/">Panelni ochish →</a>']
    return "\n".join(lines)


def lead_message(contact, deal, service: str, message: str) -> str:
    lines = [
        "🔔 <b>Saytdan yangi ariza!</b>",
        "",
        f"👤 {h(contact.name)}",
        f"📞 {h(contact.phone or contact.telegram)}",
        f"🛠 {h(service)}",
    ]
    if message:
        lines += ["", f"💬 {h(message[:1500])}"]
    lines += ["", f'<a href="{settings.SITE_URL}{contact.get_absolute_url()}">Mijoz kartasini ochish →</a>']
    if contact.telegram:
        lines.append(f'<a href="https://t.me/{h(contact.telegram.lstrip("@"))}">Telegram\'da yozish →</a>')
    return "\n".join(lines)
