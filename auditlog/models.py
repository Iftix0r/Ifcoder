from django.contrib.auth.models import User
from django.db import models


class AuditLog(models.Model):
    """
    Tizimda kim qachon nima qilganligini kuzatuvchi audit jurnali.
    Barcha muhim harakat (create, update, delete, login, status_change) bu modelga yoziladi.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Yaratildi"
        UPDATE = "update", "Yangilandi"
        DELETE = "delete", "O'chirildi"
        STATUS = "status", "Holat o'zgardi"
        LOGIN = "login", "Tizimga kirdi"
        LOGOUT = "logout", "Tizimdan chiqdi"
        EXPORT = "export", "Eksport qilindi"
        UPLOAD = "upload", "Fayl yuklandi"
        OTHER = "other", "Boshqa"

    user = models.ForeignKey(
        User,
        verbose_name="Foydalanuvchi",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField("Harakat", max_length=20, choices=Action.choices)
    model_name = models.CharField("Model", max_length=100, blank=True)
    object_id = models.PositiveIntegerField("Obyekt ID", null=True, blank=True)
    object_repr = models.CharField("Obyekt", max_length=255, blank=True)
    message = models.TextField("Xabar", blank=True)
    ip_address = models.GenericIPAddressField("IP Manzil", null=True, blank=True)
    user_agent = models.CharField("User-Agent", max_length=512, blank=True)
    timestamp = models.DateTimeField("Vaqt", auto_now_add=True)

    class Meta:
        verbose_name = "Audit Yozuvi"
        verbose_name_plural = "Audit Jurnali"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.object_repr} [{self.timestamp:%d.%m.%Y %H:%M}]"


def log_action(
    user=None,
    action=AuditLog.Action.OTHER,
    model_name="",
    object_id=None,
    object_repr="",
    message="",
    request=None,
):
    """Audit voqeasini yozuvchi yordamchi funksiya."""
    ip = None
    ua = ""
    if request:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = x_forwarded.split(",")[0] if x_forwarded else request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:512]
        if user is None and request.user.is_authenticated:
            user = request.user

    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=str(object_repr)[:255],
        message=str(message),
        ip_address=ip,
        user_agent=ua,
    )
