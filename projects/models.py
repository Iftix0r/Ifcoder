from django.db import models

from clients.models import Client


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Rejalashtirilmoqda"
        IN_PROGRESS = "in_progress", "Jarayonda"
        PAUSED = "paused", "To'xtatilgan"
        COMPLETED = "completed", "Yakunlangan"

    name = models.CharField("Nomi", max_length=200)
    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        related_name="projects",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    description = models.TextField("Tavsif", blank=True)
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.PLANNING
    )
    repo_url = models.URLField("Repozitoriy havolasi", blank=True)
    deadline = models.DateField("Muddat", null=True, blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Loyiha"
        verbose_name_plural = "Loyihalar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
