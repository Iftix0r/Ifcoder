import csv
from datetime import date

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, done, form_modal

from .forms import (
    BudgetForm,
    CategoryForm,
    CreditForm,
    DebtForm,
    InvoiceForm,
    InvoiceLineForm,
    RecurringForm,
    TransactionForm,
    WishDepositForm,
    WishForm,
)
from .models import (
    Budget,
    Category,
    Credit,
    CreditPayment,
    Debt,
    Invoice,
    InvoiceLine,
    Kind,
    Recurring,
    Transaction,
    Wish,
    totals_by_currency,
)

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


def budget_rows(month):
    """Oy bo'yicha byudjetlar: sarflangan, qolgan, foiz va rang (limitga yaqinlashganda sariq, oshganda qizil)."""
    spent = {
        (r["category_id"], r["currency"]): r["s"]
        for r in Transaction.objects.filter(kind=Kind.EXPENSE, date__gte=month, date__lt=_shift(month, 1))
        .values("category_id", "currency")
        .annotate(s=Sum("amount"))
    }
    rows = []
    for budget in Budget.objects.select_related("category"):
        used = spent.get((budget.category_id, budget.currency), 0)
        pct = round(float(used) * 100 / float(budget.amount)) if budget.amount else 100
        rows.append(
            {
                "budget": budget,
                "spent": used,
                "left": budget.amount - used,
                "pct": pct,
                "width": min(pct, 100),
                "over": used > budget.amount,
                "bar": "bg-rose-500"
                if used > budget.amount
                else "bg-amber-500"
                if pct >= Budget.WARN_AT
                else "bg-emerald-500",
            }
        )
    return sorted(rows, key=lambda r: -r["pct"])


def _month_transactions(request, month):
    """Oydagi operatsiyalar sahifadagi filtrlar bilan: ro'yxat va CSV bir xil natija beradi."""
    kind = request.GET.get("kind", "")
    category = request.GET.get("category", "")
    txs = Transaction.objects.filter(date__gte=month, date__lt=_shift(month, 1))
    txs = txs.select_related("category", "contact", "project")
    if kind in Kind.values:
        txs = txs.filter(kind=kind)
    if category.isdigit():
        txs = txs.filter(category_id=category)
    return txs, kind, category


def overview(request):
    month = _month(request)
    nxt = _shift(month, 1)
    month_qs = Transaction.objects.filter(date__gte=month, date__lt=nxt)
    txs, kind, category = _month_transactions(request, month)
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
            "budgets": budget_rows(month),
            "due_recurring": Recurring.objects.filter(is_active=True, next_date__lte=timezone.localdate()).count(),
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


def _csv_text(value):
    """Mijoz ismi landing formadan keladi: Excel «=...» ni formula sifatida ishga tushirmasin."""
    text = str(value or "")
    return f"'{text}" if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text


def _csv_amount(value):
    text = f"{value:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def transaction_export(request):
    """Excel uchun CSV: BOM kirill/o'zbek harflarini, «;» esa ustunlarni to'g'ri ochadi."""
    month = _month(request)
    txs, _, _ = _month_transactions(request, month)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="kirim-chiqim-{month:%Y-%m}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Sana", "Turi", "Summa", "Valyuta", "Toifa", "To'lov usuli", "Mijoz", "Loyiha", "Izoh"])
    for tx in txs:
        writer.writerow(
            [
                tx.date.isoformat(),
                tx.get_kind_display(),
                _csv_amount(tx.amount),
                tx.currency,
                _csv_text(tx.category),
                tx.get_method_display(),
                _csv_text(tx.contact),
                _csv_text(tx.project),
                _csv_text(tx.description),
            ]
        )
    return response


# --- Byudjet ------------------------------------------------------------------------------


def budget_create(request):
    return form_modal(
        request,
        BudgetForm,
        title="Oylik limit",
        icon="gauge",
        tone="tone-amber",
        subtitle="Toifaga oyiga qancha sarflashni belgilang",
    )


def budget_edit(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    return form_modal(
        request,
        BudgetForm,
        instance=budget,
        title=budget.category.name,
        icon="gauge",
        tone="tone-amber",
        delete_url=reverse("budget_delete", args=[pk]),
    )


@require_POST
def budget_delete(request, pk):
    return delete_done(get_object_or_404(Budget, pk=pk), "Limit o'chirildi.")


# --- Takroriy to'lovlar -------------------------------------------------------------------


def recurring_list(request):
    items = list(Recurring.objects.select_related("category", "contact", "project"))
    active = [r for r in items if r.is_active]
    monthly = {Kind.INCOME: {}, Kind.EXPENSE: {}}
    for r in active:
        bucket = monthly[r.kind]
        bucket[r.currency] = bucket.get(r.currency, 0) + r.monthly_amount
    return render(
        request,
        "finance/recurring_list.html",
        {
            "nav_active": "recurring",
            "due": [r for r in active if r.is_due],
            "upcoming": [r for r in active if not r.is_due],
            "paused": [r for r in items if not r.is_active],
            "monthly_income": monthly[Kind.INCOME],
            "monthly_expense": monthly[Kind.EXPENSE],
        },
    )


def recurring_create(request):
    kind = request.GET.get("kind", Kind.EXPENSE)
    return form_modal(
        request,
        RecurringForm,
        initial={"kind": kind if kind in Kind.values else Kind.EXPENSE},
        title="Takroriy to'lov",
        icon="calendar-clock",
        size="xl",
        subtitle="Vaqti kelganda eslatiladi, bir tugma bilan kirim-chiqimga yoziladi",
    )


def recurring_edit(request, pk):
    item = get_object_or_404(Recurring, pk=pk)
    return form_modal(
        request,
        RecurringForm,
        instance=item,
        title=item.title,
        icon="calendar-clock",
        size="xl",
        delete_url=reverse("recurring_delete", args=[pk]),
    )


@require_POST
def recurring_delete(request, pk):
    return delete_done(get_object_or_404(Recurring, pk=pk), "O'chirildi. Yozilgan operatsiyalar saqlanib qoladi.")


def _period(request, item):
    """Tugma qaysi davr uchun bosilgan: sahifa eskirgan bo'lsa, boshqa davrga yozib yubormaymiz."""
    return item.next_date if request.POST.get("period") == item.next_date.isoformat() else None


@require_POST
def recurring_post(request, pk):
    item = get_object_or_404(Recurring.objects.select_related("category", "contact", "project"), pk=pk)
    period = _period(request, item)
    if period and item.post(period):
        return done(f"«{item.title}» kirim-chiqimga yozildi.", close=False)
    return done("Bu davr allaqachon belgilangan.", close=False)


@require_POST
def recurring_skip(request, pk):
    item = get_object_or_404(Recurring, pk=pk)
    period = _period(request, item)
    if period and item.skip(period):
        return done("Bu davr o'tkazib yuborildi.", close=False)
    return done("Bu davr allaqachon belgilangan.", close=False)


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
    qs = Debt.objects.select_related("contact").prefetch_related("contact__telegram_dialogs")
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


# --- Orzular: sotib olmoqchi bo'lgan narsalar va ularga pul yig'ish ------------------------


def wish_list(request):
    show_bought = request.GET.get("bought") == "1"
    wishes = list(Wish.objects.prefetch_related("deposits"))
    active = [w for w in wishes if not w.is_bought]
    saved, needed = {}, {}
    for w in active:
        saved[w.currency] = saved.get(w.currency, 0) + w.saved
        needed[w.currency] = needed.get(w.currency, 0) + w.remaining
    order = {p: i for i, p in enumerate(Wish.Priority.values)}
    active.sort(key=lambda w: (not w.is_ready, order[w.priority], w.target_date or date.max))
    bought = [w for w in wishes if w.is_bought]
    return render(
        request,
        "finance/wish_list.html",
        {
            "nav_active": "wishes",
            "wishes": active + (bought if show_bought else []),
            "saved": saved,
            "needed": needed,
            "bought_count": len(bought),
            "ready_count": sum(1 for w in active if w.is_ready),
            "show_bought": show_bought,
        },
    )


def wish_create(request):
    return form_modal(
        request,
        WishForm,
        title="Yangi orzu",
        icon="sparkles",
        tone="tone-violet",
        size="xl",
        subtitle="Narxini yozing — har gal pul qo'shganingizda qancha qolganini ko'rasiz",
        success="Orzu qo'shildi ✨",
    )


def wish_edit(request, pk):
    wish = get_object_or_404(Wish, pk=pk)
    return form_modal(
        request,
        WishForm,
        instance=wish,
        title=wish.title,
        icon=wish.icon,
        tone=wish.tone,
        size="xl",
        delete_url=reverse("wish_delete", args=[pk]),
    )


@require_POST
def wish_delete(request, pk):
    return delete_done(get_object_or_404(Wish, pk=pk), "Orzu o'chirildi.")


def wish_deposit(request, pk):
    wish = get_object_or_404(Wish.objects.prefetch_related("deposits"), pk=pk)

    def save(form):
        deposit = form.save(commit=False)
        deposit.wish = wish
        deposit.save()
        return deposit

    return form_modal(
        request,
        WishDepositForm,
        title=f"{wish.title} uchun pul",
        icon="piggy-bank",
        tone="tone-emerald",
        subtitle=f"Hozircha {wish.progress}% yig'ildi",
        initial={"amount": wish.monthly_needed or wish.remaining},
        save=save,
        success="Pul qo'shildi 💰",
    )


@require_POST
def wish_undeposit(request, pk):
    """Oxirgi qo'shilgan pulni bekor qiladi (xato kiritilgan bo'lsa)."""
    wish = get_object_or_404(Wish, pk=pk)
    last = wish.deposits.order_by("-pk").first()
    if last:
        last.delete()
    return done("Oxirgi qo'shilgan pul bekor qilindi.", close=False)


@require_POST
def wish_buy(request, pk):
    """«Sotib oldim» — chiqimga yoziladi; qayta bosilsa bekor qilinadi."""
    wish = get_object_or_404(Wish, pk=pk)
    if wish.is_bought:
        wish.unbuy()
        return done("Yana orzular ro'yxatida.", close=False)
    wish.buy()
    return done(f"🎉 Tabriklaymiz! «{wish.title}» endi sizniki!", close=False)
