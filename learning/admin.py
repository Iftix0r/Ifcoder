from django.contrib import admin
from .models import Topic, FlashCard, LearningNote, AiTutorMessage


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "icon", "order")
    list_filter = ("category",)
    prepopulated_fields = {"slug": ("title",)}


@admin.register(FlashCard)
class FlashCardAdmin(admin.ModelAdmin):
    list_display = ("front_text", "category", "is_mastered", "created_at")
    list_filter = ("category", "is_mastered")
    search_fields = ("front_text", "back_text", "example_sentence")


@admin.register(LearningNote)
class LearningNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "updated_at")
    list_filter = ("category",)
    search_fields = ("title", "content", "tags")


@admin.register(AiTutorMessage)
class AiTutorMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "mode", "user_prompt", "created_at")
    list_filter = ("mode",)
