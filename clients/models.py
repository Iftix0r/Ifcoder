from django.db import models


class Client(models.Model):
    name = models.CharField("Ism / kompaniya", max_length=200)
    phone = models.CharField("Telefon", max_length=30, blank=True)
    telegram = models.CharField("Telegram username", max_length=100, blank=True)
    email = models.EmailField("Email", blank=True)
    notes = models.TextField("Izoh", blank=True)
    created_at = models.DateTimeField("Qo'shilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
