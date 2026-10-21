from django.db import models

from apps.core.models import TimeStamped


class Note(TimeStamped):
    class Kind(models.TextChoices):
        NOTE = "note", "Eslatma"
        SNIPPET = "snippet", "Kod parchasi"
        LINK = "link", "Havola"
        IDEA = "idea", "G'oya"

    KIND_STYLE = {
        "note": ("sticky-note", "tone-amber"),
        "snippet": ("code-xml", "tone-violet"),
        "link": ("link", "tone-cyan"),
        "idea": ("lightbulb", "tone-emerald"),
    }

    title = models.CharField("Sarlavha", max_length=200)
    kind = models.CharField("Turi", max_length=8, choices=Kind.choices, default=Kind.NOTE)
    body = models.TextField("Matn / kod", blank=True)
    language = models.CharField("Til", max_length=30, blank=True, help_text="python, bash, sql…")
    url = models.URLField("Havola", blank=True)
    tags = models.CharField("Teglar", max_length=200, blank=True)
    pinned = models.BooleanField("Qadab qo'yish", default=False)
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="Loyiha",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notes",
    )

    class Meta:
        ordering = ["-pinned", "-updated_at"]
        verbose_name = "Eslatma"
        verbose_name_plural = "Eslatmalar"

    def __str__(self):
        return self.title

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def icon(self):
        return self.KIND_STYLE[self.kind][0]

    @property
    def tone(self):
        return self.KIND_STYLE[self.kind][1]
