from django.contrib.auth.models import User
from django.db import models

from clients.models import Client
from projects.models import Project


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Ochiq"
        IN_PROGRESS = "in_progress", "Ko'rib chiqilmoqda"
        ANSWERED = "answered", "Javob berildi"
        CLOSED = "closed", "Yopildi"

    class Priority(models.TextChoices):
        LOW = "low", "Past"
        MEDIUM = "medium", "O'rta"
        HIGH = "high", "Yuqori"
        URGENT = "urgent", "Shoshilinch"

    title = models.CharField("Mavzu", max_length=255)
    body = models.TextField("Muammo tavsifi")
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.OPEN
    )
    priority = models.CharField(
        "Muhimlik darajasi", max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        on_delete=models.CASCADE,
        related_name="tickets",
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        verbose_name="Loyiha",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    created_by = models.ForeignKey(
        User,
        verbose_name="Yaratuvchi",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tickets",
    )
    created_at = models.DateTimeField("Yaratilgan", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan", auto_now=True)

    class Meta:
        verbose_name = "Tiket"
        verbose_name_plural = "Tiketlar"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} — {self.title}"

    @property
    def reply_count(self):
        return self.replies.count()

    @property
    def last_reply(self):
        return self.replies.order_by("-created_at").first()

    @property
    def is_open(self):
        return self.status in (self.Status.OPEN, self.Status.IN_PROGRESS)


class TicketReply(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        verbose_name="Tiket",
        on_delete=models.CASCADE,
        related_name="replies",
    )
    author = models.ForeignKey(
        User,
        verbose_name="Muallif",
        on_delete=models.SET_NULL,
        null=True,
    )
    body = models.TextField("Javob matni")
    is_staff = models.BooleanField("Admin javobiми", default=False)
    created_at = models.DateTimeField("Yuborilgan", auto_now_add=True)

    class Meta:
        verbose_name = "Tiket Javobi"
        verbose_name_plural = "Tiket Javoblari"
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply #{self.pk} — Tiket #{self.ticket_id}"


def ticket_attachment_path(instance, filename):
    return f"tickets/{instance.ticket_id}/{filename}"


class TicketAttachment(models.Model):
    """Tiket yoki tiket javobiga biriktirilgan fayl."""
    ticket = models.ForeignKey(
        Ticket,
        verbose_name="Tiket",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    reply = models.ForeignKey(
        TicketReply,
        verbose_name="Javob",
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    file = models.FileField("Fayl", upload_to=ticket_attachment_path)
    filename = models.CharField("Fayl nomi", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        verbose_name="Yuklagan",
        on_delete=models.SET_NULL,
        null=True,
    )
    uploaded_at = models.DateTimeField("Yuklangan vaqt", auto_now_add=True)

    class Meta:
        verbose_name = "Tiket Fayli"
        verbose_name_plural = "Tiket Fayllari"
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.filename or str(self.file)

    def save(self, *args, **kwargs):
        if not self.filename:
            import os
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    @property
    def extension(self):
        import os
        return os.path.splitext(self.filename or "")[1].lower().lstrip(".")

    @property
    def is_image(self):
        return self.extension in ("jpg", "jpeg", "png", "gif", "webp", "svg")

