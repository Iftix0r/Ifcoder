from django.db import models


class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        PUBLISHED = "published", "Nashr etilgan"

    title = models.CharField("Sarlavha", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True)
    body = models.TextField("Matn", blank=True)
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField("Nashr sanasi", null=True, blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Blog post"
        verbose_name_plural = "Blog postlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Idea(models.Model):
    class Platform(models.TextChoices):
        YOUTUBE = "youtube", "YouTube"
        INSTAGRAM = "instagram", "Instagram"
        TELEGRAM = "telegram", "Telegram"

    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        IN_PROGRESS = "in_progress", "Jarayonda"
        DONE = "done", "Tayyor"

    title = models.CharField("Sarlavha", max_length=200)
    platform = models.CharField(
        "Platforma", max_length=20, choices=Platform.choices, default=Platform.TELEGRAM
    )
    description = models.TextField("Tavsif", blank=True)
    status = models.CharField(
        "Holati", max_length=20, choices=Status.choices, default=Status.NEW
    )
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "G'oya"
        verbose_name_plural = "G'oyalar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
