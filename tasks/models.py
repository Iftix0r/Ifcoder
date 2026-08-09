from django.db import models
from django.utils import timezone

from clients.models import Client
from projects.models import Project


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "Bajarilmagan"
        IN_PROGRESS = "in_progress", "Jarayonda"
        DONE = "done", "Bajarilgan"

    class Priority(models.TextChoices):
        LOW = "low", "Past"
        MEDIUM = "medium", "O'rta"
        HIGH = "high", "Yuqori"

    title = models.CharField("Sarlavha", max_length=200)
    description = models.TextField("Tavsif", blank=True)
    project = models.ForeignKey(
        Project,
        verbose_name="Loyiha",
        related_name="tasks",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        related_name="tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        "Muhimlik", max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    due_date = models.DateField("Muddat", null=True, blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Vazifa"
        verbose_name_plural = "Vazifalar"
        ordering = ["status", "due_date"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return self.status != self.Status.DONE and bool(self.due_date) and self.due_date < timezone.localdate()
