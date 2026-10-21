from datetime import date

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, done, form_modal

from .forms import CategoryForm, CreditForm, DebtForm, InvoiceForm, InvoiceLineForm, TransactionForm
from .models import Category, Credit, CreditPayment, Debt, Invoice, InvoiceLine, Kind, Transaction, totals_by_currency

MONTHS = [
    "",
    "Yanvar",
    "Fevral",
    "Mart",
    "Aprel",
    "May",
    "Iyun",
    "Iyul",
    "Avgust",
    "Sentabr",
    "Oktabr",
    "Noyabr",
    "Dekabr",
]


def _month(request):
    today = timezone.localdate()
    raw = request.GET.get("m", "")
    try:
        y, m = (int(x) for x in raw.split("-"))
        return date(y, m, 1)
    except ValueError:
        return today.replace(day=1)


def _shift(d, months):
    m = d.month - 1 + months
    return date(d.year + m // 12, m % 12 + 1, 1)


def month_series(months=6, currency="UZS"):
    """Oxirgi N oy: kirim/chiqim (bitta valyutada) — dashboard va moliya grafigi uchun."""
    start = _shift(timezone.localdate().replace(day=1), -(months - 1))
    rows = (
        Transaction.objects.filter(date__gte=start, currency=currency)
        .annotate(month=TruncMonth("date"))
        .values("month", "kind")
        .annotate(s=Sum("amount"))
    )
    data = {}
    for r in rows:
        key = r["month"].date() if hasattr(r["month"], "date") else r["month"]
        data.setdefault(key, {})[r["kind"]] = r["s"] or 0
    series = []
    for i in range(months):
        m = _shift(start, i)
        series.append(
            {
                "label": MONTHS[m.month][:3],
                "income": data.get(m, {}).get("income", 0),
                "expense": data.get(m, {}).get("expense", 0),
            }
        )
    peak = max([max(s["income"], s["expense"]) for s in series] + [1])
    for s in series:
        s["income_h"] = round(float(s["income"]) * 100 / float(peak))
        s["expense_h"] = round(float(s["expense"]) * 100 / float(peak))
    return series


def overview(request):
    month = _month(request)
    nxt = _shift(month, 1)
    kind = request.GET.get("kind", "")
    category = request.GET.get("category", "")
    month_qs = Transaction.objects.filter(date__gte=month, date__lt=nxt)
    txs = month_qs.select_related("category", "contact", "project")
    if kind in Kind.values:
        txs = txs.filter(kind=kind)
    if category.isdigit():
        txs = txs.filter(category_id=category)
    income = totals_by_currency(month_qs.filter(kind=Kind.INCOME))
    expense = totals_by_currency(month_qs.filter(kind=Kind.EXPENSE))
    net = {c: income.get(c, 0) - expense.get(c, 0) for c in set(income) | set(expense)}
    breakdown = list(
        month_qs.filter(kind=Kind.EXPENSE, currency="UZS")
        .values("category__name", "category__tone")
        .annotate(s=Sum("amount"))
        .order_by("-s")
    )
    exp_total = sum(r["s"] for r in breakdown) or 0
    for r in breakdown:
        r["pct"] = round(float(r["s"]) * 100 / float(exp_total)) if exp_total else 0
    unpaid = Invoice.objects.filter(status=Invoice.Status.SENT)
    return render(
        request,
        "finance/overview.html",
        {
            "nav_active": "finance",
            "month": month,
            "month_label": f"{MONTHS[month.month]} {month.year}",
            "prev": _shift(month, -1),
            "next": nxt,
            "is_current": month == timezone.localdate().replace(day=1),
            "transactions": txs,
            "income": income,
            "expense": expense,
            "net": {k: v for k, v in net.items() if v},
            "series": month_series(6),
            "breakdown": breakdown,
            "categories": Category.objects.all(),
            "kind": kind,
            "category": category,
            "unpaid": totals_by_currency_lines(unpaid),
            "unpaid_count": unpaid.count(),
        },
    )


def totals_by_currency_lines(invoices):
    out = {}
    for inv in invoices.prefetch_related("lines"):
        out[inv.currency] = out.get(inv.currency, 0) + inv.total
    return out


def transaction_create(request):
    kind = request.GET.get("kind", Kind.INCOME)
    initial = {"kind": kind if kind in Kind.values else Kind.INCOME}
    for key in ("project", "contact", "invoice"):
        if request.GET.get(key):
            initial[key] = request.GET[key]
    is_income = initial["kind"] == Kind.INCOME
    return form_modal(
        request,
        TransactionForm,
        initial=initial,
        title="Kirim qo'shish" if is_income else "Chiqim qo'shish",
        icon="trending-up" if is_income else "trending-down",
        tone="tone-emerald" if is_income else "tone-rose",
        subtitle="Pul harakatini yozib boring — oy oxirida aniq hisob bo'ladi",
    )


def transaction_edit(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    return form_modal(
        request,
        TransactionForm,
        instance=tx,
        title=f"{tx.get_kind_display()}",
        icon="wallet",
        tone="tone-emerald" if tx.kind == Kind.INCOME else "tone-rose",
        delete_url=reverse("transaction_delete", args=[pk]),
    )


@require_POST
def transaction_delete(request, pk):
    return delete_done(get_object_or_404(Transaction, pk=pk))


def category_list(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        form = CategoryForm()
    return render(request, "finance/partials/categories.html", {"form": form, "categories": Category.objects.all()})


@require_POST
def category_delete(request, pk):
    get_object_or_404(Category, pk=pk).delete()
    return render(
        request, "finance/partials/categories.html", {"form": CategoryForm(), "categories": Category.objects.all()}
    )


# --- Hisob-fakturalar ---------------------------------------------------------------------


def invoice_list(request):
    status = request.GET.get("status", "")
    qs = Invoice.objects.select_related("contact", "project").prefetch_related("lines")
    if status == "overdue":
        qs = qs.filter(status=Invoice.Status.SENT, due_date__lt=timezone.localdate())
    elif status in Invoice.Status.values:
        qs = qs.filter(status=status)
    tabs = [("", "Barchasi")] + list(Invoice.Status.choices[:3]) + [("overdue", "Muddati o'tgan")]
    invoices = list(qs)
    return render(
        request,
        "finance/invoice_list.html",
        {
            "nav_active": "invoices",
            "invoices": invoices,
            "status": status,
            "tabs": tabs,
            "outstanding": totals_by_currency_lines(Invoice.objects.filter(status=Invoice.Status.SENT)),
            "paid_year": totals_by_currency_lines(
                Invoice.objects.filter(status=Invoice.Status.PAID, paid_at__year=timezone.localdate().year)
            ),
        },
    )


def invoice_create(request):
    initial = {"number": Invoice.next_number()}
    for key in ("contact", "project"):
        if request.GET.get(key):
            initial[key] = request.GET[key]
    return form_modal(
        request,
        InvoiceForm,
        initial=initial,
        title="Yangi hisob-faktura",
        icon="receipt-text",
        tone="tone-cyan",
        subtitle="Keyingi qadamda xizmatlar qatorini qo'shasiz",
        redirect=lambda inv: inv.get_absolute_url(),
    )


def invoice_edit(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    return form_modal(
        request,
        InvoiceForm,
        instance=inv,
        title=inv.number,
        icon="receipt-text",
        tone="tone-cyan",
        delete_url=reverse("invoice_delete", args=[pk]),
    )


@require_POST
def invoice_delete(request, pk):
    return delete_done(get_object_or_404(Invoice, pk=pk), redirect=reverse("invoice_list"))


def invoice_detail(request, pk):
    inv = get_object_or_404(Invoice.objects.select_related("contact", "project"), pk=pk)
    form = InvoiceLineForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        line = form.save(commit=False)
        line.invoice = inv
        line.save()
        return done("Qator qo'shildi.", close=False)
    return render(
        request,
        "finance/invoice_detail.html",
        {"nav_active": "invoices", "inv": inv, "lines": inv.lines.all(), "form": form, "payments": inv.payments.all()},
    )


@require_POST
def invoice_line_delete(request, pk):
    return delete_done(get_object_or_404(InvoiceLine, pk=pk), "Qator o'chirildi.")


@require_POST
def invoice_status(request, pk):
    inv = get_object_or_404(Invoice, pk=pk)
    status = request.POST.get("status")
    if status not in Invoice.Status.values:
        return HttpResponse(status=400)
    inv.status = status
    if status == Invoice.Status.PAID:
        inv.paid_at = inv.paid_at or timezone.localdate()
        if not inv.payments.exists() and inv.total:
            incomes = Category.objects.filter(kind=Kind.INCOME)
            category = incomes.filter(name__istartswith="Loyiha").first() or incomes.first()
            Transaction.objects.create(
                kind=Kind.INCOME,
                amount=inv.total,
                currency=inv.currency,
                category=category,
                date=inv.paid_at,
                description=f"{inv.number} bo'yicha to'lov",
                contact=inv.contact,
                project=inv.project,
                invoice=inv,
            )
    else:
        inv.paid_at = None
    inv.save()
    message = (
        "To'langan deb belgilandi — kirim avtomatik yozildi." if status == Invoice.Status.PAID else "Holat yangilandi."
    )
    return done(message, close=False)


def invoice_print(request, pk):
    inv = get_object_or_404(Invoice.objects.select_related("contact", "project"), pk=pk)
    return render(request, "finance/invoice_print.html", {"inv": inv, "lines": inv.lines.all(), "user": request.user})


# --- Qarzlar ----------------------------------------------------------------------------


def debt_list(request):
    show_closed = request.GET.get("closed") == "1"
    qs = Debt.objects.select_related("contact")
    if not show_closed:
        qs = qs.filter(is_closed=False)
    open_qs = Debt.objects.filter(is_closed=False)

    def remaining(direction):
        out = {}
        for d in open_qs.filter(direction=direction):
            out[d.currency] = out.get(d.currency, 0) + d.remaining
        return out

    return render(
        request,
        "finance/debt_list.html",
        {
            "nav_active": "debts",
            "they_owe": qs.filter(direction=Debt.Direction.THEY_OWE),
            "i_owe": qs.filter(direction=Debt.Direction.I_OWE),
            "they_total": remaining(Debt.Direction.THEY_OWE),
            "i_total": remaining(Debt.Direction.I_OWE),
            "show_closed": show_closed,
            "overdue": open_qs.filter(due_date__lt=timezone.localdate()).count(),
        },
    )


def debt_create(request):
    direction = request.GET.get("direction", Debt.Direction.THEY_OWE)
    return form_modal(
        request,
        DebtForm,
        initial={"direction": direction},
        title="Yangi qarz",
        icon="hand-coins",
        tone="tone-amber",
    )


def debt_edit(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    return form_modal(
        request,
        DebtForm,
        instance=debt,
        title=debt.person,
        icon="hand-coins",
        tone="tone-amber",
        delete_url=reverse("debt_delete", args=[pk]),
    )


@require_POST
def debt_delete(request, pk):
    return delete_done(get_object_or_404(Debt, pk=pk))


@require_POST
def debt_close(request, pk):
    debt = get_object_or_404(Debt, pk=pk)
    debt.is_closed = not debt.is_closed
    if debt.is_closed:
        debt.paid_amount = debt.amount
    debt.save()
    return done("Qarz yopildi ✅" if debt.is_closed else "Qayta ochildi.", close=False)


# --- Kreditlar va bo'lib to'lash ----------------------------------------------------


def credit_list(request):
    show_closed = request.GET.get("closed") == "1"
    credits = list(Credit.objects.prefetch_related("payments").filter(**({} if show_closed else {"is_closed": False})))
    active = [c for c in credits if not c.is_closed]
    monthly, remaining = {}, {}
    for c in active:
        monthly[c.currency] = monthly.get(c.currency, 0) + c.monthly_payment
        remaining[c.currency] = remaining.get(c.currency, 0) + c.remaining
    upcoming = sorted((c for c in active if c.next_due), key=lambda c: c.next_due)
    return render(
        request,
        "finance/credit_list.html",
        {
            "nav_active": "debts",
            "credits": credits,
            "monthly": monthly,
            "remaining": remaining,
            "next_credit": upcoming[0] if upcoming else None,
            "overdue": sum(1 for c in active if c.next_due and c.next_due < timezone.localdate()),
            "show_closed": show_closed,
        },
    )


def credit_create(request):
    return form_modal(
        request,
        CreditForm,
        title="Kredit yoki bo'lib to'lash",
        icon="credit-card",
        tone="tone-rose",
        size="xl",
        initial={"first_payment_date": _shift(timezone.localdate(), 1)},
        subtitle="Har oylik to'lov jadvali avtomatik tuziladi",
    )


def credit_edit(request, pk):
    credit = get_object_or_404(Credit, pk=pk)
    return form_modal(
        request,
        CreditForm,
        instance=credit,
        title=credit.title,
        icon=credit.icon,
        tone="tone-rose",
        size="xl",
        delete_url=reverse("credit_delete", args=[pk]),
    )


@require_POST
def credit_delete(request, pk):
    return delete_done(get_object_or_404(Credit, pk=pk), "Kredit o'chirildi.")


def _credit_category():
    category, _ = Category.objects.get_or_create(name="Kredit va nasiya", kind=Kind.EXPENSE, defaults={"tone": "rose"})
    return category


@require_POST
def credit_pay(request, pk):
    """Navbatdagi oy to'lovini belgilaydi va chiqimga yozadi."""
    credit = get_object_or_404(Credit.objects.prefetch_related("payments"), pk=pk)
    if credit.next_due is None:
        return done("Bu kredit to'liq to'langan.", close=False)
    period, amount = credit.paid_count, credit.next_amount
    tx = Transaction.objects.create(
        kind=Kind.EXPENSE,
        amount=amount,
        currency=credit.currency,
        category=_credit_category(),
        description=f"{credit.title}: {period + 1}/{credit.months}-to'lov",
    )
    CreditPayment.objects.create(credit=credit, period=period, amount=amount, transaction=tx)
    if period + 1 >= credit.months:
        credit.is_closed = True
        credit.save(update_fields=["is_closed", "updated_at"])
        return done(f"🎉 «{credit.title}» to'liq yopildi!", close=False)
    return done(f"{period + 1}/{credit.months}-to'lov yozildi (chiqimga ham).", close=False)


@require_POST
def credit_unpay(request, pk):
    """Oxirgi to'lovni bekor qiladi (xato bosilgan bo'lsa)."""
    credit = get_object_or_404(Credit, pk=pk)
    last = credit.payments.order_by("-period").first()
    if last:
        if last.transaction:
            last.transaction.delete()
        last.delete()
        if credit.is_closed:
            credit.is_closed = False
            credit.save(update_fields=["is_closed", "updated_at"])
    return done("Oxirgi to'lov bekor qilindi.", close=False)
