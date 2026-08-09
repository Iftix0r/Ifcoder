from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db.models import Sum
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
    projects_by_status = [
        {"label": label, "value": value, "count": Project.objects.filter(status=value).count()}
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
    overdue_tasks_count = open_tasks.filter(due_date__lt=today).count()

    context = {
        "clients_count": Client.objects.count(),
        "projects_count": Project.objects.count(),
        "bots_count": Bot.objects.count(),
        "bots_active_count": Bot.objects.filter(status=Bot.Status.ACTIVE).count(),
        "projects_by_status": projects_by_status,
        "recent_projects": Project.objects.select_related("client").order_by("-created_at")[:5],
        "recent_bots": Bot.objects.select_related("project", "client").order_by("-created_at")[:5],
        "recent_clients": Client.objects.order_by("-created_at")[:5],
        "month_income": month_income,
        "month_expense": month_expense,
        "outstanding_invoices_count": outstanding_invoices.count(),
        "expiring_domains": Domain.objects.expiring_soon().order_by("expiration_date")[:5],
        "expiring_certificates": SSLCertificate.objects.expiring_soon()
        .select_related("domain")
        .order_by("expiration_date")[:5],
        "open_tasks_count": open_tasks.count(),
        "overdue_tasks_count": overdue_tasks_count,
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
