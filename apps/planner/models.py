from django.db import models
from django.utils import timezone

from apps.core.models import TimeStamped


class Task(TimeStamped):
    class Status(models.TextChoices):
        TODO = "todo", "Rejada"
        DOING = "doing", "Jarayonda"
        DONE = "done", "Bajarildi"

    class Priority(models.IntegerChoices):
        LOW = 1, "Past"
        MEDIUM = 2, "O'rta"
        HIGH = 3, "Yuqori"
        URGENT = 4, "Shoshilinch"

    PRIORITY_STYLE = {1: "text-ink-3", 2: "text-cyan-500", 3: "text-amber-500", 4: "text-rose-500"}

    title = models.CharField("Vazifa", max_length=250)
    notes = models.TextField("Izoh", blank=True)
    status = models.CharField("Holati", max_length=6, choices=Status.choices, default=Status.TODO)
    priority = models.PositiveSmallIntegerField("Muhimlik", choices=Priority.choices, default=Priority.MEDIUM)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="Loyiha",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    contact = models.ForeignKey(
        "crm.Contact", verbose_name="Mijoz", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    planned_for = models.DateField("Qaysi kuni bajaraman", null=True, blank=True)
    due_date = models.DateField("Muddat (deadline)", null=True, blank=True)
    estimate = models.PositiveIntegerField("Taxminiy vaqt (daqiqa)", null=True, blank=True)
    position = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "-priority", "due_date", "-created_at"]
        verbose_name = "Vazifa"
        verbose_name_plural = "Vazifalar"

    def __str__(self):
        return self.title

    @property
    def is_done(self):
        return self.status == self.Status.DONE

    @property
    def priority_color(self):
        return self.PRIORITY_STYLE[self.priority]

    def set_status(self, status):
        self.status = status
        self.completed_at = timezone.now() if status == self.Status.DONE else None


class TimeEntry(models.Model):
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name="time_entries")
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="Loyiha",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="time_entries",
    )
    note = models.CharField("Izoh", max_length=250, blank=True)
    started_at = models.DateTimeField("Boshlandi", default=timezone.now)
    ended_at = models.DateTimeField("Tugadi", null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Vaqt yozuvi"
        verbose_name_plural = "Vaqt yozuvlari"

    def __str__(self):
        return self.label

    @property
    def is_running(self):
        return self.ended_at is None

    @property
    def minutes(self):
        end = self.ended_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds() // 60))

    @property
    def hours(self):
        return self.minutes / 60

    @property
    def label(self):
        return self.task.title if self.task else (self.note or "Vazifasiz ish")
