from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from bots.models import Bot
from clients.models import Client
from finance.models import Expense, Income, Invoice
from infrastructure.models import Domain, SSLCertificate
from projects.models import Project


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
    }
    return render(request, "dashboard/home.html", context)
