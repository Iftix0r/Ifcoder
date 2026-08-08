from django.db import models
from django.utils import timezone

from clients.models import Client
from projects.models import Project


class Income(models.Model):
    class Method(models.TextChoices):
        CASH = "naqd", "Naqd"
        CARD = "karta", "Karta"
        OTHER = "boshqa", "Boshqa"

    amount = models.DecimalField("Summa", max_digits=12, decimal_places=2)
    method = models.CharField(
        "To'lov usuli", max_length=20, choices=Method.choices, default=Method.CARD
    )
    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        related_name="incomes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        verbose_name="Loyiha",
        related_name="incomes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.TextField("Tavsif", blank=True)
    date = models.DateField("Sana", default=timezone.localdate)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Daromad"
        verbose_name_plural = "Daromadlar"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.amount} — {self.date}"


class Expense(models.Model):
    class Category(models.TextChoices):
        SERVER = "server", "Server"
        DOMAIN = "domain", "Domen"
        SUBSCRIPTION = "subscription", "Obuna"
        OTHER = "other", "Boshqa"

    amount = models.DecimalField("Summa", max_digits=12, decimal_places=2)
    category = models.CharField(
        "Toifa", max_length=20, choices=Category.choices, default=Category.OTHER
    )
    description = models.TextField("Tavsif", blank=True)
    date = models.DateField("Sana", default=timezone.localdate)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Xarajat"
        verbose_name_plural = "Xarajatlar"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.amount} — {self.date}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        SENT = "sent", "Yuborilgan"
        PAID = "paid", "To'langan"
        OVERDUE = "overdue", "Muddati o'tgan"

    number = models.CharField("Raqami", max_length=50, unique=True)
    client = models.ForeignKey(
        Client, verbose_name="Mijoz", related_name="invoices", on_delete=models.PROTECT
    )
    project = models.ForeignKey(
        Project,
        verbose_name="Loyiha",
        related_name="invoices",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    amount = models.DecimalField("Summa", max_digits=12, decimal_places=2)
    issued_date = models.DateField("Chiqarilgan sana", default=timezone.localdate)
    due_date = models.DateField("To'lov muddati")
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Hisob-faktura"
        verbose_name_plural = "Hisob-fakturalar"
        ordering = ["-issued_date"]

    def __str__(self):
        return self.number

    @property
    def is_overdue(self):
        return self.status != self.Status.PAID and self.due_date < timezone.localdate()
