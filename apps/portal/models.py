from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.core.models import TimeStamped

from .catalog import BY_SLUG, TOTAL_LEVELS
from .levels import XP_PER_STAR


class StudentQuerySet(models.QuerySet):
    def with_stats(self):
        return self.select_related("user", "group").annotate(
            stars=Coalesce(Sum("progress__stars"), 0),
            solved=Count("progress", filter=Q(progress__stars__gt=0)),
        )


class Group(TimeStamped):
    name = models.CharField("Nomi", max_length=100)
    schedule = models.CharField("Dars vaqti", max_length=100, blank=True, help_text="Masalan: Du, Cho, Ju · 16:00")
    monthly_fee = models.DecimalField("Oylik to'lov (so'm)", max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        ordering = ["-is_active", "name"]

    def __str__(self):
        return self.name


class Student(TimeStamped):
    """Bu yozuvi bor foydalanuvchi faqat /portal/ ni ko'radi. Yozuv foydalanuvchi bilan birga o'chiriladi."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student")
    group = models.ForeignKey(
        Group, verbose_name="Guruh", null=True, blank=True, on_delete=models.SET_NULL, related_name="students"
    )
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
        return round(self.solved * 100 / TOTAL_LEVELS)


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
        level = BY_SLUG.get(self.level)
        return level.title if level else self.level


class Post(TimeStamped):
    """O'qituvchidan o'quvchilarga: e'lon, dars materiali yoki uy vazifasi."""

    class Kind(models.TextChoices):
        NEWS = "news", "E'lon"
        MATERIAL = "material", "Material"
        HOMEWORK = "homework", "Uy vazifasi"

    title = models.CharField("Sarlavha", max_length=200)
    kind = models.CharField("Turi", max_length=20, choices=Kind.choices, default=Kind.NEWS)
    # Guruh o'chsa yozuv ham o'chadi: SET_NULL uni hamma o'quvchiga ochib yuborardi
    group = models.ForeignKey(
        Group,
        verbose_name="Guruh",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="posts",
        help_text="Bo'sh qolsa, hamma o'quvchiga ko'rinadi",
    )
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


class Submission(TimeStamped):
    """O'quvchining uy vazifasi javobi. Qaytarilgan javob qayta topshiriladi, qabul qilingani yopiladi."""

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Tekshirilmoqda"
        ACCEPTED = "accepted", "Qabul qilindi"
        RETURNED = "returned", "Qaytarildi"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="submissions")
    text = models.TextField("Javob", max_length=5000, blank=True)
    url = models.URLField("Havola", blank=True)
    status = models.CharField("Holati", max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    grade = models.PositiveSmallIntegerField(
        "Baho", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback = models.TextField("O'qituvchi izohi", blank=True)
    reviewed_at = models.DateTimeField("Tekshirilgan", null=True, blank=True)

    class Meta:
        verbose_name = "Uy vazifasi javobi"
        verbose_name_plural = "Uy vazifasi javoblari"
        ordering = ["-updated_at"]
        constraints = [models.UniqueConstraint(fields=["post", "student"], name="portal_submission_unique")]

    def __str__(self):
        return f"{self.student}: {self.post}"

    @property
    def badge(self) -> str:
        return {"submitted": "badge-brand", "accepted": "badge-success", "returned": "badge-warning"}[self.status]


class Lesson(TimeStamped):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="lessons")
    date = models.DateField("Sana")
    topic = models.CharField("Mavzu", max_length=200, blank=True)

    class Meta:
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["group", "date"], name="portal_lesson_unique")]

    def __str__(self):
        return f"{self.group} {self.date}"


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Keldi"
        LATE = "late", "Kechikdi"
        ABSENT = "absent", "Kelmadi"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="marks")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="attendance")
    status = models.CharField("Holati", max_length=10, choices=Status.choices, default=Status.PRESENT)

    class Meta:
        verbose_name = "Davomat"
        verbose_name_plural = "Davomat"
        constraints = [models.UniqueConstraint(fields=["lesson", "student"], name="portal_attendance_unique")]

    def __str__(self):
        return f"{self.student}: {self.get_status_display()}"


class Payment(models.Model):
    """O'quv to'lovi. Summa bu yerda saqlanmaydi: u moliyadagi kirim yozuvining o'zi.

    Kirim-chiqimda summa tahrirlansa shu yerda ham o'zgaradi, kirim o'chirilsa to'lov ham o'chadi. O'quvchi
    o'chirilganda kirim qoladi: pul haqiqatan olingan.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    month = models.DateField("Oy")
    transaction = models.OneToOneField("finance.Transaction", on_delete=models.CASCADE, related_name="tuition")

    class Meta:
        verbose_name = "O'quv to'lovi"
        verbose_name_plural = "O'quv to'lovlari"
        ordering = ["-month"]

    def __str__(self):
        return f"{self.student}: {self.month:%Y-%m}"
