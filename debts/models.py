from django.db import models
from django.utils import timezone


class Debt(models.Model):
    class Direction(models.TextChoices):
        I_OWE = "i_owe", "Men qarzdorman (men olganman)"
        THEY_OWE = "they_owe", "Menga qarzdor (men berganman)"

    class Status(models.TextChoices):
        PENDING = "pending", "To'lanmagan"
        PARTIAL = "partial", "Qisman to'langan"
        PAID = "paid", "To'liq to'langan"
        OVERDUE = "overdue", "Muddati o'tgan"
        CANCELLED = "cancelled", "Bekor qilingan"

    class Currency(models.TextChoices):
        UZS = "uzs", "UZS (so'm)"
        USD = "usd", "USD (dollar)"
        RUB = "rub", "RUB (rubl)"

    # Qarz yo'nalishi: men olganman yoki men berganman
    direction = models.CharField(
        "Qarz yo'nalishi",
        max_length=10,
        choices=Direction.choices,
        default=Direction.I_OWE,
    )

    # Qarama-qarshi tomon (ism)
    counterparty = models.CharField(
        "Qarama-qarshi tomon (ism / kompaniya)", max_length=200
    )

    # Mijoz bilan bog'lash (ixtiyoriy)
    client = models.ForeignKey(
        "clients.Client",
        verbose_name="Mijoz (ixtiyoriy)",
        related_name="debts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Loyiha bilan bog'lash (ixtiyoriy)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="Loyiha (ixtiyoriy)",
        related_name="debts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    amount = models.DecimalField("Qarz summasi", max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(
        "To'langan summa", max_digits=14, decimal_places=2, default=0
    )
    currency = models.CharField(
        "Valyuta", max_length=5, choices=Currency.choices, default=Currency.UZS
    )

    reason = models.CharField("Sabab / izoh qisqacha", max_length=300)
    notes = models.TextField("Batafsil izoh", blank=True)

    debt_date = models.DateField("Qarz olingan/berilgan sana", default=timezone.localdate)
    due_date = models.DateField("To'lov muddati", null=True, blank=True)

    status = models.CharField(
        "Holati", max_length=12, choices=Status.choices, default=Status.PENDING
    )

    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)
    updated_at = models.DateTimeField("O'zgartirilgan sana", auto_now=True)

    class Meta:
        verbose_name = "Qarz"
        verbose_name_plural = "Qarzlar"
        ordering = ["-debt_date", "-created_at"]

    def __str__(self):
        direction_label = "dan" if self.direction == self.Direction.I_OWE else "ga"
        return f"{self.counterparty}{direction_label} — {self.amount} {self.get_currency_display()}"

    @property
    def remaining_amount(self):
        return self.amount - self.paid_amount

    @property
    def is_overdue(self):
        return (
            self.status not in (self.Status.PAID, self.Status.CANCELLED)
            and self.due_date is not None
            and self.due_date < timezone.localdate()
        )

    @property
    def paid_percent(self):
        if self.amount == 0:
            return 0
        return int((self.paid_amount / self.amount) * 100)
