from django.db import models

from clients.models import Client
from projects.models import Project


class Bot(models.Model):
    class Platform(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"
        OTHER = "other", "Boshqa"

    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        INACTIVE = "inactive", "Faol emas"

    name = models.CharField("Nomi", max_length=200)
    username = models.CharField("Username", max_length=100, blank=True)
    platform = models.CharField(
        "Platforma", max_length=20, choices=Platform.choices, default=Platform.TELEGRAM
    )
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    project = models.ForeignKey(
        Project,
        verbose_name="Loyiha",
        related_name="bots",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        related_name="bots",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Bot"
        verbose_name_plural = "Botlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
