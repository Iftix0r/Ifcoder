"""Egasining Telegram akkaunti va shaxsiy suhbatlar nusxasi.

Telegram ulanishini faqat ``manage.py userbot`` jarayoni ushlab turadi. Panel u bilan shu jadvallar orqali gaplashadi:
kelgan xabarlar ``Message`` ga yoziladi, paneldan yuborilganlari ``Outbox`` navbatiga tushadi.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStamped
from apps.vault.crypto import decrypt, encrypt

from .voice import DEFAULT_SPEED, DEFAULT_VOICE, SPEEDS, VOICES

HEARTBEAT_ALIVE = timedelta(seconds=90)
# Faqat shu turlar brauzerda ochiladi. Qolgani (html, svg, ...) panel domenida ishga tushmasligi uchun yuklab olinadi.
INLINE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp4",
}
MEDIA_LABELS = {"[Rasm]", "[Ovozli xabar]", "[Video xabar]", "[Video]", "[Stiker]", "[Audio]", "[Fayl]", "[Media]"}


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
    voice = models.CharField("Ovoz", max_length=30, choices=VOICES, default=DEFAULT_VOICE)
    voice_speed = models.CharField("Tezlik", max_length=8, choices=SPEEDS, default=DEFAULT_SPEED)
    notify_changes = models.BooleanField("Xabar o'chirilsa yoki tahrirlansa, botdan xabar berish", default=True)

    heartbeat_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    sync_requested = models.BooleanField(default=False)
    last_command_id = models.BigIntegerField(default=0)
    reconciled_at = models.DateTimeField(null=True, blank=True)
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
    pinned = models.BooleanField(default=False)
    read_outbox_id = models.BigIntegerField(default=0)  # suhbatdosh shu id gacha o'qigan
    seen_kind = models.CharField(max_length=10, blank=True)  # online, offline, recently, week, month
    seen_at = models.DateTimeField(null=True, blank=True)  # online: tugash vaqti, offline: oxirgi ko'rilgan
    typing_until = models.DateTimeField(null=True, blank=True)
    contact = models.ForeignKey(
        "crm.Contact", null=True, blank=True, on_delete=models.SET_NULL, related_name="telegram_dialogs"
    )
    unread = models.PositiveIntegerField(default=0)
    last_text = models.CharField(max_length=200, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-pinned", models.F("last_message_at").desc(nulls_last=True)]
        verbose_name = "Telegram suhbat"
        verbose_name_plural = "Telegram suhbatlar"

    def __str__(self):
        return self.title

    @property
    def title(self):
        return self.name or (f"@{self.username}" if self.username else str(self.peer_id))

    @property
    def last_label(self):
        if not self.last_message_at:
            return ""
        local = timezone.localtime(self.last_message_at)
        return f"{local:%H:%M}" if local.date() == timezone.localdate() else f"{local:%d.%m.%y}"

    @property
    def is_online(self):
        return self.seen_kind == "online" and bool(self.seen_at and self.seen_at > timezone.now())

    @property
    def is_typing(self):
        return bool(self.typing_until and self.typing_until > timezone.now())

    @property
    def status_label(self):
        if self.is_typing:
            return "yozmoqda…"
        if self.is_online:
            return "online"
        if self.seen_at and self.seen_kind in ("online", "offline"):
            seen = timezone.localtime(self.seen_at)
            if seen.date() == timezone.localdate():
                return f"bugun {seen:%H:%M} da ko'rilgan"
            return f"{seen:%d.%m.%Y %H:%M} da ko'rilgan"
        return {"recently": "yaqinda ko'rilgan", "week": "shu hafta ko'rilgan", "month": "shu oy ko'rilgan"}.get(
            self.seen_kind, ""
        )


class Message(models.Model):
    dialog = models.ForeignKey(Dialog, on_delete=models.CASCADE, related_name="messages")
    tg_id = models.BigIntegerField()
    outgoing = models.BooleanField(default=False)
    text = models.TextField(blank=True)
    media_pending = models.BooleanField(default=False)  # runner faylni alohida navbat bilan yuklaydi
    media = models.FileField(upload_to="telegram/photos", blank=True)
    media_kind = models.CharField(max_length=10, blank=True)  # photo, sticker, video, round, voice, audio, document
    mime = models.CharField(max_length=100, blank=True)
    file_name = models.CharField(max_length=200, blank=True)
    reply_to_id = models.BigIntegerField(null=True, blank=True)
    edited = models.BooleanField(default=False)
    # Xabar bazadan hech qachon o'chirilmaydi: Telegram'da o'chsa, shu belgi qo'yiladi
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by_me = models.BooleanField(default=False)  # faqat paneldan o'chirilgani aniq ma'lum
    date = models.DateTimeField()

    class Meta:
        ordering = ["-date", "-tg_id"]
        constraints = [models.UniqueConstraint(fields=["dialog", "tg_id"], name="userbot_message_unique")]

    def __str__(self):
        return self.text[:60]

    @property
    def caption(self):
        """Matn; media ko'rsatilayotgan bo'lsa «[Rasm]» kabi yorliqsiz."""
        return "" if self.media and self.text in MEDIA_LABELS else self.text

    @property
    def is_inline(self):
        return self.mime in INLINE_MIMES


class MessageEdit(models.Model):
    """Tahrirdan oldingi matn."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="edits")
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.text[:60]


class Outbox(TimeStamped):
    """Paneldan berilgan topshiriq (xabar, tahrir, o'chirish...). ``manage.py userbot`` bajaradi."""

    class Kind(models.TextChoices):
        SEND = "send", "Xabar"
        EDIT = "edit", "Tahrir"
        DELETE = "delete", "O'chirish"
        READ = "read", "O'qildi"
        HISTORY = "history", "Eski xabarlar"
        OPEN = "open", "Yangi suhbat"
        VOICE = "voice", "Ovozli xabar"

    class Status(models.TextChoices):
        PENDING = "pending", "Navbatda"
        SENDING = "sending", "Yuborilmoqda"
        SENT = "sent", "Yuborildi"
        FAILED = "failed", "Yuborilmadi"

    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.SEND)
    dialog = models.ForeignKey(Dialog, null=True, blank=True, on_delete=models.CASCADE, related_name="outbox")
    text = models.TextField(blank=True)
    target_id = models.BigIntegerField(null=True, blank=True)
    reply_to_id = models.BigIntegerField(null=True, blank=True)
    file = models.FileField(upload_to="telegram/outbox", blank=True)
    voice = models.CharField(max_length=30, blank=True)
    speed = models.CharField(max_length=8, blank=True)
    debt = models.ForeignKey(
        "finance.Debt", null=True, blank=True, on_delete=models.SET_NULL, related_name="voice_reminders"
    )
    file_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.text[:60]
