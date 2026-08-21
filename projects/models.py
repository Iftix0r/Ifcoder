from django.db import models
from django.db.models import Sum

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
    contract_value = models.DecimalField(
        "Kelishilgan summa", max_digits=12, decimal_places=2, default=0
    )
    hourly_rate = models.DecimalField(
        "Soatlik stavka", max_digits=10, decimal_places=2, default=0
    )
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Loyiha"
        verbose_name_plural = "Loyihalar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def completed_task_count(self):
        return self.tasks.filter(status="done").count()

    @property
    def progress_percent(self):
        if not self.task_count:
            return 0
        return round(self.completed_task_count * 100 / self.task_count)

    @property
    def total_income(self):
        return self.incomes.aggregate(total=Sum("amount"))["total"] or 0

    @property
    def total_expenses(self):
        return self.expenses.aggregate(total=Sum("amount"))["total"] or 0

    @property
    def tracked_hours(self):
        return self.tasks.aggregate(total=Sum("time_entries__hours"))["total"] or 0

    @property
    def labor_cost(self):
        return self.tracked_hours * self.hourly_rate

    @property
    def profit(self):
        return self.total_income - self.total_expenses - self.labor_cost
