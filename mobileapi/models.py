from django.contrib.auth.models import User
from django.db import models


class DeviceToken(models.Model):
    """Operator telefonining Firebase push (FCM) tokeni."""

    user = models.ForeignKey(
        User,
        verbose_name="Operator",
        related_name="device_tokens",
        on_delete=models.CASCADE,
    )
    fcm_token = models.CharField("FCM token", max_length=255, unique=True)
    device_id = models.CharField("Qurilma ID", max_length=100, blank=True)
    updated_at = models.DateTimeField("Yangilangan sana", auto_now=True)

    class Meta:
        verbose_name = "Qurilma tokeni"
        verbose_name_plural = "Qurilma tokenlari"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.device_id or self.fcm_token[:12]}"


class LocationPing(models.Model):
    """Operator ilovasi tomonidan yuborilgan bitta joylashuv nuqtasi."""

    user = models.ForeignKey(
        User,
        verbose_name="Operator",
        related_name="location_pings",
        on_delete=models.CASCADE,
    )
    latitude = models.DecimalField("Kenglik", max_digits=9, decimal_places=6)
    longitude = models.DecimalField("Uzunlik", max_digits=9, decimal_places=6)
    accuracy = models.FloatField("Aniqlik (metr)", null=True, blank=True)
    recorded_at = models.DateTimeField("Qurilmada qayd etilgan vaqt")
    created_at = models.DateTimeField("Serverga kelgan vaqt", auto_now_add=True)

    class Meta:
        verbose_name = "Joylashuv"
        verbose_name_plural = "Joylashuv tarixi"
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["user", "-recorded_at"])]

    def __str__(self):
        return f"{self.user} @ {self.recorded_at:%Y-%m-%d %H:%M}"
