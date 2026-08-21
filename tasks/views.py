from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin

from .forms import TaskForm
from .models import Task


class TaskListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Task
    template_name = "tasks/list.html"
    context_object_name = "tasks"
    paginate_by = 20
    csv_filename = "vazifalar.csv"
    csv_headers = ["Sarlavha", "Holati", "Muhimlik", "Muddat", "Loyiha", "Mijoz"]

    def get_csv_row(self, obj):
        return [
            obj.title,
            obj.get_status_display(),
            obj.get_priority_display(),
            obj.due_date,
            obj.project,
            obj.client,
        ]

    def get_queryset(self):
        qs = super().get_queryset().select_related("project", "client")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = Task.Status.choices
        return ctx


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/detail.html"
    context_object_name = "task"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Task.Status.choices
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/form.html"
    success_url = reverse_lazy("tasks:list")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/form.html"

    def get_success_url(self):
        return reverse("tasks:detail", args=[self.object.pk])


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("tasks:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx


@login_required
@require_POST
def task_set_status(request, pk):
    task = Task.objects.get(pk=pk)
    status = request.POST.get("status")
    if status in Task.Status.values:
        task.status = status
        task.save(update_fields=["status"])
        return JsonResponse({"ok": True, "status": task.status, "label": task.get_status_display()})
    return JsonResponse({"ok": False}, status=400)
