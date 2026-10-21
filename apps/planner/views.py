import json
from datetime import timedelta

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, done, form_modal
from apps.core.htmx import add_triggers
from apps.projects.models import Project

from . import services
from .forms import TaskForm, TimeEntryForm
from .models import Task, TimeEntry

COLUMNS = [
    (Task.Status.TODO, "bg-brand-500", "ring-brand-500/30"),
    (Task.Status.DOING, "bg-amber-500", "ring-amber-500/30"),
    (Task.Status.DONE, "bg-emerald-500", "ring-emerald-500/30"),
]
VIEWS = [
    ("board", "Kanban", "square-kanban"),
    ("today", "Bugun", "sun"),
    ("week", "Hafta", "calendar-range"),
    ("list", "Ro'yxat", "list"),
]


def _filtered(request):
    qs = Task.objects.select_related("project", "contact")
    q = request.GET.get("q", "").strip()
    project = request.GET.get("project", "")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(notes__icontains=q))
    if project.isdigit():
        qs = qs.filter(project_id=project)
    return qs, q, project


def board(request):
    view = request.GET.get("view", "board")
    if view not in dict((v[0], v) for v in VIEWS):
        view = "board"
    qs, q, project = _filtered(request)
    today = timezone.localdate()
    ctx = {
        "nav_active": "tasks",
        "view": view,
        "views": VIEWS,
        "q": q,
        "project": project,
        "projects": Project.objects.exclude(status=Project.Status.DONE),
        "today": today,
    }
    open_qs = qs.exclude(status=Task.Status.DONE)
    if view == "board":
        cutoff = timezone.now() - timedelta(days=14)
        ctx["columns"] = [
            {
                "status": status,
                "dot": dot,
                "ring": ring,
                "tasks": list(
                    (
                        qs.filter(status=status, completed_at__gte=cutoff).order_by("-completed_at")
                        if status == Task.Status.DONE
                        else qs.filter(status=status)
                    )[:100]
                ),
            }
            for status, dot, ring in COLUMNS
        ]
    elif view == "today":
        ctx["groups"] = [
            ("Muddati o'tgan", "badge-danger", open_qs.filter(Q(due_date__lt=today) | Q(planned_for__lt=today))),
            (
                "Bugun",
                "badge-brand",
                open_qs.filter(Q(planned_for=today) | Q(due_date=today, planned_for__isnull=True)).exclude(
                    due_date__lt=today
                ),
            ),
            (
                "Jarayonda",
                "badge-warning",
                open_qs.filter(status=Task.Status.DOING).exclude(Q(planned_for__lte=today) | Q(due_date__lte=today)),
            ),
        ]
        ctx["done_today"] = qs.filter(completed_at__date=today)
    elif view == "week":
        w = request.GET.get("w", "0")
        offset = int(w) if w.lstrip("-").isdigit() else 0
        start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
        days = [start + timedelta(days=i) for i in range(7)]
        week_qs = qs.filter(
            Q(planned_for__range=(days[0], days[-1])) | Q(planned_for__isnull=True, due_date__range=(days[0], days[-1]))
        )
        by_day = {d: [] for d in days}
        for t in week_qs:
            by_day.setdefault(t.planned_for or t.due_date, []).append(t)
        ctx.update(
            days=[{"date": d, "tasks": by_day.get(d, []), "is_today": d == today} for d in days],
            inbox=open_qs.filter(planned_for__isnull=True, due_date__isnull=True)[:50],
            offset=offset,
            week_start=days[0],
            week_end=days[-1],
        )
    else:
        ctx["groups"] = [
            ("Muddati o'tgan", "badge-danger", open_qs.filter(due_date__lt=today).order_by("due_date")),
            ("Muddatli", "badge-brand", open_qs.filter(due_date__gte=today).order_by("due_date")),
            ("Muddatsiz", "badge-neutral", open_qs.filter(due_date__isnull=True)),
            (
                "Bajarilgan (oxirgi 30 kun)",
                "badge-success",
                qs.filter(status=Task.Status.DONE, completed_at__gte=timezone.now() - timedelta(days=30)).order_by(
                    "-completed_at"
                )[:50],
            ),
        ]
    ctx["stats"] = {
        "open": Task.objects.exclude(status=Task.Status.DONE).count(),
        "today": Task.objects.exclude(status=Task.Status.DONE).filter(planned_for=today).count(),
        "overdue": Task.objects.exclude(status=Task.Status.DONE).filter(due_date__lt=today).count(),
        "done_week": Task.objects.filter(completed_at__date__gte=today - timedelta(days=today.weekday())).count(),
    }
    return render(request, "planner/board.html", ctx)


def _initial(request):
    initial = {}
    for key in ("status", "project", "contact"):
        if request.GET.get(key):
            initial[key] = request.GET[key]
    if request.GET.get("planned_for"):
        initial["planned_for"] = request.GET["planned_for"]
    elif request.GET.get("today"):
        initial["planned_for"] = timezone.localdate()
    return initial


def task_create(request):
    def save(form):
        task = form.save(commit=False)
        task.set_status(task.status)
        task.save()
        return task

    return form_modal(
        request,
        TaskForm,
        title="Yangi vazifa",
        icon="list-todo",
        subtitle="Bitta aniq, bajariladigan qadam yozing",
        initial=_initial(request),
        save=save,
    )


def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    old_status = task.status

    def save(form):
        obj = form.save(commit=False)
        if obj.status != old_status:
            obj.set_status(obj.status)
        obj.save()
        return obj

    spent = sum(e.minutes for e in task.time_entries.all())
    return form_modal(
        request,
        TaskForm,
        instance=task,
        title="Vazifa",
        icon="square-pen",
        save=save,
        subtitle=f"Sarflangan vaqt: {spent // 60} soat {spent % 60} daq" if spent else "Hali vaqt yozilmagan",
        delete_url=reverse("task_delete", args=[pk]),
        template="planner/partials/task_form.html",
        extra={"task": task},
    )


@require_POST
def task_delete(request, pk):
    return delete_done(get_object_or_404(Task, pk=pk), "Vazifa o'chirildi.")


@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.set_status(Task.Status.TODO if task.is_done else Task.Status.DONE)
    task.save(update_fields=["status", "completed_at", "updated_at"])
    if task.is_done:
        running = services.running_entry()
        if running and running.task_id == task.pk:
            services.stop_timer()
    response = done("Bajarildi! 🎉" if task.is_done else "Qayta ochildi.", close=False)
    return add_triggers(response, {"timer:changed": True})


@require_POST
def task_plan(request, pk):
    task = get_object_or_404(Task, pk=pk)
    when = request.POST.get("when", "today")
    task.planned_for = None if when == "none" else timezone.localdate() + timedelta(days=1 if when == "tomorrow" else 0)
    task.save(update_fields=["planned_for", "updated_at"])
    return done("Rejaga qo'shildi." if task.planned_for else "Rejadan olindi.", close=False)


@require_POST
def task_quick(request):
    title = request.POST.get("title", "").strip()[:250]
    if not title:
        return HttpResponse(status=204)
    task = Task(title=title)
    if request.POST.get("planned_for"):
        task.planned_for = request.POST["planned_for"]
    if request.POST.get("project", "").isdigit():
        task.project_id = int(request.POST["project"])
    if request.POST.get("status") in Task.Status.values:
        task.status = request.POST["status"]
    task.set_status(task.status)
    task.save()
    return done("Vazifa qo'shildi.", close=False)


@require_POST
def task_move(request, pk):
    task = get_object_or_404(Task, pk=pk)
    try:
        payload = json.loads(request.body)
        status = payload["stage"]
        order = [int(i) for i in payload.get("order", [])]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False}, status=400)
    if status not in Task.Status.values:
        return JsonResponse({"ok": False}, status=400)
    if task.status != status:
        task.set_status(status)
        task.save(update_fields=["status", "completed_at", "updated_at"])
        if status == Task.Status.DONE:
            running = services.running_entry()
            if running and running.task_id == task.pk:
                services.stop_timer()
    services.reorder(Task, order)
    return JsonResponse(
        {"ok": True, "toast": "Bajarildi! 🎉" if status == Task.Status.DONE and task.status == status else ""}
    )


# --- Taymer ---------------------------------------------------------------------------


def _timer_response(message):
    response = done(message, event="timer:changed", close=False)
    return add_triggers(response, {"changed": True})


@require_POST
def timer_start(request, pk=None):
    task = get_object_or_404(Task, pk=pk) if pk else None
    services.start_timer(task, note=request.POST.get("note", "")[:250])
    return _timer_response("Taymer ishga tushdi ⏱")


@require_POST
def timer_stop(request):
    entry = services.stop_timer()
    return _timer_response(f"To'xtatildi: {entry.minutes} daqiqa yozildi." if entry else "Taymer ishlamayapti.")


def timer_chip(request):
    return render(request, "planner/partials/timer_chip.html")


def time_report(request):
    today = timezone.localdate()
    period = request.GET.get("period", "week")
    start = {
        "week": today - timedelta(days=today.weekday()),
        "month": today.replace(day=1),
        "30": today - timedelta(days=29),
    }.get(period, today - timedelta(days=today.weekday()))
    entries = list(
        TimeEntry.objects.select_related("task", "project").filter(started_at__date__gte=start).order_by("-started_at")
    )
    total = sum(e.minutes for e in entries)
    by_project = {}
    for e in entries:
        key = e.project or e.task and e.task.project
        name = str(key) if key else "Loyihasiz"
        tone = key.tone if key else "neutral"
        row = by_project.setdefault(name, {"name": name, "minutes": 0, "tone": tone})
        row["minutes"] += e.minutes
    projects = sorted(by_project.values(), key=lambda r: -r["minutes"])
    for row in projects:
        row["hours"] = row["minutes"] / 60
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    per_day = {d: 0 for d in days}
    for e in TimeEntry.objects.filter(started_at__date__gte=days[0]):
        d = timezone.localtime(e.started_at).date()
        if d in per_day:
            per_day[d] += e.minutes
    peak = max(per_day.values()) or 1
    return render(
        request,
        "planner/time_report.html",
        {
            "nav_active": "time",
            "entries": entries[:200],
            "total": total,
            "total_hours": total / 60,
            "projects": projects,
            "period": period,
            "start": start,
            "chart": [{"date": d, "minutes": m, "height": round(m * 100 / peak)} for d, m in per_day.items()],
        },
    )


def entry_create(request):
    return form_modal(
        request,
        TimeEntryForm,
        title="Vaqtni qo'lda yozish",
        icon="timer",
        tone="tone-amber",
        initial={
            "started_at": timezone.localtime().replace(second=0, microsecond=0) - timedelta(hours=1),
            "ended_at": timezone.localtime().replace(second=0, microsecond=0),
        },
    )


def entry_edit(request, pk):
    entry = get_object_or_404(TimeEntry, pk=pk)
    return form_modal(
        request,
        TimeEntryForm,
        instance=entry,
        title="Vaqt yozuvi",
        icon="timer",
        tone="tone-amber",
        delete_url=reverse("entry_delete", args=[pk]),
    )


@require_POST
def entry_delete(request, pk):
    response = delete_done(get_object_or_404(TimeEntry, pk=pk))
    return add_triggers(response, {"timer:changed": True})
