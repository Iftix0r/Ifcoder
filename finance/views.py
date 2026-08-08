from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ExpenseForm, IncomeForm, InvoiceForm
from .models import Expense, Income, Invoice


def _months_back(base, n):
    year, month = base.year, base.month - n
    while month <= 0:
        month += 12
        year -= 1
    return base.replace(year=year, month=month, day=1)


@login_required
def home(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    month_income = Income.objects.filter(date__gte=month_start).aggregate(total=Sum("amount"))[
        "total"
    ] or 0
    month_expense = Expense.objects.filter(date__gte=month_start).aggregate(
        total=Sum("amount")
    )["total"] or 0

    outstanding_invoices = Invoice.objects.exclude(status=Invoice.Status.PAID).select_related(
        "client"
    )
    outstanding_total = outstanding_invoices.aggregate(total=Sum("amount"))["total"] or 0

    range_start = _months_back(month_start, 5)
    income_by_month = {
        row["month"]: row["total"]
        for row in Income.objects.filter(date__gte=range_start)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
    }
    expense_by_month = {
        row["month"]: row["total"]
        for row in Expense.objects.filter(date__gte=range_start)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
    }
    monthly_summary = []
    for i in range(5, -1, -1):
        m = _months_back(month_start, i)
        m_income = income_by_month.get(m, 0)
        m_expense = expense_by_month.get(m, 0)
        monthly_summary.append(
            {
                "month": m,
                "income": m_income,
                "expense": m_expense,
                "diff": m_income - m_expense,
            }
        )

    context = {
        "month_income": month_income,
        "month_expense": month_expense,
        "outstanding_invoices": outstanding_invoices[:10],
        "outstanding_count": outstanding_invoices.count(),
        "outstanding_total": outstanding_total,
        "monthly_summary": monthly_summary,
        "recent_income": Income.objects.select_related("client", "project")[:5],
        "recent_expense": Expense.objects.all()[:5],
    }
    return render(request, "finance/home.html", context)


class IncomeListView(LoginRequiredMixin, ListView):
    model = Income
    template_name = "finance/income_list.html"
    context_object_name = "incomes"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "project")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(description__icontains=q) | Q(client__name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["total"] = self.get_queryset().aggregate(total=Sum("amount"))["total"] or 0
        return ctx


class IncomeDetailView(LoginRequiredMixin, DetailView):
    model = Income
    template_name = "finance/income_detail.html"
    context_object_name = "income"


class IncomeCreateView(LoginRequiredMixin, CreateView):
    model = Income
    form_class = IncomeForm
    template_name = "finance/income_form.html"
    success_url = reverse_lazy("finance:income_list")


class IncomeUpdateView(LoginRequiredMixin, UpdateView):
    model = Income
    form_class = IncomeForm
    template_name = "finance/income_form.html"

    def get_success_url(self):
        return reverse("finance:income_detail", args=[self.object.pk])


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = "finance/expense_list.html"
    context_object_name = "expenses"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(description__icontains=q))
        category = self.request.GET.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["category"] = self.request.GET.get("category", "")
        ctx["category_choices"] = Expense.Category.choices
        ctx["total"] = self.get_queryset().aggregate(total=Sum("amount"))["total"] or 0
        return ctx


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    model = Expense
    template_name = "finance/expense_detail.html"
    context_object_name = "expense"


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "finance/expense_form.html"
    success_url = reverse_lazy("finance:expense_list")


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = "finance/expense_form.html"

    def get_success_url(self):
        return reverse("finance:expense_detail", args=[self.object.pk])


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "finance/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "project")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(client__name__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = Invoice.Status.choices
        return ctx


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "finance/invoice_detail.html"
    context_object_name = "invoice"


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "finance/invoice_form.html"
    success_url = reverse_lazy("finance:invoice_list")


class InvoiceUpdateView(LoginRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "finance/invoice_form.html"

    def get_success_url(self):
        return reverse("finance:invoice_detail", args=[self.object.pk])


class InvoicePrintView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = "finance/invoice_print.html"
    context_object_name = "invoice"
