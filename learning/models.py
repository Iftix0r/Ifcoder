from django.contrib.auth.models import User
from django.db import models


class LearningCategory(models.TextChoices):
    ENGLISH = "english", "🇬🇧 Ingliz Tili (IT & Business)"
    CODING = "coding", "💻 Dasturlash & Architecture"
    BUSINESS = "business", "💼 Biznes & Monetizatsiya"


class Topic(models.Model):
    category = models.CharField(
        "Toifa", max_length=20, choices=LearningCategory.choices, default=LearningCategory.ENGLISH
    )
    title = models.CharField("Mavzu Sarlavhasi", max_length=200)
    slug = models.SlugField("Slug", max_length=200, unique=True)
    description = models.TextField("Tavsif", blank=True)
    icon = models.CharField("Emoji / Icon", max_length=50, default="📖")
    order = models.PositiveIntegerField("Tartib", default=0)

    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"
        ordering = ["category", "order", "id"]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class FlashCard(models.Model):
    category = models.CharField(
        "Toifa", max_length=20, choices=LearningCategory.choices, default=LearningCategory.ENGLISH
    )
    topic = models.ForeignKey(
        Topic,
        verbose_name="Mavzu",
        related_name="cards",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    front_text = models.CharField("Savol / So'z / Tushuncha", max_length=255)
    pronunciation = models.CharField("Talaffuz (Transkripsiya)", max_length=100, blank=True)
    back_text = models.TextField("Ma'nosi / Izohi / Yechim")
    example_sentence = models.TextField("Misol Matn / Senariy", blank=True)
    code_snippet = models.TextField("Kod Namunasi", blank=True)
    is_mastered = models.BooleanField("O'zlashtirildi", default=False)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)

    class Meta:
        verbose_name = "Lug'at / Kartochka"
        verbose_name_plural = "Lug'atlar va Kartochkalar"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.front_text} ({self.get_category_display()})"


class LearningNote(models.Model):
    user = models.ForeignKey(
        User, verbose_name="Foydalanuvchi", on_delete=models.CASCADE, related_name="learning_notes"
    )
    category = models.CharField(
        "Toifa", max_length=20, choices=LearningCategory.choices, default=LearningCategory.ENGLISH
    )
    title = models.CharField("Sarlavha", max_length=200)
    content = models.TextField("Qayd Matni (Markdown / Text)")
    tags = models.CharField("Teglar (vergul bilan)", max_length=200, blank=True)
    created_at = models.DateTimeField("Yaratilgan sana", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan sana", auto_now=True)

    class Meta:
        verbose_name = "Shaxsiy Qayd"
        verbose_name_plural = "Shaxsiy Qaydlar"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class AiTutorMessage(models.Model):
    class Mode(models.TextChoices):
        ENGLISH = "english", "🇬🇧 English Conversation & Grammar"
        CODING = "coding", "💻 Code Review & Architecture"
        BUSINESS = "business", "💼 Business & Client Pitching"

    user = models.ForeignKey(
        User, verbose_name="Foydalanuvchi", on_delete=models.CASCADE, related_name="ai_tutor_messages"
    )
    mode = models.CharField("Rejim", max_length=20, choices=Mode.choices, default=Mode.ENGLISH)
    user_prompt = models.TextField("Foydalanuvchi Savoli")
    ai_response = models.TextField("AI Javobi")
    feedback = models.TextField("Tahlil / Xatolar / Tavsiyalar", blank=True)
    created_at = models.DateTimeField("Vaqt", auto_now_add=True)

    class Meta:
        verbose_name = "AI Tutor Xabari"
        verbose_name_plural = "AI Tutor Xabarlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_mode_display()}] {self.user_prompt[:30]}..."
