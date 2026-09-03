from django.contrib.auth.models import User
from django.db import models


class Client(models.Model):
    user = models.OneToOneField(
        User,
        verbose_name="Foydalanuvchi hisobi",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_profile",
    )
    class LeadStatus(models.TextChoices):
        NEW = "new", "Yangi lead"
        CONTACTED = "contacted", "Aloqa qilingan"
        PROPOSAL = "proposal", "Taklif yuborilgan"
        ACTIVE = "active", "Faol mijoz"
        LOST = "lost", "Yo'qotilgan"

    name = models.CharField("Ism / kompaniya", max_length=200)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    telegram = models.CharField("Telegram username", max_length=100, blank=True)
    telegram_id = models.CharField("Telegram User ID", max_length=50, blank=True)
    avatar = models.ImageField("Rasm / Avatar", upload_to="clients/avatars/", blank=True, null=True)
    email = models.EmailField("Email", blank=True)
    notes = models.TextField("Izoh", blank=True)
    lead_status = models.CharField(
        "Lead holati", max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW
    )
    follow_up_date = models.DateField("Keyingi aloqa sanasi", null=True, blank=True)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
