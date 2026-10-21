from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        abstract = True


class Currency(models.TextChoices):
    UZS = "UZS", "so'm"
    USD = "USD", "$"


TONE_CHOICES = [
    ("brand", "Indigo"),
    ("violet", "Binafsha"),
    ("cyan", "Moviy"),
    ("emerald", "Yashil"),
    ("amber", "Sariq"),
    ("rose", "Qizil"),
]

# Tailwind klasslari to'liq yozilgan — CSS build ularni shu fayldan topadi.
TONE_DOT = {
    "brand": "bg-brand-500",
    "violet": "bg-violet-500",
    "cyan": "bg-cyan-500",
    "emerald": "bg-emerald-500",
    "amber": "bg-amber-500",
    "rose": "bg-rose-500",
    "neutral": "bg-ink-3",
}
