from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin

from .forms import GoalForm, GoalTaskForm
from .models import Goal, GoalTask


class GoalListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Goal
    template_name = "goals/list.html"
    context_object_name = "goals"
    paginate_by = 20
    csv_filename = "maqsadlar.csv"
    csv_headers = ["Maqsad", "Davr", "Kategoriya", "Holat", "Progress", "Deadline"]

    def get_csv_row(self, obj):
        return [
            obj.title,
            obj.get_period_display(),
            obj.get_category_display(),
            obj.get_status_display(),
            f"{obj.progress}%",
            obj.deadline or "",
        ]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        period = self.request.GET.get("period")
        if period:
            qs = qs.filter(period=period)
        category = self.request.GET.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["period"] = self.request.GET.get("period", "")
        ctx["category"] = self.request.GET.get("category", "")
        ctx["status_choices"] = Goal.Status.choices
        ctx["period_choices"] = Goal.Period.choices
        ctx["category_choices"] = Goal.Category.choices

        today = timezone.localdate()
        all_goals = Goal.objects.all()
        ctx["stat_active"] = all_goals.filter(status=Goal.Status.ACTIVE).count()
        ctx["stat_completed"] = all_goals.filter(status=Goal.Status.COMPLETED).count()
        ctx["stat_overdue"] = all_goals.filter(
            status=Goal.Status.ACTIVE, deadline__lt=today
        ).count()
        return ctx


class GoalDetailView(LoginRequiredMixin, DetailView):
    model = Goal
    template_name = "goals/detail.html"
    context_object_name = "goal"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        goal = self.object
        tasks = goal.goal_tasks.all()
        today = timezone.localdate()

        ctx["tasks_all"] = tasks
        ctx["tasks_todo"] = tasks.filter(status=GoalTask.Status.TODO)
        ctx["tasks_in_progress"] = tasks.filter(status=GoalTask.Status.IN_PROGRESS)
        ctx["tasks_done"] = tasks.filter(status=GoalTask.Status.DONE)
        ctx["tasks_overdue"] = tasks.exclude(
            status__in=[GoalTask.Status.DONE, GoalTask.Status.SKIPPED]
        ).filter(due_date__lt=today)
        ctx["task_form"] = GoalTaskForm()
        ctx["status_choices"] = GoalTask.Status.choices
        ctx["today"] = today
        return ctx


class GoalCreateView(LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = "goals/form.html"
    success_url = reverse_lazy("goals:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Yangi maqsad qo'shish"
        return ctx


class GoalUpdateView(LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = "goals/form.html"

    def get_success_url(self):
        return reverse("goals:detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Maqsadni tahrirlash"
        return ctx


class GoalDeleteView(LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("goals:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("goals:detail", args=[self.object.pk])
        return ctx


# ── GoalTask views ──────────────────────────────────────────────────────────

@login_required
@require_POST
def goal_task_add(request, goal_pk):
    goal = get_object_or_404(Goal, pk=goal_pk)
    form = GoalTaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.goal = goal
        task.save()  # save() triggers recalc_progress
    return redirect("goals:detail", pk=goal_pk)


@login_required
@require_POST
def goal_task_set_status(request, pk):
    task = get_object_or_404(GoalTask, pk=pk)
    status = request.POST.get("status")
    if status in GoalTask.Status.values:
        task.status = status
        task.save()  # triggers recalc_progress via model save()
        return JsonResponse({
            "ok": True,
            "status": task.status,
            "label": task.get_status_display(),
            "progress": task.goal.progress,
        })
    return JsonResponse({"ok": False}, status=400)


@login_required
@require_POST
def goal_task_delete(request, pk):
    task = get_object_or_404(GoalTask, pk=pk)
    goal_pk = task.goal_id
    task.delete()
    # recalc after delete
    goal = Goal.objects.get(pk=goal_pk)
    goal.recalc_progress()
    return JsonResponse({"ok": True, "progress": goal.progress})
