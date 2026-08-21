from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin
from tasks.models import Task

from .forms import ProjectForm
from .models import Project


class ProjectListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20
    csv_filename = "loyihalar.csv"
    csv_headers = ["Nomi", "Mijoz", "Holati", "Muddat", "Yaratilgan sana"]

    def get_csv_row(self, obj):
        return [obj.name, obj.client, obj.get_status_display(), obj.deadline, obj.created_at]

    def get_queryset(self):
        qs = super().get_queryset().select_related("client")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = Project.Status.choices
        return ctx


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tasks_by_status"] = [
            (
                status,
                label,
                self.object.tasks.filter(status=status).select_related("assigned_to"),
            )
            for status, label in Task.Status.choices
        ]
        return ctx


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/form.html"
    success_url = reverse_lazy("projects:list")


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/form.html"

    def get_success_url(self):
        return reverse("projects:detail", args=[self.object.pk])


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("projects:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx
