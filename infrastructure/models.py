from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ExpiringQuerySet(models.QuerySet):
    def expiring_soon(self, days=30):
        today = timezone.localdate()
        return self.filter(
            expiration_date__gte=today, expiration_date__lte=today + timedelta(days=days)
        )

    def expired(self):
        return self.filter(expiration_date__lt=timezone.localdate())


class Domain(models.Model):
    name = models.CharField("Nomi", max_length=200, unique=True)
    registrar = models.CharField("Registrator", max_length=150, blank=True)
    expiration_date = models.DateField("Tugash sanasi")
    auto_renew = models.BooleanField("Avtomatik uzaytirish", default=False)
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    objects = ExpiringQuerySet.as_manager()

    class Meta:
        verbose_name = "Domen"
        verbose_name_plural = "Domenlar"
        ordering = ["expiration_date"]

    def __str__(self):
        return self.name

    @property
    def is_expired(self):
        return self.expiration_date < timezone.localdate()

    @property
    def is_expiring_soon(self):
        return not self.is_expired and self.expiration_date <= timezone.localdate() + timedelta(
            days=30
        )


class Server(models.Model):
    name = models.CharField("Nomi", max_length=150)
    ip_address = models.GenericIPAddressField("IP manzil")
    provider = models.CharField("Provayder", max_length=150, blank=True)
    specs = models.TextField("Xarakteristika / izoh", blank=True)
    ssh_port = models.PositiveIntegerField("SSH port", default=22)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Server"
        verbose_name_plural = "Serverlar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SSLCertificate(models.Model):
    domain = models.ForeignKey(
        Domain,
        verbose_name="Domen",
        related_name="certificates",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    name = models.CharField(
        "Nomi", max_length=200, blank=True, help_text="Domen tanlanmasa, erkin nom kiriting"
    )
    issuer = models.CharField("Beruvchi (issuer)", max_length=150, blank=True)
    expiration_date = models.DateField("Tugash sanasi")
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    objects = ExpiringQuerySet.as_manager()

    class Meta:
        verbose_name = "SSL sertifikat"
        verbose_name_plural = "SSL sertifikatlar"
        ordering = ["expiration_date"]

    def __str__(self):
        return self.name or (self.domain.name if self.domain else f"Sertifikat #{self.pk}")

    def clean(self):
        if not self.domain and not self.name:
            raise ValidationError("Domen yoki nom kiritilishi shart.")

    @property
    def is_expired(self):
        return self.expiration_date < timezone.localdate()

    @property
    def is_expiring_soon(self):
        return not self.is_expired and self.expiration_date <= timezone.localdate() + timedelta(
            days=30
        )
