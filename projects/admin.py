from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "status", "deadline", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    autocomplete_fields = ("client",)
