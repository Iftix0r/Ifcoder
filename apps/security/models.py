"""Xavfsizlik jurnali: kim, qachon, qayerdan. Baza sizib chiqsa ham sessiya kaliti ochilmasligi uchun xesh saqlanadi."""

from django.conf import settings
from django.db import models


class Event(models.Model):
    class Kind(models.TextChoices):
        LOGIN_OK = "login_ok", "Kirish"
        LOGIN_FAIL = "login_fail", "Xato parol"
        NEW_IP = "new_ip", "Sessiya yangi IP'dan"
        TRAP = "trap", "Skaner"
        LEAK = "leak", "Maxfiy fayl yuklandi"
        KILLED = "killed", "Sessiya yopildi"

    TONE = {"login_ok": "badge-success", "login_fail": "badge-warning", "new_ip": "badge-warning"}
    TONE |= {"trap": "badge-neutral", "leak": "badge-danger", "killed": "badge-neutral"}

    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)
    ip = models.CharField(max_length=45, blank=True, db_index=True)
    user_agent = models.CharField(max_length=300, blank=True)
    path = models.CharField(max_length=300, blank=True)
    username = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.ip}"

    @property
    def badge(self):
        return self.TONE.get(self.kind, "badge-neutral")


class TrustedIP(models.Model):
    """To'liq IP yoki boshi: «84.54.» kabi. Bu manzillardan kirishga ogohlantirish kelmaydi."""

    ip = models.CharField("IP yoki boshi", max_length=45, unique=True)
    note = models.CharField("Izoh", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ip"]

    def __str__(self):
        return self.ip


class SessionRecord(models.Model):
    key_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="session_records")
    ip = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.user} {self.ip}"


class ScanState(models.Model):
    """Apache logi qayergacha o'qilgani: {fayl: pozitsiya}."""

    offsets = models.JSONField(default=dict)
    scanned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.scanned_at)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]
