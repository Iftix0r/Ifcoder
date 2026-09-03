from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin

from .forms import DebtForm
from .models import Debt


class DebtListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Debt
    template_name = "debts/list.html"
    context_object_name = "debts"
    paginate_by = 25
    csv_filename = "qarzlar.csv"
    csv_headers = [
        "Yo'nalish", "Tomon", "Sabab", "Summa", "To'langan",
        "Valyuta", "Holat", "Qarz sanasi", "To'lov muddati",
    ]

    def get_csv_row(self, obj):
        return [
            obj.get_direction_display(),
            obj.counterparty,
            obj.reason,
            obj.amount,
            obj.paid_amount,
            obj.get_currency_display(),
            obj.get_status_display(),
            obj.debt_date,
            obj.due_date or "",
        ]

    def get_queryset(self):
        qs = super().get_queryset()

        # Yo'nalish filtri
        direction = self.request.GET.get("direction")
        if direction in (Debt.Direction.I_OWE, Debt.Direction.THEY_OWE):
            qs = qs.filter(direction=direction)

        # Holat filtri
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        # Valyuta filtri
        currency = self.request.GET.get("currency")
        if currency:
            qs = qs.filter(currency=currency)

        # Qidiruv
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(counterparty__icontains=q)
                | Q(reason__icontains=q)
                | Q(notes__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Filtr holatlari
        ctx["q"] = self.request.GET.get("q", "")
        ctx["direction"] = self.request.GET.get("direction", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["currency"] = self.request.GET.get("currency", "")
        ctx["direction_choices"] = Debt.Direction.choices
        ctx["status_choices"] = Debt.Status.choices
        ctx["currency_choices"] = Debt.Currency.choices

        # Umumiy statistika (barcha qarzlar bo'yicha, filtrlanmagan)
        all_qs = Debt.objects.all()

        def _sum(qs):
            return qs.aggregate(
                s=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
            )["s"]

        def _paid(qs):
            return qs.aggregate(
                s=Coalesce(Sum("paid_amount"), Value(0, output_field=DecimalField()))
            )["s"]

        i_owe_qs = all_qs.filter(direction=Debt.Direction.I_OWE).exclude(
            status__in=[Debt.Status.PAID, Debt.Status.CANCELLED]
        )
        they_owe_qs = all_qs.filter(direction=Debt.Direction.THEY_OWE).exclude(
            status__in=[Debt.Status.PAID, Debt.Status.CANCELLED]
        )

        ctx["stat_i_owe"] = _sum(i_owe_qs) - _paid(i_owe_qs)
        ctx["stat_they_owe"] = _sum(they_owe_qs) - _paid(they_owe_qs)
        ctx["stat_overdue_count"] = all_qs.filter(
            status__in=[Debt.Status.PENDING, Debt.Status.PARTIAL],
        ).filter(due_date__lt=timezone.localdate()).count()

        return ctx


class DebtDetailView(LoginRequiredMixin, DetailView):
    model = Debt
    template_name = "debts/detail.html"
    context_object_name = "debt"


import html
from bots.telegram import send_telegram_message


class DebtCreateView(LoginRequiredMixin, CreateView):
    model = Debt
    form_class = DebtForm
    template_name = "debts/form.html"
    success_url = reverse_lazy("debts:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        try:
            d = self.object
            cp = html.escape(d.counterparty)
            direction = "Men qarzdorman" if d.direction == Debt.Direction.I_OWE else "Menga qarzdor"
            due_str = d.due_date.strftime("%d.%m.%Y") if d.due_date else "Belgilanmagan"
            msg = (
                f"💸 <b>YANGI QARZ YOZUVY QO'SHILDI</b>\n\n"
                f"👤 <b>Tomon:</b> {cp} ({direction})\n"
                f"💰 <b>Summa:</b> {d.amount:,.2f} {d.get_currency_display()}\n"
                f"📅 <b>To'lov muddati:</b> {due_str}\n"
                f"📝 <b>Sabab:</b> {html.escape(d.reason)}"
            )
            send_telegram_message(msg)
        except Exception:
            pass
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Yangi qarz qo'shish"
        return ctx


class DebtUpdateView(LoginRequiredMixin, UpdateView):
    model = Debt
    form_class = DebtForm
    template_name = "debts/form.html"

    def get_success_url(self):
        return reverse("debts:detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form_title"] = "Qarzni tahrirlash"
        return ctx


class DebtDeleteView(LoginRequiredMixin, DeleteView):
    model = Debt
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("debts:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("debts:detail", args=[self.object.pk])
        return ctx
