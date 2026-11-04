"""Egasining Telegram akkaunti va shaxsiy suhbatlar nusxasi.

Telegram ulanishini faqat ``manage.py userbot`` jarayoni ushlab turadi. Panel u bilan shu jadvallar orqali gaplashadi:
kelgan xabarlar ``Message`` ga yoziladi, paneldan yuborilganlari ``Outbox`` navbatiga tushadi.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStamped
from apps.vault.crypto import decrypt, encrypt

HEARTBEAT_ALIVE = timedelta(seconds=90)


class Account(TimeStamped):
    """Yagona yozuv (pk=1): panel bitta egaga tegishli."""

    class Status(models.TextChoices):
        DISCONNECTED = "off", "Ulanmagan"
        CODE_SENT = "code", "Kod kutilmoqda"
        PASSWORD = "password", "2FA parol kutilmoqda"
        CONNECTED = "on", "Ulangan"

    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DISCONNECTED)
    api_id = models.PositiveIntegerField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    encrypted_api_hash = models.TextField(blank=True, editable=False)
    encrypted_session = models.TextField(blank=True, editable=False)
    encrypted_code_hash = models.TextField(blank=True, editable=False)

    tg_id = models.BigIntegerField(null=True, blank=True)
    tg_name = models.CharField(max_length=200, blank=True)
    tg_username = models.CharField(max_length=100, blank=True)

    commands_enabled = models.BooleanField("Saqlangan xabarlardagi buyruqlar", default=True)
    log_to_crm = models.BooleanField("Mijoz yozganda aloqalar tarixiga qo'shish", default=True)

    heartbeat_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    sync_requested = models.BooleanField(default=False)
    last_command_id = models.BigIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Telegram akkaunt"
        verbose_name_plural = "Telegram akkauntlar"

    def __str__(self):
        return self.tg_name or self.phone or "Telegram"

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    @property
    def api_hash(self):
        return decrypt(self.encrypted_api_hash) if self.encrypted_api_hash else ""

    @api_hash.setter
    def api_hash(self, raw):
        self.encrypted_api_hash = encrypt(raw) if raw else ""

    @property
    def session(self):
        return decrypt(self.encrypted_session) if self.encrypted_session else ""

    @session.setter
    def session(self, raw):
        self.encrypted_session = encrypt(raw) if raw else ""

    @property
    def code_hash(self):
        return decrypt(self.encrypted_code_hash) if self.encrypted_code_hash else ""

    @code_hash.setter
    def code_hash(self, raw):
        self.encrypted_code_hash = encrypt(raw) if raw else ""

    @property
    def is_connected(self):
        return self.status == self.Status.CONNECTED

    @property
    def runner_alive(self):
        return bool(self.heartbeat_at and timezone.now() - self.heartbeat_at < HEARTBEAT_ALIVE)


class Dialog(TimeStamped):
    """Shaxsiy suhbat. Guruh, kanal, bot va Telegram xizmat chatlari saqlanmaydi."""

    peer_id = models.BigIntegerField(unique=True)
    access_hash = models.BigIntegerField(default=0)
    name = models.CharField(max_length=200, blank=True)
    username = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.FileField(upload_to="telegram/avatars", blank=True)
    photo_id = models.BigIntegerField(default=0)  # Telegram'dagi joriy profil rasmi (0 — yo'q)
    avatar_photo_id = models.BigIntegerField(default=0)  # yuklab olingani; farq qilsa runner yangilaydi
    contact = models.ForeignKey(
        "crm.Contact", null=True, blank=True, on_delete=models.SET_NULL, related_name="telegram_dialogs"
    )
    unread = models.PositiveIntegerField(default=0)
    last_text = models.CharField(max_length=200, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = [models.F("last_message_at").desc(nulls_last=True)]
        verbose_name = "Telegram suhbat"
        verbose_name_plural = "Telegram suhbatlar"

    def __str__(self):
        return self.title

    @property
    def title(self):
        return self.name or (f"@{self.username}" if self.username else str(self.peer_id))


class Message(models.Model):
    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name="messages")
    tg_id = models.BigIntegerField()
    outgoing = models.BooleanField(default=False)
    text = models.TextField(blank=True)
    has_photo = models.BooleanField(default=False)  # runner rasmni alohida navbat bilan yuklaydi
    image = models.FileField(upload_to="telegram/photos", blank=True)
    date = models.DateTimeField()

    class Meta:
        ordering = ["-date", "-tg_id"]
        constraints = [models.UniqueConstraint(fields=["dialog", "tg_id"], name="userbot_message_unique")]

    def __str__(self):
        return self.text[:60]


class Outbox(TimeStamped):
    """Paneldan yuborilgan xabar. ``manage.py userbot`` olib ketadi."""

    class Status(models.TextChoices):
        PENDING = "pending", "Navbatda"
        SENDING = "sending", "Yuborilmoqda"
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Yuborilmadi"

    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name="outbox")
    text = models.TextField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.text[:60]
