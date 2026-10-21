from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TONE_CHOICES, Currency, TimeStamped


class Kind(models.TextChoices):
    INCOME = "income", "Kirim"
    EXPENSE = "expense", "Chiqim"


class Category(models.Model):
    name = models.CharField("Nomi", max_length=80)
    kind = models.CharField("Turi", max_length=7, choices=Kind.choices)
    tone = models.CharField("Rang", max_length=10, choices=TONE_CHOICES, default="brand")

    class Meta:
        ordering = ["kind", "name"]
        verbose_name = "Toifa"
        verbose_name_plural = "Toifalar"

    def __str__(self):
        return self.name


DEFAULT_CATEGORIES = [
    ("Loyiha to'lovi", Kind.INCOME, "emerald"),
    ("Obuna / SaaS", Kind.INCOME, "cyan"),
    ("Maosh", Kind.INCOME, "brand"),
    ("Boshqa kirim", Kind.INCOME, "violet"),
    ("Server va hosting", Kind.EXPENSE, "rose"),
    ("Domen", Kind.EXPENSE, "amber"),
    ("Dasturlar / obunalar", Kind.EXPENSE, "violet"),
    ("O'qish va kitoblar", Kind.EXPENSE, "cyan"),
    ("Texnika", Kind.EXPENSE, "brand"),
    ("Shaxsiy", Kind.EXPENSE, "emerald"),
]


class Transaction(TimeStamped):
    class Method(models.TextChoices):
        CARD = "card", "Karta"
        CASH = "cash", "Naqd"
        BANK = "bank", "Bank o'tkazma"
        CRYPTO = "crypto", "Kripto / boshqa"

    kind = models.CharField("Turi", max_length=7, choices=Kind.choices, default=Kind.INCOME)
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    category = models.ForeignKey(Category, verbose_name="Toifa", null=True, blank=True, on_delete=models.SET_NULL)
    method = models.CharField("To'lov usuli", max_length=7, choices=Method.choices, default=Method.CARD)
    date = models.DateField("Sana", default=timezone.localdate)
    description = models.CharField("Izoh", max_length=250, blank=True)
    contact = models.ForeignKey(
        "crm.Contact", verbose_name="Mijoz", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions"
    )
    project = models.ForeignKey(
        "projects.Project", verbose_name="Loyiha", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions"
    )
    invoice = models.ForeignKey("Invoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Tranzaksiya"
        verbose_name_plural = "Tranzaksiyalar"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.amount} {self.currency}"

    @property
    def signed(self):
        return self.amount if self.kind == Kind.INCOME else -self.amount


def totals_by_currency(qs, field="amount"):
    """{"UZS": Decimal, "USD": Decimal} — faqat nol bo'lmaganlari."""
    rows = qs.values("currency").annotate(s=Sum(field))
    return {r["currency"]: r["s"] for r in rows if r["s"]}


class Invoice(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        SENT = "sent", "Yuborilgan"
        PAID = "paid", "To'langan"
        CANCELLED = "cancelled", "Bekor qilingan"

    number = models.CharField("Raqami", max_length=30, unique=True)
    contact = models.ForeignKey("crm.Contact", verbose_name="Mijoz", on_delete=models.PROTECT, related_name="invoices")
    project = models.ForeignKey(
        "projects.Project", verbose_name="Loyiha", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices"
    )
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    issued_date = models.DateField("Sana", default=timezone.localdate)
    due_date = models.DateField("To'lov muddati", null=True, blank=True)
    status = models.CharField("Holati", max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField("Izoh / to'lov rekvizitlari", blank=True)
    paid_at = models.DateField("To'langan sana", null=True, blank=True)

    class Meta:
        ordering = ["-issued_date", "-pk"]
        verbose_name = "Hisob-faktura"
        verbose_name_plural = "Hisob-fakturalar"

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("invoice_detail", args=[self.pk])

    @property
    def total(self):
        return sum((line.total for line in self.lines.all()), Decimal(0))

    @property
    def is_overdue(self):
        return self.status == self.Status.SENT and self.due_date and self.due_date < timezone.localdate()

    @property
    def status_badge(self):
        if self.is_overdue:
            return "badge-danger"
        return {"draft": "badge-neutral", "sent": "badge-warning", "paid": "badge-success", "cancelled": "badge-neutral"}[
            self.status
        ]

    @property
    def status_label(self):
        return "Muddati o'tgan" if self.is_overdue else self.get_status_display()

    @classmethod
    def next_number(cls):
        year = timezone.localdate().year
        prefix = f"INV-{year}-"
        last = cls.objects.filter(number__startswith=prefix).order_by("-number").values_list("number", flat=True).first()
        seq = int(last.rsplit("-", 1)[1]) + 1 if last and last.rsplit("-", 1)[1].isdigit() else 1
        return f"{prefix}{seq:03d}"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField("Xizmat", max_length=250)
    quantity = models.DecimalField("Miqdor", max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField("Narxi", max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["pk"]

    @property
    def total(self):
        return (self.quantity or 0) * (self.unit_price or 0)


class Debt(TimeStamped):
    class Direction(models.TextChoices):
        THEY_OWE = "they_owe", "Menga qarzdor"
        I_OWE = "i_owe", "Men qarzdorman"

    direction = models.CharField("Yo'nalish", max_length=8, choices=Direction.choices, default=Direction.THEY_OWE)
    person = models.CharField("Kim", max_length=150)
    contact = models.ForeignKey(
        "crm.Contact", verbose_name="Mijoz (CRM)", null=True, blank=True, on_delete=models.SET_NULL, related_name="debts"
    )
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField("Qaytarilgan", max_digits=14, decimal_places=2, default=0)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    reason = models.CharField("Sabab", max_length=250, blank=True)
    date = models.DateField("Sana", default=timezone.localdate)
    due_date = models.DateField("Qaytarish muddati", null=True, blank=True)
    is_closed = models.BooleanField("Yopilgan", default=False)

    class Meta:
        ordering = ["is_closed", "due_date", "-date"]
        verbose_name = "Qarz"
        verbose_name_plural = "Qarzlar"

    def __str__(self):
        return f"{self.person}: {self.amount}"

    @property
    def remaining(self):
        return max(Decimal(0), self.amount - self.paid_amount)
