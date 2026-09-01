from django.contrib.auth.models import User
from django.db import models

from clients.models import Client


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
