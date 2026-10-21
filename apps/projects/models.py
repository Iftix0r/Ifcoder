from django.db import models
from django.urls import reverse

from apps.core.models import TONE_CHOICES, Currency, TimeStamped


class Project(TimeStamped):
    class Status(models.TextChoices):
        IDEA = "idea", "G'oya"
        PLANNING = "planning", "Rejalashtirish"
        ACTIVE = "active", "Jarayonda"
        PAUSED = "paused", "To'xtatilgan"
        DONE = "done", "Yakunlangan"

    class Kind(models.TextChoices):
        CLIENT = "client", "Mijoz loyihasi"
        PRODUCT = "product", "O'z mahsulotim"
        PERSONAL = "personal", "Shaxsiy / o'qish"

    name = models.CharField("Nomi", max_length=200)
    kind = models.CharField("Turi", max_length=10, choices=Kind.choices, default=Kind.CLIENT)
    contact = models.ForeignKey(
        "crm.Contact", verbose_name="Mijoz", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects"
    )
    status = models.CharField("Holati", max_length=10, choices=Status.choices, default=Status.PLANNING)
    tone = models.CharField("Rang", max_length=10, choices=TONE_CHOICES, default="brand")
    description = models.TextField("Tavsif", blank=True)
    stack = models.CharField("Texnologiyalar", max_length=200, blank=True, help_text="Django, Flutter, PostgreSQL")
    repo_url = models.URLField("Repozitoriy", blank=True)
    live_url = models.URLField("Sayt / demo", blank=True)
    start_date = models.DateField("Boshlanish", null=True, blank=True)
    deadline = models.DateField("Muddat", null=True, blank=True)
    budget = models.DecimalField("Byudjet", max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Loyiha"
        verbose_name_plural = "Loyihalar"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("project_detail", args=[self.pk])

    @property
    def stack_list(self):
        return [s.strip() for s in self.stack.split(",") if s.strip()]

    @property
    def status_badge(self):
        return {
            "idea": "badge-neutral",
            "planning": "badge-brand",
            "active": "badge-success",
            "paused": "badge-warning",
            "done": "badge-neutral",
        }[self.status]
