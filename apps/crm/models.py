from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Currency, TimeStamped


class Contact(TimeStamped):
    class Kind(models.TextChoices):
        PERSON = "person", "Shaxs"
        COMPANY = "company", "Kompaniya"

    class Status(models.TextChoices):
        LEAD = "lead", "Potentsial"
        ACTIVE = "active", "Faol mijoz"
        PARTNER = "partner", "Hamkor"
        PAST = "past", "Sobiq mijoz"

    class Source(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        INSTAGRAM = "instagram", "Instagram"
        WEBSITE = "website", "Sayt"
        REFERRAL = "referral", "Tavsiya"
        FREELANCE = "freelance", "Frilans platforma"
        CALL = "call", "Qo'ng'iroq"
        OTHER = "other", "Boshqa"

    name = models.CharField("Ism yoki nomi", max_length=200)
    kind = models.CharField("Turi", max_length=10, choices=Kind.choices, default=Kind.PERSON)
    company = models.CharField("Kompaniya", max_length=200, blank=True)
    position = models.CharField("Lavozimi", max_length=120, blank=True)
    phone = models.CharField("Telefon", max_length=40, blank=True)
    email = models.EmailField("Email", blank=True)
    telegram = models.CharField("Telegram", max_length=100, blank=True, help_text="@username")
    website = models.URLField("Sayt", blank=True)
    status = models.CharField("Holati", max_length=10, choices=Status.choices, default=Status.LEAD)
    source = models.CharField("Manba", max_length=12, choices=Source.choices, default=Source.TELEGRAM)
    tags = models.CharField("Teglar", max_length=200, blank=True, help_text="Vergul bilan: dizayn, bot, shop")
    next_contact = models.DateField("Keyingi aloqa", null=True, blank=True)
    notes = models.TextField("Izoh", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("contact_detail", args=[self.pk])

    @property
    def telegram_url(self):
        handle = self.telegram.strip().lstrip("@")
        return f"https://t.me/{handle}" if handle else ""

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def status_badge(self):
        return {
            "lead": "badge-warning",
            "active": "badge-success",
            "partner": "badge-brand",
            "past": "badge-neutral",
        }[self.status]


class Deal(TimeStamped):
    class Stage(models.TextChoices):
        NEW = "new", "Yangi"
        CONTACTED = "contacted", "Aloqa o'rnatildi"
        PROPOSAL = "proposal", "Taklif yuborildi"
        NEGOTIATION = "negotiation", "Muzokara"
        WON = "won", "Yutildi"
        LOST = "lost", "Yo'qotildi"

    OPEN_STAGES = (Stage.NEW, Stage.CONTACTED, Stage.PROPOSAL, Stage.NEGOTIATION)

    title = models.CharField("Bitim nomi", max_length=200)
    contact = models.ForeignKey(Contact, verbose_name="Mijoz", on_delete=models.CASCADE, related_name="deals")
    value = models.DecimalField("Summa", max_digits=14, decimal_places=2, default=0)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    stage = models.CharField("Bosqich", max_length=12, choices=Stage.choices, default=Stage.NEW)
    position = models.PositiveIntegerField(default=0)
    expected_close = models.DateField("Kutilayotgan sana", null=True, blank=True)
    project = models.ForeignKey(
        "projects.Project", verbose_name="Loyiha", null=True, blank=True, on_delete=models.SET_NULL, related_name="deals"
    )
    note = models.TextField("Izoh", blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "-created_at"]
        verbose_name = "Bitim"
        verbose_name_plural = "Bitimlar"

    def __str__(self):
        return self.title

    @property
    def is_open(self):
        return self.stage in self.OPEN_STAGES

    def set_stage(self, stage):
        self.stage = stage
        self.closed_at = None if stage in self.OPEN_STAGES else (self.closed_at or timezone.now())


class Activity(models.Model):
    class Kind(models.TextChoices):
        NOTE = "note", "Izoh"
        CALL = "call", "Qo'ng'iroq"
        MEETING = "meeting", "Uchrashuv"
        MESSAGE = "message", "Xabar"
        STAGE = "stage", "Bosqich"

    ICONS = {"note": "sticky-note", "call": "phone", "meeting": "calendar-clock", "message": "send", "stage": "git-commit-horizontal"}

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="activities")
    deal = models.ForeignKey(Deal, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    kind = models.CharField("Turi", max_length=10, choices=Kind.choices, default=Kind.NOTE)
    text = models.TextField("Matn")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def icon(self):
        return self.ICONS.get(self.kind, "circle-dot")
