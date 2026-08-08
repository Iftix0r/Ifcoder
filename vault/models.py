from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from .crypto import decrypt_value, encrypt_value


class APIKey(models.Model):
    name = models.CharField("Nomi", max_length=150)
    encrypted_value = models.TextField("Shifrlangan qiymat", editable=False)
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan sana", auto_now=True)

    class Meta:
        verbose_name = "API kalit"
        verbose_name_plural = "API kalitlar"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def set_value(self, plain: str) -> None:
        self.encrypted_value = encrypt_value(plain)

    def get_value(self) -> str:
        return decrypt_value(self.encrypted_value)

    @property
    def masked_value(self) -> str:
        try:
            plain = self.get_value()
        except Exception:
            return "••••••••"
        if len(plain) <= 4:
            return "•" * len(plain)
        return "•" * (len(plain) - 4) + plain[-4:]


class TOTPDevice(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Foydalanuvchi",
        related_name="totp_device",
        on_delete=models.CASCADE,
    )
    encrypted_secret = models.TextField("Shifrlangan maxfiy kod", editable=False)
    confirmed = models.BooleanField("Tasdiqlangan", default=False)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "2FA qurilma"
        verbose_name_plural = "2FA qurilmalar"

    def __str__(self):
        return f"2FA — {self.user}"

    def set_secret(self, plain: str) -> None:
        self.encrypted_secret = encrypt_value(plain)

    def get_secret(self) -> str:
        return decrypt_value(self.encrypted_secret)


class BackupCode(models.Model):
    device = models.ForeignKey(
        TOTPDevice, verbose_name="Qurilma", related_name="backup_codes", on_delete=models.CASCADE
    )
    code_hash = models.CharField("Kod xesh", max_length=200, editable=False)
    used_at = models.DateTimeField("Ishlatilgan sana", null=True, blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Zaxira kod"
        verbose_name_plural = "Zaxira kodlar"

    def set_code(self, plain: str) -> None:
        self.code_hash = make_password(plain)

    def check_code(self, plain: str) -> bool:
        return self.used_at is None and check_password(plain, self.code_hash)

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
