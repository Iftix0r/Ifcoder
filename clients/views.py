from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
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
        qs = super().get_queryset().annotate(
            project_count=Count("projects", distinct=True),
            bot_count=Count("bots", distinct=True),
        )
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(phone__icontains=q)
                | Q(telegram__icontains=q)
                | Q(email__icontains=q)
            )
        lead_status = self.request.GET.get("lead_status")
        if lead_status:
            qs = qs.filter(lead_status=lead_status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["lead_status"] = self.request.GET.get("lead_status", "")
        ctx["lead_status_choices"] = Client.LeadStatus.choices
        return ctx


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "clients/detail.html"
    context_object_name = "client"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client = self.object
        ctx["projects"] = client.projects.select_related("client").all()
        ctx["bots"] = client.bots.select_related("project").all()
        ctx["tasks"] = client.tasks.select_related("project").exclude(
            status="done"
        )[:10]
        
        incomes = client.incomes.all()
        invoices = client.invoices.all()
        
        ctx["total_income"] = sum(inc.amount for inc in incomes)
        ctx["total_invoiced"] = sum(inv.amount for inv in invoices)
        ctx["paid_invoiced"] = sum(inv.amount for inv in invoices if inv.status == "paid")
        ctx["unpaid_invoiced"] = ctx["total_invoiced"] - ctx["paid_invoiced"]
        ctx["invoices"] = invoices[:10]
        ctx["tickets"] = client.tickets.select_related("project").all()[:10]
        return ctx


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"
    success_url = reverse_lazy("clients:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        self._apply_tg_avatar(self.object)
        return response

    def _apply_tg_avatar(self, client):
        tg_path = self.request.POST.get("tg_avatar_path", "").strip()
        if tg_path and not client.avatar:
            from django.conf import settings
            import os
            full_path = os.path.join(settings.MEDIA_ROOT, tg_path)
            if os.path.exists(full_path):
                client.avatar = tg_path
                client.save(update_fields=["avatar"])


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"

    def get_success_url(self):
        return reverse("clients:detail", args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        self._apply_tg_avatar(self.object)
        return response

    def _apply_tg_avatar(self, client):
        tg_path = self.request.POST.get("tg_avatar_path", "").strip()
        if tg_path and not client.avatar:
            from django.conf import settings
            import os
            full_path = os.path.join(settings.MEDIA_ROOT, tg_path)
            if os.path.exists(full_path):
                client.avatar = tg_path
                client.save(update_fields=["avatar"])


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("clients:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx
