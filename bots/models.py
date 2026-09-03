from django.db import models

from clients.models import Client
from projects.models import Project


class Bot(models.Model):
    class Platform(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"
        OTHER = "other", "Boshqa"

    class Status(models.TextChoices):
        ACTIVE = "active", "Faol"
        INACTIVE = "inactive", "Faol emas"

    name = models.CharField("Nomi", max_length=200)
    username = models.CharField("Username", max_length=100, blank=True)
    platform = models.CharField(
        "Platforma", max_length=20, choices=Platform.choices, default=Platform.TELEGRAM
    )
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    project = models.ForeignKey(
        Project,
        verbose_name="Loyiha",
        related_name="bots",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        related_name="bots",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Bot"
        verbose_name_plural = "Botlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


from vault.crypto import decrypt_value, encrypt_value


class UserbotConfig(models.Model):
    phone_number = models.CharField("Telefon raqam (+998...)", max_length=50, blank=True)
    api_id = models.CharField("API ID (my.telegram.org)", max_length=50, blank=True)
    encrypted_api_hash = models.TextField("Shifrlangan API Hash", blank=True, editable=False)
    encrypted_session = models.TextField("Shifrlangan Session", blank=True, editable=False)
    is_active = models.BooleanField("Avto-javob faol", default=False)
    auto_reply_message = models.TextField(
        "Avto-javob matni",
        default="Salom! Hozir bandman. Murojaatingiz iftix0r.uz CRM tizimiga qabul qilindi. Tez orada siz bilan bog'lanaman.",
    )
    reply_once_per_user = models.BooleanField("Bir foydalanuvchiga 1 marta yuborish", default=True)
    ai_reply_enabled = models.BooleanField("AI (OpenAI) orqali javob berish", default=False)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan sana", auto_now=True)

    class Meta:
        verbose_name = "Userbot Sozlamasi"
        verbose_name_plural = "Userbot Sozlamalari"

    def __str__(self):
        return f"Userbot ({self.phone_number or 'Sozlanmagan'})"

    def set_api_hash(self, plain: str) -> None:
        self.encrypted_api_hash = encrypt_value(plain) if plain else ""

    def get_api_hash(self) -> str:
        if not self.encrypted_api_hash:
            return ""
        try:
            return decrypt_value(self.encrypted_api_hash)
        except Exception:
            return ""

    def set_session(self, plain: str) -> None:
        self.encrypted_session = encrypt_value(plain) if plain else ""

    def get_session(self) -> str:
        if not self.encrypted_session:
            return ""
        try:
            return decrypt_value(self.encrypted_session)
        except Exception:
            return ""

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class TelegramMessage(models.Model):
    class MediaType(models.TextChoices):
        TEXT = "text", "Matn"
        PHOTO = "photo", "Rasm"
        VIDEO = "video", "Video"
        VOICE = "voice", "Ovozli xabar"
        DOCUMENT = "document", "Fayl"
        OTHER = "other", "Boshqa"

    message_id = models.BigIntegerField("Telegram Message ID")
    chat_id = models.BigIntegerField("Telegram Chat ID", db_index=True)
    sender_id = models.BigIntegerField("Sender ID", null=True, blank=True)
    sender_name = models.CharField("Yuboruvchi ismi", max_length=200, blank=True)
    is_outgoing = models.BooleanField("Chiquvchi xabar", default=False)
    text = models.TextField("Xabar matni", blank=True)

    media_type = models.CharField(
        "Media turi", max_length=20, choices=MediaType.choices, default=MediaType.TEXT
    )
    media_file = models.FileField("Media fayli", upload_to="telegram_chat_media/", blank=True, null=True)

    is_edited = models.BooleanField("Tahrirlangan", default=False)
    original_text = models.TextField("Asl matn (tahrirdan oldingi)", blank=True)

    is_deleted = models.BooleanField("Telegramda o'chirilgan", default=False)
    deleted_at = models.DateTimeField("O'chirilgan vaqti", null=True, blank=True)

    is_read = models.BooleanField("O'qilgan", default=False, db_index=True)

    client = models.ForeignKey(
        Client,
        verbose_name="Mijoz",
        related_name="telegram_messages",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Telegram Xabari"
        verbose_name_plural = "Telegram Xabarlari"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["chat_id", "message_id"]),
        ]

    def __str__(self):
        return f"Msg #{self.message_id} in Chat {self.chat_id} ({self.sender_name})"

