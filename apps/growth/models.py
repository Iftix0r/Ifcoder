from datetime import timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TONE_CHOICES, TimeStamped


class Goal(TimeStamped):
    class Area(models.TextChoices):
        CAREER = "career", "Karyera"
        BUSINESS = "business", "Biznes"
        LEARNING = "learning", "O'rganish"
        HEALTH = "health", "Sog'liq"
        FINANCE = "finance", "Moliya"
        PERSONAL = "personal", "Shaxsiy"

    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        DONE = "done", "Erishildi"
        PAUSED = "paused", "To'xtatilgan"
        DROPPED = "dropped", "Voz kechildi"

    AREA_STYLE = {
        "career": ("briefcase", "tone-brand"),
        "business": ("rocket", "tone-violet"),
        "learning": ("graduation-cap", "tone-cyan"),
        "health": ("heart-pulse", "tone-rose"),
        "finance": ("piggy-bank", "tone-emerald"),
        "personal": ("sparkles", "tone-amber"),
    }

    title = models.CharField("Maqsad", max_length=200)
    why = models.TextField("Nega bu muhim?", blank=True)
    area = models.CharField("Soha", max_length=10, choices=Area.choices, default=Area.CAREER)
    status = models.CharField("Holati", max_length=8, choices=Status.choices, default=Status.ACTIVE)
    target_date = models.DateField("Muddat", null=True, blank=True)
    manual_progress = models.PositiveSmallIntegerField(
        "Progress (%)",
        default=0,
        validators=[MaxValueValidator(100)],
        help_text="Bosqichlar bo'lmasa ishlatiladi",
    )

    class Meta:
        ordering = ["status", "target_date", "-created_at"]
        verbose_name = "Maqsad"
        verbose_name_plural = "Maqsadlar"

    def __str__(self):
        return self.title

    @property
    def progress(self):
        if self.status == self.Status.DONE:
            return 100
        steps = list(self.milestones.all())
        if steps:
            return round(sum(s.done for s in steps) * 100 / len(steps))
        return self.manual_progress

    @property
    def area_icon(self):
        return self.AREA_STYLE[self.area][0]

    @property
    def area_tone(self):
        return self.AREA_STYLE[self.area][1]


class Milestone(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField("Bosqich", max_length=200)
    done = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return self.title


class Habit(TimeStamped):
    title = models.CharField("Odat", max_length=120)
    emoji = models.CharField("Emoji", max_length=8, default="✅")
    tone = models.CharField("Rang", max_length=10, choices=TONE_CHOICES, default="brand")
    cue = models.CharField("Qachon / qayerda", max_length=150, blank=True, help_text="Masalan: ertalab, kofedan keyin")
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        ordering = ["-is_active", "created_at"]
        verbose_name = "Odat"
        verbose_name_plural = "Odatlar"

    def __str__(self):
        return self.title

    def done_dates(self):
        if not hasattr(self, "_dates"):
            self._dates = set(self.logs.values_list("date", flat=True))
        return self._dates

    @property
    def done_today(self):
        return timezone.localdate() in self.done_dates()

    @property
    def streak(self):
        dates = self.done_dates()
        day = timezone.localdate()
        if day not in dates:
            day -= timedelta(days=1)
        n = 0
        while day in dates:
            n += 1
            day -= timedelta(days=1)
        return n

    def rate(self, days=30):
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)
        return round(sum(1 for d in self.done_dates() if start <= d <= today) * 100 / days)


class HabitLog(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField(default=timezone.localdate)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["habit", "date"], name="uniq_habit_day")]

    def __str__(self):
        return f"{self.habit} — {self.date}"


class LearningItem(TimeStamped):
    class Kind(models.TextChoices):
        BOOK = "book", "Kitob"
        COURSE = "course", "Kurs"
        SKILL = "skill", "Ko'nikma / texnologiya"
        ARTICLE = "article", "Maqola / video"

    class Status(models.TextChoices):
        PLANNED = "planned", "Rejada"
        ACTIVE = "active", "O'rganilmoqda"
        DONE = "done", "Tugatildi"
        DROPPED = "dropped", "Tashlandi"

    KIND_ICON = {"book": "book-open", "course": "monitor-play", "skill": "code-xml", "article": "newspaper"}

    title = models.CharField("Nomi", max_length=200)
    kind = models.CharField("Turi", max_length=8, choices=Kind.choices, default=Kind.COURSE)
    author = models.CharField("Muallif / platforma", max_length=150, blank=True)
    url = models.URLField("Havola", blank=True)
    status = models.CharField("Holati", max_length=8, choices=Status.choices, default=Status.PLANNED)
    progress = models.PositiveSmallIntegerField("Progress (%)", default=0, validators=[MaxValueValidator(100)])
    rating = models.PositiveSmallIntegerField(
        "Baho (1-5)", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    takeaways = models.TextField("Asosiy xulosalar", blank=True)
    finished_on = models.DateField("Tugatilgan sana", null=True, blank=True)

    class Meta:
        ordering = ["status", "-updated_at"]
        verbose_name = "O'rganish"
        verbose_name_plural = "O'rganish"

    def __str__(self):
        return self.title

    @property
    def icon(self):
        return self.KIND_ICON[self.kind]


class JournalEntry(TimeStamped):
    MOODS = {1: "😞", 2: "😕", 3: "😐", 4: "🙂", 5: "🤩"}

    date = models.DateField("Sana", default=timezone.localdate, unique=True)
    mood = models.PositiveSmallIntegerField("Kayfiyat", default=4, choices=[(k, f"{v} {k}") for k, v in MOODS.items()])
    energy = models.PositiveSmallIntegerField("Energiya", default=3, choices=[(i, str(i)) for i in range(1, 6)])
    wins = models.TextField("Bugungi yutuqlar", blank=True)
    lessons = models.TextField("Nimani o'rgandim", blank=True)
    tomorrow = models.TextField("Ertangi eng muhim ish", blank=True)
    notes = models.TextField("Erkin fikrlar", blank=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Kundalik"
        verbose_name_plural = "Kundalik"

    def __str__(self):
        return str(self.date)

    @property
    def mood_emoji(self):
        return self.MOODS.get(self.mood, "🙂")
