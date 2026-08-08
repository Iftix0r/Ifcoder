from django.contrib import admin

from .models import BlogPost, Idea


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "published_at", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ("title", "platform", "status", "created_at")
    list_filter = ("platform", "status")
    search_fields = ("title", "description")
