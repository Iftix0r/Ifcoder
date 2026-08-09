from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin

from .forms import BotForm
from .models import Bot


class BotListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Bot
    template_name = "bots/list.html"
    context_object_name = "bots"
    paginate_by = 20
    csv_filename = "botlar.csv"
    csv_headers = ["Nomi", "Username", "Platforma", "Holati", "Loyiha", "Mijoz"]

    def get_csv_row(self, obj):
        return [
            obj.name,
            obj.username,
            obj.get_platform_display(),
            obj.get_status_display(),
            obj.project,
            obj.client,
        ]

    def get_queryset(self):
        qs = super().get_queryset().select_related("project", "client")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(username__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        platform = self.request.GET.get("platform")
        if platform:
            qs = qs.filter(platform=platform)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["platform"] = self.request.GET.get("platform", "")
        ctx["status_choices"] = Bot.Status.choices
        ctx["platform_choices"] = Bot.Platform.choices
        return ctx


class BotDetailView(LoginRequiredMixin, DetailView):
    model = Bot
    template_name = "bots/detail.html"
    context_object_name = "bot"


class BotCreateView(LoginRequiredMixin, CreateView):
    model = Bot
    form_class = BotForm
    template_name = "bots/form.html"
    success_url = reverse_lazy("bots:list")


class BotUpdateView(LoginRequiredMixin, UpdateView):
    model = Bot
    form_class = BotForm
    template_name = "bots/form.html"

    def get_success_url(self):
        return reverse("bots:detail", args=[self.object.pk])


class BotDeleteView(LoginRequiredMixin, DeleteView):
    model = Bot
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("bots:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx
