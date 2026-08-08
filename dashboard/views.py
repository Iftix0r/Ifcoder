from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from bots.models import Bot
from clients.models import Client
from projects.models import Project


@login_required
def home(request):
    projects_by_status = [
        {"label": label, "value": value, "count": Project.objects.filter(status=value).count()}
        for value, label in Project.Status.choices
    ]
    context = {
        "clients_count": Client.objects.count(),
        "projects_count": Project.objects.count(),
        "bots_count": Bot.objects.count(),
        "bots_active_count": Bot.objects.filter(status=Bot.Status.ACTIVE).count(),
        "projects_by_status": projects_by_status,
        "recent_projects": Project.objects.select_related("client").order_by("-created_at")[:5],
        "recent_bots": Bot.objects.select_related("project", "client").order_by("-created_at")[:5],
        "recent_clients": Client.objects.order_by("-created_at")[:5],
    }
    return render(request, "dashboard/home.html", context)
