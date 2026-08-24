from django.db import models
from django.utils import timezone


class Goal(models.Model):
    class Period(models.TextChoices):
        DAILY = "daily", "Kunlik"
        WEEKLY = "weekly", "Haftalik"
        MONTHLY = "monthly", "Oylik"
        QUARTERLY = "quarterly", "Choraklik"
        YEARLY = "yearly", "Yillik"
        CUSTOM = "custom", "Boshqa"

    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        COMPLETED = "completed", "Bajarildi"
        FAILED = "failed", "Bajarilmadi"
        PAUSED = "paused", "To'xtatilgan"

    class Category(models.TextChoices):
        BUSINESS = "business", "Biznes"
        PERSONAL = "personal", "Shaxsiy"
        LEARNING = "learning", "O'rganish"
        HEALTH = "health", "Sog'liq"
        FINANCE = "finance", "Moliya"
        OTHER = "other", "Boshqa"

    title = models.CharField("Maqsad", max_length=200)
    description = models.TextField("Tavsif", blank=True)

    period = models.CharField(
        "Davr", max_length=12, choices=Period.choices, default=Period.MONTHLY
    )
    category = models.CharField(
        "Kategoriya", max_length=12, choices=Category.choices, default=Category.BUSINESS
    )
    status = models.CharField(
        "Holati", max_length=12, choices=Status.choices, default=Status.ACTIVE
    )

    start_date = models.DateField("Boshlanish sanasi", default=timezone.localdate)
    deadline = models.DateField("Deadline", null=True, blank=True)

    # 0–100 foiz — qo'lda ham o'zgartirish mumkin
    progress = models.PositiveSmallIntegerField(
        "Progress (%)", default=0,
        help_text="0 dan 100 gacha. Vazifalar asosida avtomatik hisoblanadi."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maqsad"
        verbose_name_plural = "Maqsadlar"
        ordering = ["status", "deadline"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return (
            self.status == self.Status.ACTIVE
            and self.deadline is not None
            and self.deadline < timezone.localdate()
        )

    @property
    def days_left(self):
        if not self.deadline:
            return None
        delta = (self.deadline - timezone.localdate()).days
        return delta

    def recalc_progress(self):
        """GoalTask lardan progress ni qayta hisoblaydi va saqlaydi."""
        tasks = self.goal_tasks.all()
        total = tasks.count()
        if total == 0:
            return
        done = tasks.filter(status=GoalTask.Status.DONE).count()
        self.progress = int((done / total) * 100)
        self.save(update_fields=["progress"])


class GoalTask(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "Bajarilmagan"
        IN_PROGRESS = "in_progress", "Jarayonda"
        DONE = "done", "Bajarildi"
        SKIPPED = "skipped", "O'tkazib yuborildi"

    class Priority(models.TextChoices):
        LOW = "low", "Past"
        MEDIUM = "medium", "O'rta"
        HIGH = "high", "Yuqori"

    goal = models.ForeignKey(
        Goal,
        verbose_name="Maqsad",
        related_name="goal_tasks",
        on_delete=models.CASCADE,
    )
    title = models.CharField("Vazifa", max_length=200)
    notes = models.TextField("Izoh", blank=True)

    status = models.CharField(
        "Holati", max_length=12, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        "Muhimlik", max_length=8, choices=Priority.choices, default=Priority.MEDIUM
    )

    due_date = models.DateField("Muddat", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Maqsad vazifasi"
        verbose_name_plural = "Maqsad vazifalari"
        ordering = ["status", "due_date", "priority"]

    def __str__(self):
        return f"{self.goal} → {self.title}"

    @property
    def is_overdue(self):
        return (
            self.status not in (self.Status.DONE, self.Status.SKIPPED)
            and self.due_date is not None
            and self.due_date < timezone.localdate()
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.goal.recalc_progress()
