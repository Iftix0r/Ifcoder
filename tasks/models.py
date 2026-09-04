from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

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
    assigned_to = models.ForeignKey(
        User,
        verbose_name="Mas'ul",
        related_name="assigned_tasks",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    estimated_hours = models.DecimalField(
        "Taxminiy soat", max_digits=7, decimal_places=2, default=0, blank=True
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


class TimeEntry(models.Model):
    task = models.ForeignKey(
        Task, verbose_name="Vazifa", related_name="time_entries", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, verbose_name="Dasturchi", related_name="time_entries", on_delete=models.PROTECT
    )
    date = models.DateField("Sana", default=timezone.localdate)
    hours = models.DecimalField("Ishlangan soat", max_digits=7, decimal_places=2, default=0)
    note = models.CharField("Izoh", max_length=255, blank=True)
    # Live timer support
    started_at = models.DateTimeField("Boshlangan vaqt", null=True, blank=True)
    is_running = models.BooleanField("Ishlayaptimi?", default=False)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Ish vaqti"
        verbose_name_plural = "Ish vaqtlari"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.task} — {self.hours} soat"

    def stop_timer(self):
        """Timerni to'xtatadi va ishlangan soatni hisoblaydi."""
        if self.is_running and self.started_at:
            elapsed = timezone.now() - self.started_at
            self.hours += round(elapsed.total_seconds() / 3600, 2)
            self.is_running = False
            self.started_at = None
            self.save(update_fields=["hours", "is_running", "started_at"])

