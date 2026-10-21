from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, form_modal
from apps.crm.models import Deal
from apps.finance.models import Kind, totals_by_currency
from apps.planner.models import Task

from .forms import ProjectForm
from .models import Project


def project_list(request):
    status = request.GET.get("status", "open")
    qs = Project.objects.select_related("contact").annotate(
        task_total=Count("tasks", distinct=True),
        task_done=Count("tasks", filter=Q(tasks__status=Task.Status.DONE), distinct=True),
    )
    if status == "open":
        qs = qs.exclude(status__in=[Project.Status.DONE])
    elif status in Project.Status.values:
        qs = qs.filter(status=status)
    counts = dict(Project.objects.values_list("status").annotate(n=Count("id")))
    tabs = [("open", "Ochiq", sum(n for s, n in counts.items() if s != "done"))] + [
        (v, label, counts.get(v, 0)) for v, label in Project.Status.choices
    ]
    return render(
        request, "projects/list.html", {"nav_active": "projects", "projects": qs, "status": status, "tabs": tabs}
    )


def project_detail(request, pk):
    project = get_object_or_404(Project.objects.select_related("contact"), pk=pk)
    tasks = project.tasks.select_related("contact")
    open_tasks = tasks.exclude(status=Task.Status.DONE)
    done_tasks = tasks.filter(status=Task.Status.DONE).order_by("-completed_at")
    total = tasks.count()
    minutes = sum(e.minutes for e in project.time_entries.all())
    income = totals_by_currency(project.transactions.filter(kind=Kind.INCOME))
    expense = totals_by_currency(project.transactions.filter(kind=Kind.EXPENSE))
    return render(
        request,
        "projects/detail.html",
        {
            "nav_active": "projects",
            "project": project,
            "open_tasks": open_tasks,
            "done_tasks": done_tasks[:10],
            "progress": round(done_tasks.count() * 100 / total) if total else 0,
            "hours": minutes / 60,
            "income": income,
            "expense": expense,
            "transactions": project.transactions.select_related("category")[:8],
            "notes": project.notes.all()[:6],
            "resources": project.resources.all(),
            "secrets": project.secrets.all(),
            "deals": project.deals.select_related("contact"),
            "invoices": project.invoices.prefetch_related("lines"),
            "today": timezone.localdate(),
        },
    )


def project_create(request):
    initial = {"start_date": timezone.localdate()}
    deal = None
    if request.GET.get("deal", "").isdigit():
        deal = Deal.objects.filter(pk=request.GET["deal"]).select_related("contact").first()
        if deal:
            initial.update(
                name=deal.title, contact=deal.contact_id, budget=deal.value, currency=deal.currency, status="active"
            )
    if request.GET.get("contact"):
        initial["contact"] = request.GET["contact"]

    def save(form):
        project = form.save()
        if deal:
            deal.project = project
            deal.save(update_fields=["project", "updated_at"])
        return project

    return form_modal(
        request,
        ProjectForm,
        title="Yangi loyiha",
        icon="folder-plus",
        tone="tone-violet",
        size="xl",
        initial=initial,
        save=save,
        redirect=lambda p: p.get_absolute_url(),
    )


def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return form_modal(
        request,
        ProjectForm,
        instance=project,
        title=project.name,
        icon="folder-pen",
        tone="tone-violet",
        size="xl",
        delete_url=reverse("project_delete", args=[pk]),
    )


@require_POST
def project_delete(request, pk):
    return delete_done(get_object_or_404(Project, pk=pk), redirect=reverse("project_list"))
