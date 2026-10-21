from django.db import models

from apps.core.models import Currency, TimeStamped


class Resource(TimeStamped):
    class Kind(models.TextChoices):
        DOMAIN = "domain", "Domen"
        SERVER = "server", "Server / hosting"
        SUBSCRIPTION = "subscription", "Obuna / servis"
        SSL = "ssl", "SSL sertifikat"

    class Billing(models.TextChoices):
        MONTHLY = "monthly", "Oylik"
        YEARLY = "yearly", "Yillik"
        ONCE = "once", "Bir martalik"
        FREE = "free", "Bepul"

    KIND_ICON = {"domain": "globe", "server": "server", "subscription": "credit-card", "ssl": "shield-check"}

    name = models.CharField("Nomi", max_length=200, help_text="example.uz, VPS-1, GitHub Copilot…")
    kind = models.CharField("Turi", max_length=12, choices=Kind.choices, default=Kind.DOMAIN)
    provider = models.CharField("Provayder", max_length=120, blank=True)
    url = models.URLField("Panel havolasi", blank=True)
    ip_address = models.CharField("IP / host", max_length=100, blank=True)
    renews_on = models.DateField("Tugash / yangilanish sanasi", null=True, blank=True)
    billing = models.CharField("To'lov davri", max_length=8, choices=Billing.choices, default=Billing.YEARLY)
    cost = models.DecimalField("Narxi", max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.USD)
    auto_renew = models.BooleanField("Avtomatik yangilanadi", default=False)
    is_active = models.BooleanField("Faol", default=True)
    project = models.ForeignKey(
        "projects.Project", verbose_name="Loyiha", null=True, blank=True, on_delete=models.SET_NULL, related_name="resources"
    )
    notes = models.TextField("Izoh", blank=True)

    class Meta:
        ordering = ["-is_active", "renews_on", "name"]
        verbose_name = "Resurs"
        verbose_name_plural = "Resurslar"

    def __str__(self):
        return self.name

    @property
    def icon(self):
        return self.KIND_ICON[self.kind]
