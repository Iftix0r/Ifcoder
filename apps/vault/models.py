from django.conf import settings
from django.db import models

from apps.core.models import TimeStamped

from .crypto import decrypt, encrypt


class Secret(TimeStamped):
    class Kind(models.TextChoices):
        API_KEY = "api_key", "API kalit"
        PASSWORD = "password", "Login / parol"
        TOKEN = "token", "Bot token"
        SSH = "ssh", "SSH / server"
        OTHER = "other", "Boshqa"

    KIND_ICON = {"api_key": "key-round", "password": "lock-keyhole", "token": "bot", "ssh": "terminal", "other": "shield"}

    name = models.CharField("Nomi", max_length=150)
    kind = models.CharField("Turi", max_length=10, choices=Kind.choices, default=Kind.API_KEY)
    login = models.CharField("Login / username", max_length=200, blank=True)
    url = models.URLField("Havola", blank=True)
    encrypted_value = models.TextField(editable=False)
    notes = models.TextField("Izoh", blank=True)
    project = models.ForeignKey(
        "projects.Project", verbose_name="Loyiha", null=True, blank=True, on_delete=models.SET_NULL, related_name="secrets"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Maxfiy kalit"
        verbose_name_plural = "Maxfiy kalitlar"

    def __str__(self):
        return self.name

    @property
    def icon(self):
        return self.KIND_ICON[self.kind]

    @property
    def value(self):
        return decrypt(self.encrypted_value)

    @value.setter
    def value(self, raw):
        self.encrypted_value = encrypt(raw)


class TOTPDevice(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totp")
    encrypted_secret = models.TextField(editable=False)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "2FA qurilma"
        verbose_name_plural = "2FA qurilmalar"

    @property
    def secret(self):
        return decrypt(self.encrypted_secret)


class BackupCode(models.Model):
    device = models.ForeignKey(TOTPDevice, on_delete=models.CASCADE, related_name="backup_codes")
    code_hash = models.CharField(max_length=200, editable=False)
    used_at = models.DateTimeField(null=True, blank=True)
