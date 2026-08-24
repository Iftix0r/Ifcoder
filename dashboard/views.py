from datetime import timedelta
import json
import urllib.error
import urllib.request

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from clients.models import Client
from debts.models import Debt
from finance.models import Expense, Income, Invoice
from goals.models import Goal, GoalTask
from projects.models import Project
from tasks.models import Task

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 300  # soniya


class ThrottledLoginView(LoginView):
    """Login urinishlarini IP bo'yicha cheklaydi (parol qo'pol kuch hujumidan himoya).

    Eslatma: IP manzil request.META['REMOTE_ADDR'] orqali olinadi. cPanel kabi
    reverse-proxy ortida bu har doim proksi IP'siga teng bo'lishi mumkin — bu
    holatda cheklov barcha foydalanuvchilar uchun umumiy bo'lib qoladi (baribir
    himoya beradi, faqat IP-bo'yicha aniqlik pasayadi).
    """

    template_name = "dashboard/login.html"

    def _cache_key(self):
        ip = self.request.META.get("REMOTE_ADDR", "unknown")
        return f"login-attempts:{ip}"

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST" and cache.get(self._cache_key(), 0) >= LOGIN_ATTEMPT_LIMIT:
            messages.error(
                request,
                "Juda ko'p noto'g'ri urinish. Bir necha daqiqadan so'ng qayta urinib ko'ring.",
            )
            return render(request, self.template_name, {"form": self.get_form_class()()})
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self._cache_key()
        cache.set(key, cache.get(key, 0) + 1, LOGIN_ATTEMPT_WINDOW)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._cache_key())
        return super().form_valid(form)


@login_required
def home(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    # ── Asosiy hisoblar ───────────────────────────────────────────────────
    client_count   = Client.objects.count()
    project_count  = Project.objects.count()

    open_tasks     = Task.objects.exclude(status=Task.Status.DONE)
    task_counts    = open_tasks.aggregate(
        open    = Count("id"),
        overdue = Count("id", filter=Q(due_date__lt=today, due_date__isnull=False)),
    )

    # ── Moliya ────────────────────────────────────────────────────────────
    month_income   = Income.objects.filter(date__gte=month_start).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]
    month_expense  = Expense.objects.filter(date__gte=month_start).aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]
    month_net      = month_income - month_expense

    outstanding_qs = Invoice.objects.exclude(status=Invoice.Status.PAID)
    outstanding_count = outstanding_qs.count()
    outstanding_total = outstanding_qs.aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]

    # ── Qarzlar ───────────────────────────────────────────────────────────
    active_debts = Debt.objects.exclude(
        status__in=[Debt.Status.PAID, Debt.Status.CANCELLED]
    )
    i_owe_remaining = active_debts.filter(direction=Debt.Direction.I_OWE).aggregate(
        s=Coalesce(Sum("amount"), Value(0, output_field=DecimalField())),
        p=Coalesce(Sum("paid_amount"), Value(0, output_field=DecimalField())),
    )
    they_owe_remaining = active_debts.filter(direction=Debt.Direction.THEY_OWE).aggregate(
        s=Coalesce(Sum("amount"), Value(0, output_field=DecimalField())),
        p=Coalesce(Sum("paid_amount"), Value(0, output_field=DecimalField())),
    )
    debt_i_owe    = i_owe_remaining["s"] - i_owe_remaining["p"]
    debt_they_owe = they_owe_remaining["s"] - they_owe_remaining["p"]
    overdue_debts = active_debts.filter(due_date__lt=today).count()

    # ── Maqsadlar ─────────────────────────────────────────────────────────
    active_goals   = Goal.objects.filter(status=Goal.Status.ACTIVE)
    goals_total    = active_goals.count()
    goals_overdue  = active_goals.filter(deadline__lt=today).count()
    # Faol maqsadlar uchun o'rtacha progress
    avg_progress   = active_goals.aggregate(
        avg=Coalesce(Sum("progress"), Value(0, output_field=DecimalField()))
    )["avg"]
    avg_progress   = int(avg_progress / goals_total) if goals_total else 0

    # ── Bugungi kun uchun muhim ma'lumotlar ───────────────────────────────
    today_tasks = open_tasks.filter(due_date=today).select_related("project").order_by("priority")[:5]
    overdue_tasks_list = open_tasks.filter(
        due_date__lt=today, due_date__isnull=False
    ).select_related("project").order_by("due_date")[:5]
    upcoming_tasks = open_tasks.filter(
        due_date__gt=today
    ).select_related("project").order_by("due_date")[:6]

    recent_projects = Project.objects.select_related("client").order_by("-created_at")[:5]
    recent_clients  = Client.objects.order_by("-created_at")[:4]

    # Faol maqsadlar (progress bar uchun)
    top_goals = active_goals.order_by("deadline")[:4]

    context = {
        "today": today,
        # stat kartalar
        "clients_count":        client_count,
        "projects_count":       project_count,
        "open_tasks_count":     task_counts["open"],
        "overdue_tasks_count":  task_counts["overdue"],
        "month_income":         month_income,
        "month_expense":        month_expense,
        "month_net":            month_net,
        "outstanding_count":    outstanding_count,
        "outstanding_total":    outstanding_total,
        # qarzlar
        "debt_i_owe":           debt_i_owe,
        "debt_they_owe":        debt_they_owe,
        "overdue_debts":        overdue_debts,
        # maqsadlar
        "goals_total":          goals_total,
        "goals_overdue":        goals_overdue,
        "avg_progress":         avg_progress,
        "top_goals":            top_goals,
        # jadvallar
        "today_tasks":          today_tasks,
        "overdue_tasks_list":   overdue_tasks_list,
        "upcoming_tasks":       upcoming_tasks,
        "recent_projects":      recent_projects,
        "recent_clients":       recent_clients,
    }
    return render(request, "dashboard/home.html", context)


def _collect_alerts():
    """Barcha e'tibor talab qiladigan holatlarni bitta ro'yxatga yig'adi."""
    today = timezone.localdate()
    soon = today + timedelta(days=7)
    alerts = []

    for invoice in Invoice.objects.exclude(status=Invoice.Status.PAID).filter(
        due_date__lt=today
    ).select_related("client"):
        alerts.append(
            {
                "level": "critical",
                "title": f"Hisob-faktura #{invoice.number} muddati o'tgan",
                "detail": f"{invoice.client} — {invoice.amount} ({invoice.due_date})",
                "link": reverse("finance:invoice_detail", args=[invoice.pk]),
            }
        )

    for task in Task.objects.exclude(status=Task.Status.DONE).filter(due_date__lt=today):
        alerts.append(
            {
                "level": "critical",
                "title": f"Vazifa muddati o'tgan: {task.title}",
                "detail": f"{task.due_date}",
                "link": reverse("tasks:detail", args=[task.pk]),
            }
        )

    for project in Project.objects.exclude(
        status__in=[Project.Status.COMPLETED, Project.Status.PAUSED]
    ).filter(deadline__isnull=False, deadline__lte=soon).select_related("client"):
        level = "critical" if project.deadline < today else "warning"
        alerts.append(
            {
                "level": level,
                "title": f"Loyiha muddati yaqin: {project.name}",
                "detail": f"{project.client or '—'} — {project.deadline}",
                "link": reverse("projects:detail", args=[project.pk]),
            }
        )

    for task in Task.objects.exclude(status=Task.Status.DONE).filter(
        due_date__gte=today, due_date__lte=soon
    ):
        alerts.append(
            {
                "level": "warning",
                "title": f"Vazifa muddati yaqin: {task.title}",
                "detail": f"{task.due_date}",
                "link": reverse("tasks:detail", args=[task.pk]),
            }
        )

    # Muddati o'tgan qarzlar
    from debts.models import Debt
    for debt in Debt.objects.exclude(
        status__in=[Debt.Status.PAID, Debt.Status.CANCELLED]
    ).filter(due_date__lt=today):
        alerts.append(
            {
                "level": "critical",
                "title": f"Qarz muddati o'tgan: {debt.counterparty}",
                "detail": f"{debt.remaining_amount} {debt.get_currency_display()} ({debt.due_date})",
                "link": reverse("debts:detail", args=[debt.pk]),
            }
        )

    # Muddati o'tgan maqsadlar
    from goals.models import Goal
    for goal in Goal.objects.filter(status=Goal.Status.ACTIVE, deadline__lt=today):
        alerts.append(
            {
                "level": "warning",
                "title": f"Maqsad muddati o'tgan: {goal.title}",
                "detail": f"Deadline: {goal.deadline} — {goal.progress}% bajarildi",
                "link": reverse("goals:detail", args=[goal.pk]),
            }
        )

    order = {"critical": 0, "warning": 1}
    alerts.sort(key=lambda a: order[a["level"]])
    return alerts


@login_required
def alerts(request):
    return render(request, "dashboard/alerts.html", {"alerts": _collect_alerts()})


@login_required
def search(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        lookup = Q(name__icontains=query)
        for client in Client.objects.filter(
            lookup | Q(email__icontains=query) | Q(telegram__icontains=query)
        ).order_by("name")[:10]:
            results.append(
                {"type": "Mijoz", "title": client.name, "detail": client.email or client.phone,
                 "url": reverse("clients:detail", args=[client.pk])}
            )

        for project in Project.objects.filter(name__icontains=query).select_related("client").order_by("name")[:10]:
            results.append(
                {"type": "Loyiha", "title": project.name, "detail": str(project.client or ""),
                 "url": reverse("projects:detail", args=[project.pk])}
            )

        for task in Task.objects.filter(title__icontains=query).order_by("title")[:10]:
            results.append(
                {"type": "Vazifa", "title": task.title, "detail": task.get_status_display(),
                 "url": reverse("tasks:detail", args=[task.pk])}
            )

        for debt in Debt.objects.filter(
            Q(counterparty__icontains=query) | Q(reason__icontains=query)
        ).order_by("counterparty")[:5]:
            results.append(
                {"type": "Qarz", "title": debt.counterparty,
                 "detail": f"{debt.amount} {debt.get_currency_display()} — {debt.get_status_display()}",
                 "url": reverse("debts:detail", args=[debt.pk])}
            )

        for goal in Goal.objects.filter(title__icontains=query).order_by("title")[:5]:
            results.append(
                {"type": "Maqsad", "title": goal.title,
                 "detail": f"{goal.progress}% — {goal.get_status_display()}",
                 "url": reverse("goals:detail", args=[goal.pk])}
            )

    return render(request, "dashboard/search.html", {"query": query, "results": results})


AI_FOCUSES = {
    "general": "Umumiy CRM maslahati ber.",
    "today": "Bugungi ishlarni muhimlik va muddat bo'yicha ustuvorlashtir.",
    "projects": "Faol loyihalardagi xavflarni top va keyingi amallarni taklif qil.",
    "finance": "Joriy oy moliyaviy holatini tahlil qil va pul oqimini yaxshilash bo'yicha maslahat ber.",
}


def _ask_openai(question, focus="general"):
    today = timezone.localdate()
    open_tasks = list(
        Task.objects.exclude(status=Task.Status.DONE)
        .select_related("project")
        .order_by("due_date", "priority")[:8]
    )
    active_projects = list(
        Project.objects.exclude(
            status__in=[Project.Status.COMPLETED, Project.Status.PAUSED]
        )
        .order_by("deadline", "name")[:8]
    )
    task_context = "; ".join(
        f"{task.title} ({task.get_priority_display()}, muddat: {task.due_date or 'belgilanmagan'})"
        for task in open_tasks
    ) or "ochiq vazifa yo'q"
    project_context = "; ".join(
        f"{project.name} ({project.get_status_display()}, muddat: {project.deadline or 'belgilanmagan'})"
        for project in active_projects
    ) or "faol loyiha yo'q"
    month_start = today.replace(day=1)
    month_income = Income.objects.filter(date__gte=month_start).aggregate(total=Sum("amount"))["total"] or 0
    month_expense = Expense.objects.filter(date__gte=month_start).aggregate(total=Sum("amount"))["total"] or 0
    unpaid_amount = Invoice.objects.exclude(status=Invoice.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0
    prompt = (
        "Sen Ifcoder CRM panelining ichki yordamchisisan. O'zbek tilida, qisqa va amaliy javob ber. "
        "Faqat berilgan CRM ma'lumotlariga tayangan holda javob ber, mavjud bo'lmagan faktni o'ylab topma. "
        "Avval xulosani, keyin 3 tagacha aniq amalni yoz. Bugungi sana: "
        f"{today}. "
        f"CRM ko'rsatkichlari: mijozlar={Client.objects.count()}, loyihalar={Project.objects.count()}, "
        f"ochiq vazifalar={Task.objects.exclude(status=Task.Status.DONE).count()}, "
        f"to'lanmagan invoice'lar={Invoice.objects.exclude(status=Invoice.Status.PAID).count()}. "
        f"To'lanmagan invoice summasi={unpaid_amount}, joriy oy daromadi={month_income}, "
        f"joriy oy xarajati={month_expense}. Ochiq vazifalar: {task_context}. "
        f"Faol loyihalar: {project_context}. Tahlil rejimi: {AI_FOCUSES.get(focus, AI_FOCUSES['general'])}"
    )
    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "input": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": question},
            ],
            "max_output_tokens": 700,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("output_text"):
        return result["output_text"]
    return "\n".join(
        item.get("text", "")
        for output in result.get("output", [])
        for item in output.get("content", [])
        if item.get("text")
    )


@login_required
def ai_assistant(request):
    answer = ""
    question = ""
    focus = "general"
    error = ""
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        focus = request.POST.get("focus", "general")
        if focus not in AI_FOCUSES:
            focus = "general"
        if not settings.OPENAI_API_KEY:
            error = "OPENAI_API_KEY sozlanmagan. Kalitni .env yoki production environment'ga qo'shing."
        elif not question:
            error = "Savol kiriting."
        elif len(question) > 2000:
            error = "Savol 2000 belgidan oshmasin."
        else:
            try:
                answer = _ask_openai(question, focus)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                error = "AI xizmatiga ulanib bo'lmadi. API kaliti va internet ulanishini tekshiring."
    return render(
        request,
        "dashboard/ai_assistant.html",
        {
            "answer": answer,
            "question": question,
            "focus": focus,
            "error": error,
            "focuses": AI_FOCUSES,
            "quick_questions": [
                "Bugun qaysi ishlarni birinchi qilishim kerak?",
                "Muddati yaqin loyihalar bo'yicha reja tuz.",
                "Ochiq vazifalarimni ustuvorlik bo'yicha tartibla.",
                "Bu oy moliyaviy holatim qanday?",
            ],
        },
    )


@login_required
def reports(request):
    today = timezone.localdate()
    # Build the last 6 calendar months (oldest first) without relying on
    # a third-party date library.
    months = []
    year, month = today.year, today.month
    for _ in range(6):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    months.reverse()

    monthly = []
    max_amount = 0
    for year, month in months:
        start = today.replace(year=year, month=month, day=1)
        if month == 12:
            end = start.replace(year=year + 1, month=1, day=1)
        else:
            end = start.replace(month=month + 1, day=1)
        income = Income.objects.filter(date__gte=start, date__lt=end).aggregate(
            total=Sum("amount")
        )["total"] or 0
        expense = Expense.objects.filter(date__gte=start, date__lt=end).aggregate(
            total=Sum("amount")
        )["total"] or 0
        max_amount = max(max_amount, float(income), float(expense))
        monthly.append(
            {
                "label": start.strftime("%b"),
                "income": income,
                "expense": expense,
                "net": income - expense,
            }
        )

    for row in monthly:
        row["income_pct"] = round(float(row["income"]) / max_amount * 100) if max_amount else 0
        row["expense_pct"] = round(float(row["expense"]) / max_amount * 100) if max_amount else 0

    total_income = sum((row["income"] for row in monthly), 0)
    total_expense = sum((row["expense"] for row in monthly), 0)

    projects_by_status = [
        {"label": label, "value": value, "count": Project.objects.filter(status=value).count()}
        for value, label in Project.Status.choices
    ]
    max_project_count = max((s["count"] for s in projects_by_status), default=0)
    for s in projects_by_status:
        s["pct"] = round(s["count"] / max_project_count * 100) if max_project_count else 0

    invoices_by_status = [
        {"label": label, "value": value, "count": Invoice.objects.filter(status=value).count()}
        for value, label in Invoice.Status.choices
    ]

    top_clients = (
        Client.objects.annotate(total_income=Sum("incomes__amount"))
        .filter(total_income__gt=0)
        .order_by("-total_income")[:5]
    )

    context = {
        "monthly": monthly,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_income": total_income - total_expense,
        "projects_by_status": projects_by_status,
        "invoices_by_status": invoices_by_status,
        "top_clients": top_clients,
    }
    return render(request, "dashboard/reports.html", context)
