from django.conf import settings
from django.db import models
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.core.models import TimeStamped

from .levels import ALL_LEVELS, LEVELS, XP_PER_STAR


class StudentQuerySet(models.QuerySet):
    def with_stats(self):
        return self.select_related("user").annotate(
            stars=Coalesce(Sum("progress__stars"), 0),
            solved=Count("progress", filter=Q(progress__stars__gt=0)),
        )


class Student(TimeStamped):
    """Bu yozuvi bor foydalanuvchi faqat /portal/ ni ko'radi. Yozuv foydalanuvchi bilan birga o'chiriladi."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student")
    phone = models.CharField("Telefon", max_length=30, blank=True)
    note = models.TextField("O'qituvchi izohi", blank=True)

    objects = StudentQuerySet.as_manager()

    class Meta:
        verbose_name = "O'quvchi"
        verbose_name_plural = "O'quvchilar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        return self.user.get_full_name() or self.user.get_username()

    @property
    def public_name(self) -> str:
        """Reytingda boshqa bolalarga familiya to'liq ko'rinmaydi."""
        first, last = self.user.first_name, self.user.last_name
        if not first:
            return self.user.get_username()
        return f"{first} {last[0]}." if last else first

    @property
    def xp(self) -> int:
        return self.stars * XP_PER_STAR

    @property
    def percent(self) -> int:
        return round(self.solved * 100 / len(ALL_LEVELS))


class LevelProgress(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="progress")
    level = models.CharField("Bosqich", max_length=50)
    attempts = models.PositiveIntegerField("Urinishlar", default=0)
    stars = models.PositiveSmallIntegerField("Yulduzlar", default=0)
    code = models.TextField("Oxirgi kod", blank=True)
    best_code = models.TextField("Eng yaxshi kod", blank=True)
    solved_at = models.DateTimeField("Yechilgan", null=True, blank=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        verbose_name = "Bosqich natijasi"
        verbose_name_plural = "Bosqich natijalari"
        constraints = [models.UniqueConstraint(fields=["student", "level"], name="portal_progress_unique")]

    def __str__(self):
        return f"{self.student}: {self.level}"

    @property
    def level_title(self) -> str:
        level = LEVELS.get(self.level)
        return level.title if level else self.level


class Post(TimeStamped):
    """O'qituvchidan o'quvchilarga: e'lon, dars materiali yoki uy vazifasi."""

    class Kind(models.TextChoices):
        NEWS = "news", "E'lon"
        MATERIAL = "material", "Material"
        HOMEWORK = "homework", "Uy vazifasi"

    title = models.CharField("Sarlavha", max_length=200)
    kind = models.CharField("Turi", max_length=20, choices=Kind.choices, default=Kind.NEWS)
    body = models.TextField("Matn", blank=True)
    url = models.URLField("Havola", blank=True)
    due_date = models.DateField("Muddat", null=True, blank=True)
    pinned = models.BooleanField("Yuqorida turadi", default=False)
    is_published = models.BooleanField("O'quvchilarga ko'rinadi", default=True)

    class Meta:
        verbose_name = "E'lon yoki material"
        verbose_name_plural = "E'lon va materiallar"
        ordering = ["-pinned", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def icon(self) -> str:
        return {"news": "megaphone", "material": "book-open", "homework": "pencil-ruler"}[self.kind]

    @property
    def tone(self) -> str:
        return {"news": "tone-brand", "material": "tone-cyan", "homework": "tone-amber"}[self.kind]
