from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin

from .forms import ClientForm
from .models import Client


class ClientListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Client
    template_name = "clients/list.html"
    context_object_name = "clients"
    paginate_by = 20
    csv_filename = "mijozlar.csv"
    csv_headers = ["Ism", "Telefon", "Telegram", "Email", "Qo'shilgan sana"]

    def get_csv_row(self, obj):
        return [obj.name, obj.phone, obj.telegram, obj.email, obj.created_at]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(phone__icontains=q)
                | Q(telegram__icontains=q)
                | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "clients/detail.html"
    context_object_name = "client"


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"
    success_url = reverse_lazy("clients:list")


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"

    def get_success_url(self):
        return reverse("clients:detail", args=[self.object.pk])


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("clients:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx
