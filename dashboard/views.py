from datetime import timedelta
import json
import urllib.error
import urllib.request

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from bots.models import Bot
from clients.models import Client
from finance.models import Expense, Income, Invoice
from infrastructure.models import Domain, SSLCertificate
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
    project_status_counts = dict(
        Project.objects.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )
    projects_by_status = [
        {"label": label, "value": value, "count": project_status_counts.get(value, 0)}
        for value, label in Project.Status.choices
    ]

    month_start = timezone.localdate().replace(day=1)
    month_income = Income.objects.filter(date__gte=month_start).aggregate(total=Sum("amount"))[
        "total"
    ] or 0
    month_expense = Expense.objects.filter(date__gte=month_start).aggregate(
        total=Sum("amount")
    )["total"] or 0
    outstanding_invoices = Invoice.objects.exclude(status=Invoice.Status.PAID)
    today = timezone.localdate()
    open_tasks = Task.objects.exclude(status=Task.Status.DONE)
    client_count = Client.objects.aggregate(total=Count("id"))["total"]
    project_count = Project.objects.aggregate(total=Count("id"))["total"]
    bot_counts = Bot.objects.aggregate(
        total=Count("id"), active=Count("id", filter=Q(status=Bot.Status.ACTIVE))
    )
    task_counts = open_tasks.aggregate(
        open=Count("id"), overdue=Count("id", filter=Q(due_date__lt=today))
    )
    invoice_counts = outstanding_invoices.aggregate(total=Count("id"))

    context = {
        "clients_count": client_count,
        "projects_count": project_count,
        "bots_count": bot_counts["total"],
        "bots_active_count": bot_counts["active"],
        "projects_by_status": projects_by_status,
        "recent_projects": Project.objects.select_related("client").order_by("-created_at")[:5],
        "recent_bots": Bot.objects.select_related("project", "client").order_by("-created_at")[:5],
        "recent_clients": Client.objects.order_by("-created_at")[:5],
        "month_income": month_income,
        "month_expense": month_expense,
        "outstanding_invoices_count": invoice_counts["total"],
        "expiring_domains": Domain.objects.expiring_soon().order_by("expiration_date")[:5],
        "expiring_certificates": SSLCertificate.objects.expiring_soon()
        .select_related("domain")
        .order_by("expiration_date")[:5],
        "open_tasks_count": task_counts["open"],
        "overdue_tasks_count": task_counts["overdue"],
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

    for domain in Domain.objects.expired():
        alerts.append(
            {
                "level": "critical",
                "title": f"Domen muddati tugagan: {domain.name}",
                "detail": f"{domain.expiration_date}",
                "link": reverse("infrastructure:domain_detail", args=[domain.pk]),
            }
        )

    for cert in SSLCertificate.objects.expired().select_related("domain"):
        alerts.append(
            {
                "level": "critical",
                "title": f"SSL sertifikat muddati tugagan: {cert}",
                "detail": f"{cert.expiration_date}",
                "link": reverse("infrastructure:ssl_detail", args=[cert.pk]),
            }
        )

    for domain in Domain.objects.expiring_soon():
        alerts.append(
            {
                "level": "warning",
                "title": f"Domen muddati yaqinlashmoqda: {domain.name}",
                "detail": f"{domain.expiration_date}",
                "link": reverse("infrastructure:domain_detail", args=[domain.pk]),
            }
        )

    for cert in SSLCertificate.objects.expiring_soon().select_related("domain"):
        alerts.append(
            {
                "level": "warning",
                "title": f"SSL sertifikat muddati yaqinlashmoqda: {cert}",
                "detail": f"{cert.expiration_date}",
                "link": reverse("infrastructure:ssl_detail", args=[cert.pk]),
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

        for bot in Bot.objects.filter(name__icontains=query).order_by("name")[:10]:
            results.append(
                {"type": "Bot", "title": bot.name, "detail": bot.get_status_display(),
                 "url": reverse("bots:detail", args=[bot.pk])}
            )

    return render(request, "dashboard/search.html", {"query": query, "results": results})


def _ask_openai(question):
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
    prompt = (
        "Sen Ifcoder CRM panelining ichki yordamchisisan. O'zbek tilida, qisqa va amaliy javob ber. "
        "Faqat berilgan CRM ma'lumotlariga tayangan holda javob ber, mavjud bo'lmagan faktni o'ylab topma. "
        "Avval xulosani, keyin 3 tagacha aniq amalni yoz. Bugungi sana: "
        f"{today}. "
        f"CRM ko'rsatkichlari: mijozlar={Client.objects.count()}, loyihalar={Project.objects.count()}, "
        f"ochiq vazifalar={Task.objects.exclude(status=Task.Status.DONE).count()}, "
        f"to'lanmagan invoice'lar={Invoice.objects.exclude(status=Invoice.Status.PAID).count()}. "
        f"Ochiq vazifalar: {task_context}. Faol loyihalar: {project_context}."
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
    error = ""
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        if not settings.OPENAI_API_KEY:
            error = "OPENAI_API_KEY sozlanmagan. Kalitni .env yoki production environment'ga qo'shing."
        elif not question:
            error = "Savol kiriting."
        elif len(question) > 2000:
            error = "Savol 2000 belgidan oshmasin."
        else:
            try:
                answer = _ask_openai(question)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                error = "AI xizmatiga ulanib bo'lmadi. API kaliti va internet ulanishini tekshiring."
    return render(
        request,
        "dashboard/ai_assistant.html",
        {
            "answer": answer,
            "question": question,
            "error": error,
            "quick_questions": [
                "Bugun qaysi ishlarni birinchi qilishim kerak?",
                "Muddati yaqin loyihalar bo'yicha reja tuz.",
                "Ochiq vazifalarimni ustuvorlik bo'yicha tartibla.",
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
        monthly.append({"label": start.strftime("%b"), "income": income, "expense": expense})

    for row in monthly:
        row["income_pct"] = round(float(row["income"]) / max_amount * 100) if max_amount else 0
        row["expense_pct"] = round(float(row["expense"]) / max_amount * 100) if max_amount else 0

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
        "projects_by_status": projects_by_status,
        "invoices_by_status": invoices_by_status,
        "top_clients": top_clients,
    }
    return render(request, "dashboard/reports.html", context)
